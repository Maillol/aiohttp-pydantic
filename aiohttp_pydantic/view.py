from functools import update_wrapper
from inspect import iscoroutinefunction, getattr_static
from typing import Any, Generator, Set, ClassVar, Type

from aiohttp.abc import AbstractView
from aiohttp.hdrs import METH_ALL
from aiohttp.web import json_response
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_response import StreamResponse
from pydantic import ValidationError

from .injectors import (
    AbstractInjector,
    BodyGetter,
    HeadersGetter,
    MatchInfoGetter,
    QueryGetter,
    FuncSignatureParser,
    CONTEXT,
    Group,
)


class PydanticView(AbstractView):
    """
    An AIOHTTP View that validate request using function annotations.
    """

    # Allowed HTTP methods; overridden when subclassed.
    allowed_methods: ClassVar[Set[str]] = {}
    func_signature_parser: ClassVar[Type[FuncSignatureParser]] = FuncSignatureParser

    async def _iter(self) -> StreamResponse:
        if (method_name := self.request.method) not in self.allowed_methods:
            self._raise_allowed_methods()
        return await getattr(self, method_name.lower())()

    def __await__(self) -> Generator[Any, None, StreamResponse]:
        return self._iter().__await__()

    def __init_subclass__(cls, **kwargs) -> None:
        """Define allowed methods and decorate handlers.

        Handlers are decorated if and only if they directly bound on the PydanticView class or
        PydanticView subclass. This prevents that methods are decorated multiple times and that method
        defined in aiohttp.View parent class is decorated.
        """

        cls.allowed_methods = {
            meth_name for meth_name in METH_ALL if hasattr(cls, meth_name.lower())
        }

        for meth_name in METH_ALL:
            if meth_name.lower() in vars(cls):
                static_handler = getattr_static(cls, meth_name.lower())
                handler = getattr(cls, meth_name.lower())
                if isinstance(static_handler, (staticmethod, classmethod)):
                    decorator = inject_params_decorator_builder(
                        func_signature_parser=cls.func_signature_parser,
                        target_type='staticmethod',
                        on_validation_error=cls.on_validation_error)
                else:
                    decorator = inject_params_decorator_builder(
                        func_signature_parser=cls.func_signature_parser,
                        target_type='method',
                        on_validation_error=cls.on_validation_error)
                decorated_handler = decorator(handler)
                setattr(cls, meth_name.lower(), decorated_handler)

    def _raise_allowed_methods(self) -> None:
        raise HTTPMethodNotAllowed(self.request.method, self.allowed_methods)

    @staticmethod
    async def on_validation_error(
        request, exception: ValidationError, context: CONTEXT
    ) -> StreamResponse:
        """
        This method is a hook to intercept ValidationError.

        This hook can be redefined to return a custom HTTP response error.
        The exception is a pydantic.ValidationError and the context is "body",
        "headers", "path" or "query string"
        """
        errors = exception.errors()
        for error in errors:
            error["in"] = context

        return json_response(data=errors, status=400)

    @classmethod
    def decorator(cls):
        """
        Return a decorator to use pydantic with http handler.
        """
        return inject_params_decorator_builder(
            func_signature_parser=cls.func_signature_parser,
            target_type='function',
            on_validation_error=cls.on_validation_error)


def inject_params_decorator_builder(
    *,
    func_signature_parser: Type[FuncSignatureParser],
    target_type='function',
    on_validation_error,
):
    """
    Build a decorator to unpack the query string, route path, body and http header in
    the parameters of the web handler regarding annotations.
    """

    def inject_params_decorator(handler):
        """
        Decorator to unpack the query string, route path, body and http header in
        the parameters of the web handler regarding annotations.
        """
        func_parser = func_signature_parser()
        func_parser.parse(handler)
        injectors = func_parser.injectors()

        if target_type == 'function':
            async def wrapped_handler(request):
                args = []
                kwargs = {}
                for injector in injectors:
                    try:
                        if iscoroutinefunction(injector.inject):
                            await injector.inject(request, args, kwargs)
                        else:
                            injector.inject(request, args, kwargs)
                    except ValidationError as error:
                        return await on_validation_error(request, error, injector.context)

                return await handler(request, *args, **kwargs)

            wrapped_handler.is_pydantic_handler = True

        elif target_type == 'method':
            async def wrapped_handler(self):
                args = []
                kwargs = {}
                for injector in injectors:
                    try:
                        if iscoroutinefunction(injector.inject):
                            await injector.inject(self.request, args, kwargs)
                        else:
                            injector.inject(self.request, args, kwargs)
                    except ValidationError as error:
                        return await on_validation_error(self.request, error, injector.context)

                return await handler(self, *args, **kwargs)

        elif target_type == 'staticmethod':
            async def wrapped_handler(self):
                args = []
                kwargs = {}
                for injector in injectors:
                    try:
                        if iscoroutinefunction(injector.inject):
                            await injector.inject(self.request, args, kwargs)
                        else:
                            injector.inject(self.request, args, kwargs)
                    except ValidationError as error:
                        return await on_validation_error(self.request, error, injector.context)

                return await handler(*args, **kwargs)

        update_wrapper(wrapped_handler, handler)
        return wrapped_handler

    return inject_params_decorator


def is_pydantic_view(obj) -> bool:
    """
    Return True if obj is a PydanticView subclass else False.
    """
    try:
        return issubclass(obj, PydanticView)
    except TypeError:
        return False


def is_pydantic_handler(obj) -> bool:
    """
    Return True if obj is a function decorated with unpack_request.
    """
    return getattr(obj, "is_pydantic_handler", False)


__all__ = (
    "AbstractInjector",
    "BodyGetter",
    "HeadersGetter",
    "MatchInfoGetter",
    "QueryGetter",
    "CONTEXT",
    "Group",
)
