import hashlib
from typing import Annotated

from commondao import Commondao
from lessweb.annotation import Get, Post

from shared.auth_gateway.auth_gateway import AuthGateway
from src.entity.admin import (
    Admin,
    AdminChangePasswordRequest,
    AdminForPassword,
    AdminInsert,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUpdate,
)
from src.service.auth_service import AuthRole, CurrentAdmin


def _hash_password(password: str) -> str:
    """对密码进行SHA256哈希"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


async def login(login_data: AdminLoginRequest, /, auth_gateway: AuthGateway, dao: Commondao) -> Annotated[AdminLoginResponse, Post('/public/admin/login')]:
    """管理员登录"""
    hashed_password = _hash_password(login_data.password)

    # 查询管理员（使用AdminForPassword来验证密码）
    admin_with_password = await dao.get_by_key(AdminForPassword, key={'username': login_data.username, 'password': hashed_password})
    assert admin_with_password, "用户名或密码错误"

    # 返回不包含密码的管理员信息
    admin = await dao.get_by_id_or_fail(Admin, admin_with_password.id)

    # 生成JWT token
    token = auth_gateway.encrypt_jwt(str(admin.id), AuthRole.ADMIN)

    return AdminLoginResponse(admin=admin, token=token)


async def get_current_admin(current_admin: CurrentAdmin) -> Annotated[Admin, Get('/admin/me')]:
    """查询当前登录管理员信息"""
    admin = await current_admin.get()
    return admin


async def change_password(password_data: AdminChangePasswordRequest, /, current_admin: CurrentAdmin, dao: Commondao) -> Annotated[dict, Post('/admin/me/change-password')]:
    """修改当前管理员密码"""
    admin_id = current_admin.id  # 这会自动验证是否为 admin 角色

    # 验证旧密码
    old_hashed = _hash_password(password_data.oldPassword)
    admin = await dao.get_by_id_or_fail(AdminForPassword, admin_id)
    assert admin.password == old_hashed, "旧密码错误"

    # 更新密码
    new_hashed = _hash_password(password_data.newPassword)
    admin_update = AdminUpdate(id=admin_id, password=new_hashed)
    await dao.update_by_id(admin_update)

    return {'message': '密码修改成功'}


async def init_admin(dao: Commondao) -> Annotated[Admin, Get('/public/admin/init')]:
    """初始化管理员：创建一个密码为12345678的初始管理员"""
    existing_admins = await dao.select_all("SELECT * FROM tbl_admin LIMIT 1", Admin)
    assert not existing_admins, "系统中已存在管理员，无法初始化"

    # 创建初始管理员
    hashed_password = _hash_password("12345678")
    initial_admin = AdminInsert(username="admin", password=hashed_password)
    await dao.insert(initial_admin)
    admin_id = dao.lastrowid()
    admin = await dao.get_by_id_or_fail(Admin, admin_id)
    return admin
