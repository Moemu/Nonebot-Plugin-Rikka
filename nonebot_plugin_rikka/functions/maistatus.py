from __future__ import annotations

import asyncio
from typing import TypedDict

from nonebot import get_driver, logger

_driver = get_driver()

# Lazy singletons for Playwright/Chromium process reuse
_init_lock = asyncio.Lock()
_page_semaphore = asyncio.Semaphore(2)
_playwright = None
_browser = None


class Viewport(TypedDict):
    width: int
    height: int


async def _get_browser():
    """Get (and lazily initialize) a shared Chromium browser instance."""

    global _playwright, _browser

    async with _init_lock:
        if _browser is not None:
            try:
                if not _browser.is_closed():
                    return _browser
            except Exception:
                # Browser object may be in a bad state; fall through to re-init.
                _browser = None

        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "缺少依赖 playwright，无法截图。请安装 playwright 并执行 `python -m playwright install chromium`。"
            ) from exc

        if _playwright is None:
            _playwright = await async_playwright().start()

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        return _browser


async def _shutdown_browser():
    global _playwright, _browser

    async with _init_lock:
        if _browser is not None:
            try:
                await _browser.close()
            except Exception:
                pass
            _browser = None

        if _playwright is not None:
            try:
                await _playwright.stop()
            except Exception:
                pass
            _playwright = None


@_driver.on_shutdown
async def _on_shutdown():
    await _shutdown_browser()


async def capture_webpage_png(
    url: str,
    *,
    viewport: Viewport | None = None,
    full_page: bool = True,
    timeout_ms: int = 30_000,
    wait_ms: int = 500,
) -> bytes:
    """Capture a webpage screenshot as PNG bytes.

    Notes:
        - This relies on Playwright + Chromium.
        - If you see errors about missing browser executables, run:
          `python -m playwright install chromium`
    """

    try:
        from playwright.async_api import Error as PlaywrightError
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "缺少依赖 playwright，无法截图。请安装 playwright 并执行 `python -m playwright install chromium`。"
        ) from exc

    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError("url 必须以 http:// 或 https:// 开头")

    viewport = viewport or {"width": 1400, "height": 900}

    try:
        async with _page_semaphore:
            browser = await _get_browser()
            context = await browser.new_context(viewport=viewport)
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                if wait_ms > 0:
                    await page.wait_for_timeout(wait_ms)
                return await page.screenshot(type="png", full_page=full_page)
            finally:
                await context.close()
    except PlaywrightError as exc:
        logger.warning(f"Playwright 截图失败: {exc}")
        raise RuntimeError(
            "截图失败：Playwright/Chromium 运行异常。"
            "请确认已执行 `python -m playwright install chromium`，并且当前环境允许启动浏览器。"
        ) from exc


async def capture_maimai_status_png(maimai_status_url: str) -> bytes:
    """Capture maimai status page screenshot."""

    return await capture_webpage_png(
        maimai_status_url,
        viewport={"width": 1200, "height": 750},
        full_page=True,
        timeout_ms=30_000,
        wait_ms=800,
    )
