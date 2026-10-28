"""Collect weekly freight index observations into data/observations.csv.

Sources:
  - Shanghai Shipping Exchange (www.sse.net.cn), public pages, no login:
      singleIndex?indexType=ccfi   CCFI composite and 12 lanes, current and previous period (published on Fridays)
      singleIndex?indexType=scfi   SCFI composite, current and previous period (lane rates need a subscription)
      scfisTrace                   SCFIS Europe and US West Coast, last four periods (published on Mondays)
    Earlier periods (single-date queries, the multi-period query) require a paid SSE account, so history
    builds up from the weekly runs.
  - Internet Archive Wayback Machine: snapshots of the same SSE pages since 2016 (a few dozen per index),
    parsed with the same code. They give sparse history before this tool started collecting.
  - The published copy of this tool's history.csv on the live site (env INVESTDIY_SITE, e.g.
    https://invest-diy.surge.sh): merged on every run so that history survives a lost local data folder.

Precedence for the same (index, series, date): the live SSE page > existing rows > published copy > archive.
Archive values that disagree with SSE values are reported.

Usage:
  .venv/bin/python3 -m investdiy.global_track_container_freight.fetch
  .venv/bin/python3 -m investdiy.global_track_container_freight.fetch --refresh-archive   # query the archive index now
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from ..common import net
from ..common.csvio import read_rows, write_rows
from . import TOOL
from .indices import SERIES, match_series

DATA = Path(__file__).resolve().parent / "data"
OBS_CSV = DATA / "observations.csv"      # index,series,date,value,source
ARCHIVE_DIR = DATA / "archive"           # cached Wayback snapshots: <index>/<page>_<timestamp>.html
ARCHIVE_STAMP = DATA / "archive_checked.txt"
ARCHIVE_EVERY_DAYS = 7                    # how often to look for new snapshots
ARCHIVE_PAUSE = 6                         # seconds between snapshot downloads (the archive allows about 15 a minute)
ARCHIVE_MAX_FAILURES = 3                  # failures in a row that end an archive pass
FIELDS = ["index", "series", "date", "value", "source"]

SSE = "https://www.sse.net.cn"
PAGES = {   # index -> [(page id, path)]; the first page of each index is fetched live
    "ccfi": [("single", "/index/singleIndex?indexType=ccfi")],
    "scfi": [("single", "/index/singleIndex?indexType=scfi")],
    "scfis": [("trace", "/index/scfisTrace"), ("single", "/index/singleIndex?indexType=scfis")],
}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NUM = re.compile(r"-?\d+(?:\.\d+)?")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class _Tables(HTMLParser):
    """Collect every table as a list of rows, each row a list of cell texts (whitespace collapsed)."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._stack: list[list[list[str]]] = []
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._stack[-1].append([])
        elif tag in ("td", "th") and self._stack and self._stack[-1]:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._stack[-1][-1].append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse(index: str, page: str, html: str) -> list[tuple[str, str, float]]:
    """(series, date, value) rows found in one SSE page."""
    p = _Tables()
    p.feed(html)
    out = []
    for table in p.tables:
        out += _parse_trace(index, table) if page == "trace" else _parse_single(index, table)
    return out


def _parse_single(index: str, table: list[list[str]]) -> list[tuple[str, str, float]]:
    """Single-period table: a header row with "上期 <date>" (optional) and "本期 <date>", then one row per series
    whose numeric cells start with the values for those dates (followed by the change)."""
    out, dates = [], None
    for row in table:
        if dates is None:
            text = " ".join(row)
            if "本期" in text:
                dates = DATE.findall(text)
            continue
        if not row or not dates:
            continue
        key = match_series(index, row[0])
        nums = [float(c) for c in row[1:] if NUM.fullmatch(c)]
        if key and len(nums) >= len(dates):
            out += [(key, d, v) for d, v in zip(dates, nums)]
    return out


def _parse_trace(index: str, table: list[list[str]]) -> list[tuple[str, str, float]]:
    """Multi-period table: a header row naming the series in columns, then one row per date."""
    out, cols = [], None
    for row in table:
        if cols is None:
            keys = [match_series(index, c) for c in row]
            if any(keys) and not DATE.search(" ".join(row)):
                cols = keys
            continue
        if row and DATE.fullmatch(row[0]):
            for key, cell in zip(cols, row):
                if key and NUM.fullmatch(cell):
                    out.append((key, row[0], float(cell)))
    return out


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def fetch_live() -> list[dict]:
    rows = []
    for index, pages in PAGES.items():
        page, path = pages[0]
        try:
            html = net.get(SSE + path).text
        except Exception as exc:  # noqa: BLE001 - one failed page should not stop the others
            print(f"  ! {index}: {exc}")
            continue
        got = parse(index, page, html)
        print(f"  sse {index}: {len(got)} values, {', '.join(sorted({d for _, d, _ in got}))}")
        if not got:
            print(f"  ! {index}: no values found; the page layout may have changed")
        rows += [{"index": index, "series": s, "date": d, "value": v, "source": "sse"} for s, d, v in got]
    return rows


def _archive_due() -> bool:
    if not ARCHIVE_STAMP.exists():
        return True
    last = datetime.fromisoformat(ARCHIVE_STAMP.read_text().strip())
    return (datetime.now(timezone.utc) - last).days >= ARCHIVE_EVERY_DAYS


def update_archive() -> None:
    """Download Wayback snapshots of the SSE pages not cached yet (one per day and page).

    The Wayback Machine refuses connections for a while after bursts of requests, so requests are spaced out
    and the pass stops after a few failures in a row; the next run carries on where it stopped. The check is
    marked as done only when every snapshot was downloaded."""
    failures, complete = 0, True
    for index, pages in PAGES.items():
        for page, path in pages:
            if failures >= ARCHIVE_MAX_FAILURES:
                break
            try:
                r = net.get("https://web.archive.org/cdx/search/cdx", timeout=90, params={
                    "url": "sse.net.cn" + path, "output": "json", "filter": "statuscode:200", "collapse": "timestamp:8"})
                snaps = r.json()[1:]
            except Exception as exc:  # noqa: BLE001 - the archive is a best-effort source
                print(f"  ! archive index {index}/{page}: {exc}")
                failures, complete = failures + 1, False
                continue
            folder = ARCHIVE_DIR / index
            folder.mkdir(parents=True, exist_ok=True)
            new = [(ts, orig) for _, ts, orig, *_ in snaps if not (folder / f"{page}_{ts}.html").exists()]
            print(f"  archive {index}/{page}: {len(snaps)} snapshots, {len(new)} new", flush=True)
            for ts, orig in new:
                time.sleep(ARCHIVE_PAUSE)
                try:
                    html = net.get(f"https://web.archive.org/web/{ts}id_/{orig}", timeout=45, retries=2).text
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {ts}: {exc}")
                    failures, complete = failures + 1, False
                    if failures >= ARCHIVE_MAX_FAILURES:
                        print("  archive: too many failures in a row, continuing next run")
                        break
                    continue
                failures = 0
                (folder / f"{page}_{ts}.html").write_text(html, encoding="utf-8")
    if complete:
        ARCHIVE_STAMP.write_text(datetime.now(timezone.utc).isoformat())


def read_archive() -> list[dict]:
    rows = []
    for f in sorted(ARCHIVE_DIR.glob("*/*.html")):
        index, page = f.parent.name, f.stem.split("_")[0]
        if index not in SERIES:
            continue
        for s, d, v in parse(index, page, f.read_text(encoding="utf-8", errors="replace")):
            rows.append({"index": index, "series": s, "date": d, "value": v, "source": "archive"})
    return rows


def read_published() -> list[dict]:
    site = os.environ.get("INVESTDIY_SITE", "").rstrip("/")
    if not site:
        return []
    try:
        text = net.get(f"{site}/{TOOL['slug']}/data/history.csv").text
    except Exception as exc:  # noqa: BLE001 - the site may not have this tool yet
        print(f"  published history not available: {exc}")
        return []
    rows = [r for r in csv.DictReader(io.StringIO(text)) if set(FIELDS) <= r.keys()]
    print(f"  published history: {len(rows)} rows")
    return [{k: r[k] for k in FIELDS} for r in rows]


# ---------------------------------------------------------------------------

def merge(*layers: list[dict]) -> list[dict]:
    """Merge layers given from highest to lowest precedence; report archive values that disagree with SSE."""
    out: dict[tuple, dict] = {}
    conflicts = 0
    for layer in layers:
        for r in layer:
            k = (r["index"], r["series"], r["date"])
            v = float(r["value"])
            if k in out:
                if r["source"] == "archive" and out[k]["source"] == "sse" and abs(v - float(out[k]["value"])) > 0.011:
                    conflicts += 1
                    print(f"  ! archive differs: {k} archive {v} vs sse {out[k]['value']}")
                continue
            out[k] = {**r, "value": f"{v:.2f}"}
    if conflicts:
        print(f"  {conflicts} archive values differ from SSE (SSE kept)")
    return list(out.values())


def run(refresh_archive: bool = False) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    print("SSE pages")
    live = fetch_live()
    if refresh_archive or _archive_due():
        print("Wayback Machine")
        update_archive()
    rows = merge(live, read_rows(OBS_CSV), read_published(), read_archive())
    write_rows(OBS_CSV, rows, FIELDS, sort_by=("index", "series", "date"))
    print(f"  {len(rows)} observations -> {OBS_CSV.relative_to(DATA.parent)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch CCFI / SCFI / SCFIS observations")
    ap.add_argument("--refresh-archive", action="store_true", help="look for new archive snapshots now")
    run(ap.parse_args().refresh_archive)
