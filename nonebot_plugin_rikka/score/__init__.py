"""Score providers registry.

本模块作为统一入口，按游戏类型拆分为子包：
- score.maimai: 舞萌DX
- score.chunithm: 中二节奏
"""

from __future__ import annotations

# 中二节奏
from .chunithm import (
    LXNSChuScoreProvider,
    PlayerChuBests,
    PlayerChuInfo,
    PlayerChuScore,
    get_lxns_chu_provider,
)

# 舞萌DX
from .maimai import (
    BaseScoreProvider,
    DivingFishScoreProvider,
    LXNSScoreProvider,
    MaimaiPyScoreProvider,
    PlayerMaiB50,
    PlayerMaiInfo,
    PlayerMaiScore,
    auto_get_score_provider,
    get_all_score_providers,
    get_divingfish_provider,
    get_lxns_provider,
    get_maimaipy_provider,
)

__all__ = [
    # 舞萌DX
    "BaseScoreProvider",
    "LXNSScoreProvider",
    "DivingFishScoreProvider",
    "MaimaiPyScoreProvider",
    "get_lxns_provider",
    "get_divingfish_provider",
    "get_maimaipy_provider",
    "get_all_score_providers",
    "auto_get_score_provider",
    "PlayerMaiInfo",
    "PlayerMaiB50",
    "PlayerMaiScore",
    # 中二节奏
    "LXNSChuScoreProvider",
    "get_lxns_chu_provider",
    "PlayerChuInfo",
    "PlayerChuBests",
    "PlayerChuScore",
]
