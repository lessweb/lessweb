# lessweb

Lessweb is a ready-to-use, production-grade Python web framework with the following goals:

* **Ready-to-use**: Easily parse configuration files, set up logging with ease, and dynamically override configuration items using environ variables.
* **Production-grade**: Built on the aiohttp ecosystem and boasting powerful IOC capabilities.
* **Pythonic**: Supports the latest Python versions and syntax.

---

## 📦 Installation

To install the latest version of lessweb for **Python ≥ 3.10**, run:

```bash
pip install lessweb
```

### Dependencies

* [aiohttp](https://github.com/aio-libs/aiohttp)
* [orjson](https://github.com/ijl/orjson)
* [pydantic](https://github.com/pydantic/pydantic)
* [python-dotenv](https://github.com/theskumar/python-dotenv)

---

## ⚡ Quick Start Example

Save the following to `main.py`:

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

Run your app:

```bash
python main.py
```

Now open your browser at [http://localhost:8080](http://localhost:8080)

Output:

```json
{"message": "Hello, world!"}
```

Or try [http://127.0.0.1:8080?who=John](http://127.0.0.1:8080?who=John):

```json
{"message": "Hello, John!"}
```

---

## 📚 Official Documentation

* **Quick Start**: [https://lessweb.castdict.com/quickstart/](https://lessweb.castdict.com/quickstart/)
* **IOC / Dependency Injection**: [https://lessweb.castdict.com/ioc/](https://lessweb.castdict.com/ioc/)
* **Reference Manual**: [https://lessweb.castdict.com/reference/](https://lessweb.castdict.com/reference/)

---

# 📘 Lessweb Framework Guide

Below is a summarized version of the **Quick Start** and **IOC (Dependency Injection)** documentation.

---

## 🧭 Endpoint Basics

An **endpoint** in lessweb is an async function bound to a specific HTTP route (URL).
Endpoints can automatically receive parameters from query strings, path variables, or the request body.

Example:

```python
from typing import Annotated
from aiohttp.web import Request
from lessweb import Bridge
from lessweb.annotation import Get, Post

async def get_pet_detail(request: Request) -> Annotated[dict, Get('/pet/{pet_id}')]:
    return {'pet_id': request.match_info['pet_id']}

async def create_pet(request: Request) -> Annotated[dict, Post('/pet')]:
    pet = await request.json()
    return pet

if __name__ == '__main__':
    bridge = Bridge()
    bridge.scan(get_pet_detail, create_pet)
    bridge.run_app()
```

You can also scan an entire package:

```python
bridge.scan('myapp.endpoint')
```

### Dynamic Path Parameters

Supports regex-based path matching:

```python
async def get_pet_detail(request: Request) -> Annotated[dict, Get('/pet/{pet_id:[0-9]+}')]:
    ...
```

---

## 🧩 Request Parameter Injection

Lessweb automatically injects request data into endpoint parameters:

* **keyword-only parameters** (`*, name: str`) → path/query parameters
* **positional-only parameters** (`data: Model, /`) → JSON body
* **normal parameters** (`request: Request`) → context objects or services

Example:

```python
from pydantic import BaseModel
from lessweb.annotation import Get, Post
from typing import Annotated

class Pet(BaseModel):
    pet_id: int
    name: str

async def get_pet_detail(*, pet_id: int) -> Annotated[dict, Get('/pet/{pet_id}')]:
    return {'pet_id': pet_id}

async def create_pet(pet: Pet, /) -> Annotated[dict, Post('/pet')]:
    return pet
```

Supported types include:

* `str`, `int`, `float`, `bool`, `list`
* `datetime`, `date`, `time`
* `enum`, `Literal`, `Union`, `NewType`
* `pydantic.BaseModel`

---

## 💡 JSON Responses

Endpoints can directly return JSON-compatible data:

```python
async def get_pet_list() -> Annotated[dict, Get('/pet')]:
    return [{'pet_id': 1, 'name': 'Kitty'}]
```

Or use helper functions for advanced responses:

```python
from lessweb import rest_response, rest_error
from aiohttp.web import HTTPBadRequest

async def get_pet_list() -> Annotated[dict, Get('/pet')]:
    return rest_response([{'name': 'Kitty'}], headers={'X-TOKEN': 'abc123'})

async def bad_request() -> Annotated[dict, Get('/error')]:
    raise rest_error(HTTPBadRequest, {'code': -1, 'message': 'Invalid request'})
```

---

## ⚙️ JSON Serialization

Based on [orjson](https://github.com/ijl/orjson) with support for:

* dataclasses
* datetime / date / time (RFC 3339)
* enum
* numpy types
* uuid
* pydantic models

Configurable in `config.toml`:

```toml
[lessweb]
orjson_option = 'APPEND_NEWLINE,INDENT_2,UTC_Z'
```

---

## 🧠 Dependency Injection (IOC)

Lessweb’s IOC system auto-injects dependencies based on parameter types, similar to **Spring Boot**.

### Lifecycle Levels

| Type           | Scope                        | Description             |
| -------------- | ---------------------------- | ----------------------- |
| **Module**     | Process-level singleton      | e.g. DB connection pool |
| **Middleware** | Request-level wrapper        | Pre/post processing     |
| **Service**    | Request-level singleton      | Business logic          |
| **Bean**       | Request-level factory result | Complex object creation |

---

### Example: Modules

```python
class Mysql(Module):
    async def on_startup(self, app):
        self.pool = await aiomysql.create_pool(...)

class RedisModule(Module):
    async def on_startup(self, app):
        self.redis_client = redis.Redis(...)
```

### Example: Middleware

```python
class MysqlConn(Middleware):
    def __init__(self, mysql: Mysql):
        self.mysql = mysql

    async def on_request(self, request, handler):
        async with self.mysql.pool.acquire() as conn:
            self.conn = conn
            return await handler(request)
```

### Example: Services and Beans

```python
class TaskService(Service):
    def __init__(self, dao: Commondao, redis: redis.Redis):
        self.dao = dao
        self.redis = redis

def commondao_bean(mysqlConn: MysqlConn) -> Commondao:
    return Commondao(mysqlConn.conn, mysqlConn.cur)

def redis_bean(redis_module: RedisModule) -> redis.Redis:
    return redis_module.redis_client
```

Register all in `main.py`:

```python
def main():
    bridge = Bridge()
    bridge.beans(commondao_bean, redis_bean)
    bridge.middlewares(MysqlConn)
    bridge.scan('src')
    bridge.run_app()
```

---

## ✅ Best Practices

* Use **Middleware** for request pre/post hooks (e.g. auth, logging)
* Use **Service** for business logic
* Keep **Module** dependencies only between other Modules
* Let **Beans** create reusable request-scoped objects

---

## 📄 License

Lessweb is offered under the **Apache 2.0 License**.

---

## 🧭 Source Code

GitHub Repository:
👉 [https://github.com/lessweb/lessweb](https://github.com/lessweb/lessweb)
