"""Refresh public sources, retain last-good sections on failure, and export CSVs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sys

from ..common.csvio import atomic_csv, read_rows
from . import demand, fetch, model

DATA = Path(__file__).resolve().parent / 'data'
PRICE_FIELDS = ['date', 'gold', 'silver', 'brent', 'wti', 'gold_brent', 'gold_wti', 'gold_silver']
MARKET_FIELDS = ['date', 'stock_t', 'gold_price', 'gold_usd', 'debt_usd', 'public_debt_usd',
                 'gold_debt_ratio', 'debt_date', 'stock_method', 'stock_left', 'stock_right']
RESERVE_FIELDS = ['date', 'country', 'name', 'name_en', 'gold_t', 'change_t', 'yoy_t',
                  'gold_usd', 'total_usd', 'fx_usd', 'gold_total_pct', 'gold_fx_pct']
SOURCES = {'prices': (fetch.fetch_prices, fetch.WB_PAGE), 'debt': (fetch.fetch_debt, fetch.DEBT_URL),
           'stocks': (fetch.fetch_stocks, fetch.STOCK_PAGE), 'reserves': (fetch.fetch_imf, fetch.IMF_URL),
           'demand': (demand.fetch_demand, demand.PAGE)}


def run(data=DATA, *, offline=False):
    out = data / 'out'
    out.mkdir(parents=True, exist_ok=True)
    old = {r['source']: r for r in read_rows(out / 'sources.csv')}
    statuses, results = [], {}
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    failed = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {key: pool.submit(func, data, offline) for key, (func, _) in SOURCES.items()}
        for key, job in jobs.items():
            status = dict(source=key, status='cached' if offline else 'ok', latest='', fetched_at='',
                          checked_at=now, url=SOURCES[key][1], error='')
            try:
                rows = job.result()
                if not rows:
                    raise ValueError('No observations')
                if key == 'reserves':
                    rows = model.reserves(rows)
                results[key] = rows
                status.update(latest=max(r['date'] for r in rows),
                              fetched_at=old.get(key, {}).get('fetched_at', '') if offline else now)
            except Exception as exc:
                failed = True
                status.update(status='error', error=str(exc), latest=old.get(key, {}).get('latest', ''),
                              fetched_at=old.get(key, {}).get('fetched_at', ''))
                print(f'[{key}] failed; retaining previous output: {exc}', file=sys.stderr)
            statuses.append(status)
    if 'prices' in results:
        atomic_csv(out / 'prices.csv', model.price_ratios(results['prices']), PRICE_FIELDS)
    if 'reserves' in results:
        atomic_csv(out / 'reserves.csv', results['reserves'], RESERVE_FIELDS)
    if 'stocks' in results:
        atomic_csv(out / 'stocks.csv', results['stocks'], ['date', 'stock_t', 'method', 'anchor_date'])
    if 'demand' in results:
        atomic_csv(out / 'demand.csv', results['demand'], demand.FIELDS)
    if all(k in results for k in ('prices', 'debt', 'stocks')):
        market = model.compare_market(results['prices'], results['debt'], results['stocks'])
        if not market or not any(r['gold_debt_ratio'] is not None for r in market):
            raise ValueError('No overlapping gold/debt periods')
        atomic_csv(out / 'market.csv', market, MARKET_FIELDS)
        atomic_csv(out / 'annual.csv', [r for r in market if r['date'][5:7] == '12'], MARKET_FIELDS)
    atomic_csv(out / 'sources.csv', statuses, ['source', 'status', 'latest', 'fetched_at', 'checked_at', 'url', 'error'])
    prices = read_rows(out / 'prices.csv')
    market = read_rows(out / 'market.csv')
    atomic_csv(out / 'summary.csv', [dict(as_of=prices[-1]['date'] if prices else '',
                                        market_as_of=market[-1]['date'] if market else '',
                                        checked_at=now, status='error' if failed else 'ok')],
               ['as_of', 'market_as_of', 'checked_at', 'status'])
    for s in statuses:
        print(f"[{s['source']}] {s['status']} | {s['latest'] or 'unavailable'}")
    return not failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Rebuild using previously validated raw downloads')
    args = parser.parse_args()
    return 0 if run(offline=args.offline) else 1


if __name__ == '__main__':
    raise SystemExit(main())
