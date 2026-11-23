"""Reviewed article locations. Observations are extracted from the publications at update time."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Report:
    month: str
    published: str
    source: str
    url: str


EASTMONEY = "https://caifuhao.eastmoney.com/news/"
SINA_TD = "https://cj.sina.com.cn/articles/view/7504351895/"
TD_FEED = "https://search.cj.sina.cn/news/get_list_by_vuid"

SINA_ROLL = "https://finance.sina.com.cn/roll/"
SUMMER_REVIEW = "https://finance.sina.com.cn/wm/2025-10-22/doc-infuuprm0306767.shtml"

MARKET_REPORTS = (
    Report("2025-01", "2025-01-14", "td", EASTMONEY + "20250114144646919311280"),
    Report("2025-02", "2025-02-06", "gdbattery", SINA_ROLL + "2025-02-06/doc-ineipxuw1491913.shtml"),
    Report("2025-03", "2025-03-04", "gdbattery", SINA_ROLL + "2025-03-04/doc-inennutf9743064.shtml"),
    Report("2025-04", "2025-03-27", "survey_repost", "https://xueqiu.com/3002072056/329165611"),
    Report("2025-05", "2025-04-29", "survey_repost", "https://xueqiu.com/1334287437/333559186"),
    *(Report(f"2025-{month:02d}", "2025-10-22", "tiger", SUMMER_REVIEW) for month in (6, 7, 8)),
    Report("2025-09", "2025-09-02", "gdbattery", "https://finance.sina.cn/2025-09-02/detail-infpccsz6745453.d.html"),
    Report("2025-10", "2025-09-26", "gdbattery", SINA_ROLL + "2025-09-26/doc-infrvnmp6437000.shtml"),
    Report("2025-11", "2025-11-04", "td", EASTMONEY + "20251104135104420638020"),
    Report("2025-12", "2025-12-03", "td", EASTMONEY + "20251203134827751897280"),
    Report("2026-01", "2025-12-25", "td", "https://xueqiu.com/4964213805/367617350"),
    Report("2026-01", "2026-01-21", "aijian", "https://stock.stockstar.com/JC2026012100022077.shtml"),
    Report("2026-02", "2026-01-28", "td", EASTMONEY + "20260128160417363880780"),
    Report("2026-03", "2026-02-28", "td", EASTMONEY + "20260228160153277372640"),
    Report("2026-04", "2026-03-25", "td", EASTMONEY + "20260325150125576556700"),
    Report("2026-05", "2026-05-07", "cls", "https://cj.sina.com.cn/articles/view/2868676035/aafc85c302001qiji"),
    Report("2026-06", "2026-05-26", "td", EASTMONEY + "20260526102619313618470"),
    Report("2026-07", "2026-06-25", "hicend", "https://finance.sina.com.cn/wm/2026-06-25/doc-inieqsme2545580.shtml"),
    Report("2026-07", "2026-06-26", "mysteel", "https://news.mysteel.com/a/26062520/1CA773DD082238E8.html"),
    Report("2026-08", "2026-07-24", "td", SINA_TD + "1bf4b529700102pnyo"),
    Report("2026-09", "2026-08-26", "td", SINA_TD + "1bf4b529700102qmv8"),
    Report("2026-10", "2026-09-24", "td", SINA_TD + "1bf4b529700102rc1g"),
    Report("2026-11", "2026-10-23", "td", SINA_TD + "1bf4b529700102rrpq"),
)

# The company is named in each of these reports. Anonymous producer rankings are ambiguous.
CATL_REPORTS = (
    Report("2025-01", "2024-12-08", "datayes", "https://m-robo.datayes.com/feed/detail?id=446338"),
    *(Report(f"2026-{month:02d}", "2026-03-25", "xq_survey", "https://xueqiu.com/9265667347/380971967")
      for month in (2, 3, 4)),
    Report("2026-05", "2026-05-27", "caiwen", "https://finance.sina.com.cn/jjxw/2026-05-27/doc-inhzikrs0815512.shtml"),
    *(Report(f"2026-{month:02d}", "2026-08-18", "citi_ze", EASTMONEY + "20260818163314756031410")
      for month in range(7, 12)),
    Report("2026-10", "2026-10-07", "soochow", "https://www.jiuyangongshe.com/a/febd6272e7aa46fd8ae96c27c215bd22"),
    Report("2026-11", "2026-11-22", "autosupplier", "https://www.qcgys.com/show_article-97125.html"),
)

CATL_FOLLOWUPS = (
    Report("2026-09", "2026-09-18", "guandian", "https://www.guandian.cn/article/20260918/603598.html"),
    Report("2026-10", "2026-10-16", "timeweekly", "https://finance.sina.com.cn/jjxw/2026-10-16/doc-inivmazr8330052.shtml"),
)

# The July report gives July and August together in Figure 1.
CITI_A_REPORT = Report("2026-07", "2026-07-29", "citi_a",
                       "https://finance.sina.com.cn/stock/hkstock/marketalerts/2026-07-29/doc-inikmump1707351.shtml")
