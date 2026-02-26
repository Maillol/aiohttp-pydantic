from .schema import CreatePet, CreateUser, Pet, User


class NotFound(KeyError):
    """
    Raised when a resource is not found.
    """


class Conflict(Exception):
    """
    Raised when a resource conflict.
    """


class Model:
    """
    To keep simple this demo, we use a simple dict as database to
    store the models.
    """

    def __init__(self):
        self.storage = {"pet": {}, "user": {}}

    def add_pet(self, pet: CreatePet, owner_id: int):
        new_id = len(self.storage["pet"]) + 1
        new_pet = Pet(id=new_id, owner_id=owner_id, **pet.model_dump())
        self.storage["pet"][new_id] = new_pet
        return new_pet

    def remove_pet(self, id: int):
        try:
            del self.storage["pet"][id]
        except KeyError as error:
            raise NotFound(str(error))

    def update_pet(self, id: int, pet: CreatePet):
        pet_to_update = self.storage["pet"][id]
        for key, value in pet.model_dump().items():
            setattr(pet_to_update, key, value)

    def find_pet(self, id: int):
        try:
            return self.storage["pet"][id]
        except KeyError as error:
            raise NotFound(str(error))

    def list_pets(self):
        return list(self.storage["pet"].values())

    def add_user(self, user: CreateUser):
        new_id = len(self.storage["user"]) + 1
        new_user = User(id=new_id, **user.model_dump())
        for existing_user in self.storage["user"].values():
            if existing_user.username == user.username:
                raise Conflict()
        self.storage["user"][new_id] = new_user
        return new_user

    def remove_user(self, id: int):
        try:
            del self.storage["user"][id]
        except KeyError as error:
            raise NotFound(str(error))

    def update_user(self, id: int, user: CreateUser):
        self.remove_user(id)
        self.add_user(user)

    def find_user(self, id: int):
        try:
            return self.storage["user"][id]
        except KeyError as error:
            raise NotFound(str(error))

    def list_users(self):
        return list(self.storage["user"].values())
