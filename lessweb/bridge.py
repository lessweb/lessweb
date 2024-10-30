import inspect
import logging
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from os import environ
from typing import Any, Literal, Optional, Type, TypeVar

import pydantic
import toml
from aiohttp.test_utils import make_mocked_request
from aiohttp.web import AppKey, Application, Request, run_app
from dotenv import find_dotenv, load_dotenv

from .ioc import (APP_BRIDGE_KEY, Middleware, Module, Service, autowire,
                  autowire_handler, autowire_module, get_endpoint_metas,
                  init_orjson_option)
from .typecast import typecast
from .utils import scan_import


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
    orjson_option: str = ''
    logger: Optional[LesswebLoggerConfig] = None


T = TypeVar('T')


class Bridge:
    app: Application
    config_file: Optional[str]
    config: dict[str, Any]
    bootstrap_config: LesswebBootstrapConfig

    @staticmethod
    def get_bridge(app: Application) -> 'Bridge':
        return app[APP_BRIDGE_KEY]

    def __init__(self, config: Optional[str] = None, app: Optional[Application] = None) -> None:
        if app is None:
            self.app = Application()
        else:
            self.app = app
        self.config_file = config

        self.app[APP_BRIDGE_KEY] = self
        self.bootstrap_config = self._load_config()
        self._load_logger(self.bootstrap_config)
        self._load_orjson(self.bootstrap_config)

    def _load_config(self) -> LesswebBootstrapConfig:
        if env := environ.get('ENV'):
            env_file = find_dotenv(f'.env.{env}')
            assert load_dotenv(
                env_file), f'load dotenv file failed: {env_file}'
        else:
            load_dotenv()
        self.config = self._load_config_with_env()
        return self.load_module_config('lessweb', LesswebBootstrapConfig)

    def _load_config_with_env(self) -> dict[str, Any]:
        if self.config_file:
            if not os.path.exists(self.config_file):
                raise FileNotFoundError(
                    f'config file not found: {self.config_file}')
            config = toml.loads(open(self.config_file).read())
        else:
            config = {}
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
        init_orjson_option(config.orjson_option)

    def load_module_config(self, module_config_key: str, module_config_cls: Type[T]) -> T:
        module_config = self.config.get(module_config_key, {})
        app_key = AppKey(f'{module_config_key}.config', module_config_cls)
        if app_key in self.app:
            return self.app[app_key]
        result: T
        if inspect.isclass(module_config_cls) and issubclass(module_config_cls, pydantic.BaseModel):
            result = module_config_cls.model_validate(
                module_config)  # type: ignore
        else:
            result = typecast(module_config, module_config_cls)
        self.app[app_key] = result
        return result

    def make_event_request(self, path: str, **kwargs) -> Request:
        return make_mocked_request('POST', f'/{os.path.join("__event__", path)}', **kwargs, app=self.app)

    def scan(self, *packages) -> None:
        imported_modules = scan_import(packages)
        mocked_request = self.make_event_request('/')
        for _, obj in imported_modules.items():
            if inspect.isclass(obj):
                if issubclass(obj, Module):
                    autowire_module(self.app, obj)
                elif issubclass(obj, (Middleware, Service)):
                    autowire(mocked_request, obj)
            elif inspect.isfunction(obj):
                endpoint_metas = get_endpoint_metas(obj)
                if endpoint_metas and not inspect.iscoroutinefunction(obj):
                    raise TypeError(
                        f'endpoint must be coroutine function: {obj}')
                for endpoint_meta in endpoint_metas:
                    self.app.router.add_route(
                        method=endpoint_meta.method,
                        path=endpoint_meta.path,
                        handler=autowire_handler(obj),
                    )
            else:
                pass

    def run_app(self, **kwargs) -> None:
        run_app(
            app=self.app,
            port=self.bootstrap_config.port,
            **kwargs
        )
