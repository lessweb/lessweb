from typing import Annotated

from bullmq_plugin import BullMQPlugin, Processor

from lessweb import Bridge

# from lessweb.annotation import Get


async def hello(payload: dict, /, *, name: str) -> Annotated[str, Processor('{name}')]:
    print('Processor:', payload, name)
    return f'{name}: {payload}'

bridge = Bridge()

bridge.scan(BullMQPlugin, hello)

# start server: PYTHONPATH=../.. python index.py
if __name__ == '__main__':
    bridge.run_app()
