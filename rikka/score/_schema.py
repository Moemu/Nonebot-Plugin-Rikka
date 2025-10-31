from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SongDifficulty(int, Enum):
    """铺面难度"""

    BASIC = 0
    """宴会场铺面也为0"""
    ADVANCED = 1
    EXPERT = 2
    MASTER = 3
    ReMASTER = 4


class ScoreFCType(str, Enum):
    """FULL COMBO 类型"""

    APP = "app"
    """ALL PERFECT PLUS"""
    AP = "ap"
    """ALL PERFECT"""
    FCP = "fcp"
    """FULL COMBO PLUS"""
    FC = "fc"
    """FULL COMBO"""


class ScoreFSType(str, Enum):
    """FULL SYNC 类型"""

    FSDP = "fsdp"
    """FDX+"""
    FSD = "fsd"
    """FDX"""
    FSP = "fsp"
    """FS+"""
    FS = "fs"
    """FS"""
    SYNC = "sync"
    """SYNC PLAY"""


class ScoreRateType(str, Enum):
    """评级类型"""

    SSSP = "sssp"
    """SSS+"""
    SSS = "sss"
    """SSS"""
    SSP = "ssp"
    """SS+"""
    SS = "ss"
    """SS"""
    SP = "sp"
    """S+"""
    S = "s"
    """S"""
    AAA = "aaa"
    """AAA"""
    AA = "aa"
    """AA"""
    A = "a"
    """A"""
    BBB = "bbb"
    """BBB"""
    BB = "bb"
    """BB"""
    B = "b"
    """B"""
    C = "c"
    """C"""
    D = "d"
    """D"""


class TrophyColor(str, Enum):
    """称号颜色"""

    NORMAL = "Normal"
    """普通"""
    BRONZE = "Bronze"
    """铜"""
    SILVER = "Silver"
    """银"""
    GOLD = "Gold"
    """金"""
    RAINBOW = "Rainbow"
    """虹"""


class SongType(str, Enum):
    """谱面类型"""

    STANDARD = "standard"
    """标准谱面"""
    DX = "dx"
    """DX 谱面"""
    UTAGE = "utage"
    """宴会场谱面"""


@dataclass
class PlayerMaiScore:
    song_id: int
    """乐曲 ID"""
    song_name: str
    """乐曲名"""
    song_type: SongType
    """铺面类型"""
    song_level: str
    """铺面等级，如 `11+`"""
    song_difficulty: SongDifficulty
    """铺面难度分类"""
    achievements: float
    """达成率"""
    dx_score: int
    """DX 分数"""
    dx_star: int
    """DX 星级"""
    dx_rating: float
    """DX Rating"""
    rate: ScoreRateType
    """评级"""
    fc: Optional[ScoreFCType] = None
    """FC 情况"""
    fs: Optional[ScoreFSType] = None
    """同步游玩情况"""


@dataclass
class PlayerMaiB50:
    """玩家B50信息，也可用于AP50等类型"""

    standard_total: int
    """旧版本谱面 Best 35 总分"""
    dx_total: int
    """现版本谱面 Best 15 总分"""
    standard: list[PlayerMaiScore]
    """旧版本谱面 Best 35 列表"""
    dx: list[PlayerMaiScore]
    """现版本谱面 Best 15 列表"""


@dataclass
class PlayerMaiCollection:
    """玩家舞萌收藏品"""

    id: int
    """收藏品ID"""
    name: str
    """收藏品名称"""
    description: Optional[str] = None
    """收藏品说明"""
    genre: Optional[str] = None
    """收藏品分类"""


@dataclass
class PlayerMaiTrophy:
    """玩家舞萌称号"""

    id: int
    """收藏品ID"""
    name: str
    """收藏品名称"""
    color: TrophyColor
    """称号颜色"""
    description: Optional[str] = None
    """收藏品说明"""
    genre: Optional[str] = None
    """收藏品分类"""


@dataclass
class PlayerMaiInfo:
    """玩家舞萌DX信息"""

    name: str
    """游戏内名称"""
    rating: str
    """玩家 DX Rating"""
    friend_code: str
    """好友码"""
    course_rank: int
    """段位 ID"""
    class_rank: int
    """阶级 ID"""
    trophy: PlayerMaiTrophy
    """称号"""
    icon: Optional[PlayerMaiCollection] = None
    """头像"""
    name_plate: Optional[PlayerMaiCollection] = None
    """姓名框"""
    frame: Optional[PlayerMaiCollection] = None
    """背景"""
    upload_time: Optional[str] = None
    """成绩上传时间"""
