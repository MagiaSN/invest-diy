"""Run with python -m investdiy.us_track_macro [--skip-fetch]."""

import argparse
import sys

from .fetch import run


def main():
    parser = argparse.ArgumentParser(description="Update monthly US macroeconomic data from FRED, BLS and BEA")
    parser.add_argument("--skip-fetch", action="store_true", help="rebuild from the saved snapshot without changing its fetch time")
    args = parser.parse_args()
    try:
        run(skip_fetch=args.skip_fetch)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
