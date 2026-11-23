"""CMOC report inputs from the product sales tables and consolidated income statements."""
import hashlib
import json

from .annual_history import CMOC_GROUPS, grouped_cmoc_years

# Consolidated profit before tax and income tax expense, CNY 100m. Both
# columns of the FY 2019 income statement were public before the FY 2020 anchor.
TAX_SEED = {
    2018: (69.8985741563, 18.3981590939),
    2019: (23.5844846392, 5.9260008607),
}

# Volumes are tonnes, except gold in troy ounces. Revenue and cost are CNY thousands.
# Each product tuple contains production, sales, revenue and cost, in that order.
# Financial tuples contain pretax, tax, parent, NCI and associate income in CNY thousands.
REPORTS = {
    "2023": {
        "url": "https://static.cninfo.com.cn/finalpage/2024-03-23/1219391119.PDF",
        "financial": (13207963.29326, 4677340.66442, 8249711.87251, 280910.75633, 374876.19804),
        "products": {
            "copper": (393_987, 389_791, 24_595_114, 13_453_322),
            "cobalt": (55_526, 29_733, 3_405_808, 2_145_476),
            "molybdenum": (15_635, 15_580, 7_130_781, 4_261_167),
            "tungsten": (7_975, 7_871, 1_480_270, 598_865),
            "niobium": (9_515, 9_378, 2_628_239, 1_734_671),
            "phosphate": (1_168_222, 1_163_521, 3_695_794, 3_046_952),
        },
    },
    "2024": {
        "url": "https://static.cninfo.com.cn/finalpage/2025-03-22/1222869207.PDF",
        "financial": (25124037.23075, 9664594.7408, 13532035.00294, 1927407.48701, 788496.77795),
        "products": {
            "copper": (650_161, 689_521, 41_856_695, 20_819_626),
            "cobalt": (114_165, 108_892, 8_742_978, 5_742_967),
            "molybdenum": (15_396, 14_964, 6_297_175, 4_088_852),
            "tungsten": (8_288, 8_132, 1_822_126, 635_227),
            "niobium": (10_024, 10_028, 2_955_651, 1_848_690),
            "phosphate": (1_180_492, 1_094_743, 3_584_966, 2_668_365),
        },
    },
    "2025": {
        "url": "https://static.cninfo.com.cn/finalpage/2026-04-02/1225072765.PDF",
        "financial": (35161390.55431, 11133983.24672, 20338750.79753, 3688656.51006, 715743.20215),
        "products": {
            "copper": (741_149, 730_176, 55_096_476, 24_704_431),
            "cobalt": (117_549, 51_114, 6_171_143, 2_244_820),
            "molybdenum": (13_906, 14_058, 6_329_854, 3_820_128),
            "tungsten": (7_114, 7_112, 2_422_749, 814_042),
            "niobium": (10_348, 10_347, 3_624_971, 2_014_555),
            "phosphate": (1_213_538, 1_263_477, 4_067_768, 3_040_094),
        },
    },
    "2026H1": {
        "url": "https://static.cninfo.com.cn/finalpage/2026-08-20/1225482748.PDF",
        "financial": (25704798.8444, 7254592.35621, 16152187.48537, 2298019.00282, 208723.33505),
        "products": {
            "copper": (387_961, 376_164, 32_517_992, 12_071_411),
            "cobalt": (65_305, 5_727, 3_158_086, 531_925),
            "molybdenum": (6_779, 6_772, 3_932_618, 2_096_215),
            "tungsten": (3_496, 2_575, 3_194_824, 719_590),
            "niobium": (5_351, 5_583, 1_555_162, 954_273),
            "gold": (100_432, 97_526, 3_017_007, 1_776_386),
            "phosphate": (587_226, 579_264, 2_191_112, 1_853_802),
        },
    },
    "20269M": {
        "url": "https://static.cninfo.com.cn/finalpage/2026-10-24/1225619129.PDF",
        "financial": (38709822.23133, 11018424.90734, 24019512.86956, 3671884.45443, 782688.88721),
        "products": {
            "copper": (596_691, 567_233, 52_416_906, 20_728_654),
            "cobalt": (99_694, 12_661, 3_478_232, 906_076),
            "molybdenum": (9_692, 9_748, 6_109_973, 3_309_937),
            "tungsten": (5_034, 3_830, 3_909_217, 766_429),
            "niobium": (7_999, 8_351, 2_427_970, 1_391_416),
            "gold": (160_913, 158_064, 4_707_290, 2_922_392),
            "phosphate": (831_020, 842_690, 3_378_966, 2_904_462),
        },
    },
}

# Model production in 10,000 tonnes for bulk products and tonnes for the rest.
PRODUCTS = ("copper", "cobalt", "molybdenum", "tungsten", "niobium", "gold", "phosphate")
BULK = {"copper", "cobalt", "phosphate"}
TROY_OUNCE_GRAMS = 31.1034768


def historical_product(product, values):
    # The Brazilian gold operations entered consolidation in January 2026.
    output, sold, revenue, cost = values
    if product == "gold":
        production = output * TROY_OUNCE_GRAMS / 1e6
        sales = sold * TROY_OUNCE_GRAMS / 1000  # kg, matching the shared gold model
        factor = 1000
    else:
        production = output / 10000 if product in BULK else output
        sales, factor = sold, 1
    return {
        "id": product, "production": production, "sales": sales, "factor": factor,
        "conversion": sold / output if output else 0,
        "price": revenue * 1000 / (sales * factor) if sold else 0,
        "cost": cost * 1000 / (sales * factor) if sold else 0,
        "gp": (revenue - cost) / 100000,
    }


def baseline():
    history = grouped_cmoc_years()
    for year, report in REPORTS.items():
        pretax, tax, actual, nci, associate = (v / 100000 for v in report["financial"])
        net = pretax - tax
        products = report["products"]
        metals = [historical_product(k, (0, 0, 0, 0) if k == "gold" and year < "2026" else products[k])
                  for k in PRODUCTS]
        gp = sum(m["gp"] for m in metals)
        history.append({
            "year": year, "months": {"2026H1": 6, "20269M": 9}.get(year, 12),
            "metals": metals, "gp": gp, "pretax": pretax, "associate": associate,
            "other": pretax - gp - associate, "tax": tax / pretax, "net": net,
            "share": actual / net, "actual": actual, "nci": nci, "url": report["url"],
        })
    annual_taxes = dict(TAX_SEED)
    for row in history:
        if row["months"] == 12:
            annual_taxes[int(row["year"])] = (row["pretax"], row["pretax"] - row["net"])
    for row in history:
        year = int(row["year"][:4])
        last_year = year if row["months"] == 12 else year - 1
        years = range(last_year - 2, last_year + 1)
        row["taxWindow"] = dict(firstYear=years.start, lastYear=last_year,
                                pretax=sum(annual_taxes[y][0] for y in years),
                                expense=sum(annual_taxes[y][1] for y in years))
    return {
        "version": 1, "history": history, "verified": "2026-11-23",
        "unit": "Profit CNY 100m; copper/cobalt/phosphate output 10,000 t, other output t; "
                "gold price/cost CNY/g, others CNY/t; gold sales kg, other sales t",
        "thresholds": {"mape": 15, "maxError": 25},
        "source_sha256": hashlib.sha256(json.dumps({"taxSeed": TAX_SEED, **CMOC_GROUPS, **REPORTS}, sort_keys=True).encode()).hexdigest(),
    }
