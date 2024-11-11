from pydantic import BaseModel
from aiohttp.web import Response, json_response, View

from .struct import AsyncAPISpec, Message

def generate_aas(publishers: dict[str, type[BaseModel]]) -> AsyncAPISpec:
    """
    Generate an AsyncAPI specification based on the provided publishers.

    Args:
        publishers (dict[str, type[pydantic.BaseModel]]): A dictionary where the keys are topic names
            and the values are Pydantic models defining the payload for the topic.

    Returns:
        AsyncAPISpec: The generated AsyncAPI specification.
    """
    async_api = AsyncAPISpec()

    # Add basic server information
    async_api.info.title = "MQTT Notifications"
    async_api.info.version = "1.0.0"
    async_api.info.description = "AsyncAPI specification for MQTT-based notifications."

    # Add a default server
    async_api.servers.add_server(
        name="production",
        url="mqtt://mqtt.example.com",
        protocol="mqtt",
        description="Production MQTT broker"
    )

    # Add channels for each publisher
    for topic, model in publishers.items():
        # Generate a sample payload schema from the Pydantic model
        payload_schema = model.schema()

        # Create the publish message
        publish_message = Message(
            content_type="application/json",
            summary=f"Message published on the {topic} topic",
            payload=payload_schema,
        ).to_dict()

        # Add the channel to the spec
        async_api.channels.add_channel(
            name=topic,
            description=f"Channel for the {topic} topic",
            publish_message=publish_message
        )

    return async_api


async def get_aas(request):
    """
    View to generate the Async Api Specification from publishers declared in WSApp.
    """
    # TODO:
    publishers = {}
    return json_response(generate_aas(publishers))

async def aas_ui(request):
    """
    View to serve the AsyncAPI React Component to read async api specification of application.
    """
    template = request.app["AAS INDEX TEMPLATE"]  # TODO: use key.

    return Response(
        text=template.render(
            {
                "asyncapi_spec_url": request.app.router['spec'].canonical,
                "title": request.app["AAS UI PAGE TITLE"],  # TODO use key.
                # TODO add updatable config.
            }
        ),
        content_type="text/html",
        charset="utf-8",
    )
