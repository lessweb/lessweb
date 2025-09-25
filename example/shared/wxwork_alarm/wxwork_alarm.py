import logging

import aiohttp
from aiohttp.web import Application
from pydantic import BaseModel

from lessweb import Module, load_module_config
from shared.redis.redis_plugin import RedisModule


class WxworkAlarmConfig(BaseModel):
    webhook_url: str


class WxworkAlarm(Module):
    webhook_url: str
    session: aiohttp.ClientSession | None

    def __init__(self, redis_module: RedisModule):
        self.redis_module = redis_module
        self.session = None

    async def on_startup(self, app: Application) -> None:
        config = self.load_config(app)
        self.webhook_url = config.webhook_url
        self.session = aiohttp.ClientSession()

    async def on_cleanup(self, app: Application) -> None:
        if self.session:
            await self.session.close()

    def load_config(self, app: Application) -> WxworkAlarmConfig:
        return load_module_config(app, 'wxwork_alarm', WxworkAlarmConfig)

    async def send_alarm(self, content: str, alarm_key: str, alarm_on: bool):
        redis_client = self.redis_module.redis_client
        if redis_client and alarm_key:
            alerting = await redis_client.get(alarm_key)
            # 避免重复告警：异常时已在告警状态，或恢复时本来就正常
            if (alarm_on and alerting) or (not alarm_on and not alerting):
                return
            if alarm_on:
                await redis_client.set(alarm_key, 'ON', ex=86400 * 30)
            else:
                await redis_client.delete(alarm_key)

        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        assert self.session
        async with self.session.post(self.webhook_url, json=data, headers=headers) as resp:
            if resp.status != 200:
                logging.error(f"send alarm failed: {await resp.text()}")
