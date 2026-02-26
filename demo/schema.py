from pydantic import BaseModel


class Friend(BaseModel):
    name: str
    age: int


class CreatePet(BaseModel):
    name: str
    age: int
    friends: list[Friend]


class Pet(BaseModel):
    id: int
    name: str
    age: int
    owner_id: int
    friends: list[Friend]


class Error(BaseModel):
    error: str


class CreateUser(BaseModel):
    username: str
    admin: bool


class User(BaseModel):
    id: int
    username: str
    admin: bool


class UserLogin(BaseModel):
    username: str
