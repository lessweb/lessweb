from aiohttp.web import HTTPForbidden
from commondao import Commondao

from lessweb import Service
from shared.jwt_gateway import JwtGatewayMiddleware
from src.entity.admin import Admin


class AuthRole:
    ADMIN = "ADMIN"
    USER = "USER"


class CurrentAdmin(Service):
    _id: int
    _dao: Commondao
    _jwt_gateway: JwtGatewayMiddleware

    def __init__(self, commondao: Commondao, jwt_gateway: JwtGatewayMiddleware):
        self._dao = commondao
        self._jwt_gateway = jwt_gateway

    @property
    def id(self) -> int:
        if self._jwt_gateway.user.role != AuthRole.ADMIN:
            raise HTTPForbidden
        return int(self._jwt_gateway.user.id)

    async def get(self) -> Admin:
        return await self._dao.get_by_id_or_fail(Admin, self.id)
