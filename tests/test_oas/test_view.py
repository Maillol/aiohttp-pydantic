from __future__ import annotations

from typing import List

from aiohttp import web
import openapi_spec_validator
import pytest

from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.injectors import Group
from aiohttp_pydantic.oas.typing import r200
import aiohttp_pydantic.oas.view
from .bench.model import Pet
from .bench import (
    decorated_handler,
    pydantic_view,
    decorated_handler_with_request,
    view,
)


async def ensure_content_durability(client):
    """
    Reload the page 2 times to ensure that content is always the same
    note: pydantic can return a cached dict, if a view updates the dict the
    output will be incoherent
    """
    response_1 = await client.get("/oas/spec")
    assert response_1.status == 200
    assert response_1.content_type == "application/json"
    content_1 = await response_1.json()

    response_2 = await client.get("/oas/spec")
    content_2 = await response_2.json()
    assert content_1 == content_2
    return content_2


def build_app_and_generate_oas_factory(app_builder):
    async def build_app_and_generate_oas(aiohttp_client) -> web.Application:
        app = app_builder()
        open_api_spec = await ensure_content_durability(await aiohttp_client(app))
        openapi_spec_validator.validate(open_api_spec)
        return open_api_spec

    return build_app_and_generate_oas


generate_oas_spec = [
    build_app_and_generate_oas_factory(view.build_app),
    build_app_and_generate_oas_factory(pydantic_view.build_app),
    build_app_and_generate_oas_factory(decorated_handler.build_app),
    build_app_and_generate_oas_factory(decorated_handler_with_request.build_app),
]


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_generated_oas_should_have_components_schemas(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert generated_oas["components"]["schemas"] == {
        "Color": {
            "enum": ["red", "green", "pink"],
            "title": "Color",
            "type": "string",
        },
        "Pet": {
            "properties": {
                "id": {"title": "Id", "type": "integer"},
                "name": {"title": "Name", "type": "string"},
                "toys": {
                    "items": {"$ref": "#/components/schemas/Toy"},
                    "title": "Toys",
                    "type": "array",
                },
            },
            "required": ["id", "name", "toys"],
            "title": "Pet",
            "type": "object",
        },
        "Toy": {
            "properties": {
                "brand": {"nullable": True, "title": "Brand", "type": "string"},
                "color": {"$ref": "#/components/schemas/Color"},
                "name": {"title": "Name", "type": "string"},
            },
            "required": ["name", "color"],
            "title": "Toy",
            "type": "object",
        },
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_generated_oas_should_have_pets_paths(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert "/pets" in generated_oas["paths"]


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_pets_route_should_have_get_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)

    assert generated_oas["paths"]["/pets"]["get"] == {
        "description": "Get a list of pets",
        "tags": ["pet"],
        "security": [
            {
                "APIKeyHeader": [],
            },
        ],
        "parameters": [
            {
                "in": "query",
                "name": "format",
                "required": True,
                "schema": {"title": "format", "type": "string"},
                "description": "description for format",
            },
            {
                "in": "query",
                "name": "name",
                "required": False,
                "schema": {"type": "string", "title": "name", "nullable": True},
            },
            {
                "in": "header",
                "name": "promo",
                "required": False,
                "schema": {
                    "nullable": True,
                    # "format": "uuid",
                    "type": "string",
                    "title": "promo",
                },
                "description": "description for promo",
            },
        ],
        "responses": {
            "200": {
                "description": "Successful operation",
                "content": {
                    "application/json": {
                        "schema": {
                            "items": {"$ref": "#/components/schemas/Pet"},
                            "type": "array",
                        }
                    }
                },
            }
        },
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_pets_route_should_have_post_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert generated_oas["paths"]["/pets"]["post"] == {
        "description": "Create a Pet",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {'$ref': '#/components/schemas/Pet'}
                }
            }
        },
        "responses": {
            "201": {
                "description": "",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                },
            }
        },
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_generated_oas_should_have_pets_id_paths(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert "/pets/{id}" in generated_oas["paths"]


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_pets_id_route_should_have_delete_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert generated_oas["paths"]["/pets/{id}"]["delete"] == {
        "description": "",
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"title": "id", "type": "integer"},
            }
        ],
        "responses": {"204": {"content": {}, "description": "Empty but OK"}},
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_pets_id_route_should_have_get_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    now_desc = {"enum": ["now"], "type": "string"}

    assert generated_oas["paths"]["/pets/{id}"]["get"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"title": "id", "type": "integer"},
            },
            {
                "in": "query",
                "name": "size",
                "required": True,
                "schema": {
                    "anyOf": [
                        {"type": "integer"},
                        {"enum": ["x", "l", "s"], "type": "string"},
                    ],
                    "title": "size",
                },
            },
            {
                "in": "query",
                "name": "day",
                "required": False,
                "schema": {
                    "anyOf": [{"type": "integer"}, now_desc],
                    "default": "now",
                    "title": "day",
                },
            },
            {
                "in": "query",
                "name": "age",
                "required": False,
                "schema": {"nullable": True, "title": "age", "type": "integer"},
            },
        ],
        "responses": {
            "200": {
                "description": "",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                },
            },
            "404": {"description": "", "content": {}},
        },
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_pets_id_route_should_have_put_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert generated_oas["paths"]["/pets/{id}"]["put"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"title": "id", "type": "integer"},
            }
        ],
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        '$ref': '#/components/schemas/Pet'
                    }
                }
            }
        },
        "responses": {"200": {"description": ""}},
    }


@pytest.mark.parametrize(
    "generate_oas",
    generate_oas_spec,
    ids=[
        "aiohttp view",
        "pydantic view",
        "decorated handler",
        "decorated handler with request",
    ],
)
async def test_simple_type_route_should_have_get_method(
    generate_oas, aiohttp_client, event_loop
):
    generated_oas = await generate_oas(aiohttp_client)
    assert generated_oas["paths"]["/simple-type"]["get"] == {
        "description": "",
        "responses": {
            "200": {
                "content": {"application/json": {"schema": {}}},
                "description": "The new number",
            }
        },
    }


async def test_generated_view_info_default():
    apps = (web.Application(),)
    spec = aiohttp_pydantic.oas.view.generate_oas(apps)

    assert spec == {
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "openapi": "3.0.0",
    }


async def test_generated_view_info_as_version():
    apps = (web.Application(),)
    spec = aiohttp_pydantic.oas.view.generate_oas(apps, version_spec="test version")

    assert spec == {
        "info": {"title": "Aiohttp pydantic application", "version": "test version"},
        "openapi": "3.0.0",
    }


async def test_generated_view_info_as_title():
    apps = (web.Application(),)
    spec = aiohttp_pydantic.oas.view.generate_oas(apps, title_spec="test title")

    assert spec == {
        "info": {"title": "test title", "version": "1.0.0"},
        "openapi": "3.0.0",
    }


class Pagination(Group):
    page: int = 1
    page_size: int = 20


async def test_use_parameters_group_should_not_impact_the_oas(aiohttp_client):
    class PetCollectionView1(PydanticView):
        async def get(self, page: int = 1, page_size: int = 20) -> r200[List[Pet]]:
            return web.json_response()

    class PetCollectionView2(PydanticView):
        async def get(self, pagination: Pagination) -> r200[List[Pet]]:
            return web.json_response()

    app1 = web.Application()
    app1.router.add_view("/pets", PetCollectionView1)
    oas.setup(app1)

    app2 = web.Application()
    app2.router.add_view("/pets", PetCollectionView2)
    oas.setup(app2)

    assert await ensure_content_durability(
        await aiohttp_client(app1)
    ) == await ensure_content_durability(await aiohttp_client(app2))
