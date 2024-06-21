import importlib
import inspect
import logging
import re
import sys
from dataclasses import dataclass, is_dataclass
from logging.handlers import TimedRotatingFileHandler
from os import environ, listdir
from typing import (Any, Awaitable, Callable, Dict, Literal, Optional, Type,
                    TypeVar, Union, cast, get_type_hints)

import orjson
import toml
import typing_inspect
from aiohttp.typedefs import LooseHeaders
from aiohttp.web import (Application, HTTPBadRequest, HTTPError, Request,
                         Response, middleware, run_app)

from .typecast import (is_typeddict, isinstance_safe, semi_json_schema_type,
                       typecast)

ENDPOINT_TYPE = Callable[..., Awaitable[Any]]
HANDLER_TYPE = Callable[[Request], Awaitable[Any]]
HTTP_METHOD_TYPE = Literal['GET', 'POST',
                           'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', '*']

T = TypeVar('T')
ORJSON_OPTION = 0
POSITIONAL_ONLY = 0
KEYWORD_ONLY = 3


def cast_http_method(method: str) -> HTTP_METHOD_TYPE:
    method = method.upper()
    tp_args = typing_inspect.get_args(HTTP_METHOD_TYPE)
    assert method in tp_args, f'Invalid HTTP method: {method}'
    return cast(HTTP_METHOD_TYPE, method)


def make_environ_key(key_path: str):
    return '_'.join(re.findall('[A-Z]+', key_path.upper()))


def func_arg_spec(fn) -> dict:
    """
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
    arg_spec = {}  # name: (type_, default, kind)
    for name, param in inspect.signature(fn).parameters.items():
        arg_spec[name] = (
            param.annotation,  # otherwise => inspect.Signature.empty
            param.default,  # otherwise => inspect.Signature.empty
            param.kind  # 0=POSITIONAL_ONLY 1=POSITIONAL_OR_KEYWORD 2=VAR_POSITIONAL 3=KEYWORD_ONLY 4=VAR_KEYWORD
        )
    return arg_spec


def import_ref(ref_name: str):
    module_ref, var_name = ref_name.rsplit('.', 1)
    module = importlib.import_module(module_ref)
    return getattr(module, var_name)


def absolute_ref(cls) -> str:
    return f'{cls.__module__}.{cls.__qualname__}'


def get_depends_on(fn):
    depends_on = []
    for name, (depends_type, _, _) in func_arg_spec(fn).items():
        if name != 'self':
            depends_on.append((name, depends_type))
    return depends_on


def init_orjson_option(option_text: str):
    global ORJSON_OPTION
    if option_text:
        for option_word in option_text.split(','):
            assert hasattr(orjson, f'OPT_{option_word}')
            option_flag = getattr(orjson, f'OPT_{option_word}')
            ORJSON_OPTION |= option_flag
    return ORJSON_OPTION


def rest_response(
        data,
        *,
        status: int = 200,
        reason: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
) -> Response:
    resp = Response(
        body=orjson.dumps(data, option=ORJSON_OPTION),
        status=status,
        reason=reason,
        headers=headers,
        content_type='application/json',
    )
    resp['data'] = data
    return resp


def rest_error(
        error: Type[HTTPError],
        data,
        *,
        headers: Optional[LooseHeaders] = None,
        **kwargs,
) -> HTTPError:
    return error(
        body=orjson.dumps(data, option=ORJSON_OPTION),
        headers=headers,
        content_type='application/json',
        **kwargs,
    )


def service(f: T) -> T:
    """
    Service life cycle example:

    >>> @service
    ... class Foo:
    ...   def __init__(self, request: Request): ...
    >>> async def foo_filter(handler, foo: Foo): ...
    >>> bridge.add_middleware(foo_filter)

    """
    f.__lessweb_service__ = 1  # type: ignore[attr-defined]
    return f


def config(f: T) -> T:
    """
    Config life cycle example:

    >>> @config
    ... class FooConfig:
    ...   def __init__(self, config: dict, app: Application): ...
    >>> async def foo_startup(foo_config: FooConfig): ...
    >>> async def foo_cleanup(foo_config: FooConfig): ...
    >>> bridge.add_config_ctx(foo_startup, foo_cleanup)

    """
    f.__lessweb_config__ = 1  # type: ignore[attr-defined]
    return f


def autowire(ctx: Union[Application, Request], cls: Type[T], name: Optional[str] = None) -> T:
    """
    依赖注入。
    通过注入完成后，调用__init__实例化。后续直接使用实例化结果。
    实例生命范围分为应用级(application)和请求级(request)。
    特别地，依赖Application和Request不需要加载模块。
    """
    ref = absolute_ref(cls)
    app_ctx = ctx.app if isinstance(ctx, Request) else ctx
    assert ref != 'config', f'Cannot inject {cls} since `config` is reserved word!'
    if name:  # try to inject by name
        if name == 'config' and is_typeddict(cls):
            name_ref = f'{name}:{ref}'
            if name_ref in app_ctx:
                return app_ctx[name_ref]
            else:
                app_ctx[name_ref] = data = typecast(ctx[name], cls)
                return data
        elif name in ctx:
            assert isinstance_safe(ctx[name], cls)
            return ctx[name]
        elif isinstance(ctx, Request) and name in ctx.config_dict:
            assert isinstance_safe(ctx.config_dict[name], cls)
            return ctx.config_dict[name]
    if ref in ctx:
        return ctx[ref]
    elif isinstance(ctx, Request) and ref in ctx.config_dict:
        return ctx.config_dict[ref]
    logging.debug('autowire-> %s %s', ctx, cls)
    if hasattr(cls, '__lessweb_config__'):
        ctx = app_ctx
    if isinstance(ctx, cls):
        return ctx
    elif isinstance(ctx, Request) and not hasattr(cls, '__lessweb_service__'):
        raise TypeError(
            f'cannot autowire class which is not a service: {ref} {ctx=} {cls=}')
    elif isinstance(ctx, Application) and not hasattr(cls, '__lessweb_config__'):
        raise TypeError(
            f'cannot autowire class which is not a config: {ref} {ctx=} {cls=}')
    depends_on = get_depends_on(cls.__init__)
    args: list = []
    for name, depends_type in depends_on:
        args.append(autowire(ctx, depends_type, name))
    ctx[ref] = singleton = cls(*args)
    return singleton


def make_handler(request, handler):
    async def aio_handler():
        return await handler(request)

    return aio_handler


def make_middleware(sp_middleware):
    """
    按照handler变量名注入，可使用await handler()获取下一层运行结果
    """

    @middleware
    async def aio_middleware(request, handler):
        logging.debug('middleware-> %s', request)
        args, kwargs = [], {}
        for name, (depends_type, _, kind) in func_arg_spec(sp_middleware).items():
            if name == 'handler':
                args.append(make_handler(request, handler))
            else:
                kwargs[name] = autowire(request, depends_type, name)
        return await sp_middleware(*args, **kwargs)

    return aio_middleware


def make_app_signal(sp_handler):
    """
    :return: 形如foo(app)这样的函数
    """

    async def aio_handler(app):
        kwargs = {}
        for name, (depends_type, _, kind) in func_arg_spec(sp_handler).items():
            kwargs[name] = autowire(app, depends_type, name)
        return await sp_handler(**kwargs)

    return aio_handler


@dataclass
class Route:
    method: HTTP_METHOD_TYPE
    paths: list
    summary: Optional[str]
    params: dict
    request_body: Optional[Type]
    response_body: Optional[Type]
    handler: HANDLER_TYPE
    endpoint: ENDPOINT_TYPE
    extra: dict


def make_router(method: str, paths: list, sp_endpoint: ENDPOINT_TYPE) -> Route:
    """
    :param method: HTTP方法
    :param paths: 路径列表
    :param sp_endpoint: 用户定义的endpoint
    :return: 形如foo(request)这样的函数
    :raise: `TypeCastError`
    """
    if not inspect.iscoroutinefunction(sp_endpoint):
        raise TypeError(f'endpoint must be coroutine function: {sp_endpoint=}')
    params: dict = {}
    request_body: Optional[Type] = None
    response_body: Optional[Type] = None
    for name, (depends_type, default, kind) in func_arg_spec(sp_endpoint).items():
        if kind == POSITIONAL_ONLY and request_body is None:
            request_body = depends_type
        elif kind == KEYWORD_ONLY:
            params[name] = {
                'name': name, 'required': default is not None, 'schema': semi_json_schema_type(depends_type)}

    if get_type_hints(sp_endpoint).get('return') is not None:
        response_body = get_type_hints(sp_endpoint)['return']

    async def aio_endpoint(request: Request):
        args = []
        kwargs: Dict[str, Any] = {}
        has_read_request_body = False
        for name, (depends_type, default, kind) in func_arg_spec(sp_endpoint).items():
            if kind == POSITIONAL_ONLY:
                if (request_stack := request.get('lessweb.request_stack')) and isinstance(request_stack, list):
                    request_text = request_stack.pop()
                elif not has_read_request_body:
                    request_text = await request.text()
                    has_read_request_body = True
                else:
                    raise TypeError(f'EOF when reading request body: {name=}')
                try:
                    data = orjson.loads(request_text)
                except orjson.JSONDecodeError:
                    raise HTTPBadRequest(
                        text=f'BadRequest: request body raise JSONDecodeError')
                try:
                    args.append(typecast(data, depends_type))
                except Exception as e:
                    raise HTTPBadRequest(
                        text=f'BadRequest: request body decoding error: {e}')
            elif kind == KEYWORD_ONLY:
                chosen_value = request.match_info[name] if name in request.match_info else request.query.get(
                    name)
                if chosen_value is None:
                    if default is not None:
                        raise HTTPBadRequest(
                            text=f'BadRequest: missing required parameter: {name}')
                    else:
                        kwargs[name] = None
                else:
                    try:
                        kwargs[name] = typecast(chosen_value, depends_type)
                    except Exception:
                        raise HTTPBadRequest(
                            text=f'BadRequest: invalid parameter: {name}')
            else:
                kwargs[name] = autowire(request, depends_type, name)
        result = await sp_endpoint(*args, **kwargs)
        if isinstance(result, (dict, list)) or is_dataclass(result):
            return rest_response(result)
        else:
            return result

    route = Route(
        method=cast_http_method(method),
        paths=paths,
        summary=inspect.getdoc(sp_endpoint),
        params=params,
        request_body=request_body,
        response_body=response_body,
        handler=aio_endpoint,
        endpoint=sp_endpoint,
        extra={},
    )
    return route


def contains_sub_string(s: str, sub: str) -> bool:
    p = q = 0
    while p < len(s) and q < len(sub):
        if s[p] == sub[q]:
            q += 1
        p += 1
    return q == len(sub)


def assert_endpoint_name_compatible(sp_endpoint: ENDPOINT_TYPE, method: str, path: str) -> None:
    """
    限制endpoint函数名必须字面上包含method+path。
    作用：1.避免无谓的思考;2.杜绝在endpoint上滥用修饰器。

    :raise: NameError
    """
    if method == '*':
        return
    path = re.sub(r':.*?\}', '}', path.lower())
    method_path_slug = f'{method.lower()}_' + \
        '_'.join(re.findall('[a-z0-9]+', path))
    if not contains_sub_string(sp_endpoint.__name__,  method_path_slug):
        raise NameError(
            f'endpoint name "{sp_endpoint.__name__}" should contain "{method_path_slug}" to compatible with [{method} {path}]')


def rest_mapping(method: str, paths: list) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, method, '')
        return make_router(method, paths, sp_endpoint)

    return g


def get_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, 'GET', path)
        return rest_mapping(method='GET', paths=[path])(sp_endpoint)

    return g


def post_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, 'POST', path)
        return rest_mapping(method='POST', paths=[path])(sp_endpoint)

    return g


def put_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, 'PUT', path)
        return rest_mapping(method='PUT', paths=[path])(sp_endpoint)

    return g


def patch_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, 'PATCH', path)
        return rest_mapping(method='PATCH', paths=[path])(sp_endpoint)

    return g


def delete_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        assert_endpoint_name_compatible(sp_endpoint, 'DELETE', path)
        return rest_mapping(method='DELETE', paths=[path])(sp_endpoint)

    return g


class Bridge:
    app: Application
    config: Optional[str]

    def __init__(self, config: Optional[str] = None, app: Optional[Application] = None) -> None:
        if app is None:
            self.app = Application()
        else:
            self.app = app
        self.config = config
        self._load_config()
        self.app['lessweb.bridge'] = self
        self.app['lessweb.routes'] = []

    def _load_config(self) -> None:
        self.app['config'] = self._load_config_with_env()
        self._load_logger()
        self._load_orjson()

    def _load_config_with_env(self) -> dict[str, Any]:
        if self.config:
            config = toml.loads(open(self.config).read())
        else:
            config = {}
        config.setdefault('bootstrap', {})
        dfs = [('', config)]  # list[(prefix, data)]
        while dfs:
            prefix, data = dfs.pop()
            assert isinstance(data, dict), f'config{prefix} must be dict!'
            for key, value in list(data.items()):
                key_path = f'{prefix}.{key}'
                if isinstance(value, dict):
                    dfs.append((key_path, value))
                else:
                    env_key = make_environ_key(key_path)
                    if env_key in environ:
                        data[key] = environ[env_key]
        return config

    def _load_logger(self) -> None:
        logger_conf = self.app['config'].get('logger', {})
        logger = logging.getLogger(logger_conf.get('name'))
        logger.setLevel(logger_conf.get('level', 'INFO'))
        stream_str = logger_conf.get('stream', 'stdout')
        formatter = None  # https://docs.python.org/zh-cn/3/library/logging.html#logrecord-attributes
        if logger_conf.get('format'):
            formatter = logging.Formatter(logger_conf['format'])
        if stream_str == 'file':
            file_handler = TimedRotatingFileHandler(
                logger_conf['file'],
                when=logger_conf.get('when', 'd'),
                interval=logger_conf.get('interval', 1),
                backupCount=logger_conf.get('backup_count', 10)
            )
            file_handler.suffix = "%Y%m%d"
            if formatter:
                file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logging.root = logger  # type: ignore
        else:
            stream = sys.stdout if stream_str == 'stdout' else sys.stderr
            stream_handler = logging.StreamHandler(stream)
            if formatter:
                stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

    def _load_orjson(self) -> None:
        init_orjson_option(self.app['config']
                           ['bootstrap'].get('orjson_option', ''))

    def add_middleware(self, handler) -> None:
        self.app.middlewares.append(make_middleware(handler))

    def add_on_startup(self, handler) -> None:
        self.app.on_startup.append(make_app_signal(handler))

    def add_on_cleanup(self, handler) -> None:
        self.app.on_cleanup.append(make_app_signal(handler))

    def add_config_ctx(self, handler_on_startup, handler_on_cleanup) -> None:
        async def aio_handler(app):
            await make_app_signal(handler_on_startup)(app)
            yield
            await make_app_signal(handler_on_cleanup)(app)

        self.app.cleanup_ctx.append(aio_handler)

    def add_on_shutdown(self, handler) -> None:
        self.app.on_shutdown.append(make_app_signal(handler))

    def add_route(self, route: Route) -> None:
        for path in route.paths:
            self.app.router.add_route(
                method=route.method, path=path, handler=route.handler)
            self.app['lessweb.routes'].append(route)

    def add_route_scan(self, endpoint_package: str) -> None:
        endpoint_mdl = importlib.import_module(endpoint_package)
        if endpoint_mdl.__spec__ is None or not endpoint_mdl.__spec__.submodule_search_locations:
            raise ImportError(f'{endpoint_package} is an empty package')
        for filename in listdir(endpoint_mdl.__spec__.submodule_search_locations[0]):
            if filename.endswith('.py'):
                sub_mdl = importlib.import_module(
                    f'{endpoint_package}.{filename[:-3]}')
                for item in sub_mdl.__dict__.values():
                    if isinstance(item, Route):
                        self.add_route(item)

    def run_app(self, **kwargs) -> None:
        port = int(self.app['config']['bootstrap'].get('port', 8080))
        run_app(app=self.app, port=port, **kwargs)
