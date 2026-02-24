<div align=center>
  <img width=200 src="./assets/RikkaLogo.webp"  alt="image"/>
  <h1 align="center">Nonebot-Plugin-Rikka</h1>
  <p align="center">一个简单的 NoneBot2 舞萌查询成绩插件</p>
</div>
<div align=center>
  <a href="#关于️"><img src="https://img.shields.io/github/stars/Moemu/Nonebot-Plugin-Rikka" alt="Stars"></a>
  <a href="https://pypi.org/project/Nonebot-Plugin-Rikka/"><img src="https://img.shields.io/pypi/v/Nonebot-Plugin-Rikka" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/Nonebot-Plugin-Rikka/"><img src="https://img.shields.io/pypi/dm/Nonebot-Plugin-Rikka" alt="PyPI Downloads" ></a>
  <a href="https://nonebot.dev/"><img src="https://img.shields.io/badge/nonebot-2-red" alt="nonebot2"></a>
  <a href="#"><img src="https://img.shields.io/badge/Code%20Style-Black-121110.svg" alt="codestyle"></a>
</div>

> [!NOTE]
>
> 本项目进入慢更新状态，但是您仍然可以提出新的特性请求

## 介绍✨

基于 [Nonebot2](https://nonebot.dev/) 的舞萌DX的查分插件

看板娘: [Rikka](https://bot.snowy.moe/about/Rikka)

## 功能🪄

✅ 支持游戏: 舞萌DX(Ver.CN 1.53+), ~~中二节奏(Not Plan yet.)~~

✅ 支持数据源: [落雪咖啡屋](https://maimai.lxns.net/), [水鱼查分器](https://www.diving-fish.com/maimaidx/prober/)

✅ 支持功能:
  - 基础查分功能：Best 50, Recent 50, 指定条件下的乐曲列表，牌子进度等...
  - 曲目信息查询：包括但不限于拟合系数和乐曲标签（乐曲标签需要额外配置实现）
  - 玄学功能实现：今日运势、计算推分推荐、玩家成分分析
  - 自定义成绩图：自定义背景图、字体等
  - 更新水鱼查分器

## 指令列表🕹️

带有🚧标志的指令暂不可用或仍在开发中

| 指令                                | 说明                                                   |
| ----------------------------------- | ------------------------------------------------------ |
| `.bind lxns\|divingfish`            | [查分器相关]绑定游戏账号/查分器                        |
| `.unbind lxns\|divingfish\|all`     | [查分器相关]解绑游戏账号/查分器                        |
| `.source lxns\|divingfish`          | [查分器相关]设置默认查分器                             |
| `.b50`                              | [舞萌DX]生成玩家 Best50                                |
| `.r50`                              | [舞萌DX]生成玩家 Recent 50（需绑定落雪查分器）         |
| `.n50`                              | [舞萌DX]获取玩家拟合系数 Top-50                        |
| `.ap50`                             | [舞萌DX]生成玩家 ALL PERFECT 50                        |
| `.pc50`                             | [舞萌DX]生成玩家游玩次数 Top50                         |
| `.minfo <id\|乐曲名称\|别名>`       | [舞萌DX]获取乐曲信息                                   |
| `.random`                           | [舞萌DX]随机获取一首乐曲                               |
| `.alias add <song_id> <别名>`       | [舞萌DX]添加乐曲别名（不会被 update 操作覆盖）         |
| `.alias update`                     | [舞萌DX]从落雪查分器更新乐曲别名数据库                 |
| `.alias query <id\|乐曲名称\|别名>` | [舞萌DX]查询该歌曲有什么别名                           |
| `.score <id\|乐曲名称\|别名>`       | [舞萌DX]获取玩家游玩该乐曲的成绩                       |
| `.scorelist <level\|achXX.X>`       | [舞萌DX]获取玩家对应等级/达成率的成绩列表              |
| `.update songs\|alias`              | [舞萌DX]更新乐曲或别名数据库                           |
| `.今日舞萌`                         | [舞萌DX]获取今日舞萌运势                               |
| `.成分分析`                         | [舞萌DX]获取基于 B100 的玩家成分分析                   |
| `.舞萌状态`                         | [舞萌DX]获取舞萌服务器状态                             |
| `.推分推荐`                         | [舞萌DX]生成随机推分曲目                               |
| `.trend`                            | [舞萌DX]获取玩家的 DX Rating 趋势 （需绑定落雪查分器） |
| `.import <玩家二维码>`              | [舞萌DX]导入玩家 PC 数信息                             |
| `.import divingfish <玩家二维码>`   | [舞萌DX]更新水鱼查分器                                 |

## 安装🪄

你需要一个 Nonebot 项目环境，参考：[快速上手](https://nonebot.dev/docs/quick-start)

1. 安装 `nonebot-plugin-rikka`:

  使用 `nb-cli` 安装(pending):

  ```shell
  nb plugin install nonebot-plugin-rikka
  ```

  使用包管理器安装：

  ```shell
  pip install nonebot-plugin-rikka
  ```

  在 NoneBot 的项目配置文件中追加：

  ```
  plugins = ["nonebot_plugin_rikka"]
  ```

2. 获取静态资源文件：
    本项目的渲染资源使用到了 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 提供到的文件。
    从 [私人云盘](https://cloud.yuzuchan.moe/f/1bUn/Resource.7z), [OneDrive](https://yuzuai-my.sharepoint.com/:u:/g/personal/yuzu_yuzuchan_moe/EdGUKRSo-VpHjT2noa_9EroBdFZci-tqWjVZzKZRTEeZkw?e=a1TM40) 中下载静态资源文件，并解压到机器人根目录下的 `static` 文件夹中。
    如果服务器更新了新歌但是本地不存在对应的资源文件时，插件会自动获取更新。参考第四小节。

3. 配置查分器开发者密钥，参考配置小节获取配置文件格式。你至少需要配置 [落雪咖啡屋(未绑定的首选)](https://maimai.lxns.net/), [水鱼查分器](https://www.diving-fish.com/maimaidx/prober/) 任意一个开发者密钥才可正常使用插件功能。

4. 运行 `python -m playwright install chromium` 来安装 playwright 浏览器环境，用于模拟浏览器请求游戏资源和获取舞萌状态页截图。

5. 启动 Nonebot 项目并根据提示运行数据库迁移脚本

6. 更新乐曲信息：
    使用 SUPERUSER 账号执行指令: `.update songs`（更新本地乐曲信息）, `.update alias`（更新乐曲别名）, `.update chart`（更新乐曲拟合系数等信息）。
    当服务器更新了新歌时建议再跑一次上面的三个指令。

7. （可选）如果需要支持乐曲标签，您需要自行获取来自 [DXRating](https://dxrating.net/search) 的 `combined_tags.json` 并放置在 `static` 文件夹中

## 配置⚙️

使用 `.env` 文件中配置以下内容

| 配置项                         | 说明                                                         | 类型                        | 默认值                                   |
| ------------------------------ | ------------------------------------------------------------ | --------------------------- | ---------------------------------------- |
| `add_alias_need_admin`         | 添加别名需要管理员权限                                       | `bool`                      | `True`                                   |
| `static_resource_path`         | 自定义静态资源路径（该目录下至少存在 `mai` 文件夹）          | `str`                       | `static`                                 |
| `lxns_developer_api_key`       | 落雪咖啡屋开发者密钥（两个开发者密钥二选一）                 | `Optional[str]`             | `None`                                   |
| `divingfish_developer_api_key` | 水鱼查分器开发者密钥                                         | `Optional[str]`             | `None`                                   |
| `enable_arcade_provider`       | 启用 Maimai.py 的机台源查询（需要将此值设置为 True 才可以查询 PC 数） | `bool`                      | `False`                                  |
| `maistatus_url`                | 舞萌状态页地址，用于渲染 `.maistatus`                        | `Optional[str]`             | `https://status.snowy.moe/status/maimai` |
| `scorelist_bg`                 | 成绩图背景，建议比例 8:7                                     | `Optional[str]`             | `None`                                   |
| `scorelist_font_main`          | 成绩图主字体文件                                             | `Optional[str]`             | `None`                                   |
| `scorelist_font_color`         | 成绩图默认文字颜色                                           | `tuple[int, int, int, int]` | `(124, 129, 255, 255)`                   |
| `scorelist_font_num`           | 成绩图数字字体文件                                           | `Optional[str]`             | `None`                                   |
| `scorelist_element_opacity`    | 成绩图元素不透明度（0.0 ~ 1.0）                              | `float`                     | `1.0`                                    |

有关 `enable_arcade_provider` 的说明: 部分功能需要连接至游戏服务器才可使用（比如 PC 数获取和水鱼查分器更新），但由于服务器对机房 IP 做出了限制，在部分网络环境下无法与官方服务器通信（使用 `.status` 命令以确认），因此此配置项默认为 `False` 并禁用相关功能。

## 关于🎗️

本项目基于 [MIT License](https://github.com/Moemu/Nonebot-Plugin-Rikka/blob/main/LICENSE) 许可证提供，涉及到再分发时请保留许可文件的副本。除此之外，另有 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 的许可证副本 [License](./nonebot_plugin_rikka/painters/LICENSE)

本项目的产生离不开下列开发者的支持，感谢你们的贡献：

![[Rikka 的贡献者们](https://github.com/eryajf/Moemu/Nonebot-Plugin-Rikka/contributors)](https://contrib.rocks/image?repo=Moemu/Nonebot-Plugin-Rikka)

本项目的渲染逻辑 ([painters](./nonebot_plugin_rikka/painters/)) 和资源修改或引用自 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX)，感谢上游项目的代码实现和游戏资源整理

本项目的分数查询功能基于 [TrueRou/maimai.py](https://github.com/TrueRou/maimai.py) 提供的框架进行开发。

本项目同样是 [MuikaAI](https://github.com/MuikaAI) 的一部分

<a href="https://www.afdian.com/a/Moemu" target="_blank"><img src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.png" alt="afadian" style="height: 45px !important;width: 163px !important;"></a>

免责声明：

部分服务需要连接至游戏服务器，开发者未使用软件逆向等数据和工具对任何游戏文件进行分析。本服务可能存在未知的逻辑错误，可能会导致潜在的风险如数据丢失、系统崩溃等，由用户自行决定是否下载、使用本服务。如果启用了 `enable_arcade_provider` 并使用了相关服务，则说明您已同意这一点。

Star History：

[![Star History Chart](https://api.star-history.com/svg?repos=Moemu/Nonebot-Plugin-Rikka&type=Date)](https://star-history.com/#Moemu/Nonebot-Plugin-Rikka&Date)