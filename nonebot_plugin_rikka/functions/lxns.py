import logging
from datetime import datetime, timezone
from typing import List, Literal

import httpx
from typing_extensions import TypedDict

from ..database import MaiSongORM

logger = logging.getLogger("sdgb_workflow")

BASE_URL = "https://maimai.lxns.net/api/v0/user/maimai/player"

COMBO_ID_TO_NAME = [None, "fc", "fcp", "ap", "app"]
SYNC_ID_TO_NAME = [None, "fs", "fsp", "fsd", "fsdp", "sync"]


class LXNSMaimaiRecord(TypedDict):
    id: int
    type: Literal["standard", "dx"]
    achievements: float
    level_index: int
    fc: Literal[None, "fc", "fcp", "ap", "app"]
    fs: Literal[None, "fs", "fsp", "fsd", "fsdp", "sync"]
    dx_score: int
    play_time: str  # 2023-12-31T16:00:00Z


class UserMusicDetail(TypedDict):
    musicId: int
    level: int
    playCount: int
    achievement: int
    comboStatus: int
    syncStatus: int
    deluxscoreMax: int
    scoreRank: int
    extNum1: int
    extNum2: int


async def upload_to_lxns_maimai(token: str, scores: List[LXNSMaimaiRecord]) -> None:
    """上传成绩到落雪查分器"""
    headers = {"X-User-Token": token, "Content-Type": "application/json"}

    logger.info(f"准备上传 {len(scores)} 条记录到落雪查分器...")
    payload = {"scores": scores}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{BASE_URL}/scores",
                json=payload,
                headers=headers,
                timeout=30.0,
            )

            if resp.status_code != 200:
                logger.error(f"[LXNS] 上传失败：HTTP {resp.status_code} - {resp.text}")
                resp.raise_for_status()

            logger.info("[LXNS] 上传成功！")

        except httpx.RequestError as e:
            logger.error(f"[LXNS] 连接至服务器时出现问题: {e}")
            raise


def convert_to_lxns_maimai_format(
    scores: List[UserMusicDetail],
) -> List[LXNSMaimaiRecord]:
    """将 UserMusicDetail 列表转换为落雪查分器格式"""
    lx_list = []

    play_time = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    for score in scores:
        music_id = score["musicId"]

        # 跳过很多万以上的 ID (通常是宴谱或其他特殊谱面)
        if music_id >= 100000:
            continue

        # 判断谱面类型 (heuristic)
        notes_type = "dx" if music_id > 10000 else "standard"
        music_id = music_id - 10000 if notes_type == "dx" else music_id

        try:
            # 确保索引不越界
            combo_status = score["comboStatus"]
            sync_status = score["syncStatus"]

            fc_str = COMBO_ID_TO_NAME[combo_status] if 0 <= combo_status < len(COMBO_ID_TO_NAME) else ""
            fs_str = SYNC_ID_TO_NAME[sync_status] if 0 <= sync_status < len(SYNC_ID_TO_NAME) else ""

            entry: LXNSMaimaiRecord = {
                "achievements": score["achievement"] / 10000.0,
                "id": music_id,
                "type": notes_type,  # type: ignore
                "level_index": score["level"],
                "fc": fc_str,  # type: ignore
                "fs": fs_str,  # type: ignore
                "dx_score": score["deluxscoreMax"],
                "play_time": play_time,
            }  # type: ignore
            lx_list.append(entry)
        except Exception as e:
            logger.error(f"转换成绩出错 (MusicId: {music_id}): {e}")
            continue

    return lx_list


async def get_updated_score(all_scores: list[UserMusicDetail], user_token: str) -> list[UserMusicDetail]:
    """
    获取需要更新的成绩列表
    """
    headers = {"X-User-Token": user_token, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/scores",
                headers=headers,
                timeout=30.0,
            )

            if not resp.status_code == 200:
                logger.info(f"获取成绩失败: HTTP {resp.status_code} - {resp.text}")
                resp.raise_for_status()

        except httpx.RequestError as e:
            logger.error(f"落雪查分器连接失败: {e}")
            raise

    existing_scores: list[LXNSMaimaiRecord] = resp.json()["data"]
    updated_scores: list[UserMusicDetail] = []

    for score in all_scores:
        music_id = score["musicId"]

        # 跳过很多万以上的 ID (通常是宴谱或其他特殊谱面)
        if music_id >= 100000:
            continue

        # 判断谱面类型 (heuristic)
        notes_type = "dx" if music_id > 10000 else "standard"
        music_id = music_id - 10000 if notes_type == "dx" else music_id

        # 确保数据库中真实存在目标歌曲
        all_music_id = MaiSongORM._cache.keys()
        if music_id not in all_music_id:
            continue

        # 查找对应的成绩记录
        existing_record = next(
            (
                record
                for record in existing_scores
                if record["id"] == music_id and record["type"] == notes_type and record["level_index"] == score["level"]
            ),
            None,
        )

        # 如果没有现有记录，或者成绩有更新，则添加到更新列表
        if not existing_record or (
            score["achievement"] / 10000.0 > existing_record["achievements"]
            or score["deluxscoreMax"] > existing_record["dx_score"]
        ):
            updated_scores.append(score)

    return updated_scores
