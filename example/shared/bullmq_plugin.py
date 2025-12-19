import asyncio
import logging

from aiohttp.web import Response
from bullmq import Job, Queue, Worker  # https://pypi.org/project/bullmq
from bullmq.queue import JobOptions
from pydantic import BaseModel

from lessweb import load_module_config
from lessweb.annotation import OnEvent
from lessweb.event import EventEmitter


class RedisConfig(BaseModel):
    host: str
    port: int
    password: str | None = None
    db: int


class RepeatJobConfig(BaseModel):
    job_name: str
    every: int  # milliseconds


class BullmqConfig(BaseModel):
    queue: str
    redis_db: int
    repeat_jobs: list[RepeatJobConfig] = []


class BullMQ(EventEmitter):
    def __init__(self):
        self.queue = None
        self.worker = None
        self.repeat_jobs: dict[str, RepeatJobConfig] = {}
        self.subscriber_annotation = Processor

    async def on_startup(self, app):
        await super().on_startup(app)
        bullmq_config = load_module_config(app, "bullmq", BullmqConfig)
        redis_config = load_module_config(app, "redis", RedisConfig)
        redis_config.db = bullmq_config.redis_db
        # 创建队列和工作进程
        self.queue = Queue(bullmq_config.queue, {"connection": redis_config.model_dump()})
        self.worker = Worker(bullmq_config.queue, self.process, {"connection": redis_config.model_dump()})
        for repeat_job in bullmq_config.repeat_jobs:
            logging.info(f"add repeat job: {repeat_job.job_name} every: {repeat_job.every}")
            self.repeat_jobs[repeat_job.job_name] = repeat_job
            # Check if job with same jobId exists and is in failed state, then remove it
            existing_job = await Job.fromId(self.queue, repeat_job.job_name)
            if existing_job and await existing_job.isFailed():
                logging.info(f"Removing failed job: {repeat_job.job_name}")
                await existing_job.remove()
            await self.add_job(
                repeat_job.job_name, {},
                {
                    "delay": repeat_job.every,
                    "removeOnComplete": True,
                    "removeOnFail": True,
                    "jobId": repeat_job.job_name,
                },
            )

    async def on_shutdown(self, app):
        # 关闭工作进程和队列
        if self.worker:
            await self.worker.close()
        if self.queue:
            await self.queue.close()

    def process(self, job: Job, job_token: str) -> asyncio.Future:
        return asyncio.ensure_future(self._process_async(job, job_token))

    async def _process_async(self, job: Job, job_token: str) -> str:
        print(job.name, job.data, job_token, job)
        if job.name == '_restarting_' and job.data['job_name'] in self.repeat_jobs:
            job_config = self.repeat_jobs[job.data['job_name']]
            await self.add_job(job_config.job_name, {}, {'delay': max(job_config.every - 900, 100), 'removeOnComplete': True, 'jobId': job_config.job_name})
            return ''
        response = await self.emit(job.name, job.data)
        if job.name in self.repeat_jobs:
            await self.add_job('_restarting_', {'job_name': job.name}, {'delay': 900, 'removeOnComplete': True})
        if isinstance(response, Response):
            return response.text or ""
        return str(response)

    async def add_job(self, job_name: str, data, opts: JobOptions | None = None) -> Job:
        assert self.queue
        if opts is None:
            opts = JobOptions()
        return await self.queue.add(job_name, data, opts)


class Processor(OnEvent):
    pass
