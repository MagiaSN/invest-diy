"""Merge the IMF history with SAFE's monthly tables and compute holdings, changes, buying phases and headline figures.

Merge: SAFE wins for every month it publishes (2018 onwards, the official source and the latest months);
the IMF fills the rest (1977-12 to 2017, quarterly until 1980). The overlap is checked month by month.

Valuation: until May 2015 China carried its gold at book cost (about USD 290 / oz from 2009), so USD values,
gold's share of reserves and the implied price are reported only from 2015-06, when gold moved to market prices.
Monthly disclosure of the gold volume also started then (June 2015 figures, published in July 2015); before
that the volume changed only in occasional lump disclosures (2001-12, 2002-12, 2009-04, 2015-06).

Outputs (data/out/, read directly by the page):
  monthly.csv   one row per reported month: volume (10,000 oz / tonnes), change, USD values, gold share, implied price
  annual.csv    one row per year: change in tonnes, months with additions, year-end volume
  phases.csv    buying phases (monthly era) and lump disclosures / decreases (before 2015-07)
  compare.csv   IMF vs SAFE for the overlapping months
  kpi.csv       headline figures (one row)

Usage: .venv/bin/python3 -m investdiy.cn_track_pboc_gold.analyze
"""

from __future__ import annotations

import calendar
from pathlib import Path

from ..common.csvio import read_rows, write_rows

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "out"

OZ_PER_TONNE = 32150.7466     # troy ounces per metric tonne
MARKET_FROM = "2015-06"       # first month valued at market prices and disclosed monthly
MONTHLY_FROM = "2015-07"      # first month whose change is a monthly purchase rather than a lump disclosure
MAX_PAUSE = 1                 # a phase survives this many unchanged months in a row (e.g. 2016-05)
MIN_LUMP_10K_OZ = 10          # lump changes smaller than this before 2015-07 are rounding (1,608 <-> 1,610 in 2002)
CHECK_TOL = 0.6               # IMF and SAFE agree when they differ by less than this (10,000 oz / USD 100m, rounding)

FIELDS = ["gold_10k_oz", "gold_usd_yi", "fx_usd_yi", "total_usd_yi"]


def tonnes(oz_10k: float) -> float:
    return oz_10k * 1e4 / OZ_PER_TONNE


def month_end(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{month}-{calendar.monthrange(y, m)[1]:02d}"


def months_between(a: str, b: str) -> int:
    (ya, ma), (yb, mb) = map(int, a.split("-")), map(int, b.split("-"))
    return (yb - ya) * 12 + mb - ma


def load() -> tuple[list[dict], list[dict]]:
    imf = {r["month"]: r for r in read_rows(DATA / "imf.csv")}
    safe = {r["month"]: r for r in read_rows(DATA / "safe.csv")}
    rows = []
    for m in sorted(imf.keys() | safe.keys()):
        src = safe.get(m) or imf[m]
        rows.append({"month": m, "source": "safe" if m in safe else "imf",
                     **{f: float(src[f]) if src.get(f) not in (None, "") else None for f in FIELDS}})
    compare = []
    for m in sorted(imf.keys() & safe.keys()):
        c = {"month": m}
        ok = True
        for f in ("gold_10k_oz", "gold_usd_yi"):
            a, b = float(imf[m][f]), float(safe[m][f])
            c[f"imf_{f}"], c[f"safe_{f}"] = a, b
            ok &= abs(a - b) < CHECK_TOL
        c["match"] = int(ok)
        compare.append(c)
    return rows, compare


def build_monthly(rows: list[dict]) -> list[dict]:
    out, prev = [], None
    for r in rows:
        oz = r["gold_10k_oz"]
        chg = oz - prev["gold_10k_oz"] if prev else 0.0
        market = r["month"] >= MARKET_FROM
        g, tot = r["gold_usd_yi"], r["total_usd_yi"]
        out.append({
            "month": r["month"],
            "date": month_end(r["month"]),
            "gold_10k_oz": round(oz, 2),
            "gold_t": round(tonnes(oz), 2),
            "chg_10k_oz": round(chg, 2),
            "chg_t": round(tonnes(chg), 2),
            "gold_usd_yi": round(g, 2) if market and g is not None else "",
            "fx_usd_yi": round(r["fx_usd_yi"], 2) if r["fx_usd_yi"] is not None else "",
            "total_usd_yi": round(tot, 2) if tot is not None else "",
            "gold_share_pct": round(g / tot * 100, 2) if market and g and tot else "",
            "price_usd_oz": round(g * 1e8 / (oz * 1e4), 1) if market and g else "",
            "valuation": "market" if market else "book",
            "source": r["source"],
        })
        prev = r
    return out


def build_phases(monthly: list[dict]) -> list[dict]:
    """Monthly era: runs of additions, tolerating MAX_PAUSE unchanged months; a decrease ends a run.
    Before 2015-07: each lump change is its own row."""
    phases: list[dict] = []
    cur: dict | None = None
    pause = 0

    def close(ongoing: bool = False):
        nonlocal cur
        if cur:
            cur["ongoing"] = int(ongoing)   # still open at the latest month (possibly within a pause)
            phases.append(cur)
        cur = None

    for r in monthly[1:]:
        c = r["chg_10k_oz"]
        if r["month"] < MONTHLY_FROM:
            if abs(c) >= MIN_LUMP_10K_OZ:
                phases.append({"kind": "disclosure" if c > 0 else "decrease", "start": r["month"], "end": r["month"],
                               "months": 1, "add_months": int(c > 0), "added_10k_oz": c, "end_10k_oz": r["gold_10k_oz"],
                               "cost_usd_yi": 0.0, "priced_10k_oz": 0.0, "ongoing": 0})
            continue
        if c > 0:
            if cur is None:
                cur = {"kind": "buying", "start": r["month"], "months": 0, "add_months": 0, "added_10k_oz": 0.0,
                       "cost_usd_yi": 0.0, "priced_10k_oz": 0.0}
            cur.update(end=r["month"], end_10k_oz=r["gold_10k_oz"])
            cur["add_months"] += 1
            cur["added_10k_oz"] += c
            if r["price_usd_oz"] != "":   # rough cost: the change x that month's implied (month-end) price
                cur["cost_usd_yi"] += c * 1e4 * r["price_usd_oz"] / 1e8
                cur["priced_10k_oz"] += c
            pause = 0
        elif c == 0 and cur is not None:
            pause += 1
            if pause > MAX_PAUSE:
                close()
        else:
            close()
            pause = 0
            if c < 0:
                phases.append({"kind": "decrease", "start": r["month"], "end": r["month"], "months": 1, "add_months": 0,
                               "added_10k_oz": c, "end_10k_oz": r["gold_10k_oz"], "cost_usd_yi": 0.0,
                               "priced_10k_oz": 0.0, "ongoing": 0})
    close(ongoing=True)
    out = []
    for p in phases:
        out.append({
            "kind": p["kind"], "start": p["start"], "end": p["end"],
            "months": months_between(p["start"], p["end"]) + 1, "add_months": p["add_months"],
            "added_10k_oz": round(p["added_10k_oz"], 2), "added_t": round(tonnes(p["added_10k_oz"]), 2),
            "end_10k_oz": round(p["end_10k_oz"], 2), "end_t": round(tonnes(p["end_10k_oz"]), 2),
            "cost_usd_yi": round(p["cost_usd_yi"], 1) if p["priced_10k_oz"] else "",
            "avg_price_usd_oz": round(p["cost_usd_yi"] * 1e8 / (p["priced_10k_oz"] * 1e4), 0) if p["priced_10k_oz"] else "",
            "ongoing": p["ongoing"],
        })
    return sorted(out, key=lambda p: p["start"], reverse=True)


def build_annual(monthly: list[dict]) -> list[dict]:
    by_year: dict[str, dict] = {}
    for r in monthly[1:]:
        y = r["month"][:4]
        a = by_year.setdefault(y, {"year": y, "chg_10k_oz": 0.0, "add_months": 0})
        a["chg_10k_oz"] += r["chg_10k_oz"]
        a["add_months"] += int(r["chg_10k_oz"] > 0)
        a["end_10k_oz"], a["last_month"] = r["gold_10k_oz"], r["month"]
    out = []
    for a in by_year.values():
        out.append({"year": a["year"], "chg_10k_oz": round(a["chg_10k_oz"], 2), "chg_t": round(tonnes(a["chg_10k_oz"]), 2),
                    "add_months": a["add_months"], "end_10k_oz": round(a["end_10k_oz"], 2),
                    "end_t": round(tonnes(a["end_10k_oz"]), 2), "partial": int(not a["last_month"].endswith("-12"))})
    return out


def build_kpi(monthly: list[dict], compare: list[dict]) -> dict:
    last, prev = monthly[-1], monthly[-2]
    streak, start = 0, ""
    for r in reversed(monthly):   # strict: consecutive months with an addition, as the press counts them
        if r["month"] < MONTHLY_FROM or r["chg_10k_oz"] <= 0:
            break
        streak, start = streak + 1, r["month"]
    year = last["month"][:4]
    ytd = sum(r["chg_10k_oz"] for r in monthly if r["month"][:4] == year)
    by_month = {r["month"]: r for r in monthly}
    y_ago = by_month.get(f"{int(year) - 1}{last['month'][4:]}")
    pages = read_rows(DATA / "safe_pages.csv")
    released = max((p["released"] for p in pages if p["year"] == year), default="") if last["source"] == "safe" else ""
    imf_months = [r["month"] for r in read_rows(DATA / "imf.csv")]
    return {
        "as_of": last["date"],
        "month": last["month"],
        "source": last["source"],
        "released": released,
        "gold_10k_oz": last["gold_10k_oz"],
        "gold_t": last["gold_t"],
        "chg_10k_oz": last["chg_10k_oz"],
        "chg_t": last["chg_t"],
        "streak": streak,
        "streak_start": start,
        "ytd_10k_oz": round(ytd, 2),
        "ytd_t": round(tonnes(ytd), 2),
        "yoy_t": round(last["gold_t"] - y_ago["gold_t"], 2) if y_ago else "",
        "gold_usd_yi": last["gold_usd_yi"],
        "gold_usd_chg_pct": round((last["gold_usd_yi"] / prev["gold_usd_yi"] - 1) * 100, 2) if prev["gold_usd_yi"] else "",
        "gold_share_pct": last["gold_share_pct"],
        "price_usd_oz": last["price_usd_oz"],
        "price_chg_pct": round((last["price_usd_oz"] / prev["price_usd_oz"] - 1) * 100, 2) if prev["price_usd_oz"] else "",
        "check_from": compare[0]["month"] if compare else "",
        "check_to": compare[-1]["month"] if compare else "",
        "check_months": len(compare),
        "check_mismatch": sum(1 - c["match"] for c in compare),
        "imf_last": max(imf_months, default=""),
    }


def main() -> None:
    rows, compare = load()
    if not rows:
        raise SystemExit("no data: run python -m investdiy.cn_track_pboc_gold first")
    monthly = build_monthly(rows)
    phases = build_phases(monthly)
    annual = build_annual(monthly)
    kpi = build_kpi(monthly, compare)
    write_rows(OUT / "monthly.csv", monthly, list(monthly[0]))
    write_rows(OUT / "annual.csv", annual, list(annual[0]))
    write_rows(OUT / "phases.csv", phases, list(phases[0]))
    write_rows(OUT / "compare.csv", compare, ["month", "imf_gold_10k_oz", "safe_gold_10k_oz", "imf_gold_usd_yi", "safe_gold_usd_yi", "match"])
    write_rows(OUT / "kpi.csv", [kpi], list(kpi))
    for c in compare:
        if not c["match"]:
            print(f"  ! IMF and SAFE differ in {c['month']}: {c}")
    print(f"[gold] {kpi['month']}: {kpi['gold_10k_oz']:,.0f} (10k oz) = {kpi['gold_t']:,.1f} t, "
          f"change {kpi['chg_t']:+.1f} t, streak {kpi['streak']} months since {kpi['streak_start'] or '—'}; "
          f"IMF/SAFE {kpi['check_months'] - kpi['check_mismatch']}/{kpi['check_months']} months agree")


if __name__ == "__main__":
    main()
