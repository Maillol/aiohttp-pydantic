from aiohttp.web import Application, json_response, middleware

from aiohttp_pydantic import oas

from .model import Model
from .view import PetCollectionView, PetItemView
from .security import JWTIdentityPolicy, AuthorizationPolicy
import aiohttp_security

@middleware
async def pet_not_found_to_404(request, handler):
    try:
        return await handler(request)
    except Model.NotFound as key:
        return json_response({"error": f"Pet {key} does not exist"}, status=404)


app = Application(middlewares=[pet_not_found_to_404])
oas.setup(app, version_spec="1.0.1", title_spec="My App", security={"APIKeyHeader": {"type": "apiKey", "in": "header", "name": "Authorization"}})

app["model"] = Model()
app.router.add_view("/pets", PetCollectionView)
app.router.add_view("/pets/{id}", PetItemView)


policy = JWTIdentityPolicy(secret="1234", key="sub")
aiohttp_security.setup(app, policy, AuthorizationPolicy())
