"""Import the latest encrypted Actions snapshot without losing local observations."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from investdiy.common import github_actions
from investdiy.common.csvio import read_rows, write_rows
from . import analyze, fetch, pdci
from .indices import INDEX_NAMES

STATE = Path.home() / ".local/share/invest-diy"
SCHEMAS = {"observations.csv": fetch.FIELDS, "current.csv": fetch.CURRENT_FIELDS,
           "status.csv": fetch.STATUS_FIELDS}


def decode_snapshot(contents: dict[str, bytes]) -> dict[str, list[dict]]:
    """Validate the required CSVs before touching local files."""
    result = {}
    for filename, fields in SCHEMAS.items():
        reader = csv.DictReader(io.StringIO(contents[filename].decode("utf-8-sig")))
        if not set(fields) <= set(reader.fieldnames or []):
            raise ValueError(f"Snapshot CSV has missing columns: {filename}")
        rows, seen = [], set()
        for raw in reader:
            row = {field: raw.get(field) for field in fields}
            if any(v is None for v in row.values()) or row["index"] not in INDEX_NAMES:
                raise ValueError(f"Invalid snapshot row in {filename}")
            key = ((row["index"], row["series"], row["date"]) if filename == "observations.csv"
                   else (row["index"], row["series"]) if filename == "current.csv" else row["index"])
            if key in seen:
                raise ValueError(f"Duplicate snapshot row in {filename}")
            seen.add(key)
            if row["date"]:
                date.fromisoformat(row["date"])
            if filename == "observations.csv":
                if not row["date"] or not row["series"]:
                    raise ValueError("Observation is missing its identity or date")
                try:
                    valid = Decimal(row["value"]).is_finite()
                except InvalidOperation:
                    valid = False
                if not valid:
                    raise ValueError("Snapshot contains an invalid observation value")
            if filename == "status.csv":
                if row["status"] not in {"ok", "partial", "error", "not_fetched"}:
                    raise ValueError("Invalid source status in snapshot")
                for field in ("checked_at", "last_success"):
                    if row[field] and datetime.fromisoformat(row[field]).tzinfo is None:
                        raise ValueError("Snapshot timestamps must include a timezone")
            rows.append(row)
        result[filename] = rows
    if not result["observations.csv"] or not result["status.csv"] or not result["current.csv"]:
        raise ValueError("Snapshot does not contain the required data")
    return result


def _rank(row: dict) -> tuple:
    timestamp = row.get("last_success")
    return (row.get("date", ""), datetime.fromisoformat(timestamp) if timestamp
            else datetime.min.replace(tzinfo=timezone.utc))


def merge_snapshot(cloud: dict[str, list[dict]], data: Path) -> tuple[dict[str, list[dict]], int, int]:
    """Preserve local-only history and prefer the newer successful source snapshot."""
    old_status = {r["index"]: r for r in read_rows(data / "status.csv")}
    preferred = {r["index"] for r in cloud["status.csv"]
                 if r["status"] in {"ok", "partial"} and _rank(r) >= _rank(old_status.get(r["index"], {}))}
    key = lambda r: (r["index"], r["series"], r["date"])
    observations = {key(r): r for r in read_rows(data / "observations.csv")}
    added = corrected = 0
    for row in cloud["observations.csv"]:
        old = observations.get(key(row))
        if old is None:
            observations[key(row)] = row
            added += 1
        elif ((row["source"] == "sse" and old["source"] != "sse")
              or (row["index"] == "pdci" and fetch.pdci_priority(row) > fetch.pdci_priority(old))
              or (row["source"] == old["source"] and row["index"] in preferred)):
            corrected += row["value"] != old["value"]
            observations[key(row)] = row
    current = {(r["index"], r["series"]): r for r in read_rows(data / "current.csv")}
    for row in cloud["current.csv"]:
        k = (row["index"], row["series"])
        if k not in current or (row["index"] in preferred and row["date"] >= current[k]["date"]):
            current[k] = row
    pdci_rows = [r for r in observations.values() if r["index"] == "pdci" and r["series"] == "composite"]
    if pdci_rows:
        # Keep current values consistent with the primary-over-fallback history merge.
        current[("pdci", "composite")] = pdci.snapshot(pdci_rows)[0]
    for row in cloud["status.csv"]:
        if row["index"] in preferred or row["index"] not in old_status:
            old_status[row["index"]] = row
    return {"observations.csv": list(observations.values()), "current.csv": list(current.values()),
            "status.csv": list(old_status.values())}, added, corrected


def install_snapshot(cloud: dict[str, list[dict]], data: Path, backup_dir: Path) -> dict:
    """Build outputs first, back up existing data, then replace files with rollback."""
    if backup_dir.resolve().is_relative_to(data.resolve()):
        raise ValueError("Backup directory must be outside the tool's data directory.")
    merged, added, corrected = merge_snapshot(cloud, data)
    data.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sse-sync-", dir=data.parent) as temporary:
        stage = Path(temporary)
        for name, fields in SCHEMAS.items():
            order = ("index", "series", "date") if name == "observations.csv" else ()
            write_rows(stage / name, merged[name], fields, sort_by=order)
        analyze.main(data_dir=stage)
        files = [p.relative_to(stage) for p in stage.rglob("*.csv")]
        backup = None
        if data.exists():
            backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            backup = backup_dir / f"sse-before-sync-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.tar.gz"
            with backup.open("xb") as stream:
                os.chmod(backup, 0o600)
                with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                    archive.add(data, arcname="data")
        original = {rel: (data / rel).read_bytes() if (data / rel).exists() else None for rel in files}
        written = []
        try:
            for rel in files:
                target = data / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage / rel, target)
                written.append(rel)
        except OSError:
            for rel in reversed(written):
                if original[rel] is None:
                    (data / rel).unlink(missing_ok=True)
                else:
                    (data / rel).write_bytes(original[rel])
            raise
    return {"added": added, "corrected": corrected, "total": len(merged["observations.csv"]), "backup": backup}


def sync(repo: str, branch: str | None, key_file: Path, backup_dir: Path) -> dict:
    for command in ("gh", "gpg"):
        if shutil.which(command) is None:
            raise RuntimeError(f"Install {command} before synchronizing data.")
    if not key_file.expanduser().is_file():
        raise ValueError(f"Decryption key file not found: {key_file}")
    artifact = github_actions.latest_artifact(repo, "sse-update.yml", "sse-history-encrypted", branch)
    with tempfile.TemporaryDirectory(prefix="invest-diy-sse-download-") as temporary:
        encrypted = Path(temporary) / "sse-history.tar.gz.gpg"
        github_actions.download_member(repo, artifact["id"], encrypted.name, encrypted)
        cloud = decode_snapshot(github_actions.decrypt_members(encrypted, key_file, list(SCHEMAS)))
    result = install_snapshot(cloud, fetch.DATA, backup_dir.expanduser())
    return {**result, "run_url": artifact["run_url"], "conclusion": artifact["run_conclusion"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="MagiaSN/invest-diy", help="GitHub owner/repository")
    parser.add_argument("--branch", help="source branch (default: repository default branch)")
    parser.add_argument("--key-file", type=Path, default=STATE / "sse-data-passphrase")
    parser.add_argument("--backup-dir", type=Path, default=STATE / "backups")
    args = parser.parse_args()
    try:
        result = sync(args.repo, args.branch, args.key_file, args.backup_dir)
    except (OSError, ValueError, RuntimeError, tarfile.TarError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"Source: {result['run_url']} ({result['conclusion']})")
    print(f"Added {result['added']}, corrected {result['corrected']}; {result['total']} observations in total.")
    if result["backup"]:
        print(f"Backup: {result['backup']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
