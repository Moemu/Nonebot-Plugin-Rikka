"""中二节奏 (CHUNITHM) Score providers registry and NoneBot dependency helpers.

本模块集中完成中二节奏查分器实现类的单例初始化，并提供可用于
NoneBot 依赖注入的获取函数，便于在对话上下文中直接获得实例。
"""

from __future__ import annotations

from nonebot import get_driver

from ._schema import (
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
from .providers.lxns import LXNSChuScoreProvider

# --- 单例初始化 ---
_lxns_chu_provider = LXNSChuScoreProvider()


def get_lxns_chu_provider() -> LXNSChuScoreProvider:
    """获取 落雪咖啡屋 中二节奏查分器的单例实例。"""

    return _lxns_chu_provider


# --- 生命周期清理：在 NoneBot 关闭时释放网络会话 ---
driver = get_driver()


@driver.on_shutdown
async def _close_chu_score_providers():
    await _lxns_chu_provider.close()


__all__ = [
    "LXNSChuScoreProvider",
    "get_lxns_chu_provider",
    "PlayerChuInfo",
    "PlayerChuBests",
    "PlayerChuScore",
    "ChuRatingTrend",
    "ChuClearType",
    "ChuDifficulty",
    "ChuFullComboType",
    "ChuFullChainType",
    "ChuRankType",
    "ChuTrophy",
]
