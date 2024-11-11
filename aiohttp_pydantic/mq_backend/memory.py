import asyncio
from collections.abc import Callable, Awaitable

from aiohttp.web_ws import WebSocketResponse

from .abstract import MQBackend
from ..wsapp import ws_context
from weakref import WeakSet, WeakKeyDictionary
import logging

LOGGER = logging.getLogger(__name__)


class MemoryMQBackend(MQBackend):

    def __init__(self):
        # Store connected clients (WebSocketResponse: user identifier)
        self._identifier_by_ws: WeakKeyDictionary[WebSocketResponse:str] = WeakKeyDictionary()
        # Store topics and their subscribers (topic: WeakSet of WebSocketResponse)
        self._topics: dict[str : WeakSet[WebSocketResponse]] = {}
        self._available_topics: set[str] = set()
        self._local_subscribers: dict[str, set[Callable[[bytes], Awaitable[None]]]] = {}

    async def ensure_topic_exists(self, topic: str):
        topic = topic.removeprefix("/")
        if not topic.isprintable():
            LOGGER.error(f"Invalid topic name {topic!r}.")
            return False

        LOGGER.debug(f"Add topic {topic!r}.")
        self._available_topics.add(topic)
        return True

    async def connect(self, identifier: str) -> bool:
        """
        Handle client connection. Returns True if the client is accepted.
        """
        ws = ws_context.get()
        if ws in self._identifier_by_ws:
            LOGGER.error(f"Client '{identifier}' is already connected on this WebSocket.")
            return False

        self._identifier_by_ws[ws] = identifier
        LOGGER.debug(f"Connecting client '{identifier}' on a new WebSocket...")
        return True

    async def subscribe(self, topic: str) -> bool:
        """
        Handle client subscription to a topic. Returns True if successful.
        """
        ws = ws_context.get()
        identifier = self._identifier_by_ws.get(ws)
        if identifier is None:
            LOGGER.error("Cannot subscribe: Client is not connected.")
            return False

        if topic not in self._available_topics:
            LOGGER.error(
                f"Cannot subscribe: Topic '{topic}' is not available. (Available topics: {self._available_topics})"
            )
            return False

        LOGGER.debug(f"Client '{identifier}' subscribing to topic '{topic}'...")
        # Add the topic to the client's subscription list
        self._topics.setdefault(topic, WeakSet()).add(ws)

        return True

    async def unsubscribe(self, topic: str) -> bool:
        """
        Handle client unsubscription from a topic. Returns True if successful.
        """
        ws = ws_context.get()
        identifier = self._identifier_by_ws.get(ws)
        if identifier is None:
            LOGGER.error(f"Cannot unsubscribe: Client is not connected.")
            return False

        if ws not in self._topics.get(topic, ()):
            LOGGER.error(f"Client '{identifier}' is not subscribed to topic '{topic}'.")
            return False

        LOGGER.debug(f"Client '{identifier}' unsubscribing from topic '{topic}'...")
        # Remove the client from the topic's subscriber list
        self._topics[topic].discard(ws)
        if not self._topics[topic]:  # Remove the topic if it has no subscribers
            del self._topics[topic]

        return True

    async def disconnect(self) -> bool:
        """
        Disconnect a client, removing its WebSocket connection and subscriptions.
        """

        ws = ws_context.get()
        identifier = self._identifier_by_ws.pop(ws, None)
        if identifier is None:
            LOGGER.warning(
                f"Warning: Client '{identifier}' Attempt to disconnect a WebSocket that is not connected."
            )
            return True

        LOGGER.debug(f"Disconnecting client '{identifier}' and cleaning up subscriptions...")
        # Clean up all subscriptions for this WebSocket
        for topic, subscribers in list(self._topics.items()):
            subscribers.discard(ws)
            if not subscribers:  # Remove the topic if no subscribers remain
                del self._topics[topic]

        return True

    async def publish(self, topic: str, payload: str) -> None:
        """
        Send a message to all remote subscribers of a topic.
        """
        subscribers = self._topics.get(topic, set())
        LOGGER.debug(f"Publishing to topic '{topic}' with {len(subscribers)} remote subscribers.")

        await asyncio.gather(*(ws.send_bytes(payload.encode("utf-8")) for ws in subscribers))

    async def notify_local_subscribers(self, topic: str, message: bytes) -> None:
        """
        Notify local subscribers of a message directly.
        """
        subscribers = self._local_subscribers.get(topic, [])
        LOGGER.debug(f"Notifying {len(subscribers)} local subscribers on topic '{topic}'.")
        await asyncio.gather(*(subscriber(message) for subscriber in subscribers))

    def register_local_subscriber(self, topic: str, subscriber: Callable[[bytes], Awaitable[None]]):
        self._local_subscribers.setdefault(topic, set()).add(subscriber)
