"""
https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.4.md#security-scheme-object
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Literal

from aiohttp import web

from .base import SecurityScheme
from .exceptions import AuthenticationError

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

SCHEME_NAMES: frozenset[str] = frozenset(
    (
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
        "vapid",  # Web Push. Perhaps is not applicable.
    )
)


class HTTPSecurityScheme(SecurityScheme, ABC):
    """
    Basic, Bearer and other HTTP authentications schemes

    If the scheme is Bearer, you can provide a hint to the client to identify
    how the bearer token is formatted by defining the class attribute `bearer_format`.
    """

    type: ClassVar[str] = "http"
    scheme: ClassVar[SchemeName]
    bearer_format: ClassVar[str]

    def extract_credentials(self, request: web.Request) -> str:
        """
        Parse and validate the authorization header.

        Returns the extracted token if valid.
        Raises AuthenticationError if the header is missing, malformed,
        or uses an incorrect scheme.
        """
        header_identity = request.headers.get(self.parameter_name)

        if header_identity is None:
            raise AuthenticationError(f"{self.parameter_name.title()} header missing")

        parts = header_identity.split()
        if len(parts) != 2:
            raise AuthenticationError(
                f"Invalid {self.parameter_name.title()} header format"
            )

        scheme, token = parts
        if scheme.lower() != self.scheme.lower():
            raise AuthenticationError(
                f"Invalid authorization scheme. Should be {self.scheme}"
            )

        return token

    def to_openapi(self) -> dict:
        schema = super().to_openapi()
        scheme = self.scheme.lower()
        schema["scheme"] = scheme
        if scheme == "bearer":
            if bearer_format := getattr(self, "bearer_format", ""):
                schema["bearerFormat"] = bearer_format
        return schema

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "scheme", "") not in SCHEME_NAMES:
            raise AttributeError(
                f"The class {cls} must define an attribute 'scheme'"
                f" and its value must be one of  {SCHEME_NAMES}"
            )


class APIKeySecurityScheme(SecurityScheme, ABC):
    """
    API keys and cookie authentication
    """

    type: ClassVar[str] = "apiKey"
    parameter_name: ClassVar[str] = "X-Api-Key"

    def to_openapi(self) -> dict:
        schema = super().to_openapi()
        schema["in"] = self.location
        schema["name"] = self.parameter_name
        return schema

    def extract_credentials(self, request: web.Request) -> str:
        """
        Extract and validate the API key from the request.

        Returns the API key if found.
        Raises AuthenticationError if the key is missing or invalid.
        """
        if self.location == "header":
            api_key = request.headers.get(self.parameter_name)
        elif self.location == "query":
            api_key = request.query.get(self.parameter_name)
        elif self.location == "cookie":
            api_key = request.cookies.get(self.parameter_name)
        else:
            raise AttributeError(
                f"Invalid value for attribute 'location' for {self.__class__.__qualname__}. "
                f"Must be 'query', 'cookie' or 'header'"
            )

        if not api_key:
            raise AuthenticationError(
                f"{self.parameter_name} missing in {self.location}"
            )

        return api_key


class OAuth2SecurityScheme(SecurityScheme, ABC):
    """
    OAuth 2 authentication scheme.
    """

    type: ClassVar[str] = "oauth2"

    def __init__(self, flows: dict[str, Any]):
        self._flows = flows
        super().__init__()

    def to_openapi(self) -> dict:
        schema = super().to_openapi()
        schema["flows"] = self._flows
        return schema


class OpenIdConnectSecurityScheme(SecurityScheme, ABC):
    """
    OpenID Connect Discovery authentication scheme.
    """

    type: ClassVar[str] = "openIdConnect"

    def __init__(self, url: str):
        self._url = url
        super().__init__()

    def to_openapi(self) -> dict:
        schema = super().to_openapi()
        schema["openIdConnectUrl"] = self._url
        return schema
