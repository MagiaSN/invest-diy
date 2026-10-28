"""Fetch daily units and closing prices of the broad-based ETFs, appending incrementally to data/.

Sources (all free, no login):
  - SSE ETF size: query.sse.com.cn commonQuery, sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L
      returns the units of every Shanghai ETF for one STAT_DATE (TOT_VOL, in 10,000 units); needs a Referer;
      history goes back to 2015. The SEC_CODE filter is ignored, so whole days are fetched
  - SZSE fund size: www.szse.cn/api/report/ShowReport/data, CATALOGID=scsj_fund_jjgm
      daily units for one code (txtDm) over txtStart/txtEnd (current_size, in 10,000 units); at most 6 months
      per request and 20 rows per page. If szse.cn does not resolve, common.net.ensure_resolvable uses DoH
  - closing prices / index: Tencent fqkline (common.market)

Units on day T are the units after day T's creations and redemptions; the exchanges publish a preliminary
figure on the evening of T and the final one on the morning of T+1.

Usage:
  .venv/bin/python3 -m investdiy.ashare_track_national_team_etf.fetch            # incremental (default start 2015-01-05)
  .venv/bin/python3 -m investdiy.ashare_track_national_team_etf.fetch --start 2023-01-03
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

from ..common import market, net
from ..common.csvio import read_rows, write_rows
from .pool import CANDIDATES, INDEX_CODE

DATA = Path(__file__).resolve().parent / "data"
SSE_CSV = DATA / "sse_shares.csv"        # date,code,name,shares_wan (all Shanghai ETFs)
SZSE_CSV = DATA / "szse_shares.csv"      # date,code,name,shares_wan (candidate Shenzhen ETFs)
PRICE_CSV = DATA / "prices.csv"          # date,code,close (all candidate ETFs + index)

SHARE_FIELDS = ["date", "code", "name", "shares_wan"]
DEFAULT_START = "2015-01-05"  # first trading day of 2015; SSE ETF size data goes back to here
NONTRADING = DATA / "sse_nontrading.txt"   # weekdays confirmed to have no data (holidays), not queried again


# ---------------------------------------------------------------------------
# Prices (the index dates double as the trading calendar)
# ---------------------------------------------------------------------------

def update_prices(start: str, end: str) -> None:
    """Incremental: per code, fill only the missing head (before the earliest date held) and tail (refetch the last 5 days)."""
    rows = read_rows(PRICE_CSV)
    span: dict[str, list[str]] = {}
    for r in rows:
        lo, hi = span.get(r["code"], [r["date"], r["date"]])
        span[r["code"]] = [min(lo, r["date"]), max(hi, r["date"])]
    # fetch every candidate, not just the pool: holders.py builds the pool dynamically, so history is ready when an ETF joins
    jobs = []
    for code, idx in [(INDEX_CODE, True)] + [(e["code"], False) for e in CANDIDATES]:
        lo, hi = span.get(code, [None, None])
        if lo is None:
            jobs.append((code, idx, start, end))
            continue
        if lo > start:  # head: there is no data before listing, so only fill clear gaps (>15 days)
            if (datetime.strptime(lo, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days > 15:
                jobs.append((code, idx, start, (datetime.strptime(lo, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")))
        jobs.append((code, idx, (datetime.strptime(hi, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d"), end))
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda j: market.daily_close(j[0], j[2], j[3], index=j[1]), jobs))
    fresh = {(d, j[0]): c for j, bars in zip(jobs, results) for d, c in bars}
    rows = [r for r in rows if (r["date"], r["code"]) not in fresh]
    rows += [{"date": d, "code": code, "close": c} for (d, code), c in fresh.items()]
    write_rows(PRICE_CSV, rows, ["date", "code", "close"], sort_by=("date", "code"))


# ---------------------------------------------------------------------------
# SSE: one full day per request
# ---------------------------------------------------------------------------

def fetch_sse_day(day: str) -> list[dict]:
    r = net.get(
        "https://query.sse.com.cn/commonQuery.do",
        params={
            "isPagination": "true",
            "pageHelp.pageSize": "5000",
            "pageHelp.pageNo": "1",
            "sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
            "STAT_DATE": day,
        },
        headers={"Referer": "https://www.sse.com.cn/"},
    )
    data = r.json()["pageHelp"]["data"]
    # on non-trading or not-yet-published days the API falls back to the latest day, so filter by STAT_DATE
    return [
        {"date": x["STAT_DATE"], "code": x["SEC_CODE"], "name": x["SEC_NAME"], "shares_wan": x["TOT_VOL"]}
        for x in data
        if x["STAT_DATE"] == day
    ]


def update_sse(start: str, end: str) -> None:
    """Query each weekday (without relying on the price API for a calendar); days without data are recorded as non-trading."""
    rows = read_rows(SSE_CSV)
    have = sorted({r["date"] for r in rows})
    if have:  # the latest day may hold the preliminary evening figure, so drop and refetch it
        rows = [r for r in rows if r["date"] != have[-1]]
        have = have[:-1]
    skip = set(have) | (set(NONTRADING.read_text().split()) if NONTRADING.exists() else set())
    d, e = datetime.strptime(start, "%Y-%m-%d").date(), datetime.strptime(end, "%Y-%m-%d").date()
    todo = []
    while d <= e:
        if d.weekday() < 5 and d.isoformat() not in skip:
            todo.append(d.isoformat())
        d += timedelta(days=1)
    print(f"[SSE] {len(have)} days held, {len(todo)} weekdays to query")
    recent = (date.today() - timedelta(days=3)).isoformat()
    holidays = []
    with ThreadPoolExecutor(6) as ex:
        for i, (day, got) in enumerate(zip(todo, ex.map(fetch_sse_day, todo))):
            if got:
                rows += got
            elif day < recent:  # missing data in the last 3 days may just be unpublished, so not a holiday
                holidays.append(day)
            if i and i % 250 == 0:
                print(f"  progress {i}/{len(todo)}")
    if holidays:
        with NONTRADING.open("a") as f:
            f.write("\n".join(holidays) + "\n")
    write_rows(SSE_CSV, rows, SHARE_FIELDS, sort_by=("date", "code"))


# ---------------------------------------------------------------------------
# SZSE: per code, in 6-month windows
# ---------------------------------------------------------------------------

def fetch_szse_code(code: str, start: date, end: date) -> list[dict]:
    out = []
    s = start
    while s <= end:
        e = min(s + timedelta(days=180), end)
        page, pages = 1, 1
        while page <= pages:  # 20 rows per page
            r = net.get(
                "https://www.szse.cn/api/report/ShowReport/data",
                params={
                    "SHOWTYPE": "JSON", "CATALOGID": "scsj_fund_jjgm", "TABKEY": "tab1", "PAGENO": page,
                    "txtStart": s.isoformat(), "txtEnd": e.isoformat(), "jjlb": "ETF", "txtDm": code,
                },
                headers={"Referer": "https://www.szse.cn/market/fund/volume/etf/index.html"},
            )
            for t in r.json():
                pages = max(pages, int(t.get("metadata", {}).get("pagecount") or 1))
                for x in t.get("data", []):
                    out.append({
                        "date": x["size_date"], "code": x["fund_code"],
                        "name": x["security_short_name"], "shares_wan": x["current_size"].replace(",", ""),
                    })
            page += 1
        s = e + timedelta(days=1)
    return out


def update_szse(start: str, end: str) -> None:
    """Incremental: refetch the tail from the last day (the evening figure for T is revised on T+1); fill head gaps from the first price date."""
    net.ensure_resolvable("www.szse.cn")
    rows = read_rows(SZSE_CSV)
    codes = [e["code"] for e in CANDIDATES if e["code"].startswith("1")]
    span: dict[str, list[str]] = {}
    for r in rows:
        lo, hi = span.get(r["code"], [r["date"], r["date"]])
        span[r["code"]] = [min(lo, r["date"]), max(hi, r["date"])]
    first_px: dict[str, str] = {}  # first price date ~ listing date, so pre-listing windows are not queried in vain
    for r in read_rows(PRICE_CSV):
        first_px[r["code"]] = min(first_px.get(r["code"], r["date"]), r["date"])
    day = lambda x: datetime.strptime(x, "%Y-%m-%d").date()
    jobs = []
    for c in codes:
        lo, hi = span.get(c, [None, None])
        if lo is None:
            jobs.append((c, day(max(start, first_px.get(c, start))), day(end)))
            continue
        head_from = max(start, first_px.get(c, start))
        if (day(lo) - day(head_from)).days > 15:
            jobs.append((c, day(head_from), day(lo) - timedelta(days=1)))
        jobs.append((c, day(hi), day(end)))
    print(f"[SZSE] {len(codes)} ETFs, {len(jobs)} windows")

    def run_job(j):
        try:
            return fetch_szse_code(*j)
        except Exception as exc:  # one failed window does not discard the others
            print(f"  ! {j[0]} {j[1]}~{j[2]} failed: {type(exc).__name__}")
            return []

    with ThreadPoolExecutor(2) as ex:  # SZSE times out with 4 workers on long backfills
        results = list(ex.map(run_job, jobs))
    fresh = {(r["date"], r["code"]): r for res in results for r in res}
    rows = [r for r in rows if (r["date"], r["code"]) not in fresh] + list(fresh.values())
    write_rows(SZSE_CSV, rows, SHARE_FIELDS, sort_by=("date", "code"))


def run(start: str = DEFAULT_START, end: str | None = None) -> None:
    end = end or date.today().isoformat()
    # the three sources are independent: one failing (Tencent 501 rate limit, SZSE timeout) does not affect the others; gaps fill on the next run
    for name, fn in [("prices", lambda: update_prices(start, end)), ("SSE", lambda: update_sse(start, end)),
                     ("SZSE", lambda: update_szse(start, end))]:
        try:
            fn()
        except Exception as exc:
            print(f"[{name}] failed this time, keeping local data, will retry next run: {type(exc).__name__} {str(exc)[:120]}")
    days = sorted({r["date"] for r in read_rows(PRICE_CSV) if r["code"] == INDEX_CODE})
    print(f"[prices] local trading days {days[0] if days else '—'} ~ {days[-1] if days else '—'}, {len(days)} in total")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=None)
    a = ap.parse_args()
    run(a.start, a.end)


if __name__ == "__main__":
    main()
