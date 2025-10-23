from typing import Optional

from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select, update

from .orm_models import UserBindInfo


class UserBindInfoORM:
    @staticmethod
    async def get_user_bind_info(session: async_scoped_session, user_id: str) -> Optional[UserBindInfo]:
        """获取用户绑定信息"""
        result = await session.execute(select(UserBindInfo).where(UserBindInfo.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_user_friend_code(session: async_scoped_session, user_id: str, friend_code: str) -> None:
        """
        设置用户好友码
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(friend_code=friend_code)
            )
        else:
            new_bind_info = UserBindInfo(user_id=user_id, friend_code=friend_code)
            session.add(new_bind_info)
        await session.commit()

    @staticmethod
    async def set_lxns_api_key(session: async_scoped_session, user_id: str, api_key: str) -> None:
        """设置用户的落雪咖啡屋 API 密钥"""
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo).where(UserBindInfo.user_id == user_id).values(lxns_api_key=api_key)
            )
        else:
            new_bind_info = UserBindInfo(user_id=user_id, lxns_api_key=api_key)
            session.add(new_bind_info)
        await session.commit()
