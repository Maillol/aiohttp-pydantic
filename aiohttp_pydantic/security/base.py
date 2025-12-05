from __future__ import annotations

import abc
from abc import ABC, abstractmethod
from inspect import getdoc
from typing import Any, ClassVar, Generic, Literal, Self

from aiohttp import web

from ._types import IdT, RuleT
from .exceptions import AuthenticationError, AuthorizationError


class AbstractAuthRule(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def authn(self, request: web.Request) -> list[tuple[AuthRule, Any]]:
        """
        Authenticate the request and return successful auth rules with their identities.

        Returns:
            List of tuples (auth_rule, identity) for each successful authentication.
        """

    @abc.abstractmethod
    async def authz(self, request: web.Request, identity, context) -> None:
        """
        Check authorization for the authenticated identity.

        Args:
            request: The current HTTP request
            identity: The authenticated user identity
            context: Validated handler parameters (path, query, body)

        Raises:
            AuthorizationError: If authorization fails
        """

    @abc.abstractmethod
    def to_openapi_security(self, app: web.Application) -> list[dict[str, list[str]]]:
        """
        Return the OpenAPI security declaration for an operation.

        Returns:
            List of security requirement objects
        """

    @abc.abstractmethod
    def to_openapi_security_schemes(
        self, app: web.Application
    ) -> dict[str, dict[str, Any]]:
        """
        Return the OpenAPI security schemes definitions for an operation.

        Returns:
            Dict mapping scheme names to their definitions
        """

    def __or__(self, other: AbstractAuthRule) -> OrAuthRule:
        return OrAuthRule(self, other)

    def __and__(self, other: AbstractAuthRule) -> AndAuthRule:
        return AndAuthRule(self, other)


class AuthRule(AbstractAuthRule, Generic[RuleT, IdT]):
    """
    A single security requirement bound to a specific authentication scheme.

    This is a leaf node in the authentication tree. It performs authentication
    using a specific SecurityScheme and checks permissions against a rule.
    """

    rule: RuleT
    __slots__ = ("key", "rule")

    def __init__(self, key: AuthSchemeRef[RuleT, IdT], rule: RuleT):
        self.key = key
        self.rule = rule

    async def authn(self, request: web.Request) -> list[tuple[AuthRule, IdT]]:
        """
        Authenticate using the bound security scheme.

        Returns:
            A single-element list containing (self, identity)

        Raises:
            ExceptionGroup with AuthenticationError: If authentication fails
        """
        security_scheme = request.app[AUTH_SCHEMES][self.key]
        try:
            identity = await security_scheme.authenticate(request)
        except* AuthenticationError:  # pylint: disable=try-except-raise
            raise  # Wrap leaf AuthenticationError in ExceptionGroup

        return [(self, identity)]

    async def authz(
        self, request: web.Request, identity: IdT, context: dict[str, Any]
    ) -> None:
        """
        Check if the identity has permission for the bound rule.

        Raises:
            AuthorizationError: If the permission check fails
        """
        security_scheme = request.app[AUTH_SCHEMES][self.key]
        if not await security_scheme.permits(request, identity, self.rule, context):
            raise AuthorizationError(self.rule)

    def to_openapi_security(self, app: web.Application) -> list[dict[str, list[str]]]:
        security_scheme = app[AUTH_SCHEMES][self.key]
        return [{self.key.name: security_scheme.to_openapi_scopes(self.rule)}]

    def to_openapi_security_schemes(self, app) -> dict[str, dict[str, Any]]:
        security_scheme = app[AUTH_SCHEMES][self.key]
        return {self.key.name: security_scheme.to_openapi()}

    def __repr__(self):
        return f"<AuthRule {self.key}>"


class OrAuthRule(AbstractAuthRule):
    """
    Only one of the security requirement objects need to be satisfied to authorize a request.

    Attempts authentication with the left branch first. If it succeeds,
    returns immediately (short-circuit). If it fails, tries the right branch.
    Both branches failing results in an ExceptionGroup.
    """

    __slots__ = ("left", "right")

    def __init__(self, left: AbstractAuthRule, right: AbstractAuthRule):
        self.left = left
        self.right = right

    async def authn(self, request: web.Request) -> list[tuple[AuthRule, IdT]]:
        """
        Try authentication branches in order, returning on first success.

        Returns:
            The result from the first successful branch

        Raises:
            ExceptionGroup: If all branches fail authentication
        """
        errors: list[AuthenticationError] = []
        for rule in (self.left, self.right):
            try:
                return await rule.authn(request)
            except* AuthenticationError as error:
                errors.extend(error.exceptions)

        raise ExceptionGroup("All authentication strategies failed", errors)

    async def authz(self, request: web.Request, identity: IdT, context):
        """
        Should never be called - OR logic is handled during authn phase.

        Raises:
            RuntimeError: Always, as this method should not be invoked
        """
        raise RuntimeError("authz should not be called from OrAuthRule object")

    def to_openapi_security(self, app: web.Application) -> list:
        return self.left.to_openapi_security(app) + self.right.to_openapi_security(app)

    def to_openapi_security_schemes(self, app) -> dict:
        return self.left.to_openapi_security_schemes(
            app
        ) | self.right.to_openapi_security_schemes(app)

    def __repr__(self):
        return f"<AuthRule ({self.left} | {self.right})>"


class AndAuthRule(AbstractAuthRule):
    """
    All of the security requirement objects must be satisfied.

    Attempts authentication with both branches. If either fails, propagates
    the exception immediately. Success requires both branches to authenticate.
    """

    __slots__ = ("left", "right")

    def __init__(self, left: AbstractAuthRule, right: AbstractAuthRule):
        self.left = left
        self.right = right

    async def authn(self, request: web.Request) -> list[tuple[AuthRule, IdT]]:
        """
        Authenticate with both branches, collecting all identities.

        Returns:
            Combined list of (auth_rule, identity) from both branches

        Raises:
            ExceptionGroup: If any branch fails authentication
        """
        identities = []
        for rule in (self.left, self.right):
            identities.extend(await rule.authn(request))

        return identities

    async def authz(self, request: web.Request, identity: IdT, context):
        """
        Should never be called - AND logic is handled by calling authz on all leaves.

        Raises:
            RuntimeError: Always, as this method should not be invoked
        """
        raise RuntimeError("authz should not be called from AndAuthRule object")

    def to_openapi_security(self, app: web.Application) -> list:
        return [
            left | right
            for left in self.left.to_openapi_security(app)
            for right in self.right.to_openapi_security(app)
        ]

    def to_openapi_security_schemes(self, app) -> dict:
        return self.left.to_openapi_security_schemes(
            app
        ) | self.right.to_openapi_security_schemes(app)

    def __repr__(self):
        return f"<AuthRule ({self.left} & {self.right})>"


class AuthSchemeRef(Generic[RuleT, IdT]):
    """
    A reference to a named security scheme.

    Used to create auth rules that bind to a specific SecurityScheme
    registered in the application.
    """

    name: str
    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"<AuthSchemeKey {self.name}>"

    def rule(self, rule: RuleT) -> AuthRule[RuleT, IdT]:
        return AuthRule(self, rule)


class SecurityScheme(ABC, Generic[IdT, RuleT]):

    type: ClassVar[str]
    parameter_name: ClassVar[str] = "Authorization"
    location: Literal["query", "cookie", "header"] = "header"

    def to_openapi(self) -> dict:
        """
        Return the OpenAPI security scheme definition for components/securitySchemes.
        """
        oas = {"type": self.type}
        if description := getdoc(self):
            oas["description"] = description
        return oas

    @abstractmethod
    async def authenticate(self, request: web.Request) -> IdT:
        """
        Authenticate the user from the request.

        Raise AuthenticationError if authentication fails.
        Return the user identity if successful.
        """

    @abstractmethod
    async def permits(
        self, request: web.Request, identity: IdT, rule: RuleT, context: dict[str, Any]
    ) -> bool:
        """
        Check if the authenticated identity has permission for the given rule.

        Args:
            request: The current HTTP request
            identity: The authenticated user identity
            rule: The permission rule to check
            context: Validated handler parameters (path, query, body)

        Returns:
            True if authorized, False otherwise.
        """

    @staticmethod
    def ref(name) -> AuthSchemeRef[RuleT, IdT]:
        """
        Create a reference to this security scheme for use in auth rules.

        Args:
            name: The name of the security scheme

        Returns:
            An AuthSchemeRef that can be used to create auth rules
        """
        return AuthSchemeRef(name)

    async def startup(self, app: web.Application) -> None:
        """
        Initialize the security scheme on application startup.

        Override this method in your subclass if needed.
        """

    async def cleanup(self, app: web.Application) -> None:
        """
        Clean up the security scheme on application shutdown.

        Override this method in your subclass if needed.
        This method is only called if startup succeeded.
        """

    def to_openapi_scopes(
        self, rule: RuleT  # pylint: disable=unused-argument
    ) -> list[str]:
        """
        Return the OpenAPI scopes or roles for a given rule.

        For OAuth2/OpenIdConnect schemes, return the list of required scopes.
        For other schemes, return a list of role names (optional).

        By default, returns an empty list.
        """
        return []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "location"):
            valid_locations = {"query", "cookie", "header"}
            if cls.location not in valid_locations:
                raise AttributeError(
                    f"Invalid location '{cls.location}' for {cls.__qualname__}. "
                    f"Must be one of {valid_locations}."
                )


AUTH_SCHEMES = web.AppKey("AUTH_SCHEMES", dict[AuthSchemeRef, SecurityScheme])
