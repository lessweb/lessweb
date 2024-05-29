import sys
import unittest
from datetime import date, datetime, time
from enum import Enum
from typing import (Any, Dict, Generator, List, Literal, NewType, Optional,
                    TypedDict, Union)
from uuid import UUID

from lessweb.typecast import (TypeCastError, inspect_type,
                              semi_json_schema_type, typecast)

NoneType = type(None)


class SampleTypedDict(TypedDict):
    name: str
    age: int


class SampleElse:
    pass


UserId = NewType('UserId', int)


class TestInspectType(unittest.TestCase):
    def test_inspect_type(self):
        self.assertEqual(inspect_type(int), (int,))
        self.assertEqual(inspect_type(list), (list,))
        self.assertEqual(inspect_type(list[int]), (list, int))
        self.assertEqual(inspect_type(Optional[int]), (Union, (int, NoneType)))
        if sys.version_info[:2] >= (3, 11):
            self.assertEqual(inspect_type(int | None),
                             (Union, (int, NoneType)))
            self.assertEqual(inspect_type(int | str), (Union, (int, str)))
            self.assertEqual(inspect_type(int | str | None),
                             (Union, (int, str, NoneType)))
            self.assertEqual(inspect_type(None | str | int),
                             (Union, (NoneType, str, int)))
        self.assertEqual(inspect_type(
            Literal['a', 'b']), (Literal, ('a', 'b')))
        self.assertEqual(inspect_type(UserId), (NewType, int))
        self.assertEqual(inspect_type(dict), (dict,))
        self.assertRaises(NotImplementedError, inspect_type, dict[str, int])
        self.assertRaises(NotImplementedError, inspect_type,
                          Dict[str, Union[str, int]])
        self.assertEqual(inspect_type(SampleTypedDict),
                         (dict, {'age': int, 'name': str}))
        self.assertEqual(inspect_type(Any), (Any,))
        self.assertEqual(inspect_type(SampleElse), (SampleElse,))
        self.assertRaises(NotImplementedError, inspect_type, Generator)


class SampleEnum(Enum):
    VALUE1 = 'V1'
    VALUE2 = 'V2'


class TestTypecast(unittest.TestCase):
    def test_typecast_same_type(self):
        data = 10
        tp = int
        result = typecast(data, tp)
        self.assertEqual(result, data)

    def test_typecast_enum(self):
        data = "V1"
        tp = SampleEnum
        result = typecast(data, tp)
        self.assertEqual(result, SampleEnum.VALUE1)

    def test_typecast_datetime(self):
        data = "2022-01-01T12:00:00"
        tp = datetime
        result = typecast(data, tp)
        self.assertEqual(result, datetime.fromisoformat(data))

    def test_typecast_date(self):
        data = "2022-01-01"
        tp = date
        result = typecast(data, tp)
        self.assertEqual(result, date.fromisoformat(data))

    def test_typecast_time(self):
        data = "12:00:00"
        tp = time
        result = typecast(data, tp)
        self.assertEqual(result, time.fromisoformat(data))

    def test_typecast_uuid(self):
        data = 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6'
        tp = UUID
        result = typecast(data, tp)
        self.assertEqual(result.hex, 'f81d4fae7dec11d0a76500a0c91e6bf6')

    def test_typecast_str(self):
        data = "Hello"
        tp = str
        result = typecast(data, tp)
        self.assertEqual(result, data)

    def test_typecast_list(self):
        data = "1,2,3"
        tp = List[int]
        result = typecast(data, tp)
        self.assertEqual(result, [1, 2, 3])

    def test_typecast_dict_missing_required_keys(self):
        data = '{"age": 25}'
        tp = Dict[str, Union[str, int]]
        with self.assertRaises(NotImplementedError):
            typecast(data, tp)

    def test_typecast_unsupported_type(self):
        data = "data"
        tp = float
        with self.assertRaises(TypeCastError):
            typecast(data, tp)

    def test_typecast_literal(self):
        data = "b"
        tp = Literal['a', 'b']
        result = typecast(data, tp)
        self.assertEqual(result, data)
        data = "c"
        try:
            typecast(data, tp)
            self.fail('should raise TypeCastError')
        except TypeCastError as e:
            self.assertEqual(str(e), f'{data=} is not member of {tp=}')
        tp = Literal
        try:
            typecast(data, tp)
            self.fail('should raise TypeCastError')
        except TypeCastError as e:
            self.assertEqual(str(e), f'{tp=} is empty')

    def test_typecast_union(self):
        data = "10"
        tp = Union[int, list[int]]
        result = typecast(data, tp)
        self.assertEqual(result, 10)
        data = "11,12"
        result = typecast(data, tp)
        self.assertEqual(result, [11, 12])
        data = "12.3"
        with self.assertRaises(TypeCastError):
            typecast(data, tp)

    def test_typecast_newtype(self):
        data = "10"
        tp = UserId
        result = typecast(data, tp)
        self.assertEqual(result, UserId(10))
        data = "12.3"
        with self.assertRaises(TypeCastError):
            typecast(data, tp)


class TestSemiJsonSchemaType(unittest.TestCase):
    def test_list(self):
        result = semi_json_schema_type(list)
        self.assertEqual(result, {'type': 'array'})

        result = semi_json_schema_type(list[int])
        self.assertEqual(result, {'type': 'array', 'items': {'type': int}})

    def test_union(self):
        result = semi_json_schema_type(Union[int, str])
        self.assertEqual(
            result, {'union': [{'type': int}, {'type': str}], 'optional': False})

        result = semi_json_schema_type(Union[int, None])
        self.assertEqual(result, {'type': int, 'optional': True})

        result = semi_json_schema_type(Union[None, int, str])
        self.assertEqual(
            result, {'union': [{'type': int}, {'type': str}], 'optional': True})

    def test_literal(self):
        result = semi_json_schema_type(Literal['a', 'b'])
        self.assertEqual(result, {'enum': ['a', 'b']})

    def test_any(self):
        result = semi_json_schema_type(Any)
        self.assertEqual(result, {})

    def test_custom_class(self):
        result = semi_json_schema_type(SampleElse)
        self.assertEqual(result, {'type': SampleElse})


if __name__ == '__main__':
    unittest.main()
