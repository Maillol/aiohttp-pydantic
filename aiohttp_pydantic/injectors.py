import abc
import typing
from inspect import signature, getmro
from json.decoder import JSONDecodeError
from types import SimpleNamespace
from typing import Callable, Tuple, Literal, Type

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import BaseRequest
from multidict import MultiDict
from pydantic import BaseModel

from .utils import is_pydantic_base_model, robuste_issubclass

CONTEXT = Literal["body", "headers", "path", "query string"]


class AbstractInjector(metaclass=abc.ABCMeta):
    """
    An injector parse HTTP request and inject params to the view.
    """

    model: Type[BaseModel]

    @property
    @abc.abstractmethod
    def context(self) -> CONTEXT:
        """
        The name of part of parsed request
        i.e "HTTP header", "URL path", ...
        """

    @abc.abstractmethod
    def __init__(self, args_spec: dict, default_values: dict):
        """
        args_spec - ordered mapping: arg_name -> type
        """

    @abc.abstractmethod
    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        """
        Get elements in request and inject them in args_view or kwargs_view.
        """


class MatchInfoGetter(AbstractInjector):
    """
    Validates and injects the part of URL path inside the view positional args.
    """

    context = "path"

    def __init__(self, args_spec: dict, default_values: dict):
        attrs = {"__annotations__": args_spec}
        attrs.update(default_values)
        self.model = type("PathModel", (BaseModel,), attrs)

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        args_view.extend(self.model(**request.match_info).dict().values())


class BodyGetter(AbstractInjector):
    """
    Validates and injects the content of request body inside the view kwargs.
    """

    context = "body"

    def __init__(self, args_spec: dict, default_values: dict):
        self.arg_name, self.model = next(iter(args_spec.items()))
        self._expect_object = self.model.schema()["type"] == "object"

    async def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        try:
            body = await request.json()
        except JSONDecodeError:
            raise HTTPBadRequest(
                text='{"error": "Malformed JSON"}', content_type="application/json"
            ) from None

        # Pydantic tries to cast certain structures, such as a list of 2-tuples,
        # to a dict. Prevent this by requiring the body to be a dict for object models.
        if self._expect_object and not isinstance(body, dict):
            raise HTTPBadRequest(
                text='[{"in": "body", "loc": ["__root__"], "msg": "value is not a '
                'valid dict", "type": "type_error.dict"}]',
                content_type="application/json",
            ) from None

        kwargs_view[self.arg_name] = self.model.parse_obj(body)


class QueryGetter(AbstractInjector):
    """
    Validates and injects the query string inside the view kwargs.
    """

    context = "query string"

    def __init__(self, args_spec: dict, default_values: dict):
        args_spec = args_spec.copy()

        self._groups = {}
        for group_name, group in args_spec.items():
            if robuste_issubclass(group, Group):
                self._groups[group_name] = (group, _get_group_signature(group)[0])

        _unpack_group_in_signature(args_spec, default_values)
        attrs = {"__annotations__": args_spec}
        attrs.update(default_values)

        self.model = type("QueryModel", (BaseModel,), attrs)
        self.args_spec = args_spec
        self._is_multiple = frozenset(
            name for name, spec in args_spec.items() if typing.get_origin(spec) is list
        )

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        data = self._query_to_dict(request.query)
        cleaned = self.model(**data).dict()
        for group_name, (group_cls, group_attrs) in self._groups.items():
            group = group_cls()
            for attr_name in group_attrs:
                setattr(group, attr_name, cleaned.pop(attr_name))
            cleaned[group_name] = group
        kwargs_view.update(**cleaned)

    def _query_to_dict(self, query: MultiDict):
        """
        Return a dict with list as value from the MultiDict.

        The value will be wrapped in a list if the args spec is define as a list or if
        the multiple values are sent (i.e ?foo=1&foo=2)
        """
        return {
            key: values
            if len(values := query.getall(key)) > 1 or key in self._is_multiple
            else value
            for key, value in query.items()
        }


class HeadersGetter(AbstractInjector):
    """
    Validates and injects the HTTP headers inside the view kwargs.
    """

    context = "headers"

    def __init__(self, args_spec: dict, default_values: dict):
        args_spec = args_spec.copy()

        self._groups = {}
        for group_name, group in args_spec.items():
            if robuste_issubclass(group, Group):
                self._groups[group_name] = (group, _get_group_signature(group)[0])

        _unpack_group_in_signature(args_spec, default_values)

        attrs = {"__annotations__": args_spec}
        attrs.update(default_values)
        self.model = type("HeaderModel", (BaseModel,), attrs)

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        header = {k.lower().replace("-", "_"): v for k, v in request.headers.items()}
        cleaned = self.model(**header).dict()
        for group_name, (group_cls, group_attrs) in self._groups.items():
            group = group_cls()
            for attr_name in group_attrs:
                setattr(group, attr_name, cleaned.pop(attr_name))
            cleaned[group_name] = group
        kwargs_view.update(cleaned)


class Group(SimpleNamespace):
    """
    Class to group header or query string parameters.

    The parameter from query string or header will be set in the group
    and the group will be passed as function parameter.

    Example:

    class Pagination(Group):
        current_page: int = 1
        page_size: int = 15

    class PetView(PydanticView):
        def get(self, page: Pagination):
            ...
    """


def _get_group_signature(cls) -> Tuple[dict, dict]:
    """
    Analyse Group subclass annotations and return them with default values.
    """

    sig = {}
    defaults = {}
    mro = getmro(cls)
    for base in reversed(mro[: mro.index(Group)]):
        attrs = vars(base)
        for attr_name, type_ in base.__annotations__.items():
            sig[attr_name] = type_
            if (default := attrs.get(attr_name)) is None:
                defaults.pop(attr_name, None)
            else:
                defaults[attr_name] = default

    return sig, defaults


def _parse_func_signature(
    func: Callable, unpack_group: bool = False
) -> Tuple[dict, dict, dict, dict, dict]:
    """
    Analyse function signature and returns 5-tuple:
        0 - arguments will be set from the url path
        1 - argument will be set from the request body.
        2 - argument will be set from the query string.
        3 - argument will be set from the HTTP headers.
        4 - Default value for each parameters
    """

    path_args = {}
    body_args = {}
    qs_args = {}
    header_args = {}
    defaults = {}

    for param_name, param_spec in signature(func).parameters.items():
        if param_name == "self":
            continue

        if param_spec.annotation == param_spec.empty:
            raise RuntimeError(f"The parameter {param_name} must have an annotation")

        if param_spec.default is not param_spec.empty:
            defaults[param_name] = param_spec.default

        if param_spec.kind is param_spec.POSITIONAL_ONLY:
            path_args[param_name] = param_spec.annotation

        elif param_spec.kind is param_spec.POSITIONAL_OR_KEYWORD:
            if is_pydantic_base_model(param_spec.annotation):
                body_args[param_name] = param_spec.annotation
            else:
                qs_args[param_name] = param_spec.annotation
        elif param_spec.kind is param_spec.KEYWORD_ONLY:
            header_args[param_name] = param_spec.annotation
        else:
            raise RuntimeError(f"You cannot use {param_spec.VAR_POSITIONAL} parameters")

    if unpack_group:
        try:
            _unpack_group_in_signature(qs_args, defaults)
            _unpack_group_in_signature(header_args, defaults)
        except DuplicateNames as error:
            raise TypeError(
                f"Parameters conflict in function {func},"
                f" the group {error.group} has an attribute named {error.attr_name}"
            ) from None

    return path_args, body_args, qs_args, header_args, defaults


class DuplicateNames(Exception):
    """
    Raised when a same parameter name is used in group and function signature.
    """

    group: Type[Group]
    attr_name: str

    def __init__(self, group: Type[Group], attr_name: str):
        self.group = group
        self.attr_name = attr_name
        super().__init__(
            f"Conflict with {group}.{attr_name} and function parameter name"
        )


def _unpack_group_in_signature(args: dict, defaults: dict) -> None:
    """
    Unpack in place each Group found in args.
    """
    for group_name, group in args.copy().items():
        if robuste_issubclass(group, Group):
            group_sig, group_default = _get_group_signature(group)
            for attr_name in group_sig:
                if attr_name in args and attr_name != group_name:
                    raise DuplicateNames(group, attr_name)

            del args[group_name]
            args.update(group_sig)
            defaults.update(group_default)
