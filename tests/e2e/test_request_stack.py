import json
from typing import Annotated

import pytest
from aiohttp import web
from aiohttp.web import HTTPInternalServerError, Request

from lessweb import Bridge
from lessweb.annotation import Post, Put
from lessweb.ioc import Middleware, Service, push_request_stack


async def put_edit_user(vo, /) -> Annotated[dict, Put('/user')]:
    return {'data': vo}


async def post_create_user(real_vo, raw_vo, /) -> Annotated[list, Post('/user')]:
    return [real_vo, raw_vo]


async def post_user_expect_eof(real_vo, raw_vo, eof_vo, /) -> Annotated[dict, Post('/user/_eof')]:
    return {}


class UpperService(Service):
    def upper(self, name: str) -> str:
        return name.upper()


class UpperFilter(Middleware):
    upper_service: UpperService

    def __init__(self, upper_service: UpperService) -> None:
        self.upper_service = upper_service

    async def on_request(self, request: Request, handler):
        raw_request = await request.json()
        push_request_stack(request, raw_request.copy())
        raw_request['name'] = self.upper_service.upper(raw_request['name'])
        push_request_stack(request, raw_request.copy())
        try:
            return await handler(request)
        except TypeError as e:
            raise HTTPInternalServerError(text=str(e))


@pytest.mark.asyncio
async def test_hello(aiohttp_client):
    app = web.Application()
    bridge = Bridge(app=app)
    bridge.scan(
        put_edit_user,
        post_create_user,
        post_user_expect_eof,
        UpperFilter,
    )
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
    assert response_text == 'request stack is empty for param: eof_vo'
