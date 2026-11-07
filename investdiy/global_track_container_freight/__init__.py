"""Global Shipping Index Tracker: SSE indices and the Xinhua–Panasia PDCI."""

TOOL = {
    "slug": "global-track-container-freight",
    "visibility": "local",
    "title": "全球航运指数数据跟踪",
    "description": "跟踪 SSE 全部航运指数及分项与 PDCI 内贸集装箱运价，涵盖散货、油轮、准班率与航贸数据，显示数据期、单位及更新状态。",
    "kind": "数据跟踪",
    "title_en": "Global Shipping Index Tracker",
    "description_en": "All SSE shipping indices and components plus PDCI domestic container freight, with period dates, units and update status.",
    "kind_en": "Tracker",
    "update": "python -m investdiy.global_track_container_freight --latest-only",
    "asof_file": "data/out/kpi.csv",   # the home page shows the as_of column of the first row as "data as of"
    "max_stale_days": 17,              # weekly data; the scheduled update fails when as_of is older than this
}
