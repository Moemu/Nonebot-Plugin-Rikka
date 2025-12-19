from PIL import Image

from ..score import PlayerMaiB50, PlayerMaiInfo
from ._base import ScoreBaseImage
from ._config import PIC_DIR


class DrawBest(ScoreBaseImage):
    """
    绘制玩家 Best 50 成绩图
    """

    def __init__(self) -> None:
        """
        初始化 DrawBest
        """
        super().__init__(Image.open(PIC_DIR / "b50_bg.png").convert("RGBA"))

    def draw(self, player_info: PlayerMaiInfo, best50: PlayerMaiB50) -> Image.Image:
        """
        执行绘制操作

        :param player_info: 玩家信息
        :param best50: 玩家 Best 50 数据
        :return: 绘制完成的图片
        """
        self.draw_profile(player_info)

        # Calculate sum of ratings
        sd_rating = sum([s.dx_rating for s in best50.standard])
        dx_rating_sum = sum([s.dx_rating for s in best50.dx])

        rating_img = Image.open(PIC_DIR / "UI_CMN_Shougou_Rainbow.png").resize((270, 27))
        self._im.alpha_composite(rating_img, (435, 160))
        self._tb.draw(
            570,
            172,
            17,
            f"B35: {sd_rating} + B15: {dx_rating_sum} = {player_info.rating}",
            (0, 0, 0, 255),
            "mm",
            3,
            (255, 255, 255, 255),
        )

        self.whiledraw(best50.standard)
        self.whiledraw(best50.dx, 1085)

        self.draw_footer()

        return self._im
