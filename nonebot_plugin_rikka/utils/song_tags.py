from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from typing_extensions import TypedDict

from ..config import config

_SONG_TAGS_FILE = Path(config.static_resource_path) / "combined_tags.json"
SONG_TAGS_DATA_AVAILABLE = _SONG_TAGS_FILE.exists() and _SONG_TAGS_FILE.stat().st_size > 0
_SONG_TAGS_DATA: DxRatingCombinedTags = (
    json.loads(_SONG_TAGS_FILE.read_text(encoding="utf-8")) if SONG_TAGS_DATA_AVAILABLE else {}  # type:ignore
)


class DxRatingTag(TypedDict):
    id: int
    localized_name: dict[str, str]
    localized_description: dict[str, str]
    group_id: int


class DxRatingTagGroup(TypedDict):
    id: int
    localized_name: dict[str, str]


class DxRatingTagSong(TypedDict):
    song_id: str
    """In fact, this is song name."""
    sheet_type: Literal["dx", "std"]
    sheet_difficulty: Literal["remaster", "master", "expert"]
    tag_id: int


class DxRatingCombinedTags(TypedDict):
    tags: list[DxRatingTag]
    tagGroups: list[DxRatingTagGroup]
    tagSongs: list[DxRatingTagSong]


def get_songs_tags(
    song_name: str, song_type: Literal["dx", "std"], song_difficulty: Literal["remaster", "master", "expert"]
) -> list[str]:
    tags = []
    for tag_song in _SONG_TAGS_DATA["tagSongs"]:
        if (
            tag_song["song_id"] == song_name
            and tag_song["sheet_type"] == song_type
            and tag_song["sheet_difficulty"] == song_difficulty
        ):
            tag_id = tag_song["tag_id"]
            for tag in _SONG_TAGS_DATA["tags"]:
                if tag["id"] == tag_id:
                    tags.append(tag["localized_name"].get("zh-Hans", "未知标签"))
                    break
    return tags
