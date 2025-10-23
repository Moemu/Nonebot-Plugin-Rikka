from aiohttp.client_exceptions import ClientResponseError
from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot.adapters import Event
from nonebot.params import Depends
from nonebot_plugin_alconna import (
    AlconnaMatch,
    At,
    CommandMeta,
    Match,
    Subcommand,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_orm import async_scoped_session

from .database import UserBindInfoORM
from .score import LXNSScoreProvider, get_lxns_provider

COMMAND_PREFIXES = [".", "/"]

alconna_bind = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "bind",
        Subcommand("help"),
        Subcommand("lxns", Args["token", str], help_text=".bind lxns <落雪咖啡屋的个人 API 密钥> 绑定落雪咖啡屋查分器"),
        meta=CommandMeta("[查分器相关]绑定游戏账号/查分器"),
    ),
    priority=10,
    block=True,
    skip_for_unmatch=False,
)

alconna_b50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "b50", meta=CommandMeta("[舞萌DX]生成玩家 B50")),
    priority=10,
    block=True,
)


@alconna_bind.assign("lxns")
async def handle_bind_lxns(
    event: Event,
    db_session: async_scoped_session,
    score_provider: LXNSScoreProvider = Depends(get_lxns_provider),
    token: Match[str] = AlconnaMatch("token"),
):
    user_id = event.get_user_id()

    if not token.available:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的落雪咖啡屋 API 密钥",
            ]
        ).finish()
        return

    lxns_token = token.result

    logger.debug("尝试验证玩家 API 密钥是否正确")
    try:
        player_info = await score_provider.fetch_player_info_by_user_token(lxns_token)
    except ClientResponseError as e:
        logger.warning(f"玩家提供的 API 可能有误: {e.message}")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的落雪咖啡屋 API 密钥",
            ]
        ).finish()
        return

    await UserBindInfoORM.set_user_friend_code(db_session, user_id, player_info.friend_code)
    await UserBindInfoORM.set_lxns_api_key(db_session, user_id, lxns_token)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已绑定至游戏账号: {player_info.name} ⭐",
        ]
    ).finish()
