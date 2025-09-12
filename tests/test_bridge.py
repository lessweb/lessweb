from typing import Annotated
from unittest.mock import patch

import pytest
from aiohttp import web
from pydantic import BaseModel

from lessweb.annotation import Endpoint
from lessweb.bridge import Bridge


class SampleModel1(BaseModel):
    field1: str
    field2: int


class SampleModel2(BaseModel):
    name: str
    value: float


class TestDumpOpenAPIComponents:
    """Test cases for Bridge#dump_openapi_components method"""

    def test_dump_openapi_components_empty_models(self):
        """Test dump_openapi_components with no endpoint models"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = []
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is None

    def test_dump_openapi_components_single_model(self):
        """Test dump_openapi_components with single endpoint model"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [SampleModel1]
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is not None
        assert "SampleModel1" in result["components"]["schemas"]
        
        schema = result["components"]["schemas"]["SampleModel1"]
        assert "properties" in schema
        assert "field1" in schema["properties"]
        assert "field2" in schema["properties"]
        assert schema["properties"]["field1"]["type"] == "string"
        assert schema["properties"]["field2"]["type"] == "integer"

    def test_dump_openapi_components_multiple_models(self):
        """Test dump_openapi_components with multiple endpoint models"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [SampleModel1, SampleModel2]
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is not None
        assert "SampleModel1" in result["components"]["schemas"]
        assert "SampleModel2" in result["components"]["schemas"]
        
        # Check SampleModel1 schema
        schema1 = result["components"]["schemas"]["SampleModel1"]
        assert "properties" in schema1
        assert "field1" in schema1["properties"]
        assert "field2" in schema1["properties"]
        
        # Check SampleModel2 schema
        schema2 = result["components"]["schemas"]["SampleModel2"]
        assert "properties" in schema2
        assert "name" in schema2["properties"]
        assert "value" in schema2["properties"]
        assert schema2["properties"]["name"]["type"] == "string"
        assert schema2["properties"]["value"]["type"] == "number"

    def test_dump_openapi_components_duplicate_models(self):
        """Test dump_openapi_components with duplicate models"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [SampleModel1, SampleModel1, SampleModel2]
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is not None
        # Should handle duplicates correctly
        assert "SampleModel1" in result["components"]["schemas"]
        assert "SampleModel2" in result["components"]["schemas"]

    def test_dump_openapi_components_ref_template(self):
        """Test that ref_template is correctly set"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [SampleModel1]
        
        with patch('lessweb.bridge.models_json_schema') as mock_models_json_schema:
            mock_models_json_schema.return_value = ({}, {'$defs': {}})
            
            bridge.dump_openapi_components()
            
            # Verify models_json_schema was called with correct parameters
            mock_models_json_schema.assert_called_once_with(
                [(SampleModel1, "validation")],
                ref_template="#/components/schemas/{model}"
            )

    def test_dump_openapi_components_nested_model(self):
        """Test dump_openapi_components with nested Pydantic models"""
        class NestedModel(BaseModel):
            inner: SampleModel1
            count: int
        
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [NestedModel]
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is not None
        assert "NestedModel" in result["components"]["schemas"]
        # Nested model should also be included
        assert "SampleModel1" in result["components"]["schemas"]

    def test_dump_openapi_components_complex_types(self):
        """Test dump_openapi_components with complex field types"""
        class ComplexModel(BaseModel):
            items: list[str]
            mapping: dict[str, int]
            optional_field: str | None = None
        
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [ComplexModel]
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        assert result["components"]["schemas"] is not None
        assert "ComplexModel" in result["components"]["schemas"]
        
        schema = result["components"]["schemas"]["ComplexModel"]
        assert "properties" in schema
        assert "items" in schema["properties"]
        assert "mapping" in schema["properties"]
        assert "optional_field" in schema["properties"]

    @patch('lessweb.bridge.models_json_schema')
    def test_dump_openapi_components_models_json_schema_error(self, mock_models_json_schema):
        """Test dump_openapi_components when models_json_schema raises an error"""
        bridge = Bridge(app=web.Application())
        bridge.endpoint_models = [SampleModel1]
        
        mock_models_json_schema.side_effect = ValueError("Schema generation error")
        
        with pytest.raises(ValueError, match="Schema generation error"):
            bridge.dump_openapi_components()

    def test_dump_openapi_components_integration(self):
        """Integration test with actual Bridge scan_interface behavior"""
        bridge = Bridge(app=web.Application())
        
        # Simulate endpoint with Pydantic model in positional-only parameter
        def endpoint(request: SampleModel1, /) -> Annotated[SampleModel2, Endpoint('POST', '/test')]:
            return SampleModel2(name="test", value=1.0)
        
        # Manually add models as scan_interface would
        from lessweb.ioc import get_pydantic_models_from_endpoint
        
        models = get_pydantic_models_from_endpoint(endpoint)
        bridge.endpoint_models.extend(models)
        
        result = bridge.dump_openapi_components()
        
        assert "components" in result
        assert "schemas" in result["components"]
        # Should include models from function parameters and return type
        assert "SampleModel1" in result["components"]["schemas"]
        assert "SampleModel2" in result["components"]["schemas"]


if __name__ == '__main__':
    pytest.main([__file__])
