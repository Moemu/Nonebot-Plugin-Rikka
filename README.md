<div align=center>
  <img width=200 src="./assets/RikkaLogo.webp"  alt="image"/>
  <h1 align="center">Nonebot-Plugin-Rikka</h1>
  <p align="center">一个简单的 NoneBot2 舞萌查询成绩插件</p>
</div>
<div align=center>
  <a href="#关于️"><img src="https://img.shields.io/github/stars/Moemu/Nonebot-Plugin-Rikka" alt="Stars"></a>
  <!-- <a href="https://pypi.org/project/MuiceBot/"><img src="https://img.shields.io/pypi/v/Muicebot" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/MuiceBot/"><img src="https://img.shields.io/pypi/dm/Muicebot" alt="PyPI Downloads" ></a> -->
  <a href="https://nonebot.dev/"><img src="https://img.shields.io/badge/nonebot-2-red" alt="nonebot2"></a>
  <a href="#"><img src="https://img.shields.io/badge/Code%20Style-Black-121110.svg" alt="codestyle"></a>
</div>

## 介绍✨

基于 [Nonebot2](https://nonebot.dev/) 的舞萌DX的查分插件

看板娘: [Rikka](https://bot.snowy.moe/about/Rikka)

## 功能🪄

✅ 支持游戏: 舞萌DX(Ver.CN 1.5x), ~~中二节奏(Not Plan yet.)~~

✅ 支持数据源: [落雪咖啡屋(未绑定的首选)](https://maimai.lxns.net/), [水鱼查分器](https://www.diving-fish.com/maimaidx/prober/)

✅ 支持功能: Best50 ~~好像就只有这个?~~

## 指令列表🕹️

带有🚧标志的指令暂不可用或仍在开发中

| 指令                          | 说明                                                   |
| ----------------------------- | ------------------------------------------------------ |
| `.bind lxns|divingfish`       | [查分器相关]绑定游戏账号/查分器                        |
| `.b50`                        | [舞萌DX]生成玩家 Best50                                |
| `.minfo <id|别名>`            | [舞萌DX]获取乐曲信息                                   |
| `.alias add <song_id> <别名>` | [舞萌DX]添加乐曲别名（不会被 update 操作覆盖）         |
| `.alias update`               | [舞萌DX]从落雪查分器更新乐曲别名数据库                 |
| 🚧`.r50`                       | [舞萌DX]生成玩家 Recent 50（需绑定落雪查分器）         |
| 🚧`.ap50`                      | [舞萌DX]生成玩家 ALL PERFECT 50                        |
| 🚧`.score <id|别名>`           | [舞萌DX]获取玩家游玩该乐曲的成绩                       |
| 🚧`.trend`                     | [舞萌DX]获取玩家的 DX Rating 趋势 （需绑定落雪查分器） |

## 配置⚙️

### lxns_developer_api_key

- 说明: 落雪开发者密钥

- 类型: str

### static_resource_path

- 说明: 静态资源路径（类似于 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 的实现，你需要从 [此处](https://cloud.yuzuchan.moe/f/1bUn/Resource.7z) 获取游戏的资源文件，这将用于 Best 50 等的渲染）

- 类型: str

- 默认值: static

## 关于🎗️

本项目基于 [MIT License](https://github.com/Moemu/Nonebot-Plugin-Rikka/blob/main/LICENSE) 许可证提供，涉及到再分发时请保留许可文件的副本。

本项目的产生离不开下列开发者的支持，感谢你们的贡献：

![[Rikka 的贡献者们](https://github.com/eryajf/Moemu/Nonebot-Plugin-Rikka/contributors)](https://contrib.rocks/image?repo=Moemu/Nonebot-Plugin-Rikka)

本项目同样是 MuikaAI 的一部分

<a href="https://www.afdian.com/a/Moemu" target="_blank"><img src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.png" alt="afadian" style="height: 45px !important;width: 163px !important;"></a>

<!-- Star History：

[![Star History Chart](https://api.star-history.com/svg?repos=Moemu/MuiceBot&type=Date)](https://star-history.com/#Moemu/MuiceBot&Date) -->