"""店铺分布查询模块

提供舞萌 (maimai) 和中二节奏 (CHUNITHM) 的店铺查询功能。
数据来源于华立科技世嘉注册接口，带 12 小时 TTL 缓存。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import aiohttp
from nonebot import logger

# API endpoints
_MAI_LOCATION_URL = "https://sega-register.wahlap.net/api/sega/maidx/rest/location"
_CHU_LOCATION_URL = "https://sega-register.wahlap.net/api/sega/midtr/rest/location"

# TTL: 12 hours in seconds
_CACHE_TTL = 12 * 60 * 60


@dataclass
class ArcadeLocation:
    """单个店铺信息"""

    arcade_name: str
    """店铺名称"""
    address: str
    """地址"""
    place_id: str
    """场所 ID"""

    def format(self, index: int) -> str:
        """格式化为用户可见的文本"""
        return f"{index}. {self.arcade_name}({self.place_id})\n地址: {self.address}"


class LocationCache:
    """带 TTL 的店铺数据缓存"""

    def __init__(self) -> None:
        self._locations: list[ArcadeLocation] = []
        self._last_update: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self._last_update > _CACHE_TTL

    async def get_locations(self, url: str) -> list[ArcadeLocation]:
        """获取店铺列表，如果缓存过期则重新拉取"""
        if self.is_expired or not self._locations:
            await self._fetch(url)
        return self._locations

    async def _fetch(self, url: str) -> None:
        """从远程接口拉取店铺数据"""
        logger.debug(f"[Location] 正在从 {url} 拉取店铺数据...")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        locations: list[ArcadeLocation] = []
        for item in data:
            locations.append(
                ArcadeLocation(
                    arcade_name=item.get("arcadeName", "未知店铺"),
                    address=item.get("address", "未知地址"),
                    place_id=str(item.get("placeId", "")),
                )
            )

        # API 已按添加时间逆序排列，保持原序
        self._locations = locations
        self._last_update = time.time()
        logger.debug(f"[Location] 拉取完成，共 {len(self._locations)} 家店铺")

    def clear(self) -> None:
        self._locations.clear()
        self._last_update = 0.0


# 全局缓存实例
_mai_cache = LocationCache()
_chu_cache = LocationCache()


def list_locations(
    locations: list[ArcadeLocation],
    *,
    num: int = 5,
) -> str:
    """列出前 num 家店铺"""
    if not locations:
        return "暂无店铺数据"

    num = min(num, len(locations))
    lines = [locations[i].format(i + 1) for i in range(num)]

    result = "\n".join(lines)
    total = len(locations)
    if num < total:
        result += f"\n\n共 {total} 家店铺（显示前 {num} 家）"
    else:
        result += f"\n\n共 {total} 家店铺"

    return result


def search_locations(
    locations: list[ArcadeLocation],
    *,
    keyword: str,
    max_results: int = 20,
) -> str:
    """搜索包含关键词的店铺"""
    if not keyword:
        return "请输入搜索关键词"

    matched = [loc for loc in locations if keyword in loc.arcade_name or keyword in loc.address]

    if not matched:
        return f'未找到与 "{keyword}" 相关的店铺'

    display = matched[:max_results]
    lines = [display[i].format(i + 1) for i in range(len(display))]

    title = f"共找到 {len(matched)} 家店铺" + (f"（仅显示前 {max_results} 家）" if len(matched) > max_results else "")
    result = f"{title}: \n" + "\n".join(lines)

    return result


async def get_mai_locations() -> list[ArcadeLocation]:
    """获取舞萌店铺列表"""
    return await _mai_cache.get_locations(_MAI_LOCATION_URL)


async def get_chu_locations() -> list[ArcadeLocation]:
    """获取中二节奏店铺列表"""
    return await _chu_cache.get_locations(_CHU_LOCATION_URL)
