import logging
from typing import Callable

from aiohttp.web import (
    HTTPBadRequest,
    HTTPException,
    HTTPInternalServerError,
    Request,
    Response,
    middleware,
)
from lessweb import rest_error
from pydantic import BaseModel


class Failed(BaseModel):
    code: int = -1
    message: str


@middleware
async def error_middleware(request: Request, handler: Callable) -> Response:
    try:
        response = await handler(request)
        if isinstance(response, Failed):
            raise rest_error(HTTPBadRequest, response)
    except AssertionError as e:
        raise rest_error(HTTPBadRequest, Failed(code=-1, message=str(e)))
    except HTTPException:
        raise
    except Exception as e:
        error_type = e.__class__.__name__
        logging.exception(f'global error: [{error_type}] {e}')
        raise rest_error(HTTPInternalServerError, Failed(code=-1, message=f'[{error_type}] {e}'))
    return response
