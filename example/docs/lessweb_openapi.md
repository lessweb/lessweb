# Lessweb OpenAPI Integration

## Overview

Lessweb provides built-in support for generating OpenAPI 3.0.3 specifications from endpoint handler functions. The framework automatically extracts API metadata from handler docstrings written in YAML format and generates comprehensive OpenAPI documentation.

## Features

- Automatic path and operation discovery from endpoint handlers
- YAML-based docstring parsing for OpenAPI metadata
- Integration with Pydantic models for schema generation
- Automatic filtering of non-RESTful endpoints (HTML, PlainText responses)
- Support for parameters, request bodies, and response definitions

## Endpoint Docstring Format

Handler functions should use YAML-formatted docstrings to define OpenAPI metadata. The framework uses `textwrap.dedent` to normalize indentation, allowing natural Python docstring formatting.

### Basic Structure

```python
async def get_example(dao: Commondao, *, query_param: str) -> Annotated[ExampleModel, Get('/example')]:
    """
    summary: Brief endpoint description
    description: Detailed explanation of what this endpoint does
    tags:
      - Category Name
    parameters:
      - name: query_param
        in: query
        required: true
        description: Parameter description
        schema:
          type: string
    responses:
      200:
        description: Success response description
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ExampleModel'
      404:
        description: Not found error description
    """
    # Implementation
```

### Supported OpenAPI Fields

The following fields from handler docstrings are automatically included in the OpenAPI specification:

- `summary`: Brief operation description
- `description`: Detailed operation explanation
- `tags`: List of tags for grouping operations
- `parameters`: Query, path, header, or cookie parameters
- `requestBody`: Request body specification
- `responses`: Response definitions by status code

### Operation ID Generation

Each operation is automatically assigned an `operationId` based on the handler function name. The framework extracts the function name from the handler's fully qualified reference path (e.g., `src.endpoint.task.get_home` becomes `get_home`). This ensures clean, semantic operation IDs that are compatible with OpenAPI code generation tools.

## Examples

### GET Endpoint with Query Parameters

```python
async def query_task(dao: Commondao, *, assignee: str, task_status: int) -> Annotated[Task, Get('/task')]:
    """
    summary: Query assignable task
    description: Find a task with specified status assignable to the given handler
    tags:
      - Task Management
    parameters:
      - name: assignee
        in: query
        required: true
        description: Handler identifier
        schema:
          type: string
      - name: task_status
        in: query
        required: true
        description: Task status (0=pending, 1=OCR complete, 2=translation complete)
        schema:
          type: integer
    responses:
      200:
        description: Successfully retrieved matching task
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Task'
      404:
        description: No assignable task found
    """
    # Implementation
```

### POST Endpoint with Request Body

```python
async def create_item(item_data: CreateItemDto, /, dao: Commondao) -> Annotated[Item, Post('/items')]:
    """
    summary: Create new item
    description: Create a new item with the provided data
    tags:
      - Item Management
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/CreateItemDto'
    responses:
      200:
        description: Item created successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'
      400:
        description: Invalid input data
    """
    # Implementation
```

### PUT Endpoint with Path Parameters

```python
async def update_task(
    put_input: PutTaskInput,
    /,
    dao: Commondao,
    *,
    task_id: int
) -> Annotated[TaskIdDto, Put('/task/{task_id}')]:
    """
    summary: Update task progress
    description: Update task status and related data based on processing stage
    tags:
      - Task Management
    parameters:
      - name: task_id
        in: path
        required: true
        description: ID of the task to update
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/PutTaskInput'
    responses:
      200:
        description: Task updated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskIdDto'
      400:
        description: Missing required fields or invalid task ID
    """
    # Implementation
```

### Multipart File Upload

```python
async def upload_file(request: Request, storage: StorageService) -> Annotated[UploadDto, Post('/upload')]:
    """
    summary: Upload file
    description: Accept multipart file upload and return storage URL
    tags:
      - File Management
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              file:
                type: string
                format: binary
    responses:
      200:
        description: File uploaded successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UploadDto'
      400:
        description: Missing file field or invalid filename
    """
    # Implementation
```

## Endpoint Filtering

The following types of endpoints are automatically excluded from OpenAPI documentation:

### Non-RESTful Endpoints

Endpoints that return non-JSON responses:

- `Html`: Returns HTML content
- `PlainText`: Returns plain text content
- `Xml`: Returns XML content
- `TextResponse`: Base class for text responses

Example:

```python
async def get_home_page(j2env: J2Env) -> Annotated[str, Get('/home'), Html]:
    """HTML page endpoint - will not appear in OpenAPI spec"""
    return j2env.get_template('home.html').render()
```

### Wildcard Method Endpoints

Endpoints using the wildcard method `'*'` (matching all HTTP methods) are not compatible with OpenAPI specification and will be excluded:

```python
# This endpoint will be excluded from OpenAPI spec
async def catch_all_handler() -> Annotated[dict, Endpoint('*', '/api/catch-all')]:
    """Wildcard method endpoint - will not appear in OpenAPI spec"""
    return {'message': 'Handles all HTTP methods'}
```

## Generating OpenAPI Specification

### Using the Bridge Class

```python
from lessweb import Bridge

bridge = Bridge('config')
bridge.beans(commondao_bean, redis_bean)
bridge.middlewares(MysqlConn)
bridge.scan('src')

components = bridge.dump_openapi_components()
# Returns: { "paths": {...}, "components": { "schemas": {...} } }
```

## Integration with Pydantic Models

The framework automatically generates JSON schemas for Pydantic models used in endpoint signatures. Models are referenced using `$ref` notation in the OpenAPI specification.

Example model reference:

```yaml
responses:
  200:
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/Task'
```

The corresponding schema definition is automatically generated in `components.schemas` from the Pydantic model definition.

## Best Practices

### Documentation Guidelines

1. **Be concise**: Write clear, brief summaries (one sentence)
2. **Be specific**: Provide detailed descriptions of behavior
3. **Document errors**: Include common error responses (400, 404, etc.)
4. **Use tags**: Group related operations with consistent tag names
5. **Describe parameters**: Include descriptions and constraints for all parameters

### YAML Formatting

1. Use consistent indentation (2 spaces recommended)
2. Include required fields: `summary`, `description`, `responses`
3. Document all parameters in the `parameters` section
4. Match parameter names with function keyword-only arguments
5. Match path parameter names with path template variables

### Schema References

1. Use `$ref` for Pydantic models instead of inline schemas
2. Reference models consistently: `#/components/schemas/ModelName`
3. Let the framework generate schemas automatically from models
4. Define inline schemas only for simple or one-off structures

## Error Handling

The YAML parser gracefully handles malformed docstrings:

- If YAML parsing fails, the endpoint is still registered but without OpenAPI metadata
- Only the `operationId` field is included for endpoints with invalid docstrings
- Check application logs for YAML parsing errors during development

## Limitations

1. YAML docstrings are required for OpenAPI metadata
2. Non-YAML docstrings are ignored (no metadata extracted)
3. Only RESTful JSON endpoints are included in the specification
4. Custom response types require manual documentation in YAML

## Complete Example

```python
from typing import Annotated
from commondao import Commondao
from lessweb.annotation import Get, Post, Put
from src.entity import Task
from src.types import CreateTaskDto, UpdateTaskDto

async def list_tasks(
    dao: Commondao,
    *,
    status: int | None = None,
    limit: int = 100
) -> Annotated[list[Task], Get('/tasks')]:
    """
    summary: List tasks
    description: Retrieve a paginated list of tasks with optional status filtering
    tags:
      - Task Management
    parameters:
      - name: status
        in: query
        required: false
        description: Filter by task status
        schema:
          type: integer
      - name: limit
        in: query
        required: false
        description: Maximum number of results
        schema:
          type: integer
          default: 100
    responses:
      200:
        description: Successfully retrieved task list
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/Task'
    """
    query = "SELECT * FROM tasks WHERE 1=1"
    params = {}

    if status is not None:
        query += " AND status = :status"
        params['status'] = status

    query += " LIMIT :limit"
    params['limit'] = limit

    return await dao.select_all(query, Task, params)
```

## See Also

- [Lessweb Quick Start](lessweb_quickstart.md)
- [Lessweb Reference](lessweb_reference.md)
- [OpenAPI 3.0.3 Specification](https://spec.openapis.org/oas/v3.0.3)
