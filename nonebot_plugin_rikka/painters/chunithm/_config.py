"""中二节奏绘图配置文件
包含路径配置、颜色配置以及各种映射表
"""

from pathlib import Path

from ...config import config
from ..maimai._config import FONT_DIR as MAI_FONT_DIR

# Paths
STATIC_DIR = Path(config.static_resource_path)
CHU_DIR = STATIC_DIR / "chu"
COVER_DIR = CHU_DIR / "cover"
PIC_DIR = CHU_DIR / "pic"
FONT_DIR = CHU_DIR / "font"
ICON_DIR = CHU_DIR / "icon"
PLATE_DIR = CHU_DIR / "plate"
TROPHY_DIR = CHU_DIR / "trophy"

# Fonts
FONT_MAIN = FONT_DIR / "FOT-RodinNTLGPro-B.otf" if not config.scorelist_font_main else Path(config.scorelist_font_main)
FONT_NUM = FONT_DIR / "FOT-RodinNTLGPro-EB.otf" if not config.scorelist_font_num else Path(config.scorelist_font_num)
FONT_TITLE = (
    MAI_FONT_DIR / "ResourceHanRoundedCN-Bold.ttf"
    if not config.scorelist_font_main
    else Path(config.scorelist_font_main)
)

# Rating colors
RATING_COLORS = {
    17.00: [(255, 235, 0), (255, 56, 56), (186, 82, 255), (50, 90, 200), (69, 174, 255)],  # 彩极
    16.00: [(11, 229, 186), (60, 249, 25), (244, 222, 49), (255, 235, 238), (42, 201, 240)],  # 彩
    15.25: (255, 255, 224),  # 白金
    14.50: (255, 215, 0),  # 金
    13.25: (202, 242, 255),  # 银
    12.00: (150, 107, 231),  # 铜
    10.00: (128, 0, 128),  # 紫
    7.00: (255, 0, 0),  # 红
    4.00: (255, 165, 0),  # 橙
    0.00: (0, 128, 0),  # 绿
}

# Difficulty colors
DIFF_COLORS = [
    (69, 193, 36),  # BASIC - 绿
    (255, 186, 1),  # ADVANCED - 黄
    (255, 90, 102),  # EXPERT - 红
    (134, 49, 200),  # MASTER - 紫
    (25, 25, 25),  # ULTIMA - 黑
]

# Score to rank mapping
SCORE_TO_RANK = {
    (0, 499999): "D",
    (500000, 599999): "C",
    (600000, 699999): "B",
    (700000, 799999): "BB",
    (800000, 899999): "BBB",
    (900000, 924999): "A",
    (925000, 949999): "AA",
    (950000, 974999): "AAA",
    (975000, 989999): "S",
    (990000, 999999): "S+",
    (1000000, 1004999): "SS",
    (1005000, 1007499): "SS+",
    (1007500, 1008999): "SSS",
    (1009000, 1010000): "SSS+",
}

# FC type display mapping
FC_DISPLAY = {
    "fullcombo": "FULL COMBO",
    "alljustice": "ALL JUSTICE",
    "alljusticecritical": "ALL JUSTICE CRITICAL",
}

# Rank to image index mapping (icon_rank_N.png)
RANK_TO_IMAGE = {
    "D": 0,
    "C": 1,
    "B": 2,
    "BB": 3,
    "BBB": 4,
    "A": 5,
    "AA": 6,
    "AAA": 7,
    "S": 8,
    "S+": 9,
    "SS": 10,
    "SS+": 11,
    "SSS": 12,
    "SSS+": 13,
}

# Achievement text to image file mapping
ACH_TO_IMAGE = {
    "alljustice": "icon_alljustice.png",
    "alljusticecritical": "icon_alljusticecritical.png",
    "fullcombo": "icon_fullcombo.png",
    "fullchain": "icon_chain.png",
    "clear": "clear.png",
}

# Difficulty index to chu-frame-N.png mapping
DIFF_TO_FRAME = {
    0: "chu-frame-0.png",  # BASIC
    1: "chu-frame-1.png",  # ADVANCED
    2: "chu-frame-2.png",  # EXPERT
    3: "chu-frame-3.png",  # MASTER
    4: "chu-frame-4.png",  # ULTIMA
    5: "chu-frame-0.png",  # WORLDS_END (fallback to BASIC)
}

# Trophy color to CHU_UI_Trophy_N.png index mapping
TROPHY_COLOR_INDEX = {
    "normal": 0,
    "bronze": 1,
    "silver": 2,
    "gold": 3,
    "platina": 4,
    "rainbow": 5,
    "staff": 6,
    "ongeki": 7,
    "maimai": 8,
}

# Rating threshold to color name mapping
RATING_COLOR_NAME = {
    17.00: "rainbow",
    16.00: "platinum",
    15.25: "gold",
    14.50: "sliver",
    13.25: "bronze",
    12.00: "murasaki",
    10.00: "red",
    7.00: "orange",
    4.00: "green",
    0.00: "green",
}


def get_rating_color_name(rating: float) -> str:
    """根据 Rating 获取颜色名称，用于加载对应图片资源。"""
    for threshold, color in sorted(RATING_COLOR_NAME.items(), reverse=True):
        if rating >= threshold:
            return color
    return "green"


def score_to_rank(score: int) -> str:
    """根据分数获取评级"""
    for (low, high), rank in SCORE_TO_RANK.items():
        if low <= score <= high:
            return rank
    return "D"
