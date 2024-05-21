from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from unittest.mock import ANY

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.injectors import Group


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


class FormatEnum(str, Enum):
    UTM = "UMT"
    MGRS = "MGRS"


class ViewWithEnumType(PydanticView):
    async def get(self, *, format: FormatEnum):
        return web.json_response({"format": format}, dumps=JSONEncoder().encode)


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


async def test_get_article_without_required_header_should_return_an_error_message(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
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


async def test_get_article_with_wrong_header_type_should_return_an_error_message(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get("/article", headers={"signature_expired": "foo"})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "headers",
            "input": "foo",
            "ctx": {"error": "input is too short"},
            "loc": ["signature_expired"],
            "msg": "Input should be a valid datetime or date, input is too short",
            "type": "datetime_from_date_parsing",
        }
    ]


async def test_get_article_with_valid_header_should_return_the_parsed_type(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get(
        "/article", headers={"signature_expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


async def test_get_article_with_valid_header_containing_hyphen_should_be_returned(
    aiohttp_client, event_loop
):
    app = web.Application()
    app.router.add_view("/article", ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get(
        "/article", headers={"Signature-Expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


async def test_wrong_value_to_header_defined_with_str_enum(aiohttp_client, event_loop):
    app = web.Application()
    app.router.add_view("/coord", ViewWithEnumType)

    client = await aiohttp_client(app)
    resp = await client.get("/coord", headers={"format": "WGS84"})
    assert (
        await resp.json()
        == [
            {
                "ctx": {"expected": "'UMT' or 'MGRS'"},
                "in": "headers",
                'input': 'WGS84',
                "loc": ["format"],
                "msg": "Input should be 'UMT' or 'MGRS'",
                "type": "enum",
            }
        ]
        != {"signature": "2020-10-04T18:01:00"}
    )
    assert resp.status == 400
    assert resp.content_type == "application/json"


async def test_correct_value_to_header_defined_with_str_enum(aiohttp_client, event_loop):
    app = web.Application()
    app.router.add_view("/coord", ViewWithEnumType)

    client = await aiohttp_client(app)
    resp = await client.get("/coord", headers={"format": "UMT"})
    assert await resp.json() == {"format": "UMT"}
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_with_signature_group(aiohttp_client, event_loop):
    app = web.Application()
    app.router.add_view("/article", ArticleViewWithSignatureGroup)

    client = await aiohttp_client(app)
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
