# 1. pydantic如何反序列化/反序列化/校验？

```python
from pydantic import BaseModel, Field


class Dog(BaseModel):
    breed: str
    friends: list
    birthday: datetime = Field(default_factory=datetime.now)


partial_dog_json = {"breed": "lab", "friends": [
    "buddy", "spot", "rufus"], "age": 5}
dog = Dog.model_validate(partial_dog_json)
print(repr(dog))
print(dog.model_dump_json())
# > Dog(breed='lab', friends=['buddy', 'spot', 'rufus'], birthday=datetime.datetime(2024, 10, 29, 13, 29, 47, 419940))
# > {"breed":"lab","friends":["buddy","spot","rufus"],"birthday":"2024-10-29T13:29:47.419940"}
```

注意：
- Model的每个字段必须要有默认值。
- pydantic的序列化已通过rust重写，性能很好。
- 对于lessweb来说，pydantic自带序列化/反序列化和orjson是二选一的。

# 3. pydantic如何生成jsonschema?

参考：https://docs.pydantic.dev/latest/concepts/json_schema/

# 4. pydantic如何与sqlalchemy协作？

版本答案是[SQLModel](https://sqlmodel.tiangolo.com/tutorial/)

## 4.1 如何基于sqlalchemy生成sql但不运行？

参考：
- https://kimi.moonshot.cn/share/csg9diha584a0p4q624g
- https://stackoverflow.com/questions/4617291/how-do-i-get-a-raw-compiled-sql-query-from-a-sqlalchemy-expression

## 4.2 CRUD版本答案
1. 基于SQLModel+commondao+alembic
2. 提供一个Paged父类，采用子类的方式进行validate和生成jsonschema，无法使用泛型。

### todo
- [ ] 新的`commondao::paginate(query, limit, offset)->Paged`函数，基于sqlalchemy生成sql但不运行。
- [ ] 对于endpoint的返回值是BaseModel的情况，如果返回值的类型和声明类型不一致，则需要手动验证。