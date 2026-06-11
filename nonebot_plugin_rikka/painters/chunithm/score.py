from typing import List

from PIL import Image

from ...score import PlayerChuInfo, PlayerChuScore
from ._base import ScoreBaseImage


class DrawChuScores(ScoreBaseImage):
    """
    绘制成绩列表图
    """

    def __init__(self, image: Image.Image | None = None) -> None:
        super().__init__(image)

        self.width = 1400
        self.height = 1600

        self._reset_im()

    def draw_scorelist(
        self, player_info: PlayerChuInfo, scores: List[PlayerChuScore], title: str, page: int = 1, page_size: int = 50
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
        self._reset_im()

        self._draw_header(player_info)

        scores = scores[(page - 1) * page_size : page * page_size]
        y = self.header_h + self.section_gap
        y = self._draw_section(y, title, scores, page_size, (40, 185, 110))

        self._draw_footer()

        return self._im
