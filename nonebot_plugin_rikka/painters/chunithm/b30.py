"""
中二节奏 Best 30 + Selection 10 + New 20 绘图模块
"""

from PIL import Image

from ...score import PlayerChuBests, PlayerChuInfo
from ._base import ScoreBaseImage

SEC_B30_COLOR = (220, 60, 50)
SEC_S10_COLOR = (220, 150, 30)
SEC_N20_COLOR = (40, 185, 110)


class DrawChuBest(ScoreBaseImage):
    def draw(self, player_info: PlayerChuInfo, bests: PlayerChuBests) -> Image.Image:
        self._reset_im()

        self._draw_header(player_info)

        y = self.header_h + self.section_gap
        y = self._draw_section(y, "BEST 30", bests.bests, 30, SEC_B30_COLOR)
        y += self.section_gap
        y = self._draw_section(y, "SELECTION 10", bests.selections, 10, SEC_S10_COLOR)
        y += self.section_gap
        y = self._draw_section(y, "NEW 20", bests.new_bests, 20, SEC_N20_COLOR)

        self._draw_footer()

        return self._im
