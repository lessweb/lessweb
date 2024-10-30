# 1. Python dotenv

## Installation

First, install the `python-dotenv` package using pip. Open your terminal and run:

```bash
pip install python-dotenv
```

If you are using Python 3, you might need to use `pip3` instead.

## Creating a `.env` File

Create a file named `.env` in the root directory of your project. This file will contain your environment variables in the format of key-value pairs. Here’s an example of what it might look like:

```
SECRET_KEY=mysecretkey
DATABASE_URL=postgres://user:password@localhost/db
DEBUG=True
```

You can also include multi-line values or reference other variables within the file:

```
ACCESS_TOKEN=ABC123
SECRET_TOKEN="SUPERSECRET123
CONTINUEDSECRET"
LOGS_PATH=${ROOT_PATH}/logs
```

## Loading Environment Variables

In your Python script, you can load the environment variables from the `.env` file using the `load_dotenv()` function from the `dotenv` module. Here’s a basic example:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Accessing the environment variables
secret_key = os.getenv('SECRET_KEY')
database_url = os.getenv('DATABASE_URL')
debug = os.getenv('DEBUG')

print(f"Secret Key: {secret_key}")
print(f"Database URL: {database_url}")
print(f"Debug Mode: {debug}")
```

### Example Output

If your `.env` file contains:

```
SECRET_KEY=mysecretkey
DATABASE_URL=postgres://user:password@localhost/db
DEBUG=True
```

The output will be:

```
Secret Key: mysecretkey
Database URL: postgres://user:password@localhost/db
Debug Mode: True
```

## Managing Different Environments

You can manage different configurations for various environments (development, testing, production) by creating multiple `.env` files, such as `.env.development` and `.env.production`. You can load the appropriate file based on an environment variable:

```python
import os
from dotenv import load_dotenv, find_dotenv

# Determine which .env file to load based on ENV variable
env_file = find_dotenv(f'.env.{os.getenv("ENV", "development")}')
load_dotenv(env_file)

# Accessing environment variables as before
secret_key = os.getenv('SECRET_KEY')
print(f"Secret Key: {secret_key}")
```

In this example, if you set `ENV=production`, it will load variables from `.env.production`.

# 2. lessweb配置方案

## 2.1 Module如何指定并加载自己的配置项类型与key

`Module.load_config()->Annotated(T, 'key')`

T必须是pydantic类，才能生成jsonschema

key的规则参考：https://docs.aiohttp.org/en/stable/web_advanced.html#naming-hint

### 加载的实现

依然是注入app，app在加载时即调用`_load_config_with_env`

调用load_config就像bean一样，只加载一次

## 2.2 cli生成总的jsonschema

生成的位置比如在./config-schema.json

### 如何校验？

1. VSCode可以装一个Even Better TOML插件，然后参考：https://taplo.tamasfe.dev/configuration/directives.html#the-schema-directive
2. cli工具可以使用：https://www.npmjs.com/package/pajv

## 2.3 如何与dotenv协作？

1. 如果设置了环境变量ENV，则调用`find_dotenv()`，否则忽略。
2. 调用`load_dotenv()` （如果设置了环境变量ENV但load_dotenv返回False则失败退出）
3. 像原来一样，app在加载时即调用`_load_config_with_env`

## 2.4 load_config是否与mypy校验冲突？

结论不冲突。例程如下：

```python
class Model:
    def load_config(self):
        pass

class A(Model):
    def load_config(self) -> Annotated[str, 'key']:
        return 'Loading config for A with'
```

mypy校验通过。如果改成`def load_config(self, n: str)`，则会报错：

```
main.py:5: error: Signature of "load_config" incompatible with supertype "Model"  [override]
main.py:5: note:      Superclass:
main.py:5: note:          def load_config(self) -> Any
main.py:5: note:      Subclass:
main.py:5: note:          def load_config(self, s: str) -> str
```