from dataclasses import fields
from typing import Any, TypedDict

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


class LXNSBest50Response(TypedDict):
    standard_total: int
    dx_total: int
    standard: list[dict]
    dx: list[dict]


class LXNSScoreProvider(BaseScoreProvider):
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

    async def fetch_player_info(self, friend_code: str, auth_token: str) -> PlayerMaiInfo:
        endpoint = friend_code

        data = await self._get_resp(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_info_by_user_token(self, auth_token: str) -> PlayerMaiInfo:
        endpoint = ""

        data = await self._get_resp_by_user_token(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_info_by_qq(self, qq: str, auth_token: str) -> PlayerMaiInfo:
        endpoint = f"qq/{qq}"

        data = await self._get_resp(endpoint, auth_token)
        player_info = self._info_unpack(data["data"])
        return player_info

    async def fetch_player_b50(self, friend_code: str, auth_token: str) -> PlayerMaiB50:
        endpoint = f"{friend_code}/bests"

        response = await self._get_resp(endpoint, auth_token)
        data: LXNSBest50Response = response["data"]

        standard_scores = []
        dx_scores = []

        for raw_score in data["standard"]:
            score = self._score_unpack(raw_score)
            standard_scores.append(score)

        for raw_score in data["dx"]:
            score = self._score_unpack(raw_score)
            dx_scores.append(score)

        b50 = PlayerMaiB50(data["standard_total"], data["dx_total"], standard_scores, dx_scores)
        return b50
