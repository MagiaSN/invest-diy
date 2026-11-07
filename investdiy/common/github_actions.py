"""Download completed workflow artifacts and read selected files from encrypted backups."""

from __future__ import annotations

import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def _gh(*args: str) -> bytes:
    result = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError("GitHub request failed; check gh auth status and repository access.")
    return result.stdout


def api(endpoint: str) -> dict:
    return json.loads(_gh("api", endpoint))


def latest_artifact(repo: str, workflow: str, name: str, branch: str | None = None) -> dict:
    """Select the newest unexpired artifact, including saved progress from failed runs."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("Repository must be owner/name.")
    repository = api(f"repos/{repo}")
    branch = branch or repository["default_branch"]
    workflow_id = api(f"repos/{repo}/actions/workflows/{workflow}")["id"]
    candidates = []
    page = 1
    while True:
        data = api(f"repos/{repo}/actions/artifacts?per_page=100&page={page}")
        candidates.extend(a for a in data["artifacts"] if a["name"] == name and not a["expired"]
                          and a.get("workflow_run", {}).get("head_branch") == branch)
        if page * 100 >= data["total_count"] or not data["artifacts"]:
            break
        page += 1
    for artifact in sorted(candidates, key=lambda a: (a["created_at"], a["id"]), reverse=True):
        run = api(f"repos/{repo}/actions/runs/{artifact['workflow_run']['id']}")
        if (run["workflow_id"] == workflow_id and run["status"] == "completed"
                and (run.get("head_repository") or {}).get("id") == repository["id"]):
            return {**artifact, "run_url": run["html_url"], "run_conclusion": run["conclusion"]}
    raise RuntimeError(f"No retained {name} artifact from completed {workflow} runs on {branch}.")


def download_member(repo: str, artifact_id: int, filename: str, destination: Path) -> None:
    """Read one exact ZIP member, without extracting paths supplied by the artifact."""
    payload = _gh("api", f"repos/{repo}/actions/artifacts/{artifact_id}/zip")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = [entry for entry in archive.infolist() if entry.filename == filename]
        if len(entries) != 1 or entries[0].file_size > 256 * 1024 * 1024:
            raise ValueError("Missing, duplicate or oversized encrypted snapshot.")
        destination.write_bytes(archive.read(entries[0]))


def decrypt_members(encrypted: Path, key_file: Path, filenames: list[str]) -> dict[str, bytes]:
    """Pass the key over stdin and read only regular, explicitly requested TAR members."""
    key = key_file.expanduser().read_bytes().strip()
    if not key:
        raise ValueError("The decryption key file is empty.")
    with tempfile.TemporaryDirectory(prefix="invest-diy-gpg-") as home:
        result = subprocess.run([
            "gpg", "--homedir", home, "--batch", "--pinentry-mode", "loopback",
            "--passphrase-fd", "0", "--decrypt", str(encrypted),
        ], input=key, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError("Snapshot decryption failed; local data has not been changed.")
    contents = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:gz") as archive:
        members = archive.getmembers()
        for name in filenames:
            matches = [m for m in members if m.name in (name, "./" + name)]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 256 * 1024 * 1024:
                raise ValueError(f"Missing, invalid or oversized snapshot member: {name}")
            contents[name] = archive.extractfile(matches[0]).read()
    return contents
