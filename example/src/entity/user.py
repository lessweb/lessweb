from datetime import datetime
from typing import Annotated, Optional

from commondao.annotation import TableId
from pydantic import BaseModel


class User(BaseModel):
    """用户查询实体"""
    id: Annotated[int, TableId('user')]
    createdAt: datetime
    updatedAt: datetime
    userName: str


class UserForPassword(BaseModel):
    """用户密码验证实体"""
    id: Annotated[int, TableId('user')]
    userName: str
    userPassword: str


class UserInsert(BaseModel):
    """用户插入实体"""
    id: Annotated[Optional[int], TableId('user')] = None
    userName: str
    userPassword: str


class UserUpdate(BaseModel):
    """用户更新实体"""
    id: Annotated[int, TableId('user')]
    userName: Optional[str] = None
    userPassword: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    userName: str
    password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    oldPassword: str
    newPassword: str
