"""Monthly US inflation, employment and federal funds data."""

TOOL = {
    "slug": "us-track-macro",
    "visibility": "public",
    "title": "美国宏观经济数据跟踪",
    "description": "每月 CPI、PPI、PCE、失业率、非农就业总人数与新增就业，以及联邦基金有效利率。",
    "kind": "数据跟踪",
    "title_en": "US Macroeconomic Tracker",
    "description_en": "Monthly CPI, PPI, PCE, unemployment, total nonfarm payrolls and job gains, and the effective federal funds rate.",
    "kind_en": "Tracker",
    "update": "python -m investdiy.us_track_macro",
    "asof_file": "data/out/monthly.csv",
    "max_stale_days": 75,
}
