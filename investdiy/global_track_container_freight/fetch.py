"""Collect weekly freight index observations into data/observations.csv.

Sources:
  - Shanghai Shipping Exchange (www.sse.net.cn): all 24 index sections and their
    components, using the latest single-period pages plus the SCFIS trace page.
    Empty/restricted cells remain empty. Optional SSE_COOKIE uses an existing
    authorized session; cookies are never written to the output files.
  - Internet Archive Wayback Machine: snapshots of the same SSE pages since 2016 (a few dozen per index),
    parsed with the same code. They give sparse history before this tool started collecting.
  - The published copy of this tool's history.csv on the live site (env INVESTDIY_SITE, e.g.
    https://invest-diy.surge.sh): merged on every run so that history survives a lost local data folder.
  - PDCI composite history: Panasia's official API, falling back to Xinhua's chart API.

Precedence for the same (index, series, date): the live SSE page > existing rows > published copy > archive.
For PDCI, Panasia observations always take precedence over Xinhua fallback observations.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..common import net
from ..common.csvio import read_rows, write_rows
from . import TOOL
from .indices import SERIES, INDEX_NAMES, frequency, match_series, source_url
from .parse import CURRENT_FIELDS, Tables as _Tables, parse_page
from . import pdci

DATA = Path(__file__).resolve().parent / "data"
OBS_CSV = DATA / "observations.csv"      # index,series,date,value,source
ARCHIVE_DIR = DATA / "archive"           # cached Wayback snapshots: <index>/<page>_<timestamp>.html
ARCHIVE_STAMP = DATA / "archive_checked.txt"
ARCHIVE_EVERY_DAYS = 7                    # how often to look for new snapshots
ARCHIVE_PAUSE = 6                         # seconds between snapshot downloads (the archive allows about 15 a minute)
ARCHIVE_MAX_FAILURES = 3                  # failures in a row that end an archive pass
FIELDS = ["index", "series", "date", "value", "source"]

SSE = "https://www.sse.net.cn"
ARCHIVE_PAGES = {   # historical snapshots are limited to the original three indices
    "ccfi": [("single", "/index/singleIndex?indexType=ccfi")],
    "scfi": [("single", "/index/singleIndex?indexType=scfi")],
    "scfis": [("trace", "/index/scfisTrace"), ("single", "/index/singleIndex?indexType=scfis")],
}
PAGES = {index: [("single", f"/index/singleIndex?indexType={index}")] for index in INDEX_NAMES if index != "pdci"}
PAGES["pdci"] = [("json", pdci.PANASIA_PAGE)]
CURRENT_CSV = DATA / "current.csv"
STATUS_CSV = DATA / "status.csv"
STATUS_FIELDS = ["index", "name", "name_en", "frequency", "date", "checked_at", "last_success", "status", "available", "total", "url"]

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NUM = re.compile(r"-?\d+(?:\.\d+)?")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse(index: str, page: str, html: str) -> list[tuple[str, str, float]]:
    """(series, date, value) rows found in one SSE page."""
    if page != "trace":
        out = []
        for r in parse_page(index, html):
            if r["value"]:
                out.append((r["series"], r["date"], float(r["value"])))
            if r["prev"] and r["prev_date"]:
                out.append((r["series"], r["prev_date"], float(r["prev"])))
        return out
    p = _Tables()
    p.feed(html)
    return [r for table in p.tables for r in _parse_trace(index, table)]


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
    """Refresh every index independently, retaining its last successful snapshot on failure."""
    rows = []
    current = {(r["index"], r["series"]): r for r in read_rows(CURRENT_CSV)}
    previous_status = {r["index"]: r for r in read_rows(STATUS_CSV)}
    saved_pdci = [r for r in read_rows(OBS_CSV) if r["index"] == "pdci"]
    statuses = []
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    headers = {"Cache-Control": "no-cache", "Referer": SSE + "/"}
    if os.environ.get("SSE_COOKIE"):
        headers["Cookie"] = os.environ["SSE_COOKIE"]

    def fetch_index(index):
        url = source_url(index)
        try:
            if index == "pdci":
                history, url = pdci.fetch()
                return index, pdci.snapshot(merge(history, saved_pdci)), history, url, ""
            response = net.get(url, headers=headers, timeout=25, retries=2)
            response.encoding = "utf-8"
            snapshot = parse_page(index, response.text)
            if not snapshot or not any(r["value"] for r in snapshot):
                raise ValueError("no current values; check the page layout or access")
            keys = [r["series"] for r in snapshot]
            if len(keys) != len(set(keys)):
                raise ValueError("ambiguous series labels")
            history = [{"index": index, "series": r["series"], "date": d, "value": value, "source": "sse"}
                       for r in snapshot for d, value in [(r["date"], r["value"]), (r["prev_date"], r["prev"])]
                       if d and value]
            return index, snapshot, history, url, ""
        except Exception as exc:  # one failed source must not discard other updates
            # Do not log request headers/cookies or authentication details.
            return index, [], [], url, type(exc).__name__

    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, snapshot, history, url, error in pool.map(fetch_index, PAGES):
            old = previous_status.get(index, {})
            status = {"index": index, "name": INDEX_NAMES[index][0], "name_en": INDEX_NAMES[index][1],
                      "frequency": frequency(index), "date": old.get("date", ""), "checked_at": checked,
                      "last_success": old.get("last_success", ""), "status": "error",
                      "available": old.get("available", 0), "total": old.get("total", 0),
                      "url": old.get("url", url) if error else url}
            if error:
                print(f"  ! {index}: {error}; keeping saved data", flush=True)
            else:
                for r in snapshot:
                    current[(index, r["series"])] = r
                rows.extend(history)
                available = sum(bool(r["value"]) for r in snapshot)
                # PDCI's saved snapshot may be newer than the fallback response.
                fetched_date = max(r["date"] for r in (history if index == "pdci" else snapshot))
                status.update(date=fetched_date, last_success=checked,
                              status="ok" if available == len(snapshot) else "partial", available=available, total=len(snapshot))
                print(f"  {index}: {available}/{len(snapshot)} current values, {status['date']}", flush=True)
            statuses.append(status)
    # The trace page adds the last four settlement periods, not just the latest one.
    if "scfis" in PAGES:
        try:
            response = net.get(SSE + "/index/scfisTrace", headers=headers, timeout=25, retries=2)
            response.encoding = "utf-8"
            rows.extend({"index": "scfis", "series": s, "date": d, "value": v, "source": "sse"}
                        for s, d, v in parse("scfis", "trace", response.text))
        except Exception as exc:
            print(f"  ! scfis trace: {type(exc).__name__}; single-period data retained")
    write_rows(CURRENT_CSV, list(current.values()), CURRENT_FIELDS, sort_by=("index", "series"))
    write_rows(STATUS_CSV, statuses, STATUS_FIELDS)
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
    for index, pages in ARCHIVE_PAGES.items():
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


def read_archive_metadata() -> list[dict]:
    """Retain names and units for historical components no longer listed live."""
    catalog = {}
    for f in sorted(ARCHIVE_DIR.glob("*/*.html")):
        index, page = f.parent.name, f.stem.split("_")[0]
        if index not in ARCHIVE_PAGES or page == "trace":
            continue
        for r in parse_page(index, f.read_text(encoding="utf-8", errors="replace")):
            catalog[(index, r["series"])] = {k: r[k] for k in ("index", "series", "name", "name_en", "unit")}
    return list(catalog.values())


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
                if r["index"] == "pdci" and pdci_priority(r) > pdci_priority(out[k]):
                    out[k] = {**r, "value": format(v, ".12g")}
                if r["source"] == "archive" and out[k]["source"] == "sse" and abs(v - float(out[k]["value"])) > 0.011:
                    conflicts += 1
                    print(f"  ! archive differs: {k} archive {v} vs sse {out[k]['value']}")
                continue
            out[k] = {**r, "value": format(v, ".12g")}
    if conflicts:
        print(f"  {conflicts} archive values differ from SSE (SSE kept)")
    return list(out.values())


def pdci_priority(row: dict) -> int:
    """The primary source also wins over fallback values saved on another run."""
    return {"panasia": 2, "xinhua": 1}.get(row.get("source"), 0)


def run(refresh_archive: bool = False, latest_only: bool = False) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    print("Shipping indices (SSE and PDCI)")
    live = fetch_live()
    if not latest_only and (refresh_archive or _archive_due()):
        print("Wayback Machine")
        update_archive()
    rows = merge(live, read_rows(OBS_CSV), read_published(), read_archive())
    write_rows(OBS_CSV, rows, FIELDS, sort_by=("index", "series", "date"))
    print(f"  {len(rows)} observations -> {OBS_CSV.relative_to(DATA.parent)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch SSE and PDCI shipping index observations")
    ap.add_argument("--refresh-archive", action="store_true", help="look for new archive snapshots now")
    ap.add_argument("--latest-only", action="store_true", help="update latest SSE data and PDCI history without archive downloads")
    a = ap.parse_args()
    run(a.refresh_archive, a.latest_only)
