"""Global gold valuation, relative prices and official reserves."""

TOOL = {
    "slug": "global-track-gold",
    "visibility": "local",
    "title": "全球黄金数据跟踪",
    "title_en": "Global Gold Tracker",
    "description": "全球黄金估算市值与美债、金油比、金银比，以及主要经济体黄金储备及占比。",
    "description_en": "Estimated global gold value versus US debt, gold/oil and gold/silver ratios, and major economies' official reserves.",
    "kind": "数据跟踪",
    "kind_en": "Tracker",
    "update": "python -m investdiy.global_track_gold",
    "asof_file": "data/out/summary.csv",
    "max_stale_days": 60,
}
