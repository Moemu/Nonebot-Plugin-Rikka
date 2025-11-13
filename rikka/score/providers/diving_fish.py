from dataclasses import fields
from typing import Optional, TypedDict

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
    records: DivingFishCharts
    nickname: str
    """用户的昵称"""
    plate: str
    """用户的牌子信息"""
    rating: int
    username: str
    """水鱼用户名"""


class DivingFishScoreProvider(BaseScoreProvider):
    provider = "diving-fish"
    base_url = "https://www.diving-fish.com/api/maimaidxprober/"

    def _build_headers(self, auth_token: Optional[str]) -> dict:
        # diving-fish 使用 Import-Token 作为鉴权头
        return {"Import-Token": auth_token} if auth_token else {}

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

    async def fetch_player_info(
        self,
        friend_code: Optional[str] = None,
        username: Optional[str] = None,
        qq: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> PlayerMaiInfo:
        """
        通过 QQ 获取玩家信息(水鱼不支持获取收藏品信息)
        """
        if username:
            endpoint = "query/player"
            params = {"username": username, "b50": 1}
        elif qq:
            endpoint = "query/player"
            params = {"qq": qq, "b50": 1}
        elif friend_code:
            # diving-fish 不支持 friend_code 直接查询
            raise ValueError("DivingFishScoreProvider 不支持通过 friend_code 查询玩家信息")
        else:
            raise ValueError("必须提供 username 或 qq")

        data: DivingFishBest50Response = await self._post_resp(endpoint, params)
        return PlayerMaiInfo(data["nickname"], data["rating"], 0, 0)

    async def fetch_player_info_by_qq(self, qq: str, auth_token: Optional[str] = None) -> PlayerMaiInfo:
        """
        通过 QQ 获取玩家信息(水鱼不支持获取收藏品信息)
        """
        endpoint = "query/player"
        params = {"qq": qq, "b50": 1}

        data: DivingFishBest50Response = await self._post_resp(endpoint, params)

        return PlayerMaiInfo(data["nickname"], data["rating"], 0, 0)

    async def fetch_player_b50(
        self,
        friend_code: Optional[str] = None,
        username: Optional[str] = None,
        qq: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> PlayerMaiB50:
        """
        获得玩家 Best50 信息
        """
        if username:
            endpoint = "query/player"
            params = {"username": username, "b50": 1}
        elif qq:
            endpoint = "query/player"
            params = {"qq": qq, "b50": 1}
        elif friend_code:
            raise ValueError("DivingFishScoreProvider 不支持通过 friend_code 查询 Best50")
        else:
            raise ValueError("必须提供 username 或 qq 用于查询 Best50")

        data: DivingFishBest50Response = await self._post_resp(endpoint, params)

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

    async def fetch_player_b50_by_qq(self, qq: str, auth_token: Optional[str] = None) -> PlayerMaiB50:
        # 兼容旧 API：委托到统一签名
        return await self.fetch_player_b50(qq=qq, auth_token=auth_token)

    async def fetch_player_records_by_import_token(self, import_token: str) -> DivingFishPlayerRecordsResponse:
        """
        通过 import-token 获取玩家游玩记录
        """
        endpoint = "player/records"

        data: DivingFishPlayerRecordsResponse = await self._get_resp(endpoint, import_token)

        return data
