from aiohttp.web import Application, json_response, middleware

from aiohttp_pydantic import oas
from aiohttp_pydantic import wsapp
from aiohttp_pydantic.mq_backend.memory import MemoryMQBackend
from aiohttp_pydantic.ws_subprotocol.mqtt import MQTT
from aiohttp_pydantic.wsapp import WSApp
from .model import Model, Pet, Friend
from .view import PetCollectionView, PetItemView


@middleware
async def pet_not_found_to_404(request, handler):
    try:
        return await handler(request)
    except Model.NotFound as key:
        return json_response({"error": f"Pet {key} does not exist"}, status=404)


app = Application(middlewares=[pet_not_found_to_404])
oas.setup(app,
          version_spec="1.0.1",
          title_spec="My App",
          security={"APIKeyHeader": {"type": "apiKey", "in": "header", "name": "Authorization"}})


app["model"] = Model()
app.router.add_view("/pets", PetCollectionView)
app.router.add_view("/pets/{id}", PetItemView)

multiplexer = WSApp(MQTT)
multiplexer.add_publisher("new-pet-available", Pet)

async def pony_is_fun(friend: Friend):
    print("pony_is_fun", friend)


multiplexer.add_subscriber("pony-is-fun", pony_is_fun)


wsapp.setup(app, "/ws", multiplexer, MemoryMQBackend())
