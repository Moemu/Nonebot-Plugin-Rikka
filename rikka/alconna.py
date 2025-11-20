import itertools
from pathlib import Path
from typing import cast

from aiohttp.client_exceptions import ClientResponseError
from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot.adapters import Event
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
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
from .database import MaiSongORM, UserBindInfo, UserBindInfoORM
from .renderer import PicRenderer
from .score import (
    DivingFishScoreProvider,
    LXNSScoreProvider,
    PlayerMaiInfo,
    auto_get_score_provider,
    get_divingfish_provider,
    get_lxns_provider,
)
from .utils.update_songs import update_song_alias_list

renderer = PicRenderer()

COMMAND_PREFIXES = [".", "/"]

_MAI_SONG_INFO_TEMPLATE = """[舞萌DX] 乐曲信息
标题: {title}
艺术家: {artist}
分类: {genre}
BPM: {bpm}
版本: {version}
"""

_MAI_VERSION_MAP = {
    100: "maimai",
    110: "maimai PLUS",
    120: "GreeN",
    130: "GreeN PLUS",
    140: "ORANGE",
    150: "ORANGE PLUS",
    160: "PiNK",
    170: "PiNK PLUS",
    180: "MURASAKi",
    185: "MURASAKi PLUS",
    190: "MiLK",
    195: "MiLK PLUS",
    199: "FiNALE",
    200: "舞萌DX",
    210: "舞萌DX 2021",
    220: "舞萌DX 2022",
    230: "舞萌DX 2023",
    240: "舞萌DX 2024",
    250: "舞萌DX 2025",
}

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
    Alconna(COMMAND_PREFIXES, "b50", meta=CommandMeta("[舞萌DX]生成玩家 Best 50")),
    priority=10,
    block=True,
)

alconna_ap50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "ap50", meta=CommandMeta("[舞萌DX]生成玩家 ALL PERFECT 50")),
    priority=10,
    block=True,
)

alconna_r50 = on_alconna(
    Alconna(COMMAND_PREFIXES, "r50", meta=CommandMeta("[舞萌DX]生成玩家 Recent 50 (需绑定落雪查分器)")),
    priority=10,
    block=True,
)

alconna_minfo = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "minfo",
        Args["name", str],
        meta=CommandMeta("[舞萌DX]获取乐曲信息", usage=".minfo <id|别名>"),
    ),
    priority=10,
    block=True,
)

alconna_alias = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "alias",
        Subcommand("help"),
        Subcommand(
            "add", Args["song_id", int], Args["alias", str], help_text=".alias add <乐曲ID> <别名> 添加乐曲别名"
        ),
        Subcommand("update", help_text=".alias update 更新本地乐曲别名列表"),
        meta=CommandMeta("[舞萌DX]乐曲别名管理"),
    ),
    priority=10,
    block=True,
    permission=SUPERUSER,
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
    # elif isinstance(score_provider, DivingFishScoreProvider):
    else:
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


@alconna_ap50.handle()
async def handle_mai_ap50(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()
    score_provider = await auto_get_score_provider(user_id)

    logger.info(f"[{user_id}] 获取玩家 AP 50, 查分器名称: {score_provider.provider}")
    logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家绑定信息...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    # 落雪查分器
    if isinstance(score_provider, LXNSScoreProvider):
        new_player_friend_code = None
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

        logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 AP50...")
        player_ap50 = await score_provider.fetch_player_ap50(friend_code)

    # elif isinstance(score_provider, DivingFishScoreProvider):
    else:
        # When score_provider is DivingFish, user_bind_info and diving_fish_import_token is not None.
        user_bind_info = cast(UserBindInfo, user_bind_info)
        diving_fish_import_token = user_bind_info.diving_fish_import_token
        diving_fish_username = user_bind_info.diving_fish_username
        assert diving_fish_import_token
        assert diving_fish_username

        logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家 AP 50...")
        player_ap50 = await score_provider.fetch_player_ap50(diving_fish_import_token)

        logger.debug(f"[{user_id}] 3/4 构建玩家数据...")
        rating = sum(score.dx_rating for score in itertools.chain(player_ap50.dx, player_ap50.standard))
        player_info = PlayerMaiInfo(diving_fish_username, int(rating), 0, 0)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_ap50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_r50.handle()
async def handle_mai_r50(
    event: Event, db_session: async_scoped_session, score_provider: LXNSScoreProvider = Depends(get_lxns_provider)
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 获取玩家 Recent 50, 查分器名称: {score_provider.provider}")
    logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家绑定信息...")

    user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)

    new_player_friend_code = None
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
                    "查询 Recent 50 的操作需要绑定落雪查分器喵，还请使用 /bind 指令进行绑定喵呜",
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

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Recent 50...")
    player_r50 = await score_provider.fetch_player_r50(friend_code)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_scores(player_r50, player_info, title="Recent 50")

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_minfo.handle()
async def handle_minfo(
    event: Event,
    db_session: async_scoped_session,
    name: Match[str] = AlconnaMatch("name"),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result
    song_id = int(raw_query) if raw_query.isdigit() else None
    song_name = raw_query if song_id is None else None

    logger.info(f"[{user_id}] 查询乐曲信息, 查询内容: {raw_query}")
    songs = []

    if song_id is not None:
        logger.debug(f"[{user_id}] 1/4 通过乐曲ID {song_id} 查询乐曲信息...")
        song_id = song_id if song_id < 10000 or song_id > 100000 else song_id % 10000
        songs = [await MaiSongORM.get_song_info(db_session, song_id)]
    elif song_name is not None:
        logger.debug(f"[{user_id}] 1/4 通过乐曲名称/别名 {song_name} 查询乐曲信息...")
        songs = await MaiSongORM.get_song_info_by_name_or_alias(db_session, song_name)
    else:
        raise ValueError("Unreachable code reached in handle_minfo")

    if not songs:
        await UniMessage([At(flag="user", target=user_id), f"未找到与 '{raw_query}' 相关的乐曲信息！"]).finish()
        return

    if len(songs) > 1:
        logger.debug(f"[{user_id}] 4/4 找到多条乐曲信息，提前返回向用户确定具体乐曲ID")
        contents = [
            At(flag="user", target=user_id),
            f"找到多条与 '{raw_query}' 相关的乐曲信息，请指定你想查询的乐曲ID：",
        ]
        for song in songs:
            contents.append(f"\nID: {song.id} 标题: {song.title} 艺术家: {song.artist}")
        await UniMessage(contents).finish()
        return

    song = songs[0]

    logger.debug(f"[{user_id}] 2/4 获取乐曲封面...")
    song_cover = Path(config.static_resource_path) / "mai" / "cover" / f"{song.id}.png"

    if not song_cover.exists():
        dx_song_id = song.id + 10000  # DX 版封面
        song_cover = Path(config.static_resource_path) / "mai" / "cover" / f"{dx_song_id}.png"
        if not song_cover.exists():
            logger.warning(f"未找到乐曲 {song.id} 的封面图片")
            song_cover = Path(config.static_resource_path) / "mai" / "cover" / "0.png"

    logger.debug(f"[{user_id}] 3/4 获取定数信息...")

    response_difficulties_content = []

    if song.difficulties.standard:
        std_diffs = "/".join([str(diff.level_value) for diff in song.difficulties.standard])
        response_difficulties_content.append(f"定数: {std_diffs}")

        if song.difficulties.standard[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in song.difficulties.standard
                ]
            )
            response_difficulties_content.append(f"拟合定数: {fit_diffs}")

    if song.difficulties.dx:
        dx_diffs = "/".join([str(diff.level_value) for diff in song.difficulties.dx])
        response_difficulties_content.append(f"定数(DX): {dx_diffs}")

        if song.difficulties.dx[0].level_fit is not None:
            fit_diffs = "/".join(
                [
                    "{:.2f}".format(diff.level_fit) if diff.level_fit is not None else f"{diff.level}"
                    for diff in song.difficulties.dx
                ]
            )
            response_difficulties_content.append(f"拟合定数(DX): {fit_diffs}")

    logger.debug(f"[{user_id}] 4/4 构建乐曲信息模板...")

    response_content = UniMessage(
        [
            At(flag="user", target=user_id),
            UniImage(path=song_cover),
            _MAI_SONG_INFO_TEMPLATE.format(
                title=song.title,
                artist=song.artist,
                genre=song.genre,
                bpm=song.bpm,
                version=_MAI_VERSION_MAP.get(song.version // 100, "未知版本"),
            ),
            "\n".join(response_difficulties_content),
        ]
    )

    await response_content.finish()


@alconna_alias.assign("update")
async def handle_alias_update(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()

    logger.info(f"[{user_id}] 更新乐曲别名列表")

    await update_song_alias_list(db_session)

    logger.info(f"[{user_id}] 乐曲别名列表更新完成")

    await UniMessage(
        [
            At(flag="user", target=user_id),
            "乐曲别名列表已更新完成 ⭐",
        ]
    ).finish()
