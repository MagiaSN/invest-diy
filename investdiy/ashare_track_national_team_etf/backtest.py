"""Backtest of the national team's ETF account and of a "next-day mirror" strategy, with money-weighted (IRR) returns.

Why money-weighted: the point of interest is buying low and selling high, i.e. when how much money goes in.
A time-weighted return treats the account as always fully invested and strips out the timing of flows,
which is exactly what we want to see. Its drawback is that years with more money weigh more (the national
team's holdings grew dozens of times from 2024), so every account is also split into full period /
2015-2023 / 2024 to date (SPLIT).

Two accounts (CNY 100 millions, summed over the pool ETFs):
  nt  national team, actual (estimated): each pool ETF's holding is rolled forward daily with its
      total-return NAV, anchored to the national-team holdings disclosed in periodic reports (units x close
      that day). The net amount traded between two anchors is spread across that window's signal days in
      proportion to the ETF's same-direction net creations (any same-direction day if there is no signal day,
      evenly as a last resort). After the last disclosure there are no anchors, so same-direction net creations
      on signal days count as national-team trades (capped by institutional holdings in the next interim
      report). This uses reports published later and represents what the national team actually did.
  mr  next-day mirror (strategy): starts aligned with the national-team holdings of the 2014 annual reports;
      afterwards, each evening it uses only data visible that evening (same-direction net creations on
      signal days count as that day's national-team trades, sales capped at the estimated holding) and at
      the next close sets its units in each ETF to match the estimated national-team holding (proportional;
      scale does not affect a money-weighted return). One-way cost COST.
  benchmark: the CSI 300 Total Return index (H00300, dividends reinvested, the index the big CSI 300 ETFs track,
      no fees). Holding it is a single investment, so money-weighted = time-weighted = annual return.

Signals come from analyze.py's daily.csv (pool net creation beyond the threshold). Units for day T are
published after the close, so the mirror trades at the close of T+1.

Outputs (data/out/):
  bt_equity.csv   daily: bench (CSI 300 Total Return index, 1 on day one), <account>_value (holdings value),
                  <account>_trade (cash traded that day, buys positive, mr includes costs)
  bt_summary.csv  per account x period: money-weighted annual return, cumulative P&L, bought / sold,
                  holdings at start / end / on average
  bt_events.csv   after signals: average return and hit rate 5 / 20 / 60 / 120 days after the first day of
                  each entry / exit wave

Usage: .venv/bin/python3 -m investdiy.ashare_track_national_team_etf.backtest
"""

from __future__ import annotations

import bisect
import statistics
from collections import defaultdict
from pathlib import Path

from ..common import market
from ..common.csvio import read_rows as _read, write_rows as _write

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "out"

BENCH_INDEX = "H00300"  # CSI 300 Total Return index (benchmark and event study)
COST = 0.0005           # 0.05% each way
CONTRA_WIN = 5          # "contrarian" = CSI 300 lower than 5 days before the signal day
HORIZONS = (5, 20, 60, 120)
SPLIT = "2024-01-01"    # split point: pool holdings were tens of billions before, over a trillion after (keep in sync with SPLIT in web/backtest.js)
RECENT_FROM = SPLIT     # the event study also reports a "since 2024" group

ENTRY, EXIT = ("进场", "强进场"), ("退出", "强退出")

def _index(start: str, end: str) -> dict[str, float]:
    """Benchmark index closes, falling back to the last cache if the fetch fails."""
    cache = DATA / f"index_{BENCH_INDEX}.csv"
    try:
        rows = market.csindex_history(BENCH_INDEX, start, end)
        _write(cache, [{"date": d, "close": v} for d, v in rows], ["date", "close"])
        return dict(rows)
    except Exception as e:  # noqa: BLE001 - fall back to the cache on network or format problems
        cached = _read(cache)
        if not cached:
            raise
        print(f"[warning] {BENCH_INDEX} fetch failed ({e}), using the cache (up to {cached[-1]['date']})")
        return {r["date"]: float(r["close"]) for r in cached}


def _nav(code: str) -> dict[str, float]:
    """ETF total-return NAV, falling back to the last cache if the fetch fails."""
    cache = DATA / f"nav_{code}.csv"
    try:
        rows = market.fund_total_return(code)
        _write(cache, [{"date": d, "tr": round(v, 6)} for d, v in rows], ["date", "tr"])
        return dict(rows)
    except Exception as e:  # noqa: BLE001 - fall back to the cache on network or format problems
        cached = _read(cache)
        if not cached:
            raise
        print(f"[warning] {code} NAV fetch failed ({e}), using the cache (up to {cached[-1]['date']})")
        return {r["date"]: float(r["tr"]) for r in cached}


def events(daily: list[dict], dates: list[str], tr: list[float]) -> list[dict]:
    """Performance after the first day of each wave (signal day T): total return over N trading days from the close of T+1."""
    pos = {d: i for i, d in enumerate(dates)}
    idx = {r["date"]: float(r["csi300"]) for r in daily}
    eps = _read(OUT / "episodes.csv")

    def fwd(i: int, h: int) -> float | None:
        a, b = i + 1, i + 1 + h
        return tr[b] / tr[a] - 1 if b < len(tr) else None

    def contra(d: str) -> bool:
        i = pos[d]
        return i >= CONTRA_WIN and idx[d] < idx[dates[i - CONTRA_WIN]]

    groups = {
        "entry": lambda e: e["side"] == "进场",
        "entry_contra": lambda e: e["side"] == "进场" and contra(e["start"]),
        "entry_trend": lambda e: e["side"] == "进场" and not contra(e["start"]),
        "exit": lambda e: e["side"] == "退出",
    }
    rows = []
    for period, since in (("all", ""), ("recent", RECENT_FROM)):
        starts = {g: [pos[e["start"]] for e in eps if e["start"] in pos and e["start"] >= since and f(e)]
                  for g, f in groups.items()}
        starts["all_days"] = [i for i, d in enumerate(dates) if d >= since]
        for g, ix in starts.items():
            row = {"period": period, "group": g, "n": len(ix)}
            for h in HORIZONS:
                vals = [v for v in (fwd(i, h) for i in ix) if v is not None]
                row[f"ret{h}"] = round(statistics.fmean(vals) * 100, 2) if vals else ""
                row[f"win{h}"] = round(sum(v > 0 for v in vals) / len(vals) * 100, 1) if vals else ""
                row[f"n{h}"] = len(vals)
            rows.append(row)
    return rows


def _spread(g: list[float], w: list[float], s: int, e: int, need: float) -> list[float]:
    """Spread need (valued at day e) over days (s, e]: a_t proportional to w_t, with sum of a_t x (growth from t to e) = need."""
    grow, acc = [0.0] * (e + 1), 1.0
    for t in range(e, s, -1):
        grow[t] = acc
        acc *= g[t]
    den = sum(w[t] * grow[t] for t in range(s + 1, e + 1))
    return [need * w[t] / den if den and t > s else 0.0 for t in range(e + 1)]


def national_team(daily: list[dict], dates: list[str]) -> dict[str, tuple[list[float], list[float]]]:
    """The two accounts {nt, mr: (holdings value, daily cash traded)} in CNY 100 millions, summed over the pool. See the module docstring."""
    sig = [r["signal"] for r in daily]
    side = [1 if s in ENTRY else -1 if s in EXIT else 0 for s in sig]
    n = len(dates)
    pool = [r["code"] for r in _read(OUT / "pool.csv") if r["in_pool"] == "1"]
    rows = defaultdict(dict)
    for r in _read(OUT / "etf_daily.csv"):
        if r["code"] in pool:
            rows[r["code"]][r["date"]] = (float(r["close"]), float(r["flow_yi"]))
    marks = defaultdict(list)  # code -> [(period end, units in 100 millions, cap only?)]
    for r in _read(OUT / "nt_holdings.csv"):
        # top-ten tables of annual / interim reports are anchors; quarterly reports list only >=20% holders, used only when the national team is identified
        if r["code"] in pool and (r["has_top10"] == "1" or float(r["nt_yi"]) > 0):
            marks[r["code"]].append((r["period_end"], float(r["nt_yi"]), False))
    for r in _read(OUT / "floor.csv"):
        if r["cap_date"]:
            marks[r["code"]].append((r["cap_date"], min(float(r["base_nt_yi"]), float(r["cap_inst_yi"])), True))

    acc = {k: ([0.0] * n, [0.0] * n) for k in ("nt", "mr")}
    for code in pool:
        nav, px = _nav(code), rows[code]
        tr, last_tr = [], None
        for d in dates:  # carry the last NAV over missing days
            last_tr = nav.get(d, last_tr)
            tr.append(last_tr)
        g = [1.0] + [tr[i] / tr[i - 1] if tr[i] and tr[i - 1] else 1.0 for i in range(1, n)]
        close = [px[d][0] if d in px else None for d in dates]
        flow = [px[d][1] if d in px else 0.0 for d in dates]

        def at(d: str) -> int | None:
            """Index of the trading day for a period end (last day <= period end with a close; day 0 if before the data starts)."""
            i = bisect.bisect_right(dates, d) - 1
            while i > 0 and close[i] is None:
                i -= 1
            return max(i, 0) if close[max(i, 0)] is not None else None

        def weights(s: int, e: int, sgn: int) -> list[float]:
            for pick in (lambda t: side[t] == sgn, lambda t: True):
                w = [abs(flow[t]) if s < t <= e and pick(t) and flow[t] * sgn > 0 else 0.0 for t in range(e + 1)]
                if any(w):
                    return w
            return [1.0 if s < t <= e and close[t] is not None else 0.0 for t in range(e + 1)]

        a = [0.0] * n
        anchors = sorted((at(d), sh, cap) for d, sh, cap in marks[code] if at(d) is not None)
        last = -1
        for i, sh, cap in anchors:
            if i <= last:
                continue
            # roll forward to i on signals first (there is no disclosure before a cap anchor, only signal-day flows)
            v = value_of(a, g, i)
            if cap:
                for t in range(last + 1, i + 1):
                    a[t] = raw(flow[t], side[t], a, g, t)
                v = value_of(a, g, i)
                if v <= sh * close[i]:
                    last = i
                    continue
            need = sh * close[i] - v
            if abs(need) > 1e-9:
                for t, x in enumerate(_spread(g, weights(last, i, 1 if need > 0 else -1), last, i, need)):
                    a[t] += x
            last = i
        for t in range(last + 1, n):  # after the last anchor
            a[t] = raw(flow[t], side[t], a, g, t)
        # next-day mirror: v is the national-team holding estimated each evening (starting from the 2014 annual
        # reports, then adding only same-direction net creations on signal days); the mirror holds the previous
        # evening's estimate x that day's return, i.e. it matches units at the next close; day 0 is aligned directly
        v = a[0]
        acc["mr"][0][0] += v
        acc["mr"][1][0] += v * (1 + COST)
        x_prev = 0.0
        for t in range(1, n):
            v_prev = v
            v *= g[t]
            x = max(flow[t], -v) if side[t] and flow[t] * side[t] > 0 else 0.0
            v += x
            b = g[t] * x_prev
            acc["mr"][0][t] += v_prev * g[t]
            acc["mr"][1][t] += b + abs(b) * COST
            x_prev = x
        v = 0.0
        for t in range(n):
            v = v * g[t] + a[t]
            acc["nt"][0][t] += v
            acc["nt"][1][t] += a[t]
    return acc


def value_of(a: list[float], g: list[float], i: int) -> float:
    v = 0.0
    for t in range(i + 1):
        v = v * g[t] + a[t]
    return v


def raw(flow: float, side: int, a: list[float], g: list[float], t: int) -> float:
    """Without anchors: same-direction net creations on signal days count as national-team trades, sales capped at the holding."""
    if not side or flow * side <= 0:
        return 0.0
    return max(flow, -value_of(a[:t] + [0.0], g, t))


def xirr(flows: list[tuple[int, float]]) -> float | None:
    """Money-weighted annual return: sum of cf x (1+r)^(-t/252) = 0, t = trading-day index (252 days a year, as for CAGR). Solved by bisection."""
    def npv(r: float) -> float:
        return sum(cf * (1 + r) ** (-t / 252) for t, cf in flows)
    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def period_stats(value: list[float], trade: list[float], i0: int, i1: int) -> dict:
    """Money-weighted result over (i0, i1]: holdings on day i0 count as invested at the start (the initial position when i0 = 0), holdings on day i1 as returned at the end."""
    flows = [(0, -value[i0])] + [(t - i0, -trade[t]) for t in range(i0 + 1, i1 + 1) if trade[t]] + [(i1 - i0, value[i1])]
    irr = xirr(flows)
    buy = sum(a for a in trade[i0 + 1: i1 + 1] if a > 0)
    sell = -sum(a for a in trade[i0 + 1: i1 + 1] if a < 0)
    return {
        "irr_pct": round(irr * 100, 2) if irr is not None else "",
        "pnl_yi": round(value[i1] - value[i0] - buy + sell, 1), "bought_yi": round(buy, 1), "sold_yi": round(sell, 1),
        "value_start_yi": round(value[i0], 1), "value_end_yi": round(value[i1], 1),
        "value_avg_yi": round(statistics.fmean(value[i0: i1 + 1]), 1),
    }


def periods(dates: list[str]) -> list[tuple[str, int, int]]:
    """Full period / before SPLIT / SPLIT to date as (key, i0, i1); the later period starts from the last day of the earlier one."""
    k = next(i for i, d in enumerate(dates) if d >= SPLIT)
    return [("all", 0, len(dates) - 1), ("pre", 0, k - 1), ("post", k - 1, len(dates) - 1)]


def main() -> None:
    daily = _read(OUT / "daily.csv")
    idx = _index(daily[0]["date"], daily[-1]["date"])
    daily = [r for r in daily if r["date"] in idx]  # daily.csv holds trading days only, which drops index rows on holidays
    dates = [r["date"] for r in daily]
    tr = [idx[d] for d in dates]
    bench = [v / tr[0] for v in tr]
    accts = national_team(daily, dates)

    summary = []
    for key, i0, i1 in periods(dates):
        base = {"period": key, "start": dates[i0 + 1] if i0 else dates[0], "end": dates[i1]}
        cagr = (bench[i1] / bench[i0]) ** (252 / (i1 - i0)) - 1
        summary.append({"account": "bench", **base, "irr_pct": round(cagr * 100, 2)})
        for k, (value, trade) in accts.items():
            summary.append({"account": k, **base, **period_stats(value, trade, i0, i1)})
    cols = ["account", "period", "start", "end", "irr_pct", "pnl_yi", "bought_yi", "sold_yi",
            "value_start_yi", "value_end_yi", "value_avg_yi"]
    _write(OUT / "bt_summary.csv", summary, cols)
    rows = [{"date": d, "bench": round(bench[i], 5),
             **{f"{k}_{c}": round(accts[k][j][i], 2) for k in accts for j, c in enumerate(("value", "trade"))}}
            for i, d in enumerate(dates)]
    _write(OUT / "bt_equity.csv", rows, ["date", "bench"] + [f"{k}_{c}" for k in accts for c in ("value", "trade")])
    ev = events(daily, dates, tr)
    _write(OUT / "bt_events.csv", ev, list(ev[0]))

    print(f"backtest {dates[0]} ~ {dates[-1]}, {len(dates)} trading days (money-weighted annual return / cumulative P&L in yi)")
    for s in summary:
        extra = f"  P&L {s['pnl_yi']:>8}  avg holdings {s['value_avg_yi']:>8}" if s["account"] != "bench" else ""
        print(f"  {s['period']:4} {s['account']:5} {s['irr_pct']:>7}%{extra}")


if __name__ == "__main__":
    main()
