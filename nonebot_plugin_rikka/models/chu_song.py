"""中二节奏 (CHUNITHM) 曲目数据模型"""

from dataclasses import dataclass, fields
from typing import Literal, Optional


@dataclass
class ChuSongNotes:
    total: int
    """总物量"""
    tap: int
    """TAP 物量"""
    hold: int
    """HOLD 物量"""
    slide: int
    """SLIDE 物量"""
    air: int
    """AIR 物量"""
    flick: int
    """FLICK 物量"""

    @staticmethod
    def from_dict(data: dict[str, int]) -> "ChuSongNotes":
        """
        Initialize ChuSongNotes from a dictionary.
        """
        return ChuSongNotes(
            total=data.get("total", 0),
            tap=data.get("tap", 0),
            hold=data.get("hold", 0),
            slide=data.get("slide", 0),
            air=data.get("air", 0),
            flick=data.get("flick", 0),
        )


@dataclass
class ChuSongDifficulty:
    """中二节奏谱面难度"""

    difficulty: Literal[0, 1, 2, 3, 4, 5]
    """难度 (0=BASIC, 1=ADVANCED, 2=EXPERT, 3=MASTER, 4=ULTIMA, 5=WORLDS_END)"""
    level: str
    """难度标级，如 `14+`"""
    level_value: float
    """谱面定数"""
    note_designer: str
    """谱师"""
    notes: ChuSongNotes
    """谱面物量"""
    kanji: Optional[str] = None
    """谱面属性（仅 WORLDS_END）"""


@dataclass
class ChuSongDifficulties:
    """中二节奏曲目难度集合"""

    difficulties: list[ChuSongDifficulty]

    @staticmethod
    def from_list(data: list[dict]) -> "ChuSongDifficulties":
        """
        从 API 返回的难度列表初始化
        """
        diff_fields = {f.name for f in fields(ChuSongDifficulty)}
        result = []
        for item in data:
            notes = item.get("notes", {})
            item["notes"] = ChuSongNotes.from_dict(notes) if notes else ChuSongNotes(0, 0, 0, 0, 0, 0)
            result.append(ChuSongDifficulty(**{k: v for k, v in item.items() if k in diff_fields}))
        return ChuSongDifficulties(difficulties=result)


@dataclass
class ChuSong:
    """中二节奏曲目"""

    id: int
    """曲目 ID"""
    title: str
    """曲名"""
    artist: str
    """艺术家"""
    genre: str
    """曲目分类"""
    bpm: int
    """曲目 BPM"""
    version: int
    """曲目首次出现版本"""
    difficulties: ChuSongDifficulties
    """曲目难度集合"""

    def __hash__(self) -> int:
        return hash(self.id)
