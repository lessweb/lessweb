from aiohttp.web import HTTPForbidden
from lessweb import get_mapping
from lessweb import rest_response
from aiohttp.web import Request, HTTPBadRequest
from lessweb import rest_error

@get_mapping('/')
async def example_for_response():
    raise HTTPForbidden(text='Access Denied')

@get_mapping('/pet')
async def get_pet_list_header():
    pet_list = [{'pet_id': 1, 'name': 'Kitty', 'kind': 'CAT'}]
    return rest_response(pet_list, headers={'X-TOKEN': 'abc123'})

@get_mapping('/pet/{pet_id}')
async def get_pet_list(request: Request):
    if not request.match_info['pet_id'].isdigit():
        raise rest_error(HTTPBadRequest, {'code': -1, 'message': 'Invalid pet_id'})
    return {'pet_id': 1, 'name': 'Kitty', 'kind': 'CAT'}


from dataclasses import dataclass
from datetime import date
from enum import Enum


class PetKind(Enum):
    CAT = 'CAT'
    DOG = 'DOG'


@dataclass
class Pet:
    pet_id: int
    name: str
    kind: PetKind
    birthday: date


@get_mapping('/pet')
async def get_pet_list():
    return [Pet(pet_id=123, name='Kitty', kind=PetKind.CAT, birthday=date(2000, 12, 31))]


if __name__ == '__main__':
    from lessweb import Bridge
    bridge = Bridge()
    # bridge.add_route(get_pet_list_header)
    # bridge.add_route(get_pet_list)
    bridge.run_app()
