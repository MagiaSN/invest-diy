"""Compute daily net creations from units and prices, flag likely national-team entries and exits, and write the dashboard datasets.

Flow: flow_t = (units_t - units_{t-1}) x close_t
  - units are in 10,000s x CNY -> CNY 10,000s, / 1e4 -> CNY 100 millions (yi)
  - the close approximates NAV (premiums / discounts of broad-based ETFs are usually < 0.1%)
  - unit splits: a jump in units offset by an opposite price jump on T-1 / T / T+1 -> that day's flow is 0

National-team detection (heuristic, parameters in SIGNAL_* / STRONG_*):
  - thresholds float with the market: max(previous day's pool AUM x 0.6% (strong 1.8%), multiple x median
    |total flow| over the previous 60 days)
  - pool net creation >= strong threshold -> "strong entry"; >= normal threshold -> "entry"; outflows
    symmetrically -> "strong exit" / "exit"
  - retail and ordinary institutions rarely move billions across a dozen broad-based ETFs in one day, and
    Huijin has historically concentrated in the four big CSI 300 ETFs, so the CSI 300 share is also
    reported as a fingerprint for manual review

Outputs (data/out/, read directly by the pages):
  daily.csv       daily total and per-index-family flow + CSI 300 index + signal
  etf_daily.csv   per ETF per day: units (100 millions) / close / flow
  episodes.csv    entry and exit "waves" merged from consecutive signal days
  monthly.csv     month x index family
  etf_summary.csv per ETF: latest units / AUM / flow over 5 and 20 days and year to date
  kpi.csv         headline figures for the page (one row)
  floor.csv       per ETF: national-team baseline from reports, and selling lower bounds from the share floor
                  and the institutional-holding cap
  floor_daily.csv daily total of the share-floor lower bound (CNY 100 millions)
  nt_history.csv  national-team holdings value per disclosure period (by index family); the latest
                  period after disclosure stopped is the institutional-holding cap

Signal labels (进场 entry, 强进场 strong entry, 退出 exit, 强退出 strong exit) and index-family names are
kept in Chinese in the data files; the pages translate them.

Usage: .venv/bin/python3 -m investdiy.ashare_track_national_team_etf.analyze
"""

from __future__ import annotations

import bisect
import statistics
from collections import defaultdict
from pathlib import Path

from ..common.csvio import read_rows as _read, write_rows as _write
from .pool import FAMILIES, INDEX_CODE, load_pool

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "out"

# threshold = max(floor, multiple x median |total flow| over the previous 60 trading days)
# The floor is a percentage of the previous day's pool AUM: the pool grew from about CNY 100bn in 2015 to
# almost CNY 1.9tn in 2025, so a fixed floor would almost never trigger in the early years.
# 0.6% / 1.8% is roughly CNY 10bn / 30bn in 2024-2025.
SIGNAL_FLOOR_PCT, SIGNAL_MULT = 0.6, 3.0        # entry / exit
STRONG_FLOOR_PCT, STRONG_MULT = 1.8, 6.0        # strong entry / strong exit
BASELINE_WINDOW = 60
EPISODE_GAP = 2         # same-direction signals at most 2 trading days apart merge into one wave

ACTIVE_WITHIN = 3       # a wave that ended within the last 3 trading days counts as ongoing

# column names are ASCII (the pages read columns by name); display names live in the pages
FAMILY_KEY = dict(zip(FAMILIES, ["hs300", "sz50", "zz500", "zz1000", "cyb", "kc50", "a500", "other"]))


def thresholds(history: list[float], pool_aum: float) -> tuple[float, float]:
    """history = total flows of previous days, pool_aum = previous day's pool AUM (CNY 100 millions); returns (normal, strong) thresholds."""
    if not history or pool_aum <= 0:  # no reference on the first day, no signal
        return float("inf"), float("inf")
    base = statistics.median(abs(x) for x in history[-BASELINE_WINDOW:])
    return (max(SIGNAL_FLOOR_PCT / 100 * pool_aum, SIGNAL_MULT * base),
            max(STRONG_FLOOR_PCT / 100 * pool_aum, STRONG_MULT * base))


def classify(flow: float, normal: float, strong: float) -> str:
    side = "进场" if flow > 0 else "退出"
    if abs(flow) >= strong:
        return "强" + side
    if abs(flow) >= normal:
        return side
    return ""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    pool = {e["code"]: e for e in load_pool(OUT)}  # built by holders.py, default pool otherwise

    price: dict[tuple[str, str], float] = {}
    for r in _read(DATA / "prices.csv"):
        price[(r["date"], r["code"])] = float(r["close"])
    days = sorted(d for d, c in price if c == INDEX_CODE)

    shares: dict[str, dict[str, float]] = defaultdict(dict)
    for path in (DATA / "sse_shares.csv", DATA / "szse_shares.csv"):
        for r in _read(path):
            if r["code"] in pool:
                shares[r["code"]][r["date"]] = float(r["shares_wan"])

    missing = [c for c in pool if not shares[c]]
    for c in missing:
        print(f"[warning] {c} {pool[c]['name_en']} has no unit data (the next fetch will backfill it); skipped this time")
        pool.pop(c)

    # ---- per ETF ----
    etf_rows = []
    flow_by_day: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    aum_by_day: dict[str, float] = defaultdict(float)  # daily pool AUM (CNY 100 millions), for the threshold floor
    for code, e in pool.items():
        obs = [(d, shares[code][d], price[(d, code)])
               for d in days if d in shares[code] and (d, code) in price]
        for i, (d, s, p) in enumerate(obs):
            flow = 0.0
            if i:
                prev_s = obs[i - 1][1]
                rs = s / prev_s if prev_s else 1.0
                # unit split: a unit jump offset by an opposite price jump, which may be published a day apart
                # (e.g. E Fund CSI 300 halved its units on 2024-09-20 but its price doubled only on 09-23)
                split = False
                if not 0.7 < rs < 1.43:
                    for j in (i - 1, i, i + 1):
                        if 1 <= j < len(obs) and abs(rs * obs[j][2] / obs[j - 1][2] - 1) < 0.08:
                            split = True
                flow = 0.0 if split else (s - prev_s) * p / 1e4
            etf_rows.append({
                "date": d, "code": code, "name": e["name"], "family": e["family"],
                "shares_yi": round(s / 1e4, 4), "close": p, "flow_yi": round(flow, 3),
            })
            flow_by_day[d][e["family"]] += flow
            aum_by_day[d] += s / 1e4 * p
    _write(OUT / "etf_daily.csv", etf_rows,
           ["date", "code", "name", "family", "shares_yi", "close", "flow_yi"])

    # ---- daily totals ----
    daily = []
    cum = 0.0
    prev_idx = None
    prev_aum = 0.0
    history: list[float] = []
    for d in days:
        idx = price[(d, INDEX_CODE)]
        fam = flow_by_day.get(d, {})
        total = sum(fam.values())
        if d not in flow_by_day:  # units not published yet (e.g. during the trading day)
            prev_idx = idx
            continue
        cum += total
        hs300 = fam.get("沪深300", 0.0)
        normal, strong = thresholds(history, prev_aum)
        sig = classify(total, normal, strong)
        history.append(total)
        prev_aum = aum_by_day.get(d, prev_aum)
        row = {
            "date": d,
            "csi300": idx,
            "csi300_ret": round((idx / prev_idx - 1) * 100, 3) if prev_idx else 0.0,
            "flow_total": round(total, 2),
            "flow_cum": round(cum, 2),
            "hs300_share": round(hs300 / total * 100, 1) if sig else "",
            "threshold": round(normal, 1) if normal != float("inf") else "",
            "signal": sig,
        }
        for f in FAMILIES:
            row[FAMILY_KEY[f]] = round(fam.get(f, 0.0), 2)
        daily.append(row)
        prev_idx = idx
    fields = ["date", "csi300", "csi300_ret", "flow_total", "flow_cum", "hs300_share", "threshold", "signal"] + list(FAMILY_KEY.values())
    _write(OUT / "daily.csv", daily, fields)

    # ---- waves ----
    episodes = []
    cur = None
    for i, r in enumerate(daily):
        if not r["signal"]:
            continue
        side = "进场" if r["flow_total"] > 0 else "退出"
        if cur and cur["side"] == side and i - cur["_last"] <= EPISODE_GAP + 1:
            cur["end"] = r["date"]
            cur["days"] += 1
            cur["flow"] += r["flow_total"]
            cur["hs300"] += r["hs300"]
            cur["_last"] = i
            cur["_peak"] = max(cur["_peak"], abs(r["flow_total"]))
            cur["idx_end"] = r["csi300"]
        else:
            if cur:
                episodes.append(cur)
            prev_close = daily[i - 1]["csi300"] if i else r["csi300"]
            cur = {"side": side, "start": r["date"], "end": r["date"], "days": 1,
                   "flow": r["flow_total"], "hs300": r["hs300"], "_last": i, "_peak": abs(r["flow_total"]),
                   "idx_start": prev_close, "idx_end": r["csi300"]}
    if cur:
        episodes.append(cur)
    ep_rows = [{
        "start": e["start"], "end": e["end"], "side": e["side"], "signal_days": e["days"],
        "flow_yi": round(e["flow"], 1), "peak_day_yi": round(e["_peak"] if e["side"] == "进场" else -e["_peak"], 1),
        "csi300_chg": round((e["idx_end"] / e["idx_start"] - 1) * 100, 2),
        # share of the four big CSI 300 ETFs in the wave's total flow: Huijin concentrates there, so a high share looks more like the national team
        "hs300_pct": round(e["hs300"] / e["flow"] * 100, 1) if e["flow"] else "",
    } for e in episodes]
    _write(OUT / "episodes.csv", ep_rows,
           ["start", "end", "side", "signal_days", "flow_yi", "peak_day_yi", "csi300_chg", "hs300_pct"])

    # ---- month x index family ----
    monthly: dict[str, dict] = {}
    for r in daily:
        m = monthly.setdefault(r["date"][:7], {"month": r["date"][:7], "total": 0.0,
                                               **{k: 0.0 for k in FAMILY_KEY.values()}})
        m["total"] += r["flow_total"]
        for k in FAMILY_KEY.values():
            m[k] += r[k]
    m_rows = [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()} for m in monthly.values()]
    _write(OUT / "monthly.csv", m_rows, ["month", "total"] + list(FAMILY_KEY.values()))

    # ---- per-ETF summary ----
    obs_days = [r["date"] for r in daily]
    ytd_start = obs_days[-1][:4] + "-01-01"
    by_code: dict[str, list[dict]] = defaultdict(list)
    for r in etf_rows:
        by_code[r["code"]].append(r)
    summary = []
    for code, e in pool.items():
        rs = by_code[code]
        last = rs[-1]
        flows = {r["date"]: r["flow_yi"] for r in rs}
        summary.append({
            "code": code, "name": e["name"], "name_en": e["name_en"], "family": e["family"],
            "shares_yi": last["shares_yi"],
            "aum_yi": round(last["shares_yi"] * last["close"], 1),
            "flow_5d": round(sum(flows.get(d, 0.0) for d in obs_days[-5:]), 1),
            "flow_20d": round(sum(flows.get(d, 0.0) for d in obs_days[-20:]), 1),
            "flow_ytd": round(sum(v for d, v in flows.items() if d >= ytd_start), 1),
        })
    _write(OUT / "etf_summary.csv", summary,
           ["code", "name", "name_en", "family", "shares_yi", "aum_yi", "flow_5d", "flow_20d", "flow_ytd"])

    # ---- national-team baseline, share floor, institutional cap ----
    floor_rows, floor_daily, nt_hist = holdings_bounds(pool, by_code)
    _write(OUT / "floor.csv", floor_rows, list(floor_rows[0]) if floor_rows else ["code"])
    _write(OUT / "floor_daily.csv", floor_daily, ["date", "floor_amt_yi"])
    _write(OUT / "nt_history.csv", nt_hist, ["period_end", "kind", "total"] + list(FAMILY_KEY.values()))
    base_amt_now = sum(r["base_nt_yi"] * r["close"] for r in floor_rows)
    floor_amt = sum(r["floor_amt_yi"] for r in floor_rows)
    cap_amt = sum(r["cap_floor_amt_yi"] for r in floor_rows if r["cap_floor_amt_yi"] != "")

    # ---- headline KPIs ----
    last = daily[-1]
    ep = ep_rows[-1] if ep_rows else None
    active = bool(ep) and obs_days.index(ep["end"]) >= len(obs_days) - ACTIVE_WITHIN
    kpi = {
        "as_of": last["date"],
        "flow_1d": last["flow_total"],
        "flow_5d": round(sum(r["flow_total"] for r in daily[-5:]), 1),
        "flow_20d": round(sum(r["flow_total"] for r in daily[-20:]), 1),
        "flow_ytd": round(sum(r["flow_total"] for r in daily if r["date"] >= ytd_start), 1),
        "csi300": last["csi300"],
        "csi300_ret": last["csi300_ret"],
        "signal_1d": last["signal"] or "无信号",
        "threshold": last["threshold"],
        "state": ep["side"] + "中" if active else "观望",
        "episode_start": ep["start"] if active else "",
        "episode_days": ep["signal_days"] if active else "",
        "episode_flow": ep["flow_yi"] if active else "",
        "episode_csi300_chg": ep["csi300_chg"] if active else "",
        "pool_size": len(pool),
        "nt_base_date": max((r["base_date"] for r in floor_rows), default=""),
        "nt_base_amt": round(sum(r["base_amt_yi"] for r in floor_rows), 1),
        "floor_amt": round(floor_amt, 1),
        "floor_pct": round(floor_amt / base_amt_now * 100, 1) if base_amt_now else "",
        "cap_date": max((r["cap_date"] for r in floor_rows), default=""),
        "cap_floor_amt": round(cap_amt, 1),
        "cap_floor_pct": round(cap_amt / base_amt_now * 100, 1) if base_amt_now else "",
    }
    _write(OUT / "kpi.csv", [kpi], list(kpi))

    print(f"daily: {len(daily)} rows ({daily[0]['date']} ~ {daily[-1]['date']}), cumulative net creation {cum:.0f} yi")
    print(f"signal days: {sum(1 for r in daily if r['signal'])}, waves: {len(ep_rows)}")


def holdings_bounds(pool: dict, by_code: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Derive lower bounds on national-team selling from the holding H disclosed in periodic reports.

    - share floor (daily): after the baseline date, if total units S_t < H, the national team sold at least H - S_t
    - institutional cap (interim / annual): national-team holdings <= total institutional units I, so at least
      H - I was sold (usually tighter than the floor)
    Baseline = the latest report period in which a national-team holding was identified.
    """
    nt = defaultdict(list)
    for r in _read(OUT / "nt_holdings.csv"):
        if r["code"] in pool:
            nt[r["code"]].append(r)
    floor_rows, by_day = [], defaultdict(float)
    hist: dict[str, dict] = {}
    for code, e in pool.items():
        obs = by_code[code]
        if not obs:
            continue
        dates = [r["date"] for r in obs]

        def on_or_before(d: str) -> dict:
            i = bisect.bisect_right(dates, d) - 1
            return obs[max(i, 0)]  # before the data starts, use the first trading day

        rs = sorted(nt.get(code, []), key=lambda r: r["period_end"])
        # holdings history uses only periods with a top-ten table; quarterly reports list only >=20% holders and would understate
        for r in rs:
            if r["has_top10"] == "1":
                o = on_or_before(r["period_end"])
                h = hist.setdefault(r["period_end"], {"period_end": r["period_end"], "kind": "披露", "total": 0.0,
                                                      **{k: 0.0 for k in FAMILY_KEY.values()}})
                if o:
                    amt = float(r["nt_yi"]) * o["close"]
                    h[FAMILY_KEY[e["family"]]] += amt
                    h["total"] += amt
        base = next((r for r in reversed(rs) if float(r["nt_yi"]) > 0), None)
        if not base:
            continue
        H, bd = float(base["nt_yi"]), base["period_end"]
        bo = on_or_before(bd)
        after = [r for r in obs if r["date"] > bd]
        for r in after:
            by_day[r["date"]] += max(0.0, H - r["shares_yi"]) * r["close"]
        last = obs[-1]
        floor_sh = max(0.0, H - last["shares_yi"])
        cap = next((r for r in reversed(rs) if r["period_end"] > bd and r["inst_yi"]), None)
        cap_sh = max(0.0, H - float(cap["inst_yi"])) if cap else None
        if cap:  # the cap is also drawn in the holdings history
            o = on_or_before(cap["period_end"])
            h = hist.setdefault(cap["period_end"], {"period_end": cap["period_end"], "kind": "上限", "total": 0.0,
                                                    **{k: 0.0 for k in FAMILY_KEY.values()}})
            h["kind"] = "上限"
            if o:
                amt = min(H, float(cap["inst_yi"])) * o["close"]
                h[FAMILY_KEY[e["family"]]] += amt
                h["total"] += amt
        floor_rows.append({
            "code": code, "name": e["name"], "name_en": e["name_en"], "family": e["family"],
            "base_date": bd, "base_nt_yi": round(H, 2), "base_nt_pct": base["nt_pct"], "holders": base["detail"],
            "base_amt_yi": round(H * bo["close"], 1) if bo else "",
            "shares_yi": round(last["shares_yi"], 2), "close": last["close"],
            "floor_yi": round(floor_sh, 2), "floor_pct": round(floor_sh / H * 100, 1),
            "floor_amt_yi": round(floor_sh * last["close"], 1),
            "breach_date": next((r["date"] for r in after if r["shares_yi"] < H), ""),
            "cap_date": cap["period_end"] if cap else "", "cap_inst_yi": round(float(cap["inst_yi"]), 2) if cap else "",
            "cap_floor_yi": round(cap_sh, 2) if cap else "", "cap_floor_pct": round(cap_sh / H * 100, 1) if cap else "",
            "cap_floor_amt_yi": round(cap_sh * last["close"], 1) if cap else "",
        })
    floor_daily = [{"date": d, "floor_amt_yi": round(v, 1)} for d, v in sorted(by_day.items())]
    nt_hist = [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in hist[p].items()} for p in sorted(hist)]
    return floor_rows, floor_daily, nt_hist


if __name__ == "__main__":
    main()
