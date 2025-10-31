"""Score providers registry and NoneBot dependency helpers.

本模块集中完成各个查分器实现类的单例初始化，并提供可用于
NoneBot 依赖注入的获取函数，便于在对话上下文中直接获得实例。
"""

from __future__ import annotations

from typing import Dict

from nonebot import get_driver

from ._base import BaseScoreProvider
from ._schema import PlayerMaiB50, PlayerMaiInfo
from .providers.lxns import LXNSScoreProvider

# --- 单例初始化（每个实现类仅初始化一次） ---
_lxns_provider = LXNSScoreProvider()


# --- 依赖注入获取函数（用于 Depends(...)） ---
def get_lxns_provider() -> LXNSScoreProvider:
    """获取 落雪咖啡屋 查分器的单例实例。

    可用于 NoneBot 依赖注入：

        from nonebot.params import Depends
        from rikka.score import get_lxns_provider

        async def handler(provider: LXNSScoreProvider = Depends(get_lxns_provider)):
            ...
    """

    return _lxns_provider


def get_all_score_providers() -> Dict[str, BaseScoreProvider]:
    """获取当前已注册的全部查分器实例。

    返回一个简单的字典映射，键为实现名，值为对应的单例实例。
    便于按需遍历或根据配置选择具体实现。
    """

    return {
        "lxns": _lxns_provider,
    }


# --- 生命周期清理：在 NoneBot 关闭时释放网络会话 ---
driver = get_driver()


@driver.on_shutdown
async def _close_score_providers():
    for provider in get_all_score_providers().values():
        await provider.close()


__all__ = [
    "BaseScoreProvider",
    "LXNSScoreProvider",
    "get_lxns_provider",
    "get_all_score_providers",
    "PlayerMaiInfo",
    "PlayerMaiB50",
]
