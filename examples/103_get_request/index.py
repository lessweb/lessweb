from aiohttp.web import Request
from datetime import date
from enum import Enum
from lessweb import get_mapping, post_mapping
from typing import TypedDict


class PetKind(Enum):
    CAT = 'CAT'
    DOG = 'DOG'


class Pet(TypedDict):
    pet_id: int
    name: str
    kind: PetKind
    birthday: date


@get_mapping('/pet/{pet_id}')
async def get_pet_detail(request: Request, *, pet_id: int, kind: list[PetKind] = None):
    return {
        'name': request.query['name'],
        'pet_id': pet_id,
        'kind': kind
    }


@post_mapping('/pet')
async def create_pet(pet: Pet, /):
    return pet


if __name__ == '__main__':
    from lessweb import Bridge
    bridge = Bridge()
    bridge.add_route(get_pet_detail)
    bridge.add_route(create_pet)
    bridge.run_app()