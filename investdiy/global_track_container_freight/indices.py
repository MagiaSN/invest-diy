"""The indices and series tracked, with the labels used to find them in the Shanghai Shipping Exchange pages.

Every index is in points. Bases: CCFI 1998-01-01 = 1000, SCFI 2009-10-16 = 1000, SCFIS 2020-06-01 = 1000.
Each series is matched by the first keyword contained in a table row's first cell (Chinese label), so a
more specific keyword must come before a shorter one that it contains.
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
}


def match_series(index: str, label: str) -> str | None:
    for key, word, *_ in SERIES[index]:
        if word in label:
            return key
    return None
