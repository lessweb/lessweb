import inspect
import logging
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from os import environ
from pathlib import Path
from typing import Any, Callable, Literal, Optional, Type, TypeVar, get_type_hints

import pydantic
import toml
from aiohttp.test_utils import make_mocked_request
from aiohttp.web import (
    AppKey,
    Application,
    HTTPException,
    HTTPInternalServerError,
    Request,
    Response,
    middleware,
    run_app,
)
from aiojobs.aiohttp import setup as aiojobs_setup
from dotenv import find_dotenv, load_dotenv
from pydantic.json_schema import models_json_schema

from .ioc import (
    APP_BRIDGE_KEY,
    APP_CONFIG_KEY,
    APP_EVENT_SUBSCRIBER_KEY,
    APP_ON_CLEANUP_KEY,
    APP_ON_SHUTDOWN_KEY,
    APP_ON_STARTUP_KEY,
    BEAN_MAP_KEY,
    LESSWEB_SCAN_PATH,
    Middleware,
    Module,
    Service,
    autowire,
    autowire_handler,
    autowire_module,
    get_depends_types_from_endpoint,
    get_endpoint_metas,
    get_event_subscriber_metas,
    get_pydantic_models_from_endpoint,
    make_middleware,
)
from .typecast import TypeCast
from .utils import absolute_ref, is_first_touch, scan_import


@middleware
async def global_error_handler(request: Request, handler: Callable) -> Response:
    try:
        response = await handler(request)
    except HTTPException:
        raise
    except Exception as e:
        error_type = absolute_ref(type(e))
        logging.exception(f'global error: [{error_type}] {e}')
        raise HTTPInternalServerError(text=f'[{error_type}] {e}')
    return response


def make_environ_key(key_path: str):
    return '_'.join(re.findall('[A-Z]+', key_path.upper()))


class LesswebLoggerRotatingConfig(pydantic.BaseModel):
    when: str = 'd'
    interval: int = 1
    backup_count: int = 30
    suffix: str = "%Y%m%d"


class LesswebLoggerConfig(pydantic.BaseModel):
    # https://docs.python.org/zh-cn/3/library/logging.html#logrecord-attributes
    format: str = '%(asctime)s %(name)s %(filename)s:%(lineno)d %(levelname)s - %(message)s'
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'
    stream: Literal['stdout', 'stderr', 'file'] = 'stdout'
    name: Optional[str] = None
    file: Optional[str] = None
    rotating: Optional[LesswebLoggerRotatingConfig] = None


class LesswebBootstrapConfig(pydantic.BaseModel):
    port: int = 8080
    enable_global_error_handling: bool = True
    orjson_option: str = ''
    logger: Optional[LesswebLoggerConfig] = None


T = TypeVar('T')


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
    module_config = app[APP_CONFIG_KEY].get(module_config_key, {})
    app_key = AppKey(f'{module_config_key}.config', module_config_cls)
    if app_key in app:
        return app[app_key]
    result: T
    if inspect.isclass(module_config_cls) and issubclass(module_config_cls, pydantic.BaseModel):
        result = module_config_cls.model_validate(
            module_config)  # type: ignore
    else:
        raise TypeError(f'{module_config_cls=} is not supported')
    app[app_key] = result
    return result


class Bridge:
    app: Application
    config_file: Optional[str]
    config: dict[str, Any]
    bootstrap_config: LesswebBootstrapConfig
    endpoint_models: list[Type[pydantic.BaseModel]]

    @staticmethod
    def get_bridge(app: Application) -> 'Bridge':
        return app[APP_BRIDGE_KEY]

    def __init__(self, config: Optional[str] = None, app: Optional[Application] = None) -> None:
        """
        config: path to config file/directory
        app: aiohttp application
        """
        if app is None:
            self.app = Application()
        else:
            self.app = app
        self.config_file = config

        self.app[APP_BRIDGE_KEY] = self
        self.app[APP_EVENT_SUBSCRIBER_KEY] = []
        self.app[APP_ON_STARTUP_KEY] = []
        self.app[APP_ON_CLEANUP_KEY] = []
        self.app[APP_ON_SHUTDOWN_KEY] = []
        self.app[BEAN_MAP_KEY] = {}
        self.bootstrap_config = self._load_config()
        self._load_logger(self.bootstrap_config)
        self._load_orjson(self.bootstrap_config)
        if self.bootstrap_config.enable_global_error_handling:
            logging.debug('add global_error_handling middleware')
            self.app.middlewares.append(global_error_handler)
        self.endpoint_models = []

    def _load_config(self) -> LesswebBootstrapConfig:
        if env := environ.get('ENV'):
            env_file = find_dotenv(f'.env.{env}')
            assert load_dotenv(
                env_file, override=True), f'load dotenv file failed: {env_file}'
        else:
            load_dotenv(override=True)
        self.config = self._load_config_with_env()
        self.app[APP_CONFIG_KEY] = self.config
        return load_module_config(self.app, 'lessweb', LesswebBootstrapConfig)

    def _load_config_with_env(self) -> dict[str, Any]:
        config = {}
        if self.config_file:
            if not os.path.exists(self.config_file):
                raise FileNotFoundError(
                    f'config file not found: {self.config_file}')
            elif os.path.isdir(self.config_file):
                config_dir = Path(self.config_file)
                for config_path in config_dir.iterdir():
                    if config_path.is_file():
                        with open(config_path) as f:
                            config.update(toml.loads(f.read()))
            else:
                config.update(toml.loads(open(self.config_file).read()))
        config.setdefault('lessweb', {})
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

    def _load_logger(self, config: LesswebBootstrapConfig) -> None:
        logger_conf = config.logger
        if not logger_conf:
            return
        logger = logging.getLogger(logger_conf.name)
        logger.setLevel(logger_conf.level)
        formatter = logging.Formatter(logger_conf.format)
        if logger_conf.stream == 'file':
            rotating_conf = logger_conf.rotating or LesswebLoggerRotatingConfig()
            file_handler = TimedRotatingFileHandler(
                logger_conf.file or 'log.txt',
                when=rotating_conf.when,
                interval=rotating_conf.interval,
                backupCount=rotating_conf.backup_count
            )
            file_handler.suffix = rotating_conf.suffix
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logging.root = logger  # type: ignore
        else:
            stream = sys.stdout if logger_conf.stream == 'stdout' else sys.stderr
            stream_handler = logging.StreamHandler(stream)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

    def _load_orjson(self, config: LesswebBootstrapConfig) -> None:
        TypeCast.init_orjson_option(config.orjson_option)

    def _autowire_handler_depends(self, request: Request, handler: Callable) -> None:
        ref = absolute_ref(handler)
        logging.debug('autowire_handler_depends-> %s %s', ref, handler)
        for depends_type in get_depends_types_from_endpoint(handler):
            assert inspect.isclass(depends_type), f'Handler {ref} cannot autowire non-class depends: {depends_type}'
            if depends_type is Request or depends_type is Application:
                continue
            elif issubclass(depends_type, Module):
                autowire_module(self.app, depends_type)
            else:
                autowire(request, depends_type)

    def beans(self, *beans) -> None:
        for bean_func in beans:
            if inspect.iscoroutinefunction(bean_func):
                raise TypeError(
                    f'bean function must not be coroutine function: {bean_func}')
            for name, bean_type in get_type_hints(bean_func, include_extras=False).items():
                if name == 'return':
                    if not inspect.isclass(bean_type):
                        raise TypeError(f'bean return type must be class: {bean_func} {bean_type}')
                    bean_type_ref = absolute_ref(bean_type)
                    self.app[BEAN_MAP_KEY][bean_type_ref] = bean_func

    def middlewares(self, *middlewares) -> None:
        for m in middlewares:
            if inspect.isclass(m) and issubclass(m, Middleware):
                self.app.middlewares.append(make_middleware(m))
            elif inspect.isfunction(m):
                self.app.middlewares.append(m)
            else:
                raise TypeError(f'middleware must be subclass of Middleware or function: {m}')

    def scan(self, *packages) -> None:
        imported_modules = scan_import(packages)
        temp_req = make_mocked_request('POST', LESSWEB_SCAN_PATH, app=self.app)
        ref_set: set[str] = set()
        for ref, obj in imported_modules.items():
            # logging.debug('scanning: %s %s', ref, obj)
            if inspect.isclass(obj):
                if issubclass(obj, Module) and obj is not Module:
                    autowire_module(self.app, obj)
                elif issubclass(obj, (Service, Middleware)):
                    # Avoid situations where modules with indirect dependencies are not loaded automatically
                    autowire(temp_req, obj)
            elif inspect.isfunction(obj):
                endpoint_metas = get_endpoint_metas(obj)
                event_subscriber_metas = get_event_subscriber_metas(obj)
                if endpoint_metas:
                    if not inspect.iscoroutinefunction(obj):
                        raise TypeError(
                            f'endpoint must be coroutine function: {obj}')
                    if is_first_touch(ref, ref_set):
                        self._autowire_handler_depends(temp_req, obj)
                        for endpoint_meta in endpoint_metas:
                            self.app.router.add_route(
                                method=endpoint_meta.method,
                                path=endpoint_meta.path,
                                handler=autowire_handler(obj),
                            )
                        self.endpoint_models.extend(get_pydantic_models_from_endpoint(obj))
                if event_subscriber_metas:
                    if not inspect.iscoroutinefunction(obj):
                        raise TypeError(
                            f'event subscriber must be coroutine function: {obj}')
                    if is_first_touch(ref, ref_set):
                        self._autowire_handler_depends(temp_req, obj)
                        for event_subscriber_meta in event_subscriber_metas:
                            self.app[APP_EVENT_SUBSCRIBER_KEY].append(
                                (event_subscriber_meta,
                                 autowire_handler(obj, background=event_subscriber_meta.background)))
            else:
                pass

    def dump_openapi_components(self) -> dict:
        """
        Returns a dict containing the OpenAPI components for the application.

        The returned dict will have the following structure:
        {
            "components": {
                "schemas": {...}
            }
        }

        The schemas dict will contain the OpenAPI schema definitions for each of the
        endpoint models in the application.

        :return: dict containing OpenAPI components
        """
        _, schemas = models_json_schema(
            [(model, "validation") for model in self.endpoint_models],
            ref_template="#/components/schemas/{model}",
        )
        return {
            "components": {
                "schemas": schemas.get('$defs'),
            }
        }

    def ready(self) -> None:
        aiojobs_setup(self.app)
        for signal_handler in self.app[APP_ON_STARTUP_KEY]:
            self.app.on_startup.append(signal_handler)
        for signal_handler in reversed(self.app[APP_ON_CLEANUP_KEY]):
            self.app.on_cleanup.append(signal_handler)
        for signal_handler in reversed(self.app[APP_ON_SHUTDOWN_KEY]):
            self.app.on_shutdown.append(signal_handler)

    def run_app(self, ready=True, **kwargs) -> None:
        if ready:
            self.ready()
        run_app(
            app=self.app,
            port=self.bootstrap_config.port,
            **kwargs
        )
