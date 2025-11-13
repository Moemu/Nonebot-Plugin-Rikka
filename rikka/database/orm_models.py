from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from typing_extensions import TypedDict


class SongDifficulties(TypedDict):
    standard: list
    """曲目标准谱面难度列表"""
    dx: list
    """曲目 DX 谱面难度列表"""
    utage: list
    """可选，宴会场曲目谱面难度列表"""


class UserBindInfo(Model):
    user_id: Mapped[str] = mapped_column(primary_key=True)
    friend_code: Mapped[str] = mapped_column(String, nullable=True, default="")
    lxns_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_import_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    diving_fish_username: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")


class MaiSong(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=False)
    bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    map: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    locked: Mapped[bool] = mapped_column(nullable=True, default=False)
    disabled: Mapped[bool] = mapped_column(nullable=True, default=False)
    difficulties: Mapped[SongDifficulties] = mapped_column(String, nullable=False)
