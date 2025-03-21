from typing import Annotated

from lessweb import Bridge
from lessweb.annotation import Get


async def hello(*, who: str = 'world') -> Annotated[dict, Get('/')]:
    return {'message': f'Hello, {who}!'}


def main():
    bridge = Bridge()
    bridge.scan(hello)
    bridge.run_app()


if __name__ == '__main__':
    main()
