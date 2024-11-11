from collections.abc import Callable
from contextvars import ContextVar
from types import MappingProxyType
from typing import Awaitable

from aiohttp import web
from .compat import AppKey
from aiohttp_pydantic.ws_subprotocol.abstract import WSSubProtocol
from .mq_backend.abstract import MQBackend, CloseWSConnection


ws_context: ContextVar[web.WebSocketResponse] = ContextVar("ws_context")
subscriber_type = Callable[..., Awaitable[None]]


class Publisher:

    def __init__(self, protocol: WSSubProtocol, topics: MappingProxyType):
        self._protocol = protocol
        self._topics = topics  # mapping PydanticBase: topic_name

    async def publish(self, message):
        try:
            topic = self._topics[type(message)]
        except KeyError:
            raise ValueError(
                f"The type {type(message)} is not bound to a topic."
                f" Use 'WSMultiplexer.add_publisher' to bind a type to a topic."
            )

        return await self._protocol.publish(topic, message.model_dump_json())


class WSApp:

    def build_publisher(self, backend: MQBackend) -> Publisher:
        return Publisher(self._protocol_cls(backend), self._publishers.items().mapping)

    def __init__(self, protocol_cls: type[WSSubProtocol]):
        self._protocol_cls = protocol_cls
        self._publishers: dict[type, str] = {}
        self._subscribers: dict[str, set[subscriber_type]] = {}

    @property
    def topics(self):
        yield from self._publishers.values()
        yield from self._subscribers.keys()

    def add_publisher(self, topic: str, msg_type: type):
        if (previous := self._publishers.setdefault(msg_type, topic)) != topic:
            raise ValueError(
                f"The msg_type ({msg_type}) is already bound to the topic {previous}"
            )

    def add_subscriber(self, topic: str, subscriber: subscriber_type):
        """
        Bind the subscriber to the topic.

        Multiple subscribers can be bound to the same
        topic, and the same subscriber can be bound to multiple topics.
        """
        self._subscribers.setdefault(topic, set()).add(subscriber)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse(protocols=[self._protocol_cls.sub_protocol_name])
        await ws.prepare(request)
        token = ws_context.set(ws)
        protocol = self._protocol_cls(request.app[MQ_BACKEND])

        try:
            async for msg in ws:
                try:
                    await protocol.read_ws_packet(msg)
                except CloseWSConnection:
                    break
        finally:
            ws_context.reset(token)
            await ws.close()
        return ws


MQ_BACKEND = AppKey("aiohttp-pydantic.mq-backend", MQBackend)
WS_MULTIPLEXER = AppKey("aiohttp-pydantic.ws-multiplexer", WSApp)
PUBLISHER = AppKey("aiohttp-pydantic.publisher", Publisher)


def setup(app: web.Application, route: str, ws_app: WSApp, mq_backend: MQ_BACKEND):
    app.router.add_get(route, ws_app.websocket_handler)

    async def context(app):
        for topic in ws_app.topics:
            await mq_backend.ensure_topic_exists(topic)
        yield
        # do cleanup

    app.cleanup_ctx.append(context)
    app[MQ_BACKEND] = mq_backend
    app[WS_MULTIPLEXER] = ws_app
    app[PUBLISHER] = ws_app.build_publisher(mq_backend)
    for topic, subscribers in ws_app._subscribers.items():
        for subscriber in subscribers:
            mq_backend.register_local_subscriber(topic, subscriber)
