from __future__ import annotations

import json
from asyncio import sleep
from dataclasses import fields
from pathlib import Path

from aiohttp import ClientSession
from nonebot import logger
from nonebot_plugin_orm import async_scoped_session
from typing_extensions import TypedDict

from ..config import config
from ..models.song import MaiSong, SongDifficulties

_BASE_SONG_QUERY_URL = "https://maimai.lxns.net/api/v0/maimai/song/{song_id}"
_DIVING_FISH_CHART_STATS_URL = "https://www.diving-fish.com/api/maimaidxprober/chart_stats"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)

_MUSIC_CHART_PATH = Path(config.static_resource_path) / "music_chart.json"
_MUSIC_CHART_DATA: "MusicChart" = json.loads(_MUSIC_CHART_PATH.read_text(encoding="utf-8"))


class MusicChartInfo(TypedDict):
    cnt: float
    diff: str
    """难度标级"""
    fit_diff: float
    """拟合定数"""
    avg: float
    """平均达成率"""
    avg_dx: float
    """平均 DX 分数"""
    std_dev: float
    dist: list[int]
    fc_dist: list[int]


class MusicChart(TypedDict):
    charts: dict[str, list[MusicChartInfo]]
    diff_data: dict[str, dict]


class MusicAliasResponseItem(TypedDict):
    song_id: int
    aliases: list[str]


class LXNSApiAliasResponse(TypedDict):
    aliases: list[MusicAliasResponseItem]


def get_song_fit_diff_from_local(song_id: int, difficulty: int) -> float:
    """
    从 `music_chart.json` 获取拟合定数

    :param song_id: 铺面ID
    :param difficulty: 难度类别
    """
    if not (chart_infos := _MUSIC_CHART_DATA["charts"].get(str(song_id))):
        raise ValueError(f"所请求的铺面 ID: {song_id} 不存在")

    if len(chart_infos) < difficulty:
        raise ValueError(f"难度 {difficulty} 在铺面 {song_id} 中不存在")

    return chart_infos[difficulty]["fit_diff"]


async def update_local_chart_file():
    """
    从水鱼更新 `music_chart.json` 文件
    """
    async with ClientSession() as session:
        async with session.get(_DIVING_FISH_CHART_STATS_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.json()

    _MUSIC_CHART_PATH.write_text(json.dumps(content, ensure_ascii=False, indent=4), encoding="utf-8")
    logger.info("已更新本地 music_chart.json 文件")

    global _MUSIC_CHART_DATA
    _MUSIC_CHART_DATA = content


async def fetch_song_info(song_id: int, interval: float = 0.3) -> MaiSong:
    """
    获取曲目信息

    :param song_id: 曲目 ID
    :param interval: 请求间隔时间
    """
    url = _BASE_SONG_QUERY_URL.format(song_id=song_id)

    async with ClientSession() as session:
        async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.json()
            await sleep(interval)  # 避免请求过于频繁

    song_info_fields = {f.name for f in fields(MaiSong)}
    song_info_dict = {k: v for k, v in content.items() if k in song_info_fields}
    song_info_dict["difficulties"] = SongDifficulties.init_from_dict(content.get("difficulties", {}))

    # 从本地获取拟合定数
    try:
        for index, difficulty in enumerate(song_info_dict["difficulties"].standard):
            difficulty.level_fit = get_song_fit_diff_from_local(song_id, index)
        for index, difficulty in enumerate(song_info_dict["difficulties"].dx):
            difficulty.level_fit = get_song_fit_diff_from_local(song_id + 10000, index)
    except ValueError:
        # 如果失败就先更新 `music_chart.json` 文件
        logger.warning(f"曲目 {song_id} 的拟合定数获取失败，尝试更新本地 chart 文件")
        await update_local_chart_file()
        try:
            for index, difficulty in enumerate(song_info_dict["difficulties"].standard):
                difficulty.level_fit = get_song_fit_diff_from_local(song_id, index)
            for index, difficulty in enumerate(song_info_dict["difficulties"].dx):
                difficulty.level_fit = get_song_fit_diff_from_local(song_id + 10000, index)
        except ValueError:
            logger.error(f"曲目 {song_id} 的拟合定数获取失败，跳过该曲目拟合定数设置")

    song_info = MaiSong(**song_info_dict)

    return song_info


async def update_song_alias_list(db_session: async_scoped_session):
    """
    通过落雪查分器更新别名表
    """
    _BASE_URL = "https://maimai.lxns.net/api/v0/maimai/alias/list"
    async with ClientSession() as session:
        async with session.get(_BASE_URL, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content: LXNSApiAliasResponse = await resp.json()

    from ..database import MaiSongAliasORM

    await MaiSongAliasORM.add_alias_batch(db_session, content["aliases"])
