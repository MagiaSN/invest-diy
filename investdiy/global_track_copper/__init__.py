"""Local copper prices, exchange inventories and cross-market price comparisons."""

TOOL = {
    "slug": "global-track-copper",
    "visibility": "local",
    "title": "全球铜市场数据跟踪",
    "title_en": "Global Copper Market Tracker",
    "description": "跟踪 COMEX、LME、上期所铜价参考序列与库存，统一币种、重量及税率口径，比较相对溢价。",
    "description_en": "COMEX, LME and SHFE copper price references, inventories and relative premiums, with currency, weight and VAT normalization.",
    "kind": "数据跟踪",
    "kind_en": "Tracker",
    "update": "python -m investdiy.global_track_copper",
    "asof_file": "data/out/summary.csv",
}
