import re
import time
from enum import Enum
from typing import Annotated, Any, Awaitable, Callable

import jwt
import redis.asyncio as redis
from aiohttp.web import Application, HTTPForbidden, HTTPUnauthorized, Request, Response
from pydantic import BaseModel

import lessweb
from lessweb import Middleware, Module
from shared.redis_plugin import RedisModule


class DefaultPolicy(str, Enum):
    """兜底策略枚举"""
    AUTHENTICATED = "authenticated"  # 只要登录即可访问（默认）
    DENY = "deny"  # 拒绝访问
    PERMIT_ALL = "permit_all"  # 直接放行


class UrlRoleMapping(BaseModel):
    """URL和角色映射配置"""
    pattern: str  # URL匹配正则表达式
    roles: list[str] | None = None  # 允许访问的角色列表，None或空表示需要登录但不限制角色
    permitAll: bool = False  # 是否允许所有人访问（包括未登录用户）

    def model_post_init(self, __context: Any) -> None:
        """验证配置的合法性"""
        if self.roles and self.permitAll:
            raise ValueError(f"Pattern '{self.pattern}': permitAll and roles cannot be set at the same time")


class CompiledUrlRoleMapping:
    """预编译的URL角色映射，用于高效匹配"""
    def __init__(self, pattern: str, roles: list[str] | None, permitAll: bool):
        self.pattern_str = pattern
        self.compiled_pattern = re.compile(pattern)
        self.roles = set(roles) if roles else None
        self.permitAll = permitAll


class JwtGatewayConfig(BaseModel):
    jwt_salt: str
    expire_seconds: int
    url_role_mappings: list[UrlRoleMapping]
    default_policy: DefaultPolicy = DefaultPolicy.AUTHENTICATED  # 兜底策略，默认为需要登录
    redis_prefix: str = "jwt_gateway"  # Redis key 前缀


class JwtUser(BaseModel):
    id: str
    role: str


class JwtGateway(Module):
    config: JwtGatewayConfig
    permit_all_patterns: list[re.Pattern]  # 预编译的公开访问URL正则列表
    auth_required_mappings: list[CompiledUrlRoleMapping]  # 需要认证的URL映射列表
    redis_module: RedisModule
    redis_client: redis.Redis

    def __init__(self, redis_module: RedisModule) -> None:
        self.redis_module = redis_module

    def load_config(self, app: Application) -> Annotated[JwtGatewayConfig, 'jwt_gateway']:
        return lessweb.load_module_config(app, 'jwt_gateway', JwtGatewayConfig)

    async def on_startup(self, app: Application) -> None:
        self.config = self.load_config(app=app)
        self.redis_client = self.redis_module.redis_client
        # 验证配置：permitAll=true的必须放在最前面
        found_auth_required = False
        for mapping in self.config.url_role_mappings:
            if not mapping.permitAll:
                found_auth_required = True
            elif found_auth_required:
                raise ValueError(
                    f"Configuration error: permitAll patterns must be placed before authenticated patterns. "
                    f"Pattern '{mapping.pattern}' with permitAll=true comes after authenticated patterns."
                )

        # 分组预编译：公开访问 vs 需要认证
        self.permit_all_patterns = []
        self.auth_required_mappings = []

        for mapping in self.config.url_role_mappings:
            if mapping.permitAll:
                # 公开访问，只需要预编译正则
                self.permit_all_patterns.append(re.compile(mapping.pattern))
            else:
                # 需要认证，预编译并保存角色信息
                self.auth_required_mappings.append(
                    CompiledUrlRoleMapping(
                        pattern=mapping.pattern,
                        roles=mapping.roles,
                        permitAll=False
                    )
                )

    def _calculate_expire_at(self) -> int:
        """
        计算统一的过期时间
        - 基于当前时间 + expire_seconds
        - 调整到北京时间（UTC+8）早上 6 点过期
        """
        expire_at = int(time.time()) + self.config.expire_seconds
        return expire_at // 86400 * 86400 + 3600 * 22  # 北京时间6点过期

    def encrypt_jwt(self, user_id: str, subject: str, expire_at: int = 0) -> str:
        """
        加密 JWT token
        - user_id: 用户 ID
        - subject: 用户角色
        - expire_at: 自定义过期时间（可选），默认使用统一计算的过期时间
        """
        payload = {
            'uid': user_id,
            'sub': subject,
            'exp': expire_at or self._calculate_expire_at()
        }
        return jwt.encode(payload, self.config.jwt_salt, algorithm='HS256')

    def decrypt_jwt(self, token: str) -> dict:
        """
        return payload dict or raises jwt.ExpiredSignatureError if the expiration time is in the past
        """
        return jwt.decode(token, self.config.jwt_salt, algorithms=['HS256'])

    def _get_redis_key(self, user_role: str, user_id: str) -> str:
        """生成 Redis key: {prefix}:{user_role}:{user_id}"""
        return f"{self.config.redis_prefix}:{user_role}:{user_id}"

    async def login(self, user_id: str, user_role: str) -> None:
        """
        登录方法：在 Redis 中设置用户登录状态
        - key: {prefix}:{user_role}:{user_id}
        - value: 登录时间戳
        - 过期时间: 使用统一的过期时间计算方法
        """
        key = self._get_redis_key(user_role, user_id)
        login_timestamp = int(time.time())
        expire_at = self._calculate_expire_at()

        # 设置 key，使用 exat 参数设置过期的 UNIX 时间戳
        await self.redis_client.set(key, str(login_timestamp), exat=expire_at)

    async def logout(self, user_id: str, user_role: str) -> None:
        """
        登出方法：删除 Redis 中的用户登录状态
        """
        key = self._get_redis_key(user_role, user_id)
        await self.redis_client.delete(key)

    async def is_logged_in(self, user_id: str, user_role: str) -> bool:
        """
        检查用户是否在 Redis 中登录
        """
        key = self._get_redis_key(user_role, user_id)
        return await self.redis_client.exists(key) > 0


class JwtGatewayMiddleware(Middleware):
    gateway: JwtGateway
    user: JwtUser

    def __init__(self, gateway: JwtGateway) -> None:
        self.user = JwtUser(id='', role='')
        self.gateway = gateway

    async def on_request(self, request: Request, handler: Callable[[Request], Awaitable[Any]]) -> Response:
        path = request.path

        # 第一步：检查是否是公开访问路径（无需认证）
        for pattern in self.gateway.permit_all_patterns:
            if pattern.match(path):
                return await handler(request)

        # 第二步：需要认证，解析JWT token（只做一次）
        auth_token = request.headers.get('Authorization', '')
        token = auth_token.removeprefix('Bearer ')
        default_policy = self.gateway.config.default_policy

        try:
            if not token:
                raise HTTPUnauthorized

            try:
                auth_payload = self.gateway.decrypt_jwt(token)
                user_id = auth_payload['uid']
                user_role = auth_payload.get("sub", "")

                # 验证 Redis 登录状态（必须在设置self.user之前验证）
                if not await self.gateway.is_logged_in(user_id, user_role):
                    raise HTTPUnauthorized

                # 只有通过所有验证后才设置用户信息
                self.user = JwtUser(id=user_id, role=user_role)
            except Exception:
                raise HTTPUnauthorized
        except HTTPUnauthorized:
            if default_policy != DefaultPolicy.PERMIT_ALL:
                raise

        # 第三步：检查角色权限
        for mapping in self.gateway.auth_required_mappings:
            if mapping.compiled_pattern.match(path):
                # 如果配置了角色限制，检查用户角色
                if mapping.roles:
                    if not self.user.role:
                        raise HTTPUnauthorized
                    elif self.user.role not in mapping.roles:
                        raise HTTPForbidden(reason=f"Role '{self.user.role}' is not allowed for this resource")
                # 匹配成功并通过权限检查，放行
                return await handler(request)

        # 第四步：兜底策略（没有匹配到任何规则）
        if default_policy == DefaultPolicy.AUTHENTICATED:
            # 需要登录才能访问
            if not self.user.role:
                raise HTTPUnauthorized
            return await handler(request)
        elif default_policy == DefaultPolicy.PERMIT_ALL:
            # 直接放行
            return await handler(request)
        else:  # default_policy == DefaultPolicy.DENY
            # 拒绝访问（不管是否登录）
            raise HTTPForbidden(reason="Access denied")
