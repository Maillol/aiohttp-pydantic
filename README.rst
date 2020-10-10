Aiohttp pydantic - Aiohttp View to validate and parse request
=============================================================

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

        async def get(self, with_comments: Optional[bool]):
            return web.json_response({'with_comments': with_comments})


    app = web.Application()
    app.router.add_view('/article', ArticleView)
    web.run_app(app)


.. code-block:: bash

    $ curl -X GET http://127.0.0.1:8080/article?with_comments=a
    [
      {
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

To declare a path parameters, you must declare your argument as a `positional-only parameters`_:


Example:

.. code-block:: python3

    class AccountView(PydanticView):
        async def get(self, customer_id: str, account_id: str, /):
            ...

    app = web.Application()
    app.router.add_get('/customers/{customer_id}/accounts/{account_id}', AccountView)

Inject Query String Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To declare a query parameters, you must declare your argument as simple argument:


.. code-block:: python3

    class AccountView(PydanticView):
        async def get(self, customer_id: str):
            ...

    app = web.Application()
    app.router.add_get('/customers', AccountView)

Inject Request Body
~~~~~~~~~~~~~~~~~~~

To declare a body parameters, you must declare your argument as a simple argument annotated with `pydantic Model`_.


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

To declare a HTTP headers parameters, you must declare your argument as a `keyword-only argument`_.


.. code-block:: python3

    class CustomerView(PydanticView):
        async def get(self, *, authorization: str, expire_at: datetime):
            ...

    app = web.Application()
    app.router.add_view('/customers', CustomerView)


.. _positional-only parameters: https://www.python.org/dev/peps/pep-0570/
.. _pydantic Model: https://pydantic-docs.helpmanual.io/usage/models/
.. _keyword-only argument: https://www.python.org/dev/peps/pep-3102/
