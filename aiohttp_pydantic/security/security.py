"""
https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.4.md#security-scheme-object
"""
from __future__ import annotations

from abc import ABC
from typing import Literal, ClassVar, Any
from inspect import getdoc

from aiohttp_security.api import AUTZ_KEY
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from enum import Enum
from aiohttp_security.abc import AbstractIdentityPolicy, AbstractAuthorizationPolicy

from aiohttp import web


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
    "Digest",  # Deprecated
    "DPoP",  # OAuth2.1
    "GNAP",  # Future alternative OAuth ?
    "HOBA",  # Deprecated
    "Mutual",
    "Negotiate",
    "OAuth",  # Deprecated, become Bearer with OAuth2.
    "PrivateToken",
    "SCRAM-SHA-1",  # BDD, Perhaps is not applicable.
    "SCRAM-SHA-256",  # BDD, Perhaps is not applicable.
    "vapid"  # Web Push. Perhaps is not applicable.
))


class SecurityScheme(AbstractIdentityPolicy, ABC):

    type: ClassVar[str]

    def __init__(self, *, permission: str | Enum | None = None, location: Literal["query", "cookie", "header"],
                 name):
        self._permission = permission
        self._location = location
        self._name = name
        self._user_id = None

    def security_scheme(self) -> dict:
        oas = {
            "type": self.type,
            "in": self._location,
        }
        if description := getdoc(self):
            oas["description"] = description
        return oas

    async def __call__(self, request):
        identity_policy: AbstractIdentityPolicy = self
        autz_policy: AbstractAuthorizationPolicy | None = request.config_dict.get(AUTZ_KEY)
        if autz_policy is None:
            return None
        identity = await identity_policy.identify(request)
        if identity is None:
            return None  # non-registered user has None user_id

        self._user_id = await autz_policy.authorized_userid(identity)
        if self._user_id is None:
            raise web.HTTPUnauthorized()  # TODO: Allow Customisation.

        if self._permission is not None:
            allowed = await autz_policy.permits(identity, self._permission)  # TODO: How to pass context ?
            if not allowed:
                raise web.HTTPForbidden(reason="User does not have '{}' permission".format(self._permission))

    async def remember(self, request: web.Request,  # type: ignore[misc]
                       response: web.StreamResponse, identity: str, **kwargs: Any) -> None:
        """Remember identity.

        Modify response object by filling it's headers with remembered user.

        An individual identity policy and its consumers can decide on
        the composition and meaning of **kwargs.
        """
        pass

    async def forget(self, request: web.Request, response: web.StreamResponse) -> None:
        """ Modify response which can be used to 'forget' the
        current identity on subsequent requests."""
        pass


    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        return core_schema.is_instance_schema(cls)


class HTTPSecurityScheme(SecurityScheme, ABC):
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
        if self.scheme.lower() == "bearer":
            if bearer_format := getattr(self, "bearer_format", ""):
                schema["bearerFormat"] = bearer_format
        return schema

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "scheme", "") not in SCHEME_NAMES:
            raise AttributeError(f"The class {cls} must define an attribute 'scheme'"
                                 f" and its value must be one of  {SCHEME_NAMES}")



class APIKeySecurityScheme(SecurityScheme, ABC):
    """
    API keys and cookie authentication
    """

    type: ClassVar[str] = "apiKey"

    def security_scheme(self) -> dict:
        schema = super().security_scheme()
        schema["name"] = self._name
        return schema


class OAuth2SecurityScheme(SecurityScheme, ABC):
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
