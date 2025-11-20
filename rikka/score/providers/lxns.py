from dataclasses import fields
from typing import Any, Optional, TypedDict

from ...config import config
from .._base import BaseScoreProvider
from .._schema import (
    PlayerMaiB50,
    PlayerMaiCollection,
    PlayerMaiInfo,
    PlayerMaiScore,
    PlayerMaiTrophy,
    ScoreFCType,
    ScoreFSType,
    ScoreRateType,
    SongDifficulty,
    SongType,
    TrophyColor,
)

_developer_api_key = config.lxns_developer_api_key


class LXNSBest50Response(TypedDict):
    standard_total: int
    dx_total: int
    standard: list[dict]
    dx: list[dict]


class LXNSScoreProvider(BaseScoreProvider):
    provider = "lxns"
    base_url = "https://maimai.lxns.net/api/v0/maimai/player"
    user_base_url = "https://maimai.lxns.net/api/v0/user/maimai/player"

    async def _get_resp_by_user_token(self, endpoint: str, user_token: str) -> Any:
        """
        发起 GET 请求，自动拼接 URL 并附带 Authorization。
        """
        session = await self._get_session()
        headers = {"X-User-Token": user_token} if user_token else {}
        url = f"{self.user_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    @staticmethod
    def _score_unpack(raw_score: dict) -> PlayerMaiScore:
        raw_score["song_difficulty"] = SongDifficulty(raw_score["level_index"])
        raw_score["fc"] = ScoreFCType(raw_score["fc"]) if raw_score.get("fc") else None
        raw_score["fs"] = ScoreFSType(raw_score["fs"]) if raw_score.get("fs") else None
        raw_score["rate"] = ScoreRateType(raw_score["rate"])
        raw_score["type"] = SongType(raw_score["type"])

        valid_keys = {f.name for f in fields(PlayerMaiScore)}
        filtered = {k: v for k, v in raw_score.items() if k in valid_keys}
        filtered["song_id"] = raw_score["id"]
        filtered["song_type"] = raw_score["type"]
        filtered["song_level"] = raw_score["level"]

        return PlayerMaiScore(**filtered)

    @staticmethod
    def _info_unpack(raw_info: dict) -> PlayerMaiInfo:
        unpacked_info = raw_info.copy()

        trophy = raw_info.get("trophy")
        icon = raw_info.get("icon")
        name_plate = raw_info.get("name_plate")
        frame = raw_info.get("frame")

        if trophy:
            unpacked_info["trophy"]["color"] = TrophyColor(raw_info["trophy"]["color"])
            unpacked_info["trophy"] = PlayerMaiTrophy(**unpacked_info["trophy"])
        if icon:
            unpacked_info["icon"] = PlayerMaiCollection(**raw_info["icon"])
        if name_plate:
            unpacked_info["name_plate"] = PlayerMaiCollection(**raw_info["name_plate"])
        if frame:
            unpacked_info["frame"] = PlayerMaiCollection(**raw_info["frame"])

        valid_keys = {f.name for f in fields(PlayerMaiInfo)}
        filtered = {k: v for k, v in unpacked_info.items() if k in valid_keys}

        return PlayerMaiInfo(**filtered)

    async def fetch_player_info(
        self,
        friend_code: Optional[str] = None,
        username: Optional[str] = None,
        qq: Optional[str] = None,
        auth_token: Optional[str] = _developer_api_key,
    ) -> PlayerMaiInfo:
        assert auth_token, "落雪查分器必须使用 developer_token 鉴权"
        if friend_code:
            endpoint = friend_code
        elif qq:
            endpoint = f"qq/{qq}"
        elif username:
            # LXNS 不支持 username 直接查, 给出明确异常
            raise ValueError("LXNSScoreProvider 不支持通过 username 查询玩家信息")
        else:
            raise ValueError("必须提供 friend_code 或 qq")

        data = await self._get_resp(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_info_by_user_token(self, auth_token: str) -> PlayerMaiInfo:
        endpoint = ""

        data = await self._get_resp_by_user_token(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_info_by_qq(self, qq: str, auth_token: Optional[str] = _developer_api_key) -> PlayerMaiInfo:
        endpoint = f"qq/{qq}"

        data = await self._get_resp(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_b50(
        self,
        friend_code: Optional[str] = None,
        username: Optional[str] = None,
        qq: Optional[str] = None,
        auth_token: Optional[str] = _developer_api_key,
    ) -> PlayerMaiB50:
        assert auth_token, "落雪查分器必须使用 developer_token 鉴权"
        if friend_code:
            endpoint = f"{friend_code}/bests"
        elif qq:
            # 先查 info 拿 friend_code 再取 best
            info = await self.fetch_player_info(qq=qq, auth_token=auth_token)
            endpoint = f"{info.friend_code}/bests"  # type: ignore
        elif username:
            raise ValueError("LXNSScoreProvider 不支持通过 username 查询 Best50")
        else:
            raise ValueError("必须提供 friend_code 或 qq 用于查询 Best50")

        response = await self._get_resp(endpoint, auth_token)
        data: LXNSBest50Response = response.get("data", response)

        standard_scores = []
        dx_scores = []

        for raw_score in data["standard"]:
            score = self._score_unpack(raw_score)
            standard_scores.append(score)

        for raw_score in data["dx"]:
            score = self._score_unpack(raw_score)
            dx_scores.append(score)

        b50 = PlayerMaiB50(
            standard=standard_scores,
            dx=dx_scores,
        )
        return b50

    async def fetch_player_b50_by_qq(self, qq: str, auth_token: Optional[str] = _developer_api_key) -> PlayerMaiB50:
        # 保持兼容旧调用路径
        return await self.fetch_player_b50(qq=qq, auth_token=auth_token)

    async def fetch_player_ap50(self, friend_code: str, auth_token: str = _developer_api_key) -> PlayerMaiB50:
        """
        获取玩家 ALL PERFECT 50
        """
        endpoint = f"{friend_code}/bests/ap"

        response = await self._get_resp(endpoint, auth_token)
        data: LXNSBest50Response = response.get("data", response)

        standard_scores = []
        dx_scores = []

        for raw_score in data["standard"]:
            score = self._score_unpack(raw_score)
            standard_scores.append(score)

        for raw_score in data["dx"]:
            score = self._score_unpack(raw_score)
            dx_scores.append(score)

        ap50 = PlayerMaiB50(
            standard=standard_scores,
            dx=dx_scores,
        )
        return ap50

    async def fetch_player_r50(self, friend_code: str, auth_token: str = _developer_api_key) -> list[PlayerMaiScore]:
        """
        获取玩家 Recent 50
        """
        endpoint = f"{friend_code}/recents"

        response = await self._get_resp(endpoint, auth_token)
        data: list[dict] = response.get("data", response)

        scores = []

        for raw_score in data:
            score = self._score_unpack(raw_score)
            scores.append(score)

        return scores
