from __future__ import annotations

from aiohttp import web

from aiohttp_pydantic import PydanticView


class ArticleView(PydanticView):
    async def get(self, author_id: str, tag: str, date: int, /):
        return web.json_response({"path": [author_id, tag, date]})


async def test_get_article_with_correct_path_parameters_should_return_parameters_in_path(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article/{author_id}/tag/{tag}/before/{date}", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get("/article/1234/tag/music/before/1980")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"path": ["1234", "music", 1980]}


async def test_get_article_with_wrong_path_parameters_should_return_error(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article/{author_id}/tag/{tag}/before/{date}", ArticleView)

    client = await aiohttp_client(app)
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
