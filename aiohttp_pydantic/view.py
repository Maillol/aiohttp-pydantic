import warnings
from typing import Any, ClassVar, Generator, Set

from aiohttp.abc import AbstractView
from aiohttp.hdrs import METH_ALL
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_response import StreamResponse
from pydantic import ValidationError

from .decorator import inject_params, json_response_error
from .injectors import (
    CONTEXT,
    AbstractInjector,
    BodyGetter,
    Group,
    HeadersGetter,
    MatchInfoGetter,
    QueryGetter,
)


class PydanticView(AbstractView):
    """
    An AIOHTTP View that validate request using function annotations.
    """

    # Allowed HTTP methods; overridden when subclassed.
    allowed_methods: ClassVar[Set[str]] = set()

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
                handler = getattr(cls, meth_name.lower())
                decorated_handler = inject_params.in_method(handler)
                setattr(cls, meth_name.lower(), decorated_handler)

    def _raise_allowed_methods(self) -> None:
        raise HTTPMethodNotAllowed(self.request.method, self.allowed_methods)

    def raise_not_allowed(self) -> None:
        warnings.warn(
            "PydanticView.raise_not_allowed is deprecated and renamed _raise_allowed_methods",
            DeprecationWarning,
            stacklevel=2,
        )
        self._raise_allowed_methods()

    async def on_validation_error(
        self, exception: ValidationError, context: CONTEXT
    ) -> StreamResponse:
        """
        This method is a hook to intercept ValidationError.

        This hook can be redefined to return a custom HTTP response error.
        The exception is a pydantic.ValidationError and the context is "body",
        "headers", "path" or "query string"
        """
        return await json_response_error(exception, context)


def is_pydantic_view(obj) -> bool:
    """
    Return True if obj is a PydanticView subclass else False.
    """
    try:
        return issubclass(obj, PydanticView)
    except TypeError:
        return False


__all__ = (
    "AbstractInjector",
    "BodyGetter",
    "HeadersGetter",
    "MatchInfoGetter",
    "QueryGetter",
    "CONTEXT",
    "Group",
)
