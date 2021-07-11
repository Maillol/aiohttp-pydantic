import pytest

from aiohttp_pydantic.oas.struct import OpenApiSpec3


def test_info_title():
    oas = OpenApiSpec3()
    assert oas.info.title == "Aiohttp pydantic application"
    oas.info.title = "Info Title"
    assert oas.info.title == "Info Title"
    assert oas.spec == {
        "info": {
            "title": "Info Title",
            "version": "1.0.0",
        },
        "openapi": "3.0.0",
    }


def test_info_description():
    oas = OpenApiSpec3()
    assert oas.info.description is None
    oas.info.description = "info description"
    assert oas.info.description == "info description"
    assert oas.spec == {
        "info": {
            "description": "info description",
            "title": "Aiohttp pydantic application",
            "version": "1.0.0",
        },
        "openapi": "3.0.0",
    }


def test_info_version():
    oas = OpenApiSpec3()
    assert oas.info.version == "1.0.0"
    oas.info.version = "3.14"
    assert oas.info.version == "3.14"
    assert oas.spec == {
        "info": {"version": "3.14", "title": "Aiohttp pydantic application"},
        "openapi": "3.0.0",
    }


def test_info_terms_of_service():
    oas = OpenApiSpec3()
    assert oas.info.terms_of_service is None
    oas.info.terms_of_service = "http://example.com/terms/"
    assert oas.info.terms_of_service == "http://example.com/terms/"
    assert oas.spec == {
        "info": {
            "title": "Aiohttp pydantic application",
            "version": "1.0.0",
            "termsOfService": "http://example.com/terms/",
        },
        "openapi": "3.0.0",
    }


@pytest.mark.skip("Not yet implemented")
def test_info_license():
    oas = OpenApiSpec3()
    oas.info.license.name = "Apache 2.0"
    oas.info.license.url = "https://www.apache.org/licenses/LICENSE-2.0.html"
    assert oas.spec == {
        "info": {
            "license": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            }
        },
        "openapi": "3.0.0",
    }
