from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    log_level: str = "debug"
    """日志等级"""

    lxns_developer_api_key: str
    """落雪咖啡屋开发者密钥"""


config = get_plugin_config(Config)
