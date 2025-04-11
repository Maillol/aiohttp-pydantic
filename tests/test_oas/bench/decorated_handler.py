from __future__ import annotations


from typing import List, Optional, Union, Literal
from uuid import UUID

from aiohttp import web
from pydantic import Field
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404
from aiohttp_pydantic import oas
from aiohttp_pydantic.decorator import inject_params

from .model import Pet


@inject_params
async def list_pet(
    format: str,
    name: Optional[str] = None,
    *,
    promo: Optional[UUID] = Field(
        None, description="description for promo")
) -> r200[List[Pet]]:
    """
    Get a list of pets

    Security: APIKeyHeader
    Tags: pet
    Status Codes:
      200: Successful operation
    """
    return web.json_response()


@inject_params
async def post_pet(pet: Pet) -> r201[Pet]:
    """Create a Pet"""
    return web.json_response()


@inject_params
async def get_pet(
    self,
    id: int,
    /,
    size: Union[int, Literal["x", "l", "s"]],
    day: Union[int, Literal["now"]] = "now",
) -> Union[r200[Pet], r404]:
    return web.json_response()


@inject_params
async def put_pet(id: int, /, pet: Pet):
    return web.json_response()


@inject_params
async def delete_pet(id: int, /) -> r204:
    """
    Status Code:
      204: Empty but OK
    """
    return web.json_response()


@inject_params
async def get_a_simple_type() -> r200[int]:
    """
    Status Codes:
      200: The new number
    """
    return web.json_response()


def build_app():
    app = web.Application()
    app.router.add_get("/pets", list_pet)
    app.router.add_post("/pets", post_pet)
    app.router.add_get("/pets/{id}", get_pet)
    app.router.add_put("/pets/{id}", put_pet)
    app.router.add_delete("/pets/{id}", delete_pet)
    app.router.add_get("/simple-type", get_a_simple_type)
    oas.setup(app)
    return app
