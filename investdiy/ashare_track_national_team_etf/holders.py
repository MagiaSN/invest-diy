"""Scan the periodic reports of the candidate ETFs, identify national-team holdings and build the pool.

Identifying holders:
  - top-ten holder tables carry names -> matched against NT_KEYWORDS
  - quarterly / interim reports only have the unnamed "single investor >= 20%" table. Rows are linked to
    named rows by exactly equal unit counts:
      - same period: closing units of a >=20% row = units of a top-ten row -> same investor
      - across periods: opening units of this row = closing units of an earlier row -> same investor
        (inherit forwards); conversely, a later row whose opening units equal this row's closing units
        lends its identity backwards
  - >=20% rows that cannot be linked are recorded as unidentified and do not count as national team
    (conservative)

Pool rule: in any report since 2015, identified national-team holdings reached POOL_MIN_PCT of the fund
(this excludes small incidental positions).

Disclosure gap: from 2026 Huijin no longer appears in the >=20% tables (even for ETFs it held 40-80% of at
the start of the year), and the 2026 interim reports dropped the top-ten holder table, so 2026 holdings are
essentially undisclosed and can only be bounded (see analyze.holdings_bounds).

Outputs:
  data/holders/<announcement id>.json  parse cache per report (PDFs are not stored)
  data/out/holders.csv        each holder row per period, with its identity
  data/out/nt_holdings.csv    national-team units and institutional units (an upper bound) per ETF and period
  data/out/pool.csv           candidate -> in pool or not, and why

Usage: .venv/bin/python3 -m investdiy.ashare_track_national_team_etf.holders
"""

from __future__ import annotations

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..common import fund_reports as fr
from ..common.csvio import write_rows
from .pool import CANDIDATES, NT_KEYWORDS

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "holders"
OUT = ROOT / "data" / "out"
SINCE = "2014-12-31"   # earliest report period: the 2014 annual report gives the early-2015 baseline
TOL = 1.0              # tolerance for equal unit counts (units)
POOL_MIN_PCT = 10.0    # pool threshold: combined national-team holding (% of the fund)


def nt_group(name: str) -> str:
    return next((g for k, g in NT_KEYWORDS.items() if k in name), "")


def parsed(rep: fr.Report) -> dict:
    path = CACHE / f"{rep.id}.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("parser_version", 1) >= fr.PARSER_VERSION:  # re-parse old caches after a parser upgrade
            return cached
    try:
        tables = fr.parse_holder_tables(fr.download_pdf(rep.id)).to_dict()
    except Exception as exc:  # one failed report does not stop the run; no cache is written, retry next time
        print(f"  ! failed to parse {rep.title}: {exc}")
        return {"top10": [], "big": [], "total_shares": None, "inst_shares": None}
    tables["report"] = rep.__dict__
    path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    return tables


def scan(code: str) -> list[dict]:
    """Return reports merged by period: [{period_end, kinds, top10, big, total_shares}]"""
    reps = [r for r in fr.list_reports(code, since_year=int(SINCE[:4])) if r.period_end >= SINCE]
    by_period: dict[str, dict] = {}
    for rep in reps:
        t = parsed(rep)
        p = by_period.setdefault(rep.period_end, {"period_end": rep.period_end, "kinds": [], "top10": [], "big": [],
                                                  "total_shares": None, "inst_shares": None})
        p["kinds"].append(rep.kind)
        if t["top10"]:
            p["top10"] = t["top10"]
        # quarterly and annual / interim reports of the same period share the >=20% table; take the first non-empty one
        if t["big"] and not p["big"]:
            p["big"] = t["big"]
        p["total_shares"] = p["total_shares"] or t["total_shares"]
        p["inst_shares"] = p["inst_shares"] or t.get("inst_shares")
    return [by_period[k] for k in sorted(by_period)]


def attribute(periods: list[dict]) -> list[dict]:
    """Attach identities to the >=20% rows of each period and return the holder rows."""
    rows = []  # {period_end, source, name, group, shares, begin, pct}
    for p in periods:
        named = {r["name"]: r for r in p["top10"]}
        for b in p["big"]:
            hit = next((n for n, r in named.items() if abs(r["shares"] - b["end"]) <= TOL), "")
            rows.append({"period_end": p["period_end"], "source": "≥20%", "name": hit, "shares": b["end"],
                         "begin": b["begin"], "pct": b["pct"]})
        matched = {r["name"] for r in rows if r["period_end"] == p["period_end"] and r["name"]}
        for n, r in named.items():
            if n not in matched and nt_group(n):  # keep national-team top-ten rows (those below 20%)
                rows.append({"period_end": p["period_end"], "source": "前十名", "name": n, "shares": r["shares"],
                             "begin": None, "pct": r["pct"]})

    big = [r for r in rows if r["source"] == "≥20%"]
    named_rows = [r for r in rows if r["name"]]  # link sources: identified >=20% rows + national-team top-ten rows
    changed = True
    while changed:  # propagate forwards and backwards until stable
        changed = False
        for r in big:
            if r["name"]:
                continue
            # forwards: an earlier period's closing units = this row's opening units
            prev = [x for x in named_rows if x["period_end"] < r["period_end"] and r["begin"] and abs(x["shares"] - r["begin"]) <= TOL]
            # backwards: a later period's opening units = this row's closing units
            nxt = [x for x in big if x["period_end"] > r["period_end"] and x["name"] and x["begin"] and abs(x["begin"] - r["shares"]) <= TOL]
            src = max(prev, key=lambda x: x["period_end"]) if prev else (min(nxt, key=lambda x: x["period_end"]) if nxt else None)
            if src:
                r["name"] = src["name"]
                named_rows.append(r)
                changed = True
    for r in rows:
        r["group"] = nt_group(r["name"]) if r["name"] else ""
    return rows


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"[holders] scanning periodic reports of {len(CANDIDATES)} candidate ETFs")
    with ThreadPoolExecutor(4) as ex:
        scans = dict(zip([e["code"] for e in CANDIDATES], ex.map(lambda e: scan(e["code"]), CANDIDATES)))

    holder_rows, nt_rows, pool_rows = [], [], []
    for e in CANDIDATES:
        code = e["code"]
        periods = scans[code]
        rows = attribute(periods)
        for r in rows:
            holder_rows.append({"code": code, **{k: r[k] for k in ("period_end", "source", "name", "group", "shares", "pct")}})
        per = defaultdict(lambda: {"nt": 0.0, "pct": 0.0, "unknown": 0.0, "detail": []})
        for r in rows:
            d = per[r["period_end"]]
            if r["group"]:
                d["nt"] += r["shares"]
                d["pct"] += r["pct"]
                d["detail"].append(f"{r['group']} {r['shares'] / 1e8:.2f}")
            elif r["source"] == "≥20%" and not r["name"]:
                d["unknown"] += r["shares"]
        for p in periods:
            d = per[p["period_end"]]
            nt_rows.append({
                "code": code, "period_end": p["period_end"], "kinds": "/".join(sorted(set(p["kinds"]))),
                "has_top10": int(bool(p["top10"])),
                "nt_yi": round(d["nt"] / 1e8, 4), "nt_pct": round(d["pct"], 2), "unknown_big_yi": round(d["unknown"] / 1e8, 4),
                "total_yi": round(p["total_shares"] / 1e8, 4) if p["total_shares"] else "",
                "inst_yi": round(p["inst_shares"] / 1e8, 4) if p["inst_shares"] else "",
                "detail": "；".join(d["detail"]),
            })
        mine = [n for n in nt_rows if n["code"] == code]
        held = [n for n in mine if n["nt_yi"] > 0]
        latest = held[-1] if held else None
        max_pct = max((n["nt_pct"] for n in mine), default=0.0)
        in_pool = max_pct >= POOL_MIN_PCT
        pool_rows.append({
            "code": code, "name": e["name"], "family": e["family"], "in_pool": int(in_pool), "max_nt_pct": max_pct,
            "reports": len(periods),
            "first_held": held[0]["period_end"] if held else "",
            "last_held": latest["period_end"] if latest else "",
            "last_nt_yi": latest["nt_yi"] if latest else 0,
            "reason": (f"国家队最高持有 {max_pct:.1f}%" if in_pool else
                       f"国家队最高仅 {max_pct:.1f}%，低于门槛" if held else
                       "无定期报告" if not periods else "未发现国家队持有人"),
        })
        flag = "pool" if in_pool else "   -"
        print(f"  {flag} {code} {e['name_en']:<24} max {max_pct:>5.1f}%  last held {latest['period_end'] if latest else '—'}"
              f"  {latest['detail'] if latest else ''}")

    write_rows(OUT / "holders.csv", holder_rows, ["code", "period_end", "source", "name", "group", "shares", "pct"])
    write_rows(OUT / "nt_holdings.csv", nt_rows,
               ["code", "period_end", "kinds", "has_top10", "nt_yi", "nt_pct", "unknown_big_yi", "total_yi", "inst_yi", "detail"])
    write_rows(OUT / "pool.csv", pool_rows,
               ["code", "name", "family", "in_pool", "max_nt_pct", "reports", "first_held", "last_held", "last_nt_yi", "reason"])
    print(f"[holders] in pool: {sum(r['in_pool'] for r in pool_rows)} / {len(pool_rows)}")


if __name__ == "__main__":
    main()
