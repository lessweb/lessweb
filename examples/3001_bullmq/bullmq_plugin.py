
from aiohttp.web import Response
from bullmq import Queue, Worker

from lessweb.annotation import OnEvent
from lessweb.event import EventEmitter


class BullMQPlugin(EventEmitter):
    def __init__(self):
        self.queue = None
        self.worker = None
        self.subscriber_annotation = Processor

    async def on_startup(self, app):
        await super().on_startup(app)
        # 创建队列和工作进程
        self.queue = Queue("myQueue", {"connection": {
            "host": "192.168.65.44",
            "port": 12138,
            "password": "3UQjmWrPe3ZYBcEv2AnoDWsM",
            "db": 2,
        }})

        self.worker = Worker("myQueue", self.process, {"connection": {
            "host": "192.168.65.44",
            "port": 12138,
            "password": "3UQjmWrPe3ZYBcEv2AnoDWsM",
            "db": 2,
        }})

    async def on_shutdown(self, app):
        # 关闭工作进程和队列
        if self.worker:
            await self.worker.close()
        if self.queue:
            await self.queue.close()

    async def process(self, job, job_token):
        print(job.name, job.data, job_token)
        response = await self.emit(job.name, job.data)
        if isinstance(response, Response):
            return response.text
        return str(response)


class Processor(OnEvent):
    pass
