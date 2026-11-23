"""Build a source-linked history of published monthly schedules."""
from __future__ import annotations

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from ..common import csvio, net
from .sources import CATL_FOLLOWUPS, CATL_REPORTS, CITI_A_REPORT, MARKET_REPORTS, SINA_TD, TD_FEED, Report

OUTPUT = Path(__file__).parent / "data/out/monthly.csv"
FIELDS = ["month", "series", "gwh", "attribution", "qualifier", "previous_plan_gwh", "as_of", "source", "url",
          "prior_lfp_gwh", "lfp_gwh", "ncm_gwh", "followup_kind", "followup_mom_pct", "followup_as_of", "followup_url"]
NUMBER = r"(\d+(?:\.\d+)?)"


def observation(report, series, value, qualifier="estimate", previous="", month=None, attribution=None):
    if attribution is None:
        attribution = "named" if series == "catl" else ""
    return dict(month=month or report.month, series=series, gwh=value, attribution=attribution, qualifier=qualifier,
                previous_plan_gwh=previous, as_of=report.published, source=report.source, url=report.url)


def market_rows(report, body):
    year, month = map(int, report.month.split("-"))
    # Some releases state the year in the title and only the month in the body.
    period = rf"(?:{year}年|预计){month}月"
    total = (r"中国(?:锂电(?:全市场（储能\+动力\+消费）总排产|(?:（储能\+动力\+消费）)?市场排产总量)"
             r"|市场动力\+储能\+消费类电池排产量)约?")
    match = re.search(period + total + NUMBER + "GWh", body, re.I)
    if not match:
        raise ValueError(f"China market schedule missing in {report.url}")
    rows = [observation(report, "mainland", match[1])]
    # Older releases give producer volumes before the market total. Compilations quote several months.
    producer = r"锂电池A排产量" + NUMBER + "GWh"
    company = re.search(rf"{year}年{month}月中国电池厂动力\+储能产量[\d.]+GWh[；;，]" + producer, body, re.I)
    if not company:
        # The article summary may repeat the total without its producer breakdown.
        company = re.search(period + total + r"[\d.]+GWh(?:(?!\d+月)[^。]){0,160}。?" + producer, body, re.I)
    if company:
        rows.append(observation(report, "catl", company[1], attribution="survey_a"))
    revision = re.search(r"(\d{1,2})月中国锂电全市场实际总排产从上月报告的" + NUMBER +
                         r"GWh(?:下修|上修)至" + NUMBER + r"GWh(附近|左右)?", body, re.I)
    if revision:
        previous_month = 12 if month == 1 else month - 1
        if int(revision[1]) != previous_month:
            raise ValueError(f"Unexpected revision month in {report.url}")
        revised_period = f"{year - (month == 1)}-{previous_month:02d}"
        qualifier = "revised_approx" if revision[4] else "revised"
        rows.append(observation(report, "mainland", revision[3], qualifier, revision[2], revised_period))
    return rows


def catl_rows(report, body):
    year, month = map(int, report.month.split("-"))
    if "宁德时代" not in body and "CATL" not in body:
        raise ValueError(f"CATL attribution missing in {report.url}")
    if report.source == "datayes":
        match = re.search(rf"宁德时代排产确认{month}月[^。]*{year}年有效产能约{NUMBER}GWh[^。]*。"
                          rf"-?12月排产[\d.]+，{month}月排产{NUMBER}上修至{NUMBER}，", body, re.I)
        if match:
            return [observation(report, "catl", match[3], "revised", match[2])]
    elif report.source == "xq_survey" and "宁德时代（CATL）3月与4月排产" in body:
        period = rf"{year}年{month}月排产（[^）]+）-总排产：约{NUMBER}GWh"
        if month == 2:
            period = rf"{year}年3月排产（已执行）-总排产：约[\d.]+GWh-环比（2月约{NUMBER}GWh"
        match = re.search(period, body, re.I)
        if match:
            return [observation(report, "catl", match[1])]
    elif report.source == "citi_ze":
        match = re.search(r"CATL一家[^。]+。逐月排产[^：]+：8月" + NUMBER + r"GWh（7月才" +
                          NUMBER + r"GWh），9月" + NUMBER + r"GWh，10月和11月双双站上" + NUMBER + "GWh", body, re.I)
        if match:
            group = {7: 2, 8: 1, 9: 3, 10: 4, 11: 4}[month]
            return [observation(report, "catl", match[group])]
    elif report.source == "autosupplier":
        match = re.search(rf"宁德时代将{year}年{month}月产量计划由月初的{NUMBER}GWh"
                          rf"（{NUMBER}GWh三元\+{NUMBER}GWh磷酸铁锂）(?:下调|上调)至{NUMBER}GWh"
                          rf"（{NUMBER}GWh三元\+{NUMBER}GWh磷酸铁锂）", body, re.I)
        if match:
            prior, prior_ncm, prior_lfp, total, ncm, lfp = map(Decimal, match.groups())
            if prior != prior_ncm + prior_lfp or total != ncm + lfp or prior_ncm != ncm:
                raise ValueError(f"Unexpected CATL chemistry breakdown in {report.url}")
            row = observation(report, "catl", match[4], "revised", match[1])
            row.update(prior_lfp_gwh=match[3], lfp_gwh=match[6], ncm_gwh=match[5])
            return [row]
    elif report.source == "caiwen":
        match = re.search(rf"宁德时代（300750\.SZ）[^。]*。{month}月排产首次突破{NUMBER}GWh", body, re.I)
        if match:
            return [observation(report, "catl", match[1], "above")]
    elif report.source == "soochow":
        match = re.search(rf"公司{month}月排产环比提升，预期在{NUMBER}GWh\+", body, re.I)
        if match:
            return [observation(report, "catl", match[1], "at_least")]
    raise ValueError(f"Named CATL schedule missing in {report.url}")


def citi_a_rows(report, body):
    match = re.search(r"图注匿名化处理为A公司）8月排产从" + NUMBER + "GWh升到" + NUMBER + "GWh", body, re.I)
    if not match:
        raise ValueError(f"Company A forecast missing in {report.url}")
    rows = [observation(report, "catl", value, month=month, attribution="citi_a")
            for month, value in zip(("2026-07", "2026-08"), match.groups())]
    # The source prints chemistry only in an image. Optional local transcriptions are checked against its totals.
    figure = Path(__file__).parent / "data/in/citi_20260727_figure1.csv"
    components = {r["month"]: r for r in csvio.read_rows(figure)}
    for row in rows:
        if row["month"] in components:
            split = components[row["month"]]
            lfp, ncm = Decimal(split["lfp_gwh"]), Decimal(split["ncm_gwh"])
            if min(lfp, ncm) < 0 or lfp + ncm != Decimal(row["gwh"]):
                raise ValueError(f"Chemistry does not add up for {row['month']} in {figure}")
            row.update(lfp_gwh=split["lfp_gwh"], ncm_gwh=split["ncm_gwh"])
    return rows


def report_body(url):
    response = net.get(url)
    charset = re.search(rb'charset=["\']?([\w-]+)', response.content[:5000], re.I)
    encoding = charset[1].decode() if charset else (response.apparent_encoding or "utf-8")
    body = unescape(re.sub(r"<[^>]+>", "", response.content.decode(encoding, errors="replace")))
    return re.sub(r"\s+", "", body)


def followup_fields(report, body):
    fields = dict(followup_as_of=report.published, followup_url=report.url)
    if report.source == "guandian":
        match = re.search(r"宁德时代（HK3750）9月月产量环比下跌" + NUMBER + "%，10月月产量或大致持平", body)
        if match:
            return dict(fields, followup_kind="mom_decline", followup_mom_pct="-" + match[1])
    if report.source == "timeweekly" and "已下调2026年10月电池产量" in body:
        if re.search(r"该行下调宁德时代[（(]03750[）)][^。]*的产量管道预测", body):
            return dict(fields, followup_kind="cut")
    raise ValueError(f"Company-specific follow-up missing in {report.url}")


def fetch_rows(reports):
    body = report_body(reports[0].url)
    rows = []
    for report in reports:
        if report == CITI_A_REPORT:
            rows.extend(citi_a_rows(report, body))
        elif report in CATL_REPORTS:
            rows.extend(catl_rows(report, body))
        else:
            rows.extend(market_rows(report, body))
    return rows


def recent_market_reports():
    # The author's feed rolls over. Keep archive links so a clean checkout can backfill.
    reports = []
    for page in (1, 2):
        result = net.get(TD_FEED, params={"author_id": "7504351895", "num": 50, "page": page}).json()["result"]
        if result["status"]["code"] != 0 or (page == 1 and not result["data"]):
            raise ValueError("TD author feed is unavailable")
        for item in result["data"]:
            title = re.search(r"(20\d\d)年(1[0-2]|[1-9])月中国电池排产", item["title"])
            if title:
                url = item["url"].replace("http://", "https://", 1)
                if not url.startswith(SINA_TD):
                    raise ValueError(f"Unexpected TD article URL {url}")
                published = datetime.fromtimestamp(int(item["ctime"]), timezone(timedelta(hours=8))).date()
                reports.append(Report(f"{title[1]}-{int(title[2]):02d}", published.isoformat(), "td", url))
        if len(result["data"]) < 50:
            break
    return reports


def update():
    # All source reads must succeed before replacing the last working snapshot.
    net.ensure_resolvable(urlsplit(TD_FEED).hostname)
    reports = defaultdict(list)
    for report in dict.fromkeys((*MARKET_REPORTS, *CATL_REPORTS, CITI_A_REPORT, *recent_market_reports())):
        reports[report.url].append(report)
    urls = [*reports, *(r.url for r in CATL_FOLLOWUPS)]
    history = {}
    for row in csvio.read_rows(OUTPUT):
        row.setdefault("attribution", "named" if row["series"] == "catl" else "")
        history[row["series"], row["month"], row["attribution"]] = row
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(net.ensure_resolvable, sorted({urlsplit(url).hostname for url in urls})))
        for rows in pool.map(fetch_rows, reports.values()):
            for row in rows:
                key = row["series"], row["month"], row["attribution"]
                if key not in history or row["as_of"] >= history[key]["as_of"]:
                    history[key] = row
        for report, body in zip(CATL_FOLLOWUPS, pool.map(report_body, [r.url for r in CATL_FOLLOWUPS])):
            fields = followup_fields(report, body)
            row = history["catl", report.month, "named"]
            if report.published >= row["as_of"]:
                row.update(fields)
    rows = sorted(history.values(), key=lambda r: (r["as_of"], r["month"]), reverse=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=OUTPUT.parent) as stage:
        snapshot = Path(stage) / OUTPUT.name
        csvio.write_rows(snapshot, rows, FIELDS)
        snapshot.replace(OUTPUT)
    for series in ("mainland", "catl"):
        months = sorted({r["month"] for r in rows if r["series"] == series})
        print(f"{series}: {len(months)} reported months, {months[0]} to {months[-1]}")


if __name__ == "__main__":
    update()
