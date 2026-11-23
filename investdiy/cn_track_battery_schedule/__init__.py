"""Monthly lithium battery production schedules."""

TOOL = {
    "slug": "cn-track-battery-schedule",
    "visibility": "local",
    "title": "中国锂电池排产数据跟踪",
    "title_en": "China Lithium Battery Production Schedule Tracker",
    "description": "按月查看中国大陆与宁德时代的锂电池排产估计、修订和数据来源。",
    "description_en": "Monthly lithium battery production plans for mainland China and CATL, with revisions and sources.",
    "kind": "数据跟踪",
    "kind_en": "Tracker",
    "update": "python -m investdiy.cn_track_battery_schedule",
    "asof_file": "data/out/monthly.csv",
}
