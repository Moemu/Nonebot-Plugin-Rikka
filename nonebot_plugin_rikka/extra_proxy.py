from __future__ import annotations

import importlib
import inspect
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from nonebot import logger

DEV_MODULE_PATH = Path("./nonebot-plugin-rikka-extra")
if DEV_MODULE_PATH.exists():
    sys.path.insert(0, str(DEV_MODULE_PATH))


class ExtraNotInstalledError(RuntimeError):
    """Raised when nonebot-plugin-rikka-extra is not installed."""


class TitleServerEmptyResponseError(RuntimeError):
    """Raised when Title Server return an empty response, the bot server may have been blocked."""


def _load_extra_attr(module_name: str, attr: str) -> Any:
    try:
        mod = importlib.import_module(f"nonebot_plugin_rikka_extra.{module_name}")
    except ModuleNotFoundError as e:
        raise ExtraNotInstalledError("未安装 nonebot-plugin-rikka-extra") from e

    try:
        return getattr(mod, attr)
    except AttributeError as e:
        raise RuntimeError(f"nonebot-plugin-rikka-extra 缺少接口: {attr}") from e


async def _run_extra_function(func: Callable, *args):
    try:
        result = func(*args)
        if inspect.isawaitable(result):
            result = await result
    except AssertionError as exc:
        logger.error(exc)
        raise TitleServerEmptyResponseError("服务器返回空数据，可能 Bot 服务器被封锁，请联系管理员处理。")

    return result


async def run_extend_score_workflow(qr_code: str) -> list[dict[str, Any]]:
    """Proxy to nonebot-plugin-rikka-extra.score.run_workflow"""

    workflow = _load_extra_attr("score", "run_workflow")
    result = await _run_extra_function(workflow, qr_code)
    if not isinstance(result, list):
        raise RuntimeError("run_workflow 返回结果格式异常")
    return result


async def run_extend_ticket_workflow(qr_code: str) -> None:
    """Proxy to nonebot-plugin-rikka-extra.ticket.run_workflow"""

    workflow = _load_extra_attr("ticket", "run_workflow")
    result = workflow(qr_code)
    if inspect.isawaitable(result):
        await result


async def run_unlock_workflow(qr_code: str) -> None:
    """Proxy to nonebot-plugin-rikka-extra.unlock_all.run_workflow"""

    workflow = _load_extra_attr("unlock_all", "run_workflow")
    result = workflow(qr_code)
    if inspect.isawaitable(result):
        await result


async def run_divingfish_import_workflow(qr_code: str, import_token: str) -> None:
    """Proxy to nonebot-plugin-rikka-extra.Best50_To_Diving_Fish.run_workflow"""

    workflow = _load_extra_attr("convert", "run_workflow")
    result = workflow(qr_code, import_token)
    if inspect.isawaitable(result):
        await result


async def run_extent_force_logout(qr_code: str):
    func = _load_extra_attr("logout", "force_logout")
    result = func(qr_code)
    if inspect.isawaitable(result):
        await result


async def get_maistatus(
    *,
    title_ver: str = "1.51",
    initialize_payload: Optional[str] = None,
    timeout_seconds: float = 20.0,
) -> str:
    """Proxy to nonebot_plugin_rikka_extra.server_status.check_allnet_server_status.

    Returns a human-readable text summary, so callers don't need to care about
    extra package's dataclass shapes.
    """

    status = await _check_allnet_server_status_obj(
        title_ver=title_ver,
        initialize_payload=initialize_payload,
        timeout_seconds=timeout_seconds,
    )
    data = _status_obj_to_dict(status)
    return format_allnet_server_status(data)


_PACKAGE_KIND_TEXT = {
    "app": "本体/补丁",
    "opt": "选项包",
    "pack": "资源包",
}


def _fmt_size(value: Any) -> str:
    """复用 extra 包里的字节格式化，保证两边显示一致。"""
    human_size = _load_extra_attr("netdelivery", "human_size")
    return human_size(value)


async def get_update_event(
    *,
    title_ver: Optional[str] = None,
    timeout_seconds: float = 20.0,
) -> str:
    """Proxy to nonebot_plugin_rikka_extra.netdelivery.get_download_event.

    Returns a human-readable text summary, so callers don't need to care about
    extra package's dict shapes.
    """

    fetch = _load_extra_attr("netdelivery", "get_download_event")
    version_kwargs = {"title_ver": title_ver} if title_ver else {}
    event = await fetch(timeout_seconds=timeout_seconds, **version_kwargs)
    return format_update_event(event)


async def download_update_packages(
    *,
    title_ver: Optional[str] = None,
    timeout_seconds: float = 20.0,
) -> str:
    """Proxy to nonebot_plugin_rikka_extra.netdelivery.download_updates.

    Returns a human-readable text summary of every package's download result.
    """

    download = _load_extra_attr("netdelivery", "download_updates")
    version_kwargs = {"title_ver": title_ver} if title_ver else {}
    results = await download(timeout_seconds=timeout_seconds, **version_kwargs)
    return format_update_download(results)


def format_update_event(event: Mapping[str, Any]) -> str:
    """Format an update event dict into a human-readable summary."""

    meta = event.get("meta") or {}
    items = list(event.get("items") or [])

    lines = [f"舞萌DX 机台更新检测（{meta.get('title_ver', '?')}）"]

    for entry in meta.get("instructions") or []:
        name = entry.get("name") or entry.get("url", "?")
        if entry.get("status") != 200:
            lines.append(f"- 配信指示書 {name} 获取失败：{entry.get('error', '未知错误')}")
            continue
        common = entry.get("common") or {}
        release = common.get("RELEASE_TIME")
        desc = common.get("GAME_DESC") or "?"
        lines.append(f"- 配信指示書 {name}：{desc}" + (f"（配信时间 {release}）" if release else ""))

    if not items:
        lines.append("没有需要下载的更新包（本体与选项包均已是最新）。")
        return "\n".join(lines)

    lines.append(f"共 {len(items)} 个更新包，可用 `.netupdate download` 下载全部：")
    for item in items:
        size = item.get("size")
        size_text = _fmt_size(size) if size is not None else (item.get("note") or "大小未知")
        kind_text = _PACKAGE_KIND_TEXT.get(item.get("kind", "?"), "其他包")
        lines.append(f"  [{item.get('idx')}] {kind_text}｜{size_text}｜{item.get('name', '?')}")

    return "\n".join(lines)


def format_update_download(results: Sequence[Mapping[str, Any]]) -> str:
    """Format per-package download results into a human-readable summary."""

    if not results:
        return "没有需要下载的更新包（本体与选项包均已是最新）。"

    succeeded = [item for item in results if item.get("ok")]
    lines = [f"更新包下载完成：成功 {len(succeeded)} 个，失败 {len(results) - len(succeeded)} 个"]

    directories = {str(Path(str(item["path"])).parent) for item in results if item.get("path")}
    if len(directories) == 1:
        lines.append(f"保存目录：{directories.pop()}")

    for item in results:
        if item.get("ok"):
            lines.append(f"- ✅ {item.get('name', '?')}（{_fmt_size(item.get('size'))}）")
        else:
            lines.append(f"- ❌ {item.get('name', '?')}：{item.get('error', '未知错误')}")

    return "\n".join(lines)


async def _check_allnet_server_status_obj(
    *,
    title_ver: str,
    initialize_payload: Optional[str],
    timeout_seconds: float,
) -> Any:
    check_func = _load_extra_attr("server_status", "check_allnet_server_status")
    return await check_func(
        title_ver=title_ver,
        initialize_payload=initialize_payload,
        timeout_seconds=timeout_seconds,
    )


def _status_obj_to_dict(status: Any) -> dict[str, Any]:
    if hasattr(status, "to_dict"):
        data = status.to_dict()
        if isinstance(data, dict):
            return data

    if is_dataclass(status) and not isinstance(status, type):
        return asdict(status)

    if isinstance(status, dict):
        return dict(status)

    return {"value": status}


def _get_result_code(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(?:^|&)result=([^&\s]+)", text)
    return m.group(1) if m else None


def _fmt_elapsed_ms(value: Any) -> str:
    try:
        if value is None:
            return "-"
        return f"{float(value):.0f}ms"
    except Exception:
        return "-"


def format_allnet_server_status(status: Mapping[str, Any]) -> str:
    """Format server status dict into a human-readable summary."""

    overall_ok = bool(status.get("ok"))
    header = f"所有服务器状态: {'正常' if overall_ok else '异常'}"

    delivery = status.get("delivery") or {}
    init = status.get("initialize") or {}
    aime = status.get("aime") or {}
    title = status.get("title") or {}

    delivery_ok = bool(delivery.get("ok"))
    delivery_elapsed = _fmt_elapsed_ms(delivery.get("elapsed_ms"))
    # Hide low-level details like result codes by default.

    init_ok = bool(init.get("ok"))
    init_elapsed = _fmt_elapsed_ms(init.get("elapsed_ms"))
    # Hide low-level details like status_code/result by default.

    aime_ok = bool(aime.get("ok"))
    aime_elapsed = _fmt_elapsed_ms(aime.get("elapsed_ms"))

    title_ok = bool(title.get("ok"))
    title_elapsed = _fmt_elapsed_ms(title.get("elapsed_ms"))
    title_empty = bool(title.get("empty_response"))

    lines: list[str] = [header]

    delivery_line = f"- 舞萌更新服务(Net delivery): {'正常' if delivery_ok else '异常'} ({delivery_elapsed})"
    lines.append(delivery_line)

    init_line = f"- 机台启动服务(NET Initialize): {'正常' if init_ok else '异常'} ({init_elapsed})"
    lines.append(init_line)

    aime_line = f"- 舞萌登录服务(Chime): {'正常' if aime_ok else '异常'} ({aime_elapsed})"
    lines.append(aime_line)

    title_line = f"- 舞萌游戏服务(Title): {'正常' if title_ok else '异常'} ({title_elapsed})"
    if title_ok and title_empty:
        title_line += " | 空响应（可能是 Bot 所属服务器 IP 被限制请求）"
    elif not title_ok and title_elapsed > "5000ms":
        title_line += " | 响应超时"
    lines.append(title_line)

    return "\n".join(lines)
