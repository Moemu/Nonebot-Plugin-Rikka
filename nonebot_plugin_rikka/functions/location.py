"""店铺分布查询模块

提供舞萌 (maimai) 和中二节奏 (CHUNITHM) 的店铺查询功能。
数据来源于华立科技世嘉注册接口，带 12 小时 TTL 缓存。
支持店铺变动订阅：当缓存刷新时检测新增/移除店铺，并主动通知匹配关键词的订阅者。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal, Optional

import aiohttp
from nonebot import get_bot, logger
from nonebot_plugin_alconna.uniseg import Target, UniMessage
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import get_scoped_session

from ..database.crud import LocationSubscriptionORM
from ..database.orm_models import LocationSubscription

# API endpoints
_MAI_LOCATION_URL = "https://sega-register.wahlap.net/api/sega/maidx/rest/location"
_CHU_LOCATION_URL = "https://sega-register.wahlap.net/api/sega/midtr/rest/location"

# TTL: 12 hours in seconds
_CACHE_TTL = 12 * 60 * 60

# 每条消息之间的延迟（秒），避免风控
_DELAYED_SECOND_PER_PARAGRAPH = 0.5


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


@dataclass
class LocationDiff:
    """店铺变动差异"""

    added: list[ArcadeLocation] = field(default_factory=list)
    """新增的店铺"""
    removed: list[ArcadeLocation] = field(default_factory=list)
    """移除的店铺"""

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)


class LocationCache:
    """带 TTL 的店铺数据缓存，支持差异检测和订阅通知"""

    def __init__(self, game_type: str, url: str) -> None:
        self._game_type = game_type
        """游戏类型: 'mai' 或 'chu'"""
        self._url = url
        self._locations: list[ArcadeLocation] = []
        self._last_update: float = 0.0
        self._previous_place_ids: set[str] = set()
        """上一次缓存的 placeId 集合，用于差异检测"""

    @property
    def is_expired(self) -> bool:
        return time.time() - self._last_update > _CACHE_TTL

    async def _fetch(self) -> list[ArcadeLocation]:
        """从远程接口拉取店铺数据"""
        logger.debug(f"[Location] 正在从 {self._url} 拉取店铺数据...")
        async with aiohttp.ClientSession() as session:
            async with session.get(self._url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
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

        return locations

    def _compute_diff(self, new_locations: list[ArcadeLocation]) -> LocationDiff:
        """计算新旧数据之间的差异"""
        old_place_ids = self._previous_place_ids
        new_place_ids = {loc.place_id for loc in new_locations}

        added_ids = new_place_ids - old_place_ids
        removed_ids = old_place_ids - new_place_ids

        added = [loc for loc in new_locations if loc.place_id in added_ids]
        removed = [loc for loc in self._locations if loc.place_id in removed_ids]

        return LocationDiff(added=added, removed=removed)

    async def sync(self) -> Optional[LocationDiff]:
        """同步店铺列表"""
        locations = await self._fetch()

        # 检测差异并通知订阅者
        diff = None
        if self._previous_place_ids:
            diff = self._compute_diff(locations)
            if diff.has_changes:
                logger.info(
                    f"[Location][{self._game_type}] 检测到店铺变动: "
                    f"新增 {len(diff.added)} 家, 移除 {len(diff.removed)} 家"
                )
                await self._notify_subscribers(diff)

        # 更新缓存
        self._locations = locations
        self._previous_place_ids = {loc.place_id for loc in locations}
        self._last_update = time.time()
        logger.debug(f"[Location] 拉取完成，共 {len(self._locations)} 家店铺")

        return diff

    async def get_locations(self) -> list[ArcadeLocation]:
        """获取店铺列表，如果缓存过期则重新拉取"""
        if self.is_expired or not self._locations:
            await self.sync()
        return self._locations

    async def _notify_subscribers(self, diff: LocationDiff) -> None:
        """通知所有匹配关键词的订阅者"""

        session = get_scoped_session()
        subscriptions: list[LocationSubscription] = await LocationSubscriptionORM.get_all_subscriptions(
            session, self._game_type
        )

        if not subscriptions:
            return

        game_name = "舞萌" if self._game_type == "mai" else "中二"

        for sub in subscriptions:
            keyword = sub.keyword
            matched_added = [loc for loc in diff.added if keyword in loc.arcade_name or keyword in loc.address]
            matched_removed = [loc for loc in diff.removed if keyword in loc.arcade_name or keyword in loc.address]

            if not matched_added and not matched_removed:
                continue

            # 构造通知消息
            parts = [f"📍 [{game_name}店铺变动提醒] 关键词: {keyword}"]
            if matched_added:
                parts.append(f"\n🆕 新增 ({len(matched_added)} 家):")
                for i, loc in enumerate(matched_added, 1):
                    parts.append(f"  {i}. {loc.arcade_name}({loc.place_id})\n     地址: {loc.address}")
            if matched_removed:
                parts.append(f"\n❌ 移除 ({len(matched_removed)} 家):")
                for i, loc in enumerate(matched_removed, 1):
                    parts.append(f"  {i}. {loc.arcade_name}({loc.place_id})")

            message = "\n".join(parts)

            try:
                await self._send_message(sub.user_id, sub.group_id, message)
                logger.debug(f"[Location] 已通知用户 {sub.user_id} (关键词: {keyword})")
            except Exception as e:
                logger.warning(f"[Location] 通知用户 {sub.user_id} 失败: {e}")

    @staticmethod
    async def _send_message(user_id: str, group_id: Optional[str], message: str) -> None:
        """发送消息给用户

        如果有 group_id 则向群组发送，否则私聊发送。
        """
        if group_id:
            target = Target(group_id, private=False)
        else:
            target = Target(user_id, private=True)

        messages = LocationCache._split_message(message)
        bot = get_bot()
        for msg in messages:
            await UniMessage(msg).send(target=target, bot=bot)
            await asyncio.sleep(_DELAYED_SECOND_PER_PARAGRAPH)

    @staticmethod
    def _split_message(message: str, max_length: int = 4000) -> list[str]:
        """将长消息拆分为多段，避免超出平台消息长度限制"""
        if len(message) <= max_length:
            return [message]

        parts: list[str] = []
        current = ""
        for line in message.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                if current:
                    parts.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            parts.append(current)
        return parts

    def clear(self) -> None:
        self._locations.clear()
        self._previous_place_ids.clear()
        self._last_update = 0.0


# 全局缓存实例
_mai_cache = LocationCache("mai", _MAI_LOCATION_URL)
_chu_cache = LocationCache("chu", _CHU_LOCATION_URL)


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
    return await _mai_cache.get_locations()


async def get_chu_locations() -> list[ArcadeLocation]:
    """获取中二节奏店铺列表"""
    return await _chu_cache.get_locations()


async def location_sync(target: Optional[Literal["mai", "chu"]] = None) -> Optional[LocationDiff]:
    """同步店铺列表"""
    if target == "mai":
        diff = await _mai_cache.sync()
    elif target == "chu":
        diff = await _chu_cache.sync()
    else:
        diff = LocationDiff()
        mai_diff = await _mai_cache.sync()
        chu_diff = await _chu_cache.sync()
        if mai_diff:
            diff.added += mai_diff.added
            diff.removed += mai_diff.removed
        if chu_diff:
            diff.added += chu_diff.added
            diff.removed += chu_diff.removed
    return diff


@scheduler.scheduled_job("cron", hour="*/6", id="sync_locations")
async def run_every_2_hour():
    """每 6 小时同步一次店铺列表"""
    try:
        await location_sync()
        logger.info("[Location] 定时同步店铺列表完成")
    except Exception as e:
        logger.error(f"[Location] 定时同步店铺列表失败: {e}")
