"""Artifact provenance, safe decryption and lossless local imports."""

import contextlib
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from investdiy.common import github_actions
from investdiy.common.csvio import read_rows, write_rows
from investdiy.global_track_container_freight import sync


def snapshot(day="2026-11-06", value="200", checked="2026-11-07T05:00:00+00:00"):
    def row(filename, **values):
        return {**dict.fromkeys(sync.SCHEMAS[filename], ""), **values}
    return {
        "observations.csv": [row("observations.csv", index="ccfi", series="composite", date=day, value=value, source="sse")],
        "current.csv": [row("current.csv", index="ccfi", series="composite", date=day, value=value,
                            name="Composite", name_en="Composite", unit="points", period=day)],
        "status.csv": [row("status.csv", index="ccfi", date=day, available="1", total="1", status="ok",
                           last_success=checked, checked_at=checked)],
    }


def save(data, rows):
    for name, records in rows.items():
        write_rows(data / name, records, sync.SCHEMAS[name])


class ArtifactTests(unittest.TestCase):
    def test_selects_matching_completed_artifact_across_pages_including_partial_progress(self):
        def artifact(i, **changes):
            return dict(id=i, name="history", expired=False, created_at=f"2026-11-{i:02d}",
                        workflow_run={"id": i, "head_branch": "main"}, **changes)
        a = artifact(6); a["expired"] = True
        b = artifact(5); b["workflow_run"]["head_branch"] = "other"
        def api(endpoint):
            if endpoint == "repos/o/r": return {"id": 1, "default_branch": "main"}
            if endpoint.endswith("workflows/sse.yml"): return {"id": 8}
            if endpoint.endswith("&page=1"): return {"total_count": 101, "artifacts": [a, b, artifact(4), artifact(3)]}
            if endpoint.endswith("&page=2"): return {"total_count": 101, "artifacts": [artifact(2), artifact(1)]}
            i = int(endpoint.rsplit("/", 1)[1])
            return {"workflow_id": 99 if i == 4 else 8, "status": "in_progress" if i == 3 else "completed",
                    "head_repository": {"id": 1}, "html_url": f"https://example.test/{i}", "conclusion": "failure"}
        with patch.object(github_actions, "api", side_effect=api):
            selected = github_actions.latest_artifact("o/r", "sse.yml", "history")
        self.assertEqual(selected["id"], 2)
        self.assertEqual(selected["run_conclusion"], "failure")

    def test_no_retained_artifact_is_an_error(self):
        with patch.object(github_actions, "api", side_effect=[{"id": 1, "default_branch": "main"},
                          {"id": 8}, {"total_count": 0, "artifacts": []}]):
            with self.assertRaisesRegex(RuntimeError, "No retained"):
                github_actions.latest_artifact("o/r", "sse.yml", "history")

    def test_wrong_key_is_not_logged_or_passed_on_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "key"; key.write_bytes(b"private-passphrase\n")
            with patch.object(github_actions.subprocess, "run", return_value=subprocess.CompletedProcess([], 2, b"", b"secret error")) as run:
                with self.assertRaisesRegex(RuntimeError, "decryption failed"):
                    github_actions.decrypt_members(Path(tmp) / "data.gpg", key, ["observations.csv"])
            self.assertNotIn("private-passphrase", str(run.call_args.args))
            self.assertEqual(run.call_args.kwargs["input"], b"private-passphrase")

    def test_tar_symlink_is_rejected_without_extraction(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            entry = tarfile.TarInfo("./observations.csv"); entry.type = tarfile.SYMTYPE; entry.linkname = "/etc/passwd"
            archive.addfile(entry)
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "key"; key.write_text("test")
            with patch.object(github_actions.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output.getvalue(), b"")):
                with self.assertRaisesRegex(ValueError, "Invalid|invalid"):
                    github_actions.decrypt_members(Path(tmp) / "data.gpg", key, ["observations.csv"])


class ImportTests(unittest.TestCase):
    def test_merge_preserves_newer_local_values_and_adds_missing_cloud_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            local = snapshot(value="201", checked="2026-11-07T06:00:00+00:00")
            local["observations.csv"].append(dict(local["observations.csv"][0], date="2020-01-01", source="archive", value="100"))
            save(data, local)
            cloud = snapshot()
            cloud["observations.csv"].append(dict(cloud["observations.csv"][0], date="2026-10-30", value="150"))
            merged, added, corrected = sync.merge_snapshot(cloud, data)
            self.assertEqual((added, corrected), (1, 0))
            self.assertEqual({r["date"]: r["value"] for r in merged["observations.csv"]},
                             {"2020-01-01": "100", "2026-10-30": "150", "2026-11-06": "201"})
            self.assertEqual(merged["current.csv"][0]["value"], "201")

    def test_live_correction_wins_over_archive_and_failed_snapshot_keeps_local_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp); local = snapshot(value="100")
            local["observations.csv"][0]["source"] = "archive"; save(data, local)
            cloud = snapshot(value="101"); cloud["status.csv"][0]["status"] = "error"
            merged, added, corrected = sync.merge_snapshot(cloud, data)
            self.assertEqual((added, corrected), (0, 1))
            self.assertEqual(merged["observations.csv"][0]["value"], "101")
            self.assertEqual(merged["status.csv"][0]["status"], "ok")

    def test_backup_rebuild_and_repeat_import_keep_all_local_history(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync.analyze, "read_archive_metadata", return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            data = Path(tmp) / "data"; backups = Path(tmp) / "backups"
            save(data, snapshot("2026-10-30", "150"))
            (data / "archive").mkdir(); (data / "archive" / "saved.html").write_text("keep")
            original = (data / "observations.csv").read_bytes()
            result = sync.install_snapshot(snapshot(), data, backups)
            self.assertEqual(result["added"], 1)
            with tarfile.open(result["backup"]) as archive:
                self.assertEqual(archive.extractfile("data/observations.csv").read(), original)
            self.assertEqual(len(read_rows(data / "out/history.csv")), 2)
            self.assertEqual((data / "archive/saved.html").read_text(), "keep")
            self.assertEqual(sync.install_snapshot(snapshot(), data, backups)["added"], 0)
            self.assertEqual(len(read_rows(data / "observations.csv")), 2)

    def test_build_failure_does_not_touch_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"; save(data, snapshot())
            before = {p.name: p.read_bytes() for p in data.iterdir()}
            with patch.object(sync.analyze, "main", side_effect=ValueError("invalid")):
                with self.assertRaises(ValueError): sync.install_snapshot(snapshot(), data, Path(tmp) / "backups")
            self.assertEqual(before, {p.name: p.read_bytes() for p in data.iterdir()})

    def test_replace_failure_rolls_back_already_written_files(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sync.analyze, "read_archive_metadata", return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            data = Path(tmp) / "data"; save(data, snapshot("2026-10-30", "150"))
            before = {p.name: p.read_bytes() for p in data.iterdir()}
            replace = sync.os.replace; count = 0
            def fail_second(source, target):
                nonlocal count
                count += 1
                if count == 2: raise OSError("simulated write failure")
                replace(source, target)
            with patch.object(sync.os, "replace", side_effect=fail_second):
                with self.assertRaises(OSError): sync.install_snapshot(snapshot(), data, Path(tmp) / "backups")
            self.assertEqual(before, {p.name: p.read_bytes() for p in data.iterdir() if p.is_file()})

    def test_invalid_snapshot_fails_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp); save(data, snapshot(value="NaN"))
            contents = {name: (data / name).read_bytes() for name in sync.SCHEMAS}
            with self.assertRaisesRegex(ValueError, "invalid observation"):
                sync.decode_snapshot(contents)


if __name__ == "__main__":
    unittest.main()
