import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from nonebot import logger
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from ...config import config
from ...database.crud import ChuSongORM
from ...score import PlayerChuInfo, PlayerChuScore
from ._config import (
    ACH_TO_IMAGE,
    COVER_DIR,
    DIFF_TO_FRAME,
    FONT_MAIN,
    FONT_NUM,
    FONT_TITLE,
    ICON_DIR,
    PIC_DIR,
    PLATE_DIR,
    RANK_TO_IMAGE,
    TROPHY_COLOR_INDEX,
    get_rating_color_name,
    score_to_rank,
)

GAP_X = 8  # horizontal gap between cards
GAP_Y = 8  # vertical gap between card rows


class ScoreBaseImage:
    _draw: ImageDraw.ImageDraw

    def __init__(self, image: Optional[Image.Image] = None) -> None:
        """
        初始化 ScoreBaseImage

        :param image: 可选的 PIL Image 对象，如果提供则在其上绘图
        """
        self._bg = image

        self.width = 1400
        self.height = 1800

        self.header_h = 240
        self.section_gap = 30
        self.section_pad_x = 28
        self.section_height = 44
        self.footer_h = 42

        self._col = 5
        self._card_width = (self.width - 2 * self.section_pad_x - (self._col - 1) * GAP_X) // self._col
        _card_width_orginal = 1060  # chu-frame 的有效内容宽度
        _card_width_height = 400
        scaling_radio = self._card_width / _card_width_orginal
        self._card_height = int(_card_width_height * scaling_radio)

        self._reset_im()

    @staticmethod
    @lru_cache(64)
    def _f(path: Path, size: int) -> ImageFont.FreeTypeFont:
        """
        使用 lru 缓存加载字体
        """
        return ImageFont.truetype(str(path), size, encoding="utf-8")

    @staticmethod
    @lru_cache(64)
    def _load_resources(path: Path) -> Image.Image:
        """
        使用 lru 缓存加载本地资源
        """
        return Image.open(path).convert("RGBA")

    @staticmethod
    def _trunc(text: str, max_px: int, font, draw) -> str:
        while text and draw.textlength(text, font=font) > max_px:
            text = text[:-1]
        return text

    @staticmethod
    def _score_str(s: int) -> str:
        return f"{s:,}"

    @staticmethod
    def _achievement_badge(score: PlayerChuScore) -> Optional[Image.Image]:
        """
        返回 fc 或 clear 微标
        """
        ach_badge: Optional[str] = None
        if score.full_combo:
            ach_badge = ACH_TO_IMAGE.get(score.full_combo.value, "fullcombo")
        # elif score.full_chain:
        #     ach_badge = ACH_TO_IMAGE.get(score.full_chain.value, "fullchain")
        elif score.clear:
            ach_badge = "clear.png"
        if ach_badge:
            badge_path = PIC_DIR / ach_badge
            return ScoreBaseImage._load_resources(badge_path)
        return None

    @staticmethod
    def _score_badge(score: PlayerChuScore) -> Image.Image:
        """
        返回评级微标
        """
        rank_str = score_to_rank(score.score)
        rank_idx = RANK_TO_IMAGE.get(rank_str, 0)
        rank_path = PIC_DIR / f"icon_rank_{rank_idx}.png"
        return ScoreBaseImage._load_resources(rank_path)

    @staticmethod
    def _get_song_level_value(score: PlayerChuScore) -> str:
        song_id = score.song_id
        song = ChuSongORM.get_song_sync(song_id)
        if not song:
            logger.warning(f"曲目 {song_id} 不存在乐曲对象！")
            return score.song_level
        diff = score.song_difficulty.value
        level_value = float(song.difficulties.difficulties[diff].level_value)
        return str(level_value)

    def _make_bg(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (16, 12, 28, 255))
        draw = ImageDraw.Draw(img)
        # Dot grid
        for gx in range(0, self.width, 30):
            for gy in range(0, self.height, 30):
                draw.ellipse((gx, gy, gx + 1, gy + 1), fill=(255, 255, 255, 16))
        # Diagonal lines top-right
        for i in range(0, 240, 24):
            draw.line([(self.width - 320 + i, 0), (self.width, 320 - i)], fill=(255, 255, 255, 8), width=1)
        return img

    def _reset_im(self):
        """重置当前图像内容为纯背景图"""
        if self._bg:
            self._im = self._bg
        elif config.scorelist_bg:
            self._im = Image.open(config.scorelist_bg).convert("RGBA").resize((self.width, self.height))
        else:
            self._im = self._make_bg()

        self._draw = ImageDraw.Draw(self._im)

    def _draw_header(self, player: PlayerChuInfo) -> None:
        # Player name card — use plate image directly as card canvas
        SCALING_FACTOR = 0.75  # 姓名框缩放比例
        plate_path = PLATE_DIR / f"{player.name_plate_id or 1}.png"
        if not plate_path.exists():
            plate_path = PLATE_DIR / "CHU_UI_NamePlate_00000001.png"  # 576*228(实际的图像存在较大间距)
        plate_raw = Image.open(plate_path).convert("RGBA")
        plate_size = [int(x * SCALING_FACTOR) for x in plate_raw.size]
        card = plate_raw.resize(plate_size, Resampling.LANCZOS)  # 75%

        # ── Character icon: bottom-right, 40% of card height ──
        icon_size = int(card.height * 0.40)
        icon_path = ICON_DIR / f"{player.character_id or 1}.png"
        if not icon_path.exists():
            icon_path = ICON_DIR / "CHU_UI_Character_0000_00_02.png.png"
        icon_raw = Image.open(icon_path).convert("RGBA")
        icon_disp = icon_raw.resize((icon_size, icon_size), Resampling.LANCZOS)
        icon_x, icon_y = 351, 64
        card.alpha_composite(icon_disp, (icon_x, icon_y))

        # ── Player info panel: draw text on top_panel, then paste onto card ──
        top_panel_path = PIC_DIR / "top_panel_background_restored.png"
        top_panel_raw = Image.open(top_panel_path).convert("RGBA")
        top_panel_size = [int(x * SCALING_FACTOR) for x in top_panel_raw.size]
        top_panel = top_panel_raw.resize(top_panel_size, Resampling.LANCZOS)
        PANEL_W, PANEL_H = top_panel.size

        # Line 1: Lv.XX  Name  (top 60% of panel)
        line1_h = int(PANEL_H * 0.6)
        line1_y = 13
        lv_font = self._f(FONT_MAIN, 13)
        lvn_font = self._f(FONT_MAIN, 20)
        nm_font = self._f(FONT_MAIN, 23)

        pd = ImageDraw.Draw(top_panel)
        lv_text = "Lv."
        lvn_text = str(player.level)
        lv_w = int(pd.textlength(lv_text, font=lv_font))
        lvn_w = int(pd.textlength(lvn_text, font=lvn_font))
        display_name = player.name
        name_text = self._trunc(display_name, PANEL_W - 12 - lv_w - lvn_w - 10, nm_font, pd)

        pd.text((12, line1_y + 10), lv_text, fill="black", font=lv_font)
        pd.text((12 + lv_w, line1_y + 3), lvn_text, fill="black", font=lvn_font)
        pd.text((12 + lv_w + lvn_w + 8, line1_y), name_text, fill="black", font=nm_font)

        # Line 2: RATING label image + digit images (bottom 40% of panel)
        line2_y = line1_h + 5
        rating_color = get_rating_color_name(player.rating)

        # Rating label image
        rating_label_path = PIC_DIR / f"rating_{rating_color}.png"
        if rating_label_path.exists():
            rating_label = Image.open(rating_label_path).convert("RGBA")
            rating_label = rating_label.resize((56, 13), Resampling.LANCZOS)
            top_panel.paste(rating_label, (8, line2_y + 3), rating_label)

        # Rating digit images (18×24 each)
        rating_str = f"{player.rating:.2f}"
        digit_x = 80
        digit_y = line2_y  # vertically center with label
        for ch in rating_str:
            fname = f"point_{rating_color}.png" if ch == "." else f"{ch}_{rating_color}.png"
            digit_path = PIC_DIR / fname
            if digit_path.exists():
                digit_img = Image.open(digit_path).convert("RGBA")
                digit_img = digit_img.resize((12, 16), Resampling.LANCZOS)
                top_panel.paste(digit_img, (digit_x, digit_y), digit_img)
            digit_x += 12

        place_panel_x = plate_size[0] - icon_size - top_panel_size[0] - int(plate_size[0] * 0.05)
        place_panel_y = icon_y + 3
        card.alpha_composite(top_panel, (place_panel_x, place_panel_y))

        # ── Trophy title bar (top of card, full width) ──
        cd = ImageDraw.Draw(card)
        trophy_x, trophy_y = 384, 36  # 50%
        if player.trophy:
            color_idx = TROPHY_COLOR_INDEX.get(player.trophy.color, 0)
            trophy_bg_path = PIC_DIR / f"CHU_UI_Trophy_{color_idx}.png"
            if not trophy_bg_path.exists():
                raise FileNotFoundError(f"称号背景文件 {trophy_bg_path} 不存在, 请检查资源文件路径")
            timg = Image.open(trophy_bg_path).convert("RGBA")
            timg = timg.resize((trophy_x, trophy_y), Resampling.LANCZOS)
            place_trophy_x = place_panel_x - 32
            place_trophy_y = place_panel_y - trophy_y + 3
            card.alpha_composite(timg, (place_trophy_x, place_trophy_y))

            trophy_font = self._f(FONT_MAIN, 12)
            name_w = cd.textlength(player.trophy.name, font=trophy_font)
            name_x = place_trophy_x + (trophy_x - int(name_w)) // 2
            name_y = place_trophy_y + (trophy_y - 16) // 2
            cd.text((name_x, name_y), player.trophy.name, fill=(0, 0, 0), font=trophy_font)

        # ── Paste card onto header ──
        # Place card centred vertically and 18px from the left in the header area.
        card_paste_x = 18
        card_paste_y = (self.header_h - card.height) // 2 + 30
        self._im.alpha_composite(card, (card_paste_x, card_paste_y))

        # ── Logo top-right ────────────────────────────────────────────
        logo_path = PIC_DIR / "chunithm_cn_2026.png"
        if logo_path.exists():
            logo_raw = Image.open(logo_path).convert("RGBA")
            logo_w, logo_h = 300, 300
            logo_img = logo_raw.resize((logo_w, logo_h), Resampling.LANCZOS)
            logo_x = self.width - logo_w - 20
            logo_y = (self.header_h - logo_h) // 2
            self._im.alpha_composite(logo_img, (logo_x, logo_y))

    def _draw_footer(self) -> None:
        fy = self.height - self.footer_h + 4
        # self._draw.line((14, fy, self.width - 14, fy), fill=(255, 255, 255, 25), width=1)
        font = self._f(FONT_NUM, 12)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._draw.text((18, fy + 12), ts, fill=(130, 120, 165), font=font)
        rt = "Powered By maimai.lxns.net / Generated By Rikka"
        rw = self._draw.textlength(rt, font=font)
        self._draw.text((self.width - rw - 18, fy + 12), rt, fill=(130, 120, 165), font=font)

    def _draw_score_card(self, score: PlayerChuScore, rank_num: int, x: int, y: int) -> None:
        # ── Frame background ──
        diff_val = score.song_difficulty.value
        frame_file = DIFF_TO_FRAME.get(diff_val, "chu-frame-0.png")
        frame_path = PIC_DIR / frame_file
        if not frame_path.exists():
            raise FileNotFoundError(f"未能找到 Chunithm 资源: {frame_path}, 请重新拉取存储库或更新 rikka 包体")

        frame_raw = Image.open(frame_path).convert("RGBA")

        border = 33
        frame_raw = frame_raw.crop((border, border, frame_raw.width - border, frame_raw.height - border))
        card = frame_raw.resize((self._card_width, self._card_height), Resampling.LANCZOS)
        cd = ImageDraw.Draw(card)

        scaling_factor = card.width / frame_raw.width
        cover_pad = int(32 * scaling_factor)
        cover_size = int(250 * scaling_factor)

        # ── Cover image (43×43) ──
        cp = COVER_DIR / f"{score.song_id}.png"
        if cp.exists():
            cover = Image.open(cp).convert("RGBA").resize((cover_size, cover_size), Resampling.LANCZOS)
        else:
            cover = Image.new("RGBA", (cover_size, cover_size), (48, 38, 68, 255))
        card.paste(cover, (cover_pad + 3, cover_pad), cover)

        # #N (right-top)
        idx_font = self._f(FONT_NUM, 7)
        idx_font_w = cd.textlength(f"#{rank_num}", idx_font)
        cd.text((card.width - idx_font_w - 3, 3), f"#{rank_num}", fill=(255, 255, 255), font=idx_font)

        row_start_x = cover_pad + cover_size + 8

        # ── Row 1: Song name ──
        name_font = self._f(FONT_MAIN, 13)
        max_name_w = self._card_width - row_start_x - 12
        trunc = self._trunc(score.song_name, max_name_w, name_font, cd)
        cd.text((row_start_x, 9), trunc, fill=(255, 255, 255), font=name_font)

        # Score
        score_font = self._f(FONT_NUM, 18)
        cd.text((row_start_x, 32), self._score_str(score.score), fill=(255, 255, 255), font=score_font)

        # Diff level + rating
        diff_font = self._f(FONT_MAIN, 11)
        song_diff = self._get_song_level_value(score)
        diff_txt = f"{song_diff} -> {score.rating:.2f}"
        cd.text((row_start_x + 1, 57), diff_txt, fill=(255, 255, 255), font=diff_font)

        bottom_data_y = int(321 * scaling_factor)

        # Song ID
        id_font = self._f(FONT_MAIN, 9)
        cd.text((cover_pad * 1.5, bottom_data_y + 3), f"ID {score.song_id}", fill=(0, 0, 0), font=id_font)

        # Rank badge
        rank_badge = self._score_badge(score)
        rank_badge = rank_badge.resize((48, 14), Resampling.LANCZOS)
        rank_badge_x = card.width - 2 - rank_badge.width
        card.paste(rank_badge, (rank_badge_x, bottom_data_y), rank_badge)

        # Achievement badge (bottom-right)
        ach_badge = self._achievement_badge(score)
        if ach_badge:
            ach_badge = ach_badge.resize((48, 14), Resampling.LANCZOS)
            ach_w = rank_badge_x - ach_badge.width - 6
            card.paste(ach_badge, (ach_w, bottom_data_y), ach_badge)

        self._im.alpha_composite(card, (x, y))

    def _draw_section_title(self, y: int, title: str, avg: float, accent: tuple) -> None:
        draw = ImageDraw.Draw(self._im)
        x0, x1 = self.section_pad_x, self.width - self.section_pad_x

        # Bar background (only title bar height)
        bar = Image.new("RGBA", (x1 - x0 + 1, self.section_height), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bar)
        bd.rounded_rectangle(
            (0, 0, x1 - x0, self.section_height - 1),
            radius=6,
            fill=(*accent, 205),
            outline=(*accent, 155),
            width=2,
        )
        self._im.alpha_composite(bar, (x0, y))

        # Left accent stripe
        draw.rounded_rectangle((x0, y, x0 + 7, y + self.section_height - 1), radius=3, fill=accent)

        # Title
        text_length = draw.textlength(title, self._f(FONT_TITLE, 21))
        title_x = (self._im.width - text_length) // 2
        draw.text((title_x, y + 4), title, fill=(255, 255, 255), font=self._f(FONT_TITLE, 21))

        # AVG
        avg_font = self._f(FONT_NUM, 18)
        avg_txt = f"AVG: {avg:.2f}"
        aw = draw.textlength(avg_txt, font=avg_font)
        draw.text((x1 - aw - 14, y + 15), avg_txt, fill=(255, 255, 255), font=avg_font)

    def _draw_section(self, y0: int, title: str, scores: list[PlayerChuScore], limit: int, accent: tuple) -> int:
        """Render one section. Returns y position immediately after."""
        avg = sum(s.rating for s in scores) / len(scores) if scores else 0.0
        self._draw_section_title(y0, title, avg, accent)

        grid_y = y0 + self.section_height + 4
        for idx, sc in enumerate(scores[:limit]):
            col = idx % self._col
            row = idx // self._col
            cx = self.section_pad_x + col * (self._card_width + GAP_X)
            cy = grid_y + row * (self._card_height + GAP_Y)
            self._draw_score_card(sc, idx + 1, cx, cy)

        rows = math.ceil(min(len(scores), limit) / self._col)
        return grid_y + rows * (self._card_height + GAP_Y)
