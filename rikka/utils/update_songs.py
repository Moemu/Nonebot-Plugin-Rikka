from __future__ import annotations

import json
from asyncio import sleep
from dataclasses import fields
from pathlib import Path

from aiohttp import ClientSession
from nonebot import logger
from typing_extensions import TypedDict

from ..models.song import MaiSong, SongDifficulties

_BASE_SONG_QUERY_URL = "https://maimai.lxns.net/api/v0/maimai/song/{song_id}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)

_MUSIC_CHART_PATH = Path("./static/music_chart.json")
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
        # TODO: 用另外的 API 拿拟合系数
        logger.warning(f"曲目 {song_id} 不存在于静态资源文件中，将此曲目的拟合系数设为 0")
        for index, difficulty in enumerate(song_info_dict["difficulties"].standard):
            difficulty.level_fit = 0.0
        for index, difficulty in enumerate(song_info_dict["difficulties"].dx):
            difficulty.level_fit = 0.0

    song_info = MaiSong(**song_info_dict)

    return song_info
