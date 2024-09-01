from __future__ import annotations

from enum import Enum
from typing import List
from pydantic.main import BaseModel


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    PINK = "pink"


class Toy(BaseModel):
    name: str
    color: Color


class Pet(BaseModel):
    id: int
    name: str
    toys: List[Toy]
