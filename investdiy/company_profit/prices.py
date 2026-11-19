"""Fetch a complete metal-price and FX snapshot during page builds only."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import math
import re
from xml.etree import ElementTree

from ..common import net

SHANGHAI = timezone(timedelta(hours=8))
SYMBOLS = {"gold": ("au", "CNY/g"), "copper": ("cu", "CNY/t"),
           "zinc": ("zn", "CNY/t"), "silver": ("ag", "CNY/kg")}
BASE_URL = "https://www.shfe.com.cn/data/tradedata/future/delaymarket/delaymarket_{}.dat"
SOURCE_PAGE = "https://www.shfe.com.cn/reports/marketdata/delayedquotes/"
FX_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FX_PAGE = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html"


def parse_quote(payload: dict, metal: str, now: datetime) -> dict:
    """Select the greatest-open-interest valid contract on the latest observation date."""
    symbol, unit = SYMBOLS[metal]
    candidates = []
    for row in payload.get("delaymarket", []):
        try:
            contract = row["contractname"]
            if row["instrumentid"] != symbol or not re.fullmatch(symbol + r"\d{4}", contract):
                continue
            price, interest, volume = (float(row[key]) for key in ("lastprice", "openinterest", "volume"))
            stamp = datetime.strptime(row["updatetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=SHANGHAI)
            if (not all(math.isfinite(v) for v in (price, interest, volume)) or
                    price <= 0 or price > 1e7 or interest <= 0 or volume <= 0 or
                    not timedelta(minutes=-5) <= now - stamp <= timedelta(days=7)):
                continue
            candidates.append((stamp, interest, volume, contract, price))
        except (KeyError, ValueError, TypeError):
            continue
    if not candidates:
        raise ValueError(f"No valid recent SHFE quote for {metal}")
    latest_day = max(c[0].date() for c in candidates)
    stamp, interest, volume, contract, price = max(
        (c for c in candidates if c[0].date() == latest_day), key=lambda c: (c[1], c[2], c[3]))
    return {"id": metal, "contract": contract, "price": price, "unit": unit,
            "quoted_at": stamp.isoformat(), "open_interest": interest,
            "source_url": BASE_URL.format(symbol), "older_than_day": now - stamp > timedelta(days=1)}


def parse_fx(text: str, now: datetime) -> dict:
    """Cross same-day ECB CNY/EUR and USD/EUR references into CNY/USD."""
    root = ElementTree.fromstring(text)
    dated = [node for node in root.iter() if "time" in node.attrib]
    if len(dated) != 1:
        raise ValueError("Expected one ECB reference date")
    node = dated[0]
    day = datetime.strptime(node.attrib["time"], "%Y-%m-%d").date()
    if not 0 <= (now.date() - day).days <= 7:
        raise ValueError("ECB reference date is stale or in the future")
    rates = {}
    for child in node:
        currency = child.attrib.get("currency")
        if currency not in ("USD", "CNY"):
            continue
        rate = float(child.attrib["rate"])
        if currency in rates or not math.isfinite(rate) or rate <= 0:
            raise ValueError("Invalid ECB reference rate")
        rates[currency] = rate
    if set(rates) != {"USD", "CNY"}:
        raise ValueError("Missing ECB USD or CNY reference")
    value = rates["CNY"] / rates["USD"]
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Invalid CNY/USD cross rate")
    return {"cny_per_usd": value, "as_of": day.isoformat(), "source": "ECB",
            "source_url": FX_PAGE, "data_url": FX_URL, "eur_rates": rates}


def fetch_snapshot() -> dict:
    """Fetch every component afresh; a partial failure must not replace saved data."""
    now = datetime.now(SHANGHAI)

    def fetch(metal):
        response = net.get(BASE_URL.format(SYMBOLS[metal][0]), retries=2, timeout=12,
                           headers={"Referer": SOURCE_PAGE})
        return parse_quote(response.json(), metal, now)

    with ThreadPoolExecutor(max_workers=5) as pool:
        quote_jobs = [pool.submit(fetch, metal) for metal in SYMBOLS]
        fx_job = pool.submit(net.get, FX_URL, retries=2, timeout=12)
        quotes = [job.result() for job in quote_jobs]
        fx = parse_fx(fx_job.result().text, now)
    return {"source": "SHFE", "source_url": SOURCE_PAGE, "delay_minutes": 30,
            "fetched_at": now.isoformat(), "quotes": quotes, "fx": fx,
            "conversion": {"vat_pct": {"gold": 0, "copper": 13, "zinc": 13, "silver": 13},
                           "realization_pct": 100}}
