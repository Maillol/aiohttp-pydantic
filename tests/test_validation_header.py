import json
from datetime import datetime
from enum import Enum

import pytest
from aiohttp import web

from aiohttp_pydantic import PydanticView, unpack_request
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


@unpack_request
async def get_article(request, *, signature_expired: datetime):
    return web.json_response(
        {"signature": signature_expired}, dumps=JSONEncoder().encode
    )


class FormatEnum(str, Enum):
    UTM = "UMT"
    MGRS = "MGRS"


class ViewWithEnumType(PydanticView):
    async def get(self, *, format: FormatEnum):
        return web.json_response({"format": format}, dumps=JSONEncoder().encode)


@unpack_request
async def get_article_with_enum_type(request, *, format: FormatEnum):
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


@unpack_request
async def get_article_with_signature_group(request, *, signature: Signature):
    return web.json_response(
        {"expired": signature.expired, "scope": signature.scope},
        dumps=JSONEncoder().encode,
    )


def application_maker_factory(use_view):
    def make_application():
        app = web.Application()
        if use_view:
            app.router.add_view("/article", ArticleView)
            app.router.add_view("/coord", ViewWithEnumType)
            app.router.add_view(
                "/article_with_signature_group", ArticleViewWithSignatureGroup
            )
        else:
            app.router.add_get("/article", get_article)
            app.router.add_get("/coord", get_article_with_enum_type)
            app.router.add_get(
                "/article_with_signature_group", get_article_with_signature_group
            )

        return app

    return make_application


@pytest.fixture(
    params=[
        application_maker_factory(use_view=True),
        application_maker_factory(use_view=False),
    ]
)
def make_app(request):
    return request.param


async def test_get_article_without_required_header_should_return_an_error_message(
    aiohttp_client, loop, make_app
):
    app = make_app()

    client = await aiohttp_client(app)
    resp = await client.get("/article", headers={})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "headers",
            "loc": ["signature_expired"],
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]


async def test_get_article_with_wrong_header_type_should_return_an_error_message(
    aiohttp_client, loop, make_app
):
    app = make_app()

    client = await aiohttp_client(app)
    resp = await client.get("/article", headers={"signature_expired": "foo"})
    assert resp.status == 400
    assert resp.content_type == "application/json"
    assert await resp.json() == [
        {
            "in": "headers",
            "loc": ["signature_expired"],
            "msg": "invalid datetime format",
            "type": "value_error.datetime",
        }
    ]


async def test_get_article_with_valid_header_should_return_the_parsed_type(
    aiohttp_client, loop, make_app
):
    app = make_app()

    client = await aiohttp_client(app)
    resp = await client.get(
        "/article", headers={"signature_expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


async def test_get_article_with_valid_header_containing_hyphen_should_be_returned(
    aiohttp_client, loop, make_app
):
    app = make_app()
    client = await aiohttp_client(app)
    resp = await client.get(
        "/article", headers={"Signature-Expired": "2020-10-04T18:01:00"}
    )
    assert resp.status == 200
    assert resp.content_type == "application/json"
    assert await resp.json() == {"signature": "2020-10-04T18:01:00"}


async def test_wrong_value_to_header_defined_with_str_enum(
    aiohttp_client, loop, make_app
):
    app = make_app()
    app.router.add_view("/coord", ViewWithEnumType)

    client = await aiohttp_client(app)
    resp = await client.get("/coord", headers={"format": "WGS84"})
    assert (
        await resp.json()
        == [
            {
                "ctx": {"enum_values": ["UMT", "MGRS"]},
                "in": "headers",
                "loc": ["format"],
                "msg": "value is not a valid enumeration member; permitted: 'UMT', 'MGRS'",
                "type": "type_error.enum",
            }
        ]
        != {"signature": "2020-10-04T18:01:00"}
    )
    assert resp.status == 400
    assert resp.content_type == "application/json"


async def test_correct_value_to_header_defined_with_str_enum(
    aiohttp_client, loop, make_app
):
    app = make_app()
    app.router.add_view("/coord", ViewWithEnumType)

    client = await aiohttp_client(app)
    resp = await client.get("/coord", headers={"format": "UMT"})
    assert await resp.json() == {"format": "UMT"}
    assert resp.status == 200
    assert resp.content_type == "application/json"


async def test_with_signature_group(aiohttp_client, loop, make_app):
    app = make_app()
    client = await aiohttp_client(app)
    resp = await client.get(
        "/article_with_signature_group",
        headers={
            "signature_expired": "2020-10-04T18:01:00",
            "signature.scope": "write",
        },
    )

    assert await resp.json() == {"expired": "2020-10-04T18:01:00", "scope": "read"}
    assert resp.status == 200
    assert resp.content_type == "application/json"
