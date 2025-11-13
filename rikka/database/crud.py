import json
from typing import Optional

from nonebot import logger
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select, update

from ..models.song import MaiSong, SongDifficulties, SongDifficulty, SongDifficultyUtage
from ..utils.update_songs import fetch_song_info
from .orm_models import MaiSong as MaiSongORMModel
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

    @staticmethod
    async def set_diving_fish_import_token(
        session: async_scoped_session, user_id: str, import_token: str, diving_fish_username: str
    ) -> None:
        """设置用户的水鱼查分器导入密钥"""
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)
        if bind_info:
            await session.execute(
                update(UserBindInfo)
                .where(UserBindInfo.user_id == user_id)
                .values(diving_fish_import_token=import_token, diving_fish_username=diving_fish_username)
            )
        else:
            new_bind_info = UserBindInfo(
                user_id=user_id, diving_fish_import_token=import_token, diving_fish_username=diving_fish_username
            )
            session.add(new_bind_info)
        await session.commit()


class MaiSongORM:
    @staticmethod
    def _convert(row: MaiSongORMModel) -> MaiSong:
        """
        反序列化 MaiSongORMModel 为 MaiSong
        """
        # 数据库存储为字符串列，需要反序列化为字典
        diffs = row.difficulties if isinstance(row.difficulties, dict) else json.loads(row.difficulties)
        standard_difficulties = [SongDifficulty(**d) for d in diffs.get("standard", [])]
        dx_difficulties = [SongDifficulty(**d) for d in diffs.get("dx", [])]
        utage_difficulties = [SongDifficultyUtage(**d) for d in diffs.get("utage", [])] if diffs.get("utage") else None
        return MaiSong(
            id=row.id,
            title=row.title,
            artist=row.artist,
            genre=row.genre,
            bpm=row.bpm,
            map=row.map,
            version=row.version,
            difficulties=SongDifficulties(standard=standard_difficulties, dx=dx_difficulties, utage=utage_difficulties),
        )

    @staticmethod
    async def save_song_info(session: async_scoped_session, song: MaiSong) -> None:
        """
        保存曲目信息到数据库
        """
        difficulties_dict = {
            "standard": [d.__dict__ for d in song.difficulties.standard],
            "dx": [d.__dict__ for d in song.difficulties.dx],
            "utage": [d.__dict__ for d in song.difficulties.utage] if song.difficulties.utage else [],
        }
        song_obj = MaiSongORMModel(
            id=song.id,
            title=song.title,
            artist=song.artist,
            genre=song.genre,
            bpm=song.bpm,
            map=song.map,
            version=song.version,
            # ORM 列为 String，这里序列化为 JSON 字符串
            difficulties=json.dumps(difficulties_dict, ensure_ascii=False),
        )
        session.add(song_obj)
        await session.commit()

    @staticmethod
    async def get_song_info(session: async_scoped_session, song_id: int) -> MaiSong:
        """
        获取曲目信息，如果数据库中不存在则从远程获取并保存

        :param song_id: 曲目 ID
        """
        result = await session.execute(select(MaiSongORMModel).where(MaiSongORMModel.id == song_id))
        song_row = result.scalar_one_or_none()
        if song_row:
            return MaiSongORM._convert(song_row)

        logger.warning(f"曲目 ID {song_id} 不存在于数据库，正在从远程获取...")
        song_info = await fetch_song_info(song_id)
        await MaiSongORM.save_song_info(session, song_info)
        return song_info
