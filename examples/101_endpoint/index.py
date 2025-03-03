from typing import Annotated

from aiohttp.web import Request

from lessweb import Bridge
from lessweb.annotation import Endpoint, Get, Post


async def get_pet_detail(request: Request) -> Annotated[dict, Endpoint('GET', '/pet/{pet_id}')]:
    return {'pet_id': request.match_info['pet_id']}


async def get_pet_list(request: Request) -> Annotated[dict, Get('/pet')]:
    return {'name': request.query['name']}


async def create_pet(request: Request) -> Annotated[dict, Post('/pet')]:
    pet = await request.json()
    return pet

if __name__ == '__main__':
    bridge = Bridge()
    bridge.scan(get_pet_detail, get_pet_list, create_pet)
    bridge.run_app()
