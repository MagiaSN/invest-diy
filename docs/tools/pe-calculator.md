# PE Valuation Calculator

A browser-only calculator at `/pe-calculator/`. The home page discovers it automatically. It is local-only by default and does not enter public exports. No data download, update command, generated CSV source files or build step is needed; start the normal server:

```bash
.venv/bin/python3 -m investdiy.server
```

## Inputs and interaction

- Add or remove growth stages, each with an integer duration, an annual earnings growth rate and its own distributable profit ratio. Up to 20 stages and 100 total years are supported. Growth ranges from -100% to 1000%; it compounds across stage boundaries. The ratio changes at the beginning of each stage and does not reset earnings.
- Enter an equity risk premium, from 0% to 100%. Each scenario's discount rate is its risk-free rate plus this premium. That discount rate applies to both forecast cash flows and the exit value and is displayed in the scenario table.
- Enter up to 20 risk-free rate scenarios, each above 0% and at most 100%. Commas, Chinese commas, whitespace and semicolons are accepted, with optional percent signs. Duplicate rates are merged and sorted. Risk-free rates also capitalize terminal cash flows under the simplified exit assumption.
- The UI calls the ratio "distributable profit ratio" (利润可分配比例): cash available to equity holders / net income, equivalent to FCFE / earnings in this model. It is not actual dividend payout. Every stage defaults to 100%. Any finite nonnegative percentage is accepted, including values above 100%; negative FCFE needs an explicit annual cash-flow model.
- Set an independent long-run distributable profit ratio, defaulting to 100%, for the years after all forecast stages. It affects terminal value only and does not inherit the last stage's ratio. It starts in year `N+1`, leaving year-N forecast cash unchanged.
- Results update immediately, with PE and forecast-contribution ranges, contribution bars, a scenario table and expandable annual calculations with a scenario selector. Invalid inputs hide previous results and disable export. Language changes preserve inputs and the selected detail scenario.
- Download a scenario CSV containing the risk-free rate, equity risk premium, derived discount rate, `terminal_distributable_ratio_pct`, and encoded stages (`years@growth_percent@distributable_percent` separated by semicolons), full-precision contributions and current PE. For example, `5@20@30;5@3@70` means five years at 20% growth with a 30% ratio, then five years at 3% growth with a 70% ratio. Stable English column names make it usable in spreadsheets.

The illustrative defaults are 5 years of earnings growth at 20%, then 5 years at 3%; a 10% equity risk premium; 100% distributable ratios in both stages and the long run; and 2%, 4%, 6% risk-free rates. These yield discount rates of 12%, 14% and 16%, respectively. The 100% ratios are illustrative assumptions, not universal estimates for businesses. Inputs are not saved or transmitted. No live market data is used.

## Method

Normalize positive current annual earnings to `E_0 = 1`. Let `N` be the total forecast years, `g_t` and `q_t` the earnings growth and distributable profit ratios assigned to year `t` by its stage, `q_terminal` the independent long-run ratio, `i` the scenario risk-free rate, `ERP` the equity risk premium and `d = i + ERP` the scenario discount rate. All rates below are fractions, not percentages. Each ratio is constant within its stage; the long-run ratio applies only after the forecast.

```text
E_t = E_(t-1) * (1 + g_t)
FCFE_t = q_t * E_t
d = i + ERP
Forecast PV = sum(t = 1..N, FCFE_t / (1 + d)^t)
Terminal PE = q_terminal / i
Terminal value at N = E_N * q_terminal / i
Terminal PV = E_N * q_terminal / i / (1 + d)^N
Current PE = Forecast PV + Terminal PV
```

This is a forecast cash-flow plus exit-multiple model. From year `N+1`, earnings stay at `E_N` and FCFE equals `q_terminal * E_N` forever. This may differ from year-N FCFE because the long-run ratio is independent. The risk-free rate capitalizes that level cash flow under the existing simplified exit assumption. Both forecast cash flows and exit value are discounted using the scenario's risk-free rate plus the equity risk premium. Terminal value excludes year-N FCFE, which is already included in the forecast sum. With a 100% long-run ratio, risk-free rates of 2%, 4% and 6% imply terminal PE multiples of 50, 25 and 16.6667.

The reported PE denominator is current annual earnings, not next-year earnings. Cash arrives at year-end, shares outstanding are constant, and the terminal contribution is shown separately so its influence is visible.

FCFE is cash available to equity holders after reinvestment and debt financing, whether or not paid out. A typical reconciliation is net income plus depreciation and amortization, minus capital expenditures and increases in noncash working capital, plus net borrowing. It differs from FCFF, which belongs to both lenders and equity holders. With net income of 100, FCFE of 60 and actual dividends of 30, the input is 60%, not 30%. See [Damodaran's financial definitions](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html).

Available cash retained on the balance sheet is not automatically excluded from FCFE. Forecast FCFE already valued in the model must not also be added as accumulated terminal cash. The calculator does not separately value existing excess cash or forecast its accumulation and investment income. Growth and cash conversion must be chosen consistently with reinvestment; the calculator does not enforce that relationship.

Under the default growth, premium and 2% risk-free rate, setting both stage ratios and the long-run ratio to 30% gives forecast PV of 3.51258 and terminal PV of 13.93168, or PE of 17.44426. This assumes a 30% distributable ratio throughout the forecast and perpetuity. It cannot be inferred solely from an actual dividend payout ratio of 30%.

The theoretical reference is [Aswath Damodaran, Determinants of the PE ratio](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/peratio.htm), which relates PE to growth, payout and required equity returns. This calculator deliberately uses the stated simplified exit-rate assumption rather than estimating a full cost-of-equity model.

## Validation

```bash
node --test tests/test_pe_calculator.cjs
node --check investdiy/pe_calculator/web/model.js
node --check investdiy/pe_calculator/web/strings.js
node --check investdiy/pe_calculator/web/app.js
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/tools.json
```

Analytical checks include a one-year hand calculation, flat earnings with zero premium and all ratios at 100% (`PE = 1 / i` regardless of horizon), stage boundary compounding, distributable ratio changes at stage boundaries, independence of stage and long-run ratios, zero and above-100% ratios, declining earnings, a full earnings loss and rate/premium sensitivity. The 17.44426 PE example is a regression case. Annual present values are checked separately for each scenario. Validation also covers empty, fractional, non-finite and out-of-range inputs and numerical overflow. Inspect the UI in both languages and at a 400px width; confirm a language switch retains stage ratios and the selected detail scenario, adding/removing stages preserves other ratios, discount rates equal risk-free rates plus the premium, and downloaded assumptions reproduce the displayed results.

## Limitations

- Terminal capitalization still uses the risk-free rate `i`, without adding the equity premium to the terminal PE denominator. The premium affects present values through `d = i + ERP`. This simplified exit assumption can overstate terminal value and does not use a single required return for both capitalization and discounting.
- The distributable ratio is constant within each stage; the long-run ratio is constant forever after the forecast. A 100% default means FCFE equals earnings, not that all earnings are distributed. Check cash conversion against reinvestment and financing needs. Setting every stage ratio and the long-run ratio to zero produces zero value because it assumes no FCFE forever; zero cash in a forecast stage alone does not eliminate terminal value.
- Zero or negative current earnings cannot support this PE normalization. Forecast declines are permitted, including -100%; earnings that reach zero cannot recover through percentage growth alone.
- Negative FCFE, separate tax/financing schedules, dilution and existing excess cash are not modeled. A larger terminal contribution makes results more dependent on the exit assumption.
- Values are floating-point estimates. On-screen rounding is for readability; CSV exports retain calculation precision.
