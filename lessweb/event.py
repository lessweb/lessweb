import json
import os
from typing import Any, Type

from aiohttp.test_utils import make_mocked_request
from aiohttp.web import Application, Response, StreamResponse, UrlDispatcher
from aiojobs.aiohttp import spawn as aiojobs_spawn

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
    事件发射器
    """
    app: Application
    subscriber_annotation: Type[OnEvent] = OnEvent
    router: UrlDispatcher

    async def on_startup(self, app: Application) -> None:
        self.app = app
        self.build_router(app)

    def build_router(self, app: Application) -> None:
        self.app = app
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
        event_path = os.path.join(EVENT_PATH_PREFIX, event)
        request = make_mocked_request(
            'POST', event_path,
            headers={'Content-Type': 'application/json'},
            app=self.app
        )
        print('emit:', event_path, payload)
        request._read_bytes = json.dumps(payload).encode()
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
