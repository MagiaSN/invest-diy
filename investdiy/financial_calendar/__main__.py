"""Refresh both local financial calendar snapshots."""

import sys

from . import earnings, fetch

if __name__ == "__main__":
    failed = False
    for label, update in [("macro and oversight", fetch.run), ("earnings", earnings.run)]:
        try:
            print(f"Saved {update()} {label} events.")
        except Exception as exc:
            print(f"Could not refresh {label}: {exc}", file=sys.stderr)
            failed = True
    sys.exit(int(failed))
