# lessweb
>「嘞是web」

> A pythonic web framework

## Get lessweb
```bash
pip3 install lessweb
```

## Hello World!
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

## Cookbook：
### http://www.lessweb.cn
