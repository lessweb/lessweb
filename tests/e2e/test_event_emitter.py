from typing import Annotated

import pytest
from aiohttp import web
from aiohttp.web import Request, StreamResponse

from lessweb import Bridge
from lessweb.annotation import Get, OnEvent
from lessweb.event import EventEmitter


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
    bridge.scan(EventEmitter, handle_test_event, trigger_test_event)
    client = await aiohttp_client(app)
    resp = await client.get('/')
    assert resp.status == 200
    resp_data = await resp.json()
    assert resp_data['message'] == 'Received: Hello, World'
