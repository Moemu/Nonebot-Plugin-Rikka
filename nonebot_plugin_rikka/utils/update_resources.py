from functools import partial
from pathlib import Path

from aiohttp import ClientSession

_BASE_RESOURCE_URL = "https://assets2.lxns.net/maimai"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)


async def download_resource(
    file_id: str, file_type: str, postfix: str = ".png", save_dir: str = "./static/mai/cover"
) -> str:
    """
    下载游戏资源文件

    :param file_id: 资源文件 ID
    :param file_type: 资源文件类型，包括 `icon`, `plate`, `frame`, `jacket`, `music`
    :param postfix: 资源文件后缀，默认为 `.png`
    :param save_dir: 资源文件保存目录，默认为 `./static/mai/cover`
    """
    url = f"{_BASE_RESOURCE_URL}/{file_type}/{file_id}{postfix}"
    save_path = Path(save_dir) / f"{file_id}{postfix}"

    if save_path.exists():
        return str(save_path.resolve())

    async with ClientSession() as session:
        async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
            resp.raise_for_status()
            content = await resp.read()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(content)
            return str(save_path.resolve())


download_icon = partial(download_resource, file_type="icon", postfix=".png", save_dir="./static/mai/icon")
download_plate = partial(download_resource, file_type="plate", postfix=".png", save_dir="./static/mai/plate")
download_frame = partial(download_resource, file_type="frame", postfix=".png", save_dir="./static/mai/frame")
download_jacket = partial(download_resource, file_type="jacket", postfix=".png", save_dir="./static/mai/cover")
download_music = partial(download_resource, file_type="music", postfix=".mp3", save_dir="./static/mai/music")
