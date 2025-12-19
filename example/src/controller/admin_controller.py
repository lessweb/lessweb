from typing import Annotated

import bcrypt
from commondao import Commondao

from lessweb.annotation import Get, Post
from shared.jwt_gateway import JwtGateway
from src.entity.admin import Admin, AdminInfoOutput, AdminLoginInput, AdminLoginOutput
from src.service.auth_service import AuthRole, CurrentAdmin


async def login_admin(
        login_input: AdminLoginInput,
        /,
        dao: Commondao,
        jwt_gateway: JwtGateway) -> Annotated[AdminLoginOutput, Post('/login/admin')]:
    """
    summary: 管理员登录
    description: 管理员使用用户名和密码登录，验证成功后返回JWT token
    tags:
      - 认证管理
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/AdminLoginInput'
    responses:
      200:
        description: 登录成功，返回JWT token
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AdminLoginOutput'
      400:
        description: 用户名或密码错误，或账号未激活
    """
    # 查询管理员账号
    admin = await dao.select_one(
        'from tbl_admin where username = :username limit 1',
        Admin,
        {'username': login_input.username}
    )

    # 验证账号是否存在
    assert admin, 'Invalid username or password'

    # 验证账号是否激活
    assert admin.is_active, 'Account is not active'

    # 验证密码
    assert bcrypt.checkpw(
        login_input.password.encode('utf-8'),
        admin.password_hash.encode('utf-8')
    ), 'Invalid username or password'

    # 生成JWT token
    token = jwt_gateway.encrypt_jwt(
        user_id=str(admin.id),
        subject=AuthRole.ADMIN
    )

    # 在Redis中设置登录状态
    await jwt_gateway.login(
        user_id=str(admin.id),
        user_role=AuthRole.ADMIN
    )

    # 返回登录结果
    return AdminLoginOutput(
        token=token,
        admin_id=admin.id,
        username=admin.username
    )


async def get_admin_me(current_admin: CurrentAdmin) -> Annotated[AdminInfoOutput, Get('/admin/me')]:
    """
    summary: 获取当前登录管理员信息
    description: 获取当前已登录的管理员的详细信息（不包含密码等敏感信息）
    tags:
      - 管理员管理
    security:
      - bearerAuth: []
    responses:
      200:
        description: 成功返回管理员信息
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AdminInfoOutput'
      401:
        description: 未登录或token无效
      403:
        description: 无权限访问（非管理员角色）
    """
    # 通过 CurrentAdmin service 获取当前登录的管理员
    admin = await current_admin.get()

    # 返回管理员信息（不包含 password_hash）
    return AdminInfoOutput(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        is_active=admin.is_active,
        create_time=admin.create_time,
        update_time=admin.update_time
    )
