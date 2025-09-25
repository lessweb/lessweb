# CommonDAO

A powerful, type-safe, and Pydantic-integrated async MySQL toolkit for Python.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Async](https://img.shields.io/badge/Async-FF5A00?style=for-the-badge&logo=python&logoColor=white)
![Type Safe](https://img.shields.io/badge/Type_Safe-3178C6?style=for-the-badge&logoColor=white)

CommonDAO is a lightweight, type-safe async MySQL toolkit designed to simplify database operations with a clean, intuitive API. It integrates seamlessly with Pydantic for robust data validation while providing a comprehensive set of tools for common database tasks.

## ✨ Features

- **Async/Await Support**: Built on aiomysql for non-blocking database operations
- **Type Safety**: Strong typing with Python's type hints and runtime type checking
- **Pydantic Integration**: Seamless validation and transformation of database records to Pydantic models
- **SQL Injection Protection**: Parameterized queries for secure database access
- **Comprehensive CRUD Operations**: Simple methods for common database tasks
- **Raw SQL Support**: Full control when you need it with parameterized raw SQL
- **Connection Pooling**: Efficient database connection management
- **Minimal Boilerplate**: Write less code while maintaining readability and control

## 🚀 Installation

```bash
pip install commondao
```

## 🔍 Quick Start

```python
import asyncio
from commondao import connect
from commondao.annotation import TableId
from pydantic import BaseModel
from typing import Annotated

# Define your Pydantic models with TableId annotation
class User(BaseModel):
    id: Annotated[int, TableId('users')]  # First field with TableId is the primary key
    name: str
    email: str

class UserInsert(BaseModel):
    id: Annotated[Optional[int], TableId('users')] = None  # Optional for auto-increment
    name: str
    email: str

async def main():
    # Connect to database
    config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'db': 'testdb',
        'autocommit': True,
    }

    async with connect(**config) as db:
        # Insert a new user using Pydantic model
        user = UserInsert(name='John Doe', email='john@example.com')
        await db.insert(user)

        # Query the user by key with Pydantic model validation
        result = await db.get_by_key(User, key={'email': 'john@example.com'})
        if result:
            print(f"User: {result.name} ({result.email})")  # Output => User: John Doe (john@example.com)

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Core Operations

### Connection

```python
from commondao import connect

async with connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='password', 
    db='testdb'
) as db:
    # Your database operations here
    pass
```

### Insert Data (with Pydantic Models)

```python
from pydantic import BaseModel
from commondao.annotation import TableId
from typing import Annotated, Optional

class UserInsert(BaseModel):
    id: Annotated[Optional[int], TableId('users')] = None  # Auto-increment primary key
    name: str
    email: str

# Insert using Pydantic model (id will be auto-generated)
user = UserInsert(name='John', email='john@example.com')
await db.insert(user)
print(f"New user id: {db.lastrowid()}")  # Get the auto-generated id

# Insert with ignore option (skips duplicate key errors)
user2 = UserInsert(name='Jane', email='jane@example.com')
await db.insert(user2, ignore=True)

# Insert with custom field handling
# exclude_unset=False: includes all fields, even those not explicitly set
# exclude_none=True: excludes fields with None values
user3 = UserInsert(name='Bob', email='bob@example.com')
await db.insert(user3, exclude_unset=False, exclude_none=True)
```

### Update Data (with Pydantic Models)

```python
class UserUpdate(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None

# Update by primary key (id must be provided)
user = UserUpdate(id=1, name='John Smith', email='john.smith@example.com')
await db.update_by_id(user)

# Update by custom key (partial update - only specified fields)
user_update = UserUpdate(name='Jane Doe', email='jane.doe@example.com')
await db.update_by_key(user_update, key={'email': 'john.smith@example.com'})

# Update with field handling options
# exclude_unset=True (default): only update explicitly set fields
# exclude_none=False (default): include None values (set column to NULL)
user = UserUpdate(id=2, name='Alice', email=None)
await db.update_by_id(user, exclude_unset=True, exclude_none=False)  # Sets email to NULL

# Update excluding None values
user = UserUpdate(id=3, name='Bob', email=None)
await db.update_by_id(user, exclude_unset=True, exclude_none=True)  # Won't update email column
```

### Delete Data

```python
# Delete by primary key
await db.delete_by_id(User, 1)

# Delete by custom key
await db.delete_by_key(User, key={'email': 'john@example.com'})
```

### Query Data

```python
# Get a single row by primary key
user = await db.get_by_id(User, 1)

# Get a row by primary key or raise NotFoundError if not found
user = await db.get_by_id_or_fail(User, 1)

# Get by custom key
user = await db.get_by_key(User, key={'email': 'john@example.com'})

# Get by key or raise NotFoundError if not found
user = await db.get_by_key_or_fail(User, key={'email': 'john@example.com'})

# Use with Pydantic models
from pydantic import BaseModel
from commondao.annotation import RawSql
from typing import Annotated

class UserModel(BaseModel):
    id: int
    name: str
    email: str
    full_name: Annotated[str, RawSql("CONCAT(first_name, ' ', last_name)")]

# Query with model validation
user = await db.select_one(
    "select * from users where id = :id",
    UserModel,
    {"id": 1}
)

# Query multiple rows
users = await db.select_all(
    "select * from users where status = :status",
    UserModel,
    {"status": "active"}
)

# Paginated queries
from commondao import Paged

result: Paged[UserModel] = await db.select_paged(
    "select * from users where status = :status",
    UserModel,
    {"status": "active"},
    size=10,
    offset=0
)

print(f"Total users: {result.total}")
print(f"Current page: {len(result.items)} users")
```

### Raw SQL Execution

CommonDAO supports parameterized SQL queries using named parameters with the `:parameter_name` format for secure and readable queries.

#### execute_query - For SELECT operations

```python
# Simple query without parameters
rows = await db.execute_query("SELECT * FROM users")

# Query with single parameter
user_rows = await db.execute_query(
    "SELECT * FROM users WHERE id = :user_id",
    {"user_id": 123}
)

# Query with multiple parameters
filtered_rows = await db.execute_query(
    "SELECT * FROM users WHERE name = :name AND age > :min_age",
    {"name": "John", "min_age": 18}
)

# Query with IN clause (using list parameter)
users_in_group = await db.execute_query(
    "SELECT * FROM users WHERE id IN :user_ids",
    {"user_ids": [1, 2, 3, 4]}
)

# Complex query with date filtering
recent_users = await db.execute_query(
    "SELECT * FROM users WHERE created_at > :date AND status = :status",
    {"date": "2023-01-01", "status": "active"}
)
```

#### execute_mutation - For INSERT, UPDATE, DELETE operations

```python
# INSERT statement
affected = await db.execute_mutation(
    "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
    {"name": "John", "email": "john@example.com", "age": 25}
)
print(f"Inserted {affected} rows")

# UPDATE statement
affected = await db.execute_mutation(
    "UPDATE users SET email = :new_email WHERE id = :user_id",
    {"new_email": "newemail@example.com", "user_id": 123}
)
print(f"Updated {affected} rows")

# DELETE statement
affected = await db.execute_mutation(
    "DELETE FROM users WHERE age < :min_age",
    {"min_age": 18}
)
print(f"Deleted {affected} rows")

# Multiple parameter UPDATE
affected = await db.execute_mutation(
    "UPDATE users SET name = :name, age = :age WHERE id = :id",
    {"name": "Jane", "age": 30, "id": 456}
)

# Bulk operations with loop
user_list = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
]

for user_data in user_list:
    affected = await db.execute_mutation(
        "INSERT INTO users (name, email) VALUES (:name, :email)",
        user_data
    )
```

#### Parameter Format Rules

- **Named Parameters**: Use `:parameter_name` format in SQL
- **Dictionary Keys**: Match parameter names without the colon prefix
- **Supported Types**: str, int, float, bytes, datetime, date, time, timedelta, Decimal
- **Lists/Tuples**: Supported for IN clauses in queries
- **None Values**: Properly handled as SQL NULL

```python
# Example with various data types
from datetime import datetime, date
from decimal import Decimal

result = await db.execute_query(
    """
    SELECT * FROM orders
    WHERE customer_id = :customer_id
    AND total >= :min_total
    AND created_date = :order_date
    AND status IN :valid_statuses
    """,
    {
        "customer_id": 123,
        "min_total": Decimal("99.99"),
        "order_date": date(2023, 12, 25),
        "valid_statuses": ["pending", "confirmed", "shipped"]
    }
)
```

### Transactions

```python
from commondao.annotation import TableId
from typing import Annotated, Optional

class OrderInsert(BaseModel):
    id: Annotated[Optional[int], TableId('orders')] = None
    customer_id: int
    total: float

class OrderItemInsert(BaseModel):
    id: Annotated[Optional[int], TableId('order_items')] = None
    order_id: int
    product_id: int

async with connect(host='localhost', user='root', db='testdb') as db:
    # Start transaction (autocommit=False by default)
    order = OrderInsert(customer_id=1, total=99.99)
    await db.insert(order)
    order_id = db.lastrowid()  # Get the auto-generated order id

    item = OrderItemInsert(order_id=order_id, product_id=42)
    await db.insert(item)

    # Commit the transaction
    await db.commit()
```

## 🔐 Type Safety

CommonDAO provides robust type checking to help prevent errors:

```python
from commondao import is_row_dict, is_query_dict
from typing import Dict, Any
from datetime import datetime

# Valid row dict (for updates/inserts)
valid_data: Dict[str, Any] = {
    "id": 1,
    "name": "John",
    "created_at": datetime.now(),
}

# Check type safety
assert is_row_dict(valid_data)  # Type check passes

# Valid query dict (can contain lists/tuples for IN clauses)
valid_query: Dict[str, Any] = {
    "id": 1,
    "status": "active",
    "tags": ["admin", "user"],  # Lists are valid for query dicts
    "codes": (200, 201)  # Tuples are also valid
}

assert is_query_dict(valid_query)  # Type check passes

# Invalid row dict (contains a list)
invalid_data: Dict[str, Any] = {
    "id": 1,
    "tags": ["admin", "user"]  # Lists are not valid row values
}

assert not is_row_dict(invalid_data)  # Type check fails
```

## 📖 API Documentation

For complete API documentation, please see the docstrings in the code or visit our documentation website.

## 🧪 Testing

CommonDAO comes with comprehensive tests to ensure reliability:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest tests
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the Apache License 2.0.
