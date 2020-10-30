from typing import List, Union

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404

from .model import Error, Pet


class PetCollectionView(PydanticView):
    async def get(self) -> r200[List[Pet]]:
        pets = self.request.app["model"].list_pets()
        return web.json_response([pet.dict() for pet in pets])

    async def post(self, pet: Pet) -> r201[Pet]:
        self.request.app["model"].add_pet(pet)
        return web.json_response(pet.dict())


class PetItemView(PydanticView):
    async def get(self, id: int, /) -> Union[r200[Pet], r404[Error]]:
        pet = self.request.app["model"].find_pet(id)
        return web.json_response(pet.dict())

    async def put(self, id: int, /, pet: Pet) -> r200[Pet]:
        self.request.app["model"].update_pet(id, pet)
        return web.json_response(pet.dict())

    async def delete(self, id: int, /) -> r204:
        self.request.app["model"].remove_pet(id)
        return web.Response(status=204)
