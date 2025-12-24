from typing import List, Optional

from PIL import Image

from ..score import PlayerMaiInfo, PlayerMaiScore
from ._base import ScoreBaseImage
from ._config import PIC_DIR


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
        self.draw_profile(player_info)

        # Draw title
        self._im.alpha_composite(self.title_lengthen_bg, (475, 200))
        self._sy.draw(700, 245, 28, title, self.text_color, "mm")

        scores = scores[(page - 1) * page_size : page * page_size]
        self.whiledraw(scores, 320)

        self.draw_footer()

        return self._im
