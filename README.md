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

> [!WARNING]
>
> 欢迎来到本项目！目前此项目尚处于开发早期，因此运行时可能会频繁遇到问题，作为一个开发新人，我在此提前跟大家表示歉意！
>
> 由于本项目是 Owner 的练手项目，待实现的功能还有很多，因此近期没有也可能永远也不会有**发布**正式版或商店的打算。

## 介绍✨

基于 [Nonebot2](https://nonebot.dev/) 的舞萌DX的查分插件

看板娘: [Rikka](https://bot.snowy.moe/about/Rikka)

## 功能🪄

✅ 支持游戏: 舞萌DX(Ver.CN 1.5x), ~~中二节奏(Not Plan yet.)~~

✅ 支持数据源: [落雪咖啡屋(未绑定的首选)](https://maimai.lxns.net/), [水鱼查分器](https://www.diving-fish.com/maimaidx/prober/)

✅ 支持功能: 基础查分功能、拟合系数查询

## 指令列表🕹️

带有🚧标志的指令暂不可用或仍在开发中

| 指令                                | 说明                                                   |
| ----------------------------------- | ------------------------------------------------------ |
| `.bind lxns\|divingfish`            | [查分器相关]绑定游戏账号/查分器                        |
| `.unbind lxns\|divingfish\|all`    | [查分器相关]解绑游戏账号/查分器                        |
| `.b50`                              | [舞萌DX]生成玩家 Best50                                |
| `.r50`                              | [舞萌DX]生成玩家 Recent 50（需绑定落雪查分器）         |
| `.ap50`                             | [舞萌DX]生成玩家 ALL PERFECT 50                        |
| `.minfo <id\|乐曲名称\|别名>`       | [舞萌DX]获取乐曲信息                                   |
| `.alias add <song_id> <别名>`       | [舞萌DX]添加乐曲别名（不会被 update 操作覆盖）         |
| `.alias update`                     | [舞萌DX]从落雪查分器更新乐曲别名数据库                 |
| `.alias query <id\|乐曲名称\|别名>` | [舞萌DX]查询该歌曲有什么别名                           |
| `.score <id\|乐曲名称\|别名>`       | [舞萌DX]获取玩家游玩该乐曲的成绩                       |
| `.scorelist <level\|achXX.X>`      | [舞萌DX]获取玩家对应等级/达成率的成绩列表              |
| `.update maisong\|alias`                  | [舞萌DX]更新乐曲或别名数据库                     |
| 🚧`.trend`                           | [舞萌DX]获取玩家的 DX Rating 趋势 （需绑定落雪查分器） |


## 安装🪄

你需要一个 Nonebot 项目环境，参考：[快速上手](https://nonebot.dev/docs/quick-start)

1. 安装 `nonebot-plugin-rikka`:

  - 使用源代码安装：

    定位到插件目录，执行：

    ```bash
    git clone https://github.com/Moemu/Nonebot-Plugin-Rikka
    cd Nonebot-Plugin-Rikka
    pip install .
    ```

2. 获取资源文件：

  下载静态资源文件，并解压到 `static` 目录中: [私人云盘](https://cloud.yuzuchan.moe/f/1bUn/Resource.7z), [OneDrive](https://yuzuai-my.sharepoint.com/:u:/g/personal/yuzu_yuzuchan_moe/EdGUKRSo-VpHjT2noa_9EroBdFZci-tqWjVZzKZRTEeZkw?e=a1TM40)

3. 配置查分器开发者密钥，参考配置小节。

4. 启动 Nonebot 项目并根据提示运行数据库迁移脚本

5. 更新乐曲信息：使用 SUPERUSER 账号执行指令: `.update maisong` 和 `.alias update`

## 配置⚙️

使用 `.env` 文件中配置以下内容

### lxns_developer_api_key

- 说明: 落雪开发者密钥

- 类型: str

### divingfish_developer_api_key

- 说明: 水鱼查分器开发者密钥

- 类型: Optional[str]

- 默认值: None

### static_resource_path

- 说明: 静态资源路径（类似于 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 的实现，你需要从 [此处](https://cloud.yuzuchan.moe/f/1bUn/Resource.7z) 获取游戏的资源文件，这将用于 Best 50 等的渲染）

- 类型: str

- 默认值: static

## 关于🎗️

本项目基于 [MIT License](https://github.com/Moemu/Nonebot-Plugin-Rikka/blob/main/LICENSE) 许可证提供，涉及到再分发时请保留许可文件的副本。

本项目的产生离不开下列开发者的支持，感谢你们的贡献：

![[Rikka 的贡献者们](https://github.com/eryajf/Moemu/Nonebot-Plugin-Rikka/contributors)](https://contrib.rocks/image?repo=Moemu/Nonebot-Plugin-Rikka)

本项目同样是 [MuikaAI](https://github.com/MuikaAI) 的一部分

<a href="https://www.afdian.com/a/Moemu" target="_blank"><img src="https://pic1.afdiancdn.com/static/img/welcome/button-sponsorme.png" alt="afadian" style="height: 45px !important;width: 163px !important;"></a>

<!-- Star History：

[![Star History Chart](https://api.star-history.com/svg?repos=Moemu/MuiceBot&type=Date)](https://star-history.com/#Moemu/MuiceBot&Date) -->