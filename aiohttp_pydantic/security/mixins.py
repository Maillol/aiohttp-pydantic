from  aiohttp import web
import jwt


class JWTMixin:

    async def identify(self, request: web.Request) -> str | None:
        header_identity = request.headers.get(AUTH_HEADER_NAME)

        if header_identity is None:
            return None

        if not header_identity.startswith(AUTH_SCHEME):
            raise ValueError("Invalid authorization scheme. "
                             + "Should be `{}<token>`".format(AUTH_SCHEME))

        token = header_identity.split(' ')[1].strip()

        identity = jwt.decode(token,
                              self.secret,
                              algorithms=[self.algorithm])
        return identity.get(self.key)  # type: ignore[no-any-return]


class BearerMixin:
    scheme = "Bearer"


class BasicMixin:

    scheme = "Basic"

    async def identify(self, request: web.Request) -> str | None:
        pass  # TODO: basic auth

