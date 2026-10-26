import asyncio
import hashlib
import time
from dataclasses import dataclass, fields
from typing import Any, Optional, TypedDict

import httpx
from nonebot import logger
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_orm import get_scoped_session

from ....config import config
from ....constants import MAI_VERSION_MAP
from ....database import MaiSongORM
from ....updater.songs import update_maimai_song_database
from .._base import BaseScoreProvider
from .._schema import (
    PlayerMaiB50,
    PlayerMaiInfo,
    PlayerMaiScore,
    ScoreFCType,
    ScoreFSType,
    ScoreRateType,
    SongDifficulty,
    SongType,
)

# 水鱼查分器的成绩状态转换
COMBO_ID_TO_NAME = ["", "fc", "fcp", "ap", "app"]
SYNC_ID_TO_NAME = ["", "fs", "fsp", "fsd", "fsdp", "sync"]


class DivingFishCharts(TypedDict):
    sd: list[dict]
    dx: list[dict]


class DivingFishBest50Response(TypedDict):
    additional_rating: int
    """段位信息"""
    charts: DivingFishCharts
    nickname: str
    """用户的昵称"""
    plate: str
    """用户的牌子信息"""
    rating: int
    user_general_data: None
    """占位符"""
    username: str
    """水鱼用户名"""


class DivingFishPlayerRecordsResponse(TypedDict):
    additional_rating: int
    """段位信息"""
    records: list[dict]
    nickname: str
    """用户的昵称"""
    plate: str
    """用户的牌子信息"""
    rating: int
    username: str
    """水鱼用户名"""


class DivingFishRecord(TypedDict):
    achievements: float
    title: str
    type: str  # "SD" or "DX"
    level_index: int
    fc: str  # "" | "fc" | "fcp" | "ap" | "app"
    fs: str  # "" | "fs" | "fsp" | "fsd" | "fsdp" | "sync"
    dxScore: int


@dataclass
class DivingFishParams:
    user_id: str


class DivingFishScoreProvider(BaseScoreProvider[DivingFishParams]):
    provider = "diving-fish"
    auth_url = "https://auth.diving-fish.com"
    base_url = "https://www.diving-fish.com/api/maimaidxprober/"
    ParamsType = DivingFishParams

    def __init__(self) -> None:
        super().__init__()
        self._client = httpx.AsyncClient(timeout=30)

        from .maimai import _divingfish_provider, maimai_client

        self._access_token_cache = maimai_client._cache
        self._oauth_token_namespace = _divingfish_provider.oauth_token_namespace

    @staticmethod
    def check_divingfish_configure():
        if config.divingfish_client_id and config.divingfish_client_secret:
            return
        raise ValueError("Bot 未配置水鱼 OAuth，请联系管理员")

    @staticmethod
    def subject_ref(user_id: str) -> str:
        return hashlib.sha256(f"{config.divingfish_client_id}:{user_id}".encode()).hexdigest()

    @staticmethod
    def mask_user(user_id: str) -> str:
        return f"User {user_id[:2]}****{user_id[-2:]}" if len(user_id) > 4 else "User ****"

    async def poll(self, device_code: str, interval: int = 5, timeout: int = 600) -> dict:
        deadline = time.time() + timeout

        while time.time() < deadline:
            await asyncio.sleep(interval)
            response = await self._client.post(
                f"{self.auth_url}/oauth/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": config.divingfish_client_id,
                    "client_secret": config.divingfish_client_secret,
                },
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()

            error = response.json().get("error")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            raise RuntimeError(f"绑定失败: {error}")  # access_denied / expired_token
        raise TimeoutError("用户未在有效期内完成绑定")

    async def start_binding(self, user_id: str):
        """向用户发起一次绑定。label 是给用户看的遮挡后展示串。"""
        self.check_divingfish_configure()

        response = await self._client.post(
            f"{self.auth_url}/oauth/device_authorization",
            data={
                "client_id": config.divingfish_client_id,
                "client_secret": config.divingfish_client_secret,
                "scope": "prober.profile.read prober.records.read prober.records.write",
                "subject_ref": self.subject_ref(user_id),
                "binding_label": self.mask_user(user_id),
            },
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

        await UniMessage(f"请进入以下链接完成绑定: {data['verification_uri_complete']} (10 分钟内有效)").send()

        await self.poll(data["device_code"])

    async def access_token(self, user_id: str) -> str:
        self.check_divingfish_configure()

        subject = self.subject_ref(user_id)
        token = await self._access_token_cache.get(subject, namespace=self._oauth_token_namespace)
        if token:
            return token

        response = await self._client.post(
            f"{self.auth_url}/oauth/token",
            data={
                "grant_type": "urn:diving-fish:params:oauth:grant-type:on-behalf-of",
                "client_id": config.divingfish_client_id,
                "client_secret": config.divingfish_client_secret,
                "subject": "ref:" + self.subject_ref(user_id),
                "scope": "prober.records.read",
            },
            timeout=10,
        )

        if response.status_code == 400 and response.json().get("error") == "consent_required":
            await self.start_binding(user_id)
            return await self.access_token(user_id)

        response.raise_for_status()

        data = response.json()
        expires_in = data["expires_in"]
        token = data["access_token"]
        await self._access_token_cache.set(
            subject, token, ttl=max(expires_in - 30, 0), namespace=self._oauth_token_namespace
        )

        return data["access_token"]

    @staticmethod
    def _score_unpack(raw_score: dict) -> PlayerMaiScore:
        raw_score["song_difficulty"] = SongDifficulty(raw_score["level_index"])
        raw_score["fc"] = ScoreFCType(raw_score["fc"]) if raw_score.get("fc") else None
        raw_score["fs"] = ScoreFSType(raw_score["fs"]) if raw_score.get("fs") else None
        raw_score["rate"] = ScoreRateType(raw_score["rate"])
        raw_score["song_type"] = SongType("standard" if raw_score["type"] == "SD" else "dx")

        valid_keys = {f.name for f in fields(PlayerMaiScore)}
        filtered = {k: v for k, v in raw_score.items() if k in valid_keys}
        filtered["song_name"] = raw_score["title"]
        filtered["song_level"] = raw_score["level"]
        filtered["dx_score"] = raw_score["dxScore"]
        filtered["dx_rating"] = raw_score["ra"]
        filtered["dx_star"] = 0  # unsupported.

        return PlayerMaiScore(**filtered)

    async def fetch_player_info(self, params: DivingFishParams) -> PlayerMaiInfo:
        """
        获取玩家信息(水鱼不支持获取收藏品信息)
        """
        endpoint = "oauth/userinfo"
        access_token = await self.access_token(params.user_id)

        data: DivingFishBest50Response = await self._post_resp(endpoint, auth_token=access_token)
        return PlayerMaiInfo(data["nickname"], data["rating"], 0, 0)

    async def fetch_player_b50(self, params: DivingFishParams) -> PlayerMaiB50:
        """
        获得玩家 Best50 信息
        """
        endpoint = "query/player"
        access_token = await self.access_token(params.user_id)

        data: DivingFishBest50Response = await self._post_resp(endpoint, auth_token=access_token)

        standard_scores = []
        dx_scores = []

        for raw_score in data["charts"]["sd"]:
            score = self._score_unpack(raw_score)
            standard_scores.append(score)

        for raw_score in data["charts"]["dx"]:
            score = self._score_unpack(raw_score)
            dx_scores.append(score)

        b50 = PlayerMaiB50(standard=standard_scores, dx=dx_scores)
        return b50

    async def fetch_player_records(self, params: DivingFishParams) -> DivingFishPlayerRecordsResponse:
        """
        获取玩家完整游玩记录
        """
        endpoint = "player/records"
        access_token = await self.access_token(params.user_id)

        data: DivingFishPlayerRecordsResponse = await self._get_resp(endpoint, auth_token=access_token)

        return data

    async def fetch_player_ap50(self, params: DivingFishParams) -> PlayerMaiB50:
        """
        获取玩家 AP 50
        """
        _CURRENT_VERSION = list(MAI_VERSION_MAP.keys())[-1]

        logger.debug("通过水鱼查分器间接查询 AP 50...")
        logger.debug("1/2 获取完整游玩记录")

        datas = await self.fetch_player_records(params)
        records = datas["records"]
        ap_records = [record for record in records if record["fc"] in ["ap", "app"]]

        logger.debug("2/2 划分版本信息")

        session = get_scoped_session()
        old_version_records = []
        current_vesion_records = []

        for record in ap_records:
            song_id = record["song_id"] if record["type"].lower() != "dx" else record["song_id"] - 10000
            song = await MaiSongORM.get_song_info(session, song_id)
            is_current_version = song.version // 100 == _CURRENT_VERSION

            if is_current_version:
                current_vesion_records.append(record)
            else:
                old_version_records.append(record)

        old_version_records.sort(key=lambda x: x["ra"], reverse=True)
        current_vesion_records.sort(key=lambda x: x["ra"], reverse=True)

        standard_scores = [self._score_unpack(record) for record in old_version_records[:35]]
        dx_scores = [self._score_unpack(record) for record in current_vesion_records[:15]]

        ap50 = PlayerMaiB50(standard=standard_scores, dx=dx_scores)
        return ap50

    @staticmethod
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

    async def convert_to_diving_fish_format(
        self,
        scores: list[dict[str, Any]],
    ) -> list[DivingFishRecord]:
        """将 UserMusicDetail 列表转换为水鱼查分器格式"""
        df_list = []
        send_warning_message = False
        updated = False
        for score in scores:
            music_id = score["musicId"]

            # 跳过很多万以上的 ID (通常是宴谱或其他特殊谱面)
            if music_id >= 100000 or music_id == 11407:
                continue

            title = self._get_song_title(music_id)

            if not title and not updated:
                db_session = get_scoped_session()
                logger.debug("发现未跟踪的曲目，自动进行同步中...")
                count = await update_maimai_song_database(db_session)
                logger.info(f"自动更新了 {count} 条曲目")
                updated = True
                title = self._get_song_title(music_id)

            if not title:
                logger.warning(f"未知曲目 ID: {music_id}, 已跳过")
                if not send_warning_message:
                    await UniMessage(
                        f"导入过程中发现了未知曲目: {music_id} 等，部分成绩可能丢失请联系管理员更新数据库"
                    ).send()
                    send_warning_message = True
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

    async def upload_to_diving_fish(self, params: DivingFishParams, payload: list[DivingFishRecord]) -> None:
        """上传成绩到水鱼查分器"""
        logger.info(f"准备上传 {len(payload)} 条记录到水鱼查分器...")
        access_token = await self.access_token(params.user_id)

        try:
            await self._post_resp(
                "/player/update_records",
                params=payload,
                auth_token=access_token,
            )

            logger.info("水鱼查分器上传成功！")

        except httpx.RequestError as e:
            logger.error(f"水鱼查分器连接失败: {e}")
            raise
