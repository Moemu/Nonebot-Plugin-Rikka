"""
绘图模块
按游戏类型拆分为子包：
- painters.maimai: 舞萌DX
- painters.chunithm: 中二节奏

`painters.maimai` 参考自: - maimaidx_draw (https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx)
`painters.chunithm` 参考自:
- [NightmareDreemurr/image-generator](https://github.com/NightmareDreemurr/image-generator)
- [StartendInfinity/CometInfinity_Bot](https://github.com/StartendInfinity/CometInfinity_Bot)
"""

from .chunithm import DrawChuBest
from .maimai import (
    DrawBest,
    DrawScores,
    draw_music_info,
    draw_player_rating_trend,
    draw_player_strength_analysis,
)
from .utils import image_to_bytes

__all__ = [
    "DrawBest",
    "DrawScores",
    "draw_music_info",
    "draw_player_strength_analysis",
    "draw_player_rating_trend",
    "DrawChuBest",
    "image_to_bytes",
]
