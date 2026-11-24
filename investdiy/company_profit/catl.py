"""CATL's original annual disclosures and the Q4 2026 scenario anchors."""
from __future__ import annotations

import hashlib
import json


def report(path: str) -> str:
    return "https://static.cninfo.com.cn/finalpage/" + path + ".PDF"


# Product tuples are (GWh sold, revenue, cost of sales). Early storage volumes
# are total reported battery sales less EV battery sales (2020 through 2022).
# Monetary figures retain each filing's presentation currency unit.
def annual(year, path, yuan, ev, storage, revenue, cost, expenses, finance,
           investment, other_income, impairment, pretax, tax, net, parent, nonrec,
           *, payroll, other_business, cash, interest_income, interest_expense, fees, associates):
    scale = yuan / 1e8
    products = {}
    for key, (volume, sales, cogs) in zip(("ev", "storage"), (ev, storage)):
        products[key] = {"volume": volume, "revenue": sales * scale, "cost": cogs * scale}
    return {
        "year": year, "url": report(path), "products": products,
        "groupGross": (revenue - cost) * scale,
        "expenses": sum(expenses) * scale,  # Levies, selling, administration and R&D.
        # Consolidated expense notes and the separate other-business line in
        # the revenue/cost note. Production payroll is already in cost of sales.
        "payroll": sum(payroll) * scale,
        "ancillaryBusinessGross": (other_business[0] - other_business[1]) * scale,
        "openingCash": cash[0] * scale, "closingCash": cash[1] * scale,
        "interestIncome": interest_income * scale, "interestExpense": interest_expense * scale,
        "financeFees": fees * scale, "associates": associates * scale,
        "finance": -finance * scale, "investment": investment * scale,
        "otherIncome": other_income * scale, "impairment": sum(impairment) * scale,
        "pretax": pretax * scale, "tax": tax * scale, "net": net * scale,
        "parent": parent * scale,
        # Reported attributable nonrecurring income, its tax and minority effects.
        "nonRecurring": sum(nonrec) * scale,
    }


def baseline():
    history = [
        annual(2020, "2021-04-28/1209834834", 1,
               (44.45, 39425820651.13, 28955599917.98), (2.39, 1943450187.74, 1243285666.92),
               50319487697.20, 36349153592.22,
               (295129893.60, 2216709532.73, 1768115240.89, 3569377694.03),
               -712642421.45, -117648607.80, 1135940385.95, (-341982529.63, -827489419.04),
               6982553409.24, 878635356.78, 6103918052.46, 5583338710.38,
               (1318644334.41, 277761166.31, 125415883.75),
               payroll=(321430416.81, 885591947.00, 1424700624.97),
               other_business=(5521090192.62, 3422501366.22), cash=(32269635327.07, 68424116053.67),
               interest_income=1494600958.67, interest_expense=640434316.54, fees=23617041.40,
               associates=-4027332.09),
        annual(2021, "2022-04-22/1213027750", 10000,
               (116.71, 9149077.45, 7136178.14), (16.70, 1362383.47, 973864.52),
               13035579.64, 9609372.23, (48653.42, 436786.94, 336893.71, 769142.76),
               -64120.00, 123269.90, 167345.41, (-1330.16, -203443.78),
               1988712.91, 202639.90, 1786073.01, 1593131.79, (248895.35, 50461.66, 16866.49),
               payroll=(59813.62, 201230.08, 345213.59), other_business=(978457.49, 341882.56),
               cash=(6842411.61, 8907188.97), interest_income=232326.20, interest_expense=116110.04,
               fees=10173.29, associates=57583.69),
        annual(2022, "2023-03-10/1216084559", 10000,
               (242, 23659349.73, 19596508.67), (47, 4498027.73, 3732737.72),
               32859398.75, 26204960.92, (90748.45, 1109940.12, 697866.94, 1551045.35),
               -279998.58, 251453.86, 303734.48, (-114624.79, -282692.66),
               3667285.62, 321571.27, 3345714.35, 3072916.35, (251606.53, 68918.71, 17957.79),
               payroll=(112920.01, 417701.06, 613959.36), other_business=(1648006.61, 429426.83),
               cash=(8907188.97, 19104340.95), interest_income=398736.52, interest_expense=213237.54,
               fees=21763.20, associates=261451.70),
        annual(2023, "2024-03-16/1219313047", 10000,
               (321, 28525291.73, 22171419.30), (69, 5990052.19, 4564778.20),
               40091704.49, 30907043.40, (169550.77, 1795444.05, 846182.43, 1835610.84),
               -492769.74, 318920.12, 626738.80, (-25404.14, -585392.69),
               5391405.33, 715301.88, 4676103.45, 4412124.83, (402957.47, 119402.68, 78066.39),
               payroll=(134702.41, 455137.47, 742124.83), other_business=(1442717.07, 573282.40),
               cash=(19104340.95, 26430651.47), interest_income=832180.21, interest_expense=344651.58,
               fees=36910.68, associates=374576.20),
        annual(2024, "2025-03-15/1222806982", 1000,
               (381, 253041337, 192461282), (93, 57290460, 41914003),
               362012554, 273518959, (2057466, 3562797, 9689839, 18606756),
               -4131918, 3987823, 9967630, (-872526, -8423325),
               63182039, 9175245, 54006794, 50744682, (5751762, 1665244, 1115034),
               payroll=(1533505, 4707167, 7561191), other_business=(17487818, 8436146),
               cash=(264306515, 303511993), interest_income=9502997, interest_expense=3879076,
               fees=204953, associates=3743040),
        annual(2025, "2026-03-09/1225002666", 1000,
               (541, 316506369, 241064397), (121, 62439820, 45763689),
               423701834, 312383297, (2832322, 3735118, 11666741, 22146581),
               -7939863, 7970552, 10600477, (-418585, -8660164),
               89526545, 12740236, 76786309, 72201282, (7693417, 2017532, 1180684),
               payroll=(1991174, 6626219, 8422709), other_business=(16916612, 4349799),
               cash=(303511993, 333512927), interest_income=10594657, interest_expense=2734017,
               fees=203075, associates=7353106),
    ]
    # The 2023 selling-expense note discloses the warranty amount separately.
    # Starting in FY 2024 the classification moves into product cost of sales.
    history[3]["warrantyInSellingExpenses"] = 1491169.64 / 10000
    # The original FY 2020 audit, PDF page 80 (printed page 72), gives
    # both EV and storage costs. The FY 2019 comparatives in the original
    # FY 2020 consolidated income statement seed the first two-period pool.
    history[0]["costUrl"] = report("2021-04-28/1209834789")
    history[0]["priorIncome"] = {"year": 2019, "pretax": 5760764564.25 / 1e8,
                                  "tax": 748090666.38 / 1e8, "net": 5012673897.87 / 1e8,
                                  "parent": 4560307432.71 / 1e8}
    # Interim consolidated amounts are CNY 100m. H1 supplies other-business
    # GP. Q3 expenses use the 9M less H1 income statements, in CNY thousands.
    forecast = {
        "halfUrl": report("2026-07-24/1225442062"),
        "quarterUrl": report("2026-10-21/1225613175"),
        "callUrl": report("2026-10-21/1225613436"),
        "volume": {"ev": 195, "storage": 65},
        "h1OtherGross": ((276916580 - 210654890) - (192124890 - 152492111)
                         - (53260967 - 40500853)) / 1e5,
        "q3Expenses": ((3539029 + 3371025 + 9315309 + 18516986)
                       - (1324939 + 2163577 + 6019599 + 11376545)) / 1e5,
        "half": {
            "batteryGross": ((192124890 - 152492111) + (53260967 - 40500853)) / 1e5,
            "materialsGross": (18811078 - 13723882) / 1e5,
            "expenses": (1324939 + 2163577 + 6019599 + 11376545) / 1e5,
            "payroll": (1169110 + 3645532 + 4800926) / 1e5,
            "financeFees": 54146 / 1e5,
        },
        "priorNineMonths": {"pretax": 60712402 / 1e5, "tax": 8415535 / 1e5,
                            "net": 52296866 / 1e5, "parent": 49034109 / 1e5},
        "nineMonths": {
            "openingCash": 333512927 / 1e5, "closingCash": 369813786 / 1e5,
            "interestIncome": 7412521 / 1e5, "interestExpense": 2528779 / 1e5,
            "associates": 8435673 / 1e5,
            "parent": 645.30063, "net": 694.98453, "pretax": 810.28004, "tax": 115.29551,
            "groupGross": (442137424 - 341695013) / 1e5,
            "expenses": (3539029 + 3371025 + 9315309 + 18516986) / 1e5,
            "finance": 14.46905, "investment": 90.65705, "otherIncome": 63.88126,
            "impairment": (-642154 - 3595279) / 1e5,
            "nonRecurring": (6654282 + 2164456 + 966209) / 1e5,
        },
    }
    data = {"version": 2, "history": history, "forecast": forecast}
    data["source_sha256"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return data
