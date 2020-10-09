from typing import Callable, Tuple

from aiohttp.web_request import BaseRequest
from pydantic import BaseModel
from inspect import signature


import abc


class AbstractInjector(metaclass=abc.ABCMeta):
    """
    An injector parse HTTP request and inject params to the view.
    """

    @abc.abstractmethod
    def __init__(self, args_spec: dict):
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

    def __init__(self, args_spec: dict):
        self.model = type("PathModel", (BaseModel,), {"__annotations__": args_spec})

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        args_view.extend(self.model(**request.match_info).dict().values())


class BodyGetter(AbstractInjector):
    """
    Validates and injects the content of request body inside the view kwargs.
    """

    def __init__(self, args_spec: dict):
        self.arg_name, self.model = next(iter(args_spec.items()))

    async def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        body = await request.json()
        kwargs_view[self.arg_name] = self.model(**body)


class QueryGetter(AbstractInjector):
    """
    Validates and injects the query string inside the view kwargs.
    """

    def __init__(self, args_spec: dict):
        self.model = type("QueryModel", (BaseModel,), {"__annotations__": args_spec})

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        kwargs_view.update(self.model(**request.query).dict())


class HeadersGetter(AbstractInjector):
    """
    Validates and injects the HTTP headers inside the view kwargs.
    """

    def __init__(self, args_spec: dict):
        self.model = type("HeaderModel", (BaseModel,), {"__annotations__": args_spec})

    def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        header = {k.lower().replace("-", "_"): v for k, v in request.headers.items()}
        kwargs_view.update(self.model(**header).dict())


def _parse_func_signature(func: Callable) -> Tuple[dict, dict, dict, dict]:
    """
    Analyse function signature and returns 4-tuple:
        0 - arguments will be set from the url path
        1 - argument will be set from the request body.
        2 - argument will be set from the query string.
        3 - argument will be set from the HTTP headers.
    """

    path_args = {}
    body_args = {}
    qs_args = {}
    header_args = {}

    for param_name, param_spec in signature(func).parameters.items():
        if param_name == "self":
            continue

        if param_spec.kind is param_spec.POSITIONAL_ONLY:
            path_args[param_name] = param_spec.annotation
        elif param_spec.kind is param_spec.POSITIONAL_OR_KEYWORD:
            if issubclass(param_spec.annotation, BaseModel):
                body_args[param_name] = param_spec.annotation
            else:
                qs_args[param_name] = param_spec.annotation
        elif param_spec.kind is param_spec.KEYWORD_ONLY:
            header_args[param_name] = param_spec.annotation
        else:
            raise RuntimeError(f"You cannot use {param_spec.VAR_POSITIONAL} parameters")

    return path_args, body_args, qs_args, header_args
