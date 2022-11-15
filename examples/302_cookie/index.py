from aiohttp.web import Request, Response
from lessweb import Bridge, post_mapping, get_mapping

@post_mapping('/set')
async def set_user(*, name: str):
    resp = Response(text='ok', content_type='text/html', charset='utf-8')
    resp.set_cookie('username', name)
    return resp

@get_mapping('/get')
async def get_user(request: Request):
    username = request.cookies.get('username')
    return {'user': username}

if __name__ == '__main__':
    bridge = Bridge()
    bridge.add_route(set_user)
    bridge.add_route(get_user)
    bridge.run_app()