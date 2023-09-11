from __future__ import annotations

from typing import Iterator, List, Optional

from aiohttp import web
from aiohttp.web_response import json_response
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

    async def on_validation_error(self, exception, context):
        errors = exception.errors(include_url=False)
        for error in errors:
            error["in"] = context
            error["custom"] = "custom"
        return json_response(data=errors, status=400)


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
            "custom": "custom",
            "type": "int_parsing",
        }
    ]
