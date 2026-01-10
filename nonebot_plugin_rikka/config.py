from pathlib import Path
from typing import Optional

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    log_level: str = "debug"
    """日志等级"""
    add_alias_need_admin: bool = True
    """添加别名需要管理员权限"""
    static_resource_path: str = "static"
    """静态资源路径"""

    lxns_developer_api_key: str
    """落雪咖啡屋开发者密钥"""
    divingfish_developer_api_key: Optional[str] = None
    """水鱼查分器开发者密钥"""

    enable_arcade_provider: bool = False
    """启用 Maimai.py 的机台源查询"""
    arcade_provider_http_proxy: Optional[str] = None
    """机台源的代理地址"""

    maistatus_url: Optional[str] = None
    """舞萌状态页地址，用于渲染 .maistatus """

    scorelist_bg: Optional[str] = None
    """成绩图背景，建议比例 8:7"""
    scorelist_font_main: Optional[str] = None
    """成绩图主字体文件"""
    scorelist_font_color: tuple[int, int, int, int] = (124, 129, 255, 255)
    """成绩图默认文字颜色"""
    scorelist_font_num: Optional[str] = None
    """成绩图数字字体文件"""
    scorelist_element_opacity: float = Field(1.0, le=1.0, ge=0.0)
    """成绩图元素不透明度"""

    @field_validator("static_resource_path")
    def validate_static_resource_path(cls, v: str) -> str:
        p = Path(v)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"资源文件夹: {v} 不存在！请下载静态资源文件或者重新配置静态资源文件路径")
        return str(p.resolve())


config = get_plugin_config(Config)
