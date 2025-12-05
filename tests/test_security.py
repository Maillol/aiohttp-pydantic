from __future__ import annotations

from typing import Annotated

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.decorator import inject_params
import pytest

from aiohttp_pydantic.security import HTTPSecurityScheme, Permission


class Auth(HTTPSecurityScheme):
    """
    My Security Scheme.
    """
    scheme = "Bearer"
    bearer_format = "JWT"


class ArticleView(PydanticView):
    async def get(
        self,
        age: int | None = None,
        *,
        authorization: Annotated[Auth, Permission("read", "write")]
    ):
        return web.json_response({"age": age, "security_scheme": authorization.security_scheme()})


@inject_params
async def get(
    age: int | None = None,
    *,
    authorization: Annotated[Auth, Permission("read", "write")]
):
    return web.json_response({"age": age, "security_scheme": authorization.security_scheme()})


def build_app_with_pydantic_view_1():
    app = web.Application()
    app.router.add_view("/article", ArticleView)
    return app


def build_app_with_decorated_handler_1():
    app = web.Application()
    app.router.add_get("/article", get)
    return app


app_builders_1 = [build_app_with_pydantic_view_1, build_app_with_decorated_handler_1]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_required_qs_should_return_an_error_message(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
    resp = await client.get("/article")
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "query string",
            "input": {},
            "loc": ["with_comments"],
            "msg": "Field required",
            "type": "missing",
        }
    ]

@pytest.mark.parametrize(
    "app_builder", app_builders_1[1:], ids=["pydantic view", "decorated handler"][1:]
)
async def test_get_article_with_valid_authorization(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())

    resp = await client.get("/article",
                            params={"age": 3},
                            headers={"authorization": "Bearer 1234"})

    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {
        "age": 3,
        'security_scheme': {
            'description': 'My Security Scheme.',
            'in': 'header',
            'scheme': 'Bearer',
            'type': 'http'
        }
    }
