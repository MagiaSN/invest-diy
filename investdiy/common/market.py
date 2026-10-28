"""Daily A-share bars from Tencent (fqkline) for stocks, ETFs and indices, fund total-return series, and
index history from the index provider (CSIndex).

Indices must be flagged with index=True: by stock rules "000300" would map to sz000300 (Shenzhen),
but the CSI 300 index is sh000300. Bars are fetched by start / end date, up to 2,000 per request.

Do not use Tencent's adjusted prices (hfq / qfq) for ETFs: for 510300 they start only in 2018-05 and
the adjustment factors jump around. For dividend-inclusive returns use fund_total_return (Eastmoney NAVs).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from . import net

SH_PREFIXES = ("5", "6", "9")  # Shanghai: stocks 6xx, ETFs 51x/56x/58x, B shares 900


def tx_code(code: str, index: bool = False) -> str:
    if index:
        # Shanghai indices 000xxx (000300 CSI 300, 000001 SSE Composite); Shenzhen indices 399xxx
        return ("sz" if code.startswith("399") else "sh") + code
    return ("sh" if code.startswith(SH_PREFIXES) else "sz") + code


CHUNK_YEARS = 6  # at most 2,000 bars (about 8 years) per request, so fetch 6-year chunks


def daily_close(code: str, start: str, end: str, *, index: bool = False, fq: str = "") -> list[tuple[str, float]]:
    """Return [(YYYY-MM-DD, close)] in date order. fq: "" unadjusted / "qfq" / "hfq". Spans over 6 years are chunked."""
    tx = tx_code(code, index)
    out: dict[str, float] = {}
    y0, y1 = int(start[:4]), int(end[:4])
    for y in range(y0, y1 + 1, CHUNK_YEARS):
        s = start if y == y0 else f"{y}-01-01"
        e = min(end, f"{y + CHUNK_YEARS - 1}-12-31")
        r = net.get(
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
            params={"param": f"{tx},day,{s},{e},2000,{fq}"},
        )
        d = r.json()["data"][tx]
        bars = d.get(f"{fq}day" if fq else "day") or d.get("day") or d.get("qfqday") or []
        out.update((b[0], float(b[2])) for b in bars)
    return sorted(out.items())


CST = timezone(timedelta(hours=8))


def fund_total_return(code: str) -> list[tuple[str, float]]:
    """Fund total-return index [(YYYY-MM-DD, value)], 1 at inception, dividends reinvested and splits undone.

    Source: Eastmoney pingzhongdata, which returns the full history at once. Data_netWorthTrend gives the
    unit NAV y and the dividend-inclusive daily return equityReturn (%). Ordinary days use y_t / y_{t-1}
    (exact); dividend or split days (unitMoney set) use equityReturn.
    """
    t = net.get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js").text
    m = re.search(r"Data_netWorthTrend\s*=\s*(\[.*?\]);", t, re.S)
    if not m:
        raise ValueError(f"{code}: no Data_netWorthTrend in pingzhongdata")
    out, tr, prev = [], 1.0, None
    for x in json.loads(m.group(1)):
        d = datetime.fromtimestamp(x["x"] / 1000, CST).strftime("%Y-%m-%d")
        y = float(x["y"])
        if prev is not None:
            tr *= 1 + float(x["equityReturn"] or 0) / 100 if x.get("unitMoney") else y / prev
        out.append((d, tr))
        prev = y
    return out


def csindex_history(code: str, start: str, end: str) -> list[tuple[str, float]]:
    """Daily closes of a China Securities Index index [(YYYY-MM-DD, close)], e.g. "000300" (CSI 300) or
    "H00300" (CSI 300 Total Return). Source: csindex.com.cn, the index provider; one request covers the range.
    Non-trading days may appear with the previous close, so callers should align to a trading calendar."""
    r = net.get("https://www.csindex.com.cn/csindex-home/perf/index-perf",
                params={"indexCode": code, "startDate": start.replace("-", ""), "endDate": end.replace("-", "")},
                headers={"Referer": "https://www.csindex.com.cn/"})
    rows = r.json().get("data") or []
    if not rows:
        raise ValueError(f"{code}: no data from csindex.com.cn")
    return [(f"{x['tradeDate'][:4]}-{x['tradeDate'][4:6]}-{x['tradeDate'][6:]}", float(x["close"]))
            for x in rows if x.get("close") is not None]
