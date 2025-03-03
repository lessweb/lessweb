from typing import Annotated

from lessweb import Bridge
from lessweb.annotation import Get


async def hello() -> Annotated[dict, Get('/')]:
    return {'message': 'Hello, world!'}


def main():
    bridge = Bridge()
    bridge.scan(hello)
    bridge.run_app()


if __name__ == '__main__':
    main()
