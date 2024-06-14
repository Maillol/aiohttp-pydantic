import pytest
from aiohttp import web
from aiohttp_pydantic import PydanticView, oas
from aiohttp_pydantic.oas.typing import r200

from .test_view import ensure_content_durability


class PetCollectionView(PydanticView):
    async def get(self) -> r200[str]:
        """
        Get a plain text list of pets

        Tags: pet
        Status Codes:
          200: Successful operation
        """
        return web.Response(content_type='text/plain', body='')


    def modify_schema(oas, oas_path, view, oas_operation):
        original = oas_operation.responses[200].content["application/json"]
        oas_operation.responses[200].content["text/plain"] = original
        del oas_operation.responses[200].content["application/json"]


    get.__modify_schema__ = modify_schema


@pytest.fixture
async def generated_oas(aiohttp_client, loop) -> web.Application:
    app = web.Application()
    app.router.add_view("/pets", PetCollectionView)
    oas.setup(app)

    return await ensure_content_durability(await aiohttp_client(app))


async def test_generated_oas_initialized_with_computed_schemas(generated_oas):
    assert "/pets" in generated_oas["paths"]
    assert generated_oas["paths"]["/pets"]["get"] == {
        "description": "Get a plain text list of pets",
        "tags": ["pet"],
        "responses": {
            "200": {
                "description": "Successful operation",
                "content": {
                    "text/plain": {
                        "schema": {}
                    }
                },
            }
        }
    }


