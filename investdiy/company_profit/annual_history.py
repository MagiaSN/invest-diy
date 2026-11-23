"""Additional annual disclosures for the rolling validation window. Financials are CNY."""
import hashlib
import json

# Product rows are group output (display units), consolidated units sold (kg for
# precious metals, tonnes otherwise), realized price and unit sales cost.
ZIJIN = {
    "2020": {
        "url": "https://www.zjky.cn/investor/year-report.jsp?nowPage=2",
        "products": [
            ("gold", 40.509, 38_213, 364.98, 177.38),
            ("copper", 45.3447, 449_943, 37_316, 20_095),
            ("zinc", 34.2131, 347_604, 9_621, 6_570),
            ("silver", 298.715, 286_943, 3.17, 1.45),
        ],
        "financial": (10_846_027_174, 2_387_988_221, 6_508_553_913, 1_949_485_040, 209_744_927),
    },
    "2021": {
        "url": "https://www.zjky.cn/upload/file/2022/03/18/689c56d9d3a84d14bf7d17ae70d3b1eb.pdf",
        "products": [
            ("gold", 47.459, 45_662, 348.69, 176.22),
            ("copper", 58.4165, 528_686, 53_583, 18_194),
            ("zinc", 39.6443, 399_261, 14_136, 7_369),
            ("silver", 308.806, 305_763, 3.43, 1.57),
        ],
        "financial": (24_793_810_492, 5_194_172_140, 15_672_870_591, 3_926_767_761, 1_627_111_396),
    },
}

# Each pair of sales volumes is in tonnes, in the order of the product-group
# name. Financial notes report group revenue and cost of sales in CNY.
CMOC_GROUPS = {
    "2020": {
        "url": "https://static.cninfo.com.cn/finalpage/2021-03-23/1209426961.PDF",
        "products": [
            ("copperCobalt", (185_680, 17_333), 8_294_366_471.14, 6_642_681_663.76),
            ("molyTungsten", (13_641, 8_590), 3_550_860_438.37, 2_225_528_480.14),
            ("niobiumPhosphate", (9_674, 1_140_756), 2_817_176_587 + 2_378_092_057.58,
             1_665_558_572.28 + 2_031_945_616.41),
        ],
        "financial": (2_876_289_792.11, 397_649_247.09, 2_328_787_511.92, 149_853_033.10, -11_735_678.34),
    },
    "2021": {
        "url": "https://static.cninfo.com.cn/finalpage/2022-03-19/1212626342.PDF",
        "products": [
            ("copperCobalt", (205_081, 17_085), 13_268_256_624.20, 6_241_622_321.72),
            ("molyTungsten", (16_562, 8_366), 5_350_413_902.79, 3_162_552_021.69),
            ("niobiumPhosphate", (8_489, 1_129_770), 5_086_841_778.80, 3_615_904_038.10),
        ],
        "financial": (8_755_314_341.72, 3_327_700_999.16, 5_106_017_249.81, 321_596_092.75, -2_281_770.77),
    },
    "2022": {
        "url": "https://static.cninfo.com.cn/finalpage/2023-03-18/1216148712.PDF",
        "products": [
            ("copperCobalt", (130_414, 12_560), 9_748_225_331.68, 5_183_855_582.32),
            ("molyTungsten", (16_044, 7_745), 6_965_368_091.42, 4_020_610_663.20),
            ("niobiumPhosphate", (9_105, 1_157_340), 7_368_147_038.65, 4_566_124_333.17),
        ],
        "financial": (9_804_466_705.79, 2_612_765_878.42, 6_066_946_564.19, 1_124_754_263.18, 645_307_049.56),
    },
}


def annual_row(year, report, metals):
    pretax, tax, parent, nci, associate = (x / 1e8 for x in report["financial"])
    gp = sum(m["gp"] for m in metals)
    net = pretax - tax
    return dict(year=year, months=12, url=report["url"], metals=metals, gp=gp, pretax=pretax,
                tax=tax / pretax, actual=parent, share=parent / net, nci=nci, net=net,
                associate=associate, other=pretax - gp - associate)


def extend_zijin(data):
    existing = {row["year"] for row in data["history"]}
    additions = []
    for year, report in ZIJIN.items():
        if year in existing:
            continue
        metals = []
        for product, output, sales, price, cost in report["products"]:
            precious = product in ("gold", "silver")
            factor = 1000 if precious else 1
            metals.append(dict(id=product, production=output, sales=sales, price=price, cost=cost,
                               factor=factor, gp=sales * (price - cost) * factor / 1e8,
                               conversion=sales / (output * (1000 if precious else 10000))))
        additions.append(annual_row(year, report, metals))
    if additions:
        data["history"] = sorted(additions + data["history"], key=lambda row: (row["year"][:4], row["months"]))
        data["source_sha256"] = hashlib.sha256(json.dumps([data["source_sha256"], additions],
                                                           sort_keys=True).encode()).hexdigest()


def grouped_cmoc_years():
    rows = []
    for year, report in CMOC_GROUPS.items():
        metals = []
        for product, volumes, revenue, cost in report["products"]:
            sales = sum(volumes)
            metals.append(dict(id=product, sales=sales, factor=1, price=revenue / sales,
                               cost=cost / sales, gp=(revenue - cost) / 1e8))
        rows.append({**annual_row(year, report, metals), "grouped": True})
    return rows
