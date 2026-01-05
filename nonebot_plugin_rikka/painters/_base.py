from typing import List, Optional

from PIL import Image, ImageDraw

from ..database.crud import MaiSongORM
from ..score import PlayerMaiInfo, PlayerMaiScore
from ._config import (
    COVER_DIR,
    FCL,
    FONT_MAIN,
    FONT_NUM,
    FSL,
    ICON_DIR,
    PIC_DIR,
    PLATE_DIR,
    SCORE_RANK_L,
)
from .utils import DrawText, change_column_width, coloum_width


class ScoreBaseImage:
    """
    成绩绘图基类，提供基础的绘图资源和方法
    """

    text_color = (124, 129, 255, 255)
    t_color = [
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (255, 255, 255, 255),
        (138, 0, 226, 255),
    ]
    id_color = [(129, 217, 85, 255), (245, 189, 21, 255), (255, 129, 141, 255), (159, 81, 220, 255), (138, 0, 226, 255)]
    bg_color = [
        (111, 212, 61, 255),
        (248, 183, 9, 255),
        (255, 129, 141, 255),
        (159, 81, 220, 255),
        (219, 170, 255, 255),
    ]

    def __init__(self, image: Optional[Image.Image] = None) -> None:
        """
        初始化 ScoreBaseImage

        :param image: 可选的 PIL Image 对象，如果提供则在其上绘图
        """
        self._diff = [
            Image.open(PIC_DIR / "b50_score_basic.png"),
            Image.open(PIC_DIR / "b50_score_advanced.png"),
            Image.open(PIC_DIR / "b50_score_expert.png"),
            Image.open(PIC_DIR / "b50_score_master.png"),
            Image.open(PIC_DIR / "b50_score_remaster.png"),
        ]
        self.title_lengthen_bg = Image.open(PIC_DIR / "title-lengthen.png")
        self.design_bg = Image.open(PIC_DIR / "design.png")
        self.id_diff = [Image.new("RGBA", (55, 10), color) for color in self.bg_color]

        image = image or Image.open(PIC_DIR / "b50_bg.png").convert("RGBA")
        self._im = image
        dr = ImageDraw.Draw(self._im)
        self._sy = DrawText(dr, FONT_MAIN)
        self._tb = DrawText(dr, FONT_NUM)

    @staticmethod
    def _find_ra_pic(rating: int) -> str:
        """
        根据 Rating 获取对应的 Rating 图片文件名
        """
        if rating < 1000:
            num = "01"
        elif rating < 2000:
            num = "02"
        elif rating < 4000:
            num = "03"
        elif rating < 7000:
            num = "04"
        elif rating < 10000:
            num = "05"
        elif rating < 12000:
            num = "06"
        elif rating < 13000:
            num = "07"
        elif rating < 14000:
            num = "08"
        elif rating < 14500:
            num = "09"
        elif rating < 15000:
            num = "10"
        else:
            num = "11"
        return f"UI_CMN_DXRating_{num}.png"

    def _find_match_level(self, course_rank: int) -> str:
        """
        获取段位图片文件名
        """
        if course_rank <= 10:
            num = f"{course_rank:02d}"
        else:
            num = f"{course_rank + 1:02d}"
        return f"UI_DNM_DaniPlate_{num}.png"

    def draw_profile(self, player_info: PlayerMaiInfo):
        """
        绘制 Profile 部分

        :param player_info: 玩家信息对象
        :type player_info: PlayerMaiInfo
        """
        logo = Image.open(PIC_DIR / "logo.png").resize((249, 120))
        dx_rating = Image.open(PIC_DIR / self._find_ra_pic(player_info.rating)).resize((186, 35))
        name_img = Image.open(PIC_DIR / "Name.png")
        match_level = Image.open(PIC_DIR / self._find_match_level(player_info.course_rank)).resize((80, 32))
        class_level = Image.open(PIC_DIR / f"UI_FBR_Class_{player_info.class_rank:02d}.png").resize((90, 54))

        self._im.alpha_composite(logo, (14, 60))

        # Plate
        if player_info.name_plate:
            plate_path = PLATE_DIR / f"{player_info.name_plate.id}.png"
            if plate_path.exists():
                plate = Image.open(plate_path).resize((800, 130))
            else:
                plate = Image.open(PIC_DIR / "UI_Plate_300501.png").resize((800, 130))
        else:
            plate = Image.open(PIC_DIR / "UI_Plate_300501.png").resize((800, 130))
        self._im.alpha_composite(plate, (300, 60))

        # Icon
        if player_info.icon:
            icon_path = ICON_DIR / f"{player_info.icon.id}.png"
            if icon_path.exists():
                icon = Image.open(icon_path).resize((120, 120))
            else:
                icon = Image.open(PIC_DIR / "UI_Icon_309503.png").resize((120, 120))
        else:
            icon = Image.open(PIC_DIR / "UI_Icon_309503.png").resize((120, 120))
        self._im.alpha_composite(icon, (305, 65))

        self._im.alpha_composite(dx_rating, (435, 72))
        rating_str = f"{player_info.rating:05d}"
        for n, i in enumerate(rating_str):
            self._im.alpha_composite(
                Image.open(PIC_DIR / f"UI_NUM_Drating_{i}.png").resize((17, 20)), (520 + 15 * n, 80)
            )
        self._im.alpha_composite(name_img, (435, 115))
        self._im.alpha_composite(match_level, (625, 120))
        self._im.alpha_composite(class_level, (620, 60))

        self._sy.draw(445, 135, 25, player_info.name, (0, 0, 0, 255), "lm")

    def draw_footer(self):
        self._sy.draw(
            700,
            1570,
            27,
            "Designed by Yuri-YuzuChaN & BlueDeer233 & TomeChen. Generated by Nonebot-Plugin-Rikka",
            self.text_color,
            "mm",
            5,
            (255, 255, 255, 255),
        )

    def whiledraw(self, data: List[PlayerMaiScore], height: int = 235) -> None:
        """
        循环绘制成绩列表

        :param data: 成绩列表
        :param height: 自定义起始高度 (b35: 235; b15: 1085)
        """
        dy = 114
        y = height

        for num, info in enumerate(data):
            if num % 5 == 0:
                x = 16
                y += dy if num != 0 else 0
            else:
                x += 276

            cover_path = COVER_DIR / f"{info.song_id}.png"
            if not cover_path.exists():
                cover_path = COVER_DIR / f"{info.song_id + 10000}.png"

            if not cover_path.exists():
                # Fallback or handle missing cover
                cover = Image.new("RGBA", (75, 75), (0, 0, 0, 0))
            else:
                cover = Image.open(cover_path).resize((75, 75))

            version_path = PIC_DIR / f'{"DX" if info.song_type.value == "dx" else "SD"}.png'
            version = Image.open(version_path).resize((37, 14))

            rate_str = SCORE_RANK_L.get(info.rate.value, "D")
            rate = Image.open(PIC_DIR / f"UI_TTR_Rank_{rate_str}.png").resize((63, 28))

            max_dx_score: int | None = None
            song_obj = MaiSongORM.get_song_sync(info.song_id)
            if song_obj:
                diff_value = info.song_difficulty.value
                diff = (
                    song_obj.difficulties.dx[diff_value]
                    if info.song_type.value == "dx"
                    else song_obj.difficulties.standard[diff_value]
                )
                max_dx_score = diff.notes.total * 3

            self._im.alpha_composite(self._diff[info.song_difficulty.value], (x, y))
            self._im.alpha_composite(cover, (x + 12, y + 12))
            self._im.alpha_composite(version, (x + 51, y + 91))
            self._im.alpha_composite(rate, (x + 92, y + 78))

            if info.fc:
                fc_str = FCL.get(info.fc.value, "")
                if fc_str:
                    fc = Image.open(PIC_DIR / f"UI_MSS_MBase_Icon_{fc_str}.png").resize((34, 34))
                    self._im.alpha_composite(fc, (x + 154, y + 77))
            if info.fs:
                fs_str = FSL.get(info.fs.value, "")
                if fs_str:
                    fs = Image.open(PIC_DIR / f"UI_MSS_MBase_Icon_{fs_str}.png").resize((34, 34))
                    self._im.alpha_composite(fs, (x + 185, y + 77))

            if info.dx_star:
                # dx_star is int (1-5)
                if info.dx_star > 0:
                    self._im.alpha_composite(
                        Image.open(PIC_DIR / f"UI_GAM_Gauge_DXScoreIcon_0{info.dx_star}.png").resize((47, 26)),
                        (x + 217, y + 80),
                    )

            self._tb.draw(x + 26, y + 98, 13, info.song_id, self.id_color[info.song_difficulty.value], anchor="mm")
            # Song title
            title = info.song_name
            if coloum_width(title) > 12:
                title = change_column_width(title, 12) + "..."
            self._sy.draw(x + 93, y + 14, 14, title, self.t_color[info.song_difficulty.value], anchor="lm")
            # Play Count
            if info.play_count:
                self._sy.draw(
                    x + 215, y + 14, 14, f"PC: {info.play_count}", self.t_color[info.song_difficulty.value], anchor="lm"
                )
            # Achievements
            self._tb.draw(
                x + 93, y + 38, 30, f"{info.achievements:.4f}%", self.t_color[info.song_difficulty.value], anchor="lm"
            )
            if max_dx_score is not None:
                self._tb.draw(
                    x + 209,
                    y + 65,
                    15,
                    f"{info.dx_score}/{max_dx_score}",
                    self.t_color[info.song_difficulty.value],
                    anchor="mm",
                )
            song_level_string = "{:.1f}".format(info.song_level_value) if info.song_level_value else info.song_level
            self._tb.draw(
                x + 93,
                y + 65,
                15,
                f"{song_level_string} -> {round(info.dx_rating)}",
                self.t_color[info.song_difficulty.value],
                anchor="lm",
            )
