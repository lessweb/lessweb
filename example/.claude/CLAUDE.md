



### Environment Files
- `.env.production` - Production environment variables

## Key Dependencies

### External Services
- **commondao**: Custom ORM library (https://github.com/lessweb/commondao)
- **pyway**: Database migration tool
- **Redis**: Task queue backend for BullMQ

### Python Libraries
- `aiohttp`: Async HTTP server and client
- `pydantic`: Data validation and serialization
- `aiomysql`: Async MySQL connector
- `bullmq`: Task queue library (https://pypi.org/project/bullmq)
- `commondao`: Custom ORM library (docs/commondao_readme.md, docs/commondao_reference.md)
- `lessweb`: Custom web framework
- `pyway`: Database migration tool (https://pypi.org/project/pyway/)

## Database

### ORM Layer - Commondao
Commondao is a lightweight async MySQL toolkit for Python that provides:
- **Async Operations**: Built on aiomysql for non-blocking database operations
- **Pydantic Integration**: Models inherit from `pydantic.BaseModel` with seamless validation
- **Repository Pattern**: Pass Pydantic models to database methods for CRUD operations
- **Type Safety**: Strong typing with Python's type hints and runtime type checking
- **Parameterized Queries**: SQL injection protection with named parameters (`:param_name`)
- **Connection Management**: Request-scoped connections with automatic cleanup
- **Documentation**:
  - User guide: `docs/commondao_readme.md`
  - API reference: `docs/commondao_reference.md`

### Data Storage
- **MySQL**: Primary data storage with commondao ORM
- **Redis**: Task queue storage and caching

## Entity Design Pattern

The project follows a three-model pattern for database entities:

### Entity Types
- **Query Entity**: Full model with all fields (e.g., `Task`)
- **Insert Entity**: Model for inserts with optional ID (e.g., `TaskInsert`)
- **Update Entity**: Model for updates with all optional fields except ID (e.g., `TaskUpdate`)

### Example Pattern
```python
# Full entity for queries
class Task(BaseModel):
    id: Annotated[int, TableId('task')]
    taskName: str
    assignee: str
    # ... all fields

# Insert entity with optional ID
class TaskInsert(BaseModel):
    id: Annotated[Optional[int], TableId('task')] = None
    taskName: str
    assignee: str
    # ... fields with defaults

# Update entity with optional fields
class TaskUpdate(BaseModel):
    id: Annotated[int, TableId('task')]
    taskName: Optional[str] = None
    assignee: Optional[str] = None
    # ... all fields optional except ID
```

## Endpoint/Event Handler Parameter Injection

lessweb框架实现了基于参数类型的自动依赖注入系统，通过分析endpoint函数的参数签名，自动为不同类型的参数注入相应的值。

### 核心实现机制

lessweb会装饰每个endpoint函数/event handler，并根据参数类型进行不同的处理：

#### 1. 参数分类处理

根据Python函数参数的种类(kind)，lessweb将参数分为三类：

- **positional-only参数** (`kind == POSITIONAL_ONLY`): 从请求体(request body)中注入数据
- **keyword-only参数** (`kind == KEYWORD_ONLY`): 从路径参数或查询参数中注入数据
- **普通参数** (其他类型): 通过依赖注入容器注入服务实例

#### 2. positional-only参数注入

```python
# 示例：从请求体注入数据
async def create_task(task_data: CreateTaskDto, /) -> Annotated[dict, Post('/task')]:
    return {'task_id': task_data.task_id}

# 示例：直接注入原始bytes数据
async def upload_file(raw_data: bytes, /) -> Annotated[dict, Post('/upload')]:
    return {'size': len(raw_data)}
```

- 框架会调用`await request.read()`读取请求体
- 对于`bytes`类型：直接将请求体数据作为相应类型注入，无需JSON解析
- 对于其他类型：使用`TypeCast.validate_json()`将JSON数据反序列化为指定的Pydantic模型
- 支持`bytes`、`pydantic.BaseModel`和`list[pydantic.BaseModel]`类型

#### 3. keyword-only参数注入

```python
# 示例：从查询参数注入数据
async def query_task(*, assignee: str, task_status: int) -> Annotated[Task, Get('/task')]:
    # assignee和task_status会从URL查询参数中自动注入
```

- 优先从路径参数(`request.match_info`)中获取值
- 如果路径参数不存在，则从查询参数(`request.query`)中获取
- 使用`TypeCast.validate_query()`进行类型转换
- 支持基础类型、枚举、Pydantic模型等多种类型

#### 4. 依赖注入容器

```python
# 示例：注入服务实例
async def upload_file(request: Request, aws_api: AwsApi) -> Annotated[dict, Post('/upload')]:
    # aws_api会通过依赖注入容器自动注入
```

对于普通参数，框架会根据参数类型进行不同处理：

- **Module类型**: 调用`autowire_module()`进行进程级单例注入
- **Service/Middleware类型**: 调用`autowire()`进行请求级注入
- **Request类型**: 直接传入当前请求对象

### 依赖注入容器的实现

#### 进程级单例 (Module)

`autowire_module`函数实现进程级单例模式：

- 实例存储在Application对象中，整个应用生命周期内唯一
- 支持构造函数依赖注入，递归解析依赖关系
- 自动注册生命周期钩子（on_startup, on_cleanup, on_shutdown）

#### 请求级单例 (Service/Middleware)

`autowire`函数实现请求级单例模式：

- 实例存储在Request对象中，单次请求内唯一
- 支持构造函数依赖注入和循环依赖检测
- 可以注入Bean函数的返回值

#### Bean函数注入机制

`bridge.beans()`是lessweb框架提供的Bean工厂函数注册机制，用于创建和管理复杂的依赖对象。

##### Bean函数的工作原理

1. **注册阶段**：`bridge.beans()`会分析每个Bean函数的类型注解
```python
# main.py中的注册
bridge.beans(commondao_bean, redis_bean)
```

2. **函数签名分析**：框架会解析Bean函数的返回类型注解
```python
def commondao_bean(mysqlConn: MysqlConn) -> Commondao:
    return Commondao(mysqlConn.conn, mysqlConn.cur)

def redis_bean(redis_module: RedisModule) -> redis.Redis:
    return redis_module.redis_client
```

##### 实际应用示例

```python
# shared/lessweb_commondao/lessweb_commondao.py
def commondao_bean(mysqlConn: MysqlConn) -> Commondao:
    """Bean函数：创建Commondao实例
    - 参数mysqlConn会被自动注入（MysqlConn是Middleware类型）
    - 返回Commondao对象供endpoint使用
    - Commondao提供ORM功能，管理entity类的数据库操作
    - 每个请求会获得独立的Commondao实例（请求级单例）
    """
    return Commondao(mysqlConn.conn, mysqlConn.cur)

# shared/redis/redis_plugin.py
def redis_bean(redis_module: RedisModule) -> redis.Redis:
    """Bean函数：创建Redis客户端实例
    - 参数redis_module会被自动注入（RedisModule是Module类型）
    - 返回Redis客户端对象供endpoint使用
    """
    return redis_module.redis_client
```

当endpoint声明需要`Commondao`或`redis.Redis`类型的参数时：

```python
async def query_task(dao: Commondao, redis: redis.Redis, *, assignee: str) -> Annotated[Task, Get('/task')]:
    # dao: 通过commondao_bean函数创建
    # redis: 通过redis_bean函数创建
    # assignee: 从查询参数注入
```

### 类型转换和验证

框架使用`TypeCast`类进行数据类型转换：

- `validate_json()`: 处理JSON数据反序列化
- `validate_query()`: 处理查询参数类型转换
- 支持基础类型、Pydantic模型、枚举、日期时间等多种类型

### 示例应用

项目中的实际应用示例：

```python
# src/endpoint/task.py
async def query_task(dao: Commondao, *, assignee: str, task_status: int) -> Annotated[Task, Get('/task')]:
    # dao: 通过依赖注入获得数据访问对象
    # assignee, task_status: 从查询参数自动注入并类型转换

async def fetch_task(fetch_task_input: FetchTaskInput, /, request: Request, dao: Commondao) -> Annotated[Task, Post('/fetch_task')]:
    # fetch_task_input: 从请求体JSON反序列化注入
    # request: 直接注入请求对象
    # dao: 通过依赖注入获得数据访问对象
```

这种设计使得endpoint函数非常简洁，无需手动解析请求参数或管理依赖关系，框架会根据参数声明自动完成所有注入工作。

## lessweb的Module/Middleware/Service/bean构造参数的依赖注入用法

lessweb框架提供了类似Spring Boot的依赖注入机制，开发者只需在构造函数中声明需要的依赖类型，框架会自动注入相应的实例。

### 基本用法原则

#### 1. 组件类型和生命周期

- **Module**: 进程级单例，整个应用生命周期内唯一，用于数据库连接池、配置管理等
- **Middleware**: aiohttp中间件包装器，每次请求时创建实例，用于请求预处理和后处理
- **Service**: 请求级单例，单次请求内唯一，用于业务逻辑服务
- **Bean函数返回值**: 请求级单例，通过工厂函数创建复杂对象

#### 2. 依赖注入规则

- Module只能依赖其他Module
- Middleware/Service可以依赖Module、其他Middleware/Service、bean函数返回值
- Bean函数可以依赖Module、Middleware/Service、其他bean函数返回值

### 实际开发示例

#### 1. 开发Module组件（类似Spring的@Component + @Scope("singleton")）

```python
# 数据库连接池模块
class Mysql(Module):
    """进程级单例 - 数据库连接池"""
    pool: Pool

    # 无依赖的Module - 构造函数不需要参数
    async def on_startup(self, app: Application):
        config = self.load_config(app)
        self.pool = await aiomysql.create_pool(**config.model_dump())

# Redis模块
class RedisModule(Module):
    """进程级单例 - Redis客户端"""
    redis_client: redis.Redis

    # 无依赖的Module - 构造函数不需要参数
    async def on_startup(self, app: Application):
        config = self.load_config(app)
        self.redis_client = redis.Redis(**config.model_dump())

# 假设有Module间依赖的情况
class ComplexModule(Module):
    """依赖其他Module的示例"""

    def __init__(self, mysql: Mysql, redis_module: RedisModule):
        """构造函数依赖注入：
        - mysql: 自动注入Mysql模块实例
        - redis_module: 自动注入RedisModule模块实例
        """
        self.mysql = mysql
        self.redis_module = redis_module
```

#### 2. 开发Middleware组件（aiohttp中间件包装器）

**重要**: Middleware是请求级单例，并且是aiohttp middleware的封装。每次请求时lessweb会创建Middleware实例来处理请求。

```python
# 数据库连接中间件
class MysqlConn(Middleware):
    """为每个请求提供数据库连接的中间件"""

    def __init__(self, mysql: Mysql):
        """构造函数依赖注入：
        - mysql: 自动注入Mysql模块实例（进程级）
        """
        self.mysql = mysql

    async def on_request(self, request: Request, handler: Callable):
        """处理请求的核心逻辑"""
        async with self.mysql.pool.acquire() as conn:
            self.conn = conn
            async with conn.cursor(DictCursor) as cur:
                self.cur = cur
                return await handler(request)

# 在main.py中注册middleware
bridge.middlewares(MysqlConn)  # 这会调用make_middleware(MysqlConn)
```

**Middleware的工作原理**:
1. `bridge.middlewares(MysqlConn)` 注册Middleware类
2. lessweb框架构造函数依赖注入后会创建Middleware实例的请求级单例
3. 每次请求时lessweb会调用Middleware实例的`on_request`方法

```python
# 复杂中间件示例 - 依赖多个组件
class AuthMiddleware(Middleware):
    """认证中间件"""

    def __init__(self, redis_client: redis.Redis, config_service: ConfigService):
        """构造函数依赖注入：
        - redis_client: 自动注入Redis客户端（通过redis_bean创建）
        - config_service: 自动注入ConfigService实例
        """
        self.redis_client = redis_client
        self.config_service = config_service

    async def on_request(self, request: Request, handler: Callable):
        # 认证逻辑
        token = request.headers.get('Authorization')
        if token:
            user_data = await self.redis_client.get(f"token:{token}")
            if user_data:
                request['user'] = json.loads(user_data)
        return await handler(request)
```

#### 3. 开发Service组件（类似Spring的@Service）

```python
# 业务服务
class TaskService(Service):
    """任务处理服务 - 请求级单例"""

    def __init__(self, dao: Commondao, redis_client: redis.Redis):
        """构造函数依赖注入：
        - dao: 自动注入Commondao实例（通过commondao_bean创建）
        - redis_client: 自动注入Redis客户端（通过redis_bean创建）
        """
        self.dao = dao
        self.redis_client = redis_client

    async def process_task(self, task_id: int):
        # 使用注入的依赖进行业务处理
        task = await self.dao.get_by_id(Task, task_id)
        await self.redis_client.set(f"task:{task_id}", "processing")
        return task

# 多层依赖服务
class NotificationService(Service):
    """通知服务 - 依赖其他服务"""

    def __init__(self, task_service: TaskService, aws_api: AwsApi):
        """构造函数依赖注入：
        - task_service: 自动注入TaskService实例（请求级）
        - aws_api: 自动注入AwsApi模块实例（进程级）
        """
        self.task_service = task_service
        self.aws_api = aws_api
```

#### 4. 开发Bean工厂函数（类似Spring的@Bean）

```python
# 在main.py中注册bean函数
bridge.beans(commondao_bean, redis_bean)

# 简单bean函数
def commondao_bean(mysqlConn: MysqlConn) -> Commondao:
    """工厂函数创建Commondao实例
    - mysqlConn: 自动注入MysqlConn中间件实例
    注意：这里MysqlConn不是作为middleware使用，而是作为依赖注入的组件
    """
    return Commondao(mysqlConn.conn, mysqlConn.cur)

def redis_bean(redis_module: RedisModule) -> redis.Redis:
    """工厂函数创建Redis客户端
    - redis_module: 自动注入RedisModule模块实例
    """
    return redis_module.redis_client
```

### 注册和配置

```python
# main.py
def main():
    bridge = Bridge('config')

    # 注册bean工厂函数
    bridge.beans(commondao_bean, redis_bean)

    # 注册middleware（按顺序执行）
    bridge.middlewares(MysqlConn)  # 数据库连接中间件

    # 扫描endpoints、modules、services
    bridge.scan('src')

    bridge.run_app()
```

### 在endpoint中使用依赖注入

```python
# src/endpoint/task.py
async def query_task(dao: Commondao, task_service: TaskService, *, assignee: str) -> Annotated[Task, Get('/task')]:
    """endpoint函数依赖注入：
    - dao: 自动注入Commondao实例（通过commondao_bean创建）
    - task_service: 自动注入TaskService实例
    - assignee: 从查询参数注入
    """
    return await task_service.get_task_by_assignee(assignee)
```

### 开发最佳实践

#### 1. Middleware vs Service的选择
```python
# ✅ 使用Middleware：需要在请求处理前后执行逻辑
class LoggingMiddleware(Middleware):
    async def on_request(self, request: Request, handler: Callable):
        start_time = time.time()
        response = await handler(request)
        duration = time.time() - start_time
        logging.info(f"Request {request.path} took {duration}s")
        return response

# ✅ 使用Service：纯业务逻辑处理
class UserService(Service):
    def __init__(self, dao: Commondao):
        self.dao = dao

    async def get_user(self, user_id: int):
        return await self.dao.get_by_id(User, user_id)
```

#### 2. 依赖层次
```python
# ✅ 好的实践：Module只依赖Module
class DatabaseModule(Module):
    def __init__(self, config_module: ConfigModule):
        self.config_module = config_module

# ✅ 好的实践：Middleware可以依赖Module、Service、bean
class RequestMiddleware(Middleware):
    def __init__(self, cache_service: CacheService, redis_client: redis.Redis):
        self.cache_service = cache_service
        self.redis_client = redis_client

# ❌ 避免：Module依赖Service（违反层次结构）
class BadModule(Module):
    def __init__(self, user_service: UserService):  # 错误！
        self.user_service = user_service
```

## 最佳实践

* 如果任务跟数据库相关，你必须先阅读`docs/commondao_readme.md`和`docs/commondao_reference.md`文档。
* 如果任务跟web框架相关，必须新增/修改endpoint, event handler, module, middleware, bean, service等，你必须先阅读`docs/lessweb_quickstart.md`和`docs/lessweb_reference.md`文档。
* 文件命名规范：`src/controller`目录的文件后缀名为`_controller.py`，例如`task_controller.py`；`src/entity`目录文件没有特殊后缀名，例如`task.py`就包含`Task`, `TaskInsert`, `TaskUpdate`等实体类的实现。
* 字段命名规范：数据库表名为蛇形风格；数据库表的字段为驼峰风格；跟前端交互的请求和返回字段为驼峰风格；其他普通字段为蛇形风格。