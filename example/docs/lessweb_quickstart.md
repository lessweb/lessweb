# Lessweb Quick Start

## 端点(endpoint)

在`lessweb`中，端点(endpoint)指的是一个可以处理HTTP请求的URL路径。通过定义不同的路由，你可以将不同的端点关联到相应的处理函数上。这些处理函数必须是协程（即`async def`函数），负责响应客户端的请求，如GET、POST、PUT、DELETE等。

端点的参数可以被框架“注入”，最简单的用法是用一个`aiohttp.web.Request`类型的变量，就能获取各种请求参数。端点可以返回`aiohttp.web.Response`对象，也可以直接返回能够序列化为JSON的变量。

示例如下：

```python
from typing import Annotated

from aiohttp.web import Request

from lessweb import Bridge
from lessweb.annotation import Endpoint, Get, Post


async def get_pet_detail(request: Request) -> Annotated[dict, Endpoint('GET', '/pet/{pet_id}')]:
    return {'pet_id': request.match_info['pet_id']}


async def get_pet_list(request: Request) -> Annotated[dict, Get('/pet')]:
    return {'name': request.query['name']}


async def create_pet(request: Request) -> Annotated[dict, Post('/pet')]:
    pet = await request.json()
    return pet


if __name__ == '__main__':
    bridge = Bridge()
    bridge.scan(get_pet_detail, get_pet_list, create_pet)
    bridge.run_app()

```

### 自动搜索端点

实际项目中端点可能非常多。lessweb框架提供了根据包名(package name)自动搜索端点的能力。例如，我们先建立一个多文件的项目：

```
index.py
myapp/
myapp/endpoint/
myapp/endpoint/__init__.py
myapp/endpoint/get_pet_list.py
myapp/endpoint/create_pet.py
```

```python title="get_pet_detail.py"
...
async def get_pet_list(request: Request) -> Annotated[dict, Get('/pet')]:
    return {'name': request.query['name']}
```

```python title="create_pet.py"
...
async def create_pet(request: Request) -> Annotated[dict, Post('/pet')]:
    pet = await request.json()
    return pet
```

```python title="index.py"
from lessweb import Bridge


if __name__ == '__main__':
    bridge = Bridge()
    bridge.scan('myapp.endpoint')
    bridge.run_app()
```

### 路径高级规则

lessweb的路径规则完全基于aiohttp的路径规则。

除了普通的固定路径，aiohttp支持有“可变资源”的路径。例如，一个路径为`/a/{name}/c`的资源将匹配所有路径为`/a/b/c`、`/a/1/c`和`/a/etc/c`的请求。变量部分是以`{identifier}`的形式指定的，其中identifier部分的匹配值可以在以后的请求处理程序中用`Request.match_info`获取。

默认情况下，每个`{identifier}`都以正则表达式`[^{}/]+`进行匹配。你也可以用`{identifier:regex}`的形式指定一个自定义的正则。例如，上面例子中的`get_pet_detail()`可做如下修改，以保证传入的`pet_id`一定是数字：

```python title="get_pet_list.py"
async get_pet_detail(request: Request) -> Annotated[dict, Get('/pet/{pet_id:[0-9]+}')]:
    ...
```

## 获取请求

如果你想在endpoint中获取HTTP请求的query参数、路径参数或body参数，lessweb推荐使用参数注入的方式，即框架自动为endpoint的带类型参数赋值。

* [keyword-only参数](https://peps.python.org/pep-3102/)：可注入路径参数和query参数。当路径参数和query参数同名时，优先注入路径参数。
* [positional-only参数](https://docs.python.org/3/whatsnew/3.8.html#positional-only-parameters)： 可注入JSON反序列化后的request body。
* 普通参数：即positional-or-keyword参数，可注入上下文变量，例如: `request: Request`等。

### 示例

```python
from aiohttp.web import Request
from enum import Enum
from pydantic import BaseModel


class PetKind(Enum):
    CAT = 'CAT'
    ...


class Pet(BaseModel):
    pet_id: int
    ...


async def get_pet_detail(request: Request, *, pet_id: int, kind: list[PetKind] = None) -> Annotated[dict, Get('/pet/{pet_id}')]:
    return {
        'name': request.query['name'],
        'pet_id': pet_id,
        'kind': kind
    }


async def create_pet(pet: Pet, /) -> Annotated[dict, Post('/pet')]:
    return pet
```

### 支持的参数类型

lessweb框架支持keyword-only参数转换为如下类型：

* 基础类型：
  * `str`, `int`, `float`
  * `bool`: 字符串'true'(不区分大小写)、'1'和'✔'会转换为`True`；字符串'false'(不区分大小写)、'0'和'✖'会转换为`False`。
  * `list`: 框架会[使用csv格式解析](https://docs.python.org/3/library/csv.html)。
* `pydantic.BaseModel`: 原生支持反序列化为`pydantic.BaseModel`实例。
* datetime:
    * `datetime.datetime`：输入需符合[RFC 3339](https://tools.ietf.org/html/rfc3339)格式，例如：“1970-01-01T00:00:00+00:00”。
    * `datetime.time` 
    * `datetime.date` 
* [enum](https://docs.python.org/3/library/enum.html): 根据枚举值反序列化。
* [Union](https://docs.python.org/3/library/typing.html#typing.Union): lessweb框架会按顺序依次尝试转换（注意：从python3.10开始已支持`X | Y `形式的[语法](https://docs.python.org/3/whatsnew/3.10.html#pep-604-new-type-union-operator)）
* [Literal](https://docs.python.org/3/whatsnew/3.8.html#typing): lessweb框架会按顺序依次比较。
* [NewType](https://docs.python.org/3/library/typing.html#typing.NewType): lessweb框架会通过`NewType(name, tp).__supertype__`获取原类型并尝试继续转换。

lessweb框架支持positional-only参数转换为如下类型：

* `pydantic.BaseModel`
* `list[pydantic.BaseModel]`


## 响应返回

endpoint的响应返回应该是一个`aiohttp.web.Response`实例，更准确地说是返回一个继承自`aiohttp.web.StreamResponse`类的实例。你可以设置返回的内容、HTTP状态码和Header等等信息。例如：

```python
from aiohttp.web import Response

async def get_example_html() -> Annotated[Response, Get('/example.html')]:
    html_text = open('example.html').read()
    return Response(text=html_text, content_type='text/html', charset='utf-8')
```

另外，你也可以用抛出`aiohttp.web.HTTPException`派生实例的方式实现各种HTTP状态码的返回。例如：

```python
from aiohttp.web import HTTPForbidden

async def example_for_response() -> Annotated[Response, Get('/')]:
    raise HTTPForbidden(text='Access Denied')
```

### 返回JSON

lessweb框架会尝试将端点的返回数据进行JSON序列化后包装成`Response`实例。例如：

```python
@get_mapping('/pet')
async def get_pet_list():
    return [{'pet_id': 1, 'name': 'Kitty', 'kind': 'CAT'}]
```

不过这种方法有时会有局限，即有的时候除了返回数据，还要在附加返回header等信息。这种情况可以使用lessweb提供的`rest_response`函数得到`Response`实例。

```python
from lessweb import rest_response


async def get_pet_list() -> Annotated[dict, Get('/pet')]:
    pet_list = [{'pet_id': 1, 'name': 'Kitty', 'kind': 'CAT'}]
    return rest_response(pet_list, headers={'X-TOKEN': 'abc123'})
```

你也可以用lessweb提供的`rest_error`函数得到异常实例，然后抛出这个异常实现返回错误信息：

```python
from aiohttp.web import HTTPBadRequest
from lessweb import rest_error


async def get_pet_list() -> Annotated[dict, Get('/pet/{pet_id}')]:
    if ...:
        raise rest_error(HTTPBadRequest, {'code': -1, 'message': 'Invalid pet_id'})
```

### JSON序列化能力

lessweb框架的JSON序列化基于[orjson](https://github.com/ijl/orjson)库，默认支持序列化如下类型：

 * 基础类型：包括`str`, `int`, `float`, `bool`, `dict`, `list`。
 * dataclass: 原生支持序列化`dataclasses.dataclass`实例。
 * datetime:
    * 会将`datetime.datetime`对象序列化为[RFC 3339](https://tools.ietf.org/html/rfc3339)格式，例如：“1970-01-01T00:00:00+00:00”。
    * `datetime.time` 对象不能包含`tzinfo`。
    * `datetime.date` 对象都可以被序列化。
 * enum: 根据枚举值进行序列化。
 * numpy: 包括 `numpy.ndarray`, `numpy.float64`, `numpy.float32`, `numpy.int64`, `numpy.int32`, `numpy.int16`, `numpy.int8`, `numpy.uint64`, `numpy.uint32`, `numpy.uint16`, `numpy.uint8`, `numpy.uintp`, or `numpy.intp`, and `numpy.datetime64`等实例。
 * uuid: 会将`uuid.UUID`实例序列化为[RFC 4122](https://tools.ietf.org/html/rfc4122)格式，例如："f81d4fae-7dec-11d0-a765-00a0c91e6bf6"。
 * `pydantic.BaseModel`: lessweb框架支持`pydantic.BaseModel`实例的JSON序列化。

例如：

```python
from dataclasses import dataclass


@dataclass
class Pet:
    pet_id: int
    ...

    
async def get_pet_list() -> Annotated[Response, Get('/pet')]:
    return [Pet(pet_id=123, name='Kitty', kind=PetKind.CAT, birthday=date(2000, 12, 31))]
```


### JSON序列化配置

```toml title="config.toml"
[lessweb]
orjson_option = 'APPEND_NEWLINE,INDENT_2,NAIVE_UTC,NON_STR_KEYS,STRICT_INTEGER,OMIT_MICROSECONDS,PASSTHROUGH_DATACLASS,PASSTHROUGH_DATETIME,PASSTHROUGH_SUBCLASS,SERIALIZE_DATACLASS,SERIALIZE_NUMPY,SERIALIZE_UUID,SORT_KEYS,STRICT_INTEGER,UTC_Z'
```

这些配置功能可按需选用，具体用法请参考[https://github.com/ijl/orjson#option](https://github.com/ijl/orjson#option) 。
