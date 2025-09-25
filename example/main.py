import json

from aiohttp_middlewares.cors import cors_middleware
from lessweb import Bridge

from shared.auth_gateway.auth_gateway import AuthGatewayMiddleware, auth_user_bean
from shared.error.error_middleware import error_middleware
from shared.lessweb_commondao.lessweb_plugin import MysqlConn, commondao_bean
from shared.redis.redis_plugin import redis_bean


def update_openapi(components):
    openapi_json = json.loads(open('openapi/openapi.json').read())
    openapi_json.update(components)
    with open('openapi/openapi.json', 'w') as f:
        f.write(json.dumps(openapi_json, indent=2, ensure_ascii=False))


def main():
    bridge = Bridge('config')
    bridge.beans(commondao_bean, redis_bean, auth_user_bean)
    bridge.middlewares(
        cors_middleware(allow_all=True),
        error_middleware,
        MysqlConn,
        AuthGatewayMiddleware
    )
    bridge.scan('src', 'shared')
    update_openapi(bridge.dump_openapi_components())
    bridge.run_app()


if __name__ == '__main__':
    main()
