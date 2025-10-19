import time
from typing import Annotated, Any, Awaitable, Callable

import jwt
from aiohttp.web import Application, HTTPForbidden, HTTPUnauthorized, Request, Response
from pydantic import BaseModel

import lessweb
from lessweb import Middleware, Module


class AuthGatewayConfig(BaseModel):
    jwt_salt: str
    expire_seconds: int


class AuthUser(BaseModel):
    id: str
    role: str


class AuthGateway(Module):
    config: AuthGatewayConfig

    def load_config(self, app: Application) -> Annotated[AuthGatewayConfig, 'auth_gateway']:
        return lessweb.load_module_config(app, 'auth_gateway', AuthGatewayConfig)

    async def on_startup(self, app: Application) -> None:
        self.config = self.load_config(app=app)

    def encrypt_jwt(self, user_id: str, subject: str, expire_at: int = 0) -> str:
        default_expire_at = int(time.time()) + self.config.expire_seconds
        default_expire_at = default_expire_at // 86400 * 86400 + 3600 * 22  # 北京时间6点过期
        payload = {'uid': user_id, 'sub': subject,
                   'exp': expire_at or default_expire_at}
        return jwt.encode(payload, self.config.jwt_salt, algorithm='HS256')

    def decrypt_jwt(self, token: str) -> dict:
        """
        return payload dict or raises jwt.ExpiredSignatureError if the expiration time is in the past
        """
        return jwt.decode(token, self.config.jwt_salt, algorithms=['HS256'])


class AuthGatewayMiddleware(Middleware):
    gateway: AuthGateway
    user: AuthUser

    def __init__(self, gateway: AuthGateway) -> None:
        self.user = AuthUser(id='none', role='guest')
        self.gateway = gateway

    async def on_request(self, request: Request, handler: Callable[[Request], Awaitable[Any]]) -> Response:
        path = request.path
        if not path.startswith('/public/') and path != '/':
            auth_token = request.headers.getone('Authorization', '')
            token = auth_token[7:] if auth_token.startswith('Bearer ') else auth_token
            try:
                if token and (auth_payload := self.gateway.decrypt_jwt(token)):
                    self.user = AuthUser(id=auth_payload['uid'], role=auth_payload["sub"])
                else:
                    raise HTTPUnauthorized
            except Exception:
                raise HTTPUnauthorized
            if not path.startswith((f'/{self.user.role}/', '/common/')):
                raise HTTPForbidden
        return await handler(request)
