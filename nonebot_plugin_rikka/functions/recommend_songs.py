"""
随机上分曲目推荐
"""

from dataclasses import dataclass
from random import sample
from typing import Literal, Optional

from nonebot import logger

from ..constants import _MAI_VERSION_MAP
from ..database.crud import MaiSongORM
from ..models.song import MaiSong, SongDifficulty
from ..score import PlayerMaiScore
from .analysis import get_player_strength
from .n50 import calc_dx_rating
from .song_tags import get_song_by_tags


@dataclass
class RecommendSong:
    song_id: int
    title: str
    type: Literal["dx", "standard"]
    level_index: Literal[0, 1, 2, 3, 4, 5]
    difficulty_value: float
    difficulty_value_fit: float
    dx_score: float
    target_dx_rating: int
    target_achievements: float
    old_dx_rating: int = 0
    old_achievements: float = 0


@dataclass
class RecommendSongs:
    old_version: list[RecommendSong]
    new_version: list[RecommendSong]


def _get_song_level_value(song_id: int, song_type: Literal["standard", "dx", "utage"], difficulty: int) -> float:
    """
    获取乐曲定数

    :param song_id: 乐曲 ID
    :param song_type: 铺面类型
    :param difficulty: 铺面难度
    """

    # DX 铺面
    if 10000 < song_id < 100000:
        song_id -= 10000

    song_info = MaiSongORM.get_song_sync(song_id)

    if not song_info:
        raise ValueError(f"请求的乐曲 {song_id}({song_type}) 不存在")

    if song_type == "dx" and len(song_info.difficulties.dx) > difficulty:
        return song_info.difficulties.dx[difficulty].level_value
    elif song_type == "standard" and len(song_info.difficulties.standard) > difficulty:
        return song_info.difficulties.standard[difficulty].level_value
    elif song_type == "utage":
        return 0

    raise ValueError(f"请求的乐曲 {song_id}({song_type}) 中的难度 {difficulty} 不存在")


def get_player_raise_score_songs(scores: list[PlayerMaiScore], min_dx_rating: int) -> RecommendSongs:
    """
    获取玩家推荐加分曲目

    :param scores: 玩家的全部成绩
    :param min_dx_rating: B50 底分
    """
    if len(scores) < 100:
        raise ValueError("玩家成绩数不足 100 条，无法进行上分曲目推荐")

    # 首先从 B100 中获得玩家的优势
    scores.sort(key=lambda x: x.dx_rating, reverse=True)
    player_strengths = get_player_strength(scores[:100])

    # 前 3 铺面配置
    patterns_strengths = sorted(player_strengths.patterns_strengths.items(), key=lambda x: x[1], reverse=True)[:3]
    # Top 1 铺面类型
    song_evaluate = sorted(player_strengths.song_evaluates.items(), key=lambda x: x[1], reverse=True)[0]

    # 获取 B100 乐曲平均定数
    total_level_value = 0.0
    for score in scores[:100]:
        score.song_level_value = _get_song_level_value(
            score.song_id, score.song_type.value, score.song_difficulty.value
        )
        total_level_value += score.song_level_value
    average_level_value = total_level_value / 100.0

    # 计算推荐定数范围
    min_level_value = max(average_level_value - 0.3, 4.0)
    max_level_value = min(average_level_value + 0.3, 16.0)  # 确保覆盖拟合定数上限

    # 根据定数范围筛选推荐曲目(拟合系数)
    total_recommended_songs: list[tuple[MaiSong, SongDifficulty]] = []
    all_songs = list(MaiSongORM._cache.values())
    for song in all_songs:
        for difficulty in song.difficulties.dx + song.difficulties.standard:
            level_value = difficulty.level_fit or difficulty.level_value
            if level_value is None:
                continue
            if not (min_level_value <= level_value <= max_level_value):
                continue

            total_recommended_songs.append((song, difficulty))

    # 根据铺面优势继续添加推荐曲目(铺面系数)
    # 不需要去重: 因为如果该曲目定数范围和铺面优势都合适，应该值得更高的推荐概率
    tags = [tag for tag, _ in patterns_strengths] + [song_evaluate[0]]
    tag_filtered_song_names = get_song_by_tags(tags)
    for song in all_songs:
        if song.title in tag_filtered_song_names:
            for difficulty in song.difficulties.dx + song.difficulties.standard:
                level_value = difficulty.level_value or difficulty.level_fit
                if level_value is None:
                    continue
                if not (min_level_value <= level_value <= max_level_value):
                    continue

                total_recommended_songs.append((song, difficulty))

    # 筛选模式: 0: 不过滤; 1: 过滤诈称铺; 2: 只输出水铺
    filter_mode = 2 if len(total_recommended_songs) > 500 else (1 if len(total_recommended_songs) > 100 else 0)

    # 筛选推荐曲目: 如果达成率 > 100.5 则剔除
    pending_recommended_songs: list[tuple[MaiSong, SongDifficulty, Optional[PlayerMaiScore]]] = []
    for song, difficulty in total_recommended_songs:
        # 查找玩家该曲该难度成绩
        player_score = next(
            (
                score
                for score in scores
                if score.song_id == song.id
                and score.song_type.value == ("dx" if difficulty in song.difficulties.dx else "standard")
                and score.song_difficulty.value == difficulty.difficulty
            ),
            None,
        )
        if player_score and player_score.achievements > 100.5:
            continue

        elif filter_mode >= 2 and difficulty.level_value - difficulty.level_fit < 0.3:
            continue

        elif filter_mode >= 1 and difficulty.level_fit - difficulty.level_value > 0.3:
            continue

        pending_recommended_songs.append((song, difficulty, player_score))

    # 筛选推荐曲目: 如果该曲目达成了更高的达成率之后仍然未加分就剔除
    recommended_songs_std: list[RecommendSong] = []
    recommended_songs_dx: list[RecommendSong] = []
    current_version = sorted(_MAI_VERSION_MAP.keys())[-1]
    for song, difficulty, player_score in pending_recommended_songs:
        level_value = difficulty.level_value
        if level_value is None:
            continue

        # 计算当前达成率对应的预估分数
        if player_score:
            current_dx_rating = player_score.dx_rating
            current_achievements = player_score.achievements
        else:
            current_dx_rating = 0
            current_achievements = 0.0

        # 计算需要达到的达成率以获得加分
        # 目标达成率的起点为下一个半档 97.0, 97.5, 98.0, ...
        target_achievements = max(97, ((int(current_achievements * 2) // 1) + 1) / 2.0)
        target_dx_rating = calc_dx_rating(level_value, target_achievements)
        while target_achievements <= 101.0:
            estimated_dx_rating = calc_dx_rating(level_value, target_achievements)
            if estimated_dx_rating > min_dx_rating:
                target_dx_rating = estimated_dx_rating
                break
            target_achievements += 0.5

        # Impossible.
        if target_achievements > 101.0:
            continue

        recommended_song_obj = RecommendSong(
            song_id=song.id,
            title=song.title,
            type="dx" if difficulty in song.difficulties.dx else "standard",
            level_index=difficulty.difficulty,  # type: ignore
            difficulty_value=difficulty.level_value,
            difficulty_value_fit=difficulty.level_fit,
            dx_score=player_score.dx_score if player_score else 0.0,
            target_dx_rating=target_dx_rating,
            target_achievements=target_achievements,
            old_dx_rating=round(current_dx_rating),
            old_achievements=current_achievements,
        )

        if song.version / 100 >= current_version and recommended_song_obj not in recommended_songs_dx:
            recommended_songs_dx.append(recommended_song_obj)
        elif song.version / 100 < current_version and recommended_song_obj not in recommended_songs_std:
            recommended_songs_std.append(recommended_song_obj)

    logger.debug(f"共找到 {len(recommended_songs_std) + len(recommended_songs_dx)} 首推荐曲目")

    # 随机选取 6 首推荐曲目
    return RecommendSongs(
        old_version=sample(recommended_songs_std, min(7, len(recommended_songs_std))),
        new_version=sample(recommended_songs_dx, min(7, len(recommended_songs_dx))),
    )
