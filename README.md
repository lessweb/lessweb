# lessweb
>「嘞是web」

Lessweb is an extremely easy-to-use python web framework with the following goals.

* Simple and efficient: based on the aiohttp library IOC capabilities, native support for configuration loading and logging settings to meet production-level development requirements
* Pythonic: support for the latest python version and the latest python syntax

## Install lessweb

To install the latest lessweb for Python 3, please run:

```shell
pip3 install lessweb
```

## Hello, world!

Save the code below in file `index.py`:

```python
from lessweb import Bridge, get_mapping

@get_mapping('/')
async def hello():
    return {'message': 'Hello, world!'}

def main():
    bridge = Bridge()
    bridge.add_route(hello)
    bridge.run_app()

if __name__ == '__main__':
    main()
```

Start the application with the command below, it listens on `http://localhost:8080/` by default.

```
python3 index.py
```

## Setting port

Save the code below in file `config.toml`:

```toml
[bootstrap]
port = 80
```

Then change the code to:

```python
def main():
    bridge = Bridge(config='config.toml')
    bridge.add_route(hello)
    bridge.run_app()
```

Once you run it, you can access `http://localhost/` with your browser.

You can also use environment variables to override the configuration file's contents, e.g. run `BOOTSTRAP_PORT=8081 python3 index.py`, then it listens on `http://localhost:8081`.

## License

Lessweb is offered under the Apache 2 license.

## Source code

The latest developer version is available in a GitHub repository: https://github.com/lessweb/lessweb

## Cookbook
### https://github.com/lessweb/lessweb/wiki

## Cookbook【中文】：
### http://www.lessweb.cn
