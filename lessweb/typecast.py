import datetime
import enum
import inspect
from typing import Any, Union, get_type_hints, List, Type, Dict
import typing_inspect
import csv
import json


class JSONDecodeError(Exception):
    pass


NoneType = type(None)


classname_dict: Dict[str, Type] = {}


def parse_csv(csv_text):
    return list(csv.reader([csv_text]))[0]


def issubclass_safe(x, tp_tuple) -> bool:
    try:
        return issubclass(x, tp_tuple)
    except:
        return False


def isinstance_safe(x, tp_tuple) -> bool:
    try:
        return tp_tuple is Any or tp_tuple is inspect.Signature.empty or isinstance(x, tp_tuple)
    except:
        return False


def future_typed_dict_keys(tp):
    """
    由于typing_inspect.typed_dict_keys()在alpine上有bug，只能自实现代替版本
    """
    try:
        if issubclass(tp, dict):
            return tp.__annotations__.copy()
        else:
            return None
    except:
        return None


def is_typeddict(tp) -> bool:
    return issubclass_safe(tp, dict) and future_typed_dict_keys(tp)


def inspect_type(tp):
    """
    inspect_type(int) => int
    inspect_type(list) => list
    inspect_type(list[int]) => (list, int)
    inspect_type(int | None) => (Union, (int, NoneType))
    inspect_type(int | str) => (Union, (int, str))
    inspect_type(int | str | None) => (Union, (int, str, NoneType))
    inspect_type(dict) => dict
    inspect_type(dict[str, int]) => NotImplementedError
    inspect_type(typeddict) => (dict, __annotations__)
    inspect_type(else) => NotImplementedError
    """
    if isinstance_safe(tp, str):
        tp = classname_dict[tp]
    tp_origin = typing_inspect.get_origin(tp)
    tp_args = typing_inspect.get_args(tp)
    if tp_origin is None and tp_args == ():
        if is_typeddict(tp):
            classname_dict[tp.__qualname__] = tp
            return dict, get_type_hints(tp)
        return tp
    if tp_origin is list:
        return list, tp_args[0]
    if (tp_origin is None or tp_origin == Union) and tp_args:
        return Union, tp_args
    raise NotImplementedError(f'cannot inspect type {tp=}')


def is_list_type(tp):
    return tp is list or typing_inspect.get_origin(tp) is list


def typecast(data, tp):
    if isinstance_safe(tp, str):
        if tp not in classname_dict:
            raise JSONDecodeError(f'typename {tp=} is not valid ref')
        else:
            tp = classname_dict[tp]
    if isinstance_safe(data, tp):
        return data
    elif issubclass_safe(tp, enum.Enum):
        return tp(data)
    elif issubclass_safe(tp, datetime.datetime):
        return datetime.datetime.fromisoformat(data)
    elif issubclass_safe(tp, datetime.date):
        return datetime.date.fromisoformat(data)
    elif issubclass_safe(tp, datetime.time):
        return datetime.time.fromisoformat(data)
    elif isinstance(data, str):
        if issubclass_safe(tp, str):
            return tp(data)
        elif is_list_type(tp):
            data = parse_csv(data)
            return typecast(data, tp)
        else:
            data = json.loads(data)
            return typecast(data, tp)
    else:
        type_inspect_seed = inspect_type(tp)
        if isinstance(type_inspect_seed, tuple):
            origin_type, type_args = type_inspect_seed
            if origin_type is list:
                assert isinstance(data, list)
                return [typecast(item, type_args) for item in data]
            elif origin_type == Union:
                error_list = []
                for type_arg in type_args:
                    try:
                        return typecast(data, type_arg)
                    except Exception as e:
                        error_list.append(str(e))
                raise JSONDecodeError(f'{data=} is not any instance of {tp=}: ' + '; '.join(error_list))
            elif origin_type == dict:
                assert isinstance(data, dict)
                optional_keys = getattr(tp, '__optional_keys__')
                if optional_keys:
                    required_keys = set(type_args.keys()) - optional_keys
                else:
                    required_keys = getattr(tp, '__required_keys__', set())
                missing_keys = required_keys - set(data.keys())
                none_value_keys = set()
                result = {}
                for item_key, item_value in data.items():
                    if item_key not in type_args:
                        raise JSONDecodeError(f'{item_key=} is not member of {tp=}')
                    result[item_key] = typecast(item_value, type_args[item_key])
                for item_key in missing_keys:
                    if typing_inspect.is_optional_type(type_args[item_key]):
                        result[item_key] = None
                        none_value_keys.add(item_key)
                if missing_keys - none_value_keys:
                    raise JSONDecodeError(f'missing required keys {list(missing_keys - none_value_keys)}')
                return result
            else:
                raise JSONDecodeError(f'type {tp=} is not supported ({data=})')
        else:
            raise JSONDecodeError(f'{data=} is not instance of {tp=}')


def echo_typing_inspect():
    import typing
    int_args = typing_inspect.get_args(int)
    int_origin = typing_inspect.get_origin(int)
    print(f'{int_args=}')  # int_args=()
    print(f'{int_origin=}')  # int_origin=None
    list_args = typing_inspect.get_args(list)
    list_origin = typing_inspect.get_origin(list)
    print(f'{list_args=}')  # list_args=()
    print(f'{list_origin=}')  # list_origin=None
    list_int_args = typing_inspect.get_args(list[int])
    list_int_origin = typing_inspect.get_origin(list[int])
    print(f'{list_int_args=}')  # list_int_args=(<class 'int'>,)
    print(f'{list_int_origin=}')  # list_int_origin=<class 'list'>
    int_optional_args = typing_inspect.get_args(int | None)
    int_optional_origin = typing_inspect.get_origin(int | None)
    is_optional = typing_inspect.is_optional_type(int | None)
    print(f'{int_optional_args=}')  # int_optional_args=(<class 'int'>, <class 'NoneType'>)
    print(f'{int_optional_origin=}')  # int_optional_origin=None
    print(f'{is_optional=}')  # is_optional=True
    union_optional_args = typing_inspect.get_args(int | str)
    union_optional_origin = typing_inspect.get_origin(int | str)
    print(f'{union_optional_args=}')  # union_optional_args=(<class 'int'>, <class 'str'>)
    print(f'{union_optional_origin=}')  # union_optional_origin=None
    union_optional_args = typing_inspect.get_args(Union[int, str])
    union_optional_origin = typing_inspect.get_origin(Union[int, str])
    print(f'{union_optional_args=}')  # union_optional_args=(<class 'int'>, <class 'str'>)
    print(f'{union_optional_origin=}')  # union_optional_origin=typing.Union
    class Pet(typing.TypedDict):
        name: str
        age: int
    pet_optional_args = typing_inspect.get_args(Pet)
    pet_optional_origin = typing_inspect.get_origin(Pet)
    is_dict = issubclass_safe(Pet, dict)
    print(f'{pet_optional_args=}')  # pet_optional_args=()
    print(f'{pet_optional_origin=}')  # pet_optional_origin=None
    print(f'{is_dict=} {get_type_hints(Pet)} {get_type_hints(dict)}')  # is_dict=True {'name': <class 'str'>, 'age': <class 'int'>} {}
    is_list = issubclass_safe(list[int], list)
    print(f'{is_list=}')  # is_list=False
    print(f'is_list={is_list_type(List[int])} {is_list_type(List)}')  # is_list=True


def test_typecast():
    import typing
    class Pet(typing.TypedDict):
        name: str
        size: list[int]
        child: Union[list['test_typecast.<locals>.Pet'], None]
    data = {'name': 'duck', 'size': '10,20,15', 'child': [{'name': 'duckII', 'size': '5,10,8', 'child': None}]}
    pet = typecast(data, Pet)
    print(pet)


if __name__ == '__main__':
    # echo_typing_inspect()
    test_typecast()
