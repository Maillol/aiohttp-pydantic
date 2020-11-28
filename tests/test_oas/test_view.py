from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

import pytest
from aiohttp import web
from pydantic.main import BaseModel

from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404


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
        """
        return web.json_response()

    async def post(self, pet: Pet) -> r201[Pet]:
        """Create a Pet"""
        return web.json_response()


class PetItemView(PydanticView):
    async def get(self, id: int, /) -> Union[r200[Pet], r404]:
        return web.json_response()

    async def put(self, id: int, /, pet: Pet):
        return web.json_response()

    async def delete(self, id: int, /) -> r204:
        return web.json_response()


@pytest.fixture
async def generated_oas(aiohttp_client, loop) -> web.Application:
    app = web.Application()
    app.router.add_view("/pets", PetCollectionView)
    app.router.add_view("/pets/{id}", PetItemView)
    oas.setup(app)

    client = await aiohttp_client(app)
    response = await client.get("/oas/spec")
    assert response.status == 200
    assert response.content_type == "application/json"
    return await response.json()


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
                "content": {
                    "application/json": {
                        "schema": {
                            "items": {
                                "definitions": {
                                    "Color": {
                                        "description": "An enumeration.",
                                        "enum": ["red", "green", "pink"],
                                        "title": "Color",
                                        "type": "string",
                                    },
                                    "Toy": {
                                        "properties": {
                                            "color": {
                                                "$ref": "#/components/schemas/Color"
                                            },
                                            "name": {"title": "Name", "type": "string"},
                                        },
                                        "required": ["name", "color"],
                                        "title": "Toy",
                                        "type": "object",
                                    },
                                },
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
                }
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
                        "definitions": {
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
                        },
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
                "content": {
                    "application/json": {
                        "schema": {
                            "definitions": {
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
                            },
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
            }
        },
    }


async def test_generated_oas_should_have_pets_id_paths(generated_oas):
    assert "/pets/{id}" in generated_oas["paths"]


async def test_pets_id_route_should_have_delete_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["delete"] == {
        "parameters": [
            {
                "required": True,
                "in": "path",
                "name": "id",
                "schema": {"title": "id", "type": "integer"},
            }
        ],
        "responses": {"204": {"content": {}}},
    }


async def test_pets_id_route_should_have_get_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["get"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"title": "id", "type": "integer"},
            }
        ],
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "definitions": {
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
                            },
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
            "404": {"content": {}},
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
                        "definitions": {
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
                        },
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
