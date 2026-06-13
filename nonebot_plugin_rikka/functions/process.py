from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..models.song import MaiSong, SongDifficulty
from ..score.maimai import PlayerMaiScore
from ..score.maimai._schema import SongType


class ProcessDataError(RuntimeError):
    """进度计算失败（用于替代返回错误字符串）。"""


class LevelProcessError(ProcessDataError):
    pass


@dataclass
class LevelProcessData:
    level: str
    plan: str
    completed: List[Tuple[MaiSong, Optional[PlayerMaiScore], int]]  # Song, Score, DiffIndex
    unfinished: List[Tuple[MaiSong, Optional[PlayerMaiScore], int]]
    not_played: List[Tuple[MaiSong, int]]  # Song, DiffIndex
    counts: Dict[str, int]  # total, completed, unfinished, not_played


def get_level_process_data(
    songs: List[MaiSong],
    scores: List[PlayerMaiScore],
    level: str,
    plan: str,
) -> LevelProcessData:

    target_tasks: list[tuple[MaiSong, SongDifficulty, bool]] = []  # (Song, SongDifficulty, is_dx)

    for s in songs:
        for d in s.difficulties.standard:
            if d.level == level:
                target_tasks.append((s, d, False))
        for d in s.difficulties.dx:
            if d.level == level:
                target_tasks.append((s, d, True))

    if not target_tasks:
        raise LevelProcessError(f"未找到等级为 {level} 的曲目")

    played_map: dict[tuple[int, bool, int], PlayerMaiScore] = {}

    for player_score in scores:
        is_dx = player_score.song_type == SongType.DX
        played_map[(player_score.song_id, is_dx, int(player_score.song_difficulty))] = player_score

    completed_list: list[tuple[MaiSong, Optional[PlayerMaiScore], int]] = []
    unfinished_list: list[tuple[MaiSong, Optional[PlayerMaiScore], int]] = []
    not_played_list: list[tuple[MaiSong, int]] = []

    plan_val = 0.0
    plan_mode = "ach"  # ach, fc, fs

    plan = plan.upper()
    if plan == "SSS+":
        plan_val = 100.5
    elif plan == "SSS":
        plan_val = 100.0
    elif plan == "SS+":
        plan_val = 99.5
    elif plan == "SS":
        plan_val = 99.0
    elif plan == "S+":
        plan_val = 98.0
    elif plan == "S":
        plan_val = 97.0
    elif "FC" in plan or "AP" in plan:
        plan_mode = "fc"
    elif "FS" in plan or "SYNC" in plan:
        plan_mode = "fs"

    combo_rank_order = ["fc", "fcp", "ap", "app"]
    sync_rank_order = ["fs", "fsp", "fsd", "fsdp"]

    for s, d, is_dx in target_tasks:
        sc = played_map.get((s.id, is_dx, d.difficulty))

        if sc is None:
            not_played_list.append((s, d.difficulty))
            continue

        is_comp = False
        if plan_mode == "ach":
            is_comp = sc.achievements >= plan_val
        elif plan_mode == "fc":
            if sc.fc:
                try:
                    curr_idx = combo_rank_order.index(sc.fc.lower())
                    target_idx = -1
                    if plan.lower() in combo_rank_order:
                        target_idx = combo_rank_order.index(plan.lower())
                    if target_idx != -1:
                        is_comp = curr_idx >= target_idx
                except ValueError:
                    pass
        elif plan_mode == "fs":
            if sc.fs:
                try:
                    curr_idx = sync_rank_order.index(sc.fs.lower())
                    target_idx = -1
                    if plan.lower() in sync_rank_order:
                        target_idx = sync_rank_order.index(plan.lower())
                    if target_idx != -1:
                        is_comp = curr_idx >= target_idx
                except ValueError:
                    pass

        if is_comp:
            completed_list.append((s, sc, d.difficulty))
        else:
            unfinished_list.append((s, sc, d.difficulty))

    return LevelProcessData(
        level=level,
        plan=plan,
        completed=completed_list,
        unfinished=unfinished_list,
        not_played=not_played_list,
        counts={
            "total": len(target_tasks),
            "completed": len(completed_list),
            "unfinished": len(unfinished_list),
            "not_played": len(not_played_list),
        },
    )
