"""
用户相关接口
提供用户登录、用户信息查询等功能
"""

from typing import Annotated

from aiohttp.web import HTTPNotFound
from commondao import Commondao
from src.entity.user import User
from src.service.auth_service import CurrentAdmin, CurrentUser

from lessweb.annotation import Get


async def get_current_user(current_user: CurrentUser) -> Annotated[User, Get('/user/me')]:
    """查询当前登录用户信息"""
    user = await current_user.get()
    return user


async def get_user_by_admin(
    dao: Commondao,
    current_admin: CurrentAdmin,
    *,
    user_id: int
) -> Annotated[User, Get('/admin/user/{user_id}')]:
    """管理员查询用户详情

    GET /admin/user/{user_id}

    管理员查询指定用户的完整详情信息。

    Path Parameters:
        user_id: 要查询的用户ID

    Returns:
        User: 用户完整信息

    Raises:
        403: 管理员未登录或token无效
        404: 用户不存在
    """
    # 验证管理员身份
    _ = current_admin.id

    # 查询用户
    user = await dao.get_by_id(User, user_id)
    if not user:
        raise HTTPNotFound(text='User not found')

    return user
