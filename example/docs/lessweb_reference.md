# Lessweb Reference

## `Bridge`

### `Bridge.__init__`

```python
def __init__(self, config: str | None = None, app: Application | None = None) -> None:
    """
    config: path to config file/directory
    app: aiohttp application
    """
```

### `Bridge.scan`

```python
def scan(self, *packages) -> None: ...
```

### `Bridge.middlewares`

```python
def middlewares(self, *middlewares) -> None: ...
```

### `Bridge.run_app`

```python
def run_app(self, **kwargs) -> None: ...
```

### `Bridge.dump_openapi_components`

```python
def dump_openapi_components(self) -> dict:
    """
    返回一个包含应用程序 OpenAPI 组件的 dict。
    返回的 dict 将具有以下结构：
    {
        "components": {
            "schemas": {...}
        }
    }
    schemas dict 将包含应用程序中每个端点模型的 OpenAPI 模式定义。
    :return: 包含 OpenAPI 组件的 dict
    """
```

## `load_module_config`

```python
def load_module_config(app: Application, module_config_key: str, module_config_cls: Type[T]) -> T:
    """
    加载指定模块的配置。

    参数：
        app (Application): aiohttp的应用对象，包含全局配置信息。
        module_config_key (str): 在全局配置中查找模块配置的键名。
        module_config_cls (Type[T]): 用于校验和解析模块配置的Pydantic模型类，必须是pydantic.BaseModel的子类。

    返回：
        T: 解析后的模块配置实例。

    异常：
        TypeError: 如果module_config_cls不是pydantic.BaseModel的子类，则抛出此异常。
    """
```

## `Module`

```python
class Module:
    """
    进程级别的单例模块，兼容aiohttp的signals
    """
    def __init__(self) -> None: ...
    async def on_startup(self, app: Application) -> None: ...
    async def on_cleanup(self, app: Application) -> None: ...
    async def on_shutdown(self, app: Application) -> None: ...
    def load_config(self, app: Application) -> Any:
        """
        Example of override:
        >>> def load_config(self, app: Application) -> Annotated[MyAppConfig, 'myapp']:
        ...   return lessweb.load_module_config(app, 'myapp', MyAppConfig)
        """
```

## `Middleware`

```python
class Middleware:
    """
    请求级别的单例中间件，兼容aiohttp的middlewares
    """
    def __init__(self) -> None: ...
    async def on_request(self, request: Request, handler: HANDLER_TYPE) -> Response:
        """
        Example of override:
        >>> async def on_request(self, request: Request, handler: HANDLER_TYPE) -> Response:
        ...   return await handler(request)
        """
```

## `Service`

```python
class Service:
    """
    业务逻辑单例服务
    """
    def __init__(self) -> None: ...
```

## `autowire_module`

```python
def autowire_module(app: Application, cls: Type[T]) -> T:
    """
    进程级别单例模块注入。
    """
```

## `autowire`

```python
def autowire(request: Request, cls: Type[U]) -> U:
    """
    Request-level dependency injection, automatically instantiating Middleware or Service objects.
    """
```

## `rest_error`

```python
def rest_error(
        error: Type[HTTPError],
        data,
        *,
        headers: Optional[LooseHeaders] = None,
        **kwargs,
) -> HTTPError:
    return error(
        body=TypeCast.dumps(data),
        headers=headers,
        content_type='application/json',
        **kwargs,
    )
```

## `rest_response`

```python
def rest_response(
        data,
        *,
        status: int = 200,
        reason: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
) -> Response:
    response = Response(
        body=TypeCast.dumps(data),
        status=status,
        reason=reason,
        headers=headers,
        content_type='application/json',
    )
    return response
```

## `get_request_stack`

```python
def get_request_stack(request: Request) -> list[str | bytes]:
    """
    获取请求对象中保存的请求堆栈。

    参数：
        request (Request): aiohttp 的请求对象，通过 request 的字典属性存放中间件等过程中传递的数据堆栈，
                           该堆栈用于在处理请求过程中存放中间转换或验证后的数据（例如经过转换后的请求体）。

    返回：
        list[str | bytes]: 返回请求堆栈列表。如果请求对象中不存在该堆栈，则会在请求中初始化一个空列表后返回。
    """
```

## `push_request_stack`

```python
def push_request_stack(request: Request, value: str | bytes):
    """
    向请求对象的请求堆栈中添加一个值。

    参数：
        request (Request): aiohttp 的请求对象，其内部包含用于存储请求处理过程数据的堆栈。
        value (str | bytes): 要添加到堆栈中的数据值。
                            注意：当前逻辑要求 value 必须为 bytes 类型，否则将抛出 TypeError。

    使用示例：
        在一个Middleware中，可能先对原始请求体进行读取和预处理：

            async def some_middleware(request, handler):
                raw_data = await request.read()
                push_request_stack(request, raw_data)
                # 对读取到的数据做进一步转换（例如转换为 JSON 后修改数据），转换后的数据也必须是 bytes 类型
                modified_data = ...
                push_request_stack(request, modified_data)
                return await handler(request)

        在后续处理 endpoint 中，可以使用 positional-only 参数，框架通过调用 get_request_stack(request) 
        获取堆栈列表，并对堆栈进行 pop 操作，将最后一次推入的数据提取出来作为 positional-only 参数传递给目标处理函数。
    """
```

## `EventEmitter`

```python
class EventEmitter(Module):
    """
    事件发射器类，用于注册事件处理函数并触发事件。

    该类继承自 Module，在应用启动时会为所有标记为事件订阅（使用 OnEvent 装饰器）的处理函数构建 HTTP POST 路由，
    从而实现事件的统一管理。触发事件时，该类会模拟一个 HTTP POST 请求，将事件名称和负载数据传递给相应的处理函数，
    支持同步返回响应，也能将事件处理后台异步执行。
    """
```

### `EventEmitter.emit`

```python
async def emit(self, event: str, payload: Any) -> StreamResponse:
    """
    触发指定的事件。
    通过构造模拟的 HTTP POST 请求，将 payload 序列化为 JSON 数据传入对应的事件处理路由中，
    根据处理函数是否标记为后台异步执行，返回相应的响应（异步时返回 204 状态码）。
    """
```

## `TypeCast`

### `TypeCast.dumps`

```python
@classmethod
def dumps(self, data: Any) -> bytes:
    return orjson.dumps(
        data, option=self.ORJSON_OPTION, default=_pydantic_encoder)
```

### `TypeCast.validate_json`

```python
@classmethod
def validate_json(self, data: Union[str, bytes], tp: Type[T]) -> T:
    """
    Validate data as json to type T.

    Supported type T:
        - list[pydantic.BaseModel]
        - pydantic.BaseModel

    The validation process is different according to the type of T:
        - If T is list[pydantic.BaseModel], the validation is done by validate the list items one by one.
        - If T is pydantic.BaseModel, the validation is done by pydantic's model_validate_json method.

    Raises:
        ValueError: if the data cannot be parsed to the given type (4xx Error for Frontend)
        TypeError: if the given type is not supported (5xx Error for Frontend)
    """
```

### `TypeCast.validate_query`

```python
@classmethod
def validate_query(self, data: str, tp: Type[T]) -> T:
    """
    try to convert a query string to the given type.

    Args:
        data: a query string.
        tp: the type to convert to.

    Returns:
        the converted value.

    Raises:
        ValueError: if the data cannot be parsed to the given type (4xx Error for Frontend)
        TypeError: if the given type is not supported (5xx Error for Frontend)
    """
```

## `annotation.Endpoint`

### `annotation.Get`

### `annotation.Post`

### `annotation.Put`

### `annotation.Delete`

### `annotation.Patch`

## `annotation.DefaultFactory`

```python
class DefaultFactory:
    """
    DefaultFactory 用于为函数参数提供默认值生成器，通过传入一个无参可调用对象，
    当需要默认值时调用该工厂函数生成默认值。该类常用于注解中，用于描述参数的默认生成逻辑，
    类似于 dataclasses 中的 default_factory。

    示例用法：
    >>> async def foo(*, ids: Annotated(list[str], DefaultFactory(list)) -> Annotated[dict, Get('/')]:
    ...   pass

    注意：
    - factory_func 必须是一个不接受任何参数的可调用对象；
    - 在参数默认值处理中，当未提供具体值时，框架会调用该工厂函数返回默认值实例。
    """
    def __init__(self, factory_func) -> None: ...
```

## `annotation.OnEvent`

```python
class OnEvent:
    """
    OnEvent 是一个用于标记事件订阅的注解类。它允许开发者在定义endpoint函数时,
    标记函数为事件订阅，从而实现事件的统一管理。

    示例用法：
    async def foo_handle_event(request: Request) -> Annotated[dict, OnEvent('my_event_name')]:
        ...
    """
    def __init__(self, event: str, background: bool = False): ...
```

## `annotation.TextResponse`

```python
class TextResponse:
    """
    TextResponse 是一个用于指定 HTTP 响应内容类型的注解类。它允许开发者在定义endpoint函数时，
    明确指定返回的响应数据的 MIME 类型，默认为 'text/plain'。

    示例用法：
    async def text_endpoint() -> Annotated[str, TextResponse()]:
        return 'This is a text response.'
    """
```

### `annotation.Html`

```python
class Html(TextResponse):
    def __init__(self):
        super().__init__('text/html')
```

### `annotation.PlainText`

```python
class PlainText(TextResponse):
    def __init__(self):
        super().__init__('text/plain')
```
