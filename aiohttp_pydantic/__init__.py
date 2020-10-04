from aiohttp.abc import AbstractView
from aiohttp.hdrs import METH_ALL
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_response import StreamResponse
from pydantic import BaseModel, ValidationError
from typing import Generator, Any
from aiohttp.web import json_response


class PydanticView(AbstractView):

    async def _iter(self) -> StreamResponse:
        method = getattr(self, self.request.method.lower(), None)
        resp = await method()
        return resp

    def __await__(self) -> Generator[Any, None, StreamResponse]:
        return self._iter().__await__()

    def __init_subclass__(cls, **kwargs):
        allowed_methods = {
            meth_name for meth_name in METH_ALL
            if hasattr(cls, meth_name.lower())}

        async def raise_not_allowed(self):
            raise HTTPMethodNotAllowed(self.request.method, allowed_methods)

        if 'GET' in allowed_methods:
            cls.get = inject_qs(cls.get)
        if 'POST' in allowed_methods:
            cls.post = inject_body(cls.post)
        if 'PUT' in allowed_methods:
            cls.put = inject_body(cls.put)

        for meth_name in METH_ALL:
            if meth_name not in allowed_methods:
                setattr(cls, meth_name.lower(), raise_not_allowed)


def inject_qs(handler):
    """
    Decorator to unpack the query string in the parameters of the web handler
    regarding annotations.
    """

    nb_header_params = handler.__code__.co_kwonlyargcount
    if nb_header_params:
        from_qs = frozenset(handler.__code__.co_varnames[:-nb_header_params])
        from_header = frozenset(handler.__code__.co_varnames[-nb_header_params:])
    else:
        from_qs = frozenset(handler.__code__.co_varnames)
        from_header = frozenset()

    qs_model_class = type(
        'QSModel', (BaseModel,),
        {'__annotations__': {k: v for k, v in handler.__annotations__.items() if k in from_qs and k != 'self'}})

    header_model_class = type(
        'HeaderModel', (BaseModel,),
        {'__annotations__': {k: v for k, v in handler.__annotations__.items() if k in from_header  and k != 'self'}})

    async def wrapped_handler(self):
        try:
            qs = qs_model_class(**self.request.query)
            header = header_model_class(**self.request.headers)

        except ValidationError as error:
            return json_response(text=error.json(), status=400)
            # raise HTTPBadRequest(
            #     reason='\n'.join(
            #         f'Error with query string parameter {", ".join(err["loc"])}:'
            #         f' {err["msg"]}' for err in error.errors()))

        return await handler(self, **qs.dict(), **header.dict())

    return wrapped_handler


def inject_body(handler):
    """
    Decorator to inject the request body as parameter of the web handler
    regarding annotations.
    """

    arg_name, model_class = next(
        ((arg_name, arg_type)
         for arg_name, arg_type in handler.__annotations__.items()
         if issubclass(arg_type, BaseModel)), (None, None))

    if arg_name is None:
        return handler

    async def wrapped_handler(self):
        body = await self.request.json()
        try:
            model = model_class(**body)
        except ValidationError as error:
            return json_response(text=error.json(), status=400)

        return await handler(self, **{arg_name: model})

    return wrapped_handler
