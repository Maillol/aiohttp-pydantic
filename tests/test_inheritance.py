from typing import Any

from aiohttp_pydantic import PydanticView


def count_wrappers(obj: Any) -> int:
    """Count the number of times that an object is wrapped."""
    i = 0
    while i < 10:
        try:
            obj = obj.__wrapped__
        except AttributeError:
            return i
        else:
            i += 1
    raise RuntimeError("Too many wrappers")


class ViewParent(PydanticView):
    async def put(self):
        pass

    async def delete(self):
        pass


class ViewParentNonPydantic:
    async def post(self):
        pass


class ViewChild(ViewParent, ViewParentNonPydantic):
    async def get(self):
        pass

    async def delete(self):
        pass

    async def not_allowed(self):
        pass


def test_allowed_methods_are_set_correctly():
    assert ViewParent.allowed_methods == {"PUT", "DELETE"}
    assert ViewChild.allowed_methods == {"GET", "POST", "PUT", "DELETE"}


def test_allowed_methods_get_decorated_exactly_once():
    assert count_wrappers(ViewParent.put) == 1
    assert count_wrappers(ViewParent.delete) == 1
    assert count_wrappers(ViewChild.get) == 1
    assert count_wrappers(ViewChild.post) == 1
    assert count_wrappers(ViewChild.put) == 1
    assert count_wrappers(ViewChild.post) == 1
    assert count_wrappers(ViewChild.put) == 1

    assert count_wrappers(ViewChild.not_allowed) == 0
    assert count_wrappers(ViewParentNonPydantic.post) == 0
