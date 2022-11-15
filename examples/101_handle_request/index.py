from lessweb import Bridge, get_mapping, post_mapping, rest_mapping
from aiohttp.web import Request

@rest_mapping('GET', '/pet/{pet_id}')
async def get_pet_detail(request: Request):
    return {'pet_id': request.match_info['pet_id']}

@get_mapping('/pet')
async def get_pet_list(request: Request):  #注意必须用async，否则访问时会报错
    return {'name': request.query['name']}

@post_mapping('/pet')
async def create_pet(request: Request):
    pet = await request.json()
    return pet

if __name__ == '__main__':
    bridge = Bridge()
    bridge.add_route(get_pet_detail)
    bridge.add_route(get_pet_list)
    bridge.add_route(create_pet)
    bridge.run_app()