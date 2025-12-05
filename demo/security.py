from __future__ import annotations

from datetime import datetime
from typing import TypedDict, Literal

import jwt
from aiohttp import web
from jwt import PyJWTError

from aiohttp_pydantic.security.auth_scheme import HTTPSecurityScheme
from aiohttp_pydantic.security.exceptions import AuthenticationError
from demo.model import NotFound

from .keys import CURRENT_USER, MODEL


class JWTPayload(TypedDict):
    """
    Structure of a JWT token.

    Attributes:
        sub: User ID (subject)
        iat: Creation timestamp (issued at)
        admin: True if the user has admin privileges
    """

    sub: str
    iat: int
    admin: bool


class JWTAuth(HTTPSecurityScheme):
    """
    JSON Web Token Authentication

    This authentication scheme:
    1. Extracts the token from the "Authorization: Bearer <token>" header
    2. Verifies its signature using the JWT secret
    3. Loads the user from the database
    4. Handles permissions according to rules ("user", "admin", "owner")
    """

    scheme = "Bearer"
    bearer_format = "JWT"

    def __init__(self, jwt_secret):
        self._jwt_secret = jwt_secret

    async def authenticate(self, request: web.Request) -> JWTPayload:
        """
        Validate the JWT token and load the user.

        Steps:
        1. Extract the token from the header (via extract_credentials)
        2. Decode and verify the JWT signature
        3. Load the user from the database
        4. Store the user in request[CURRENT_USER] for later use

        Returns:
            The decoded JWT payload (used as the "identity")

        Raises:
            AuthenticationError: If the token is invalid, expired, or the user no longer exists
        """

        # extract_credentials() comes from HTTPSecurityScheme
        # It validates the "Bearer <token>" format and extracts the token
        token = self.extract_credentials(request)
        try:
            # Decode and verify the JWT signature
            payload = jwt.decode(token, self._jwt_secret, algorithms="HS256")

            # Extract the user_id from the payload
            try:
                user_id = int(payload["sub"])
            except ValueError:
                raise AuthenticationError("Value Subject Error")

            # Load the user from the database
            # This ensures the user still exists
            try:
                current_user = request.app[MODEL].find_user(user_id)
            except NotFound:
                raise AuthenticationError("User no longer exists")
            else:
                # Store the user for use in handlers
                # Useful to avoid reloading the user multiple times
                request[CURRENT_USER] = current_user

        except PyJWTError as error:
            # Invalid, expired, or incorrectly signed token
            raise AuthenticationError(str(error)) from error

        # Return the payload as the "identity"
        # It will be passed to permits() for permission checks
        return payload

    async def permits(
        self,
        request,
        identity: JWTPayload,
        rule: Literal["user", "admin", "owner"],
        context: dict,
    ) -> bool:
        """
        Check whether the user has the required permission.

        Args:
            request: The current HTTP request
            identity: The JWT payload (returned by authenticate)
            rule: The permission rule to check ("user", "admin", "owner")
            context: Validated handler parameters (e.g. {"id": 123} for /pets/{id})

        Returns:
            True if authorized, False otherwise

        """

        # "user" rule: any authenticated user can access
        if rule == "user":
            return True

        # "admin" rule: check the "admin" claim in the JWT
        if rule == "admin":
            return identity.get("admin", False)

        # "owner" rule: check that the user owns the resource
        if rule == "owner":
            if current_user_id := identity.get("sub"):
                pet = request.app[MODEL].find_pet(context["id"])
                return pet.owner_id == int(current_user_id)

        return False

    def create_token(self, sub: int, admin: bool):
        """
        Utility method to create a JWT token (used during login).

        Args:
            sub: User ID
            admin: True if the user is an admin

        Returns:
            The encoded JWT token
        """
        return jwt.encode(
            {
                "sub": str(sub),
                "admin": admin,
                "iat": int(datetime.now().timestamp()),
            },
            self._jwt_secret,
            algorithm="HS256",
        )


# Create a reference to the scheme to use it in @auth() decorators
USER_AUTH = JWTAuth.ref("USER_AUTH")
