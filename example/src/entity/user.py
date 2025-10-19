from datetime import datetime
from typing import Annotated, Optional

from commondao.annotation import TableId
from pydantic import BaseModel


# Entity for querying users
class User(BaseModel):
    """
    用户 - 用于查询
    """
    id: Annotated[int, TableId('tbl_user')]
    nickname: Optional[str]
    openid: str
    totalCount: int
    usedCount: int
    createTime: datetime
    updateTime: datetime


# Entity for inserting users
class UserInsert(BaseModel):
    """
    用户 - 用于插入
    """
    id: Annotated[Optional[int], TableId('tbl_user')] = None  # Auto-increment
    nickname: Optional[str] = None
    openid: str
    totalCount: Optional[int] = 0
    usedCount: Optional[int] = 0


# Entity for updating users
class UserUpdate(BaseModel):
    """
    用户 - 用于更新
    """
    id: Annotated[int, TableId('tbl_user')]
    nickname: Optional[str] = None
    openid: Optional[str] = None
    totalCount: Optional[int] = None
    usedCount: Optional[int] = None
