from __future__ import annotations

from typing import Optional, List
from pydantic import Field
from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.injectors import Group
from aiohttp_pydantic.decorator import inject_params
import pytest


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


@inject_params
async def get(
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


def build_app_with_pydantic_view_1():
    app = web.Application()
    app.router.add_view("/article", ArticleView)
    return app


def build_app_with_decorated_handler_1():
    app = web.Application()
    app.router.add_get("/article", get)
    return app


app_builders_1 = [build_app_with_pydantic_view_1, build_app_with_decorated_handler_1]


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


@inject_params
async def get_with_pagination_group(
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


def build_app_with_pydantic_view_2():
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithPaginationGroup)
    return app


def build_app_with_decorated_handler_2():
    app = web.Application()
    app.router.add_get("/article", get_with_pagination_group)
    return app


app_builders_2 = [build_app_with_pydantic_view_2, build_app_with_decorated_handler_2]


class PaginationParamsDefaultNone(Group):
    page: Optional[None] = None
    page_size: Optional[int] = None


class ParamsDefaultNoneView(PydanticView):
    async def get(self, pagination: PaginationParamsDefaultNone):
        return web.json_response(
            {"page": pagination.page, "page_size": pagination.page_size}
        )


@inject_params
async def get_params_default_none(pagination: PaginationParamsDefaultNone):
    return web.json_response(
        {"page": pagination.page, "page_size": pagination.page_size}
    )


def build_app_with_pydantic_view_params_default_none():
    app = web.Application()
    app.router.add_view("/bug56", ParamsDefaultNoneView)
    return app


def build_app_with_decorated_handler_params_default_none():
    app = web.Application()
    app.router.add_get("/bug56", get_params_default_none)
    return app


app_builders_3 = [
    build_app_with_pydantic_view_params_default_none,
    build_app_with_decorated_handler_params_default_none,
]


@pytest.mark.parametrize(
    "app_builder", app_builders_3, ids=["pydantic view", "decorated handler"]
)
async def test_group_with_field_type_is_union_none_int(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())
    resp = await client.get("/bug56")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"page": None, "page_size": None}


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_required_qs_should_return_an_error_message(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())
    resp = await client.get("/article")
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "query string",
            "input": {},
            "loc": ["with_comments"],
            "msg": "Field required",
            "type": "missing",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_wrong_qs_type_should_return_an_error_message(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())
    resp = await client.get("/article", params={"with_comments": "foo"})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "query string",
            "input": "foo",
            "loc": ["with_comments"],
            "msg": "Input should be a valid boolean, unable to interpret input",
            "type": "bool_parsing",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_qs_should_return_the_parsed_type(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"with_comments": "yes", "age": 3})
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {
        "with_comments": True,
        "age": 3,
        "nb_items": 7,
        "tags": [],
    }


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_qs_and_omitted_optional_should_return_default_value(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"with_comments": "yes"})
    assert await resp.json() == {
        "with_comments": True,
        "age": None,
        "nb_items": 7,
        "tags": [],
    }
    assert resp.status == 200
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_multiple_value_for_qs_age_must_failed(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"age": ["2", "3"], "with_comments": 1})
    assert await resp.json() == [
        {
            "in": "query string",
            "input": ["2", "3"],
            "loc": ["age"],
            "msg": "Input should be a valid integer",
            "type": "int_type",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_multiple_value_of_tags(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())

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


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_one_value_of_tags_must_be_a_list(
    app_builder, aiohttp_client, event_loop
):

    client = await aiohttp_client(app_builder())

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


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_required_field_page(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"with_comments": 1})
    assert await resp.json() == [
        {
            "in": "query string",
            "input": {"with_comments": "1"},
            "loc": ["page_num"],
            "msg": "Field required",
            "type": "missing",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_page(app_builder, aiohttp_client, event_loop):
    client = await aiohttp_client(app_builder())

    resp = await client.get("/article", params={"with_comments": 1, "page_num": 2})
    assert await resp.json() == {"page_num": 2, "page_size": 20, "with_comments": True}
    assert resp.status == 200
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_page_and_page_size(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article", params={"with_comments": 1, "page_num": 1, "page_size": 10}
    )
    assert await resp.json() == {"page_num": 1, "page_size": 10, "with_comments": True}
    assert resp.status == 200
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_page_and_wrong_page_size(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())

    resp = await client.get(
        "/article", params={"with_comments": 1, "page_num": 1, "page_size": "large"}
    )
    assert await resp.json() == [
        {
            "in": "query string",
            "input": "large",
            "loc": ["page_size"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert resp.status == 400
    assert resp.content_type == "application/json"
