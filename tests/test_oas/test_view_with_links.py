from typing import NewType

import pytest
from aiohttp import web
from pydantic.main import BaseModel

from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.oas.struct import Link
from aiohttp_pydantic.oas.typing import r200, r201
from aiohttp_pydantic.oas.view import LinksBuilder

UserId = NewType("UserId", int)


class UserToCreate(BaseModel):
    name: str


class ReturnedUser(BaseModel):
    id: UserId
    name: str


class GetUserView(PydanticView):
    async def get(self, user_id: UserId, /) -> r200[ReturnedUser]:
        return web.json_response()


class PostUserView(PydanticView):
    async def post(self, user: UserToCreate) -> r201[ReturnedUser]:
        return web.json_response()


@pytest.fixture
async def generated_oas(aiohttp_client, loop) -> web.Application:
    app = web.Application()
    app.router.add_view("/user", PostUserView)
    app.router.add_view("/user/{id}", GetUserView)
    oas.setup(app)

    client = await aiohttp_client(app)
    response = await client.get("/oas/spec")
    assert response.status == 200
    assert response.content_type == "application/json"
    return await response.json()


async def test_get_user_route_should_not_have_link(generated_oas):
    assert generated_oas["paths"]["/user/{id}"]["get"] == {
        # FIXME: "operationId": "tests.test_oas.test_view_with_links.GetUserView.get"
        "parameters": [
            {
                "in": "path",
                "name": "user_id",
                "required": True,
                "schema": {"title": "user_id", "type": "integer"},
            }
        ],
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "properties": {
                                "id": {"title": "Id", "type": "integer"},
                                "name": {"title": "Name", "type": "string"},
                            },
                            "required": ["id", "name"],
                            "title": "ReturnedUser",
                            "type": "object",
                        }
                    }
                },
                "description": "",
                "links": {
                    "link_name": {
                        "operation_id": "tests.test_oas.test_view_with_links.GetUserView.get",
                        "parameters": {"user_id": "$response.body#/id"},
                    }
                },
            }
        },
    }


async def test_post_user_route_should_have_link(generated_oas):
    assert generated_oas["paths"]["/user"]["post"] == {
        # FIXME: "operationId": "tests.test_oas.test_view_with_links.PostUserView.post"
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "properties": {"name": {"title": "Name", "type": "string"}},
                        "required": ["name"],
                        "title": "UserToCreate",
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
                            "properties": {
                                "id": {"title": "Id", "type": "integer"},
                                "name": {"title": "Name", "type": "string"},
                            },
                            "required": ["id", "name"],
                            "title": "ReturnedUser",
                            "type": "object",
                        }
                    }
                },
                "description": "",
                "links": {
                    "link_name": {
                        "operation_id": "tests.test_oas.test_view_with_links.GetUserView.get",
                        "parameters": {"user_id": "$response.body#/id"},
                    }
                },
            }
        },
    }


def test_links_builder():
    links_builder = LinksBuilder()
    links_builder.add_destination_parameter(
        UserId, operation_id="getUser", parameter_name="user_id"
    )
    spec = {}
    links_builder.add_src_parameter(Link(spec), UserId, "$response.body#/id")
    links_builder.build_links()
    assert spec == {
        "operation_id": "getUser",
        "parameters": {"user_id": "$response.body#/id"},
    }
