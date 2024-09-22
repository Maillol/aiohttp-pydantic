from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from unittest.mock import ANY

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.injectors import Group
from packaging.version import Version
import pydantic_core
from aiohttp_pydantic.decorator import inject_params
import pytest


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


class ArticleView(PydanticView):
    async def get(self, *, signature_expired: datetime):
        return web.json_response(
            {"signature": signature_expired}, dumps=JSONEncoder().encode
        )


@inject_params
async def get(*, signature_expired: datetime):
    return web.json_response(
        {"signature": signature_expired}, dumps=JSONEncoder().encode
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


class FormatEnum(str, Enum):
    UTM = "UMT"
    MGRS = "MGRS"


class ViewWithEnumType(PydanticView):
    async def get(self, *, format: FormatEnum):
        return web.json_response({"format": format}, dumps=JSONEncoder().encode)


@inject_params()
async def get_with_enum_type(*, format: FormatEnum):
    return web.json_response({"format": format}, dumps=JSONEncoder().encode)


def build_app_with_pydantic_view_2():
    app = web.Application()
    app.router.add_view("/coord", ViewWithEnumType)
    return app


def build_app_with_decorated_handler_2():
    app = web.Application()
    app.router.add_get("/coord", get_with_enum_type)
    return app


app_builders_2 = [build_app_with_pydantic_view_2, build_app_with_decorated_handler_2]


class Signature(Group):
    signature_expired: datetime
    signature_scope: str = "read"

    @property
    def expired(self) -> datetime:
        return self.signature_expired

    @property
    def scope(self) -> str:
        return self.signature_scope


class ArticleViewWithSignatureGroup(PydanticView):
    async def get(
        self,
        *,
        signature: Signature,
    ):
        return web.json_response(
            {"expired": signature.expired, "scope": signature.scope},
            dumps=JSONEncoder().encode,
        )


@inject_params
async def get_with_signature(
    *,
    signature: Signature,
):
    return web.json_response(
        {"expired": signature.expired, "scope": signature.scope},
        dumps=JSONEncoder().encode,
    )


def build_app_with_pydantic_view_3():
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithSignatureGroup)
    return app


def build_app_with_decorated_handler_3():
    app = web.Application()
    app.router.add_get("/article", get_with_signature)
    return app


app_builders_3 = [build_app_with_pydantic_view_3, build_app_with_decorated_handler_3]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_without_required_header_should_return_an_error_message(
    app_builder, aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app_builder())
    resp = await client.get("/article", headers={})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "headers",
            "input": ANY,
            "loc": ["signature_expired"],
            "msg": "Field required",
            "type": "missing",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_wrong_header_type_should_return_an_error_message(
    app_builder, aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app_builder())
    resp = await client.get("/article", headers={"signature_expired": "foo"})
    if Version(pydantic_core.__version__) >= Version("2.15.0"):
        expected_type = "datetime_from_date_parsing"
        expected_msg = "Input should be a valid datetime or date, input is too short"
    else:
        expected_type = "datetime_parsing"
        expected_msg = "Input should be a valid datetime, input is too short"

    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "headers",
            "input": "foo",
            "ctx": {"error": "input is too short"},
            "loc": ["signature_expired"],
            "msg": expected_msg,
            "type": expected_type,
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_header_should_return_the_parsed_type(
    app_builder, aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app_builder())
    resp = await client.get(
        "/article", headers={"signature_expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_get_article_with_valid_header_containing_hyphen_should_be_returned(
    app_builder, aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app_builder())
    resp = await client.get(
        "/article", headers={"Signature-Expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_wrong_value_to_header_defined_with_str_enum(
    app_builder, aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/coord", ViewWithEnumType)

    client = await aiohttp_client(app_builder())
    resp = await client.get("/coord", headers={"format": "WGS84"})
    assert (
        await resp.json()
        == [
            {
                "ctx": {"expected": "'UMT' or 'MGRS'"},
                "in": "headers",
                "input": "WGS84",
                "loc": ["format"],
                "msg": "Input should be 'UMT' or 'MGRS'",
                "type": "enum",
            }
        ]
        != {"signature": "2020-10-04T18:01:00"}
    )
    assert resp.status == 400
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_2, ids=["pydantic view", "decorated handler"]
)
async def test_correct_value_to_header_defined_with_str_enum(
    app_builder, aiohttp_client, event_loop
):
    client = await aiohttp_client(app_builder())
    resp = await client.get("/coord", headers={"format": "UMT"})
    assert await resp.json() == {"format": "UMT"}
    assert resp.status == 200
    assert resp.content_type == "application/json"


@pytest.mark.parametrize(
    "app_builder", app_builders_3, ids=["pydantic view", "decorated handler"]
)
async def test_with_signature_group(app_builder, aiohttp_client, event_loop):
    client = await aiohttp_client(app_builder())
    resp = await client.get(
        "/article",
        headers={
            "signature_expired": "2020-10-04T18:01:00",
            "signature.scope": "write",
        },
    )

    assert await resp.json() == {"expired": "2020-10-04T18:01:00", "scope": "read"}
    assert resp.status == 200
    assert resp.content_type == "application/json"
