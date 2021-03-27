Aiohttp pydantic - Aiohttp View to validate and parse request
=============================================================

.. image:: https://travis-ci.org/Maillol/aiohttp-pydantic.svg?branch=main
  :target: https://travis-ci.org/Maillol/aiohttp-pydantic

.. image:: https://img.shields.io/pypi/v/aiohttp-pydantic
  :target: https://img.shields.io/pypi/v/aiohttp-pydantic
  :alt: Latest PyPI package version

.. image:: https://codecov.io/gh/Maillol/aiohttp-pydantic/branch/main/graph/badge.svg
  :target: https://codecov.io/gh/Maillol/aiohttp-pydantic
  :alt: codecov.io status for master branch

Aiohttp pydantic is an `aiohttp view`_ to easily parse and validate request.
You define using the function annotations what your methods for handling HTTP verbs expects and Aiohttp pydantic parses the HTTP request
for you, validates the data, and injects that you want as parameters.


Features:

- Query string, request body, URL path and HTTP headers validation.
- Open API Specification generation.


How to install
--------------

.. code-block:: bash

    $ pip install aiohttp_pydantic

Example:
--------

.. code-block:: python3

    from typing import Optional

    from aiohttp import web
    from aiohttp_pydantic import PydanticView
    from pydantic import BaseModel

    # Use pydantic BaseModel to validate request body
    class ArticleModel(BaseModel):
        name: str
        nb_page: Optional[int]


    # Create your PydanticView and add annotations.
    class ArticleView(PydanticView):

        async def post(self, article: ArticleModel):
            return web.json_response({'name': article.name,
                                      'number_of_page': article.nb_page})

        async def get(self, with_comments: bool=False):
            return web.json_response({'with_comments': with_comments})


    app = web.Application()
    app.router.add_view('/article', ArticleView)
    web.run_app(app)


.. code-block:: bash

    $ curl -X GET http://127.0.0.1:8080/article?with_comments=a
    [
      {
        "in": "query string",
        "loc": [
          "with_comments"
        ],
        "msg": "value could not be parsed to a boolean",
        "type": "type_error.bool"
      }
    ]

    $ curl -X GET http://127.0.0.1:8080/article?with_comments=yes
    {"with_comments": true}

    $ curl -H "Content-Type: application/json" -X post http://127.0.0.1:8080/article --data '{}'
    [
      {
        "in": "body",
        "loc": [
          "name"
        ],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]

    $ curl -H "Content-Type: application/json" -X post http://127.0.0.1:8080/article --data '{"name": "toto", "nb_page": "3"}'
    {"name": "toto", "number_of_page": 3}

API:
----

Inject Path Parameters
~~~~~~~~~~~~~~~~~~~~~~

To declare a path parameter, you must declare your argument as a `positional-only parameters`_:


Example:

.. code-block:: python3

    class AccountView(PydanticView):
        async def get(self, customer_id: str, account_id: str, /):
            ...

    app = web.Application()
    app.router.add_get('/customers/{customer_id}/accounts/{account_id}', AccountView)

Inject Query String Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To declare a query parameter, you must declare your argument as a simple argument:


.. code-block:: python3

    class AccountView(PydanticView):
        async def get(self, customer_id: Optional[str] = None):
            ...

    app = web.Application()
    app.router.add_get('/customers', AccountView)


A query string parameter is generally optional and we do not want to force the user to set it in the URL.
It's recommended to define a default value. It's possible to get a multiple value for the same parameter using
the List type

.. code-block:: python3

    class AccountView(PydanticView):
        async def get(self, tags: List[str] = []):
            ...

    app = web.Application()
    app.router.add_get('/customers', AccountView)


Inject Request Body
~~~~~~~~~~~~~~~~~~~

To declare a body parameter, you must declare your argument as a simple argument annotated with `pydantic Model`_.


.. code-block:: python3

    class Customer(BaseModel):
        first_name: str
        last_name: str

    class CustomerView(PydanticView):
        async def post(self, customer: Customer):
            ...

    app = web.Application()
    app.router.add_view('/customers', CustomerView)

Inject HTTP headers
~~~~~~~~~~~~~~~~~~~

To declare a HTTP headers parameter, you must declare your argument as a `keyword-only argument`_.


.. code-block:: python3

    class CustomerView(PydanticView):
        async def get(self, *, authorization: str, expire_at: datetime):
            ...

    app = web.Application()
    app.router.add_view('/customers', CustomerView)


.. _positional-only parameters: https://www.python.org/dev/peps/pep-0570/
.. _pydantic Model: https://pydantic-docs.helpmanual.io/usage/models/
.. _keyword-only argument: https://www.python.org/dev/peps/pep-3102/

Add route to generate Open Api Specification (OAS)
--------------------------------------------------

aiohttp_pydantic provides a sub-application to serve a route to generate Open Api Specification
reading annotation in your PydanticView. Use *aiohttp_pydantic.oas.setup()* to add the sub-application

.. code-block:: python3

    from aiohttp import web
    from aiohttp_pydantic import oas


    app = web.Application()
    oas.setup(app)

By default, the route to display the Open Api Specification is /oas but you can change it using
*url_prefix* parameter


.. code-block:: python3

    oas.setup(app, url_prefix='/spec-api')

If you want generate the Open Api Specification from specific aiohttp sub-applications.
on the same route, you must use *apps_to_expose* parameter.


.. code-block:: python3

    from aiohttp import web
    from aiohttp_pydantic import oas

    app = web.Application()
    sub_app_1 = web.Application()
    sub_app_2 = web.Application()

    oas.setup(app, apps_to_expose=[sub_app_1, sub_app_2])

Add annotation to define response content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The module aiohttp_pydantic.oas.typing provides class to annotate a
response content.

For example *r200[List[Pet]]* means the server responses with
the status code 200 and the response content is a List of Pet where Pet will be
defined using a pydantic.BaseModel

The docstring of methods will be parsed to fill the descriptions in the
Open Api Specification.


.. code-block:: python3

    from aiohttp_pydantic import PydanticView
    from aiohttp_pydantic.oas.typing import r200, r201, r204, r404


    class Pet(BaseModel):
        id: int
        name: str


    class Error(BaseModel):
        error: str


    class PetCollectionView(PydanticView):
        async def get(self) -> r200[List[Pet]]:
            """
            Find all pets
            """
            pets = self.request.app["model"].list_pets()
            return web.json_response([pet.dict() for pet in pets])

        async def post(self, pet: Pet) -> r201[Pet]:
            """
            Add a new pet to the store

            Status Codes:
                201: The pet is created
            """
            self.request.app["model"].add_pet(pet)
            return web.json_response(pet.dict())


    class PetItemView(PydanticView):
        async def get(self, id: int, /) -> Union[r200[Pet], r404[Error]]:
            """
            Find a pet by ID

            Status Codes:
                200: Successful operation
                404: Pet not found
            """
            pet = self.request.app["model"].find_pet(id)
            return web.json_response(pet.dict())

        async def put(self, id: int, /, pet: Pet) -> r200[Pet]:
            """
            Update an existing pet

            Status Codes:
                200: successful operation
            """
            self.request.app["model"].update_pet(id, pet)
            return web.json_response(pet.dict())

        async def delete(self, id: int, /) -> r204:
            self.request.app["model"].remove_pet(id)
            return web.Response(status=204)

Demo
----

Have a look at `demo`_ for a complete example

.. code-block:: bash

    git clone https://github.com/Maillol/aiohttp-pydantic.git
    cd aiohttp-pydantic
    pip install .
    python -m demo

Go to http://127.0.0.1:8080/oas

You can generate the OAS in a json or yaml file using the aiohttp_pydantic.oas command:

.. code-block:: bash

    python -m aiohttp_pydantic.oas demo.main

.. code-block:: bash

    $ python3 -m aiohttp_pydantic.oas  --help
    usage: __main__.py [-h] [-b FILE] [-o FILE] [-f FORMAT] [APP [APP ...]]

    Generate Open API Specification

    positional arguments:
      APP                   The name of the module containing the asyncio.web.Application. By default the variable named
                            'app' is loaded but you can define an other variable name ending the name of module with :
                            characters and the name of variable. Example: my_package.my_module:my_app If your
                            asyncio.web.Application is returned by a function, you can use the syntax:
                            my_package.my_module:my_app()

    optional arguments:
      -h, --help            show this help message and exit
      -b FILE, --base-oas-file FILE
                            A file that will be used as base to generate OAS
      -o FILE, --output FILE
                            File to write the output
      -f FORMAT, --format FORMAT
                            The output format, can be 'json' or 'yaml' (default is json)


.. _demo: https://github.com/Maillol/aiohttp-pydantic/tree/main/demo
.. _aiohttp view: https://docs.aiohttp.org/en/stable/web_quickstart.html#class-based-views
