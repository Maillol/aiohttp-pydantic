from aiohttp.web import Application, json_response, middleware

from aiohttp_pydantic import oas

from .model import Model
from .view import PetCollectionView, PetItemView
from .customize_oas import PetDetailsView


@middleware
async def pet_not_found_to_404(request, handler):
    try:
        return await handler(request)
    except Model.NotFound as key:
        return json_response({"error": f"Pet {key} does not exist"}, status=404)


app = Application(middlewares=[pet_not_found_to_404])
oas.setup(app, version_spec="1.0.1", title_spec="My App")

app["model"] = Model()
app.router.add_view("/pets", PetCollectionView)
app.router.add_view("/pets/{id}", PetItemView)
app.router.add_view("/pets/{id}/details", PetDetailsView)
