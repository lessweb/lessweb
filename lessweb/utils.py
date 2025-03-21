import importlib
import inspect
import os
from typing import Any, Callable, Union


def absolute_ref(cls) -> str:
    return f'{cls.__module__}.{cls.__qualname__}'


def list_dirs(path: str) -> list[str]:
    """
    Example:
    >>> list_dirs('/root/lessweb')
    ['dir1', 'dir2']
    """
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]


def is_first_touch(key: str, cache: set) -> bool:
    """
    Return True if key is first seen, else False.
    Given a cache set, add the key to it if not already in it.
    """
    if key in cache:
        return False
    cache.add(key)
    return True


def list_files(path: str) -> list[str]:
    """
    Example:
    >>> list_files('/root/lessweb')
    ['file1.py', 'file2.py']
    """
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def scan_import(packages: tuple[Union[str, Callable]]) -> dict[str, Any]:
    """
    Example:
    >>> scan_import(['myapp.utils'])
    {'myapp.utils.Cls1': <class 'myapp.utils.Cls1'>, 'myapp.utils.Cls2': <class 'myapp.utils.Cls2'>}
    """
    result: dict[str, Any] = {}
    for package_name in packages:
        if not isinstance(package_name, str):
            obj = package_name
            assert inspect.isclass(obj) or inspect.isfunction(obj)
            obj_ref = absolute_ref(obj)
            result[obj_ref] = obj
            continue
        imported_module = importlib.import_module(package_name)
        assert imported_module.__spec__ and imported_module.__spec__.submodule_search_locations
        package_path = imported_module.__spec__.submodule_search_locations[0]
        for filename in list_files(package_path):
            if filename.endswith('.py'):
                sub_module = importlib.import_module(
                    f'{package_name}.{filename[:-3]}')
                for obj in sub_module.__dict__.values():
                    if inspect.isclass(obj) or inspect.isfunction(obj):
                        obj_ref = absolute_ref(obj)
                        result[obj_ref] = obj
        for dirname in list_dirs(package_path):
            if '.' not in dirname and os.path.isfile(os.path.join(package_path, f'{dirname}/__init__.py')):
                imported_sub_modules = scan_import(
                    (f'{package_name}.{dirname}', ))
                result.update(imported_sub_modules)
    return result


def import_ref(ref_name: str):
    """
    Example:
    >>> import_ref('myapp.utils.Cls1')
    <class 'myapp.utils.Cls1'>
    """
    module_ref, var_name = ref_name.rsplit('.', 1)
    module = importlib.import_module(module_ref)
    return getattr(module, var_name)
