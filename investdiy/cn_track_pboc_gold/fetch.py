"""Fetch China's official gold reserves: the IMF's long monthly history and SAFE's latest monthly tables.

Sources (all free, no login):
  - IMF International Liquidity (dataset IL, SDMX 2.1 at api.imf.org), country CHN, monthly:
      RGV_REVS (FTO)       gold, fine troy ounces
      RGOLDNV_REVS (USD)   gold at national valuation (book cost until May 2015, market price since June 2015)
      RXF11FX_REVS (USD)   foreign currency reserves
      TRGMV_REVS (USD)     total reserves including gold
    from 1977-12; it trails the official release by about three months
  - SAFE "官方储备资产（YYYY年）" (www.safe.gov.cn, statistics -> foreign exchange reserves): one page per
    year with an HTML table (from 2018) listing each month in USD 100 millions and SDR 100 millions, plus
    the gold volume in 10,000 ounces. Published around the 7th of the next month

Outputs (data/):
  imf.csv         month,gold_10k_oz,gold_usd_yi,fx_usd_yi,total_usd_yi
  safe.csv        month,gold_10k_oz,gold_usd_yi,fx_usd_yi,total_usd_yi
  safe_pages.csv  year,page,table,released (SAFE pages found; past years are not fetched again)

Usage: .venv/bin/python3 -m investdiy.cn_track_pboc_gold.fetch [--full]
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from ..common import net
from ..common.csvio import read_rows, write_rows

DATA = Path(__file__).resolve().parent / "data"
IMF_CSV = DATA / "imf.csv"
SAFE_CSV = DATA / "safe.csv"
PAGES_CSV = DATA / "safe_pages.csv"

FIELDS = ["month", "gold_10k_oz", "gold_usd_yi", "fx_usd_yi", "total_usd_yi"]
IMF_URL = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,IL/CHN.RGV_REVS+RGOLDNV_REVS+RXF11FX_REVS+TRGMV_REVS.FTO+USD.M"
IMF_FIELD = {"RGV_REVS": "gold_10k_oz", "RGOLDNV_REVS": "gold_usd_yi", "RXF11FX_REVS": "fx_usd_yi", "TRGMV_REVS": "total_usd_yi"}
IMF_MAX_AGE_DAYS = 7     # the IMF series moves once a month; refetch at most weekly

SAFE = "https://www.safe.gov.cn"
SAFE_LISTS = ["/safe/whcb/index.html", "/safe/whcb/index_2.html"]   # "foreign exchange reserves" listing
SAFE_FIRST_YEAR = 2018   # first year with an HTML table (2015-06 to 2017 are xls / xlsx files; the IMF covers them)


# ---------------------------------------------------------------------------
# IMF
# ---------------------------------------------------------------------------

def update_imf(force: bool = False) -> None:
    if not force and IMF_CSV.exists() and time.time() - IMF_CSV.stat().st_mtime < IMF_MAX_AGE_DAYS * 86400:
        print(f"[IMF] cache is less than {IMF_MAX_AGE_DAYS} days old, not refetched")
        return
    r = net.get(IMF_URL, headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}, timeout=60)
    by_month: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        field = IMF_FIELD.get(row["INDICATOR"])
        m = re.fullmatch(r"(\d{4})-M(\d{2})", row["TIME_PERIOD"])
        if not field or not m or row["OBS_VALUE"] == "":
            continue
        v = float(row["OBS_VALUE"])
        # ounces -> 10,000 ounces, USD -> USD 100 millions (the units SAFE publishes in)
        by_month.setdefault(f"{m[1]}-{m[2]}", {})[field] = round(v / 1e4, 2) if field == "gold_10k_oz" else round(v / 1e8, 2)
    rows = [{"month": k, **{f: v.get(f, "") for f in FIELDS[1:]}} for k, v in by_month.items() if v.get("gold_10k_oz")]
    if len(rows) < 500:  # the series starts in 1977-12; a short answer means a broken response, keep the cache
        raise RuntimeError(f"IMF returned only {len(rows)} months")
    write_rows(IMF_CSV, rows, FIELDS, sort_by=("month",))
    print(f"[IMF] {rows and min(r['month'] for r in rows)} ~ {max(r['month'] for r in rows)}, {len(rows)} months")


# ---------------------------------------------------------------------------
# SAFE
# ---------------------------------------------------------------------------

class _Tables(HTMLParser):
    """Collect the text of every table row (cells with whitespace collapsed)."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _html(path: str) -> str:
    return net.get(SAFE + path).content.decode("utf-8", "replace")


def safe_year_pages() -> dict[int, str]:
    """{year: page path} for every "官方储备资产（YYYY年）" page in the listing."""
    found: dict[int, str] = {}
    for lst in SAFE_LISTS:
        for href, y in re.findall(r'href="(/safe/[\d/]+\.html)"[^>]*title="官方储备资产（(\d{4})年）"', _html(lst)):
            found.setdefault(int(y), href)
    return found


def parse_table(html: str, year: int) -> list[dict]:
    """Rows of one year's table: 外汇储备 / 黄金 (USD, then the ounce row below it) / 合计.
    Header: 项目 Item | YYYY.01 ... YYYY.12; value rows: label | USD, SDR | USD, SDR | ..."""
    p = _Tables()
    p.feed(html)
    head = next((r for r in p.rows if r and r[0].startswith("项目")), None)
    if not head:
        raise ValueError(f"{year}: no header row")
    months = [c for c in head[1:] if c]
    for i, c in enumerate(months):  # months are listed in order; check the year and month of each column
        m = re.fullmatch(r"(\d{4})\.(\d{2})", c)
        if not m or int(m[1]) != year or int(m[2]) != i + 1:
            raise ValueError(f"{year}: unexpected header {head}")
    num = lambda s: float(s.replace(",", "")) if re.fullmatch(r"-?[\d,]+(\.\d+)?", s or "") else None
    usd = lambda r: [num(r[1 + 2 * i]) if 1 + 2 * i < len(r) else None for i in range(len(months))]
    series: dict[str, list] = {}
    for i, r in enumerate(p.rows):
        label = r[0] if r else ""
        if re.match(r"1\.\s*外汇储备", label):
            series["fx_usd_yi"] = usd(r)
        elif re.match(r"4\.\s*黄金", label):
            series["gold_usd_yi"] = usd(r)
            oz = p.rows[i + 1] if i + 1 < len(p.rows) else []
            series["gold_10k_oz"] = [
                float(m[1]) if 1 + 2 * k < len(oz) and (m := re.fullmatch(r"([\d.]+)\s*万盎司", oz[1 + 2 * k])) else None
                for k in range(len(months))]
        elif label.startswith("合计"):
            series["total_usd_yi"] = usd(r)
    missing = set(FIELDS[1:]) - set(series)
    if missing:
        raise ValueError(f"{year}: rows not found: {sorted(missing)}")
    out = []
    for k in range(len(months)):
        if series["gold_10k_oz"][k] is None:   # months not published yet are empty
            continue
        out.append({"month": f"{year}-{k + 1:02d}", **{f: series[f][k] for f in FIELDS[1:]}})
    return out


def update_safe(full: bool = False) -> None:
    pages = {int(r["year"]): r for r in read_rows(PAGES_CSV)}
    rows = {r["month"]: r for r in read_rows(SAFE_CSV)}
    this_year = date.today().year
    listing = safe_year_pages()
    # past years are final; the current one grows every month and the previous one may still be revised in January
    todo = [y for y in sorted(listing) if y >= SAFE_FIRST_YEAR and (full or y >= this_year - 1 or y not in pages)]
    for y in todo:
        page = _html(listing[y])
        m = re.search(r'href="(/safe/[\d/]+\.html)"[^>]*>\s*html\s*<', page)
        if not m:
            print(f"  ! SAFE {y}: no html table link on {listing[y]}")
            continue
        rel = re.search(r"发布日期：\s*(?:<[^>]*>\s*)*(\d{4}-\d{2}-\d{2})", page)
        got = parse_table(_html(m[1]), y)
        for r in got:
            rows[r["month"]] = r
        pages[y] = {"year": str(y), "page": listing[y], "table": m[1], "released": rel[1] if rel else ""}
        print(f"[SAFE] {y}: {len(got)} months ({got[-1]['month'] if got else '—'}), released {pages[y]['released'] or '?'}")
    write_rows(SAFE_CSV, list(rows.values()), FIELDS, sort_by=("month",))
    write_rows(PAGES_CSV, list(pages.values()), ["year", "page", "table", "released"], sort_by=("year",))


def run(full: bool = False) -> None:
    # the two sources are independent: if one fails, keep its local data and retry on the next run
    for name, fn in [("IMF", lambda: update_imf(full)), ("SAFE", lambda: update_safe(full))]:
        try:
            fn()
        except Exception as exc:
            print(f"[{name}] failed this time, keeping local data, will retry next run: {type(exc).__name__} {str(exc)[:160]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="refetch the IMF series and every SAFE year")
    run(ap.parse_args().full)


if __name__ == "__main__":
    main()
