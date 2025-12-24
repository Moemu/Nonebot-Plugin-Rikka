from typing import List

from PIL import Image, ImageDraw

from ..models.song import MaiSong
from ..score import PlayerMaiScore
from ._config import (
    COVER_DIR,
    FCL,
    FONT_MAIN,
    FONT_NUM,
    FSL,
    GENRE_MAPPING,
    PIC_DIR,
    SCORE_RANK_L,
)
from .utils import DrawText, change_column_width, coloum_width, dx_score


def draw_music_info(song: MaiSong, scores: List[PlayerMaiScore]) -> Image.Image:
    """
    绘制单曲详情及成绩

    :param song: 乐曲信息
    :param scores: 玩家在该乐曲上的成绩列表
    :return: 绘制后的图片
    """
    im = Image.open(PIC_DIR / "info_bg.png").convert("RGBA")
    dr = ImageDraw.Draw(im)
    mr = DrawText(dr, FONT_MAIN)
    tb = DrawText(dr, FONT_NUM)
    default_color = (124, 130, 255, 255)

    im.alpha_composite(Image.open(PIC_DIR / "logo.png").resize((249, 120)), (0, 34))

    # Cover
    cover_path = COVER_DIR / f"{song.id}.png"
    dx_cover_path = COVER_DIR / f"{song.id + 10000}.png"
    if cover_path.exists():
        cover = Image.open(cover_path).resize((300, 300))
    elif dx_cover_path.exists():
        cover = Image.open(dx_cover_path).resize((300, 300))
    else:
        cover = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    im.alpha_composite(cover, (100, 260))

    # Genre
    genre_key = GENRE_MAPPING.get(song.genre, "maimai")
    genre_path = PIC_DIR / f"info-{genre_key}.png"
    if genre_path.exists():
        im.alpha_composite(Image.open(genre_path), (100, 260))

    # Version
    version_path = PIC_DIR / f"{song.version}.png"
    if version_path.exists():
        im.alpha_composite(Image.open(version_path).resize((183, 90)), (295, 205))

    # Type (DX/Standard)
    song_type = scores[0].song_type.value if scores else "dx"
    type_path = PIC_DIR / f"{song_type.upper()}.png"
    if type_path.exists():
        im.alpha_composite(Image.open(type_path).resize((55, 20)), (350, 560))

    # Artist & Title
    artist = song.artist
    if coloum_width(artist) > 58:
        artist = change_column_width(artist, 57) + "..."
    mr.draw(255, 595, 12, artist, default_color, "mm")

    title = song.title
    if coloum_width(title) > 38:
        title = change_column_width(title, 37) + "..."
    mr.draw(255, 622, 18, title, default_color, "mm")

    tb.draw(160, 720, 22, f"{song.id}", default_color, "mm")
    tb.draw(380, 720, 22, f"{song.bpm}", default_color, "mm")

    # Difficulties
    if song_type == "dx":
        diffs = song.difficulties.dx
    else:
        diffs = song.difficulties.standard

    y = 100
    for num, diff in enumerate(diffs):
        if num >= 5:
            break

        im.alpha_composite(Image.open(PIC_DIR / f"d-{num}.png"), (650, 235 + y * num))

        score = next((s for s in scores if s.song_difficulty.value == num), None)

        if score:
            im.alpha_composite(Image.open(PIC_DIR / "ra-dx.png").resize((102, 44)), (850, 272 + y * num))

            # DX Score Stars
            max_dx = diff.notes.total * 3
            dx_val = score.dx_score
            dx_star = dx_score(int(dx_val / max_dx * 100)) if max_dx > 0 else 0

            if dx_star != 0:
                im.alpha_composite(
                    Image.open(PIC_DIR / f"UI_GAM_Gauge_DXScoreIcon_0{dx_star}.png").resize((32, 19)),
                    (851, 296 + y * num),
                )

            tb.draw(916, 304 + y * num, 13, f"{dx_val}/{max_dx}", default_color, "mm")

            im.alpha_composite(Image.open(PIC_DIR / "fcfs_score.png").resize((100, 48)), (737, 265 + y * num))

            if score.fc:
                fc_str = FCL.get(score.fc.value, "")
                if fc_str:
                    im.alpha_composite(
                        Image.open(PIC_DIR / f"UI_CHR_PlayBonus_{fc_str}.png").resize((60, 60)), (732, 261 + y * num)
                    )
            if score.fs:
                fs_str = FSL.get(score.fs.value, "")
                if fs_str:
                    im.alpha_composite(
                        Image.open(PIC_DIR / f"UI_CHR_PlayBonus_{fs_str}.png").resize((60, 60)), (780, 261 + y * num)
                    )

            im.alpha_composite(Image.open(PIC_DIR / "ra.png"), (1350, 400 + y * num))

            rate_str = SCORE_RANK_L.get(score.rate.value, "D")
            im.alpha_composite(
                Image.open(PIC_DIR / f"UI_TTR_Rank_{rate_str}.png").resize((126, 56)), (965, 265 + y * num)
            )

            tb.draw(510, 292 + y * num, 42, f"{score.achievements:.4f}%", default_color, "lm")
            tb.draw(685, 248 + y * num, 25, f"{diff.level_value}", (255, 255, 255, 255), "mm")
            tb.draw(915, 283 + y * num, 18, f"{score.dx_rating}", default_color, "mm")

        else:
            tb.draw(685, 248 + y * num, 25, f"{diff.level_value}", (255, 255, 255, 255), "mm")
            mr.draw(800, 300 + y * num, 30, "未游玩", default_color, "mm")

    if len(diffs) == 4:
        mr.draw(800, 300 + y * 4, 30, "没有该难度", default_color, "mm")

    mr.draw(
        600, 827, 22, "Designed by Yuri-YuzuChaN & BlueDeer233. Generated by NoneBot-Plugin-Rikka", default_color, "mm"
    )

    return im
