from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, field_validator


class Config(BaseModel):
    log_level: str = "debug"
    """日志等级"""
    add_alias_need_admin: bool = True
    """添加别名需要管理员权限"""
    static_resource_path: str = "static"
    """静态资源路径"""

    lxns_developer_api_key: str
    """落雪咖啡屋开发者密钥"""
    divingfish_developer_api_key: str
    """水鱼查分器开发者密钥"""

    @field_validator("static_resource_path")
    def validate_static_resource_path(cls, v: str) -> str:
        p = Path(v)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"资源文件夹: {v} 不存在！请下载静态资源文件或者重新配置静态资源文件路径")
        return str(p.resolve())


config = get_plugin_config(Config)
