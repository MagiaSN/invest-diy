"""Fetch, import or recompute the local copper dashboard."""

import argparse
from datetime import date
from pathlib import Path

from ..common.csvio import read_rows
from . import fetch
from .model import ROOT, FIELDS, atomic_csv, export, merge, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', default='2020-01-01', type=date.fromisoformat, help='earliest fetched date (upstream coverage may be shorter)')
    parser.add_argument('--skip-fetch', action='store_true', help='recompute stored observations without network requests')
    parser.add_argument('--import-csv', type=Path, help='import validated observations after fetching; matching dates are revised')
    parser.add_argument('--backfill-stocks', action='store_true', help='fill stock gaps from completed COCHILCO monthly reports since --start; preserve existing history')
    parser.add_argument('--fundamentals', action='store_true', help='build annual supply/demand, refining, reviewed forecasts and mines, including with --skip-fetch; reuse downloaded files')
    parser.add_argument('--refresh-fundamentals', action='store_true', help='download annual, refining and mine sources again; revalidate local forecast reviews; implies --fundamentals')
    parser.add_argument('--strict', action='store_true', help='exit nonzero for fetch failures, partial sources, missing or stale series')
    args = parser.parse_args()
    data = ROOT / 'data'
    # Validate the entire import before any network or persistent mutation.
    imported = validate(read_rows(args.import_csv)) if args.import_csv and args.import_csv.is_file() else []
    if args.import_csv and not imported:
        parser.error('Import CSV does not exist or contains no observations')
    statuses = [] if args.skip_fetch else fetch.run(str(args.start), data)
    if imported:
        atomic_csv(data / 'history.csv', merge(read_rows(data / 'history.csv'), imported), FIELDS)
    backfill_status = None
    if args.backfill_stocks:
        from . import backfill
        backfill_status = backfill.run(str(args.start), data)
    daily = export(data)
    print(f'Wrote {len(daily)} daily rows to {data / "out"}')
    fundamental_errors = []
    if not args.skip_fetch or args.fundamentals or args.refresh_fundamentals:
        # Capacity events are disabled: no verified complete global source for
        # annual permanent closures, commissioning and physical construction starts.
        # Retain capacity.py for offline review only; see the tool documentation.
        from . import fundamentals, mines, refining, forecasts
        for name, module in [('annual', fundamentals), ('mines', mines), ('refining', refining), ('forecasts', forecasts)]:
            try:
                rows = module.run(data, refresh=args.refresh_fundamentals)
                print(f'Wrote {len(rows)} {name} rows')
            except Exception as exc:
                fundamental_errors.append(name)
                print(f'{name}: {exc}; previous output retained')
    if not daily:
        return 1
    if args.strict:
        if fundamental_errors:
            return 1
        from .model import SERIES
        rows = read_rows(data / 'history.csv')
        for series, (_, limit) in SERIES.items():
            dates = [r['date'] for r in rows if r['series'] == series]
            if not dates or (date.today() - date.fromisoformat(max(dates))).days > limit:
                return 1
        if any(s['status'] != 'ok' for s in statuses):
            return 1
        if backfill_status and (backfill_status['errors'] or backfill_status['quarantined']):
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
