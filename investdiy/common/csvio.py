"""CSV read / write (UTF-8, header row first)."""

from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict], fields: list[str], sort_by: tuple[str, ...] = ()) -> None:
    if sort_by:
        rows = sorted(rows, key=lambda r: tuple(r[k] for k in sort_by))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
