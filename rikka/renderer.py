from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from nonebot import logger
from nonebot_plugin_htmlrender import template_to_pic
from typing_extensions import TypedDict

from .score import PlayerMaiB50, PlayerMaiInfo
from .utils.update_resources import download_icon, download_jacket


class ViewportDict(TypedDict):
    width: int
    height: int


class PicRenderer:
    def __init__(
        self,
        template_dir: str = "./rikka/templates",
        static_dir: str = "./static",
        default_width: int = 1400,
        default_height: int = 1600,
    ) -> None:
        """
        :param template_dir: 模板路径
        :param static_dir: Mai 静态文件路径
        """
        # 使用绝对路径，避免 Playwright 访问 file:// 相对目录时报错（ERR_FILE_NOT_FOUND）
        self.template_dir = str(Path(template_dir).resolve())
        self.static_dir = Path(static_dir)
        self.default_viewport = {"width": default_width, "height": default_height}

        self.env = Environment(loader=FileSystemLoader(self.template_dir), cache_size=400, auto_reload=False)

    async def _ensure_cover(self, song_id: int) -> str:
        """
        确保封面资源存在
        """
        cover = Path(self.static_dir / "mai" / "cover" / f"{song_id}.png")
        if cover.exists():
            return str(song_id)

        song_id += 10000
        dx_cover = Path(self.static_dir / "mai" / "cover" / f"{song_id}.png")
        if dx_cover.exists():
            return str(song_id)

        logger.warning(f"乐曲 {song_id} 的封面不存在!尝试从服务器下载...")
        try:
            await download_jacket(str(song_id))
            return str(song_id)
        except Exception as e:
            logger.error(f"下载乐曲 {song_id} 封面失败: {e}")

        return "0"  # 返回默认封面

    async def _ensure_avatar(self, avatar_id: int) -> bool:
        """
        确保头像资源存在
        """
        avatar = Path(self.static_dir / "mai" / "icon" / f"{avatar_id}.png")
        if avatar.exists():
            return True

        logger.warning(f"头像资源 {avatar_id} 不存在!尝试从服务器下载...")
        try:
            await download_icon(str(avatar_id))
        except Exception as e:
            logger.error(f"下载头像资源 {avatar_id} 失败: {e}")
            return False

        return True

    def _render_html(self, template_name: str, data: dict) -> str:
        """
        渲染 HTML
        """
        template = self.env.get_template(template_name)
        return template.render(data=data)

    async def _render_pic_by_plugin(
        self, template_name: str, data: dict, viewport: Optional[ViewportDict] = None
    ) -> bytes:
        """
        通过 `nonebot_plugin_htmlrender` 渲染模板
        """
        # 设定 base_url 到 pages 目录，使模板中以 "/static/..." 引用的资源能够解析到 pages/static 下
        repo_root = Path(__file__).resolve().parents[1]
        base_url = f"file://{repo_root.as_posix()}"
        pages = {"viewport": viewport or self.default_viewport, "base_url": base_url}
        # 将 base_href 提供给模板，用于 <base href>，让相对路径 static/... 指向 pages/static
        data_with_base = {**data, "base_href": base_url.rstrip("/") + "/"}
        return await template_to_pic(
            self.template_dir,
            template_name,
            data_with_base,
            pages=pages,
            wait=2,
        )

    async def render_mai_player_best50(self, player_best50: PlayerMaiB50, player_info: PlayerMaiInfo) -> bytes:
        """
        渲染玩家 Best50 信息
        """
        if player_info.icon:
            # await self._ensure_avatar(player_info.icon.id)
            avatar_url = f"https://assets2.lxns.net/maimai/icon/{player_info.icon.id}.png"
            # avatar = str(Path(self.static_dir / "mai" / "icon" / f"{player_info.icon.id}.png").absolute())
            # avatar_url = f"file://{avatar}"
        else:
            avatar_url = None

        data = {
            "player": {
                "name": player_info.name,
                "rating": player_info.rating,
                "class_rank": player_info.class_rank,
                "course_rank": player_info.course_rank,
                "avatar": avatar_url,
            },
            "best35": [
                {
                    "title": score.song_name,
                    "achievement": score.achievements,
                    "rank": score.rate.value,
                    "pc": 0,  # unsupported.
                    "difficulty": score.song_difficulty.name.lower(),
                    "level": score.song_level,
                    "level_value": 11.4,  # pending
                    "dx_rating": score.dx_rating,
                    "dx_star": score.dx_star,
                    "chartType": score.song_type.value.upper(),
                    "fc": score.fc.value if score.fc else None,
                    "fs": score.fs.value if score.fs else None,
                    "cover": await self._ensure_cover(score.song_id),
                }
                for score in player_best50.standard
            ],
            "best15": [
                {
                    "title": score.song_name,
                    "achievement": score.achievements,
                    "rank": score.rate.value,
                    "pc": 0,  # unsupported.
                    "difficulty": score.song_difficulty.name.lower(),
                    "level": score.song_level,
                    "level_value": 11.4,  # pending
                    "dx_rating": score.dx_rating,
                    "dx_star": score.dx_star,
                    "chartType": score.song_type.value.upper(),
                    "fc": score.fc.value if score.fc else None,
                    "fs": score.fs.value if score.fs else None,
                    "cover": self._ensure_cover(score.song_id),
                }
                for score in player_best50.dx
            ],
        }

        return await self._render_pic_by_plugin("PlayerMaiBest50.jinja2", data)
