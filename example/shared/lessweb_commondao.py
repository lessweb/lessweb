import logging
from typing import Annotated, Callable

import aiomysql
from aiohttp.web import Application, Request
from aiomysql import DictCursor, Pool
from commondao.commondao import Commondao
from pydantic import BaseModel

from lessweb import Middleware, Module, load_module_config


class MysqlConfig(BaseModel):
    pool_recycle: int = 60
    host: str
    port: int = 3306
    user: str
    password: str
    db: str
    echo: bool = True
    autocommit: bool = True
    maxsize: int = 20


class Mysql(Module):
    pool: Pool

    async def on_startup(self, app: Application):
        logging.debug('mysql on_startup start')
        config = self.load_config(app)
        config_dict = config.model_dump()
        self.pool = await aiomysql.create_pool(**config_dict)
        logging.debug('mysql on_startup end')

    async def on_cleanup(self, app: Application):
        self.pool.close()
        await self.pool.wait_closed()

    def load_config(self, app: Application) -> Annotated[MysqlConfig, 'mysql']:
        return load_module_config(app, 'mysql', MysqlConfig)


class MysqlConn(Middleware):
    mysql: Mysql

    def __init__(self, mysql: Mysql):
        self.mysql = mysql

    async def on_request(self, request: Request, handler: Callable):
        async with self.mysql.pool.acquire() as conn:
            self.conn = conn
            async with conn.cursor(DictCursor) as cur:
                self.cur = cur
                return await handler(request)


def commondao_bean(mysqlConn: MysqlConn) -> Commondao:
    return Commondao(mysqlConn.conn, mysqlConn.cur)
