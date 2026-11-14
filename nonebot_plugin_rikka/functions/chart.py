"""谱面下载：从第三方谱面源拉取文件并打包为 adx。"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import httpx

ONECAT_BASE = "https://dw.moant.cn:34225"
SAOP_LIST_BASE = "https://adxdls.saop.cc/charts"
SAOP_MAIDATA_BASE = "https://adxdls.saop.cc/adxcs"

_SAOP_FILE_PATTERN = r"https://astrodx-charts\.saop\.cc/\d+/%s/(track\.mp3|bg\.png)"
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def _sanitize_filename(name: str) -> str:
    for char in _INVALID_FILENAME_CHARS:
        name = name.replace(char, "_")
    return name.strip().strip(".") or "unknown"


def _chart_cache_dir(music_id: str) -> Path:
    from nonebot_plugin_localstore import get_cache_dir

    path = Path(get_cache_dir("nonebot_plugin_rikka")) / "charts" / music_id
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _fetch_onecat(music_id: str) -> list[dict[str, object]] | None:
    """OneCat 源：返回文件列表；服务不可用或没有该曲时返回 None。"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            response = await client.get(
                f"{ONECAT_BASE}/api/chartFileList",
                params={"musicId": music_id, "bga": 0},
            )
            if response.status_code != 200:
                return None
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(data, dict) or not data.get("success"):
        return None
    files = [
        {
            "name": str(item.get("name") or "file"),
            "url": ONECAT_BASE + str(item.get("url")),
            "size": int(item.get("size", -1) or -1),
        }
        for item in data.get("files", [])
        if isinstance(item, dict) and item.get("url")
    ]
    return files or None


async def _fetch_saop(music_id: str) -> list[dict[str, object]] | None:
    """saop 源：解析列表页 HTML，拿 maidata / track / bg 的地址。"""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(f"{SAOP_LIST_BASE}/{music_id}")
            if response.status_code != 200:
                return None
            html = response.text
    except httpx.HTTPError:
        return None

    files: list[dict[str, object]] = [
        {
            "name": "maidata.txt",
            "url": f"{SAOP_MAIDATA_BASE}/{music_id}/maidata.txt",
            "size": -1,
        }
    ]
    seen: set[str] = set()
    for match in re.finditer(_SAOP_FILE_PATTERN % re.escape(music_id), html):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        files.append({"name": name, "url": match.group(0), "size": -1})
    return files


async def _download_files(files: list[dict[str, object]], cache_dir: Path, *, verify: bool) -> None:
    async with httpx.AsyncClient(verify=verify, timeout=120, follow_redirects=True) as client:
        for item in files:
            name = _sanitize_filename(str(item["name"]))
            target = cache_dir / name
            if target.is_file() and target.stat().st_size > 0:
                continue
            async with client.stream("GET", str(item["url"])) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"下载 {name} 失败：HTTP {response.status_code}")
                with target.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        handle.write(chunk)


def _read_title(cache_dir: Path, music_id: str) -> str:
    maidata = cache_dir / "maidata.txt"
    if maidata.is_file():
        for line in maidata.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("&title="):
                return line.split("=", 1)[1].strip() or f"乐曲{music_id}"
    return f"乐曲{music_id}"


def _make_archive(music_id: str, cache_dir: Path, title: str) -> Path:
    archive = cache_dir.parent / f"{_sanitize_filename(title)} ({music_id}).adx"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for item in sorted(cache_dir.iterdir()):
            if item.is_file():
                package.write(item, arcname=f"{music_id}/{item.name}")
    return archive


async def build_chart_archive(music_id: str) -> tuple[Path, str, str]:
    """下载指定乐曲的谱面并打包，返回 (adx 路径, 曲名, 来源)。"""
    if not music_id.isdigit():
        raise ValueError("乐曲 ID 必须是数字")

    cache_dir = _chart_cache_dir(music_id)
    files = await _fetch_onecat(music_id)
    source = "OneCat"
    verify = False
    if not files:
        files = await _fetch_saop(music_id)
        source = "saop"
        verify = True
    if not files:
        raise RuntimeError(f"没有找到谱面 {music_id}（OneCat / saop 均无结果）")

    await _download_files(files, cache_dir, verify=verify)
    title = _read_title(cache_dir, music_id)
    return _make_archive(music_id, cache_dir, title), title, source
