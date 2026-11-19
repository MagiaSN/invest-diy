"""Company profit forecasts with company-specific models."""

TOOL = {
    "slug": "company-profit",
    "visibility": "public",
    "title": "公司利润预测",
    "title_en": "Company Profit Forecast",
    "description": "基于业务量、价格和成本预测公司利润，支持参数调整、敏感性分析和历史回测。",
    "description_en": "Forecast company earnings from business volumes, prices and costs, with editable assumptions, sensitivity analysis and historical validation.",
    "update": "python -m investdiy.company_profit",
    "asof_file": "data/out/market-status.csv",
    "max_stale_days": 7,
    "kind": "计算器",
    "kind_en": "Calculator",
}
