from .security import SecurityScheme
from typing import Literal, Iterable


from aiohttp.abc import BaseRequest
from dataclasses import dataclass
from enum import Enum
from aiohttp_pydantic.injectors import AbstractInjector, CONTEXT


class TypeAnnotation:
    __slots__ = ()


@dataclass(frozen=True, init=False, slots=True)
class Permission(TypeAnnotation):

    permissions: tuple[str | Enum, ...]

    def __init__(self, *permissions: str | Enum):
        object.__setattr__(self, "permissions", permissions)


class SecurityInjector(AbstractInjector):

    _security_scheme: SecurityScheme

    def context(self) -> CONTEXT:
        """
        The name of part of parsed request
        i.e "HTTP header", "URL path", ...
        """
        return self._context

    def __init__(self, arg_name,
                 context: CONTEXT,
                 security_scheme_cls: type[SecurityScheme],
                 security_scheme_args: Iterable):

        if context not in ("query string", "headers"):
            raise ValueError("context must be 'query string' or 'headers'")

        location: Literal["query", "cookie", "header"]
        if context == "query string":
            location = "query"
        elif arg_name.lower() == "cookie":
            location = "cookie"
        else:
            location = "header"

        self._context = context
        self._arg_name = arg_name.lower()
        self._context = context

        kwargs = {}
        for args in security_scheme_args:
            if isinstance(args, Permission):
                kwargs["permissions"] = args.permissions

        self._security_scheme = security_scheme_cls(
            name=arg_name,
            location=location,
            **kwargs
        )

    async def inject(self, request: BaseRequest, args_view: list, kwargs_view: dict):
        # TODO: get the token and call the security scheme...
        #   Should SecurityInjector implemente aiohttp_pydantic.AbstractIdentityPolicy ?
        await self._security_scheme(request)
        kwargs_view.update(**{self._arg_name: self._security_scheme})
