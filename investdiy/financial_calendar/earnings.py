"""Collect market-local reporting dates for the calendar's four equity indices."""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

from requests import RequestException

from ..common import net

OUT = Path(__file__).parent / "data/out/earnings.json"
INDICES = {
    "sp500": ("america", "SP:SPX", "America/New_York"),
    "ndx": ("america", "NASDAQ:NDX", "America/New_York"),
    "hsi": ("hongkong", "HSI:HSI", "Asia/Hong_Kong"),
    "csi300": ("china", "SSE:000300", "Asia/Shanghai"),
}
RANK = {"expected": 0, "scheduled": 1, "reported": 2}


def constituents(index):
    market, group, _ = INDICES[index]
    query = {
        "symbols": {"groups": [{"type": "index", "values": [group]}]},
        "options": {"lang": "en"},
        "columns": ["description", "earnings_release_date", "earnings_release_calendar_date",
                    "earnings_release_next_date", "earnings_release_next_calendar_date"],
        "range": [0, 2000],
    }
    result = net.post(f"https://scanner.tradingview.com/{market}/scan", json=query).json()
    rows = result["data"]
    if not rows or len({r["s"] for r in rows}) != len(rows) or len(rows) != result["totalCount"]:
        raise ValueError(f"Incomplete {group} constituent list")
    return rows


def appointments(symbols, since):
    # Query by fiscal period so a revised date outside the window also replaces an estimate inside it.
    codes = [s.split(":")[1] for s in symbols]
    for offset in range(0, len(codes), 60):
        securities = ",".join(f'"{code}"' for code in codes[offset:offset + 60])
        params = {
            "reportName": "RPT_PUBLIC_BS_APPOIN",
            "columns": "SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,APPOINT_PUBLISH_DATE,ACTUAL_PUBLISH_DATE",
            "filter": f"(REPORT_DATE>='{since}')(SECURITY_CODE in ({securities}))",
            "pageSize": 500, "pageNumber": 1, "sortColumns": "SECUCODE,REPORT_DATE", "sortTypes": "1,1",
        }
        while True:
            reply = net.get("https://datacenter-web.eastmoney.com/api/data/v1/get", params=params).json()
            if reply.get("code") == 9201 and reply.get("result") is None:
                break
            if not reply.get("success"):
                raise ValueError(f"Eastmoney disclosure calendar: {reply.get('message')}")
            result = reply["result"]
            yield from result["data"]
            if params["pageNumber"] >= result["pages"]:
                break
            params["pageNumber"] += 1


def quote_code(symbol):
    exchange, code = symbol.split(":")
    if exchange == "HKEX":
        return "hk" + code.zfill(5)
    return {"SSE": "sh", "SZSE": "sz"}.get(exchange, "us") + code


def chinese_names(symbols):
    lookup = {quote_code(s): s for s in symbols}
    codes = list(lookup)
    names = {}
    for offset in range(0, len(codes), 80):
        url = "https://qt.gtimg.cn/q=" + ",".join(codes[offset:offset + 80])
        try:
            response = net.get(url, timeout=8, retries=1)
        except RequestException as exc:
            print(f"Chinese name lookup unavailable: {exc}", file=sys.stderr)
            break
        for code, name in re.findall(r'v_([^=]+)="[^~"]*~([^~"]+)~', response.content.decode("gbk", errors="replace")):
            if code in lookup:
                names[lookup[code]] = name
    return names


def calendar_day(timestamp, zone):
    return datetime.fromtimestamp(timestamp, zone).date().isoformat() if timestamp else ""


def collect(today, previous):
    first = today.replace(day=1)
    start = first.isoformat()
    members, counts, reports = {}, {}, {}

    def record(symbol, period, day, status, agency):
        key = (symbol, period or day)
        # Prefer an actual release to an appointment and a published appointment to an estimate.
        if day and (key not in reports or RANK[status] >= RANK[reports[key]["status"]]):
            reports[key] = dict(start=day, period_end=period, status=status, agency=agency)

    for event in previous.get("events", []):
        if event["status"] == "reported" and event["start"] >= start:
            sources = event.get("reported_by", {symbol: event["agency"] for symbol in event["symbols"]})
            for symbol, agency in sources.items():
                record(symbol, event["period_end"], event["start"], "reported", agency)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, rows in zip(INDICES, pool.map(constituents, INDICES)):
            counts[index] = len(rows)
            zone = ZoneInfo(INDICES[index][2])
            for row in rows:
                symbol = row["s"]
                name, actual, actual_period, estimate, next_period = row["d"]
                if symbol in members:
                    members[symbol]["indices"].append(index)
                    continue
                members[symbol] = {"name": name or symbol, "indices": [index]}
                record(symbol, calendar_day(actual_period, timezone.utc), calendar_day(actual, zone), "reported", "TradingView")
                record(symbol, calendar_day(next_period, timezone.utc), calendar_day(estimate, zone), "expected", "TradingView")
    mainland = sorted(s for s, m in members.items() if "csi300" in m["indices"])
    names = {}
    for row in appointments(mainland, first.replace(year=first.year - 1)):
        code, exchange = row["SECUCODE"].split(".")
        symbol = {"SH": "SSE", "SZ": "SZSE"}.get(exchange, exchange) + ":" + code
        if symbol in members:
            names[symbol] = row["SECURITY_NAME_ABBR"]
            day = row["ACTUAL_PUBLISH_DATE"] or row["APPOINT_PUBLISH_DATE"]
            if not day:
                continue
            status = "reported" if row["ACTUAL_PUBLISH_DATE"] else "scheduled"
            record(symbol, row["REPORT_DATE"][:10], day[:10], status, "Eastmoney")

    current = [(symbol, report) for (symbol, _), report in reports.items()
               if symbol in members and report["start"] >= start]
    names.update(chinese_names(dict.fromkeys(symbol for symbol, _ in current if symbol not in names)))
    for old in previous.get("events", []):
        for symbol in old["symbols"]:
            names.setdefault(symbol, old["title_zh"])
    grouped = {}
    for symbol, report in current:
        name = re.sub(r" Class [A-Z]$", "", members[symbol]["name"])
        key = (name, report["period_end"] or symbol, report["start"])
        grouped.setdefault(key, {})[symbol] = report
    events = []
    for (name, _, day), listings in grouped.items():
        symbols = sorted(listings)
        primary = max(symbols, key=lambda s: (RANK[listings[s]["status"]], listings[s]["agency"] == "Eastmoney"))
        report = listings[primary]
        market, ticker = primary.split(":")
        url = (f"https://data.eastmoney.com/bbsj/stock/{ticker}.html" if report["agency"] == "Eastmoney"
               else f"https://www.tradingview.com/symbols/{market}-{ticker}/financials-earnings/")
        indices = list(dict.fromkeys(i for s in symbols for i in members[s]["indices"]))
        event = {**report, "series": "earnings", "end": day, "title_en": name, "title_zh": names.get(primary, name),
                 "symbols": symbols, "indices": indices, "url": url}
        if len(symbols) > 1 and report["status"] == "reported":
            event["reported_by"] = {s: r["agency"] for s, r in listings.items() if r["status"] == "reported"}
        events.append(event)
    return {"as_of": today.isoformat(), "counts": counts,
            "events": sorted(events, key=lambda r: (r["start"], r["title_en"]))}


def run():
    today = datetime.now(ZoneInfo("America/New_York")).date()
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    snapshot = collect(today, previous)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=OUT.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
            f.close()
            temp.replace(OUT)
        finally:
            temp.unlink(missing_ok=True)
    return len(snapshot["events"])


if __name__ == "__main__":
    print(f"Saved {run()} earnings events.")
