from aiohttp import web
import aiohttp

from aiohttp_pydantic.ws_subprotocol.mqtt import analyze_mqtt_packet, decode_remaining_length, create_mqtt_suback_packet, create_mqtt_publish_packet


async def websocket_handler(request):

    buffer = b""

    ws = web.WebSocketResponse(protocols=["mqtt"])
    await ws.prepare(request)

    total_length = 0
    num_bytes = 0
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.BINARY:
            buffer += msg.data

            if len(buffer) < 2:
                continue
            elif total_length == 0:
                remaining_length, num_bytes = decode_remaining_length(buffer[1:])
                total_length = 1 + num_bytes + remaining_length

            # Vérifier si nous avons le paquet complet
            if len(buffer) < total_length:
                continue  # Attendre plus de fragments pour compléter le paquet


            print("\n\n")
            # Extraire le paquet complet du buffer
            full_packet = buffer[:total_length]
            packet_type = (full_packet[0] >> 4) & 0x0F
            buffer = buffer[total_length:]  # Reste du buffer

            # Appeler une fonction pour traiter le paquet MQTT
            query = await analyze_mqtt_packet(packet_type, full_packet[1 + num_bytes:])
            print(query)
            if packet_type == 1:
                await ws.send_bytes(b'\x20\x02\x00\x00')
            elif packet_type == 2:
                await ws.send_bytes(create_mqtt_suback_packet(query["packet_id"], [0]))
            else:
                await ws.send_bytes(create_mqtt_publish_packet(
                    topic="test",
                    payload="Salut"))
            total_length = 0
            num_bytes = 0

            # await ws.send_bytes()
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())
        else:
            print("The received WS msg type is unexpected type", msg.type)

    print('websocket connection closed')

    return ws



app = web.Application()
app.add_routes([web.get('/ws', websocket_handler)])
web.run_app(app)
