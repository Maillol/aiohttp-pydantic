from enum import Enum
from typing import List, Optional, Union, Literal
from uuid import UUID

import pytest
from aiohttp import web
from pydantic.main import BaseModel

from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404
from aiohttp_pydantic.oas.view import generate_oas


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    PINK = "pink"


class Toy(BaseModel):
    name: str
    color: Color


class Pet(BaseModel):
    id: int
    name: str
    toys: List[Toy]


class PetCollectionView(PydanticView):
    async def get(
        self, format: str, name: Optional[str] = None, *, promo: Optional[UUID] = None
    ) -> r200[List[Pet]]:
        """
        Get a list of pets

        Status Codes:
          200: Successful operation
        """
        return web.json_response()

    async def post(self, pet: Pet) -> r201[Pet]:
        """Create a Pet"""
        return web.json_response()


class PetItemView(PydanticView):
    async def get(self, id: int, /, size: Union[int, Literal['x', 'l', 's']], day: Union[int, Literal["now"]] = "now") -> Union[r200[Pet], r404]:
        return web.json_response()

    async def put(self, id: int, /, pet: Pet):
        return web.json_response()

    async def delete(self, id: int, /) -> r204:
        """
        Status Code:
          204: Empty but OK
        """
        return web.json_response()


class ViewResponseReturnASimpleType(PydanticView):
    async def get(self) -> r200[int]:
        """
        Status Codes:
          200: The new number
        """
        return web.json_response()


@pytest.fixture
async def generated_oas(aiohttp_client, loop) -> web.Application:
    app = web.Application()
    app.router.add_view("/pets", PetCollectionView)
    app.router.add_view("/pets/{id}", PetItemView)
    app.router.add_view("/simple-type", ViewResponseReturnASimpleType)
    oas.setup(app)

    client = await aiohttp_client(app)
    response_1 = await client.get("/oas/spec")
    assert response_1.content_type == "application/json"
    assert response_1.status == 200
    content_1 = await response_1.json()

    # Reload the page to ensure that content is always the same
    # note: pydantic can return a cached dict, if a view updates
    # the dict the output will be incoherent
    response_2 = await client.get("/oas/spec")
    content_2 = await response_2.json()
    assert content_1 == content_2

    return content_2


async def test_generated_oas_should_have_components_schemas(generated_oas):
    assert generated_oas["components"]["schemas"] == {
        "Color": {
            "description": "An enumeration.",
            "enum": ["red", "green", "pink"],
            "title": "Color",
            "type": "string",
        },
        "Toy": {
            "properties": {
                "color": {"$ref": "#/components/schemas/Color"},
                "name": {"title": "Name", "type": "string"},
            },
            "required": ["name", "color"],
            "title": "Toy",
            "type": "object",
        },
    }


async def test_generated_oas_should_have_pets_paths(generated_oas):
    assert "/pets" in generated_oas["paths"]


async def test_pets_route_should_have_get_method(generated_oas):
    assert generated_oas["paths"]["/pets"]["get"] == {
        "description": "Get a list of pets",
        "parameters": [
            {
                "in": "query",
                "name": "format",
                "required": True,
                "schema": {"title": "format", "type": "string"},
            },
            {
                "in": "query",
                "name": "name",
                "required": False,
                "schema": {"title": "name", "type": "string"},
            },
            {
                "in": "header",
                "name": "promo",
                "required": False,
                "schema": {"format": "uuid", "title": "promo", "type": "string"},
            },
        ],
        "responses": {
            "200": {
                "description": "Successful operation",
                "content": {
                    "application/json": {
                        "schema": {
                            "items": {
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
                            "type": "array",
                        }
                    }
                },
            }
        },
    }


async def test_pets_route_should_have_post_method(generated_oas):
    assert generated_oas["paths"]["/pets"]["post"] == {
        "description": "Create a Pet",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
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
                    }
                }
            }
        },
        "responses": {
            "201": {
                "description": "",
                "content": {
                    "application/json": {
                        "schema": {
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
                        }
                    }
                },
            }
        },
    }


async def test_generated_oas_should_have_pets_id_paths(generated_oas):
    assert "/pets/{id}" in generated_oas["paths"]


async def test_pets_id_route_should_have_delete_method(generated_oas):
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


async def test_pets_id_route_should_have_get_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["get"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"title": "id", "type": "integer"},
            },
            {'in': 'query',
             'name': 'size',
             'required': True,
             'schema': {'anyOf': [{'type': 'integer'},
                                  {'enum': ['x', 'l', 's'],
                                   'type': 'string'}],
                        'title': 'size'}},
            {'in': 'query',
             'name': 'day',
             'required': False,
             'schema': {'anyOf': [{'type': 'integer'},
                                  {'enum': ['now'], 'type': 'string'}],
                        'default': 'now',
                        'title': 'day'}}
        ],
        "responses": {
            "200": {
                "description": "",
                "content": {
                    "application/json": {
                        "schema": {
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
                        }
                    }
                },
            },
            "404": {"description": "", "content": {}},
        },
    }


async def test_pets_id_route_should_have_put_method(generated_oas):
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
                    }
                }
            }
        },
    }


async def test_simple_type_route_should_have_get_method(generated_oas):
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
    spec = generate_oas(apps)

    assert spec == {
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "openapi": "3.0.0",
    }


async def test_generated_view_info_as_version():
    apps = (web.Application(),)
    spec = generate_oas(apps, version_spec="test version")

    assert spec == {
        "info": {"title": "Aiohttp pydantic application", "version": "test version"},
        "openapi": "3.0.0",
    }


async def test_generated_view_info_as_title():
    apps = (web.Application(),)
    spec = generate_oas(apps, title_spec="test title")

    assert spec == {
        "info": {"title": "test title", "version": "1.0.0"},
        "openapi": "3.0.0",
    }
