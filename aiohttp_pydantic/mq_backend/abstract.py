from collections.abc import Callable, Awaitable


class CloseWSConnection(Exception):
    pass


class MQBackend:

    async def ensure_topic_exists(self, topic):
        pass

    async def connect(self, identifier) -> bool:
        pass

    async def disconnect(self) -> bool:
        pass

    async def subscribe(self, topic: str) -> bool:
        pass

    async def unsubscribe(self, topic: str) -> bool:
        pass

    async def publish(self, topic, message):
        pass

    async def notify_local_subscribers(self, topic: str, message: bytes) -> None:
        """
        Notify local subscribers of a message directly.
        """

    def register_local_subscriber(self, topic: str, subscriber: Callable[[bytes], Awaitable[None]]):
        pass
