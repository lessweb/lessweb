from aiohttp.web import Application
import asyncio
from lessweb import Bridge, get_mapping, service, autowire


@service
class CountCache:
    def __init__(self):
        self.count = 0

    async def task(self):
        while 1:
            self.count += 1
            await asyncio.sleep(1)


@get_mapping('/')
async def get_count(count_cache: CountCache):
    return {'count': count_cache.count}


async def background_count_task(app: Application):
    count_cache = autowire(app, CountCache)
    app['count_task'] = asyncio.create_task(count_cache.task())
    yield
    app['count_task'].cancel()
    await app['count_task']


if __name__ == '__main__':
    app = Application()
    bridge = Bridge(app=app)
    bridge.add_route(get_count)
    app.cleanup_ctx.append(background_count_task)
    bridge.run_app()
