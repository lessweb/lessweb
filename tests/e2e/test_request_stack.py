from aiohttp.web import Request
import json

import pytest
from aiohttp import web
from aiohttp.web import HTTPInternalServerError

from lessweb import Bridge, post_mapping, put_mapping


@put_mapping('/user')
async def put_edit_user(vo, /):
    return {'data': vo}


@post_mapping('/user')
async def post_create_user(real_vo, raw_vo, /):
    return [real_vo, raw_vo]


@post_mapping('/user/_eof')
async def post_user_expect_eof(real_vo, raw_vo, eof_vo, /):
    return {}


async def request_body_filter(handler, request: Request):
    raw_request = await request.json()
    raw_request['name'] = raw_request['name'].upper()
    request['lessweb.request_stack'] = [
        json.dumps(raw_request, ensure_ascii=False)]
    try:
        return await handler()
    except TypeError as e:
        raise HTTPInternalServerError(text=str(e))


@pytest.mark.asyncio
async def test_hello(aiohttp_client):
    app = web.Application()
    bridge = Bridge(app=app)
    bridge.add_route(put_edit_user)
    bridge.add_route(post_create_user)
    bridge.add_route(post_user_expect_eof)
    bridge.add_middleware(request_body_filter)
    client = await aiohttp_client(app)
    resp = await client.put('/user', json={'name': 'John'})
    assert resp.status == 200
    response_body = await resp.json()
    assert response_body == {"data": {"name": "JOHN"}}

    resp = await client.post('/user', json={'name': 'John'})
    assert resp.status == 200
    response_body = await resp.json()
    assert response_body == [{"name": "JOHN"}, {"name": "John"}]

    resp = await client.post('/user/_eof', json={'name': 'John'})
    assert resp.status == 500
    response_text = await resp.text()
    assert response_text == 'EOF when reading request body: name=\'eof_vo\''
