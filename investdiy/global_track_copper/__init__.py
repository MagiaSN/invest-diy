"""Local copper prices, exchange inventories and cross-market price comparisons."""

TOOL = {
    "slug": "global-track-copper",
    "visibility": "local",
    "title": "全球铜市场数据跟踪",
    "title_en": "Global Copper Market Tracker",
    "description": "跟踪 COMEX、LME、上期所铜价、库存与相对溢价，查看全球年度供需及铜矿地图。",
    "description_en": "COMEX, LME and SHFE copper prices, inventories and relative premiums, alongside annual global supply and demand and a copper mine map.",
    "kind": "数据跟踪",
    "kind_en": "Tracker",
    "update": "python -m investdiy.global_track_copper",
    "asof_file": "data/out/summary.csv",
}
