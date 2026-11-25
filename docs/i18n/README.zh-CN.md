# invest-diy

[English](../../README.md) | **简体中文**

一个基于公开数据的自托管行情看板工具箱。每个工具负责抓取数据、计算指标，并通过本地服务器提供中英双语网页；公开工具可导出为静态快照，本地工具不进入公开发布目录。

在线快照：<https://invest-diy.surge.sh/>

> 本项目所有内容都是对公开信息的整理，不构成投资建议。

## 工具

| 工具 | 可见范围 | 做什么 |
|---|---|---|
| [金融大事日历](../tools/financial-calendar.md) | 公开工具 | 以每行一周的完整月历展示本月及之后三个月的标普 500、纳斯达克 100、恒生指数与沪深 300 成份公司财报，以及美国就业与通胀数据、美联储议息会议和英伟达与黄仁勋的国会与调查事件，提供美东与北京时间。 |
| [PE 估值速算](../tools/pe-calculator.md) | 公开工具 | 分阶段设置利润增速与利润可分配比例，单独设置长期比例及股权风险溢价，比较不同无风险利率下的当前合理 PE。完全在浏览器计算，支持逐年明细和 CSV 导出。 |
| [公司业绩预测](../tools/company-profit.md) | 公开工具 | 支持紫金矿业、洛阳钼业和中国海洋石油的产量指引、价格与成本调整、敏感性分析和历史回测。洛阳钼业覆盖六种金属及磷肥。宁德时代按动力和储能电池的销量与单位毛利（元/Wh）测算归母净利润。 |
| [A股国家队宽基ETF数据跟踪](../tools/ashare-track-national-team-etf.md) | 公开工具 | 用交易所每日公布的 ETF 份额，推算"国家队"（中央汇金、中证金融等）重仓宽基 ETF 的每日净申赎，识别进出场波段；由基金定期报告推出其减持的硬下界；并回测一个"每晚估计国家队仓位、次日跟上"的策略。 |
| [中国央行黄金储备数据跟踪](../tools/cn-track-pboc-gold.md) | 公开工具 | 按月跟踪中国人民银行的官方黄金储备，数据从 1977 年起（近年取国家外汇管理局月度表，更早的历史取 IMF 数据），包括持有量（吨 / 盎司）、每月增持、连续增持月数与增持阶段，以及黄金储备的价值和占官方储备的比例。 |
| [中国锂电池排产数据跟踪](../tools/cn-track-battery-schedule.md) | 仅本地 | 按月跟踪中国大陆与宁德时代锂电池排产，保留来源披露的下限、修订值及原文链接。 |
| [全球航运指数数据跟踪](../tools/global-track-container-freight.md) | 本地工具（[原因与风险](../tools/global-track-container-freight.md#why-this-tool-is-not-published)） | 跟踪 SSE 全部 24 个航运指数栏目及分项，覆盖集装箱、散货、油轮、准班率、航贸与海员薪酬，展示最新发布期、单位及各数据源的更新状态。 |
| [全球黄金数据跟踪](../tools/global-track-gold.md) | 仅本地 | 对比全球黄金估算市值与美债规模，跟踪月度金油比、金银比，展示年度黄金需求分类柱状图，以及18个主要经济体的黄金持有量、增减和储备占比。 |
| [全球铜市场数据跟踪](../tools/global-track-copper.md) | 本地工具 | 比较 COMEX、LME、上期所铜价、库存与溢价，查看全球年度供需及铜矿地图，展示矿山状态与确认日期、所属公司和披露产量。 |
| [美国宏观经济数据跟踪](../tools/us-track-macro.md) | 公开工具 | 按月跟踪 CPI、最终需求 PPI、PCE 价格、失业率、非农就业总人数与新增就业，以及联邦基金有效利率；支持独立图表范围与 CSV 下载。 |

## 特点

- **无框架、无构建步骤**：标准库 Python HTTP 服务器 + 纯 HTML / JavaScript 页面
- **前端完全本地化**：图表使用随项目附带的 d3，页面不从任何 CDN 加载资源
- **页面中英双语**：每个页面都带中英文文案，按浏览器语言自动选择，顶栏可手动切换
- **静态导出**：一条命令仅导出明确标记为公开的工具，本地工具的页面和数据不进入发布目录
- **工具即插即用**：一个工具就是一个带元数据和 `web/` 目录的 Python 子包，首页按 `investdiy/server.py` 中 `HOME_TOOLS` 列表的顺序展示工具

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
- 工具：[全球黄金数据跟踪](../tools/global-track-gold.md)、[A股国家队宽基ETF数据跟踪](../tools/ashare-track-national-team-etf.md)、[中国央行黄金储备数据跟踪](../tools/cn-track-pboc-gold.md)、[全球航运指数数据跟踪](../tools/global-track-container-freight.md)、[全球铜市场数据跟踪](../tools/global-track-copper.md)、[PE 估值速算](../tools/pe-calculator.md)、[公司业绩预测](../tools/company-profit.md)

## 参与贡献

欢迎提 Issue 和 Pull Request。动手前请先读[开发指南](../development.md)：新页面必须中英双语，不能从 CDN 加载第三方脚本。

## 免责声明

数据来自公开渠道（证券交易所、基金定期报告、官方统计、行情服务商），可能存在错误、遗漏或延迟。"国家队买入"之类的归因都是基于公开数据的推断，并非官方确认。本项目的任何内容都不构成投资建议。

仓库本身不包含任何行情数据，每个工具运行时才从原始数据源抓取。转发或公开抓取到的数据前，请先确认各数据源的使用条款。

## 第三方软件

- [d3](https://d3js.org/) v7.9.0，随项目附带于 `investdiy/web/static/vendor/`，ISC 许可证（见 `investdiy/web/static/vendor/LICENSE-d3.txt`）

## 许可证

[MIT](../../LICENSE)
