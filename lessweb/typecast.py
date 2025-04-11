import csv
import datetime
import enum
import inspect
from types import NoneType
from typing import (
    Any,
    Dict,
    List,
    Literal,
    NewType,
    Type,
    TypeGuard,
    TypeVar,
    Union,
    get_type_hints,
)

import orjson
import pydantic
import typing_inspect

T = TypeVar('T')


classname_dict: Dict[str, Type] = {}


def _pydantic_encoder(obj):
    if isinstance(obj, pydantic.BaseModel):
        return obj.model_dump()
    raise TypeError


def parse_csv(csv_text: str) -> List[str]:
    """
    Parse a single line of CSV text into a list of strings.

    :param csv_text: a single line of CSV text
    :return: a list of strings
    """
    return list(csv.reader([csv_text]))[0]


def future_typed_dict_keys(tp):
    """
    Due to a bug with typing_inspect.typed_dict_keys() on Alpine, we had to implement our own version as a workaround.
    """
    try:
        if issubclass(tp, dict):
            return tp.__annotations__.copy()
        else:
            return None
    except Exception:
        return None


def is_typeddict(tp) -> bool:
    return inspect.isclass(tp) and issubclass(tp, dict) and future_typed_dict_keys(tp)


def inspect_type(tp):
    """
    inspect_type(int) => (int,)
    inspect_type(list) => (list,)
    inspect_type(list[int]) => (list, int)
    inspect_type(int | None) => (Union, (int, NoneType))
    inspect_type(int | str) => (Union, (int, str))
    inspect_type(int | str | None) => (Union, (int, str, NoneType))
    inspect_type(None | str | int) => (Union, (str, int, NoneType))
    inspect_type(Literal['a', 'b']) => (Literal, ('a', 'b'))
    inspect_type(NewType) => (NewType, __supertype__)
    inspect_type(dict) => (dict,)
    inspect_type(dict[str, int]) => NotImplementedError
    inspect_type(typeddict) => (dict, __annotations__)
    inspect_type(cls) => (cls,)
    inspect_type(_else_) => NotImplementedError
    """
    if isinstance(tp, str):
        tp = classname_dict[tp]
    tp_origin = typing_inspect.get_origin(tp)
    tp_args = typing_inspect.get_args(tp)
    if tp_origin is None and tp_args == ():
        if is_typeddict(tp):
            classname_dict[tp.__qualname__] = tp
            return dict, get_type_hints(tp)
        elif hasattr(tp, '__supertype__'):
            return NewType, tp.__supertype__
        return (tp,)
    elif tp_origin is list:
        return list, tp_args[0]
    elif (tp_origin is None or tp_origin == Union) and tp_args:
        return Union, tp_args
    elif tp_origin == Literal and tp_args:
        return Literal, tp_args
    raise NotImplementedError(f'cannot inspect type {tp=}')


def is_list_type(tp) -> TypeGuard[Type[list]]:
    return tp is list or typing_inspect.get_origin(tp) is list


def literal_to_str(data) -> str:
    if isinstance(data, enum.Enum):
        return data.name
    elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
        return data.isoformat()
    else:
        return str(data)


def semi_json_schema_type(tp):
    """
    semi_json_schema_type(list) => {'type': 'array'}
    semi_json_schema_type(list[int]) => {'type': 'array', 'items': {'type': int}}
    semi_json_schema_type(Union[int, None]) => {'type': int, 'optional': True}
    semi_json_schema_type(Union[int, str]) => {'union': [{'type': int}, {'type': str}], 'optional': False}
    semi_json_schema_type(Union[None, int, str]) => {'union': [{'type': int}, {'type': str}], 'optional': True}
    semi_json_schema_type(Literal['a', 'b']) => {'enum': ['a', 'b']}
    semi_json_schema_type(Any) => {}
    semi_json_schema_type(cls) => {'type': cls}
    """
    origin_type, *type_args_wrapped = inspect_type(tp)
    if not type_args_wrapped:
        if origin_type == list:
            return {'type': 'array'}
        elif origin_type == Any:
            return {}
        else:
            return {'type': tp}
    type_args = type_args_wrapped[0]
    if origin_type == list:
        return {'type': 'array', 'items': semi_json_schema_type(type_args)}
    elif origin_type == Union:
        if NoneType in type_args:
            type_args_list = [
                item for item in type_args if item is not NoneType]
            is_optional = True
        else:
            type_args_list = list(type_args)
            is_optional = False
        if len(type_args_list) == 1:
            return {**semi_json_schema_type(type_args_list[0]), 'optional': is_optional}
        else:
            return {'union': [semi_json_schema_type(item) for item in type_args_list], 'optional': is_optional}
    elif origin_type == Literal:
        return {'enum': list(type_args)}
    else:
        return {'type': tp}


class TypeCast:
    ORJSON_OPTION = 0

    @classmethod
    def init_orjson_option(self, option_text: str) -> None:
        if option_text:
            for option_word in option_text.split(','):
                assert hasattr(orjson, f'OPT_{option_word}')
                option_flag = getattr(orjson, f'OPT_{option_word}')
                self.ORJSON_OPTION |= option_flag

    @classmethod
    def dumps(self, data: Any) -> bytes:
        return orjson.dumps(
            data, option=self.ORJSON_OPTION, default=_pydantic_encoder)

    @classmethod
    def validate_json(self, data: Union[str, bytes], tp: Type[T]) -> T:
        """
        Validate data as json to type T.

        Supported type T:
            - list[pydantic.BaseModel]
            - pydantic.BaseModel

        The validation process is different according to the type of T:
            - If T is list[pydantic.BaseModel], the validation is done by validate the list items one by one.
            - If T is pydantic.BaseModel, the validation is done by pydantic's model_validate_json method.

        Raises:
            ValueError: if the data cannot be parsed to the given type (4xx Error for Frontend)
            TypeError: if the given type is not supported (5xx Error for Frontend)
        """
        if is_list_type(tp):
            try:
                items = orjson.loads(data)
            except Exception as e:
                raise ValueError(f'{data=} cannot parse to JSON {e}')
            if not isinstance(items, list):
                raise ValueError(f'{data=} cannot parse to list {tp=}')
            type_inspect_result = inspect_type(tp)
            tp_args = type_inspect_result[1] \
                if len(type_inspect_result) == 2 else None
            if not tp_args:
                return items  # type: ignore
            if not inspect.isclass(tp_args) or not issubclass(tp_args, pydantic.BaseModel):
                raise TypeError(f'list type {tp=} is not supported')
            result = []
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f'{data=} cannot parse to {tp=}')
                try:
                    result.append(tp_args.model_validate(item))
                except pydantic.ValidationError as e:
                    raise ValueError(
                        f'{item=} is not an list item of {tp_args=} {e}')
            return result  # type: ignore
        else:
            if not inspect.isclass(tp) or not issubclass(tp, pydantic.BaseModel):
                raise TypeError(f'type {tp=} is not supported')
            try:
                return tp.model_validate_json(data)  # type: ignore
            except pydantic.ValidationError as e:
                raise ValueError(f'{data=} cannot parsec to {tp=} {e}')

    @classmethod
    def validate_query(self, data: str, tp: Type[T]) -> T:
        """
        try to convert a query string to the given type.

        Args:
            data: a query string.
            tp: the type to convert to.

        Returns:
            the converted value.

        Raises:
            ValueError: if the data cannot be parsed to the given type (4xx Error for Frontend)
            TypeError: if the given type is not supported (5xx Error for Frontend)
        """
        type_inspect_result = inspect_type(tp)
        tp_origin = type_inspect_result[0]
        tp_args = type_inspect_result[1] if len(
            type_inspect_result) == 2 else None
        if is_list_type(tp):
            if not tp_args:
                raise TypeError(f'{tp=} missing type of item')
            try:
                data_items = parse_csv(data)
            except Exception:
                raise ValueError(f'{data=} is not a CSV format string {tp=}')
            return [  # type: ignore
                self.validate_query(item, tp_args)
                for item in data_items]
        elif tp_origin == Union:
            if not tp_args:
                raise TypeError(f'{tp=} is empty')  # 5xx Error in fact
            for each_args_type in tp_args:
                try:
                    return self.validate_query(data, each_args_type)
                except Exception:
                    continue
            raise ValueError(f'{data=} is not any member of {tp=}')
        elif tp_origin == Literal:
            if not tp_args:
                raise TypeError(f'{tp=} is empty')  # 5xx Error in fact
            for each_args_item in tp_args:
                if literal_to_str(each_args_item) == data:
                    return data  # type: ignore
            raise ValueError(f'{data=} is not member of {tp=}')
        elif tp_origin == NewType:
            if not tp_args:
                raise TypeError(f'{tp=} is empty')
            return self.validate_query(data, tp_args)

        if not inspect.isclass(tp):
            raise TypeError(f'{tp=} is not a class')

        if issubclass(tp, enum.Enum):
            try:
                return tp(data)  # type: ignore
            except Exception:
                raise ValueError(f'{data=} is not enum of {tp=}')
        elif tp is bool:
            if data.lower() == 'true' or data == '1' or data == '✔':
                return True  # type: ignore
            elif data.lower() == 'false' or data == '0' or data == '✖':
                return False  # type: ignore
            else:
                raise ValueError(f'{data=} is not boolean')
        elif issubclass(tp, (str, int, float)):
            try:
                return tp(data)  # type: ignore
            except Exception:
                raise ValueError(f'{data=} is not an instance of {tp=}')
        elif issubclass(tp, datetime.datetime):
            return datetime.datetime.fromisoformat(data)  # type: ignore
        elif issubclass(tp, datetime.date):
            return datetime.date.fromisoformat(data)  # type: ignore
        elif issubclass(tp, datetime.time):
            return datetime.time.fromisoformat(data)  # type: ignore
        elif issubclass(tp, pydantic.BaseModel):
            try:
                return tp.model_validate_json(data)  # type: ignore
            except pydantic.ValidationError as e:
                raise ValueError(f'{data=} is not an instance of {tp=} {e}')
        else:
            raise TypeError(f'type {tp=} is not supported')
