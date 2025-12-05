from enum import Enum
from typing import Any
from aiohttp_security import JWTIdentityPolicy, AbstractAuthorizationPolicy

from aiohttp_pydantic.security import HTTPSecurityScheme


class AuthorizationPolicy(AbstractAuthorizationPolicy):

    async def permits(self, identity: str | None,  # type: ignore[misc]
                      permission: str | Enum, context: Any = None) -> bool:
        """Check user permissions.

        Return True if the identity is allowed the permission in the
        current context, else return False.
        """
        return True

    async def authorized_userid(self, identity: str) -> str | None:
        """Retrieve authorized user id.

        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        return identity


class HTTPAuth(HTTPSecurityScheme):
    scheme = "Bearer"


__all__ = ["JWTIdentityPolicy", "HTTPAuth", "AuthorizationPolicy"]
