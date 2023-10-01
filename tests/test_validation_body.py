from __future__ import annotations

from typing import Iterator, List, Optional

from aiohttp import web
from pydantic import BaseModel, RootModel

from aiohttp_pydantic import PydanticView


class ArticleModel(BaseModel):
    name: str
    nb_page: Optional[int]


class ArticleModels(RootModel):
    root: List[ArticleModel]

    def __iter__(self) -> Iterator[ArticleModel]:
        return iter(self.root)


class ArticleView(PydanticView):
    async def post(self, article: ArticleModel):
        return web.json_response(article.model_dump())

    async def put(self, articles: ArticleModels):
        return web.json_response([article.model_dump() for article in articles])


async def test_post_an_article_without_required_field_should_return_an_error_message(
    aiohttp_client, event_loop
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
            "input": {},
            "loc": ["name"],
            "msg": "Field required",
            "type": "missing",
        },
        {
            "in": "body",
            "input": {},
            "loc": ["nb_page"],
            "msg": "Field required",
            "type": "missing",
        }
    ]


async def test_post_an_article_with_wrong_type_field_should_return_an_error_message(
    aiohttp_client, event_loop
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
            "input": "foo",
            "loc": ["nb_page"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]


async def test_post_an_array_json_is_supported(aiohttp_client, event_loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    body = [{"name": "foo", "nb_page": 3}] * 2
    resp = await client.put("/article", json=body)
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == body


async def test_post_an_array_json_to_an_object_model_should_return_an_error(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json=[{"name": "foo", "nb_page": 3}])
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": "value is not a valid dict",
            "type": "type_error.dict",
        }
    ]


async def test_post_an_object_json_to_a_list_model_should_return_an_error(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    input_data = {"name": "foo", "nb_page": 3}
    resp = await client.put("/article", json=input_data)
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "body",
            "input": input_data,
            "loc": [],
            "msg": "Input should be a valid list",
            "type": "list_type",
        }
    ]


async def test_post_a_valid_article_should_return_the_parsed_type(aiohttp_client, event_loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json={"name": "foo", "nb_page": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"name": "foo", "nb_page": 3}
