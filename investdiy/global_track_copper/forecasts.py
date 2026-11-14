"""Validate a reviewed institutional outlook; never splice projections into history.

Observations live in ignored data/manual files, just like mine-report reviews.
The pinned edition must be reviewed explicitly when a new report is adopted.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import json

from .model import atomic_csv

SOURCE = ('https://www.spglobal.com/content/dam/spglobal/global-assets/en/special-reports/'
          'copper-in-the-age-of-ai/Copper%20in%20the%20Age%20of%20AI_Full%20Report_January%202026.pdf')
EDITION = '2026-01'
SCENARIO = 'spglobal-2026-baseline'
FIELDS = ['year', 'forecast_supply_t', 'forecast_demand_t', 'forecast_balance_t',
          'primary_supply_t', 'secondary_supply_t', 'scenario', 'publication', 'source',
          'source_table', 'reviewed_at', 'precision_t']


def validate(payload):
    """Require one consistent edition, units, paired years and reported totals."""
    expected = dict(source=SOURCE, publication=EDITION, scenario=SCENARIO,
                    unit='MMt Cu', source_table='Appendix B, Figures 83 and 84',
                    scope='Total copper demand; baseline primary plus secondary supply')
    if not isinstance(payload, dict) or any(payload.get(k) != v for k, v in expected.items()):
        raise ValueError('Unexpected copper forecast edition, scenario, scope or units')
    reviewed = date.fromisoformat(payload['reviewed_at'])
    if not date(2026, 1, 1) <= reviewed <= date.today():
        raise ValueError('Invalid forecast review date')
    records = payload['observations']
    # Keep the report's baseline estimates for validation, but export projections only.
    if [r.get('year') for r in records] != list(range(2024, 2041)):
        raise ValueError('Expected unique, ordered 2024–2040 source columns')
    def tonnes(value):
        try:
            n = Decimal(str(value))
            if not n.is_finite() or not 0 < n < 100 or n * 10 != (n * 10).to_integral_value():
                raise ValueError('Invalid forecast value or source precision')
            return int(n * 1_000_000)
        except InvalidOperation as exc:
            raise ValueError('Invalid forecast number') from exc
    rows = []
    for r in records:
        supply, demand, primary, secondary = [tonnes(r[k]) for k in
            ['supply_mmt', 'demand_mmt', 'primary_mmt', 'secondary_mmt']]
        if abs(primary + secondary - supply) > 100_000:
            raise ValueError('Forecast supply components disagree beyond source rounding')
        if r['year'] < 2026:
            continue
        rows.append(dict(year=r['year'], forecast_supply_t=supply, forecast_demand_t=demand,
                         forecast_balance_t=supply - demand, primary_supply_t=primary,
                         secondary_supply_t=secondary, scenario=SCENARIO, publication=EDITION,
                         source=SOURCE, source_table=payload['source_table'],
                         reviewed_at=payload['reviewed_at'], precision_t=100_000))
    return rows


def run(data, *, refresh=False):
    """Revalidate local evidence on every run; refresh cannot fabricate a new edition."""
    path = data / 'manual' / 'copper-forecast-spglobal-2026.json'
    if not path.exists():
        raise FileNotFoundError(f'Reviewed forecast input missing: {path}; see tool documentation')
    rows = validate(json.loads(path.read_text(encoding='utf-8')))
    atomic_csv(data / 'out' / 'forecasts.csv', rows, FIELDS)
    return rows
