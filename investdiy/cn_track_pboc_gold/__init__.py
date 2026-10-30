"""China PBoC Gold Reserves Tracker: monthly gold holdings of the People's Bank of China, buying streaks and phases, and gold's share of official reserves."""

TOOL = {
    "slug": "cn-track-pboc-gold",
    "title": "中国央行黄金储备数据跟踪",
    "description": "中国人民银行黄金储备的月度持有量（吨 / 万盎司）、增减持、连续增持月数与增持阶段，以及黄金占官方储备资产的比例。",
    "kind": "数据跟踪",
    "title_en": "China PBoC Gold Reserves Tracker",
    "description_en": "Monthly gold holdings of the People's Bank of China (tonnes / ounces), additions, buying streaks and phases, and gold's share of official reserve assets.",
    "kind_en": "Tracker",
    "update": "python -m investdiy.cn_track_pboc_gold",
    "asof_file": "data/out/kpi.csv",   # as_of is the last day of the latest reported month
    # monthly data published around the 7th of the next month, so as_of is normally 7-38 days old
    "max_stale_days": 45,
}
