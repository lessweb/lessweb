from typing import Annotated

import pytest
from aiohttp import web
from aiohttp.web import Request, StreamResponse
from aiojobs.aiohttp import setup as setup_aiojobs

from lessweb import Bridge
from lessweb.annotation import Get, OnEvent
from lessweb.event import EventEmitter
from lessweb.ioc import Middleware, rest_response


class AddExclamation(Middleware):
    async def on_request(self, request: Request, handler):
        response = await handler(request)
        response['data']['message'] += '!'
        return response


class AddAsterisk(Middleware):
    async def on_request(self, request: Request, handler):
        response = await handler(request)
        response['data']['message'] += '*'
        return rest_response(response['data'])


async def handle_test_event(request: Request) -> Annotated[
        dict, OnEvent('test_event')]:
    payload = await request.json()
    return {'message': f"Received: {payload['message']}"}


async def trigger_test_event(emitter: EventEmitter) -> Annotated[StreamResponse, Get('/')]:
    payload = {'message': 'Hello, World'}
    response = await emitter.emit('test_event', payload)
    return response


@pytest.mark.asyncio
async def test_event_emitter(aiohttp_client):
    app = web.Application()
    bridge = Bridge(app=app)
    bridge.scan(handle_test_event, trigger_test_event,
                AddAsterisk, AddExclamation)
    client = await aiohttp_client(app)
    resp = await client.get('/')
    assert resp.status == 200
    resp_data = await resp.json()
    assert resp_data['message'] == 'Received: Hello, World!*!*'
