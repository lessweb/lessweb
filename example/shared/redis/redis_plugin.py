from typing import Annotated

import redis.asyncio as redis
from aiohttp.web import Application
from pydantic import BaseModel

from lessweb import Module, load_module_config


class RedisConfig(BaseModel):
    host: str
    port: int
    password: str | None = None
    db: int


class RedisModule(Module):
    redis_client: redis.Redis

    async def on_startup(self, app: Application) -> None:
        config = self.load_config(app)
        self.redis_client = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.password,
            db=config.db,
            decode_responses=True,
        )

    async def on_cleanup(self, app: Application) -> None:
        await self.redis_client.aclose()

    def load_config(self, app: Application) -> Annotated[RedisConfig, 'redis']:
        return load_module_config(app, 'redis', RedisConfig)


def redis_bean(redis_module: RedisModule) -> redis.Redis:
    return redis_module.redis_client
