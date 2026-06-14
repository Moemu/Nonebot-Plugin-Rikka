"""落雪咖啡屋 (LXNS) 中二节奏查分器实现

基于 LXNS 的中二节奏 (CHUNITHM) API。
API 文档: https://maimai.lxns.net/api/doc
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Optional, TypedDict

from async_lru import alru_cache
from nonebot import logger

from ....config import config
from .._schema import (
    ChuClearType,
    ChuDifficulty,
    ChuFullChainType,
    ChuFullComboType,
    ChuRankType,
    ChuRatingTrend,
    ChuTrophy,
    PlayerChuBests,
    PlayerChuInfo,
    PlayerChuScore,
)


class LXNSChuBestsResponse(TypedDict):
    bests: list[dict]
    selections: list[dict]
    new_bests: list[dict]


class LXNSChuRatingTrend(TypedDict):
    rating: float
    bests_rating: float
    selections_rating: float
    recents_rating: float | None
    new_bests_rating: float | None
    date: str


@dataclass
class LXNSChuParams:
    """中二节奏 LXNS 查分器参数"""

    friend_code: Optional[int] = None
    qq: Optional[str] = None
    user_key: Optional[str] = None


class LXNSChuScoreProvider:
    """落雪咖啡屋 中二节奏 查分器"""

    provider = "lxns"
    base_url = "https://maimai.lxns.net/api/v0/chunithm/player"
    user_base_url = "https://maimai.lxns.net/api/v0/user/chunithm/player"
    _developer_api_key = config.lxns_developer_api_key

    ParamsType = LXNSChuParams

    def __init__(self) -> None:
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            from aiohttp import ClientSession, ClientTimeout

            self._session = ClientSession(timeout=ClientTimeout(total=60))
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_resp(self, endpoint: str, auth_token: Optional[str] = None) -> Any:
        """发起 GET 请求，自动拼接 URL 并附带鉴权。"""
        from aiohttp import ClientResponseError

        session = await self._get_session()
        headers = {"Authorization": auth_token} if auth_token else {}
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as e:
            if e.status in (401, 403):
                raise PermissionError(f"鉴权失败: {e.status} {url}") from e
            if e.status == 404:
                raise LookupError(f"未找到资源: {url}") from e
            if e.status == 429:
                raise RuntimeError("请求过于频繁(429): 请稍后重试") from e
            raise

    async def _get_resp_by_user_token(self, endpoint: str, user_token: str) -> Any:
        """通过个人 API 发起 GET 请求。"""
        from aiohttp import ClientResponseError

        session = await self._get_session()
        headers = {"X-User-Token": user_token} if user_token else {}
        url = f"{self.user_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
        except ClientResponseError as e:
            if e.status in (401, 403):
                raise PermissionError(f"鉴权失败: {e.status} {url}") from e
            if e.status == 404:
                raise LookupError(f"未找到资源: {url}") from e
            if e.status == 429:
                raise RuntimeError("请求过于频繁(429): 请稍后重试") from e
            raise

    @staticmethod
    def _score_unpack(raw_score: dict) -> PlayerChuScore:
        """将 API 返回的原始成绩数据解包为 PlayerChuScore。"""
        raw_score = raw_score.copy()

        raw_score["song_difficulty"] = ChuDifficulty(raw_score["level_index"])
        raw_score["clear"] = ChuClearType(raw_score["clear"]) if raw_score.get("clear") else None
        raw_score["full_combo"] = ChuFullComboType(raw_score["full_combo"]) if raw_score.get("full_combo") else None
        raw_score["full_chain"] = ChuFullChainType(raw_score["full_chain"]) if raw_score.get("full_chain") else None
        raw_score["rank"] = ChuRankType(raw_score["rank"]) if raw_score.get("rank") else None

        # API 返回 id/level，schema 字段为 song_id/song_level
        raw_score["song_id"] = raw_score.get("id")
        raw_score["song_name"] = raw_score.get("song_name", raw_score.get("title", ""))
        raw_score["song_level"] = raw_score.get("level", "")

        valid_keys = {f.name for f in fields(PlayerChuScore)}
        filtered = {k: v for k, v in raw_score.items() if k in valid_keys}

        return PlayerChuScore(**filtered)

    @staticmethod
    def _info_unpack(raw_info: dict) -> PlayerChuInfo:
        """将 API 返回的原始玩家信息解包为 PlayerChuInfo。

        :param raw_info: 玩家信息原始数据
        :param trophy_detail: 称号详情（可选），来自 fetch_trophy 的结果
        """
        class_emblem = raw_info.get("class_emblem", {})

        trophy = raw_info.get("trophy")
        character = raw_info.get("character")
        name_plate = raw_info.get("name_plate")
        map_icon = raw_info.get("map_icon")

        # 构建 ChuTrophy 对象
        chu_trophy = None
        if trophy:
            trophy_info = raw_info["trophy"]
            chu_trophy = ChuTrophy(
                id=trophy_info["id"],
                name=trophy_info.get("name", ""),
                color=trophy_info.get("color", "normal"),
            )

        return PlayerChuInfo(
            name=raw_info["name"],
            rating=raw_info["rating"],
            friend_code=raw_info["friend_code"],
            level=raw_info.get("level", 0),
            class_emblem_base=class_emblem.get("base", 0),
            class_emblem_medal=class_emblem.get("medal", 0),
            over_power=raw_info.get("over_power", 0.0),
            over_power_progress=raw_info.get("over_power_progress", 0.0),
            total_play_count=raw_info.get("total_play_count", 0),
            trophy_id=trophy.get("id") if trophy else None,
            trophy=chu_trophy,
            character_id=character.get("id") if character else None,
            name_plate_id=name_plate.get("id") if name_plate else None,
            map_icon_id=map_icon.get("id") if map_icon else None,
            upload_time=raw_info.get("upload_time"),
        )

    async def _get_trophy(self, raw_info: dict) -> Optional[dict]:
        # 称号详情
        trophy_detail = None
        if raw_info.get("trophy", {}).get("id"):
            trophy_id = raw_info["trophy"]["id"]
            try:
                trophy_detail = await self.fetch_trophy(trophy_id)
            except Exception as e:
                logger.warning(f"获取称号详情失败: {e}")

        return trophy_detail

    async def _get_friend_code(self, params: LXNSChuParams) -> int:
        """
        自动推断好友码。

        :raise ValueError: 用户未绑定落雪查分器
        """
        if params.friend_code:
            return params.friend_code
        if params.qq:
            info = await self.fetch_player_info(LXNSChuParams(qq=params.qq))
            return info.friend_code

        raise ValueError("无法自动获取 friend_code，请先绑定落雪查分器")

    @alru_cache(1024)
    async def fetch_trophy(self, trophy_id: int) -> dict:
        """
        获取称号详情。
        """
        url = f"https://maimai.lxns.net/api/v0/chunithm/trophy/{trophy_id}"
        session = await self._get_session()
        headers = {"Authorization": self._developer_api_key} if self._developer_api_key else {}
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", {})

    async def fetch_player_info(self, params: LXNSChuParams) -> PlayerChuInfo:
        """获取玩家信息。

        :param params: 查询参数
        """
        if params.friend_code:
            endpoint = str(params.friend_code)
        elif params.qq:
            endpoint = f"qq/{params.qq}"
        else:
            raise ValueError("必须提供 friend_code 或 qq")

        data = await self._get_resp(endpoint, self._developer_api_key)
        raw_info = data["data"]
        return self._info_unpack(raw_info)

    async def fetch_player_info_by_user_token(self, auth_token: str) -> PlayerChuInfo:
        """通过个人 API 获取玩家信息。"""
        data = await self._get_resp_by_user_token("", auth_token)
        return self._info_unpack(data["data"])

    @alru_cache(256, ttl=60)
    async def fetch_player_info_by_qq(self, qq: str) -> PlayerChuInfo:
        """通过 QQ 号获取玩家信息。"""
        data = await self._get_resp(f"qq/{qq}", self._developer_api_key)
        return self._info_unpack(data["data"])

    async def fetch_player_bests(self, params: LXNSChuParams) -> PlayerChuBests:
        """获取玩家 Rating 构成（Best 30 + Selection 10 + New 20）。"""
        friend_code = await self._get_friend_code(params)
        endpoint = f"{friend_code}/bests"

        response = await self._get_resp(endpoint, self._developer_api_key)
        data: LXNSChuBestsResponse = response.get("data", response)

        bests = [self._score_unpack(s) for s in data.get("bests", [])]
        selections = [self._score_unpack(s) for s in data.get("selections", [])]
        new_bests = [self._score_unpack(s) for s in data.get("new_bests", [])]

        return PlayerChuBests(bests=bests, selections=selections, new_bests=new_bests)

    async def fetch_player_recents(self, params: LXNSChuParams) -> list[PlayerChuScore]:
        """获取玩家 Recent 50。"""
        friend_code = await self._get_friend_code(params)
        endpoint = f"{friend_code}/recents"

        response = await self._get_resp(endpoint, self._developer_api_key)
        data: list[dict] = response.get("data", response)

        return [self._score_unpack(s) for s in data]

    async def fetch_player_scores(self, params: LXNSChuParams, use_user_api: bool = True) -> list[PlayerChuScore]:
        """
        获取玩家成绩列表

        :param use_user_api: 通过 LXNS 开发者接口无法获取完整的游玩信息，启用此标志以强制使用 user_api，需要用户绑定落雪查分器

        :raise ValueError: 用户未绑定落雪查分器
        """
        if use_user_api:
            if not params.user_key:
                raise ValueError("此功能需要获取完整的成绩列表，需要绑定落雪查分器才可使用此指令")
            response = await self._get_resp_by_user_token("scores", params.user_key)
        else:
            friend_code = await self._get_friend_code(params)
            endpoint = f"{friend_code}/scores"
            response = await self._get_resp(endpoint, self._developer_api_key)

        data: list[dict] = response.get("data", response)

        return [self._score_unpack(s) for s in data]

    async def fetch_player_trend(self, params: LXNSChuParams, version: Optional[int] = None) -> list[ChuRatingTrend]:
        """获取玩家 Rating 趋势。"""
        friend_code = await self._get_friend_code(params)
        endpoint = f"{friend_code}/trend"

        query_params = {}
        if version is not None:
            query_params["version"] = version

        # 简单拼接查询参数
        if query_params:
            query_str = "&".join(f"{k}={v}" for k, v in query_params.items())
            endpoint = f"{endpoint}?{query_str}"

        response = await self._get_resp(endpoint, self._developer_api_key)
        data: list[LXNSChuRatingTrend] = response.get("data", response)

        trends = []
        for item in data:
            trends.append(
                ChuRatingTrend(
                    rating=item["rating"],
                    bests_rating=item["bests_rating"],
                    selections_rating=item["selections_rating"],
                    recents_rating=item.get("recents_rating"),
                    new_bests_rating=item.get("new_bests_rating"),
                    date=item.get("date"),
                )
            )

        return trends

    async def fetch_song_list(self) -> list[dict]:
        """获取中二节奏曲目列表。"""
        url = "https://maimai.lxns.net/api/v0/chunithm/song/list"
        session = await self._get_session()
        headers = {"Authorization": self._developer_api_key} if self._developer_api_key else {}
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", {}).get("songs", [])

    async def fetch_song_info(self, song_id: int) -> dict:
        """获取单首曲目信息。"""
        url = f"https://maimai.lxns.net/api/v0/chunithm/song/{song_id}"
        session = await self._get_session()
        headers = {"Authorization": self._developer_api_key} if self._developer_api_key else {}
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", {})

    async def fetch_player_best_score(
        self, params: LXNSChuParams, song_id: Optional[int] = None, song_name: Optional[str] = None
    ) -> Optional[PlayerChuScore]:
        """获取玩家单曲最佳成绩。"""
        friend_code = await self._get_friend_code(params)
        endpoint = f"{friend_code}/best"
        query_parts = []
        if song_id is not None:
            query_parts.append(f"song_id={song_id}")
        if song_name is not None:
            from urllib.parse import quote

            query_parts.append(f"song_name={quote(song_name)}")
        if query_parts:
            endpoint = f"{endpoint}?{'&'.join(query_parts)}"

        try:
            response = await self._get_resp(endpoint, self._developer_api_key)
        except LookupError:
            return None
        data = response.get("data", response)
        if not data:
            return None
        return self._score_unpack(data)
