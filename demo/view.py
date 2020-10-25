from aiohttp_pydantic import PydanticView
from aiohttp import web

from .model import Pet


class PetCollectionView(PydanticView):
    async def get(self):
        pets = self.request.app["model"].list_pets()
        return web.json_response([pet.dict() for pet in pets])

    async def post(self, pet: Pet):
        self.request.app["model"].add_pet(pet)
        return web.json_response(pet.dict())


class PetItemView(PydanticView):
    async def get(self, id: int, /):
        pet = self.request.app["model"].find_pet(id)
        return web.json_response(pet.dict())

    async def put(self, id: int, /, pet: Pet):
        self.request.app["model"].update_pet(id, pet)
        return web.json_response(pet.dict())

    async def delete(self, id: int, /):
        self.request.app["model"].remove_pet(id)
        return web.json_response(id)
