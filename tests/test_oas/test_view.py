from pydantic.main import BaseModel
from aiohttp_pydantic import PydanticView, oas
from aiohttp import web

import pytest


class Pet(BaseModel):
    id: int
    name: str


class PetCollectionView(PydanticView):
    async def get(self):
        return web.json_response()

    async def post(self, pet: Pet):
        return web.json_response()


class PetItemView(PydanticView):
    async def get(self, id: int, /):
        return web.json_response()

    async def put(self, id: int, /, pet: Pet):
        return web.json_response()

    async def delete(self, id: int, /):
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


async def test_generated_oas_should_have_pets_paths(generated_oas):
    assert "/pets" in generated_oas["paths"]


async def test_pets_route_should_have_get_method(generated_oas):
    assert generated_oas["paths"]["/pets"]["get"] == {}


async def test_pets_route_should_have_post_method(generated_oas):
    assert generated_oas["paths"]["/pets"]["post"] == {
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "title": "Pet",
                        "type": "object",
                    }
                }
            }
        }
    }


async def test_generated_oas_should_have_pets_id_paths(generated_oas):
    assert "/pets/{id}" in generated_oas["paths"]


async def test_pets_id_route_should_have_delete_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["delete"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"type": "integer"},
            }
        ]
    }


async def test_pets_id_route_should_have_get_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["get"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"type": "integer"},
            }
        ]
    }


async def test_pets_id_route_should_have_put_method(generated_oas):
    assert generated_oas["paths"]["/pets/{id}"]["put"] == {
        "parameters": [
            {
                "in": "path",
                "name": "id",
                "required": True,
                "schema": {"type": "integer"},
            }
        ],
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "title": "Pet",
                        "type": "object",
                    }
                }
            }
        },
    }
