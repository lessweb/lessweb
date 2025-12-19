from datetime import datetime
from typing import Annotated, Optional

from commondao.annotation import TableId
from pydantic import BaseModel


class Admin(BaseModel):
    """
    管理员实体 - 用于查询
    """
    id: Annotated[int, TableId('tbl_admin')]
    username: str
    password_hash: str
    email: Optional[str]
    is_active: bool
    create_time: datetime
    update_time: datetime


class AdminInsert(BaseModel):
    """
    管理员实体 - 用于插入
    """
    id: Annotated[Optional[int], TableId('tbl_admin')] = None  # Auto-increment
    username: str
    password_hash: str
    email: Optional[str] = None
    is_active: bool = True


class AdminUpdate(BaseModel):
    """
    管理员实体 - 用于更新
    """
    id: Annotated[Optional[int], TableId('tbl_admin')] = None
    username: Optional[str] = None
    password_hash: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


# DTO Models

class AdminLoginInput(BaseModel):
    """管理员登录请求DTO"""
    username: str
    password: str


class AdminLoginOutput(BaseModel):
    """管理员登录响应DTO"""
    token: str
    admin_id: int
    username: str


class AdminInfoOutput(BaseModel):
    """管理员信息输出DTO（不包含敏感信息）"""
    id: int
    username: str
    email: Optional[str]
    is_active: bool
    create_time: datetime
    update_time: datetime
