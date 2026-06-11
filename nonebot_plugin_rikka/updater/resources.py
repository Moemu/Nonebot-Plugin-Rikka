from functools import partial
from pathlib import Path

from ..browser import get_browser, get_page_semaphore
from ..constants import USER_AGENT

_BASE_MAI_RESOURCE_URL = "https://assets2.lxns.net/maimai"
_BASE_CHUNITHM_RESOURCE_URL = "https://assets2.lxns.net/chunithm"


async def download_resource(
    file_id: str,
    file_type: str,
    postfix: str = ".png",
    save_dir: str = "./static/mai/cover",
    base_dir: str = _BASE_MAI_RESOURCE_URL,
) -> str:
    """
    下载游戏资源文件

    :param file_id: 资源文件 ID
    :param file_type: 资源文件类型，包括 `icon`, `plate`, `frame`, `jacket`, `music`, `trophy`
    :param postfix: 资源文件后缀，默认为 `.png`
    :param save_dir: 资源文件保存目录，默认为 `./static/mai/cover`
    :param base_dir: LXNS 资源路径
    """
    url = f"{base_dir}/{file_type}/{file_id}{postfix}"
    save_path = Path(save_dir) / f"{file_id}{postfix}"

    if save_path.exists():
        return str(save_path.resolve())

    page_semaphore = await get_page_semaphore()
    async with page_semaphore:
        browser = await get_browser()
        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-CN",
            extra_http_headers={
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
        try:
            page = await context.new_page()

            # 第一步：触发 challenge 页面
            # 等 domcontentloaded 即可——challenge 脚本同步写入 Cookie，
            # 发生在 DOMContentLoaded 之前，不需要等 setTimeout 的重定向
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # 快路径：服务器直接返回了图片（没有 challenge）
            if resp is not None:
                ct = resp.headers.get("content-type", "")
                if resp.status < 400 and ("image" in ct or "octet-stream" in ct):
                    content = await resp.body()
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_bytes(content)
                    return str(save_path.resolve())

            # 慢路径：challenge 已把 Cookie 写入 context，用 APIRequestContext 重新请求
            # context.request 自动携带浏览器上下文中的全部 Cookie（含 document.cookie 写入的）
            api_resp = await context.request.get(
                url,
                headers={"Accept": "image/*,*/*;q=0.8"},
                timeout=30_000,
            )

            if api_resp.status >= 400:
                raise RuntimeError(f"下载失败：HTTP {api_resp.status}")

            ct = api_resp.headers.get("content-type", "")
            if "html" in ct.lower():
                raise RuntimeError(f"下载失败：二次请求仍返回 HTML，Cookie Challenge 未通过（content-type: {ct}）")

            content = await api_resp.body()
            if not content:
                raise RuntimeError("下载失败：响应体为空")

        finally:
            await context.close()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(content)
    return str(save_path.resolve())


download_mai_icon = partial(download_resource, file_type="icon", postfix=".png", save_dir="./static/mai/icon")
download_mai_plate = partial(download_resource, file_type="plate", postfix=".png", save_dir="./static/mai/plate")
download_mai_frame = partial(download_resource, file_type="frame", postfix=".png", save_dir="./static/mai/frame")
download_mai_jacket = partial(download_resource, file_type="jacket", postfix=".png", save_dir="./static/mai/cover")
download_mai_music = partial(download_resource, file_type="music", postfix=".mp3", save_dir="./static/mai/music")

download_chu_jacket = partial(
    download_resource,
    file_type="jacket",
    postfix=".png",
    save_dir="./static/chu/cover",
    base_dir=_BASE_CHUNITHM_RESOURCE_URL,
)
download_chu_icon = partial(
    download_resource,
    file_type="character",
    postfix=".png",
    save_dir="./static/chu/icon",
    base_dir=_BASE_CHUNITHM_RESOURCE_URL,
)
download_chu_trophy = partial(
    download_resource,
    file_type="trophy",
    postfix=".png",
    save_dir="./static/chu/trophy",
    base_dir=_BASE_CHUNITHM_RESOURCE_URL,
)
download_chu_plate = partial(
    download_resource,
    file_type="plate",
    postfix=".png",
    save_dir="./static/chu/plate",
    base_dir=_BASE_CHUNITHM_RESOURCE_URL,
)
