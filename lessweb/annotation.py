from typing import Any, Callable, Literal

HTTP_METHOD_TYPE = Literal['GET', 'POST',
                           'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE', 'CONNECT']


class Endpoint:
    method: HTTP_METHOD_TYPE
    path: str

    def __init__(self, method: HTTP_METHOD_TYPE, path: str):
        self.method = method
        self.path = path


class Get(Endpoint):
    def __init__(self, path: str):
        super().__init__('GET', path)


class Post(Endpoint):
    def __init__(self, path: str):
        super().__init__('POST', path)


class Put(Endpoint):
    def __init__(self, path: str):
        super().__init__('PUT', path)


class Delete(Endpoint):
    def __init__(self, path: str):
        super().__init__('DELETE', path)


class Patch(Endpoint):
    def __init__(self, path: str):
        super().__init__('PATCH', path)


# TODO:
# class Path:
#     pass

# TODO:
# class Query:
#     pass

# TODO:
# class Header:
#     pass

# TODO:
# class Cookie:
#     pass


class DefaultFactory:
    factory_func: Callable[[], Any]

    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func


class OnEvent:
    event: str
    background: bool

    def __init__(self, event: str, background: bool = False):
        self.event = event
        self.background = background


class TextResponse:
    content_type: str

    def __init__(self, content_type: str = 'text/plain'):
        self.content_type = content_type


class Html(TextResponse):
    def __init__(self):
        super().__init__('text/html')


class PlainText(TextResponse):
    def __init__(self):
        super().__init__('text/plain')


class Bean:
    pass
