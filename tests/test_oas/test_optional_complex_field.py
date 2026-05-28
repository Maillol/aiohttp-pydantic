"""
Tests for OAS generation when a Pydantic model contains an optional field
whose type is itself a Pydantic model (i.e. the field is nullable and its
non-null schema is expressed as a $ref rather than a primitive type).

Pydantic v2 emits:

    {"anyOf": [{"$ref": "#/components/schemas/Engine"}, {"type": "null"}]}

The original pydantic_schema_to_oas_3_0 did ``element["type"]`` without a
guard, which raised KeyError on the $ref element and caused the /oas/spec
endpoint to return 500.

Even with the crash fixed, the default of "null" in .get("type", "null") means
the $ref element is mistakenly treated as the null branch.  The surviving anyOf
entry then becomes {"type": "null"}, so the field is documented as
``{"type": "null", "nullable": true}`` — the Engine reference is lost entirely.
"""

from aiohttp import web
from pydantic import BaseModel

from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.oas.typing import r201


class Engine(BaseModel):
    horsepower: int
    fuel_type: str


class Car(BaseModel):
    make: str
    engine: Engine | None = None


class CarView(PydanticView):
    async def post(self, car: Car) -> r201[Car]:
        return web.json_response()


def build_app():
    app = web.Application()
    app.router.add_view("/cars", CarView)
    oas.setup(app)
    return app


async def test_oas_endpoint_does_not_crash(aiohttp_client):
    client = await aiohttp_client(build_app())
    response = await client.get("/oas/spec")
    assert response.status == 200


async def test_engine_schema_is_registered(aiohttp_client):
    """Engine must appear as a named schema so it can be referenced."""
    client = await aiohttp_client(build_app())
    spec = await (await client.get("/oas/spec")).json()
    assert "Engine" in spec["components"]["schemas"]


async def test_optional_engine_field_references_engine_schema(aiohttp_client):
    """
    Car.engine is Engine | None, so it should be documented as a nullable
    reference to the Engine schema — not as {"type": "null"}.
    """
    client = await aiohttp_client(build_app())
    spec = await (await client.get("/oas/spec")).json()
    engine_field = spec["components"]["schemas"]["Car"]["properties"]["engine"]
    assert engine_field == {"$ref": "#/components/schemas/Engine", "nullable": True}
