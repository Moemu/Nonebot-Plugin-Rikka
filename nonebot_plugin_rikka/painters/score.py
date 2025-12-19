from typing import List, Optional

from PIL import Image

from ..score import PlayerMaiInfo, PlayerMaiScore
from ._base import ScoreBaseImage
from ._config import PIC_DIR


class DrawScore(ScoreBaseImage):
    """
    绘制成绩列表图
    """

    def __init__(self, image: Optional[Image.Image] = None) -> None:
        """
        初始化 DrawScore

        :param image: 基础图片对象
        """
        super().__init__(image)
        self.aurora_bg = Image.open(PIC_DIR / "aurora.png").convert("RGBA").resize((1400, 220))
        self.shines_bg = Image.open(PIC_DIR / "bg_shines.png").convert("RGBA")
        self.rainbow_bg = Image.open(PIC_DIR / "rainbow.png").convert("RGBA")
        self.rainbow_bottom_bg = Image.open(PIC_DIR / "rainbow_bottom.png").convert("RGBA").resize((1200, 200))
        self.pattern_bg = Image.open(PIC_DIR / "pattern.png")

        self._im.alpha_composite(self.aurora_bg)
        self._im.alpha_composite(self.shines_bg, (34, 0))
        self._im.alpha_composite(self.rainbow_bg, (319, self._im.size[1] - 643))
        self._im.alpha_composite(self.rainbow_bottom_bg, (100, self._im.size[1] - 343))
        for h in range((self._im.size[1] // 358) + 1):
            self._im.alpha_composite(self.pattern_bg, (0, (358 + 7) * h))

    def draw_scorelist(self, rating: str, data: List[PlayerMaiScore], page: int = 1, end_page: int = 1) -> Image.Image:
        """
        绘制分页成绩列表

        :param rating: 评分/定数描述
        :param data: 成绩列表
        :param page: 当前页码
        :param end_page: 总页码
        :return: 绘制后的图片
        """
        self._im.alpha_composite(self.title_lengthen_bg, (475, 30))
        self._sy.draw(700, 77, 28, rating, self.text_color, "mm")

        self.whiledraw(data)

        self._im.alpha_composite(self.design_bg, (200, self._im.size[1] - 113))
        self._sy.draw(700, self._im.size[1] - 70, 25, f"第 {page} / {end_page} 页", self.text_color, "mm")

        return self._im


def draw_score_list(player_info: PlayerMaiInfo, scores: List[PlayerMaiScore], title: str) -> Image.Image:
    """
    绘制成绩列表

    :param scores: 成绩列表
    :param title: 标题
    :return: 绘制后的图片
    """
    draw_score = DrawScore()

    draw_score.draw_profile(player_info)

    # Draw title
    draw_score._im.alpha_composite(draw_score.title_lengthen_bg, (475, 200))
    draw_score._sy.draw(700, 245, 28, title, draw_score.text_color, "mm")

    draw_score.whiledraw(scores, 320)

    draw_score.draw_footer()

    return draw_score._im
