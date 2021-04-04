from aiohttp_pydantic.oas.struct import OpenApiSpec3


def test_paths_description():
    oas = OpenApiSpec3()
    oas.paths["/users/{id}"].description = "This route ..."
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {"/users/{id}": {"description": "This route ..."}},
    }


def test_paths_get():
    oas = OpenApiSpec3()
    oas.paths["/users/{id}"].get
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {"/users/{id}": {"get": {}}},
    }


def test_paths_operation_description():
    oas = OpenApiSpec3()
    operation = oas.paths["/users/{id}"].get
    operation.description = "Long descriptions ..."
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {"/users/{id}": {"get": {"description": "Long descriptions ..."}}},
    }


def test_paths_operation_summary():
    oas = OpenApiSpec3()
    operation = oas.paths["/users/{id}"].get
    operation.summary = "Updates a pet in the store with form data"
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {
            "/users/{id}": {
                "get": {"summary": "Updates a pet in the store with form data"}
            }
        },
    }


def test_paths_operation_parameters():
    oas = OpenApiSpec3()
    operation = oas.paths["/users/{petId}"].get
    parameter = operation.parameters[0]
    parameter.name = "petId"
    parameter.description = "ID of pet that needs to be updated"
    parameter.in_ = "path"
    parameter.required = True

    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {
            "/users/{petId}": {
                "get": {
                    "parameters": [
                        {
                            "description": "ID of pet that needs to be updated",
                            "in": "path",
                            "name": "petId",
                            "required": True,
                        }
                    ]
                }
            }
        },
    }


def test_paths_operation_requestBody():
    oas = OpenApiSpec3()
    request_body = oas.paths["/users/{petId}"].get.request_body
    request_body.description = "user to add to the system"
    request_body.content = {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/User"},
            "examples": {
                "user": {
                    "summary": "User Example",
                    "externalValue": "http://foo.bar/examples/user-example.json",
                }
            },
        }
    }
    request_body.required = True
    assert oas.spec == {
        "openapi": "3.0.0",
        "info": {"title": "Aiohttp pydantic application", "version": "1.0.0"},
        "paths": {
            "/users/{petId}": {
                "get": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "examples": {
                                    "user": {
                                        "externalValue": "http://foo.bar/examples/user-example.json",
                                        "summary": "User Example",
                                    }
                                },
                                "schema": {"$ref": "#/components/schemas/User"},
                            }
                        },
                        "description": "user to add to the system",
                        "required": True,
                    }
                }
            }
        },
    }


def test_paths_operation_responses():
    oas = OpenApiSpec3()
    response = oas.paths["/users/{petId}"].get.responses[200]
    response.description = "A complex object array response"
    response.content = {
        "application/json": {
            "schema": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/VeryComplexType"},
            }
        }
    }
