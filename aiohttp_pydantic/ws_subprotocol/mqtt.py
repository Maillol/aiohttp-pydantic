from enum import Enum

from aiohttp import WSMessage, WSMsgType

from .abstract import WSSubProtocol
from ..mq_backend.abstract import MQBackend, CloseWSConnection
from ..wsapp import ws_context


def encode_remaining_length(length: int) -> bytes:
    """
    Encode the remaining length field as per MQTT specification.

    Args:
        length (int): The length to encode.

    Returns:
        bytes: Encoded remaining length.
    """
    encoded_bytes = []
    while True:
        byte = length % 128
        length //= 128
        if length > 0:
            byte |= 0x80  # Set the continuation bit
        encoded_bytes.append(byte)
        if length == 0:
            break
    return bytes(encoded_bytes)


def decode_remaining_length(data):
    multiplier = 1
    value = 0
    bytes_used = 0

    for bytes_used, byte in enumerate(data, 1):
        value += (byte & 127) * multiplier
        multiplier *= 128
        if (byte & 128) == 0:
            break
        if bytes_used > 3:
            raise ValueError("Malformed Remaining Length")
    return value, bytes_used


class MQTTConnAckReturnCode(int, Enum):
    CONNECTION_ACCEPTED = 0x00  # Connection accepted
    UNACCEPTABLE_PROTOCOL_VERSION = 0x01  # Connection Refused, unacceptable protocol version
    IDENTIFIER_REJECTED = 0x02  # The Client identifier is correct UTF-8 but not allowed by the Server
    SERVER_UNAVAILABLE = 0x03  # The Network Connection has been made but the MQTT service is unavailable
    BAD_USERNAME_OR_PASSWORD = 0x04  # The data in the username or password is malformed
    NOT_AUTHORIZED = 0x05  # The Client is not authorized to connect


class MQTTQoSLevel(int, Enum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2
    FAILURE = 128


class ProtocolError(Exception):
    pass


class ProtocolViolation(ProtocolError):
    """
    Close the websocket connexion immediately.
    """


class UnacceptableProtocolVersion(ProtocolError):
    return_code = MQTTConnAckReturnCode.UNACCEPTABLE_PROTOCOL_VERSION


def analyze_mqtt_connect_packet(message: bytes):
    """
    Client requests a connection to a Server


    Args:
        variable_header_and_payload (bytes): Variable header + Payload of SUBSCRIBE MQTT Packet.
    """

    # Protocol Name
    if message[2:6] != b"MQTT":
        raise UnacceptableProtocolVersion("Wrong protocol name must be MQTT")

    # Protocol Version
    if message[6] != 4:  # 4 ==> version 3.1.1
        raise UnacceptableProtocolVersion("Wrong protocol version, must be 3.1.1")

    # Connect Flags
    clean_session = bool(message[7] & 0x02)
    will_flag = bool(message[7] & 0x04)
    if will_flag:
        will_qos = (message[7] & 0x18) >> 3
        will_retain = bool(message[7] & 0x20)
    else:
        will_qos = 0
        will_retain = False

    password_flag = bool(message[7] & 64)
    username_flag = bool(message[7] & 128)

    keep_alive = int.from_bytes(message[8:10], byteorder="big")

    connect_params = {
        "clean_session": clean_session,
        "will_qos": will_qos,
        "will_retain": will_retain,
        "keep_alive": keep_alive,
    }

    ## Payload
    # Payload order: Client Identifier, Will Topic, Will Message, User Name, Password
    offset = 10

    # Client Identifier
    length = int.from_bytes(message[offset : offset + 2], byteorder="big")
    offset += 2
    client_id = message[offset : offset + length]
    offset += length
    connect_params["client_id"] = client_id

    if will_flag:
        length = int.from_bytes(message[offset : offset + 2], byteorder="big")
        offset += 2
        will_topic = message[offset : offset + length]
        offset += length

        length = int.from_bytes(message[offset : offset + 2], byteorder="big")
        offset += 2
        will_message = message[offset : offset + length]
        offset += length

        connect_params["will_topic"] = will_topic
        connect_params["will_message"] = will_message

    if username_flag:
        length = int.from_bytes(message[offset : offset + 2], byteorder="big")
        offset += 2
        username = message[offset : offset + length]
        offset += length

        connect_params["username"] = username

    if password_flag:
        length = int.from_bytes(message[offset : offset + 2], byteorder="big")
        offset += 2
        password = message[offset : offset + length]
        offset += length

        connect_params["password"] = password

    return connect_params


def create_mqtt_connect_packet(
    client_id: str,
    keep_alive: int = 60,
    username: str = None,
    password: str = None,
    clean_session: bool = True,
    will_topic: str = None,
    will_message: str = None,
    will_qos: MQTTQoSLevel = MQTTQoSLevel.AT_MOST_ONCE,
    will_retain: bool = False,
) -> bytes:
    """
    Create an MQTT CONNECT packet.

    Args:
        client_id (str): Client identifier.
        keep_alive (int): Keep-alive time in seconds (default is 60).
        username (str): Optional username for authentication.
        password (str): Optional password for authentication.
        clean_session (bool): Whether to start a clean session (default is True).
        will_topic (str): Optional last will topic.
        will_message (str): Optional last will message.
        will_qos (int): QoS level for the last will (default is 0).
        will_retain (bool): Whether to retain the last will message (default is False).

    Returns:
        bytes: Encoded MQTT CONNECT packet.
    """
    # Fixed header
    packet_type_and_flags = 0x10  # CONNECT packet (type=1, flags=0000)

    # Variable header
    variable_header = b""
    variable_header += b"\x00\x04MQTT"  # Protocol name
    variable_header += b"\x04"  # Protocol level (MQTT v3.1.1)

    connect_flags = 0
    if clean_session:
        connect_flags |= 0x02  # Set the clean session flag
    if will_topic and will_message:
        connect_flags |= 0x04 | (will_qos << 3) | (will_retain << 5)  # Will flag, QoS, and retain
    if username:
        connect_flags |= 0x80  # Username flag
    if password:
        connect_flags |= 0x40  # Password flag

    variable_header += bytes([connect_flags])
    variable_header += keep_alive.to_bytes(2, byteorder="big")  # Keep alive

    # Payload
    payload = b""
    payload += len(client_id).to_bytes(2, byteorder="big") + client_id.encode("utf-8")  # Client ID
    if will_topic and will_message:
        payload += len(will_topic).to_bytes(2, byteorder="big") + will_topic.encode("utf-8")
        payload += len(will_message).to_bytes(2, byteorder="big") + will_message.encode("utf-8")
    if username:
        payload += len(username).to_bytes(2, byteorder="big") + username.encode("utf-8")
    if password:
        payload += len(password).to_bytes(2, byteorder="big") + password.encode("utf-8")

    # Remaining length
    remaining_length = len(variable_header) + len(payload)
    remaining_length_bytes = encode_remaining_length(remaining_length)

    # Combine fixed header, remaining length, variable header, and payload
    packet = bytes([packet_type_and_flags]) + remaining_length_bytes + variable_header + payload
    return packet


def create_mqtt_subscribe_packet(packet_id: int, subscriptions: dict) -> bytes:
    """
    Create an MQTT SUBSCRIBE packet.

    Args:
        packet_id (int): Packet Identifier, unique for the session.
        subscriptions (dict): A dictionary mapping topic names (str) to QoS levels (0, 1, or 2).

    Returns:
        bytes: Encoded MQTT SUBSCRIBE packet.
    """
    # Fixed header
    packet_type_and_flags = 0x82  # SUBSCRIBE packet (type=8, flags=0010 for QoS 1)

    # Variable header
    variable_header = packet_id.to_bytes(2, byteorder="big")  # Packet Identifier

    # Payload
    payload = b""
    for topic, qos in subscriptions.items():
        if not (0 <= qos <= 2):
            raise ValueError(f"Invalid QoS level: {qos}")
        payload += len(topic).to_bytes(2, byteorder="big") + topic.encode("utf-8")  # Topic Name
        payload += bytes([qos])  # Requested QoS

    # Remaining length
    remaining_length = len(variable_header) + len(payload)
    remaining_length_bytes = encode_remaining_length(remaining_length)

    # Combine fixed header, remaining length, variable header, and payload
    packet = bytes([packet_type_and_flags]) + remaining_length_bytes + variable_header + payload
    return packet


def analyze_mqtt_subscribe_packet(variable_header_and_payload: bytes):
    """
    The SUBSCRIBE Packet is sent from the Client to the Server to create one or more Subscriptions.

    Each Subscription registers a Client’s interest in one or more Topics.

    Args:
        variable_header_and_payload: Variable header + Payload of SUBSCRIBE MQTT Packet.
    """

    # Variable Header
    # Message Identifier : 2 bytes
    message_id = int.from_bytes(variable_header_and_payload[0:2], byteorder="big")
    subscription_details = {"packet_id": message_id, "subscriptions": []}

    # Payload - The maximum QoS for each Subscription
    offset = 2
    while offset < len(variable_header_and_payload):
        # Read the topic name length (2 bytes)
        topic_length = int.from_bytes(variable_header_and_payload[offset : offset + 2], byteorder="big")
        offset += 2

        # Read the topic name
        topic = variable_header_and_payload[offset : offset + topic_length].decode("utf-8")
        offset += topic_length

        # Read the QoS (1 byte)
        qos = variable_header_and_payload[offset]
        offset += 1
        subscription_details["subscriptions"].append({"topic": topic, "qos": qos})

    if not subscription_details["subscriptions"]:
        # The payload of a SUBSCRIBE packet MUST contain at least one Topic Filter / QoS pair.
        raise ProtocolViolation("A SUBSCRIBE packet with no payload is a protocol violation")

    return subscription_details


def analyze_mqtt_publish_packet(packet_type_and_flags: int, variable_header_and_payload: bytes):
    """
    PUBLISH – Publish message

    A PUBLISH Control Packet is sent from a Client to a Server or from Server to a Client
    to transport an Application Message.

    Args:
        packet_type_and_flags: The first bytes of packet.
        variable_header_and_payload: Variable header + Payload of SUBSCRIBE MQTT Packet.
    """

    # Note: Unlike other analyze_mqtt_*_packet functions, this one requires
    # the first byte (packet_type_and_flags) to parse publish-specific details.

    qos = (packet_type_and_flags & 0b00000110) >> 1  # Flags QoS (bits 1-2)
    retain = bool(packet_type_and_flags & 0b00000001)  # Flag retain (bit 0)
    dup = bool(packet_type_and_flags & 0b00001000)  # Flag DUP (bit 3)

    # Variable header: Topic Name
    offset = 0
    topic_length = int.from_bytes(variable_header_and_payload[offset : offset + 2], byteorder="big")
    offset += 2
    topic_name = variable_header_and_payload[offset : offset + topic_length].decode("utf-8")
    offset += topic_length

    # If QoS > 0, Packet Identifier is present.
    packet_id = None
    if qos > 0:
        packet_id = int.from_bytes(variable_header_and_payload[offset : offset + 2], byteorder="big")
        offset += 2

    # Payload
    payload = variable_header_and_payload[offset:]

    publish_data = {
        "topic_name": topic_name,
        "qos": qos,
        "retain": retain,
        "dup": dup,
        "payload": payload,
    }

    if packet_id is not None:
        publish_data["packet_id"] = packet_id

    return publish_data


def analyze_mqtt_unsubscribe_packet(variable_header_and_payload: bytes):
    """
    Unsubscribe from topics

    An UNSUBSCRIBE Packet is sent by the Client to the Server, to unsubscribe from topics.

    Args:
        variable_header_and_payload: Variable header + Payload of SUBSCRIBE MQTT Packet.
    """
    # Variable header
    # Packet Identifier
    packet_id = int.from_bytes(variable_header_and_payload[:2], byteorder="big")
    offset = 2

    # Payload
    topics = []
    while offset < len(variable_header_and_payload):
        topic_length = int.from_bytes(variable_header_and_payload[offset : offset + 2], byteorder="big")
        offset += 2
        # Topic Filter
        topic = variable_header_and_payload[offset : offset + topic_length].decode("utf-8")
        offset += topic_length
        topics.append(topic)

    return {"packet_id": packet_id, "topics": topics}


def create_mqtt_suback_packet(packet_id: int, qos_levels: list[MQTTQoSLevel]):
    """
    Create SUBACK paquet

    A SUBACK Packet is sent by the Server to the Client to confirm
    receipt and processing of a SUBSCRIBE Packet.

    - packet_id: Packet Identifier from the SUBSCRIBE.
    - qos_levels:
        1: At most once delivery
        2: At least once delivery
        3: Exactly once delivery
        128: Failure
    """
    # Fixed Header
    remaining_length = 2 + len(qos_levels)  # 2 bytes (Variable Header) + Payload.
    packet = bytearray(2 + remaining_length)

    # Fixed header
    packet[0] = 0x90  # Type SUBACK
    packet[1] = remaining_length

    # Variable header (Packet Identifier)
    packet[2:4] = packet_id.to_bytes(2, "big")

    # Payload (QoS list)
    packet[4:] = qos_levels
    return bytes(packet)


def create_mqtt_pingresp_packet() -> bytes:
    """
    Create PINGRESP paquet.
    """
    return b"\xD0\x00"


def create_mqtt_unsuback_packet(packet_id: int) -> bytes:
    """
    Create UNSUBACK paquet

    - packet_id: Packet Identifier from the SUBSCRIBE.
    """

    # Fixed Header + Variable Header (Packet Identifier)
    return b"\xb0\x02" + packet_id.to_bytes(2, "big")


def create_mqtt_publish_packet(
    topic: str,
    payload: str,
    qos: MQTTQoSLevel = MQTTQoSLevel.AT_MOST_ONCE,
    retain: bool = False,
    packet_id: int = None,
):
    """
    Create A PUBLISH Packet

    A PUBLISH Packet is sent from Server to a Client to transport an Application Message.

    Args:
        topic: The name of topic.
        payload: The  message to publish.
        qos: QoS Level (0, 1 or 2).
        retain: The Server MUST store the Application Message.
        packet_id: Packet Identifier.

    """
    # Fixed Header
    packet_type = 0x30  # PUBLISH
    flags = (qos << 1) | retain  # QoS flag.
    fixed_header_byte1 = packet_type | flags

    # Variable Header - Topic Name.
    topic_bytes = topic.encode("utf-8")
    topic_length = len(topic_bytes).to_bytes(2, byteorder="big")
    variable_header = topic_length + topic_bytes

    # Add the packet identifier (For QoS 1 or 2)
    if qos > 0:
        if packet_id is None:
            raise ValueError("Message ID is required for QoS levels 1 and 2.")
        variable_header += packet_id.to_bytes(2, byteorder="big")

    # Payload
    payload_bytes = payload.encode("utf-8")

    # Compute the remaining length (Variable Header + Payload)
    remaining_length = len(variable_header) + len(payload_bytes)

    remaining_length_bytes = encode_remaining_length(remaining_length)

    # Whole Fixed Header
    fixed_header = bytes([fixed_header_byte1]) + remaining_length_bytes

    # Return the whole packet.
    return fixed_header + variable_header + payload_bytes


def create_mqtt_connack_packet(session_present: bool, return_code: MQTTConnAckReturnCode) -> bytes:
    """
    Create MQTT CONNACK  paquet

    Args:
    - session_present
    - return_code:
        - 0x00 Connection accepted
        - 0x01 Connection Refused, unacceptable protocol version
        - 0x02 The Client identifier is correct UTF-8 but not allowed by the Server
        - 0x03 The Network Connection has been made but the MQTT service is unavailable
        - 0x04 The data in the username or password is malformed
        - 0x05 The Client is not authorized to connect

    Returns:
    - bytes: Le paquet CONNACK en bytes.
    """
    packet_type = 0x20  # Type de paquet pour CONNACK est 0x20 (0010 0000 en binaire)
    remaining_length = 2  # La longueur fixe du champ variable header est 2 octets

    # Variable Header
    connect_ack_flags = 0x01 if session_present else 0x00  # 1 bit pour session présente
    variable_header = bytes([connect_ack_flags, return_code])

    # Fixed Header
    fixed_header = bytes([packet_type, remaining_length])

    return fixed_header + variable_header


async def analyze_mqtt_packet(packet, mq_backend: MQBackend):
    packet_type = packet.packet_type

    if packet_type == 1:  # CONNECT
        # Client requests a connection to a Server
        data = analyze_mqtt_connect_packet(packet.variable_header_and_payload)
        if await mq_backend.connect(data.get("username", "")):
            return create_mqtt_connack_packet(
                session_present=False,
                return_code=MQTTConnAckReturnCode.CONNECTION_ACCEPTED,
            )
        else:
            return create_mqtt_connack_packet(
                session_present=False, return_code=MQTTConnAckReturnCode.NOT_AUTHORIZED
            )

    elif packet_type == 2:  # CONNACK
        raise ProtocolViolation("The server should not received the MQTT CONNACK packet.")

    elif packet_type == 3:  # PUBLISH
        data = analyze_mqtt_publish_packet(packet.packet_type_and_flags, packet.variable_header_and_payload)
        # If we want echo the message to remote subscribers.
        # await mq_backend.publish(data["topic_name"], packet_type.to_bytes() + message)
        await mq_backend.notify_local_subscribers(data["topic_name"], data["payload"])
        return None

    elif packet_type == 4:  # PUBACK
        pass  # Ignored, PUBACK packet should not be sent by the client. (QoS 1)

    elif packet_type == 5:  # PUBREC
        pass  # Ignored, PUBREC packet should not be sent by the client. (QoS 2)

    elif packet_type == 6:  # PUBREL
        raise ProtocolViolation("The server should not received the MQTT PUBREL packet.")

    elif packet_type == 7:  # PUBCOMP
        pass  # Ignored, PUBCOMP packet should not be sent by the client. (QoS 2)

    elif packet_type == 8:  # SUBSCRIBE
        subscriptions = analyze_mqtt_subscribe_packet(packet.variable_header_and_payload)
        topic_to_subscribe = [subscription["topic"] for subscription in subscriptions["subscriptions"]]
        qos = []
        for topic in topic_to_subscribe:
            if await mq_backend.subscribe(topic):
                qos.append(MQTTQoSLevel.AT_MOST_ONCE)
            else:
                qos.append(MQTTQoSLevel.FAILURE)
        return create_mqtt_suback_packet(subscriptions["packet_id"], qos)

    elif packet_type == 9:  # SUBACK
        raise ProtocolViolation("The server should not received the MQTT SUBACK packet.")

    elif packet_type == 10:  # UNSUBSCRIBE
        unsubscribe_data = analyze_mqtt_unsubscribe_packet(packet.variable_header_and_payload)
        packet_id = unsubscribe_data["packet_id"]
        topics = unsubscribe_data["topics"]
        for topic in topics:
            await mq_backend.unsubscribe(topic)
        return create_mqtt_unsuback_packet(packet_id)

    elif packet_type == 11:  # UNSUBACK
        raise ProtocolViolation("The server should not received the MQTT UNSUBACK packet.")

    elif packet_type == 12:  # PINGREQ
        # Nothing to analyse, PINGREQ doesn't have a Variable header or a Payload.
        return create_mqtt_pingresp_packet()

    elif packet_type == 13:  # PINGRESP
        raise ProtocolViolation("The server should not received the MQTT PINGRESP packet.")

    elif packet_type == 14:  # DISCONNECT
        raise CloseWSConnection()
    else:
        raise ProtocolViolation("Unexpected packet type")


class MQTTPacket:
    """
    Represents a parsed MQTT packet with its type and payload.
    """

    def __init__(self, packet, payload_start):
        self.packet = memoryview(packet)
        self.payload_start = payload_start
        self.packet_type_and_flags = packet[0]
        self.variable_header_and_payload = packet[payload_start:]
        self.packet_type: int = (packet[0] >> 4) & 0x0F

    # def __repr__(self):
    #    return f"<MQTTPacket type={self.packet_type_and_flags} payload_length={len(self.variable_header_and_payload)}>"


class MQTTPacketAssembler:
    """
    Handles buffering and reconstruction of MQTT packets from WebSocket fragments.
    """

    def __init__(self):
        self._buffer = b""
        self._total_length = 0
        self._start_payload = 0

    def append_fragment(self, fragment: bytes) -> MQTTPacket:
        """
        Add a WebSocket fragment to the buffer and check if a complete MQTT packet can be extracted.

        Args:
            fragment: A WebSocket fragment containing part of an MQTT packet.

        Returns:
            Optional[bytes]: A complete MQTT packet if available, otherwise None.
        """
        self._buffer += fragment
        if len(self._buffer) < 2:
            return None

        # Calculate the total packet length if not already determined
        if self._total_length == 0:
            remaining_length, num_bytes = decode_remaining_length(self._buffer[1:])
            self._start_payload = 1 + num_bytes
            self._total_length = self._start_payload + remaining_length

        # Check if we have received enough data for a complete packet
        if len(self._buffer) < self._total_length:
            return None

        # Extract the full packet and reset for the next one
        packet = MQTTPacket(self._buffer[: self._total_length], self._start_payload)
        self._buffer = self._buffer[self._total_length :]
        self._total_length = 0
        self._start_payload = 0
        return packet


class MQTT(WSSubProtocol):

    sub_protocol_name = "mqtt"

    def __init__(self, mq_backend: MQBackend):
        super().__init__(mq_backend)
        self._assembler = MQTTPacketAssembler()

    async def read_ws_packet(self, msg: WSMessage):
        if msg.type == WSMsgType.BINARY:
            # Process the incoming WebSocket fragment
            packet = self._assembler.append_fragment(msg.data)
            if packet is None:
                return  # Wait for more fragments

            # Pass the complete MQTT packet for analysis
            response = await analyze_mqtt_packet(packet, self._mq_backend)
            if response is not None:
                await ws_context.get().send_bytes(response)

        else:
            raise Exception(f"Unsupported WebSocket message type: {msg.type}")
        """
        elif msg.type == WSMsgType.ERROR:
            self._ws.exception()

        else:
            await self._ws.close()
        """

    async def publish(self, topic: str, payload: str):
        """
        Publish a message to a topic. Handles the encoding and dispatch.
        """
        mqtt_packet = create_mqtt_publish_packet(topic, payload)
        await self._mq_backend.publish(topic, mqtt_packet.decode("utf-8"))
