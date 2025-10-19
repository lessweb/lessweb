from datetime import datetime
from typing import Annotated, Optional

from commondao.annotation import TableId
from pydantic import BaseModel


# Entity for querying admins
class Admin(BaseModel):
    """
    管理员 - 用于查询（不包含密码）
    """
    id: Annotated[int, TableId('tbl_admin')]
    truename: Optional[str]
    username: str
    createTime: datetime
    updateTime: datetime


# Entity for password verification
class AdminForPassword(BaseModel):
    """
    管理员 - 用于密码验证
    """
    id: Annotated[int, TableId('tbl_admin')]
    username: str
    password: str


# Entity for inserting admins
class AdminInsert(BaseModel):
    """
    管理员 - 用于插入
    """
    id: Annotated[Optional[int], TableId('tbl_admin')] = None  # Auto-increment
    truename: Optional[str] = None
    username: str
    password: str


# Entity for updating admins
class AdminUpdate(BaseModel):
    """
    管理员 - 用于更新
    """
    id: Annotated[int, TableId('tbl_admin')]
    truename: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


# DTOs for admin operations
class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    admin: Admin
    token: str


class AdminChangePasswordRequest(BaseModel):
    """管理员修改密码请求"""
    oldPassword: str
    newPassword: str
