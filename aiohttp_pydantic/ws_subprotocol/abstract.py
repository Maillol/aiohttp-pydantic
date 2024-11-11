from aiohttp import WSMessage
from typing import ClassVar

from aiohttp_pydantic.mq_backend.abstract import MQBackend


class WSSubProtocol:

    sub_protocol_name: ClassVar[str] = ""

    def __init__(self, mq_backend: MQBackend):
        self._mq_backend = mq_backend

    async def read_ws_packet(self, msg: WSMessage):
        raise NotImplementedError()

    async def publish(self, topic: str, payload: str):
        """
        Publish a message to a topic. Handles the encoding and dispatch.
        """