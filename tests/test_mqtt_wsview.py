from __future__ import annotations

import json
from unittest.mock import ANY

from aiohttp import web, ClientWebSocketResponse
import pytest
from pydantic import BaseModel
from aiohttp_pydantic import wsapp

from aiohttp_pydantic.mq_backend.memory import MemoryMQBackend
from aiohttp_pydantic.ws_subprotocol.mqtt import (
    MQTT,
    create_mqtt_connect_packet,
    create_mqtt_subscribe_packet,
    MQTTQoSLevel,
    analyze_mqtt_publish_packet,
)
from aiohttp_pydantic.wsapp import WSApp, PUBLISHER


class BookModel(BaseModel):
    title: str
    nb_page: int


async def post(request):
    await request.app[PUBLISHER].publish(BookModel(title="Salut", nb_page=54))
    return web.json_response({})


def build_app():
    app = web.Application()
    app.router.add_post("/publish", post)
    multiplexer = WSApp(MQTT)
    multiplexer.add_publisher("new-book-available", BookModel)

    async def book_is_fun(book: BookModel):
        print("book_is_fun", book)

    multiplexer.add_subscriber("book-is-fun", book_is_fun)
    wsapp.setup(app, "/ws", multiplexer, MemoryMQBackend())

    return app


app_builders = [build_app]


@pytest.mark.parametrize("app_builder", app_builders, ids=["mqtt"])
async def test_publish(app_builder, aiohttp_client, event_loop):
    client = await aiohttp_client(app_builder())
    ws: ClientWebSocketResponse
    async with client.ws_connect("/ws") as ws:
        await ws.send_bytes(create_mqtt_connect_packet("1234"))
        await ws.receive_bytes(timeout=1)
        await ws.send_bytes(
            create_mqtt_subscribe_packet(1, {"new-book-available": MQTTQoSLevel.AT_MOST_ONCE})
        )
        await ws.receive_bytes(timeout=1)

        resp = await client.post("/publish")
        assert resp.status == 200
        message = await ws.receive_bytes(timeout=1)
        analysed = analyze_mqtt_publish_packet(message[0], message[2:])
        assert analysed == {
            "topic_name": "new-book-available",
            "qos": 0,
            "retain": False,
            "dup": False,
            "payload": ANY,
        }
        assert json.loads(analysed["payload"].decode("utf-8")) == {
            "title": "Salut",
            "nb_page": 54,
        }
