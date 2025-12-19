"""
绘图配置文件
包含路径配置、字体配置、颜色配置以及各种映射表
"""

from pathlib import Path
from typing import Dict

from ..config import config

# Configuration
STATIC_DIR = Path(config.static_resource_path)
MAI_DIR = STATIC_DIR / "mai"
PIC_DIR = MAI_DIR / "pic"
COVER_DIR = MAI_DIR / "cover"
PLATE_DIR = MAI_DIR / "plate"
ICON_DIR = MAI_DIR / "icon"

# Fonts
# Adjust these paths if necessary based on your actual font files
FONT_MAIN = STATIC_DIR / "ResourceHanRoundedCN-Bold.ttf"
FONT_NUM = STATIC_DIR / "Torus SemiBold.otf"

# Colors
TEXT_COLOR = (124, 129, 255, 255)

# Mappings
SCORE_RANK_L: Dict[str, str] = {
    "d": "D",
    "c": "C",
    "b": "B",
    "bb": "BB",
    "bbb": "BBB",
    "a": "A",
    "aa": "AA",
    "aaa": "AAA",
    "s": "S",
    "sp": "Sp",
    "ss": "SS",
    "ssp": "SSp",
    "sss": "SSS",
    "sssp": "SSSp",
}
FCL: Dict[str, str] = {"fc": "FC", "fcp": "FCp", "ap": "AP", "app": "APp"}
FSL: Dict[str, str] = {"fs": "FS", "fsp": "FSp", "fsd": "FSD", "fsdp": "FSDp", "sync": "Sync"}
GENRE_MAPPING: Dict[str, str] = {
    "POPSアニメ": "anime",
    "niconicoボーカロイド": "niconico",
    "東方Project": "touhou",
    "ゲームバラエティ": "game",
    "maimai": "maimai",
    "オンゲキCHUNITHM": "ongeki",
}
