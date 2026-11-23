# 锂电池月度排产数据获取 SOP

[打开本地跟踪页](http://localhost:8765/cn-track-battery-schedule/) · [English](../tools/cn-track-battery-schedule.md)

1. **确定月份与来源。** 从 2025 年 1 月逐月核对，分别记录排产所属月份和报道发布日期。先按仓库数据更新流程检查 GitHub Actions 覆盖情况，本工具目前在本地采集。[仓库更新流程](../development.md#data-update-sop)
2. **查中国大陆。** 先找大东时代智库、广东省电池行业协会该月原文，再看次月报告有无修订。只取中国市场动力、储能、消费电池三类合计排产，单位为 GWh。原文难以取得时，用转载逐项核对年月、地区、类别及合计数；特别留意同一段里的全球总量和动力加储能小计。[2025 年 1 月原文](https://caifuhao.eastmoney.com/news/20250114144646919311280) · [2026 年 11 月原文及上月修订](https://cj.sina.com.cn/articles/view/7504351895/1bf4b529700102rrpq)
3. **查宁德时代。** 优先核对公司披露，其次采用点名公司的机构调研或有出处的公开报道。确认数值属于公司当月排产。个人发布的调研摘录在页面标明出处和原表可得性。按市场份额将月度调研的“锂电池 A”和花旗调研的“Company A”推定为宁德时代，并分别记录原始出处。图表优先取具名值，缺月依次取月度调研 A 厂、花旗 A 公司。明细保留同月各来源。仅有同比、环比、季度合计或装车量时留空。[2025 年 1 月排产上修纪要](https://m-robo.datayes.com/feed/detail?id=446338) · [花旗引则言咨询原文第 1 页](https://public.fxbaogao.com/report-image/2026/08/16/5611263-1.png)
4. **登记来源并处理修订。** 在 `investdiy/cn_track_battery_schedule/sources.py` 登记报道链接、发布日期、目标月份和来源。新格式补充提取规则。同一组、同一月份、同一归属口径采用日期较晚的报道。报道明确给出原计划时一并保留；“约”“超过”“至少”分别保留其含义。一篇报告给出多个月份时逐月登记。
5. **运行并复核。** 在仓库根目录执行下方命令。对照页面的已收录月数、月度明细及来源链接，抽查新增值、修订值和图表空档。采集失败时保留上次成功快照，修复来源后重跑。生成的 CSV 保存在工具目录的 `data/out/monthly.csv`，不纳入版本控制。

```bash
.venv/bin/python3 -m investdiy.cn_track_battery_schedule
.venv/bin/python3 -m unittest discover -s tests -p test_battery_schedule.py
```
