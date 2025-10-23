import os
import sys
import time
from importlib.metadata import PackageNotFoundError, version

from nonebot import logger
from nonebot.log import default_filter, logger_id

from ..config import config


def init_logger():
    console_handler_level = config.log_level

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    log_file_path = f"{log_dir}/{time.strftime('%Y-%m-%d')}.log"

    # 移除 NoneBot 默认的日志处理器
    logger.remove(logger_id)
    # 添加新的日志处理器
    logger.add(
        sys.stdout,
        level=console_handler_level,
        diagnose=True,
        format="<lvl>[{level}] {function}: {message}</lvl>",
        filter=default_filter,
        colorize=True,
    )

    logger.add(
        log_file_path,
        level="DEBUG",
        format="[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {function}: {message}",
        encoding="utf-8",
        rotation="1 day",
        retention="7 days",
    )


def get_version() -> str:
    """
    获取当前版本号

    优先尝试从已安装包中获取版本号, 否则从 `pyproject.toml` 读取
    """
    package_name = "nonebot-plugin-rikka"

    try:
        return version(package_name)
    except PackageNotFoundError:
        pass

    toml_path = os.path.join(os.path.dirname(__file__), "../pyproject.toml")

    if not os.path.isfile(toml_path):
        return "Unknown"

    try:
        if sys.version_info >= (3, 11):
            import tomllib

            with open(toml_path, "rb") as f:
                pyproject_data = tomllib.load(f)

        else:
            import toml

            with open(toml_path, "r", encoding="utf-8") as f:
                pyproject_data = toml.load(f)

        # 返回版本号
        return pyproject_data["tool"]["pdm"]["version"]

    except (FileNotFoundError, KeyError, ModuleNotFoundError):
        return "Unknown"
