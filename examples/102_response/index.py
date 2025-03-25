from datetime import date
from enum import Enum
from typing import Annotated

from aiohttp.web import Request
from pydantic import BaseModel

from lessweb.annotation import Get, Post


class PetKind(Enum):
    CAT = 'CAT'
    DOG = 'DOG'


class Pet(BaseModel):
    pet_id: int
    name: str
    kind: PetKind
    birthday: date


async def get_pet_detail(request: Request, *, pet_id: int, kind: list[PetKind] = None) -> Annotated[dict, Get('/pet/{pet_id}')]:
    return {
        'name': request.query['name'],
        'pet_id': pet_id,
        'kind': kind
    }


async def create_pet(pet: Pet, /) -> Annotated[dict, Post('/pet')]:
    return pet


if __name__ == '__main__':
    from lessweb import Bridge
    bridge = Bridge()
    bridge.scan(get_pet_detail, create_pet)
    bridge.run_app()
