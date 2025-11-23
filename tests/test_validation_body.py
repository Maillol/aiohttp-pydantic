from __future__ import annotations

from typing import Iterator, List, Optional

from aiohttp import web
from pydantic import BaseModel, RootModel

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.decorator import inject_params
import pytest


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


@inject_params
async def post(article: ArticleModel):
    return web.json_response(article.model_dump())


@inject_params
async def put(articles: ArticleModels):
    return web.json_response([article.model_dump() for article in articles])


def build_app_with_pydantic_view_1():
    app = web.Application()
    app.router.add_view("/article", ArticleView)
    return app


def build_app_with_decorated_handler_1():
    app = web.Application()
    app.router.add_post("/article", post)
    app.router.add_put("/article", put)
    return app


app_builders_1 = [build_app_with_pydantic_view_1, build_app_with_decorated_handler_1]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_an_article_without_required_field_should_return_an_error_message(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
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
        },
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_an_article_with_wrong_type_field_should_return_an_error_message(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
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


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_an_array_json_is_supported(app_builder, aiohttp_client):

    client = await aiohttp_client(app_builder())
    body = [{"name": "foo", "nb_page": 3}] * 2
    resp = await client.put("/article", json=body)
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == body


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_an_array_json_to_an_object_model_should_return_an_error(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
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


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_an_object_json_to_a_list_model_should_return_an_error(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
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


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_a_valid_article_should_return_the_parsed_type(
    app_builder, aiohttp_client
):

    client = await aiohttp_client(app_builder())
    resp = await client.post("/article", json={"name": "foo", "nb_page": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"name": "foo", "nb_page": 3}
