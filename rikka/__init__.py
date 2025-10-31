from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_orm")
require("nonebot_plugin_htmlrender")

from nonebot.plugin import PluginMetadata, inherit_supported_adapters  # noqa: E402

from .config import Config  # noqa: E402
from .utils.utils import init_logger  # noqa: E402

init_logger()

from . import alconna  # noqa: E402, F401
from . import database  # noqa: E402, F401

__plugin_meta__ = PluginMetadata(
    name="Nonebot-Plugin-Rikka",
    description="None yet.",
    usage="不知道喵",
    type="application",
    config=Config,
    homepage="https://bot.snowy.moe/",
    extra={},
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)
