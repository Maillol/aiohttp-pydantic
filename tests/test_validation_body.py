from typing import Optional

import pytest
from aiohttp import web
from pydantic import BaseModel

from aiohttp_pydantic import PydanticView


class ArticleModel(BaseModel):
    name: str
    nb_page: Optional[int]


class ArticleView(PydanticView):
    async def post(self, article: ArticleModel):
        return web.json_response(article.dict())


async def test_post_an_article_without_required_field_should_return_an_error_message(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json={})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["name"],
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]


async def test_post_an_article_with_wrong_type_field_should_return_an_error_message(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json={"name": "foo", "nb_page": "foo"})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["nb_page"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        }
    ]


@pytest.mark.parametrize("request_body", [["foo"], "bar", 42])
async def test_post_json_with_non_object_top_structure_should_return_an_error_message(
    aiohttp_client, loop, request_body
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json=request_body)
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == {"error": "Malformed JSON"}


async def test_post_a_valid_article_should_return_the_parsed_type(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json={"name": "foo", "nb_page": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"name": "foo", "nb_page": 3}
