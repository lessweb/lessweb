import inspect
import logging
from dataclasses import is_dataclass
from typing import (Annotated, Any, Awaitable, Callable, Dict, Optional, Tuple,
                    Type, TypeAlias, TypeVar, Union, get_origin,
                    get_type_hints)

import pydantic
from aiohttp.typedefs import LooseHeaders
from aiohttp.web import (Application, HTTPBadRequest, HTTPError, Request,
                         Response, StreamResponse, middleware)

from lessweb.annotation import DefaultFactory, Endpoint, OnEvent, TextResponse
from lessweb.typecast import TypeCast
from lessweb.utils import absolute_ref

ENDPOINT_TYPE: TypeAlias = Callable[..., Awaitable[Any]]
HANDLER_TYPE: TypeAlias = Callable[[Request], Awaitable[Any]]
POSITIONAL_ONLY = 0
KEYWORD_ONLY = 3


REQUEST_STACK_KEY = 'lessweb.request_stack'
APP_CONFIG_KEY = 'lessweb.config'
APP_BRIDGE_KEY = 'lessweb.bridge'
APP_EVENT_SUBSCRIBER_KEY = 'lessweb.event_subscriber'
APP_ON_STARTUP_KEY = 'lessweb.on_startup'
APP_ON_CLEANUP_KEY = 'lessweb.on_cleanup'
APP_ON_SHUTDOWN_KEY = 'lessweb.on_shutdown'
BACKGROUND_ANNOTAION_KEY = 'lessweb.background'


class Module:
    """
    进程级别的单例模块，兼容aiohttp的signals
    """

    def __init__(self) -> None:
        pass

    async def on_startup(self, app: Application) -> None:
        pass

    async def on_cleanup(self, app: Application) -> None:
        pass

    async def on_shutdown(self, app: Application) -> None:
        pass

    def load_config(self, app: Application) -> Any:
        """
        Example of override:
        >>> def load_config(self, app: Application) -> Annotated[MyAppConfig, 'myapp']:
        ...   return lessweb.load_module_config(app, 'myapp', MyAppConfig)
        """
        pass


class Middleware:
    """
    请求级别的单例中间件，兼容aiohttp的middlewares
    """

    def __init__(self) -> None:
        pass

    async def on_request(self, request: Request, handler: HANDLER_TYPE) -> Response:
        return await handler(request)


class Service:
    """
    业务逻辑单例服务
    """

    def __init__(self) -> None:
        pass


def annotated_origin(anno) -> Any:
    """
    Example:
    >>> annotated_origin(Annotated[int, 'meta'])
    <class 'int'>
    """
    try:
        if get_origin(anno) == Annotated:
            return anno.__origin__
    except Exception:
        pass
    return anno


def func_arg_spec(fn) -> Dict[str, Tuple]:
    """
    获取函数参数的类型、默认值和参数类型
     - 如果参数没有指定类型，则返回Any
     - 如果参数的类型是Annotated，则返回Annotated的原始类型

    >>> def foo(a, /, b, c=2, *d, e, f=3, **g):
    ...   pass
    ...
    >>> for name, (anno, default, kind) in func_arg_spec(foo).items():
    ...   print(name, kind, default)
    ...
    a POSITIONAL_ONLY <class 'inspect._empty'>
    b POSITIONAL_OR_KEYWORD <class 'inspect._empty'>
    c POSITIONAL_OR_KEYWORD 2
    d VAR_POSITIONAL <class 'inspect._empty'>
    e KEYWORD_ONLY <class 'inspect._empty'>
    f KEYWORD_ONLY 3
    g VAR_KEYWORD <class 'inspect._empty'>
    """
    assert inspect.isfunction(fn), \
        f'{fn} is not a function or classmethod or staticmethod'
    arg_spec = {}  # name: (type_, default, kind)
    for name, param in inspect.signature(fn).parameters.items():
        arg_spec[name] = (
            annotated_origin(
                Any if param.annotation is inspect.Parameter.empty else param.annotation),
            param.default,  # otherwise => inspect.Signature.empty
            param.kind  # 0=POSITIONAL_ONLY 1=POSITIONAL_OR_KEYWORD 2=VAR_POSITIONAL 3=KEYWORD_ONLY 4=VAR_KEYWORD
        )
    return arg_spec


def func_arg_annotated_metas(fn) -> Dict[str, Tuple]:
    """
    Example:
    >>> def foo(a: Annotated[int, 'meta'], b: str=''):
    ...   pass
    ...
    >>> func_arg_annotated_metas(foo)
    {'a': ('meta',)}
    """
    result = {}
    for name, anno in get_type_hints(fn, include_extras=True).items():
        if name == 'return':
            continue
        if get_origin(anno) == Annotated:
            result[name] = anno.__metadata__
    return result


def func_annotated_metas(fn) -> Tuple[Type, Tuple]:
    """
    Example:
    >>> def foo(a: int) -> Annotated[bool, 'meta']:
    ...   pass
    ...
    >>> func_annotated_metas(foo)
    (<class 'bool'>, ('meta',))
    """
    anno = get_type_hints(fn, include_extras=True).get('return', Any)
    if get_origin(anno) == Annotated:
        return anno.__origin__, anno.__metadata__
    else:
        return anno, tuple()


def spawn_default_factory(arg_annotated_metas: Dict[str, Tuple], arg_name: str):
    """
    Example:
    >>> def foo(a: Annotated(list, DefaultFactory(list), b: list):
    ...   pass
    ...
    >>> spawn_default_factory(func_arg_annotated_metas(foo), 'a')
    []
    >>> spawn_default_factory(func_arg_annotated_metas(foo), 'b')
    <class 'inspect._empty'>
    """
    if arg_name in arg_annotated_metas:
        metas = arg_annotated_metas[arg_name]
        for meta in metas:
            if isinstance(meta, DefaultFactory):
                return meta.factory_func()
    return inspect.Signature.empty


def get_depends_on(fn) -> list:
    """
    Example:
    >>> def foo(a: int, b: str=''):
    ...   pass
    ...
    >>> get_depends_on(foo)
    [('a', <class 'int'>), ('b', <class 'str'>)]
    """
    depends_on = []
    for name, (depends_type, _, _) in func_arg_spec(fn).items():
        if name != 'self':
            depends_on.append((name, depends_type))
    return depends_on


def make_middleware(cls: Type[Middleware]) -> Callable:
    @middleware
    async def middleware_func(request, handler):
        singleton = autowire(request, cls)
        return await singleton.on_request(request, handler)
    return middleware_func


T = TypeVar('T', bound=Module)


def autowire_module(app: Application, cls: Type[T]) -> T:
    """
    进程级别单例模块注入。
    副作用：将cls的实例注册到app中，同时注册on_startup, on_cleanup, on_shutdown
    """
    # assert inspect.isclass(cls) and issubclass(
    #     cls, Module), f'autowire_module can only autowire Module: {cls}'
    ref = absolute_ref(cls)
    if ref in app:
        if app[ref] is None:
            raise RuntimeError(f'circular dependency detected: {cls}')
        return app[ref]  # type: ignore
    app[ref] = None  # mark as inited
    logging.debug('autowire_module-> %s', cls)
    depends_on = get_depends_on(cls.__init__)
    args: list = []
    for _, depends_type in depends_on:
        args.append(autowire_module(app, depends_type))
    app[ref] = singleton = cls(*args)
    app[APP_ON_STARTUP_KEY].append(singleton.on_startup)
    app[APP_ON_CLEANUP_KEY].append(singleton.on_cleanup)
    app[APP_ON_SHUTDOWN_KEY].append(singleton.on_shutdown)
    return singleton


U = TypeVar('U')


def autowire(request: Request, cls: Type[U]) -> U:
    """
    Request-level dependency injection, automatically instantiating Middleware or Service objects.
    """
    assert inspect.isclass(cls), f'Can only autowire normal class: {cls}'
    if cls is Request:
        return request  # type: ignore
    assert issubclass(cls, (Middleware, Service)), \
        f'Can only autowire Middleware or Service: {cls}'
    ref = absolute_ref(cls)
    if ref in request:
        if request[ref] is None:
            raise RuntimeError(f'circular dependency detected: {cls}')
        return request[ref]
    request[ref] = None  # mark as inited
    logging.debug('autowire-> %s', cls)
    depends_on = get_depends_on(cls.__init__)
    args: list = []
    for _, depends_type in depends_on:
        if inspect.isclass(depends_type) and issubclass(depends_type, Module):
            args.append(autowire_module(request.app, depends_type))
        else:
            args.append(autowire(request, depends_type))
    request[ref] = singleton = cls(*args)
    return singleton  # type: ignore


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


def get_request_stack(request: Request) -> list[Union[str, bytes]]:
    if (request_stack := request.get(REQUEST_STACK_KEY)) and isinstance(request_stack, list):
        return request_stack
    request[REQUEST_STACK_KEY] = []
    return request[REQUEST_STACK_KEY]


def push_request_stack(request: Request, value: Union[str, bytes]):
    if not isinstance(value, bytes):
        raise TypeError('value must be str or bytes')
    request_stack = get_request_stack(request)
    request_stack.append(value)


def autowire_handler(sp_endpoint: ENDPOINT_TYPE, background: bool = False) -> HANDLER_TYPE:
    """
    Decorate an async function to make it a handler, which can be used as aiohttp's route.
    This function will be called with request as the first argument.
    The other arguments will be passed in according to func_arg_spec of the function.
    If the argument is a positional-only argument, it will be passed in from the request body.
    If the argument is a keyword-only argument, it will be passed in from the query string.
    If the argument is a Module, it will be passed in by autowire_module.
    If the argument is a Service or Middleware, it will be passed in by autowire.
    If the function returns a StreamResponse, it will be returned directly.
    If the function returns a dict or list, it will be returned as a json response.
    If the function returns a JSON-serializable object, such as a pydantic.BaseModel, it will be validated and returned as a json response.
    If the function returns None, it will be returned as a 204 response.
    If the function returns a string, it will be returned as a text response.
    """
    async def aio_route_endpoint(request: Request) -> StreamResponse:
        args: list = []
        kwargs: Dict[str, Any] = {}
        arg_annotated_metas = func_arg_annotated_metas(sp_endpoint)
        response_type = func_annotated_metas(sp_endpoint)[0]
        for name, (depends_type, default, kind) in func_arg_spec(sp_endpoint).items():
            if kind == POSITIONAL_ONLY:
                request_stack = get_request_stack(request)
                request_data: Union[str, bytes]
                if not args and not request_stack:
                    request_data = await request.read()
                elif not request_stack:
                    raise TypeError(
                        f'request stack is empty for param: {name}')
                else:
                    request_data = request_stack.pop()
                if depends_type in (bytes, str):
                    if not isinstance(request_data, depends_type):
                        raise TypeError(
                            f'positional only param: {name} must be {depends_type} not {type(request_data)}')
                try:
                    parsed_data = TypeCast.validate_json(
                        request_data, depends_type)
                    args.append(parsed_data)
                except ValueError as e:
                    logging.debug(f'invalid request body: {name=} {e}')
                    raise rest_error(
                        HTTPBadRequest, {'message': f'invalid request body'})
            elif kind == KEYWORD_ONLY:
                query_value = request.match_info[name] if name in request.match_info \
                    else request.query.get(name)
                if query_value is None:
                    if default is inspect.Signature.empty:
                        default = spawn_default_factory(
                            arg_annotated_metas, name)
                    if default is inspect.Signature.empty:
                        raise rest_error(
                            HTTPBadRequest, {'message': f'missing required parameter: {name}'})
                    else:
                        kwargs[name] = default
                else:
                    try:
                        kwargs[name] = TypeCast.validate_query(
                            query_value, depends_type)
                    except Exception:
                        raise rest_error(
                            HTTPBadRequest, {'message': f'invalid parameter: {name}'})
            elif inspect.isclass(depends_type) and issubclass(depends_type, Module):
                kwargs[name] = autowire_module(request.app, depends_type)
            else:
                kwargs[name] = autowire(request, depends_type)
        result = await sp_endpoint(*args, **kwargs)
        if isinstance(result, StreamResponse):
            return result
        if inspect.isclass(response_type) and issubclass(response_type, pydantic.BaseModel):
            return rest_response(response_type.model_validate(result))
        elif isinstance(result, (dict, list)) or is_dataclass(result) or isinstance(result, pydantic.BaseModel):
            return rest_response(result)
        elif result is None:
            return Response(status=204)
        else:
            text_response_metas = get_text_response_metas(sp_endpoint)
            if text_response_metas:
                return Response(text=str(result), content_type=text_response_metas[0].content_type, charset='utf-8')
            else:
                return Response(text=str(result), content_type='text/plain', charset='utf-8')

    if background:
        setattr(aio_route_endpoint, BACKGROUND_ANNOTAION_KEY, True)
    return aio_route_endpoint


def get_endpoint_metas(fn) -> list[Endpoint]:
    _, func_metas = func_annotated_metas(fn)
    return [meta for meta in func_metas if isinstance(meta, Endpoint)]


def get_event_subscriber_metas(fn) -> list[OnEvent]:
    _, func_metas = func_annotated_metas(fn)
    return [meta for meta in func_metas if isinstance(meta, OnEvent)]


def get_text_response_metas(fn) -> list[TextResponse]:
    _, func_metas = func_annotated_metas(fn)
    result = []
    for meta in func_metas:
        if isinstance(meta, TextResponse):
            result.append(meta)
        elif inspect.isclass(meta) and issubclass(meta, TextResponse):
            result.append(meta())
    return result
