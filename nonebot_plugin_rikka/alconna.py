from pathlib import Path

from aiohttp.client_exceptions import ClientResponseError
from arclet.alconna import Alconna, AllParam, Args
from maimai_py import LXNSProvider
from nonebot import get_driver, logger
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
from .constants import _MAI_VERSION_MAP
from .database import MaiSongAliasORM, UserBindInfoORM
from .renderer import PicRenderer
from .score import (
    DivingFishScoreProvider,
    LXNSScoreProvider,
    MaimaiPyScoreProvider,
    get_divingfish_provider,
    get_lxns_provider,
    get_maimaipy_provider,
)
from .utils.update_songs import update_song_alias_list
from .utils.utils import get_song_by_id_or_alias, is_float

renderer = PicRenderer()


COMMAND_PREFIXES = [".", "/"]

_MAI_SONG_INFO_TEMPLATE = """[舞萌DX] 乐曲信息
标题: {title}
艺术家: {artist}
分类: {genre}
BPM: {bpm}
版本: {version}
"""

alconna_help = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "help",
        meta=CommandMeta("显示帮助信息", usage=".help"),
    ),
)

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

alconna_source = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "source",
        Args["provider", str],
        meta=CommandMeta("[查分器相关]设置默认查分器", usage=".source <lxns|divingfish>"),
    ),
    priority=10,
    block=True,
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
        Args["name", AllParam(str)],
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
        Subcommand("query", Args["name", AllParam(str)], help_text=".alias query <id|别名> 查询该歌曲有什么别名"),
        meta=CommandMeta("[舞萌DX]乐曲别名管理"),
    ),
    priority=10,
    block=True,
)

alconna_score = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "score",
        Args["name", AllParam(str)],
        meta=CommandMeta("[舞萌DX]获取单曲游玩情况", usage=".score <id|别名>"),
    )
)

alconna_scoreslist = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "scoreslist",
        Args["arg", str],
        meta=CommandMeta(
            "[舞萌DX]获取指定条件的成绩列表", usage=".scoreslist <level|ach>", example=".scoreslist ach100.4"
        ),
    )
)

alconna_update = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "update",
        Subcommand("songs", help_text=".update songs 更新乐曲信息数据库"),
        Subcommand("alias", help_text=".update alias 更新乐曲别名列表"),
        Subcommand("chart", help_text=".update chart 更新 music_chart.json 文件"),
        meta=CommandMeta("[舞萌DX]更新乐曲信息或别名列表"),
    ),
    priority=10,
    block=True,
)


@alconna_help.handle()
async def handle_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "Rikka 查分器帮助:\n"
        ".bind <查分器名称> <API密钥> 绑定查分器账号\n"
        ".source <查分器名称> 设置默认查分器\n"
        ".b50 获取玩家 Best 50\n"
        ".ap50 获取玩家 ALL PERFECT 50\n"
        ".r50 获取玩家 Recent 50 (需绑定落雪查分器)\n"
        ".minfo <乐曲ID/别名> 获取乐曲信息\n"
        ".alias 管理乐曲别名（添加、查询、更新）\n"
        ".score <乐曲ID/别名> 获取单曲游玩情况\n"
        ".scoreslist <level|ach> 获取指定条件的成绩列表\n"
        ".update songs 更新乐曲信息数据库\n"
        ".update alias 更新乐曲别名列表\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


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


@alconna_bind.assign("help")
async def handle_bind_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "查分器绑定帮助:\n"
        ".bind lxns <落雪咖啡屋的个人 API 密钥> 绑定落雪咖啡屋查分器\n"
        ".bind divingfish <水鱼查分器的成绩导入密钥> 绑定水鱼查分器\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


@alconna_bind.assign("$main")
async def handle_bind_main(event: Event):
    return await handle_bind_help(event)


@alconna_source.handle()
async def handle_source(
    event: Event,
    db_session: async_scoped_session,
    provider: Match[str] = AlconnaMatch("provider"),
):
    user_id = event.get_user_id()

    if not provider.available or provider.result not in ["lxns", "divingfish"]:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "请输入有效的查分器名称: lxns 或 divingfish",
            ]
        ).finish()
        return

    try:
        await UserBindInfoORM.set_default_provider(db_session, user_id, provider.result)  # type:ignore
    except ValueError as e:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                str(e),
            ]
        ).finish()
        return

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已将默认查分器设置为: {provider.result} ⭐",
        ]
    ).finish()


@alconna_b50.handle()
async def handle_mai_b50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家 Best50, 查分器类型: {type(provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Best50...")
    player_b50 = await score_provider.fetch_player_b50(params)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_best50(player_b50, player_info)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_ap50.handle()
async def handle_mai_ap50(
    event: Event,
    db_session: async_scoped_session,
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)

    logger.info(f"[{user_id}] 获取玩家 AP50, 查分器类型: {type(score_provider)}")
    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")

    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 AP 50...")
    if isinstance(provider, LXNSProvider):
        user_bind_info = await UserBindInfoORM.get_user_bind_info(db_session, user_id)
        if user_bind_info is None or user_bind_info.lxns_api_key is None:
            await UniMessage("你还没有绑定任何查分器喵，请先用 /bind 绑定一个查分器谢谢喵").finish()
            return  # Avoid TypeError.

        identifier.credentials = user_bind_info.lxns_api_key
        params = score_provider.ParamsType(provider, identifier)

    player_ap50 = await score_provider.fetch_player_ap50(params)

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
    params = score_provider.ParamsType(friend_code=friend_code)
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家 Recent 50...")
    player_r50 = await score_provider.fetch_player_r50(friend_code)

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_scores(player_r50, player_info, title="Recent 50")

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_minfo.handle()
async def handle_minfo(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()
    logger.info(f"[{user_id}] 查询乐曲信息, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/4 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

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
    nb_config = get_driver().config

    if user_id not in nb_config.superusers:
        await UniMessage("更新乐曲别名需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 更新乐曲别名列表")

    await update_song_alias_list(db_session)

    logger.info(f"[{user_id}] 乐曲别名列表更新完成")

    await UniMessage(
        [
            At(flag="user", target=user_id),
            "乐曲别名列表已更新完成 ⭐",
        ]
    ).finish()


@alconna_alias.assign("add")
async def handle_alias_add(
    event: Event,
    db_session: async_scoped_session,
    name: Match[str] = AlconnaMatch("alias"),
    song_id: Match[int] = AlconnaMatch("song_id"),
):
    user_id = event.get_user_id()

    if config.add_alias_need_admin:
        nb_config = get_driver().config

        if user_id not in nb_config.superusers:
            await UniMessage("更新乐曲别名需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 添加乐曲别名, 乐曲ID: {song_id.result}, 别名: {name.result}")

    await MaiSongAliasORM.add_custom_alias(db_session, song_id.result, name.result)

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"已为乐曲 ID {song_id.result} 添加别名: {name.result} ⭐",
        ]
    ).finish()


@alconna_alias.assign("query")
async def handle_alias_query(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()

    logger.info(f"[{user_id}] 查询乐曲别名, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/4 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 2/4 获取乐曲别名列表...")
    aliases = await MaiSongAliasORM.get_aliases(db_session, song.id)

    logger.debug(f"[{user_id}] 3/4 构建乐曲别名模板...")

    if not aliases:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                f"乐曲 ID {song.id} ('{song.title}') 暂无别名记录！",
            ]
        ).finish()
        return

    alias_list_content = ", ".join(aliases)
    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"乐曲 ID {song.id} ('{song.title}') 的别名列表如下：\n{alias_list_content}",
        ]
    ).finish()


@alconna_alias.assign("help")
async def handle_alias_help(event: Event):
    user_id = event.get_user_id()

    help_text = (
        "乐曲别名管理帮助:\n"
        ".alias add <乐曲ID> <别名> 添加乐曲别名\n"
        ".alias update 更新本地乐曲别名列表\n"
        ".alias query <id|别名> 查询该歌曲有什么别名\n"
    )

    await UniMessage(
        [
            At(flag="user", target=user_id),
            help_text,
        ]
    ).finish()


@alconna_alias.assign("$main")
async def handle_alias_main(event: Event):
    return await handle_alias_help(event)


@alconna_score.handle()
async def handle_score(
    event: Event,
    db_session: async_scoped_session,
    name: Match[UniMessage] = AlconnaMatch("name"),
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    if not name.available:
        await UniMessage([At(flag="user", target=user_id), "请输入有效的乐曲ID/名称/别名！"]).finish()

    raw_query = name.result.extract_plain_text()
    logger.info(f"[{user_id}] 查询单曲游玩情况, 查询内容: {raw_query}")

    logger.debug(f"[{user_id}] 1/5 通过乐曲ID/别名查询乐曲信息...")
    try:
        song = await get_song_by_id_or_alias(db_session, raw_query)
    except ValueError as e:
        await UniMessage([At(flag="user", target=user_id), str(e)]).finish()
        return

    logger.debug(f"[{user_id}] 2/5 推断获取的是 DX 铺面还是标准铺面")
    if raw_query.isdigit():
        if int(raw_query) > 10000 or not song.difficulties.standard:
            is_dx = True
        else:
            is_dx = False
    else:
        is_dx = len(song.difficulties.dx) > 0
    logger.debug(f"[{user_id}] 2/5 推断为 {'DX' if is_dx else '标准'} 铺面")

    logger.debug(f"[{user_id}] 3/5 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(db_session, user_id, provider)
    params = score_provider.ParamsType(provider, identifier)

    logger.debug(f"[{user_id}] 4/5 发起 API 请求玩家信息...")
    scores = await score_provider.fetch_player_minfo(params, song.id, "dx" if is_dx else "standard")

    if not scores:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                f"未找到乐曲 '{song.title}' 的游玩记录喵~不如先去挑战一下吧~",
            ]
        ).finish()
        return

    logger.debug(f"[{user_id}] 5/5 渲染玩家数据...")
    pic = await renderer.render_mai_player_song_info(song, scores)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_scoreslist.handle()
async def handle_scoreslist(
    event: Event,
    db_session: async_scoped_session,
    arg: Match[str] = AlconnaMatch("arg"),
    score_provider: MaimaiPyScoreProvider = Depends(get_maimaipy_provider),
):
    user_id = event.get_user_id()

    if not arg.available or not arg.result:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                (
                    ".scoreslist 使用帮助\n"
                    ".scoreslist level 获取指定等级的成绩列表\n"
                    ".scoreslist ach 获取指定达成率的成绩列表\n"
                    "eg.\n"
                    ".scoreslist 12+\n"
                    ".scoreslist ach100.8"
                ),
            ]
        ).finish()

    raw_query = arg.result
    logger.info(f"[{user_id}] 查询指定条件的成绩列表, 查询内容: {raw_query}")
    level = None
    ach = None
    if raw_query.isdigit() or (raw_query.endswith("+") and raw_query[:-1].isdigit()):
        level = raw_query
        title = f"{level} 成绩列表"
    elif raw_query.startswith("ach") and is_float(raw_query[3:]):
        ach = float(raw_query[3:])
        title = f"达成率 {ach} 成绩列表"
    else:
        await UniMessage([At(flag="user", target=user_id), "命令格式错误，请检查后重新输入！"]).finish()
        return

    logger.debug(f"[{user_id}] 1/4 获得用户鉴权凭证...")
    provider = await MaimaiPyScoreProvider.auto_get_score_provider(db_session, user_id)
    identifier = await MaimaiPyScoreProvider.auto_get_player_identifier(
        db_session, user_id, provider, use_personal_api=True
    )
    params = score_provider.ParamsType(provider, identifier)
    logger.debug(f"[{user_id}] 1/4 鉴权参数: {params}")

    logger.debug(f"[{user_id}] 2/4 发起 API 请求玩家信息...")
    player_info = await score_provider.fetch_player_info(params)

    logger.debug(f"[{user_id}] 3/4 发起 API 请求玩家全部成绩...")
    scores = await score_provider.fetch_player_scoreslist(params, level, ach)

    if not scores:
        await UniMessage(
            [
                At(flag="user", target=user_id),
                "呜呜，未找到符合条件的游玩记录喵",
            ]
        ).finish()
        return

    logger.debug(f"[{user_id}] 4/4 渲染玩家数据...")
    pic = await renderer.render_mai_player_scores(scores[:50], player_info, title)

    await UniMessage([At(flag="user", target=user_id), UniImage(raw=pic)]).finish()


@alconna_update.assign("songs")
async def handle_update_songs(
    event: Event,
    db_session: async_scoped_session,
):
    user_id = event.get_user_id()
    nb_config = get_driver().config

    if user_id not in nb_config.superusers:
        await UniMessage("更新乐曲信息需要管理员权限哦").finish()

    logger.info(f"[{user_id}] 更新乐曲信息数据库")

    from .utils.update_songs import update_song_database

    updated_count = await update_song_database(db_session)

    logger.info(f"[{user_id}] 乐曲信息数据库更新完成，共更新 {updated_count} 首乐曲")

    await UniMessage(
        [
            At(flag="user", target=user_id),
            f"乐曲信息数据库已更新完成，共更新 {updated_count} 首乐曲 ⭐",
        ]
    ).finish()


@alconna_update.assign("alias")
async def handle_update_aliases(
    event: Event,
    db_session: async_scoped_session,
):
    await handle_alias_update(event, db_session)


@alconna_update.assign("chart")
async def handle_update_chart(event: Event):
    from .utils.update_songs import update_local_chart_file

    await update_local_chart_file()

    await UniMessage(
        [
            At(flag="user", target=event.get_user_id()),
            "music_chart.json 文件已更新完成⭐",
        ]
    ).finish()
