from pydantic import BaseModel
from typing import List


class Friend(BaseModel):
    name: str
    age: str


class Pet(BaseModel):
    id: int
    name: str
    age: int
    friends: Friend


class Error(BaseModel):
    error: str


class Model:
    """
    To keep simple this demo, we use a simple dict as database to
    store the models.
    """

    class NotFound(KeyError):
        """
        Raised when a pet is not found.
        """

    def __init__(self):
        self.storage = {}

    def add_pet(self, pet: Pet):
        self.storage[pet.id] = pet

    def remove_pet(self, id: int):
        try:
            del self.storage[id]
        except KeyError as error:
            raise self.NotFound(str(error))

    def update_pet(self, id: int, pet: Pet):
        self.remove_pet(id)
        self.add_pet(pet)

    def find_pet(self, id: int):
        try:
            return self.storage[id]
        except KeyError as error:
            raise self.NotFound(str(error))

    def list_pets(self):
        return list(self.storage.values())
