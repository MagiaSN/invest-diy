"""SSE index catalog and stable keys for the original container series.

Additional components and their units are discovered from each official page.
The legacy keys keep previously collected history compatible.
"""

from __future__ import annotations

# index -> list of (series, keyword in the page, Chinese name, English name)
SERIES: dict[str, list[tuple[str, str, str, str]]] = {
    "ccfi": [
        ("composite", "综合", "综合指数", "Composite"),
        ("europe", "欧洲", "欧洲航线", "Europe"),
        ("med", "地中海", "地中海航线", "Mediterranean"),
        ("uswc", "美西", "美西航线", "US West Coast"),
        ("usec", "美东", "美东航线", "US East Coast"),
        ("japan", "日本", "日本航线", "Japan"),
        ("korea", "韩国", "韩国航线", "Korea"),
        ("seasia", "东南亚", "东南亚航线", "Southeast Asia"),
        ("anz", "澳新", "澳新航线", "Australia / New Zealand"),
        ("pgulf", "波红", "波红航线", "Persian Gulf / Red Sea"),
        ("safrica", "南非", "南非航线", "South Africa"),
        ("wafrica", "东西非", "东西非航线", "West / East Africa"),
        ("samerica", "南美", "南美航线", "South America"),
    ],
    "scfi": [
        ("composite", "综合", "综合指数", "Composite"),
    ],
    "scfis": [
        ("europe", "欧洲", "欧洲航线", "Europe"),
        ("uswc", "美西", "美西航线", "US West Coast"),
    ],
}

INDEX_NAMES = {   # index -> (Chinese, English)
    "ccfi": ("中国出口集装箱运价指数", "China Containerized Freight Index"),
    "scfi": ("上海出口集装箱运价指数", "Shanghai Containerized Freight Index"),
    "scfis": ("上海出口集装箱结算运价指数", "Shanghai Containerized Freight Index (Settlement)"),
    "cicfi": ("中国进口集装箱运价指数", "China Import Containerized Freight Index"),
    "twfi": ("台湾海峡两岸间集装箱运价指数", "Cross-Strait Containerized Freight Index"),
    "seafi": ("东南亚集装箱运价指数", "Southeast Asia Containerized Freight Index"),
    "gcspi": ("全球主干航线准班率", "Global Trade Lane Schedule Reliability"),
    "gcspi_ca": ("班轮公司及联盟准班率", "Carrier and Alliance Schedule Reliability"),
    "gcspi_port": ("港口班轮准班率", "Port Schedule Reliability"),
    "cbfi": ("中国沿海散货运价指数", "China Coastal Bulk Freight Index"),
    "cbcfi": ("中国沿海煤炭运价指数", "China Coastal Coal Freight Index"),
    "cbofi": ("中国沿海金属矿石运价指数", "China Coastal Metallic Ore Freight Index"),
    "cbgfi": ("中国沿海粮食运价指数", "China Coastal Grain Freight Index"),
    "cctfi_coastal": ("中国沿海成品油运价指数", "China Coastal Tanker Freight Index"),
    "cdi": ("中国沿海散货船舶日租金指数", "China Coastal Bulk Ship Daily Hire Index"),
    "fdi": ("远东干散货指数", "Far East Dry Bulk Index"),
    "cdfi": ("中国进口干散货运价指数", "China Import Dry Bulk Freight Index"),
    "ctfi": ("中国进口原油运价指数", "China Import Crude Oil Tanker Freight Index"),
    "csi": ("中国（上海）进口贸易海运指数", "China (Shanghai) Seaborne Import Index"),
    "brsti": ("“一带一路”航贸指数", "Belt and Road Shipping and Trade Index"),
    "brtvi": ("“一带一路”贸易额指数", "Belt and Road Trade Value Index"),
    "brcvi": ("“一带一路”集装箱海运量指数", "Belt and Road Container Volume Index"),
    "srfi": ("“海上丝绸之路”运价指数", "Maritime Silk Road Freight Index"),
    "ccri": ("中国（上海）国际海员薪酬指数", "China Crew Remuneration Index"),
}

MONTHLY = {"gcspi", "gcspi_ca", "gcspi_port", "csi", "brsti", "brtvi", "brcvi", "srfi", "ccri"}
DAILY = {"cbcfi", "cdi", "cdfi", "fdi", "ctfi"}


def frequency(index: str) -> str:
    return "monthly" if index in MONTHLY else "daily" if index in DAILY else "weekly"


def match_series(index: str, label: str) -> str | None:
    for key, word, *_ in SERIES.get(index, []):
        if word in label:
            return key
    return None
