from inspect import Parameter
from typing import Annotated, Any

import pytest

from lessweb.annotation import Endpoint
from lessweb.ioc import (func_annotated_metas, func_arg_annotated_metas,
                         func_arg_spec, get_endpoint_metas)

# Test data
HTTP_METHOD_TYPE = str  # Assuming this is defined somewhere in your actual code


def test_endpoint_initialization():
    """Test basic Endpoint class initialization"""
    endpoint = Endpoint("GET", "/test")
    assert endpoint.method == "GET"
    assert endpoint.path == "/test"


def test_func_annotated_metas_with_no_annotation():
    """Test function with no Annotated return type"""
    def sample_func() -> bool:
        return True

    return_type, metadata = func_annotated_metas(sample_func)
    assert return_type == bool
    assert metadata == tuple()


def test_func_annotated_metas_with_annotation():
    """Test function with Annotated return type"""
    def sample_func() -> Annotated[bool, 'meta']:
        return True

    return_type, metadata = func_annotated_metas(sample_func)
    assert return_type == bool
    assert metadata == ('meta',)


def test_func_annotated_metas_with_multiple_metadata():
    """Test function with multiple metadata in Annotation"""
    def sample_func() -> Annotated[str, 'meta1', 'meta2']:
        return ''

    return_type, metadata = func_annotated_metas(sample_func)
    assert return_type == str
    assert metadata == ('meta1', 'meta2')


def test_get_endpoint_metas_with_no_endpoints():
    """Test function with no Endpoint metadata"""
    def sample_func() -> Annotated[bool, 'not_endpoint']:
        return True

    endpoints = get_endpoint_metas(sample_func)
    assert endpoints == []


def test_get_endpoint_metas_with_single_endpoint():
    """Test function with single Endpoint metadata"""
    endpoint = Endpoint("GET", "/test")

    def sample_func() -> Annotated[bool, endpoint]:
        return True

    endpoints = get_endpoint_metas(sample_func)
    assert len(endpoints) == 1
    assert endpoints[0].method == "GET"
    assert endpoints[0].path == "/test"


def test_get_endpoint_metas_with_multiple_endpoints():
    """Test function with multiple Endpoint metadata"""
    endpoint1 = Endpoint("GET", "/test1")
    endpoint2 = Endpoint("POST", "/test2")

    def sample_func() -> Annotated[bool, endpoint1, endpoint2, 'other_meta']:
        return True

    endpoints = get_endpoint_metas(sample_func)
    assert len(endpoints) == 2
    assert endpoints[0].method == "GET"
    assert endpoints[0].path == "/test1"
    assert endpoints[1].method == "POST"
    assert endpoints[1].path == "/test2"


def test_get_endpoint_metas_with_mixed_metadata():
    """Test function with mixed metadata types including Endpoints"""
    endpoint = Endpoint("GET", "/test")

    def sample_func() -> Annotated[bool, 'meta1', endpoint, 'meta2']:
        return False

    endpoints = get_endpoint_metas(sample_func)
    assert len(endpoints) == 1
    assert endpoints[0].method == "GET"
    assert endpoints[0].path == "/test"


def test_func_annotated_metas_with_no_return_type():
    """Test function with no return type annotation"""
    def sample_func():
        pass

    return_type, metadata = func_annotated_metas(sample_func)
    assert return_type == Any
    assert metadata == tuple()


def test_func_with_annotated_param():
    def foo(a: Annotated[int, 'meta'], b: str = ''):
        pass

    result = func_arg_annotated_metas(foo)
    assert result == {'a': ('meta',)}


def test_func_with_multiple_annotated_params():
    def bar(
        a: Annotated[int, 'meta1'],
        b: Annotated[str, 'meta2', 'meta3']
    ):
        pass

    result = func_arg_annotated_metas(bar)
    assert result == {
        'a': ('meta1',),
        'b': ('meta2', 'meta3')
    }


def test_func_with_no_annotated_params():
    def baz(a: int, b: str = ''):
        pass

    result = func_arg_annotated_metas(baz)
    assert result == {}


def test_func_with_mixed_params():
    def qux(
        a: Annotated[int, 'meta'],
        b: str,
        c: Annotated[float, 'meta2']
    ):
        pass

    result = func_arg_annotated_metas(qux)
    assert result == {
        'a': ('meta',),
        'c': ('meta2',)
    }


def test_func_with_return_annotation():
    def xyz(a: Annotated[int, 'meta']) -> str:
        return ''

    result = func_arg_annotated_metas(xyz)
    assert result == {'a': ('meta',)}


def test_empty_function():
    def empty():
        pass

    result = func_arg_annotated_metas(empty)
    assert result == {}


def test_lambda_function():
    # Lambda functions can't have annotations, so should return empty dict
    result = func_arg_annotated_metas(lambda x: x)
    assert result == {}


def test_function_with_annotated_return():
    def example_func(a: int) -> Annotated[bool, 'meta']:
        return False

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == bool
    assert result_meta == ('meta',)


def test_function_with_multiple_metadata():
    def example_func(a: int) -> Annotated[str, 'meta1', 'meta2', 'meta3']:
        return ''

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == str
    assert result_meta == ('meta1', 'meta2', 'meta3')


def test_function_without_annotation():
    def example_func(a: int) -> bool:
        return False

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == bool
    assert result_meta == tuple()


def test_function_without_return_type():
    def example_func(a: int):
        pass

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == Any
    assert result_meta == tuple()


def test_function_with_complex_type():
    def example_func(a: int) -> Annotated[list[str], 'metadata']:
        return ['']

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == list[str]
    assert result_meta == ('metadata',)


def test_empty_function2():
    def example_func():
        pass

    result_type, result_meta = func_annotated_metas(example_func)
    assert result_type == Any
    assert result_meta == tuple()


def test_func_arg_spec_basic():
    def foo(a, b: int, c: Annotated[float, 'CC'] = 2.1):
        pass

    spec = func_arg_spec(foo)
    assert len(spec) == 3
    assert 'a' in spec and 'b' in spec and 'c' in spec

    # Check types
    assert spec['a'][0] == Any  # no type
    assert spec['b'][0] == int
    assert spec['c'][0] == float

    # Check defaults
    assert spec['a'][1] == Parameter.empty  # no default
    assert spec['b'][1] == Parameter.empty  # no default
    assert spec['c'][1] == 2.1  # has default

    # Check kinds
    assert spec['a'][2] == Parameter.POSITIONAL_OR_KEYWORD
    assert spec['b'][2] == Parameter.POSITIONAL_OR_KEYWORD
    assert spec['c'][2] == Parameter.POSITIONAL_OR_KEYWORD


def test_func_arg_spec_complex():
    def foo(a, /, b, c=2, *d, e, f=3, **g):
        pass

    spec = func_arg_spec(foo)
    assert len(spec) == 7

    # Check kinds
    assert spec['a'][2] == Parameter.POSITIONAL_ONLY
    assert spec['b'][2] == Parameter.POSITIONAL_OR_KEYWORD
    assert spec['c'][2] == Parameter.POSITIONAL_OR_KEYWORD
    assert spec['d'][2] == Parameter.VAR_POSITIONAL
    assert spec['e'][2] == Parameter.KEYWORD_ONLY
    assert spec['f'][2] == Parameter.KEYWORD_ONLY
    assert spec['g'][2] == Parameter.VAR_KEYWORD

    # Check defaults
    assert spec['a'][1] == Parameter.empty
    assert spec['b'][1] == Parameter.empty
    assert spec['c'][1] == 2
    assert spec['d'][1] == Parameter.empty
    assert spec['e'][1] == Parameter.empty
    assert spec['f'][1] == 3
    assert spec['g'][1] == Parameter.empty


def test_func_arg_spec_not_function():
    class NotAFunction:
        pass

    with pytest.raises(AssertionError) as exc_info:
        func_arg_spec(NotAFunction())
    assert "is not a function" in str(exc_info.value)
