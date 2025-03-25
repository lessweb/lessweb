import json
import logging
import os
from typing import Any, Type

from aiohttp.test_utils import make_mocked_request
from aiohttp.web import Application, Response, StreamResponse, UrlDispatcher
from aiojobs.aiohttp import spawn as aiojobs_spawn

from lessweb.typecast import TypeCast

from .annotation import OnEvent
from .ioc import APP_EVENT_SUBSCRIBER_KEY, BACKGROUND_ANNOTAION_KEY, Module

EVENT_PATH_PREFIX = '/__event__'


def wrap_middleware(m):
    def wrap_handler(h):
        async def wrapper(request):
            return await m(request, h)
        return wrapper
    return wrap_handler


def make_event_handler(middlewares, handler):
    for m in reversed(middlewares):
        handler = wrap_middleware(m)(handler)
    return handler


class EventEmitter(Module):
    """
    事件发射器类，用于注册事件处理函数并触发事件。

    该类继承自 Module，在应用启动时会为所有标记为事件订阅（使用 OnEvent 装饰器）的处理函数构建 HTTP POST 路由，
    从而实现事件的统一管理。触发事件时，该类会模拟一个 HTTP POST 请求，将事件名称和负载数据传递给相应的处理函数，
    支持同步返回响应，也能将事件处理后台异步执行。
    """
    app: Application
    subscriber_annotation: Type[OnEvent] = OnEvent
    router: UrlDispatcher

    async def on_startup(self, app: Application) -> None:
        self.app = app
        self.build_router()

    def build_router(self) -> None:
        self.router = UrlDispatcher()
        for meta, handler in self.app[APP_EVENT_SUBSCRIBER_KEY]:
            if isinstance(meta, self.subscriber_annotation):
                if meta.event.startswith('/'):
                    raise ValueError('event path must not start with ‘/’')
                event_path = os.path.join(EVENT_PATH_PREFIX, meta.event)
                self.router.add_route(
                    method='POST',
                    path=event_path,
                    handler=handler,
                )

    async def emit(self, event: str, payload: Any) -> StreamResponse:
        """
        触发指定的事件。
        通过构造模拟的 HTTP POST 请求，将 payload 序列化为 JSON 数据传入对应的事件处理路由中，
        根据处理函数是否标记为后台异步执行，返回相应的响应（异步时返回 204 状态码）。
        """
        event_path = os.path.join(EVENT_PATH_PREFIX, event)
        request = make_mocked_request(
            'POST', event_path,
            headers={'Content-Type': 'application/json'},
            app=self.app
        )
        logging.debug('emit:', event_path, payload)
        request._read_bytes = TypeCast.dumps(payload)
        match_info = await self.router.resolve(request)
        match_info.add_app(self.app)
        request._match_info = match_info
        is_background = getattr(
            match_info.handler, BACKGROUND_ANNOTAION_KEY, False)
        handler = make_event_handler(self.app.middlewares, match_info.handler)
        if is_background:
            await aiojobs_spawn(request, handler(request))
            return Response(status=204)
        else:
            return await handler(request)
