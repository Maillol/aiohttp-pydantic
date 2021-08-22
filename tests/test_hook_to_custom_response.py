from typing import Iterator, List, Optional

from aiohttp import web
from aiohttp.web_response import json_response
from pydantic import BaseModel

from aiohttp_pydantic import PydanticView


class ArticleModel(BaseModel):
    name: str
    nb_page: Optional[int]


class ArticleModels(BaseModel):
    __root__: List[ArticleModel]

    def __iter__(self) -> Iterator[ArticleModel]:
        return iter(self.__root__)


class ArticleView(PydanticView):
    async def post(self, article: ArticleModel):
        return web.json_response(article.dict())

    async def put(self, articles: ArticleModels):
        return web.json_response([article.dict() for article in articles])

    async def on_validation_error(self, exception, context):
        errors = exception.errors()
        for error in errors:
            error["in"] = context
            error["custom"] = "custom"
        return json_response(data=errors, status=400)


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
            "custom": "custom",
            "type": "type_error.integer",
        }
    ]
