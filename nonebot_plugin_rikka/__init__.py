from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_orm")

from nonebot.plugin import PluginMetadata, inherit_supported_adapters  # noqa: E402

from .config import Config  # noqa: E402
from .utils import init_logger  # noqa: E402

init_logger()

from nonebot import get_driver  # noqa: E402
from nonebot_plugin_orm import get_scoped_session  # noqa: E402

from . import alconna  # noqa: E402, F401
from . import database  # noqa: E402, F401
from .database import MaiSongORM  # noqa: E402


@get_driver().on_startup
async def initialize_song_cache():
    session = get_scoped_session()
    await MaiSongORM.refresh_cache(session)


__plugin_meta__ = PluginMetadata(
    name="Nonebot-Plugin-Rikka",
    description="一个简单的舞萌成绩查询Bot插件",
    usage="使用 `.rikka` 查看指令用法",
    type="application",
    config=Config,
    homepage="https://bot.snowy.moe/",
    extra={},
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)
