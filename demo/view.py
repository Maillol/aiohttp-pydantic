from typing import List, Optional, Union

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.decorator import auth
from aiohttp_pydantic.oas.typing import default, r200, r201, r204, r404
from aiohttp_pydantic.security import AUTH_SCHEMES

from .keys import CURRENT_USER, MODEL
from .schema import CreatePet, CreateUser, Error, Pet, UserLogin
from .security import USER_AUTH


class PetCollectionView(PydanticView):
    async def get(self, age: Optional[int] = None) -> r200[List[Pet]]:
        """
        List all pets, with an optional age filter.

        Status Codes:
            200: Successful operation
        """
        pets = self.request.app[MODEL].list_pets()
        return web.json_response(
            [pet.model_dump() for pet in pets if age is None or age == pet.age]
        )

    @auth(USER_AUTH.rule("user"))
    async def post(self, pet: CreatePet) -> r201[Pet]:
        """
        Add a new pet to the store

        Security: APIKeyHeader

        Status Codes:
            201: Successful operation
        """
        current_user = self.request[CURRENT_USER]
        new_pet = self.request.app[MODEL].add_pet(pet, owner_id=current_user.id)
        return web.json_response(new_pet.model_dump())


class PetItemView(PydanticView):
    async def get(self, id: int, /) -> Union[r200[Pet], r404[Error], default[Error]]:
        """
        Find a pet by ID

        Status Codes:
            200: Successful operation
            404: Pet not found
            default: Unexpected error
        """
        pet = self.request.app[MODEL].find_pet(id)
        return web.json_response(pet.dict())

    @auth(USER_AUTH.rule("owner"))
    async def put(self, id: int, /, pet: CreatePet) -> r200[Pet]:
        """
        Update an existing object

        Status Codes:
            200: Successful operation
            404: Pet not found
        """
        self.request.app[MODEL].update_pet(id, pet)
        return web.json_response(pet.dict())

    @auth(USER_AUTH.rule("admin"))
    async def delete(self, id: int, /) -> r204:
        """
        Deletes a pet
        """
        self.request.app[MODEL].remove_pet(id)
        return web.Response(status=204)


class UserCollectionView(PydanticView):
    async def post(self, user: CreateUser) -> r201:
        """
        Create a new user.

        Status Codes:
            201: Successful operation
        """
        new_user = self.request.app[MODEL].add_user(user)
        return web.json_response(new_user.model_dump())


class UserLoginView(PydanticView):
    async def post(self, login: UserLogin) -> r200:
        """
        Logs user into the system.

        Flow:
        1. Look up the user by username
        2. If found, generate a JWT with sub=user.id and admin=user.admin
        3. Return the token to the client
        4. The client must then send this token in "Authorization: Bearer <token>"

        Status Codes:
            200: Successful operation
        """
        for user in self.request.app[MODEL].list_users():
            if user.username == login.username:
                user_auth = self.request.app[AUTH_SCHEMES][USER_AUTH]
                token = user_auth.create_token(sub=user.id, admin=user.admin)
                return web.json_response({"token": token})
        return web.json_response(
            {
                "error": "Incorrect username",
                "details": "Try again",
            },
            status=401,
        )
