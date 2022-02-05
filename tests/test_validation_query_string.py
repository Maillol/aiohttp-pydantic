from __future__ import annotations

from typing import Optional, List
from pydantic import Field
from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.injectors import Group


class ArticleView(PydanticView):
    async def get(
        self,
        with_comments: bool,
        age: Optional[int] = None,
        nb_items: int = 7,
        tags: List[str] = Field(default_factory=list),
    ):
        return web.json_response(
            {
                "with_comments": with_comments,
                "age": age,
                "nb_items": nb_items,
                "tags": tags,
            }
        )


class Pagination(Group):
    page_num: int
    page_size: int = 20

    @property
    def num(self) -> int:
        return self.page_num

    @property
    def size(self) -> int:
        return self.page_size


class ArticleViewWithPaginationGroup(PydanticView):
    async def get(
        self,
        with_comments: bool,
        page: Pagination,
    ):
        return web.json_response(
            {
                "with_comments": with_comments,
                "page_num": page.num,
                "page_size": page.size,
            }
        )


async def test_get_article_without_required_qs_should_return_an_error_message(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get("/article")
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "query string",
            "loc": ["with_comments"],
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]


async def test_get_article_with_wrong_qs_type_should_return_an_error_message(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get("/article", params={"with_comments": "foo"})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "query string",
            "loc": ["with_comments"],
            "msg": "value could not be parsed to a boolean",
            "type": "type_error.bool",
        }
    ]


async def test_get_article_with_valid_qs_should_return_the_parsed_type(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)

    resp = await client.get("/article", params={"with_comments": "yes", "age": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {
        "with_comments": True,
        "age": 3,
        "nb_items": 7,
        "tags": [],
    }


async def test_get_article_with_valid_qs_and_omitted_optional_should_return_default_value(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)

    resp = await client.get("/article", params={"with_comments": "yes"})
    assert await resp.json() == {
        "with_comments": True,
        "age": None,
        "nb_items": 7,
        "tags": [],
    }
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_get_article_with_multiple_value_for_qs_age_must_failed(
    aiohttp_client, loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)

    resp = await client.get("/article", params={"age": ["2", "3"], "with_comments": 1})
    assert await resp.json() == [
        {
            "in": "query string",
            "loc": ["age"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"


async def test_get_article_with_multiple_value_of_tags(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)

    resp = await client.get(
        "/article", params={"age": 2, "with_comments": 1, "tags": ["aa", "bb"]}
    )
    assert await resp.json() == {
        "age": 2,
        "nb_items": 7,
        "tags": ["aa", "bb"],
        "with_comments": True,
    }
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_get_article_with_one_value_of_tags_must_be_a_list(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)

    resp = await client.get(
        "/article", params={"age": 2, "with_comments": 1, "tags": ["aa"]}
    )
    assert await resp.json() == {
        "age": 2,
        "nb_items": 7,
        "tags": ["aa"],
        "with_comments": True,
    }
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_get_article_without_required_field_page(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithPaginationGroup)

    client = await aiohttp_client(app)

    resp = await client.get("/article", params={"with_comments": 1})
    assert await resp.json() == [
        {
            "in": "query string",
            "loc": ["page_num"],
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"


async def test_get_article_with_page(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithPaginationGroup)

    client = await aiohttp_client(app)

    resp = await client.get("/article", params={"with_comments": 1, "page_num": 2})
    assert await resp.json() == {"page_num": 2, "page_size": 20, "with_comments": True}
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_get_article_with_page_and_page_size(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithPaginationGroup)

    client = await aiohttp_client(app)

    resp = await client.get(
        "/article", params={"with_comments": 1, "page_num": 1, "page_size": 10}
    )
    assert await resp.json() == {"page_num": 1, "page_size": 10, "with_comments": True}
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_get_article_with_page_and_wrong_page_size(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithPaginationGroup)

    client = await aiohttp_client(app)

    resp = await client.get(
        "/article", params={"with_comments": 1, "page_num": 1, "page_size": "large"}
    )
    assert await resp.json() == [
        {
            "in": "query string",
            "loc": ["page_size"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"
