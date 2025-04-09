import typing
from importlib import import_module

if typing.TYPE_CHECKING:
    from .bridge import Bridge, load_module_config
    from .event import EventEmitter
    from .ioc import (Middleware, Module, Service, autowire, autowire_module,
                      get_request_stack, push_request_stack, rest_error,
                      rest_response)
    from .typecast import TypeCast, inspect_type, is_typeddict

__all__ = (
    # bridge
    'Bridge',
    'load_module_config',
    # event
    'EventEmitter',
    # ioc
    'Middleware',
    'Module',
    'Service',
    'autowire',
    'autowire_module',
    'get_request_stack',
    'push_request_stack',
    'rest_error',
    'rest_response',
    # typecast
    'TypeCast',
    'inspect_type',
    'is_typeddict',
)

# A mapping of {<member name>: (package, <module name>)} defining dynamic imports
_dynamic_imports: 'dict[str, tuple[str, str]]' = {
    # bridge
    'Bridge': (__spec__.parent, '.bridge'),
    'load_module_config': (__spec__.parent, '.bridge'),
    # event
    'EventEmitter': (__spec__.parent, '.event'),
    # ioc
    'Middleware': (__spec__.parent, '.ioc'),
    'Module': (__spec__.parent, '.ioc'),
    'Service': (__spec__.parent, '.ioc'),
    'autowire': (__spec__.parent, '.ioc'),
    'autowire_module': (__spec__.parent, '.ioc'),
    'get_request_stack': (__spec__.parent, '.ioc'),
    'push_request_stack': (__spec__.parent, '.ioc'),
    'rest_error': (__spec__.parent, '.ioc'),
    'rest_response': (__spec__.parent, '.ioc'),
    # typecast
    'TypeCast': (__spec__.parent, '.typecast'),
    'inspect_type': (__spec__.parent, '.typecast'),
    'is_typeddict': (__spec__.parent, '.typecast'),
}


def __getattr__(attr_name: str) -> object:
    dynamic_attr = _dynamic_imports.get(attr_name)
    if dynamic_attr is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{attr_name}'")

    package, module_name = dynamic_attr

    if module_name == '__module__':
        result = import_module(f'.{attr_name}', package=package)
        globals()[attr_name] = result
        return result
    else:
        module = import_module(module_name, package=package)
        result = getattr(module, attr_name)
        g = globals()
        for k, (_, v_module_name) in _dynamic_imports.items():
            if v_module_name == module_name:
                g[k] = getattr(module, k)
        return result


def __dir__() -> 'list[str]':
    return list(__all__)
