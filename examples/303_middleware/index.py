from lessweb import get_mapping, rest_response, Bridge


async def hook_a(handler):
    resp = await handler()
    return rest_response({'a': '[%s]' % resp['data']['a']})

async def hook_b(handler):
    resp = await handler()
    return rest_response({'a': '(%s)' % resp['data']['a']})

@get_mapping('/info')
async def controller(*, a: str):
    return {'a': a}

if __name__ == '__main__':
    bridge = Bridge()
    bridge.add_middleware(hook_a)
    bridge.add_middleware(hook_b)
    bridge.add_route(controller)
    bridge.run_app()