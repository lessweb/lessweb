from aiohttp.web import HTTPForbidden
from commondao import Commondao
from lessweb import Service

from shared.auth_gateway.auth_gateway import AuthGatewayMiddleware
from src.entity.admin import Admin
from src.entity.user import User


class AuthRole:
    ADMIN = "admin"
    USER = "app"


class CurrentAdmin(Service):
    _id: int
    _dao: Commondao
    _auth_gateway: AuthGatewayMiddleware

    def __init__(self, commondao: Commondao, auth_gateway: AuthGatewayMiddleware):
        self._dao = commondao
        self._auth_gateway = auth_gateway

    @property
    def id(self) -> int:
        if self._auth_gateway.user.role != AuthRole.ADMIN:
            raise HTTPForbidden
        return int(self._auth_gateway.user.id)

    async def get(self) -> Admin:
        return await self._dao.get_by_id_or_fail(Admin, self.id)


class CurrentUser(Service):
    _id: int
    _dao: Commondao
    _auth_gateway: AuthGatewayMiddleware

    def __init__(self, commondao: Commondao, auth_gateway: AuthGatewayMiddleware):
        self._dao = commondao
        self._auth_gateway = auth_gateway

    @property
    def id(self) -> int:
        if self._auth_gateway.user.role != AuthRole.USER:
            raise HTTPForbidden
        return int(self._auth_gateway.user.id)

    async def get(self) -> User:
        return await self._dao.get_by_id_or_fail(User, self.id)
