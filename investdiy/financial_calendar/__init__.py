"""Upcoming financial releases and policy meetings."""

TOOL = {
    "slug": "financial-calendar",
    "visibility": "local",
    "title": "金融大事日历",
    "description": "查看标普 500、纳斯达克 100、恒生指数及沪深 300 成份公司的财报日历，以及美国就业、通胀、美联储议息和英伟达与黄仁勋的国会与调查日程。",
    "kind": "日历",
    "title_en": "Financial Events Calendar",
    "description_en": "Company earnings for the S&P 500, Nasdaq-100, Hang Seng Index and CSI 300, plus US employment, inflation, Fed meetings and oversight of NVIDIA and Jensen Huang.",
    "kind_en": "Calendar",
    "update": "python -m investdiy.financial_calendar",
    "asof_file": "data/out/events.csv",
}
