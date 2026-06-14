"""中二节奏 (CHUNITHM) 数据结构定义

基于落雪咖啡屋 LXNS API 的中二节奏数据模型。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class ChuDifficulty(int, Enum):
    """谱面难度"""

    BASIC = 0
    ADVANCED = 1
    EXPERT = 2
    MASTER = 3
    ULTIMA = 4
    WORLDS_END = 5


class ChuClearType(str, Enum):
    """CLEAR 类型"""

    CATASTROPHY = "catastrophy"
    ABSOLUTE = "absolute"
    BRAVE = "brave"
    HARD = "hard"
    CLEAR = "clear"
    FAILED = "failed"


class ChuFullComboType(str, Enum):
    """FULL COMBO 类型"""

    AJC = "alljusticecritical"
    """ALL JUSTICE CRITICAL"""
    AJ = "alljustice"
    """ALL JUSTICE"""
    FC = "fullcombo"
    """FULL COMBO"""


class ChuFullChainType(str, Enum):
    """FULL CHAIN 类型"""

    FULLCHAIN = "fullchain"
    """铂 FULL CHAIN"""
    FULLCHAIN2 = "fullchain2"
    """金 FULL CHAIN"""


class ChuRankType(str, Enum):
    """评级类型"""

    SSSP = "sssp"
    SSS = "sss"
    SSP = "ssp"
    SS = "ss"
    SP = "sp"
    S = "s"
    AAA = "aaa"
    AA = "aa"
    A = "a"
    BBB = "bbb"
    BB = "bb"
    B = "b"
    C = "c"
    D = "d"


@dataclass
class PlayerChuScore:
    """中二节奏游玩成绩"""

    song_id: int
    """曲目 ID"""
    song_name: str
    """曲名"""
    song_level: str
    """难度标级，如 `14+`"""
    song_difficulty: ChuDifficulty
    """难度"""
    score: int
    """分数"""
    rating: float
    """Rating"""
    over_power: float
    """OVER POWER"""
    clear: Optional[ChuClearType] = None
    """CLEAR 类型"""
    full_combo: Optional[ChuFullComboType] = None
    """FULL COMBO 类型"""
    full_chain: Optional[ChuFullChainType] = None
    """FULL CHAIN 类型"""
    rank: Optional[ChuRankType] = None
    """评级类型"""
    play_time: Optional[str] = None
    """游玩时间"""


@dataclass
class PlayerChuBests:
    """玩家 Rating 构成

    包含 Best 30（评分对象曲·最高）、Selection 10（候选评分对象曲·最高）、
    New 20（评分对象曲·新曲）。
    """

    bests: list[PlayerChuScore] = field(default_factory=list)
    """旧版本 Best 30 列表"""
    selections: list[PlayerChuScore] = field(default_factory=list)
    """旧版本 Selection 10 列表"""
    new_bests: list[PlayerChuScore] = field(default_factory=list)
    """当前版本 Best 20 列表"""

    @property
    def rating(self) -> int:
        total = 0.0
        for score in self.bests + self.selections + self.new_bests:
            total += score.rating
        return int(total)


@dataclass
class PlayerChuInfo:
    """中二节奏玩家信息"""

    name: str
    """游戏内名称"""
    rating: float
    """玩家 Rating"""
    friend_code: int
    """好友码"""
    level: int = 0
    """玩家等级"""
    class_emblem_base: int = 0
    """CLASS 勋章 - 缎带"""
    class_emblem_medal: int = 0
    """CLASS 勋章 - 勋章"""
    over_power: float = 0.0
    """总 OVER POWER"""
    over_power_progress: float = 0.0
    """OVER POWER 总进度"""
    total_play_count: int = 0
    """总游玩次数"""
    trophy_id: Optional[int] = None
    """称号 ID"""
    trophy: Optional["ChuTrophy"] = None
    """称号详情"""
    character_id: Optional[int] = None
    """角色 ID"""
    name_plate_id: Optional[int] = None
    """名牌版 ID"""
    map_icon_id: Optional[int] = None
    """地图头像 ID"""
    upload_time: Optional[str] = None
    """同步时间"""


@dataclass
class ChuTrophy:
    """中二节奏称号"""

    id: int
    """称号 ID"""
    name: str
    """称号名称"""
    color: Literal["normal", "bronze", "silver", "gold", "platina", "rainbow", "staff", "ongeki", "maimai"] = "normal"
    """称号颜色类型: """
    description: Optional[str] = None
    """称号描述"""


@dataclass
class ChuRatingTrend:
    """Rating 趋势"""

    rating: float
    """总平均 Rating"""
    bests_rating: float
    """Best 30 平均 Rating"""
    selections_rating: float
    """Selection 10 平均 Rating"""
    recents_rating: Optional[float] = None
    """Recent 10（MAX）平均 Rating"""
    new_bests_rating: Optional[float] = None
    """Best 20（新曲）平均 Rating"""
    date: Optional[str] = None
    """日期"""
