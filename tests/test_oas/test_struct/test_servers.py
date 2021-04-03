import pytest

from aiohttp_pydantic.oas.struct import OpenApiSpec3


def test_sever_url():
    oas = OpenApiSpec3()
    oas.servers[0].url = "https://development.gigantic-server.com/v1"
    oas.servers[1].url = "https://development.gigantic-server.com/v2"
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "servers": [
            {"url": "https://development.gigantic-server.com/v1"},
            {"url": "https://development.gigantic-server.com/v2"},
        ],
    }


def test_sever_description():
    oas = OpenApiSpec3()
    oas.servers[0].url = "https://development.gigantic-server.com/v1"
    oas.servers[0].description = "Development server"
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "servers": [
            {
                "url": "https://development.gigantic-server.com/v1",
                "description": "Development server",
            }
        ],
    }


@pytest.mark.skip("Not yet implemented")
def test_sever_variables():
    oas = OpenApiSpec3()
