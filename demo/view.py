from typing import List, Optional, Union

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404

from .model import Error, Pet


class PetCollectionView(PydanticView):
    async def get(self, age: Optional[int] = None) -> r200[List[Pet]]:
        """
        List all pets

        Status Codes:
            200: Successful operation
        """
        pets = self.request.app["model"].list_pets()
        return web.json_response(
            [pet.model_dump() for pet in pets if age is None or age == pet.age]
        )

    async def post(self, pet: Pet) -> r201[Pet]:
        """
        Add a new pet to the store

        Status Codes:
            201: Successful operation
        """
        self.request.app["model"].add_pet(pet)
        return web.json_response(pet.model_dump())


class PetItemView(PydanticView):
    async def get(self, id: int, /) -> Union[r200[Pet], r404[Error]]:
        """
        Find a pet by ID

        Status Codes:
            200: Successful operation
            404: Pet not found
        """
        pet = self.request.app["model"].find_pet(id)
        return web.json_response(pet.dict())

    async def put(self, id: int, /, pet: Pet) -> r200[Pet]:
        """
        Update an existing object

        Status Codes:
            200: Successful operation
            404: Pet not found
        """
        self.request.app["model"].update_pet(id, pet)
        return web.json_response(pet.dict())

    async def delete(self, id: int, /) -> r204:
        """
        Deletes a pet
        """
        self.request.app["model"].remove_pet(id)
        return web.Response(status=204)
