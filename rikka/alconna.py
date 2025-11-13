import itertools
from typing import cast

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

from .database import UserBindInfo, UserBindInfoORM
from .renderer import PicRenderer
from .score import (
    DivingFishScoreProvider,
    LXNSScoreProvider,
    PlayerMaiInfo,
    auto_get_score_provider,
    get_divingfish_provider,
    get_lxns_provider,
)

renderer = PicRenderer()

COMMAND_PREFIXES = [".", "/"]

alconna_bind = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "bind",
        Subcommand("help"),
        Subcommand("lxns", Args["token", str], help_text=".bind lxns <落雪咖啡屋的个人 API 密钥> 绑定落雪咖啡屋查分器"),
        Subcommand(
            "divingfish", Args["token", str], help_text=".bind divingfish <水鱼查分器的成绩导入密钥> 绑定水鱼查分器"
        ),
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

    await UserBindInfoORM.set_user_friend_code(db_session, user_id, player_info.friend_code)  # type:ignore
    await UserBindInfoORM.set_lxns_api_key(db_session, user_id, lxns_token)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已绑定至游戏账号: {player_info.name} ⭐",
        ]
    ).finish()


@alconna_bind.assign("divingfish")
async def handle_bind_divingfish(
    event: Event,
    db_session: async_scoped_session,
    score_provider: DivingFishScoreProvider = Depends(get_divingfish_provider),
    token: Match[str] = AlconnaMatch("token"),
):
    user_id = event.get_user_id()

    if not token.available:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的水鱼查分器成绩导入密钥",
            ]
        ).finish()
        return

    import_token = token.result

    logger.debug("尝试验证玩家 API 密钥是否正确")
    try:
        player_info = await score_provider.fetch_player_records_by_import_token(import_token)
    except ClientResponseError as e:
        logger.warning(f"玩家提供的 import_token 可能有误: {e.message}")
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的水鱼查分器成绩导入密钥",
            ]
        ).finish()
        return

    await UserBindInfoORM.set_diving_fish_import_token(db_session, user_id, import_token, player_info["username"])

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已绑定至水鱼账号: {player_info['username']} ⭐",
        ]
    ).finish()


@alconna_b50.handle()
async def handle_mai_b50(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()
    score_provider = await auto_get_score_provider(user_id)

    logger.info(f"[{user_id}] 获取玩家 Best50, 查分器名称: {score_provider.provider}")
    logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家绑定信息...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    # 落雪查分器
    if isinstance(score_provider, LXNSScoreProvider):
        new_player_friend_code = None
        # When user_bind_info is None, score_provider is LXNSScoreProvider.
        if user_bind_info is None:
            logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
            logger.debug(f"[{user_id}] 1/4 尝试通过 QQ 请求玩家数据")
            try:
                player_info = await score_provider.fetch_player_info_by_qq(user_id)
                new_player_friend_code = player_info.friend_code
            except ClientResponseError as e:
                logger.warning(f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e.code}: {e.message}")

                await UniMessage(
                    [
                        At(flag="user", target=user_id),
                        "你还未绑定查分器，请使用 /bind 指令进行绑定！",
                    ]
                ).finish()

                return

        friend_code = new_player_friend_code or user_bind_info.friend_code  # type:ignore
        if not friend_code:
            logger.warning(f"[{user_id}] 无法获取好友码，无法继续查询。")
            await UniMessage(
                [
                    At(flag="user", target=user_id),
                    "无法获取好友码，请确认已绑定或查分器可用。",
                ]
            ).finish()
            return
        logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
        player_info = await score_provider.fetch_player_info(friend_code)

        logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Best50...")
        player_b50 = await score_provider.fetch_player_b50(friend_code)

    # 水鱼查分器
    elif isinstance(score_provider, DivingFishScoreProvider):
        # When score_provider is DivingFish, user_bind_info and diving_fish_username is not None.
        user_bind_info = cast(UserBindInfo, user_bind_info)
        diving_fish_username = user_bind_info.diving_fish_username
        assert diving_fish_username

        logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家 Best50...")
        player_b50 = await score_provider.fetch_player_b50(diving_fish_username)

        logger.debug(f"[{user_id}] 3/4 构建玩家数据...")
        rating = sum(score.dx_rating for score in itertools.chain(player_b50.dx, player_b50.standard))
        player_info = PlayerMaiInfo(diving_fish_username, int(rating), 0, 0)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_b50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()
