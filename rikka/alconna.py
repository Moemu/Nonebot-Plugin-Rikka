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
from nonebot_plugin_alconna.uniseg import Image as UniImage
from nonebot_plugin_orm import async_scoped_session

from .config import config
from .database import UserBindInfoORM
from .renderer import PicRenderer
from .score import LXNSScoreProvider, get_lxns_provider

renderer = PicRenderer()

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


@alconna_b50.handle()
async def handle_mai_b50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: LXNSScoreProvider = Depends(get_lxns_provider),
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 获取玩家 Best50")
    logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家码...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    if user_bind_info is None:
        logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
        logger.debug(f"[{user_id}] 1/4 尝试通过 QQ 请求玩家数据")
        try:
            player_info = await score_provider.fetch_player_info_by_qq(user_id, config.lxns_developer_api_key)
        except ClientResponseError as e:
            logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e.code}: {e.message}")

            await UniMessage(
                [
                    At(flag="user", target=user_id),
                    "你还未绑定查分器，请使用 /bind 指令进行绑定！",
                ]
            ).finish()

            return
    else:
        friend_code = user_bind_info.friend_code
        logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
        player_info = await score_provider.fetch_player_info(friend_code, config.lxns_developer_api_key)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Best50...")
    player_b50 = await score_provider.fetch_player_b50(friend_code, config.lxns_developer_api_key)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_b50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()
