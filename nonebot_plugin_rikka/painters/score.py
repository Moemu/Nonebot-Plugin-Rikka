from typing import List, Optional

from PIL import Image

from ..functions.recommend_songs import RecommendSong, RecommendSongs
from ..score import PlayerMaiInfo, PlayerMaiScore
from ._base import ScoreBaseImage
from ._config import COVER_DIR, PIC_DIR
from .utils import change_column_width, coloum_width, find_all_clear_rank


class DrawScores(ScoreBaseImage):
    """
    绘制成绩列表图
    """

    def __init__(self, image: Optional[Image.Image] = None) -> None:
        """
        初始化 DrawScore

        :param image: 基础图片对象
        """
        super().__init__(image)

    def _draw_score_background(self) -> None:
        self._im.alpha_composite(self._get_image(PIC_DIR / "aurora.png", size=(1400, 220), convert_rgba=True))
        self._im.alpha_composite(self._get_image(PIC_DIR / "bg_shines.png", convert_rgba=True), (34, 0))
        self._im.alpha_composite(
            self._get_image(PIC_DIR / "rainbow.png", convert_rgba=True), (319, self._im.size[1] - 643)
        )
        self._im.alpha_composite(
            self._get_image(PIC_DIR / "rainbow_bottom.png", size=(1200, 200), convert_rgba=True),
            (100, self._im.size[1] - 343),
        )
        pattern_bg = self._get_image(PIC_DIR / "pattern.png")
        for h in range((self._im.size[1] // 358) + 1):
            self._im.alpha_composite(pattern_bg, (0, (358 + 7) * h))

    def _get_rise_bg(self, level_index: int) -> Image.Image:
        rise_paths = [
            PIC_DIR / "rise_score_basic.png",
            PIC_DIR / "rise_score_advanced.png",
            PIC_DIR / "rise_score_expert.png",
            PIC_DIR / "rise_score_master.png",
            PIC_DIR / "rise_score_remaster.png",
        ]
        return self._get_image(rise_paths[level_index])

    def draw_scorelist(
        self, player_info: PlayerMaiInfo, scores: List[PlayerMaiScore], title: str, page: int = 1, page_size: int = 50
    ) -> Image.Image:
        """
        绘制分页成绩列表

        :param player_info: 玩家信息
        :param scores: 成绩列表
        :param title: 标题
        :param page: 当前页码
        :param page_size: 每个页码展示的成绩长度
        :return: 绘制后的图片
        """
        self.reset_im()
        self._draw_score_background()

        all_clear_rank = find_all_clear_rank(scores)
        self.draw_profile(player_info, all_clear_rank)

        # Draw title
        self._im.alpha_composite(self.title_lengthen_bg, (475, 200))
        if len(title) < 12:
            self._sy.draw(700, 245, 28, title, self.text_color, "mm")
        else:
            self._sy.draw(700, 245, 22, title, self.text_color, "mm")

        scores = scores[(page - 1) * page_size : page * page_size]
        self.whiledraw(scores, 320)

        self.draw_footer()

        return self._im

    def whilerisepic(self, datas: List[RecommendSong], low_score: int, isdx: bool):
        """
        循环绘制上分推荐数据
        """
        scale = 1.3

        def sv(v: int) -> int:
            return int(round(v * scale))

        y = sv(120)
        for index, data in enumerate(datas):
            x = sv(550) if isdx else sv(50)
            y += sv(150) if index != 0 else 0

            rise_bg = self._get_rise_bg(data.level_index)
            rise_bg = rise_bg.resize((sv(rise_bg.size[0]), sv(rise_bg.size[1])))
            self._im.alpha_composite(rise_bg, (x + sv(30), y))

            # Cover
            cover_path = COVER_DIR / f"{data.song_id}.png"
            if not cover_path.exists():
                cover_path = COVER_DIR / f"{data.song_id + 10000}.png"

            if not cover_path.exists():
                # Fallback or handle missing cover
                cover = Image.new("RGBA", (sv(80), sv(80)), (0, 0, 0, 0))
            else:
                cover = Image.open(cover_path).resize((sv(80), sv(80)))

            self._im.alpha_composite(cover, (x + sv(55), y + sv(40)))

            # Song info
            title = data.title
            if coloum_width(title) > 26:
                title = change_column_width(title, 25) + "..."
            self._sy.draw(x + sv(142), y + sv(44), sv(17), title, self.t_color[data.level_index], "lm")
            self._tb.draw(x + sv(55), y + sv(130), sv(12), f"ID: {data.song_id}", self.id_color[data.level_index], "lm")
            self._im.alpha_composite(
                Image.open(PIC_DIR / f'{"DX" if data.type == "dx" else "SD"}.png').resize((sv(30), sv(11))),
                (x + sv(105), y + sv(125)),
            )

            # Score
            self._tb.draw(
                x + sv(210),
                y + sv(81),
                sv(27),
                f"{data.old_achievements:.4f}%",
                self.t_color[data.level_index],
                anchor="mm",
            )
            self._tb.draw(
                x + sv(375),
                y + sv(81),
                sv(27),
                f"{data.target_achievements:.4f}%",
                self.t_color[data.level_index],
                anchor="mm",
            )

            increase_ra = data.target_dx_rating - low_score

            self._tb.draw(
                x + sv(150),
                y + sv(124),
                sv(18),
                f"Diff {data.difficulty_value:.1f}({data.difficulty_value_fit:.2f})",
                self.id_color[data.level_index],
                "lm",
            )
            self._tb.draw(
                x + sv(360),
                y + sv(124),
                sv(18),
                f"Ra {data.target_dx_rating}(+{increase_ra})",
                self.id_color[data.level_index],
                "lm",
            )

    def draw_rise(self, songs: RecommendSongs, min_dx_rating: int) -> Image.Image:
        """
        绘制上分数据表
        """
        self.reset_im()

        title_bg = self.title_lengthen_bg.copy().resize((450, 100))
        self._im.alpha_composite(title_bg, (150, 30))
        self._sy.draw(375, 75, 30, "旧版本谱面推荐", self.text_color, "mm")
        self.whilerisepic(songs.old_version, min_dx_rating, False)
        self._im.alpha_composite(title_bg, (825, 30))
        self._sy.draw(1050, 75, 30, "新版本谱面推荐", self.text_color, "mm")
        self.whilerisepic(songs.new_version, min_dx_rating, True)

        self.draw_footer()
        return self._im
