"""Reported CNOOC sales, oil and gas cost of sales, and consolidated earnings."""

import hashlib
import json
from typing import NamedTuple


class Report(NamedTuple):
    # Volumes are in million BOE, million barrels and billion cubic feet.
    sold_boe: float
    oil_sold: float
    gas_sold: float
    # Financial statement amounts are in CNY million.
    oil_revenue: int
    gas_revenue: int
    sales_cost: int
    associate: int
    pretax: int
    net: int
    parent: int
    url: str


CNINFO = "https://static.cninfo.com.cn/finalpage/"
COST_DISCLOSURE = CNINFO + "2022-04-20/1212978191.PDF"
REPORTS = {
    "2020": Report(505.8, 406.2, 577.2, 114985, 24616, 81844, -632, 34907, 24956, 24956,
                   "https://www1.hkexnews.hk/listedco/listconews/sehk/2021/0408/2021040800121.pdf"),
    "2021": Report(552.1, 440.5, 648.7, 193027, 29098, 99077, 346, 95821, 70307, 70320,
                   "https://www1.hkexnews.hk/listedco/listconews/sehk/2022/0412/2022041200025.pdf"),
    "2022": Report(603.6, 478.7, 726.2, 311035, 41921, 131920, 1911, 194770, 141677, 141700,
                   CNINFO + "2023-03-30/1216259503.PDF"),
    "2023": Report(653.2, 514.5, 807.4, 282447, 45420, 125816, 1931, 172974, 124090, 123843,
                   CNINFO + "2024-03-22/1219375221.PDF"),
    "2024": Report(712.3, 562.9, 870.3, 307812, 47803, 133674, 1836, 189976, 137982, 137936,
                   CNINFO + "2025-03-28/1222929636.PDF"),
    "2025": Report(757.6, 589.2, 984.0, 279786, 55866, 136138, -472, 169639, 122148, 122082,
                   CNINFO + "2026-03-27/1225036017.PDF"),
    "2026H1": Report(387.7, 303.6, 492.3, 178913, 27173, 80670, 610, 113513, 85869, 85818,
                     CNINFO + "2026-08-27/1225513023.PDF"),
}

# The quarterly announcement supplies realized USD prices, but no joint sales cost.
PRICE_REPORT = {"year": "20269M", "oil": 86.32, "gas": 8.13,
                "url": CNINFO + "2026-10-31/1225649273.PDF"}

GUIDANCE = {"source": "https://ltd.cnooc.com.cn/english/presscenter/pressreleases/2026/202608/t20260826_122439.html",
            "netProduction": 398.7, "mixPeriod": "2026H1",
            "plans": {"2026-mid": 790, "2026-low": 780, "2026-high": 800}}


def baseline():
    history = []
    for year, r in REPORTS.items():
        cost_per_boe = r.sales_cost / r.sold_boe
        metals = []
        for product, volume, boe, revenue in (
            ("oil", r.oil_sold, r.oil_sold, r.oil_revenue),
            ("gas", r.gas_sold, r.sold_boe - r.oil_sold, r.gas_revenue),
        ):
            allocated_cost = boe * cost_per_boe
            metals.append({"id": product, "sales": volume * 1e6, "factor": 1,
                           "price": revenue / volume, "cost": allocated_cost / volume,
                           "gp": (revenue - allocated_cost) / 100})
        gp = (r.oil_revenue + r.gas_revenue - r.sales_cost) / 100
        history.append({
            "company": "cnooc", "year": year, "months": 6 if year == "2026H1" else 12,
            "metals": metals, "gp": gp, "pretax": r.pretax / 100, "associate": r.associate / 100,
            "other": (r.pretax - r.associate) / 100 - gp, "tax": 1 - r.net / r.pretax,
            "actual": r.parent / 100, "net": r.net / 100, "nci": (r.net - r.parent) / 100,
            "url": r.url, "costUrl": COST_DISCLOSURE if year in ("2020", "2021") else r.url,
        })
    mix = REPORTS[GUIDANCE["mixPeriod"]]
    guidance = {**GUIDANCE, "oilSold": mix.oil_sold, "gasSold": mix.gas_sold}
    sources = [REPORTS, COST_DISCLOSURE, PRICE_REPORT, guidance]
    return {"version": 1, "history": history, "priceReport": PRICE_REPORT, "guidance": guidance,
            "unit": "Earnings CNY 100m. Oil volume million bbl, gas volume bcf. "
                    "Canonical prices and allocated costs CNY/bbl and CNY/Mcf.",
            "source_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
            "thresholds": {"mape": 15, "maxError": 25}}
