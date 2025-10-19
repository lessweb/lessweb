import json

from aiohttp_middlewares.cors import cors_middleware
from shared.auth_gateway.auth_gateway import AuthGatewayMiddleware
from shared.error.error_middleware import error_middleware
from shared.lessweb_commondao.lessweb_plugin import MysqlConn, commondao_bean
from shared.redis.redis_plugin import redis_bean

from lessweb import Bridge


def update_openapi(components):
    openapi_json = json.loads(open('public/openapi.json').read())
    openapi_json.update(components)
    with open('public/openapi.json', 'w') as f:
        f.write(json.dumps(openapi_json, indent=2, ensure_ascii=False))


def main():
    bridge = Bridge('config')
    bridge.app.router.add_static(prefix='/public/', path='public')
    bridge.beans(commondao_bean, redis_bean)
    bridge.middlewares(
        cors_middleware(allow_all=True),
        error_middleware,
        MysqlConn,
        AuthGatewayMiddleware
    )
    bridge.scan('src')
    update_openapi(bridge.dump_openapi_components())
    bridge.run_app()


if __name__ == '__main__':
    main()
