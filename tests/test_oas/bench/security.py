from __future__ import annotations

from aiohttp import web
from jwt import PyJWTError
import jwt
from aiohttp_pydantic.security.auth_scheme import (
    HTTPSecurityScheme,
    APIKeySecurityScheme,
)
from aiohttp_pydantic.security.exceptions import AuthenticationError

JWT_SUB = "JWT_SUB"


class JWTAuth(HTTPSecurityScheme):
    """
    My Security Scheme.
    """

    scheme = "Bearer"
    bearer_format = "JWT"

    def __init__(self, jwt_secret, jwt_algorithm, jwt_key):
        super().__init__()
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._jwt_key = jwt_key

    async def authenticate(self, request: web.Request) -> dict:
        token = self.extract_credentials(request)
        try:
            payload = jwt.decode(
                token, self._jwt_secret, algorithms=self._jwt_algorithm
            )

        except PyJWTError as error:
            raise AuthenticationError(str(error)) from error

        request[JWT_SUB] = payload["sub"]
        return payload

    async def permits(self, request, identity: dict, rule: str, context: dict) -> bool:
        return True


class APIKeyAuth(APIKeySecurityScheme):

    async def authenticate(self, request: web.Request) -> int:
        return request.headers.get(self.parameter_name)

    async def permits(self, request, identity: int, rule: int, context: dict) -> bool:
        return True


USER_AUTH = JWTAuth.ref("USER_AUTH")
MACHINE_AUTH = APIKeyAuth.ref("MACHINE_AUTH")
