from __future__ import annotations


from typing import List, Optional, Union, Literal
from uuid import UUID

from aiohttp import web
from pydantic import Field

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404
from aiohttp_pydantic import oas

from .model import Pet


class PetCollectionView(PydanticView):
    async def get(
        self,
        format: str = Field(..., description="description for format"),
        name: Optional[str] = None,
        *,
        promo: Optional[UUID] = Field(None, description="description for promo"),
    ) -> r200[List[Pet]]:
        """
        Get a list of pets

        Security: APIKeyHeader
        Tags: pet
        Status Codes:
          200: Successful operation
        """
        return web.json_response()

    async def post(self, pet: Pet) -> r201[Pet]:
        """Create a Pet"""
        return web.json_response()


class PetItemView(PydanticView):
    async def get(
        self,
        id: int,
        /,
        size: Union[int, Literal["x", "l", "s"]],
        day: Union[int, Literal["now"]] = "now",
        age: Union[int, None] = None,
    ) -> Union[r200[Pet], r404]:
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


def build_app():
    app = web.Application()
    app.router.add_view("/pets", PetCollectionView)
    app.router.add_view("/pets/{id}", PetItemView)
    app.router.add_view("/simple-type", ViewResponseReturnASimpleType)
    oas.setup(app)
    return app
