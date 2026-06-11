from nonebot import logger, require

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_orm")

from nonebot.plugin import PluginMetadata, inherit_supported_adapters  # noqa: E402

from .config import Config  # noqa: E402
from .utils import init_logger  # noqa: E402

init_logger()

from nonebot import get_driver  # noqa: E402
from nonebot_plugin_orm import get_scoped_session  # noqa: E402

from . import alconna  # noqa: E402, F401
from . import database  # noqa: E402, F401
from .database import ChuSongORM, MaiSongORM  # noqa: E402


@get_driver().on_startup
async def initialize_song_cache():
    session = get_scoped_session()
    logger.debug("更新乐曲缓存中...")
    await MaiSongORM.refresh_cache(session)
    await ChuSongORM.refresh_cache(session)


@get_driver().on_startup
async def migrate_chu_friend_codes():
    """数据迁移：为已有舞萌绑定但缺少中二好友码的用户自动补全 chu_friend_code。"""
    from sqlalchemy import select

    from .database import UserBindInfoORM
    from .database.orm_models import UserBindInfo
    from .score.chunithm import get_lxns_chu_provider

    session = get_scoped_session()
    provider = get_lxns_chu_provider()

    result = await session.execute(
        select(UserBindInfo).where(
            UserBindInfo.mai_friend_code.isnot(None),
            UserBindInfo.mai_friend_code != "",
            (UserBindInfo.chu_friend_code.is_(None) | (UserBindInfo.chu_friend_code == "")),
        )
    )
    users = result.scalars().all()

    if not users:
        return

    logger.info(f"[数据迁移] 发现 {len(users)} 个用户需要补全中二好友码")

    migrated = 0
    for user in users:
        uid = user.user_id  # 提前提取，避免 commit 后 ORM 属性过期
        try:
            from .score.chunithm.providers.lxns import LXNSChuParams

            info = await provider.fetch_player_info(LXNSChuParams(qq=uid))
            if info.friend_code:
                await UserBindInfoORM.set_user_chu_friend_code(session, uid, str(info.friend_code))
                migrated += 1
                logger.debug(f"[数据迁移] 用户 {uid} 中二好友码已补全: {info.friend_code}")
        except Exception as e:
            logger.debug(f"[数据迁移] 用户 {uid} 中二好友码补全失败: {e}")

    if migrated:
        logger.info(f"[数据迁移] 成功补全 {migrated} 个用户的中二好友码")


__plugin_meta__ = PluginMetadata(
    name="Nonebot-Plugin-Rikka",
    description="一个简单的舞萌成绩查询Bot插件，同时支持落雪咖啡屋和水鱼查分器",
    usage=".rikka",
    type="application",
    config=Config,
    homepage="https://github.com/Moemu/Nonebot-Plugin-Rikka",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)
