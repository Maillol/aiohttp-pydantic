from aiohttp import web

from aiohttp_pydantic import PydanticView


class View1(PydanticView):
    async def get(self, a: int, /):
        return web.json_response()


class View2(PydanticView):
    async def post(self, b: int, /):
        return web.json_response()


sub_app = web.Application()
sub_app.router.add_view("/route-2/{b}", View2)

app = web.Application()
app.router.add_view("/route-1/{a}", View1)
app.add_subapp("/sub-app", sub_app)


def make_app():
    app = web.Application()
    app.router.add_view("/route-3/{a}", View1)
    return app
