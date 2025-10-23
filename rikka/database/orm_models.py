from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class UserBindInfo(Model):
    user_id: Mapped[str] = mapped_column(primary_key=True)
    friend_code: Mapped[str] = mapped_column(String, nullable=True, default="")
    lxns_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
