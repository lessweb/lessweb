import aiohttp
from aiohttp.web import Request, Application, WebSocketResponse

from lessweb import Bridge, service, get_mapping


@service
class WhoCache:
    def __init__(self):
        self.who = '-'

    def get(self):
        return self.who

    def set(self, who: str):
        self.who = who


@get_mapping('/ws')
async def websocket_dealer(request: Request, who_cache: WhoCache):
    print('Websocket connection starting')
    ws = WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection ready')

    async for msg in ws:
        print(msg)
        if msg.type == aiohttp.WSMsgType.TEXT:
            print(msg.data)
            if msg.data == 'close':
                await ws.close()
            else:
                who = who_cache.get()
                await ws.send_str(f'{msg.data}@{who}')

    print('Websocket connection closed')
    return ws


@get_mapping('/set')
async def edit_who(who_cache: WhoCache, *, who: str):
    who_cache.set(who)
    return {'success': True}


if __name__ == '__main__':
    bridge = Bridge()
    bridge.app['who_cache'] = WhoCache()
    bridge.add_route(websocket_dealer)
    bridge.add_route(edit_who)
    bridge.run_app()