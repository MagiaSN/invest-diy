"""Candidate ETFs and the definition of the "national team".

The monitored pool is built automatically: holders.py scans the periodic reports of CANDIDATES and adds
every ETF whose national-team holding reached POOL_MIN_PCT in any report (written to data/out/pool.csv).
ETFs the national team has since sold out of stay in the pool, so the exit remains visible.
Before pool.csv exists (first run) FALLBACK_POOL is used.

To add a candidate, add a row to CANDIDATES; codes that do not exist or have no unit data are skipped
when fetching.
"""

INDEX_CODE = "000300"  # CSI 300 index: trading calendar and market reference

FAMILIES = ["沪深300", "上证50/180", "中证500", "中证1000", "创业板", "科创50", "中证A500", "其他宽基"]

# A holder counts as national team if its name contains any keyword (top-ten holder tables); value = group label
NT_KEYWORDS = {
    "中央汇金投资": "汇金投资",
    "中央汇金资产": "汇金资管",
    "中国证券金融": "证金公司",
    "社保基金": "社保基金",
    "社会保障基金": "社保基金",
    "国新投资": "国新",
    "中国国新": "国新",
    "诚通": "诚通",
    "梧桐树投资": "梧桐树",
}

CANDIDATES = [
    # code, short name (Chinese), index family
    {"code": "510300", "name": "华泰柏瑞沪深300", "family": "沪深300"},
    {"code": "510310", "name": "易方达沪深300", "family": "沪深300"},
    {"code": "510330", "name": "华夏沪深300", "family": "沪深300"},
    {"code": "159919", "name": "嘉实沪深300", "family": "沪深300"},
    {"code": "515330", "name": "天弘沪深300", "family": "沪深300"},
    {"code": "510360", "name": "广发沪深300", "family": "沪深300"},
    {"code": "159925", "name": "南方沪深300", "family": "沪深300"},
    {"code": "510050", "name": "华夏上证50", "family": "上证50/180"},
    {"code": "510100", "name": "易方达上证50", "family": "上证50/180"},
    {"code": "510180", "name": "华安上证180", "family": "上证50/180"},
    {"code": "510500", "name": "南方中证500", "family": "中证500"},
    {"code": "512500", "name": "华夏中证500", "family": "中证500"},
    {"code": "159922", "name": "嘉实中证500", "family": "中证500"},
    {"code": "510510", "name": "广发中证500", "family": "中证500"},
    {"code": "510580", "name": "易方达中证500", "family": "中证500"},
    {"code": "512100", "name": "南方中证1000", "family": "中证1000"},
    {"code": "159845", "name": "华夏中证1000", "family": "中证1000"},
    {"code": "560010", "name": "广发中证1000", "family": "中证1000"},
    {"code": "159633", "name": "易方达中证1000", "family": "中证1000"},
    {"code": "159915", "name": "易方达创业板", "family": "创业板"},
    {"code": "159952", "name": "广发创业板", "family": "创业板"},
    {"code": "159949", "name": "华安创业板50", "family": "创业板"},
    {"code": "588000", "name": "华夏科创50", "family": "科创50"},
    {"code": "588080", "name": "易方达科创50", "family": "科创50"},
    {"code": "588050", "name": "工银科创50", "family": "科创50"},
    {"code": "588090", "name": "华泰柏瑞科创50", "family": "科创50"},
    {"code": "512050", "name": "华夏中证A500", "family": "中证A500"},
    {"code": "563360", "name": "华泰柏瑞中证A500", "family": "中证A500"},
    {"code": "159338", "name": "国泰中证A500", "family": "中证A500"},
    {"code": "159352", "name": "南方中证A500", "family": "中证A500"},
    {"code": "560610", "name": "国泰中证A500(沪)", "family": "中证A500"},
    {"code": "563800", "name": "A500龙头", "family": "中证A500"},
    {"code": "563220", "name": "富国中证A500", "family": "中证A500"},
    {"code": "560530", "name": "A500ETF(560530)", "family": "中证A500"},
    {"code": "510210", "name": "富国上证综指", "family": "其他宽基"},
    {"code": "510760", "name": "上证ETF", "family": "其他宽基"},
    {"code": "515800", "name": "中证800ETF", "family": "其他宽基"},
    {"code": "563300", "name": "中证2000ETF", "family": "其他宽基"},
]

# English names for the English UI: fund manager + index
NAME_EN = {
    "510300": "Huatai-PB CSI 300", "510310": "E Fund CSI 300", "510330": "ChinaAMC CSI 300",
    "159919": "Harvest CSI 300", "515330": "Tianhong CSI 300", "510360": "GF CSI 300", "159925": "Southern CSI 300",
    "510050": "ChinaAMC SSE 50", "510100": "E Fund SSE 50", "510180": "Huaan SSE 180",
    "510500": "Southern CSI 500", "512500": "ChinaAMC CSI 500", "159922": "Harvest CSI 500",
    "510510": "GF CSI 500", "510580": "E Fund CSI 500",
    "512100": "Southern CSI 1000", "159845": "ChinaAMC CSI 1000", "560010": "GF CSI 1000", "159633": "E Fund CSI 1000",
    "159915": "E Fund ChiNext", "159952": "GF ChiNext", "159949": "Huaan ChiNext 50",
    "588000": "ChinaAMC STAR 50", "588080": "E Fund STAR 50", "588050": "ICBC CS STAR 50", "588090": "Huatai-PB STAR 50",
    "512050": "ChinaAMC CSI A500", "563360": "Huatai-PB CSI A500", "159338": "Guotai CSI A500",
    "159352": "Southern CSI A500", "560610": "Guotai CSI A500 (SH)", "563800": "CSI A500 Leaders",
    "563220": "Fullgoal CSI A500", "560530": "CSI A500 (560530)",
    "510210": "Fullgoal SSE Composite", "510760": "SSE Index ETF", "515800": "CSI 800 ETF", "563300": "CSI 2000 ETF",
}
for _e in CANDIDATES:
    _e["name_en"] = NAME_EN.get(_e["code"], _e["code"])

# default pool used before pool.csv has been generated
FALLBACK_POOL = ["510300", "510310", "510330", "159919", "510050", "510180", "510500", "512500", "159922",
                 "512100", "159845", "159915", "588000", "588080", "512050", "563360", "159338", "159352"]

BY_CODE = {e["code"]: e for e in CANDIDATES}


def load_pool(out_dir) -> list[dict]:
    """Read pool.csv generated by holders.py, falling back to FALLBACK_POOL."""
    import csv
    path = out_dir / "pool.csv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            codes = [r["code"] for r in csv.DictReader(f) if r["in_pool"] == "1"]
    else:
        codes = FALLBACK_POOL
    return [BY_CODE[c] for c in codes if c in BY_CODE]
