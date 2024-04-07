import importlib
import inspect
import logging
import re
import sys
from dataclasses import dataclass, is_dataclass
from logging.handlers import TimedRotatingFileHandler
from os import environ, listdir
from typing import (Any, Awaitable, Callable, Dict, Optional, Type, TypeVar,
                    Union)

import orjson
import toml
from aiohttp.typedefs import LooseHeaders
from aiohttp.web import (Application, HTTPBadRequest, HTTPError, Request,
                         Response, middleware, run_app)

from .typecast import is_typeddict, isinstance_safe, typecast

ENDPOINT_TYPE = Callable[..., Awaitable[Any]]
HANDLER_TYPE = Callable[[Request], Awaitable[Any]]

T = TypeVar('T')
ORJSON_OPTION = 0
POSITIONAL_ONLY = 0
KEYWORD_ONLY = 3


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
    f.__lessweb_service__ = 1  # type: ignore[attr-defined]
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
    if isinstance_safe(ctx, cls):
        return ctx  # type: ignore
    elif isinstance(ctx, Request) and cls is Application:
        return ctx.app  # type: ignore
    elif not hasattr(cls, '__lessweb_service__'):
        raise TypeError(f'cannot autowire ({ref}) {ctx=} {cls=})')
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


def getdoc(obj) -> str:
    """
    获得模块或对象的docstring
    实现了递归包含，只需要以「:include 」开头
    """
    if isinstance(obj, str):
        try:
            module_or_object = importlib.import_module(obj)
        except ModuleNotFoundError:
            module_name, object_name = obj.rsplit('.', 1)
            module_or_object = getattr(
                importlib.import_module(module_name), object_name)
        return getdoc(module_or_object)
    result = []
    docstring = inspect.getdoc(obj) or ''
    for line in docstring.splitlines():
        if line.strip().startswith(':include '):
            include_doc = getdoc(line.replace(':include ', '').strip())
            result.append(include_doc)
        else:
            result.append(line)
    return '\n'.join(result) + '\n'


def make_router(sp_endpoint: ENDPOINT_TYPE) -> HANDLER_TYPE:
    """
    :param sp_endpoint:
        1.POSITIONAL_ONLY参数表示requestbody
        2.int和str类型参数表示路径参数
        3.其他参数支持可注入类型
    :return: 形如foo(request)这样的函数
    """

    async def aio_endpoint(request: Request):
        assert inspect.iscoroutinefunction(
            sp_endpoint), f'{sp_endpoint} must be coroutine function'
        args = []
        kwargs: Dict[str, Any] = {}
        for name, (depends_type, default, kind) in func_arg_spec(sp_endpoint).items():
            if kind == POSITIONAL_ONLY:
                try:
                    data = orjson.loads(await request.text())
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

    return aio_endpoint


@dataclass
class Route:
    method: str
    paths: list
    handler: HANDLER_TYPE


def rest_mapping(method: str, paths: list) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        handler = make_router(sp_endpoint)
        route = Route(method=method.upper(), paths=paths, handler=handler)
        route.__doc__ = inspect.getdoc(sp_endpoint)
        return route

    return g


def get_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        return rest_mapping(method='GET', paths=[path])(sp_endpoint)

    return g


def post_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        return rest_mapping(method='POST', paths=[path])(sp_endpoint)

    return g


def put_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        return rest_mapping(method='PUT', paths=[path])(sp_endpoint)

    return g


def patch_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        return rest_mapping(method='PATCH', paths=[path])(sp_endpoint)

    return g


def delete_mapping(path: str) -> Callable[[ENDPOINT_TYPE], Route]:
    def g(sp_endpoint) -> Route:
        return rest_mapping(method='DELETE', paths=[path])(sp_endpoint)

    return g


class Bridge:
    app: Application
    config: Optional[str]

    def __init__(self, config: Optional[str] = None, app: Optional[Application] = None):
        if app is None:
            self.app = Application()
        else:
            self.app = app
        self.config = config
        self._load_config()

    def _load_config(self):
        self.app['bootstrap'] = self
        self.app['config'] = self._load_config_with_env()
        self._load_logger()
        self._load_orjson()

    def _load_config_with_env(self):
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

    def _load_logger(self):
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

    def _load_orjson(self):
        init_orjson_option(self.app['config']
                           ['bootstrap'].get('orjson_option', ''))

    def add_middleware(self, handler):
        self.app.middlewares.append(make_middleware(handler))

    def add_on_startup(self, handler):
        self.app.on_startup.append(make_app_signal(handler))

    def add_on_cleanup(self, handler):
        self.app.on_cleanup.append(make_app_signal(handler))

    def add_mod_ctx(self, handler_on_startup, handler_on_cleanup):
        async def aio_handler(app):
            await make_app_signal(handler_on_startup)(app)
            yield
            await make_app_signal(handler_on_cleanup)(app)

        self.app.cleanup_ctx.append(aio_handler)

    def add_on_shutdown(self, handler):
        self.app.on_shutdown.append(make_app_signal(handler))

    def add_route(self, route: Route) -> None:
        for path in route.paths:
            self.app.router.add_route(
                method=route.method, path=path, handler=route.handler)

    def add_route_scan(self, endpoint_package: str):
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

    def run_app(self, **kwargs):
        port = int(self.app['config']['bootstrap'].get('port', 8080))
        run_app(app=self.app, port=port, **kwargs)
