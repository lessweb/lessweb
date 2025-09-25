import time
from typing import Annotated, Any, Awaitable, Callable

import jwt
import lessweb
from aiohttp.web import Application, HTTPUnauthorized, Request, Response
from lessweb import Middleware, Module
from pydantic import BaseModel


class AuthGatewayConfig(BaseModel):
    jwt_salt: str
    expire_seconds: int


class AuthUser(BaseModel):
    id: int
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
        self.user = AuthUser(id=0, role='guest')
        self.gateway = gateway

    async def on_request(self, request: Request, handler: Callable[[Request], Awaitable[Any]]) -> Response:
        if not request.path.startswith('/public/'):
            auth_token = request.headers.getone('Authorization', '')
            token = auth_token[7:] if auth_token.startswith('Bearer ') else auth_token
            try:
                if token and (auth_payload := self.gateway.decrypt_jwt(token)):
                    self.user = AuthUser(id=int(auth_payload['uid']), role=auth_payload["sub"])
                else:
                    raise HTTPUnauthorized
            except Exception:
                raise HTTPUnauthorized
        return await handler(request)


def auth_user_bean(auth_gateway: AuthGatewayMiddleware) -> AuthUser:
    return auth_gateway.user
