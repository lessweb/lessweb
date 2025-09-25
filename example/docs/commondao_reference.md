# CommonDAO API Reference

This document provides comprehensive API reference for CommonDAO, a powerful async MySQL toolkit with Pydantic integration.

## Table of Contents

- [Connection Management](#connection-management)
- [Core CRUD Operations](#core-crud-operations)
- [Query Methods](#query-methods)
- [Raw SQL Execution](#raw-sql-execution)
- [Transaction Management](#transaction-management)
- [Type Safety Utilities](#type-safety-utilities)
- [Annotations](#annotations)
- [Error Classes](#error-classes)
- [Data Types](#data-types)

## Connection Management

### `connect(**config) -> AsyncContextManager[Commondao]`

Creates an async database connection context manager.

**Parameters:**
- `host` (str): Database host
- `port` (int): Database port (default: 3306)
- `user` (str): Database username
- `password` (str): Database password
- `db` (str): Database name
- `autocommit` (bool): Enable autocommit mode (default: True)
- Additional aiomysql connection parameters

**Returns:** AsyncContextManager yielding a Commondao instance

**Example:**
```python
async with connect(host='localhost', user='root', password='pwd', db='testdb') as db:
    # Database operations here
    pass
```

---

## Core CRUD Operations

### `insert(entity: BaseModel, *, ignore: bool = False, exclude_unset: bool = True, exclude_none: bool = False) -> int`

Insert a Pydantic model instance into the database.

**Parameters:**
- `entity` (BaseModel): Pydantic model instance to insert
- `ignore` (bool): Use INSERT IGNORE to skip duplicate key errors
- `exclude_unset` (bool): If True (default), excludes fields not explicitly set. Allows database defaults for unset fields
- `exclude_none` (bool): If False (default), includes None values. If True, excludes None values from INSERT

**Returns:** int - Number of affected rows (1 on success, 0 if ignored)

**Example:**
```python
user = UserInsert(name='John', email='john@example.com')
affected_rows = await db.insert(user)
```

### `update_by_id(entity: BaseModel, *, exclude_unset: bool = True, exclude_none: bool = False) -> int`

Update a record by its primary key using a Pydantic model.

**Parameters:**
- `entity` (BaseModel): Pydantic model with primary key value set
- `exclude_unset` (bool): If True (default), only updates explicitly set fields. Enables partial updates
- `exclude_none` (bool): If False (default), includes None values (sets to NULL). If True, excludes None values

**Returns:** int - Number of affected rows

**Raises:**
- `EmptyPrimaryKeyError`: If primary key is None or empty

**Example:**
```python
user = UserUpdate(id=1, name='John Updated', email='john.new@example.com')
affected_rows = await db.update_by_id(user)
```

### `update_by_key(entity: BaseModel, *, key: QueryDict, exclude_unset: bool = True, exclude_none: bool = False) -> int`

Update records matching the specified key conditions.

**Parameters:**
- `entity` (BaseModel): Pydantic model with update values
- `key` (QueryDict): Dictionary of key-value pairs for WHERE conditions
- `exclude_unset` (bool): If True (default), only updates explicitly set fields. Enables partial updates
- `exclude_none` (bool): If False (default), includes None values (sets to NULL). If True, excludes None values

**Returns:** int - Number of affected rows

**Example:**
```python
user_update = UserUpdate(name='Jane', email='jane@example.com')
affected_rows = await db.update_by_key(user_update, key={'id': 1})
```

### `delete_by_id(entity_class: Type[BaseModel], entity_id: Union[int, str]) -> int`

Delete a record by its primary key value.

**Parameters:**
- `entity_class` (Type[BaseModel]): Pydantic model class
- `entity_id` (Union[int, str]): The primary key value

**Returns:** int - Number of affected rows

**Raises:**
- `AssertionError`: If entity_id is None

**Example:**
```python
affected_rows = await db.delete_by_id(User, 1)
```
### `delete_by_key(entity_class: Type[BaseModel], *, key: QueryDict) -> int`

Delete records matching the specified key conditions.

**Parameters:**
- `entity_class` (Type[BaseModel]): Pydantic model class
- `key` (QueryDict): Dictionary of key-value pairs for WHERE conditions

**Returns:** int - Number of affected rows

**Example:**
```python
affected_rows = await db.delete_by_key(User, key={'id': 1})
```

---

## Query Methods

### `get_by_id(entity_class: Type[M], entity_id: Union[int, str]) -> Optional[M]`

Get a single record by its primary key value.

**Parameters:**
- `entity_class` (Type[M]): Pydantic model class
- `entity_id` (Union[int, str]): The primary key value

**Returns:** Optional[M] - Model instance or None if not found

**Raises:**
- `AssertionError`: If entity_id is None

**Example:**
```python
user = await db.get_by_id(User, 1)
if user:
    print(f"Found user: {user.name}")
```

### `get_by_id_or_fail(entity_class: Type[M], entity_id: Union[int, str]) -> M`

Get a single record by its primary key value or raise an error if not found.

**Parameters:**
- `entity_class` (Type[M]): Pydantic model class
- `entity_id` (Union[int, str]): The primary key value

**Returns:** M - Model instance

**Raises:**
- `NotFoundError`: If no record matches the primary key
- `AssertionError`: If entity_id is None

**Example:**
```python
try:
    user = await db.get_by_id_or_fail(User, 1)
    print(f"User: {user.name}")
except NotFoundError:
    print("User not found")
```

### `get_by_key(entity_class: Type[M], *, key: QueryDict) -> Optional[M]`

Get a single record matching the specified key conditions.

**Parameters:**
- `entity_class` (Type[M]): Pydantic model class
- `key` (QueryDict): Dictionary of key-value pairs for WHERE conditions

**Returns:** Optional[M] - Model instance or None if not found

**Example:**
```python
user = await db.get_by_key(User, key={'email': 'john@example.com'})
```

### `get_by_key_or_fail(entity_class: Type[M], *, key: QueryDict) -> M`

Get a single record matching the key conditions or raise an error if not found.

**Parameters:**
- `entity_class` (Type[M]): Pydantic model class
- `key` (QueryDict): Dictionary of key-value pairs for WHERE conditions

**Returns:** M - Model instance

**Raises:**
- `NotFoundError`: If no record matches the conditions

**Example:**
```python
user = await db.get_by_key_or_fail(User, key={'email': 'john@example.com'})
```

### `select_one(sql: str, select: Type[M], data: QueryDict = {}) -> Optional[M]`

Execute a SELECT query and return the first row as a validated model instance.

**Parameters:**
- `sql` (str): SQL query starting with 'select * from'
- `select` (Type[M]): Pydantic model class for result validation
- `data` (QueryDict): Parameters for the query

**Returns:** Optional[M] - Model instance or None if no results

**Example:**
```python
user = await db.select_one(
    "select * from users where age > :min_age",
    User,
    {"min_age": 18}
)
```

### `select_one_or_fail(sql: str, select: Type[M], data: QueryDict = {}) -> M`

Execute a SELECT query and return the first row or raise an error if not found.

**Parameters:**
- `sql` (str): SQL query starting with 'select * from'
- `select` (Type[M]): Pydantic model class for result validation
- `data` (QueryDict): Parameters for the query

**Returns:** M - Model instance

**Raises:**
- `NotFoundError`: If no results found

**Example:**
```python
user = await db.select_one_or_fail(
    "select * from users where email = :email",
    User,
    {"email": "john@example.com"}
)
```

### `select_all(sql: str, select: Type[M], data: QueryDict = {}) -> list[M]`

Execute a SELECT query and return all matching rows as validated model instances.

**Parameters:**
- `sql` (str): SQL query starting with 'select * from'
- `select` (Type[M]): Pydantic model class for result validation
- `data` (QueryDict): Parameters for the query

**Returns:** list[M] - List of model instances

**Example:**
```python
active_users = await db.select_all(
    "select * from users where status = :status",
    User,
    {"status": "active"}
)
```

### `select_paged(sql: str, select: Type[M], data: QueryDict = {}, *, size: int, offset: int = 0) -> Paged[M]`

Execute a paginated SELECT query with total count.

**Parameters:**
- `sql` (str): SQL query starting with 'select * from'
- `select` (Type[M]): Pydantic model class for result validation
- `data` (QueryDict): Parameters for the query
- `size` (int): Number of items per page
- `offset` (int): Number of items to skip

**Returns:** Paged[M] - Paginated result with items and total count

**Example:**
```python
result = await db.select_paged(
    "select * from users where status = :status",
    User,
    {"status": "active"},
    size=10,
    offset=20
)
print(f"Total: {result.total}, Page items: {len(result.items)}")
```

---

## Raw SQL Execution

### `execute_query(sql: str, data: Mapping[str, Any] = {}) -> list`

Execute a parameterized SQL query and return all results.

**Parameters:**
- `sql` (str): SQL query with named parameter placeholders (:param_name)
- `data` (Mapping[str, Any]): Dictionary mapping parameter names to values

**Returns:** list - List of result rows (dictionaries)

**Supported Parameter Types:**
- str, int, float, bytes, datetime, date, time, timedelta, Decimal
- Lists/tuples (for IN clauses)
- None (converted to SQL NULL)

**Examples:**
```python
# Simple query
rows = await db.execute_query("SELECT * FROM users")

# Parameterized query
rows = await db.execute_query(
    "SELECT * FROM users WHERE age > :min_age AND status = :status",
    {"min_age": 18, "status": "active"}
)

# IN clause with list
rows = await db.execute_query(
    "SELECT * FROM users WHERE id IN :user_ids",
    {"user_ids": [1, 2, 3, 4]}
)
```

### `execute_mutation(sql: str, data: Mapping[str, Any] = {}) -> int`

Execute a parameterized SQL mutation (INSERT, UPDATE, DELETE) and return affected row count.

**Parameters:**
- `sql` (str): SQL mutation statement with named parameter placeholders (:param_name)
- `data` (Mapping[str, Any]): Dictionary mapping parameter names to values

**Returns:** int - Number of affected rows

**Examples:**
```python
# INSERT
affected = await db.execute_mutation(
    "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
    {"name": "John", "email": "john@example.com", "age": 25}
)

# UPDATE
affected = await db.execute_mutation(
    "UPDATE users SET email = :email WHERE id = :id",
    {"email": "newemail@example.com", "id": 123}
)

# DELETE
affected = await db.execute_mutation(
    "DELETE FROM users WHERE age < :min_age",
    {"min_age": 18}
)
```

---

## Transaction Management

### `commit() -> None`

Commit the current transaction.

**Example:**
```python
async with connect(host='localhost', autocommit=False) as db:
    await db.insert(user)
    await db.commit()  # Explicitly commit
```

### `rollback() -> None`

Rollback the current transaction.

**Example:**
```python
try:
    await db.insert(user)
    await db.insert(order)
    await db.commit()
except Exception:
    await db.rollback()
```

### `lastrowid() -> int`

Get the auto-generated ID of the last inserted row.

**Returns:** int - The last inserted row ID

**Example:**
```python
await db.insert(user)
user_id = db.lastrowid()
print(f"New user ID: {user_id}")
```

---

## Type Safety Utilities

### `is_row_dict(data: Mapping) -> TypeGuard[RowDict]`

Check if a mapping is valid for database row operations (INSERT/UPDATE).

**Parameters:**
- `data` (Mapping): The mapping to check

**Returns:** bool - True if valid for row operations

**Valid Types:** str, int, float, bytes, datetime, date, time, timedelta, Decimal, None

**Example:**
```python
from commondao import is_row_dict

data = {"id": 1, "name": "John", "age": 25}
assert is_row_dict(data)
# Now TypeScript knows data is a valid RowDict
```

### `is_query_dict(data: Mapping) -> TypeGuard[QueryDict]`

Check if a mapping is valid for query operations (WHERE clauses).

**Parameters:**
- `data` (Mapping): The mapping to check

**Returns:** bool - True if valid for query operations

**Valid Types:** All RowDict types plus lists and tuples (for IN clauses)

**Example:**
```python
from commondao import is_query_dict

query_data = {"id": 1, "status": "active", "tags": ["admin", "user"]}
assert is_query_dict(query_data)
# Now TypeScript knows query_data is a valid QueryDict
```

---

## Annotations

### `TableId(table_name: str)`

Annotation to mark a field as the primary key and specify the table name.

**Parameters:**
- `table_name` (str): Name of the database table

**Usage:**
```python
from commondao.annotation import TableId
from typing import Annotated, Optional
from pydantic import BaseModel

class User(BaseModel):
    id: Annotated[Optional[int], TableId('users')] = None
    name: str
    email: str
```

### `RawSql(expression: str)`

Annotation to include raw SQL expressions in SELECT queries.

**Parameters:**
- `expression` (str): SQL expression to include

**Usage:**
```python
from commondao.annotation import RawSql
from typing import Annotated

class UserWithFullName(BaseModel):
    id: int
    first_name: str
    last_name: str
    full_name: Annotated[str, RawSql("CONCAT(first_name, ' ', last_name)")]
```

---

## Error Classes

### `NotFoundError(ValueError)`

Raised when a record is not found in operations that expect a result.

**Example:**
```python
try:
    user = await db.get_by_id_or_fail(User, 999)
except NotFoundError as e:
    print(f"User not found: {e}")
```

### `EmptyPrimaryKeyError(ValueError)`

Raised when attempting operations with empty or None primary key values.

**Example:**
```python
try:
    user = UserUpdate(id=None, name="John")
    await db.update_by_id(user)
except EmptyPrimaryKeyError as e:
    print(f"Primary key error: {e}")
```

### `NotTableError(ValueError)`

Raised when a Pydantic model doesn't have proper table annotation.

### `MissingParamError(ValueError)`

Raised when required parameters are missing from SQL queries.

### `TooManyResultError(ValueError)`

Raised when operations expecting single results return multiple rows.

---

## Data Types

### `RowDict`

Type alias for mappings valid in database row operations.

```python
RowDict = Mapping[str, Union[str, int, float, bytes, datetime, date, time, timedelta, Decimal, None]]
```

### `QueryDict`

Type alias for mappings valid in query operations (extends RowDict with list/tuple support).

```python
QueryDict = Mapping[str, Union[RowValueType, list, tuple]]
```

### `Paged[T]`

Generic container for paginated query results.

**Attributes:**
- `items` (list[T]): List of result items
- `total` (int): Total count of all matching records

**Example:**
```python
result: Paged[User] = await db.select_paged(
    "select * from users",
    User,
    size=10
)
print(f"Page has {len(result.items)} items out of {result.total} total")
```

---

## Type Safety with TypeGuard

CommonDAO provides TypeGuard functions `is_row_dict()` and `is_query_dict()` for runtime type checking. **Important**: These functions should only be used with `assert` statements for proper type narrowing.

### Correct Usage Pattern

```python
from commondao import is_row_dict, is_query_dict

# ✅ Correct: Use with assert
def process_database_row(data: dict):
    assert is_row_dict(data)
    # Type checker now knows data is RowDict
    # Safe to use for database operations
    user = UserInsert(**data)
    await db.insert(user)

def process_query_parameters(params: dict):
    assert is_query_dict(params)
    # Type checker now knows params is QueryDict
    # Safe to use in queries
    result = await db.execute_query(
        "SELECT * FROM users WHERE status = :status",
        params
    )

# ✅ Correct: In test validation
async def test_query_result():
    rows = await db.execute_query("SELECT * FROM users")
    assert len(rows) > 0
    row = rows[0]
    assert is_row_dict(row)  # Validates row format
    # Now safely access row data
    user_id = row['id']
```

### What NOT to do

```python
# ❌ Wrong: Don't use in if statements
if is_row_dict(data):
    # Type narrowing won't work properly
    pass

# ❌ Wrong: Don't use in boolean expressions
valid = is_row_dict(data) and data['id'] > 0

# ❌ Wrong: Don't use with or/and logic
assert is_row_dict(data) or True  # Defeats the purpose
```

### Why Use Assert

TypeGuard functions with `assert` provide both runtime validation and compile-time type narrowing:

```python
def example_function(unknown_data: dict):
    # Before assert: unknown_data is just dict
    assert is_row_dict(unknown_data)
    # After assert: type checker knows unknown_data is RowDict

    # This will have proper type hints and validation
    await db.execute_mutation(
        "INSERT INTO users (name, email) VALUES (:name, :email)",
        unknown_data  # Type checker knows this is safe
    )
```

## Best Practices

### Entity Class Naming Conventions

When designing Pydantic models for database operations, follow these naming conventions to improve code clarity and maintainability:

- **Naming Convention**: Name entity classes used for `dao.insert()` with an `Insert` suffix; name entity classes used for `dao.update()` with an `Update` suffix; keep query entity class names unchanged.

- **Field Optionality Rules**:
  - For query entity classes: If a field's DDL is `NOT NULL`, the field should not be optional
  - For insert entity classes: If a field's DDL is `nullable` or has a default value, the field can be optional
  - For update entity classes: All fields should be optional

- **Field Inclusion**:
  - Insert entity classes should only include fields that may need to be inserted
  - Update entity classes should only include fields that may need to be modified

- **TableId Annotation**: Entity classes used for insert/update operations must always include the `TableId` annotation, even if the primary key field is optional