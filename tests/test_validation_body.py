from typing import Iterator, List, Optional

from aiohttp import web
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


async def test_post_an_array_json_is_supported(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    body = [{"name": "foo", "nb_page": 3}] * 2
    resp = await client.put("/article", json=body)
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == body


async def test_post_an_array_json_to_an_object_model_should_return_an_error(
    aiohttp_client, loop
):
    """This test currently fails, using Pydantic version 1.8.

    Pydantic apparently tries some weird magic here.
    Making `nb_page` non-optional results in Pydantic rejecting the body, but it still
    fails with a different error than the expected (at least, by me)
    "Pet expected dict not list".

    >>> from typing import Optional

    >>> from pydantic import BaseModel


    >>> class Pet(BaseModel):
    ...    name: str
    ...    age: Optional[int]


    >>> Pet.parse_obj([{"name": "cat", "age": 2}]).__dict__
    {'name': 'age', 'age': None}
    >>> Pet.parse_obj([{"name": "cat", "foo": "bar"}]).__dict__
    {'name': 'foo', 'age': None}
    >>> Pet.parse_obj([{"name": "cat"}]).__dict__
    Traceback (most recent call last):
        ...
    pydantic.error_wrappers.ValidationError: 1 validation error for Pet
    __root__
      Pet expected dict not list (type=type_error)
    """
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json=[{"name": "foo", "nb_page": 3}])
    assert resp.status == 400
    assert resp.content_type == "application/json"


async def test_post_an_object_json_to_a_list_model_should_return_an_error(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.put("/article", json={"name": "foo", "nb_page": 3})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": "value is not a valid list",
            "type": "type_error.list",
        }
    ]


async def test_post_a_valid_article_should_return_the_parsed_type(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.post("/article", json={"name": "foo", "nb_page": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"name": "foo", "nb_page": 3}


if __name__ == "__main__":
    import doctest

    doctest.testmod()
