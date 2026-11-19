"""Build audited company data and offline HTML with fresh metal prices and FX."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from .prices import fetch_snapshot
from ..common import net

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
BASELINE_URL = "https://github.com/MagiaSN/invest-diy/releases/download/company-profit-baseline-v1/company-profit-baseline.json"
BASELINE_SHA256 = "52b8c8bab317559aff87ee493863d34545db14137e5ff403f5316e10f25c715c"


def load_baseline(source: Path | None = None) -> dict:
    """Load an explicit research record or the checksum-pinned public baseline."""
    if source is not None:
        text = source.read_text(encoding="utf-8")
        match = re.search(r"<!-- PROFIT_MODEL_DATA_START -->\s*```json\s*(.*?)\s*```", text, re.S)
        if not match:
            raise ValueError("Missing PROFIT_MODEL_DATA block in company record")
        data = json.loads(match[1])
        data["source_sha256"] = hashlib.sha256(match[1].encode()).hexdigest()
    else:
        cached = PACKAGE / "data" / "raw" / f"baseline-{BASELINE_SHA256}.json"
        raw = cached.read_bytes() if cached.exists() else net.get(BASELINE_URL).content
        if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
            raise ValueError("Company baseline checksum mismatch")
        data = json.loads(raw)
    if data["version"] != 1 or not data["history"]:
        raise ValueError("Unsupported or empty company baseline")
    for row in data["history"]:
        if abs(row["actual"] + row["nci"] - row["net"]) > 0.00001:
            raise ValueError(f"Profit attribution mismatch: {row['year']}")
        if abs(row["pretax"] * (1 - row["tax"]) - row["net"]) > 0.00001:
            raise ValueError(f"Tax reconciliation mismatch: {row['year']}")
        gp = sum(m["gp"] for m in row["metals"])
        if abs(gp + row["associate"] + row["other"] - row["pretax"]) > 1e-8:
            raise ValueError(f"Profit bridge mismatch: {row['year']}")
        for m in row["metals"]:
            calculated = m["sales"] * (m["price"] - m["cost"]) * m["factor"] / 1e8
            if abs(calculated - m["gp"]) > 1e-8:
                raise ValueError(f"Unit conversion mismatch: {row['year']} {m['id']}")
    if source is None and not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        temporary = cached.with_suffix(".tmp")
        temporary.write_bytes(raw)
        temporary.replace(cached)
    return data


def build(source: Path | None = None) -> Path:
    data = load_baseline(source)
    data["market"] = fetch_snapshot()
    out = PACKAGE / "data" / "out"
    out.mkdir(parents=True, exist_ok=True)
    history_json = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    js = "window.CompanyProfitData = " + json.dumps(data, ensure_ascii=False) + ";\n"

    html = (PACKAGE / "web" / "index.html").read_text(encoding="utf-8")

    def asset(path: str) -> str:
        if path == "data/history.js":
            return js
        if path.startswith("/static/"):
            return (ROOT / "investdiy" / "web" / path.lstrip("/")).read_text(encoding="utf-8")
        return ((out / path[5:]) if path.startswith("data/") else (PACKAGE / "web" / path)).read_text(encoding="utf-8")

    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', lambda m: "<style>" + asset(m[1]) + "</style>", html)
    html = re.sub(r'<script src="([^"]+)"></script>', lambda m: "<script>" + asset(m[1]).replace("</script", "<\\/script") + "</script>", html)
    html = html.replace('href="/"', 'href="#"')
    destination = out / "company-profit.html"
    market = data["market"]
    dates = {q["id"] + "_as_of": q["quoted_at"][:10] for q in market["quotes"]}
    dates["fx_as_of"] = market["fx"]["as_of"]
    # Use the oldest observation, not the build date, for publication freshness checks.
    status = {"as_of": min(dates.values()), "fetched_at": market["fetched_at"], **dates}
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(status))
    writer.writeheader()
    writer.writerow(status)
    for name, contents in (("history.json", history_json), ("history.js", js),
                           (destination.name, html), ("market-status.csv", buffer.getvalue())):
        temporary = out / (name + ".tmp")
        temporary.write_text(contents, encoding="utf-8")
        temporary.replace(out / name)
    print(destination)
    print("Market snapshot:", data["market"]["fetched_at"], "FX date:", data["market"]["fx"]["as_of"])
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Override the pinned public baseline with a company research record")
    build(parser.parse_args().source)


if __name__ == "__main__":
    main()
