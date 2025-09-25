import hashlib
from typing import Annotated

from commondao import Commondao
from lessweb.annotation import Get, Post
from pydantic import BaseModel

from shared.auth_gateway.auth_gateway import AuthGateway, AuthUser
from src.entity.user import (
    ChangePasswordRequest,
    LoginRequest,
    User,
    UserForPassword,
    UserInsert,
    UserUpdate,
)


class LoginResponse(BaseModel):
    """登录响应"""
    user: User
    token: str


def _hash_password(password: str) -> str:
    """对密码进行SHA256哈希"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


async def login(login_data: LoginRequest, /, auth_gateway: AuthGateway, dao: Commondao) -> Annotated[LoginResponse, Post('/public/login')]:
    """用户登录"""
    hashed_password = _hash_password(login_data.password)

    # 查询用户（使用UserForPassword来验证密码）
    user_with_password = await dao.get_by_key(UserForPassword, key={'userName': login_data.userName, 'userPassword': hashed_password})
    assert user_with_password, "用户名或密码错误"

    # 返回不包含密码的用户信息
    user = await dao.get_by_id_or_fail(User, user_with_password.id)

    # 生成JWT token
    token = auth_gateway.encrypt_jwt(str(user.id), "user")

    return LoginResponse(user=user, token=token)


async def get_current_user(auth_user: AuthUser, dao: Commondao) -> Annotated[User, Get('/me')]:
    """查询当前登录用户信息"""
    user = await dao.get_by_id_or_fail(User, auth_user.id)
    return user


async def change_password(password_data: ChangePasswordRequest, /, auth_user: AuthUser, dao: Commondao) -> Annotated[dict, Post('/me/change-password')]:
    """修改当前用户密码"""
    # 验证旧密码
    old_hashed = _hash_password(password_data.oldPassword)
    user = await dao.get_by_id_or_fail(UserForPassword, auth_user.id)
    assert user.userPassword == old_hashed, "旧密码错误"

    # 更新密码
    new_hashed = _hash_password(password_data.newPassword)
    user_update = UserUpdate(id=auth_user.id, userPassword=new_hashed)
    await dao.update_by_id(user_update)

    return {'message': '密码修改成功'}


async def init_user(dao: Commondao) -> Annotated[User, Get('/public/init-user')]:
    """初始化用户：创建一个密码为12345678的初始用户"""
    # 检查是否已存在用户
    existing_users = await dao.select_all("SELECT * FROM user LIMIT 1", User)
    assert not existing_users, "系统中已存在用户，无法初始化"

    # 创建初始用户
    hashed_password = _hash_password("12345678")
    initial_user = UserInsert(userName="admin", userPassword=hashed_password)
    await dao.insert(initial_user)
    user_id = dao.lastrowid()
    user = await dao.get_by_id_or_fail(User, user_id)
    return user
