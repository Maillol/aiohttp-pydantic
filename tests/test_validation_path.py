from aiohttp import web

from aiohttp_pydantic import PydanticView


class ArticleView(PydanticView):
    async def get(self, author_id: str, tag: str, date: int, /):
        return web.json_response({"path": [author_id, tag, date]})


async def test_get_article_without_required_qs_should_return_an_error_message(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article/{author_id}/tag/{tag}/before/{date}", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get("/article/1234/tag/music/before/1980")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"path": ["1234", "music", 1980]}
