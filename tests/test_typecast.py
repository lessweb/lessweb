import sys
import unittest
from datetime import date, datetime, time
from enum import Enum
from typing import (Dict, Generator, List, Literal, NewType, Optional,
                    TypedDict, Union)

from lessweb.typecast import TypeCastError, inspect_type, typecast

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
        self.assertEqual(inspect_type(
            Literal['a', 'b']), (Literal, ('a', 'b')))
        self.assertEqual(inspect_type(UserId), (NewType, int))
        self.assertEqual(inspect_type(dict), (dict,))
        self.assertRaises(NotImplementedError, inspect_type, dict[str, int])
        self.assertRaises(NotImplementedError, inspect_type,
                          Dict[str, Union[str, int]])
        self.assertEqual(inspect_type(SampleTypedDict),
                         (dict, {'age': int, 'name': str}))
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


if __name__ == '__main__':
    unittest.main()
