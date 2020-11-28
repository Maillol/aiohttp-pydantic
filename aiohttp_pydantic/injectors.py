import abc
from inspect import signature
from json.decoder import JSONDecodeError
from typing import Callable, Tuple

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import BaseRequest
from pydantic import BaseModel

from .utils import is_pydantic_base_model


class AbstractInjector(metaclass=abc.ABCMeta):
    """
    An injector parse HTTP request and inject params to the view.
    """

    @property
    @abc.abstractmethod
    def context(self) -> str:
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

    async def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        try:
            body = await request.json()
        except JSONDecodeError:
            raise HTTPBadRequest(
                text='{"error": "Malformed JSON"}', content_type="application/json"
            ) from None

        kwargs_view[self.arg_name] = self.model(**body)


class QueryGetter(AbstractInjector):
    """
    Validates and injects the query string inside the view kwargs.
    """

    context = "query string"

    def __init__(self, args_spec: dict, default_values: dict):
        attrs = {"__annotations__": args_spec}
        attrs.update(default_values)
        self.model = type("QueryModel", (BaseModel,), attrs)

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        kwargs_view.update(self.model(**request.query).dict())


class HeadersGetter(AbstractInjector):
    """
    Validates and injects the HTTP headers inside the view kwargs.
    """

    context = "headers"

    def __init__(self, args_spec: dict, default_values: dict):
        attrs = {"__annotations__": args_spec}
        attrs.update(default_values)
        self.model = type("HeaderModel", (BaseModel,), attrs)

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        header = {k.lower().replace("-", "_"): v for k, v in request.headers.items()}
        kwargs_view.update(self.model(**header).dict())


def _parse_func_signature(func: Callable) -> Tuple[dict, dict, dict, dict, dict]:
    """
    Analyse function signature and returns 4-tuple:
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

    return path_args, body_args, qs_args, header_args, defaults
