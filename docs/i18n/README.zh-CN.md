# invest-diy

[English](../../README.md) | **简体中文**

一个基于公开数据的自托管行情看板工具箱。每个工具负责抓取数据、计算指标，并通过本地服务器提供中英双语网页；整个站点也可以导出为静态快照。

在线快照：<https://invest-diy.surge.sh/>

> 本项目所有内容都是对公开信息的整理，不构成投资建议。

## 工具

| 工具 | 做什么 |
|---|---|
| [A股国家队宽基ETF数据跟踪](../tools/ashare-track-national-team-etf.md) | 用交易所每日公布的 ETF 份额，推算"国家队"（中央汇金、中证金融等）重仓宽基 ETF 的每日净申赎，识别进出场波段；由基金定期报告推出其减持的硬下界；并回测一个"每晚估计国家队仓位、次日跟上"的策略。 |

## 特点

- **无框架、无构建步骤**：标准库 Python HTTP 服务器 + 纯 HTML / JavaScript 页面
- **前端完全本地化**：图表使用随项目附带的 d3，页面不从任何 CDN 加载资源
- **页面中英双语**：每个页面都带中英文文案，按浏览器语言自动选择，顶栏可手动切换
- **静态导出**：一条命令把整站导出为静态文件，任何静态托管都能直接部署
- **工具即插即用**：一个工具就是一个带元数据和 `web/` 目录的 Python 子包，主页自动发现

## 快速开始

需要 Python 3.10 及以上。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python3 -m investdiy.ashare_track_national_team_etf   # 抓取数据并计算（首次约 10 分钟）
.venv/bin/python3 -m investdiy.server                            # 打开 http://localhost:8765/
```

## 目录结构

```
invest-diy/
├── investdiy/
│   ├── server.py        本地 HTTP 服务器
│   ├── registry.py      发现各工具子包
│   ├── export.py        静态导出
│   ├── common/          共享 Python 模块（HTTP、CSV、行情、基金定期报告）
│   ├── web/             主页与共享前端资源
│   └── <tool>/          每个工具一个子包
└── docs/                详细文档
```

## 文档

详细文档目前只有英文版：

- [架构](../architecture.md)：服务器、工具发现、前端组件、静态导出
- [开发指南](../development.md)：环境、约定、新增工具、静态导出
- 工具：[A股国家队宽基ETF数据跟踪](../tools/ashare-track-national-team-etf.md)

## 参与贡献

欢迎提 Issue 和 Pull Request。动手前请先读[开发指南](../development.md)：新页面必须中英双语，不能从 CDN 加载第三方脚本。

## 免责声明

数据来自公开渠道（证券交易所、基金定期报告、行情服务商），可能存在错误、遗漏或延迟。"国家队买入"之类的归因都是基于公开数据的推断，并非官方确认。本项目的任何内容都不构成投资建议。

仓库本身不包含任何行情数据，每个工具运行时才从原始数据源抓取。转发或公开抓取到的数据前，请先确认各数据源的使用条款。

## 第三方软件

- [d3](https://d3js.org/) v7.9.0，随项目附带于 `investdiy/web/static/vendor/`，ISC 许可证（见 `investdiy/web/static/vendor/LICENSE-d3.txt`）

## 许可证

[MIT](../../LICENSE)
