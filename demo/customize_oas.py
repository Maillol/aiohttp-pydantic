from typing import Union

from aiohttp import web

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200

from .model import Error, Pet


DOG_DESCRIPTION = '''# Good boy

This pet is a good boy and deserves lots of pets
'''


def add_custom_dog_example(oas, oas_path, view, oas_operation):
    oas.components.examples.setdefault('dog-example', {
            'summary': 'A detailed listing for a dog',
            'value': DOG_DESCRIPTION,
        })

    oas_operation.responses[200].content = {
            'text/markdown': {
                'examples': {
                    'dog': {
                        '$ref': '#/components/examples/dog-example'
                    }
                }
            }
        }

    return func


class PetDetailsView(PydanticView):
    async def get(self, id: int, /) -> r200:
        """
        Show a detailed listing describing the pet.

        Status Codes:
            200: The description for the pet was found
            404: Pet not found
        """
        pet = self.request.app["model"].find_pet(id)
        body = DOG_DESCRIPTION
        return web.Response(content_type='text/markdown', body=body)


    get.__modify_schema__ = add_custom_dog_example
