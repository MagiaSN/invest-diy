"""Global Container Freight Tracker: weekly CCFI, SCFI and SCFIS freight indices from the Shanghai Shipping Exchange."""

TOOL = {
    "slug": "global-track-container-freight",
    "title": "全球集装箱运价数据跟踪",
    "description": "上海航运交易所每周发布的中国出口集装箱运价指数（CCFI，含 12 条航线）、上海出口集装箱运价指数（SCFI）与结算运价指数（SCFIS）。",
    "kind": "数据跟踪",
    "title_en": "Global Container Freight Tracker",
    "description_en": "Weekly China and Shanghai containerized freight indices (CCFI with its 12 trade lanes, SCFI) and the settlement index SCFIS, published by the Shanghai Shipping Exchange.",
    "kind_en": "Tracker",
    "update": "python -m investdiy.global_track_container_freight",
    "asof_file": "data/out/kpi.csv",   # the home page shows the as_of column of the first row as "data as of"
    "max_stale_days": 17,              # weekly data; the scheduled update fails when as_of is older than this
}
