import pytest
from aiohttp import web

from aiohttp_pydantic import PydanticView, unpack_request


class ArticleView(PydanticView):
    async def get(self, author_id: str, tag: str, date: int, /):
        return web.json_response({"path": [author_id, tag, date]})


@unpack_request
async def get_article(request, author_id: str, tag: str, date: int, /):
    return web.json_response({"path": [author_id, tag, date]})


def application_maker_factory(use_view):
    def make_application():
        app = web.Application()
        if use_view:
            app.router.add_view(
                "/article/{author_id}/tag/{tag}/before/{date}", ArticleView
            )
        else:
            app.router.add_get(
                "/article/{author_id}/tag/{tag}/before/{date}", get_article
            )

        return app

    return make_application


@pytest.fixture(
    params=[
        application_maker_factory(use_view=True),
        application_maker_factory(use_view=False),
    ]
)
def make_app(request):
    return request.param


async def test_get_article_with_correct_path_parameters_should_return_parameters_in_path(
    aiohttp_client, loop, make_app
):
    app = make_app()

    client = await aiohttp_client(app)
    resp = await client.get("/article/1234/tag/music/before/1980")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"path": ["1234", "music", 1980]}


async def test_get_article_with_wrong_path_parameters_should_return_error(
    aiohttp_client, loop, make_app
):
    app = make_app()

    client = await aiohttp_client(app)
    resp = await client.get("/article/1234/tag/music/before/now")
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "path",
            "loc": ["date"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        }
    ]
