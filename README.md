# lessweb

Lessweb is a ready-to-use, production-grade Python web framework with the following goals:

* Ready-to-use: Easily parse configuration files, set up logging with ease, and dynamically override configuration items using environ variables.
* Production-grade: Built on the aiohttp ecosystem and boast powerful IOC capabilities.
* Pythonic: Support for the latest python version and the latest python syntax.

## Install lessweb

To install the latest lessweb for Python≥3.10, please run:

```shell
pip install lessweb
```

## Dependencies

- [aiohttp](https://github.com/aio-libs/aiohttp)
- [orjson](https://github.com/ijl/orjson)
- [pydantic](https://github.com/pydantic/pydantic)
- [python-dotenv](https://github.com/theskumar/python-dotenv)

## A Simple Example

Save the code below in file `main.py`:

```python
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
```

Start the application with the command below, it listens on `http://localhost:8080/` by default.

```shell
python main.py
```

### Check it

Open your browser at `http://localhost:8080`

You will see the JSON response as:

```json
{"message":"Hello, world!"}
```

Open your browser at `http://127.0.0.1:8000?who=John`

You will see the JSON response as:

```json
{"message":"Hello, John!"}
```

## License

Lessweb is offered under the Apache 2 license.

## Source code

The latest developer version is available in a GitHub repository: https://github.com/lessweb/lessweb

