from abc import ABC, abstractmethod
from typing import Any, Optional

from aiohttp import ClientSession

from ._schema import PlayerMaiB50, PlayerMaiInfo


class BaseScoreProvider(ABC):
    base_url: str
    """查分器的 API 接口"""
    _initialized: bool
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._session: Optional[ClientSession] = None
        self._initialized = True

    async def _get_session(self) -> ClientSession:
        """获取或创建共享的 aiohttp 会话"""
        if self._session is None or self._session.closed:
            self._session = ClientSession()
        return self._session

    async def _get_resp(self, endpoint: str, auth_token: str) -> Any:
        """
        发起 GET 请求，自动拼接 URL 并附带 Authorization。
        """
        session = await self._get_session()
        headers = {"Authorization": auth_token} if auth_token else {}
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _post_resp(self, endpoint: str, auth_token: str, params: dict) -> Any:
        """
        发起 POST 请求，自动拼接 URL 并附带 Authorization。
        """
        session = await self._get_session()
        headers = {"Authorization": auth_token} if auth_token else {}
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        async with session.post(url, headers=headers, json=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self):
        """手动关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def fetch_player_info(self, friend_code: str, auth_token: str) -> PlayerMaiInfo:
        """
        获得玩家游玩信息
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_player_b50(self, friend_code: str, auth_token: str) -> PlayerMaiB50:
        """
        获得玩家 Best50 信息
        """
        raise NotImplementedError
