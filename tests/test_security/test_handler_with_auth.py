from __future__ import annotations

from aiohttp import web
from jwt import PyJWTError
import jwt

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.decorator import inject_params, auth
import pytest

from aiohttp_pydantic.security.auth_scheme import (
    HTTPSecurityScheme,
    APIKeySecurityScheme,
)

from aiohttp_pydantic.security.exceptions import AuthenticationError, AuthorizationError

from datetime import datetime, timedelta
from aiohttp_pydantic.security import setup

JWT_SECRET = "a-string-secret-at-least-256-bits-long"
JWT_TOKEN = jwt.encode(
    {
        "sub": "1234567890",
        "name": "John Doe",
        "admin": True,
        "iat": int(datetime.now().timestamp()),
    },
    JWT_SECRET,
    algorithm="HS256",
)

EXPIRED_JWT_TOKEN = jwt.encode(
    {
        "sub": "1234567890",
        "name": "John Doe",
        "admin": False,
        "exp": int((datetime.now() - timedelta(days=1)).timestamp()),
    },
    JWT_SECRET,
    algorithm="HS256",
)

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
        # Check if user has admin role for "admin" rule
        if rule == "admin":
            return identity.get("admin", False)
        return True


class APIKeyAuth(APIKeySecurityScheme):

    async def authenticate(self, request: web.Request) -> str:
        creds = self.extract_credentials(request)
        return creds

    async def permits(self, request, identity: str, rule: int, context: dict) -> bool:
        # Rule is permission level (1=read, 2=write, 3=admin)
        # API key format: "key-level-X" where X is the permission level
        if identity.startswith("key-level-"):
            try:
                level = int(identity.split("-")[-1])
                return level >= rule
            except (ValueError, IndexError):
                return False
        return False


USER_AUTH = JWTAuth.ref("USER_AUTH")
MACHINE_AUTH = APIKeyAuth.ref("MACHINE_AUTH")


class ArticleCollectionView(PydanticView):

    @auth(MACHINE_AUTH.rule(2) | USER_AUTH.rule("read"))
    async def get(
            self,
            age: int | None = None,
    ):
        return web.json_response({"age": age, "sub": self.request.get(JWT_SUB)})

class ArticleView(PydanticView):

    @auth(USER_AUTH.rule("admin"))
    async def delete(self, article_id: int, /):
        return web.json_response({"deleted": article_id})


class ProtectedView(PydanticView):

    @auth(USER_AUTH.rule("read") & MACHINE_AUTH.rule(1))
    async def get(self):
        return web.json_response({"status": "ok"})


@inject_params.and_request.with_auth(MACHINE_AUTH.rule(2) | USER_AUTH.rule("read"))
async def get_article(
        request,
        age: int | None = None,
):
    return web.json_response({"age": age, "sub": request.get(JWT_SUB)})


@inject_params.and_request.with_auth(USER_AUTH.rule("admin"))
async def delete_article(request, article_id: int, /):
    return web.json_response({"deleted": article_id})


@inject_params.and_request.with_auth(USER_AUTH.rule("read") & MACHINE_AUTH.rule(1))
async def protected_resource(request):
    return web.json_response({"status": "ok"})


def build_app_with_pydantic_view():
    app = web.Application()
    app.router.add_view("/article", ArticleCollectionView)
    app.router.add_view("/article/{article_id}", ArticleView)
    app.router.add_view("/protected", ProtectedView)
    setup(
        app,
        {
            USER_AUTH: JWTAuth(
                jwt_secret=JWT_SECRET, jwt_algorithm="HS256", jwt_key="sub"
            ),
            MACHINE_AUTH: APIKeyAuth(),
        },
    )
    return app


def build_app_with_decorated_handler():
    app = web.Application()
    app.router.add_get("/article", get_article)
    app.router.add_delete("/article/{article_id}", delete_article)
    app.router.add_get("/protected", protected_resource)
    setup(
        app,
        {
            USER_AUTH: JWTAuth(
                jwt_secret=JWT_SECRET, jwt_algorithm="HS256", jwt_key="sub"
            ),
            MACHINE_AUTH: APIKeyAuth(),
        },
    )
    return app


app_builders = [build_app_with_pydantic_view, build_app_with_decorated_handler]


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_jwt(app_builder, aiohttp_client):
    """Test successful authentication with valid JWT token"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 3},
        headers={"authorization": f"Bearer {JWT_TOKEN}"}
    )

    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"age": 3, "sub": "1234567890"}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_api_key(app_builder, aiohttp_client):
    """Test successful authentication with valid API key"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 5},
        headers={"X-Api-Key": "key-level-3"}  # Level 3 >= rule level 2
    )

    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"age": 5, "sub": None}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_query_param(app_builder, aiohttp_client):
    """Test that optional parameters work correctly"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        headers={"authorization": f"Bearer {JWT_TOKEN}"}
    )

    assert resp.status == 200
    assert await resp.json() == {"age": None, "sub": "1234567890"}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_credentials(app_builder, aiohttp_client):
    """Test that missing credentials result in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"age": 3})

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_malformed_auth_header(app_builder, aiohttp_client):
    """Test that malformed authorization header results in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 3},
        headers={"authorization": "InvalidFormat"}
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_wrong_scheme(app_builder, aiohttp_client):
    """Test that wrong authentication scheme results in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 3},
        headers={"authorization": f"Basic {JWT_TOKEN}"}  # Should be Bearer
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_expired_jwt(app_builder, aiohttp_client):
    """Test that expired JWT token results in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 3},
        headers={"authorization": f"Bearer {EXPIRED_JWT_TOKEN}"}
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_invalid_jwt_signature(app_builder, aiohttp_client):
    """Test that JWT with invalid signature results in 401"""
    client = await aiohttp_client(app_builder())

    bad_token = jwt.encode(
        {"sub": "hacker", "name": "Evil", "admin": True},
        "wrong-secret",
        algorithm="HS256",
    )

    resp = await client.get(
        "/article",
        params={"age": 3},
        headers={"authorization": f"Bearer {bad_token}"}
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_delete_article_without_admin_role(app_builder, aiohttp_client):
    """Test that non-admin user cannot delete (403)"""
    client = await aiohttp_client(app_builder())

    # Create token without admin role
    non_admin_token = jwt.encode(
        {
            "sub": "regular_user",
            "name": "Regular User",
            "admin": False,
            "iat": int(datetime.now().timestamp()),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    resp = await client.delete(
        "/article/123",
        headers={"authorization": f"Bearer {non_admin_token}"}
    )

    assert resp.status == 403


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_delete_article_with_admin_role(app_builder, aiohttp_client):
    """Test that admin user can delete"""
    client = await aiohttp_client(app_builder())

    resp = await client.delete(
        "/article/123",
        headers={"authorization": f"Bearer {JWT_TOKEN}"}  # Has admin: true
    )

    assert resp.status == 200
    assert await resp.json() == {"deleted": 123}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_insufficient_api_key_level(app_builder, aiohttp_client):
    """Test that API key with insufficient permission level results in 403"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": 5},
        headers={"X-Api-Key": "key-level-1"}  # Level 1 < required level 2
    )

    assert resp.status == 403


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_protected_resource_with_both_credentials(app_builder, aiohttp_client):
    """Test AND operator: both credentials required"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/protected",
        headers={
            "authorization": f"Bearer {JWT_TOKEN}",
            "X-Api-Key": "key-level-1"
        }
    )

    assert resp.status == 200
    assert await resp.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_protected_resource_with_only_jwt(app_builder, aiohttp_client):
    """Test AND operator: missing one credential results in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/protected",
        headers={"authorization": f"Bearer {JWT_TOKEN}"}
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_protected_resource_with_only_api_key(app_builder, aiohttp_client):
    """Test AND operator: missing one credential results in 401"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/protected",
        headers={"X-Api-Key": "key-level-1"}
    )

    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_invalid_parameter_without_auth_returns_401(app_builder, aiohttp_client):
    """Test that 401 is returned before 400 (auth before validation)"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": "not-an-int"}  # Invalid parameter
        # No auth header
    )

    # Should get 401 (unauthorized) not 400 (bad request)
    assert resp.status == 401


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_invalid_parameter_with_auth_returns_400(app_builder, aiohttp_client):
    """Test that validation error returns 400 after successful auth"""
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article",
        params={"age": "not-an-int"},
        headers={"authorization": f"Bearer {JWT_TOKEN}"}
    )

    # Should get 400 (bad request) after successful auth
    assert resp.status == 400