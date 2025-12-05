"""
https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.4.md#security-scheme-object
"""
from __future__ import annotations

from typing import Literal, ClassVar, Any, Iterable

from inspect import getdoc

import aiohttp_security
from aiohttp.abc import BaseRequest
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from dataclasses import dataclass
from enum import Enum

from aiohttp_pydantic.injectors import AbstractInjector, CONTEXT

type SchemeName = Literal[
    "Basic",
    "Bearer",
    "Concealed",
    "Digest",
    "DPoP",
    "GNAP",
    "HOBA",
    "Mutual",
    "Negotiate",
    "OAuth",
    "PrivateToken",
    "SCRAM-SHA-1",
    "SCRAM-SHA-256",
    "vapid",
]

SCHEME_NAMES: frozenset[str] = frozenset((
    "Basic",
    "Bearer",
    "Concealed",
    "Digest",
    "DPoP",
    "GNAP",
    "HOBA",
    "Mutual",
    "Negotiate",
    "OAuth",
    "PrivateToken",
    "SCRAM-SHA-1",
    "SCRAM-SHA-256",
    "vapid"
))


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
        await self._security_scheme()
        kwargs_view.update(**{self._arg_name: self._security_scheme})


class SecurityScheme:
    type: ClassVar[str]

    def __init__(self, *, permissions=(), location=None, name=None, user_id=None):
        self._permissions = permissions
        self._location = location
        self._name = name
        self._user_id = user_id

    def security_scheme(self) -> dict:
        oas = {
            "type": self.type,
            "in": self._location,
        }
        if description := getdoc(self):
            oas["description"] = description
        return oas

    async def __call__(self, *args, **kwargs):
        pass
        # TODO: call one of:
        # aiohttp_security.check_authorized
        # aiohttp_security.check_permission
        # aiohttp_security.is_anonymous

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        return core_schema.is_instance_schema(cls)


class HTTPSecurityScheme(SecurityScheme):
    """
    Basic, Bearer and other HTTP authentications schemes

    If the scheme is Bearer, you can provide a hint to the client to identify
    how the bearer token is formatted by defining the class attribute `bearer_format`.
    """

    type: ClassVar[str] = "http"
    scheme: ClassVar[SchemeName]
    bearer_format: ClassVar[str]

    def security_scheme(self) -> dict:
        schema = super().security_scheme()
        schema["scheme"] = self.scheme
        if type == "bearer":
            if bearer_format := getattr(self, "bearer_format", ""):
                schema["bearerFormat"] = bearer_format
        return schema

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "scheme", "") not in SCHEME_NAMES:
            raise AttributeError(f"The class {cls} must define an attribute 'scheme'"
                                 f" and its value must be one of  {SCHEME_NAMES}")


class APIKeySecurityScheme(SecurityScheme):
    """
    API keys and cookie authentication
    """

    type: ClassVar[str] = "apiKey"

    def __init__(self):
        super().__init__()
        self._name = None  # Should be set by the framework.

    def security_scheme(self) -> dict:
        schema = super().security_scheme()
        schema["name"] = self._name
        return schema


class OAuth2SecurityScheme(SecurityScheme):
    """
    OAuth 2
    """
    type: ClassVar[str] = "oauth2"

    def __init__(self, flows):
        self._flows = flows
        super().__init__()

    def security_scheme(self) -> dict:
        schema = super().security_scheme()
        schema["flows"] = self._flows
        return schema


class OpenIdConnectSecurityScheme(SecurityScheme):
    """
    OpenID Connect Discovery
    """
    type: ClassVar[str] = "openIdConnect"

    def __init__(self, url: str):
        self._url = url
        super().__init__()

    def security_scheme(self) -> dict:
        schema = super().security_scheme()
        schema["openIdConnectUrl"] = self._url
        return schema
