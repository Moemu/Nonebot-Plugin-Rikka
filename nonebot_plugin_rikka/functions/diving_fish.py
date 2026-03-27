import logging
from typing import Any, Dict, List, Optional

import httpx
from typing_extensions import TypedDict

from ..database import MaiSongORM

logger = logging.getLogger("sdgb_workflow")

BASE_URL = "https://www.diving-fish.com/api/maimaidxprober"

# 水鱼查分器的成绩状态转换
COMBO_ID_TO_NAME = ["", "fc", "fcp", "ap", "app"]
SYNC_ID_TO_NAME = ["", "fs", "fsp", "fsd", "fsdp", "sync"]


class DivingFishRecord(TypedDict):
    achievements: float
    title: str
    type: str  # "SD" or "DX"
    level_index: int
    fc: str  # "" | "fc" | "fcp" | "ap" | "app"
    fs: str  # "" | "fs" | "fsp" | "fsd" | "fsdp" | "sync"
    dxScore: int


async def upload_to_diving_fish(token: str, payload: List[DivingFishRecord]) -> None:
    """上传成绩到水鱼查分器"""
    headers = {"Import-Token": token, "Content-Type": "application/json"}

    logger.info(f"准备上传 {len(payload)} 条记录到水鱼查分器...")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{BASE_URL}/player/update_records",
                json=payload,
                headers=headers,
                timeout=30.0,
            )

            if resp.status_code == 200:
                logger.info("水鱼查分器上传成功！")
            elif resp.status_code == 400:
                logger.error(f"上传失败：请求参数错误 ({resp.text})")
            elif resp.status_code == 401 or resp.status_code == 403:  # 假设 401/403 是认证失败
                logger.error("上传失败：Import Token 无效或鉴权失败")
                raise RuntimeError("DivingFish Auth Failed")
            else:
                logger.error(f"上传失败：HTTP {resp.status_code} - {resp.text}")
                resp.raise_for_status()

        except httpx.RequestError as e:
            logger.error(f"水鱼查分器连接失败: {e}")
            raise


def _get_song_title(music_id: int) -> Optional[str]:
    """根据 musicId 获取曲名"""
    if music_id >= 10000:
        # DX 谱面，ID 减去 10000 后再查询
        base_id = music_id - 10000
    else:
        base_id = music_id

    # 尝试直接获取
    song = MaiSongORM.get_song_sync(base_id)
    if song:
        return song.title

    return None


def convert_to_diving_fish_format(
    scores: List[Dict[str, Any]],
) -> List[DivingFishRecord]:
    """将 UserMusicDetail 列表转换为水鱼查分器格式"""
    df_list = []
    for score in scores:
        music_id = score["musicId"]

        # 跳过很多万以上的 ID (通常是宴谱或其他特殊谱面)
        if music_id >= 100000:
            continue

        title = _get_song_title(music_id)
        if not title:
            # logger.warning(f"未知曲目 ID: {music_id}，已跳过")
            continue

        # 判断谱面类型 (heuristic)
        notes_type = "DX" if music_id >= 10000 else "SD"

        try:
            # 确保索引不越界
            combo_status = score["comboStatus"]
            sync_status = score["syncStatus"]

            fc_str = COMBO_ID_TO_NAME[combo_status] if 0 <= combo_status < len(COMBO_ID_TO_NAME) else ""
            fs_str = SYNC_ID_TO_NAME[sync_status] if 0 <= sync_status < len(SYNC_ID_TO_NAME) else ""

            entry: DivingFishRecord = {
                "achievements": score["achievement"] / 10000.0,
                "title": title,
                "type": notes_type,
                "level_index": score["level"],
                "fc": fc_str,
                "fs": fs_str,
                "dxScore": score["deluxscoreMax"],
            }
            df_list.append(entry)
        except Exception as e:
            logger.error(f"转换成绩出错 (MusicId: {music_id}): {e}")
            continue

    return df_list
