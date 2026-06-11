from pathlib import Path
from typing import Literal, Optional

from nonebot import logger
from nonebot_plugin_orm import get_scoped_session
from typing_extensions import TypedDict

from .database.crud import MaiSongORM
from .models.song import MaiSong
from .painters.chunithm import DrawChuBest, DrawChuScores
from .painters.chunithm._config import COVER_DIR as CHU_COVER_DIR
from .painters.chunithm._config import ICON_DIR as CHU_ICON_DIR
from .painters.chunithm._config import PLATE_DIR as CHU_PLATE_DIR
from .painters.maimai import DrawBest, DrawScores, draw_music_info
from .painters.utils import image_to_bytes
from .score.chunithm import PlayerChuBests, PlayerChuInfo, PlayerChuScore
from .score.maimai import PlayerMaiB50, PlayerMaiInfo, PlayerMaiScore
from .updater.resources import (
    download_chu_icon,
    download_chu_jacket,
    download_chu_plate,
    download_mai_icon,
    download_mai_jacket,
    download_mai_plate,
)


class ViewportDict(TypedDict):
    width: int
    height: int


class MaiPicRenderer:
    def __init__(
        self,
        template_dir: Path = Path(__file__).parent / "templates",
        static_dir: str = "./static",
        default_width: int = 1400,
        default_height: int = 1600,
    ) -> None:
        """
        :param template_dir: 模板路径
        :param static_dir: Mai 静态文件路径
        """
        # 使用绝对路径，避免 Playwright 访问 file:// 相对目录时报错（ERR_FILE_NOT_FOUND）
        self.template_dir = str(template_dir.resolve())
        self.static_dir = Path(static_dir)
        self.default_viewport = {"width": default_width, "height": default_height}

        self.draw_best = DrawBest()
        self.draw_score = DrawScores()

    async def _ensure_cover(self, song_id: int) -> str:
        """
        确保封面资源存在

        :param song_id: 乐曲 id
        """
        if 10000 < song_id < 100000:
            song_id -= 10000
        elif song_id > 100000:
            song_id -= 100000

        cover = Path(self.static_dir / "mai" / "cover" / f"{song_id}.png")
        if cover.exists():
            return str(song_id)

        dx_song_id = song_id + 10000

        dx_cover = Path(self.static_dir / "mai" / "cover" / f"{dx_song_id}.png")
        if dx_cover.exists():
            return str(dx_song_id)

        logger.warning(f"乐曲 {song_id} 的封面不存在!尝试从服务器下载...")

        try:
            await download_mai_jacket(str(song_id))
            return str(song_id)
        except Exception as e:
            logger.error(f"下载乐曲 {song_id} 封面失败: {e}")

        return "0"  # 返回默认封面

    async def _validate_profile_resources(self, player_info: PlayerMaiInfo) -> bool:
        """确保玩家相关资源存在（头像/姓名框/背景框）。"""

        ok = True

        if player_info.icon:
            icon_id = player_info.icon.id
            icon_path = Path(self.static_dir / "mai" / "icon" / f"{icon_id}.png")
            if not icon_path.exists():
                logger.warning(f"头像资源 {icon_id} 不存在!尝试从服务器下载...")
                try:
                    await download_mai_icon(str(icon_id))
                except Exception as e:
                    logger.error(f"下载头像资源 {icon_id} 失败: {e}")
                    ok = False

        if player_info.name_plate:
            plate_id = player_info.name_plate.id
            plate_path = Path(self.static_dir / "mai" / "plate" / f"{plate_id}.png")
            if not plate_path.exists():
                logger.warning(f"姓名框资源 {plate_id} 不存在!尝试从服务器下载...")
                try:
                    await download_mai_plate(str(plate_id))
                except Exception as e:
                    logger.error(f"下载姓名框资源 {plate_id} 失败: {e}")
                    ok = False

        # if player_info.frame:
        #     frame_id = player_info.frame.id
        #     frame_path = Path(self.static_dir / "mai" / "frame" / f"{frame_id}.png")
        #     if not frame_path.exists():
        #         logger.warning(f"背景框资源 {frame_id} 不存在!尝试从服务器下载...")
        #         try:
        #             await download_frame(str(frame_id))
        #         except Exception as e:
        #             logger.error(f"下载背景框资源 {frame_id} 失败: {e}")
        #             ok = False

        return ok

    async def _get_song_level_value(
        self, song_id: int, song_type: Literal["standard", "dx", "utage"], difficulty: int
    ) -> float:
        """
        获取乐曲定数

        :param song_id: 乐曲 ID
        :param song_type: 铺面类型
        :param difficulty: 铺面难度
        """
        session = get_scoped_session()

        # DX 铺面
        if 10000 < song_id < 100000:
            song_id -= 10000

        song_info = await MaiSongORM.get_song_info(session, song_id)

        if song_type == "dx" and len(song_info.difficulties.dx) > difficulty:
            return song_info.difficulties.dx[difficulty].level_value
        elif song_type == "standard" and len(song_info.difficulties.standard) > difficulty:
            return song_info.difficulties.standard[difficulty].level_value
        elif song_type == "utage":
            return 0

        raise ValueError(f"请求的乐曲 {song_id}({song_type}) 中的难度 {difficulty} 不存在")

    async def render_mai_player_best50(
        self, player_best50: PlayerMaiB50, player_info: PlayerMaiInfo, calc_song_level_value: bool = True
    ) -> bytes:
        """
        渲染玩家 Best50 信息
        """
        # Ensure covers
        for score in player_best50.standard + player_best50.dx:
            await self._ensure_cover(score.song_id)
            if calc_song_level_value:
                score.song_level_value = await self._get_song_level_value(
                    score.song_id, score.song_type.value, score.song_difficulty.value  # type: ignore
                )

        # Ensure player assets
        await self._validate_profile_resources(player_info)

        draw_best = DrawBest()
        img = draw_best.draw(player_info, player_best50)
        return image_to_bytes(img)

    async def render_mai_player_scores(
        self, scores: list[PlayerMaiScore], player_info: PlayerMaiInfo, title: Optional[str] = None
    ) -> bytes:
        """
        渲染玩家具体成绩图
        """
        # Ensure player assets
        await self._validate_profile_resources(player_info)

        # Ensure covers
        for score in scores:
            await self._ensure_cover(score.song_id)
            score.song_level_value = await self._get_song_level_value(
                score.song_id, score.song_type.value, score.song_difficulty.value  # type: ignore
            )

        img = self.draw_score.draw_scorelist(player_info, scores, title or "Player Scores")
        return image_to_bytes(img)

    async def render_mai_player_song_info(self, song: MaiSong, scores: list[PlayerMaiScore]) -> bytes:
        """
        渲染单曲成绩详情图

        :param song: 乐曲对象
        :param scores: 该乐曲各难度成绩的列表
        """
        await self._ensure_cover(song.id)

        img = draw_music_info(song, scores)
        return image_to_bytes(img)


class ChuPicRenderer:
    def __init__(self, static_dir: str = "./static") -> None:
        self.static_dir = Path(static_dir)
        self.drawer_best = DrawChuBest()
        self.drawer_score = DrawChuScores()

    async def _ensure_cover(self, song_id: int) -> None:
        """确保中二节奏封面资源存在，不存在则从 LXNS 下载。"""
        cover = CHU_COVER_DIR / f"{song_id}.png"
        if cover.exists():
            return
        logger.warning(f"乐曲 {song_id} 封面不存在，尝试下载...")
        try:
            await download_chu_jacket(str(song_id))
        except Exception as e:
            logger.error(f"下载乐曲 {song_id} 封面失败: {e}")

    async def _validate_player_resources(self, player_info: PlayerChuInfo) -> None:
        """确保玩家相关资源存在（角色图标/称号）。"""
        if player_info.character_id:
            character_id = player_info.character_id
            icon = CHU_ICON_DIR / f"{character_id}.png"
            if not icon.exists():
                logger.warning(f"角色图标 {character_id} 不存在，尝试下载...")
                try:
                    await download_chu_icon(str(character_id))
                except Exception as e:
                    logger.error(f"下载角色图标 {character_id} 失败: {e}")
        if player_info.name_plate_id:
            plate_id = player_info.name_plate_id
            plate = CHU_PLATE_DIR / f"{plate_id}.png"
            if not plate.exists():
                logger.warning(f"名牌版 {plate_id} 不存在，尝试下载...")
                try:
                    await download_chu_plate(str(plate_id))
                except Exception as e:
                    logger.error(f"下载名牌版 {plate_id} 失败: {e}")

    async def render_chu_bests(self, player_info: PlayerChuInfo, bests: PlayerChuBests) -> bytes:
        """
        渲染中二节奏 Best 30 + Selection 10 + New 20

        :param player_info: 玩家信息
        :param bests: Best 30 + Selection 10 + New 20 数据
        :return: PNG 图片字节流
        """
        # 确保封面资源
        for score in bests.bests + bests.selections + bests.new_bests:
            await self._ensure_cover(score.song_id)

        # 确保玩家资源
        await self._validate_player_resources(player_info)

        img = self.drawer_best.draw(player_info, bests)
        return image_to_bytes(img)

    async def render_chu_player_scores(
        self, scores: list[PlayerChuScore], player_info: PlayerChuInfo, title: Optional[str] = None
    ) -> bytes:
        """
        渲染玩家具体成绩图
        """
        # Ensure player assets
        await self._validate_player_resources(player_info)

        # Ensure covers
        for score in scores:
            await self._ensure_cover(score.song_id)

        img = self.drawer_score.draw_scorelist(player_info, scores, title or "Player Scores")
        return image_to_bytes(img)
