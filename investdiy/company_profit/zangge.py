"""Original Zangge filings: product sales, consolidated income and Julong equity income."""
import hashlib
import json

# Product tuples contain tonnes sold, revenue and cost of sales (CNY).
# Financial tuples contain pre-tax profit, income tax, parent profit and NCI (CNY).
# Julong income is the amount recognized by Zangge on its acquisition-date basis.
REPORTS = {
    "2020": {
        "url": "2021-04-13/1209678638",
        "potash": (1_130_900, 1_826_229_834.41, 1_209_998_501.37),
        "lithium": (2_013.35, 63_545_800.81, 65_816_302.69),
        "financial": (307_438_778.23, 78_551_261.23, 228_887_517, 0),
        "julong": -226_689_228.01,
    },
    "2021": {
        "url": "2022-03-11/1212540184",
        "potash": (1_068_100, 2_660_999_095.64, 1_099_701_384.42),
        "lithium": (10_960.21, 946_208_161.95, 380_785_989.61),
        "financial": (1_694_922_647.69, 267_582_716.63, 1_427_339_931.06, 0),
        "julong": 236_783_952.62,
    },
    "2022": {
        "url": "2023-03-10/1216083648",
        "potash": (1_101_400, 3_834_902_439.26, 1_114_671_769.24),
        "lithium": (10_707, 4_323_349_152.15, 337_219_966.01),
        "financial": (6_593_009_612.40, 938_136_751.69, 5_654_872_860.71, 0),
        "julong": 724_904_528.90,
    },
    "2023": {
        "url": "2024-03-21/1219359611",
        "potash": (1_293_400, 3_215_310_642.93, 1_408_306_538.11),
        "lithium": (10_314.50, 1_979_983_731.37, 385_811_907.13),
        "financial": (3_866_309_898.90, 453_955_472.43, 3_419_880_869.14, -7_526_442.67),
        "julong": 1_296_196_116.72,
    },
    "2024": {
        "url": "2025-03-29/1222951087",
        "potash": (1_044_900, 2_210_223_570.38, 1_219_444_256.25),
        "lithium": (13_582, 1_021_649_352.54, 557_431_111.63),
        "financial": (2_708_528_965.76, 139_255_274.32, 2_579_985_938.80, -10_712_247.36),
        "julong": 1_927_683_585.59,
    },
    "2025": {
        "url": "2026-03-14/1225009932",
        "potash": (1_084_300, 2_948_852_813.24, 1_042_713_972.90),
        "lithium": (8_957, 592_742_029.58, 386_352_904.01),
        "financial": (4_055_322_495.43, 218_058_785.86, 3_852_353_240.98, -15_089_531.41),
        "julong": 2_782_419_161.74, "copperSales10kt": 19.37, "stakePct": 30.78,
        "zijinPrice": 63_613, "zijinCost": 22_362, "mineTaxPct": 9,
        "copperProxyUrl": "https://www.zjky.cn/upload/file/2026/03/20/d212b7afcbde4c9f8a169d100b36971b.pdf",
    },
    "2026H1": {
        "url": "2026-08-11/1225466935",
        "potash": (525_300, 1_472_408_944.41, 512_559_925.27),
        "lithium": (3_990, 582_422_224.19, 168_416_416.91),
        "financial": (3_795_350_770.76, 166_092_285.06, 3_638_081_370.05, -8_822_884.35),
        "julong": 2_838_809_519.25, "copperSales10kt": 13.35, "stakePct": 30.78,
        "zijinPrice": 82_624, "zijinCost": 24_480, "mineTaxPct": 9,
        "copperProxyUrl": "https://static.cninfo.com.cn/finalpage/2026-08-22/1225550244.PDF",
    },
    "20269M": {
        "url": "2026-10-17/1225608840",
        # The Q3 operating table rounds revenue and gives costs per tonne.
        "potash": (729_400, 2_042_000_000, 729_400 * 1001.59),
        "lithium": (9_210, 1_260_000_000, 9_210 * 36_500),
        "financial": (6_366_020_060.02, 269_200_050.68, 6_109_350_713.86, -12_530_704.52),
        "julong": 4_708_000_000, "copperSales10kt": 21.65, "stakePct": 30.78,
        "zijinPrice": 84_545, "zijinCost": 25_075, "mineTaxPct": 9,
        "copperProxyUrl": "https://static.cninfo.com.cn/finalpage/2026-10-24/1225620996.PDF",
    },
}


def baseline():
    history = []
    for year, report in REPORTS.items():
        pretax, tax, actual, nci = (v / 1e8 for v in report["financial"])
        associate = report["julong"] / 1e8
        metals = []
        for product in ("potash", "lithium"):
            sold, revenue, cost = report[product]
            metals.append(dict(id=product, sales=sold, factor=1, price=revenue / sold,
                               cost=cost / sold, gp=(revenue - cost) / 1e8))
        gp = sum(m["gp"] for m in metals)
        row = dict(year=year, months={"2026H1": 6, "20269M": 9}.get(year, 12),
                   metals=metals, gp=gp, associate=associate, other=pretax - gp - associate,
                   pretax=pretax, tax=tax / pretax, operatingTax=tax / (pretax - associate),
                   net=pretax - tax, actual=actual, nci=nci,
                   url=f"https://static.cninfo.com.cn/finalpage/{report['url']}.PDF")
        if "copperSales10kt" in report:
            # Reconcile the group concentrate proxy to acquisition-basis mine earnings.
            sales = report["copperSales10kt"] * 10000
            unit_net = report["julong"] / (report["stakePct"] / 100) / sales
            unit_pretax = unit_net / (1 - report["mineTaxPct"] / 100) if unit_net > 0 else unit_net
            row.update(julongSales=report["copperSales10kt"], julongStake=report["stakePct"],
                       julongPrice=report["zijinPrice"], julongCost=report["zijinCost"],
                       julongTaxPct=report["mineTaxPct"], copperProxyUrl=report["copperProxyUrl"],
                       julongOtherPerTonne=unit_pretax - (report["zijinPrice"] - report["zijinCost"]))
        history.append(row)
    return dict(version=1, history=history, verified="2026-11-24",
                unit="Profit CNY 100m; potash and Julong copper input 10,000 t; lithium carbonate t; "
                     "prices, unit costs and Julong other pre-tax items CNY/t",
                thresholds={"mape": 15, "maxError": 25},
                source_sha256=hashlib.sha256(json.dumps(REPORTS, sort_keys=True).encode()).hexdigest())
