from typing import Any

from aiohttp_pydantic import PydanticView
from aiohttp.web import View


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


class AiohttpViewParent(View):
    async def put(self):
        pass


class PydanticViewParent(PydanticView):
    async def get(self, id: int, /):
        pass


def test_allowed_methods_get_decorated_exactly_once():
    class ChildView(PydanticViewParent):
        async def post(self, id: int, /):
            pass

    class SubChildView(ChildView):
        async def get(self, id: int, /):
            return super().get(id)

    assert count_wrappers(ChildView.post) == 1
    assert count_wrappers(ChildView.get) == 1
    assert count_wrappers(SubChildView.post) == 1
    assert count_wrappers(SubChildView.get) == 1


def test_methods_inherited_from_aiohttp_view_should_not_be_decorated():
    class ChildView(AiohttpViewParent, PydanticView):
        async def post(self, id: int, /):
            pass

    assert count_wrappers(ChildView.put) == 0
    assert count_wrappers(ChildView.post) == 1


def test_allowed_methods_are_set_correctly():
    class ChildView(AiohttpViewParent, PydanticView):
        async def post(self, id: int, /):
            pass

    assert ChildView.allowed_methods == {"POST", "PUT"}

    class ChildView(PydanticViewParent):
        async def post(self, id: int, /):
            pass

    assert ChildView.allowed_methods == {"POST", "GET"}

    class ChildView(AiohttpViewParent, PydanticViewParent):
        async def post(self, id: int, /):
            pass

    assert ChildView.allowed_methods == {"POST", "PUT", "GET"}
