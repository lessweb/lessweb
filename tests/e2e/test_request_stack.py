from typing import Annotated

import orjson
import pydantic
import pytest
from aiohttp import web
from aiohttp.web import HTTPInternalServerError, Request

from lessweb import Bridge
from lessweb.annotation import Post, Put
from lessweb.ioc import Middleware, Service, push_request_stack
from lessweb.typecast import TypeCast


class UserInput(pydantic.BaseModel):
    name: str


async def put_edit_user(vo: UserInput, /) -> Annotated[dict, Put('/user')]:
    return {'data': vo}


async def post_create_user(real_vo: UserInput, raw_vo: UserInput, /) -> Annotated[list, Post('/user')]:
    return [real_vo, raw_vo]


async def post_user_expect_eof(real_vo: UserInput, raw_vo: UserInput, eof_vo: UserInput, /) -> Annotated[dict, Post('/user/_eof')]:
    return {}


class UpperService(Service):
    def upper(self, name: str) -> str:
        return name.upper()


class UpperFilter(Middleware):
    upper_service: UpperService

    def __init__(self, upper_service: UpperService) -> None:
        self.upper_service = upper_service

    async def on_request(self, request: Request, handler):
        raw_request = await request.read()
        push_request_stack(request, raw_request)
        obj = orjson.loads(raw_request)
        obj['name'] = self.upper_service.upper(obj['name'])
        push_request_stack(request, TypeCast.dumps(obj))
        try:
            return await handler(request)
        except TypeError as e:
            raise HTTPInternalServerError(text=str(e))


@pytest.mark.asyncio
async def test_request_stack(aiohttp_client):
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
