from __future__ import annotations


from typing import List, Optional, Union, Literal
from uuid import UUID

from aiohttp import web

from aiohttp_pydantic.oas.typing import r200, r201, r204, r404
from aiohttp_pydantic import oas
from aiohttp_pydantic.decorator import inject_params
from .model import Pet


class PetCollectionView(web.View):

    @inject_params.in_method
    async def get(
        self, format: str, name: Optional[str] = None, *, promo: Optional[UUID] = None
    ) -> r200[List[Pet]]:
        """
        Get a list of pets

        Security: APIKeyHeader
        Tags: pet
        Status Codes:
          200: Successful operation
        """
        return web.json_response()

    @inject_params.in_method
    async def post(self, pet: Pet) -> r201[Pet]:
        """Create a Pet"""
        return web.json_response()


class PetItemView(web.View):
    @inject_params.in_method
    async def get(
        self,
        id: int,
        /,
        size: Union[int, Literal["x", "l", "s"]],
        day: Union[int, Literal["now"]] = "now",
    ) -> Union[r200[Pet], r404]:
        return web.json_response()

    @inject_params.in_method
    async def put(self, id: int, /, pet: Pet):
        return web.json_response()

    @inject_params.in_method
    async def delete(self, id: int, /) -> r204:
        """
        Status Code:
          204: Empty but OK
        """
        return web.json_response()


class ViewResponseReturnASimpleType(web.View):

    @inject_params.in_method
    async def get(self) -> r200[int]:
        """
        Status Codes:
          200: The new number
        """
        return web.json_response()


def build_app():
    app = web.Application()
    app.router.add_view("/pets", PetCollectionView)
    app.router.add_view("/pets/{id}", PetItemView)
    app.router.add_view("/simple-type", ViewResponseReturnASimpleType)
    oas.setup(app)
    return app
