"""A-Share National Team ETF Tracker: estimate net creations from daily exchange unit counts and spot national-team entries and exits."""

TOOL = {
    "slug": "ashare-track-national-team-etf",
    "title": "A股国家队宽基ETF数据跟踪",
    "description": "国家队重仓宽基 ETF（按定期报告自动入池）的每日净申赎、进出场信号，以及由官方持仓推出的减持下界。",
    "kind": "数据跟踪",
    "title_en": "A-Share National Team ETF Tracker",
    "description_en": "Daily net creations and entry/exit signals for broad-based ETFs heavily held by the national team (pool built from fund reports), plus lower bounds on its selling derived from official holdings.",
    "kind_en": "Tracker",
    "update": "python -m investdiy.ashare_track_national_team_etf",
    "asof_file": "data/out/kpi.csv",   # the home page shows the as_of column of the first row as "data as of"
}
