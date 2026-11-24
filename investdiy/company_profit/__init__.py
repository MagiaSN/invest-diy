"""Company earnings forecasts with company-specific models."""

TOOL = {
    "slug": "company-profit",
    "visibility": "public",
    "title": "公司业绩预测",
    "title_en": "Company Earnings Forecast",
    "description": "根据业务销量、售价与成本或单位毛利预测公司利润，支持参数调整、敏感性分析和历史回测。",
    "description_en": "Forecast company earnings from sales volumes and company-specific selling prices, costs or unit gross profits, with editable assumptions, sensitivity analysis and historical validation.",
    "update": "python -m investdiy.company_profit",
    "asof_file": "data/out/market-status.csv",
    "max_stale_days": 7,
    "kind": "计算器",
    "kind_en": "Calculator",
}
