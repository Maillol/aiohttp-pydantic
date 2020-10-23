from aiohttp import web

from aiohttp_pydantic import oas
from aiohttp.web import middleware

from .view import PetItemView, PetCollectionView
from .model import Model


@middleware
async def pet_not_found_to_404(request, handler):
    try:
        return await handler(request)
    except Model.NotFound as key:
        return web.json_response({"error": f"Pet {key} does not exist"}, status=404)


app = web.Application(middlewares=[pet_not_found_to_404])
oas.setup(app)

app["model"] = Model()
app.router.add_view("/pets", PetCollectionView)
app.router.add_view("/pets/{id}", PetItemView)

web.run_app(app)
