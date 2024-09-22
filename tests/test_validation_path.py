from __future__ import annotations

from aiohttp import web

from aiohttp_pydantic import PydanticView
import pytest
from aiohttp_pydantic.decorator import inject_params


class ArticleView(PydanticView):
    async def get(self, author_id: str, tag: str, date: int, /):
        return web.json_response({"path": [author_id, tag, date]})


@inject_params
async def get(author_id: str, tag: str, date: int, /):
    return web.json_response({"path": [author_id, tag, date]})


def build_app_with_pydantic_view():
    app = web.Application()
    app.router.add_view("/article/{author_id}/tag/{tag}/before/{date}", ArticleView)
    return app


def build_app_with_decorated_handler():
    app = web.Application()
    app.router.add_get("/article/{author_id}/tag/{tag}/before/{date}", get)
    return app


app_builders = [build_app_with_pydantic_view, build_app_with_decorated_handler]


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_correct_path_parameters_should_return_parameters_in_path(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())
    resp = await client.get("/article/1234/tag/music/before/1980")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"path": ["1234", "music", 1980]}


@pytest.mark.parametrize(
    "app_builder", app_builders, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_wrong_path_parameters_should_return_error(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())
    resp = await client.get("/article/1234/tag/music/before/now")
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "path",
            "input": "now",
            "loc": ["date"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
