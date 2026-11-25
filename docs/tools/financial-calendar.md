# Financial Events Calendar

Open [the financial calendar](https://invest-diy.surge.sh/financial-calendar/) to see company earnings, announced US releases, FOMC meetings and oversight events involving NVIDIA and Jensen Huang for the current month and the next three months. Each monthly calendar runs Monday through Sunday with one week per row. The US Macro filter groups employment reports, inflation releases and Fed meetings. Earnings and NVIDIA / Huang have their own filters. The earnings filter supports index, ticker and company name searches. Select an event for its dates, timing or reporting status and a link to its source.

## Sources

| Event | Schedule |
|---|---|
| Nonfarm payrolls and the unemployment rate | One [BLS Employment Situation release](https://www.bls.gov/schedule/news_release/empsit.htm) contains both figures. |
| Consumer and producer prices | BLS publishes separate [CPI](https://www.bls.gov/schedule/news_release/cpi.htm) and [PPI](https://www.bls.gov/schedule/news_release/ppi.htm) dates. |
| PCE prices | The [BEA calendar subscription](https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics) lists the Personal Income and Outlays release. |
| FOMC meetings | The [Federal Reserve meeting calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) supplies the start and end dates. Future meeting dates can be tentative. |

### Company earnings

The updater queries the full [S&P 500](https://www.tradingview.com/symbols/SPX/components/), [Nasdaq-100](https://www.tradingview.com/symbols/NASDAQ-NDX/components/), [Hang Seng Index](https://www.tradingview.com/symbols/HSI-HSI/components/) and [CSI 300](https://www.tradingview.com/symbols/SSE-000300/components/) constituent lists each time. Coverage counts are securities per index, including share classes. The same listing can belong to multiple indices. Listings with the same issuer name, fiscal period and release day share one calendar entry. The detail dialog lists the associated tickers and indices.

[TradingView](https://www.tradingview.com/blog/en/earnings-dates-in-stock-screener-46267/) supplies the latest reported release and the next expected release when available. [Eastmoney](https://data.eastmoney.com/bbsj/) supplies A-share disclosure appointments and actual release dates. An actual release takes precedence over an appointment for the same listing and fiscal period. Tencent Finance supplies Chinese display names when available.

Reports appear on the listing market’s local calendar day. The fiscal period end month appears separately in the detail dialog. An estimated or scheduled date can move. Passing that date does not automatically mark a report as published. A constituent without a known date in the displayed months has no calendar entry.

### NVIDIA and Jensen Huang

The calendar includes dated congressional appearances, requests and briefing deadlines, investigative subpoenas, agency announcements and company disclosures about internal inquiries. Each entry links to the issuing committee, agency or company. An announcement is dated to its publication and a subpoena to its service. Future appearances use the announced date and include a clock time only where published. The event detail identifies the witness or subject and the action taken.

These one-off notices are manually reviewed in `investdiy/financial_calendar/nvidia_notices.json`. The update command merges the reviewed entries into the same calendar CSV as the macro releases. Edit the notices when a committee reschedules an appearance or an agency publishes a new milestone. Update the review date after checking the source list. The detail dialog shows this date independently of the macro refresh.

## Dates and coverage

Each month is shown from its first through its last day. Days before today in US Eastern time are shaded, and their releases and meeting dates remain available throughout the month. The window rolls forward on the first of each month. Data releases show the reference month when the source specifies a single month. The page converts announced times to Beijing time using the applicable US daylight saving rules.

## Refresh

GitHub Actions refreshes the macro schedules and company earnings every day at 08:33 Beijing time (00:33 UTC). The shared update workflow publishes both snapshots with the public site after its data checks pass. Select `financial-calendar` in the workflow’s manual refresh menu to run it on demand. NVIDIA and Jensen Huang notices retain their separate manual review date.

To run the collector locally from the repository root, use the following command.

```bash
.venv/bin/python3 -m investdiy.financial_calendar
```

The updater saves scheduled events from the start of the current Eastern month onward to `investdiy/financial_calendar/data/out/events.csv`. The page filters this snapshot at viewing time. Rerun the command to pick up revised schedules. A source parsing error or an entirely missing series fails the update before the CSV is replaced.

The earnings snapshot is written separately to `data/out/earnings.json`. It keeps available dates from the start of the current month onward, including later dates that enter the four-month view as the calendar rolls forward. Each successful refresh replaces projected dates and retains earlier reported events within the window for current constituents. A constituent or disclosure feed failure preserves the previous snapshot. To update just the earnings data, run `.venv/bin/python3 -m investdiy.financial_calendar.earnings`.

If the BLS site is unreachable, the updater reports the affected series and retains previously retrieved agency dates with their original check date. For reference months outside the saved agency schedule, or on a first run, it reads the [OMB annual release plans](https://www.whitehouse.gov/omb/information-resources/guidance/us-principal-federal-economic-indicators/). These plans give dates only and may predate agency revisions. The calendar labels those entries and links to the specific annual PDF. A gap can mean that the agency has yet to announce its schedule.
