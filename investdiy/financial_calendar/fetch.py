"""Collect announced US schedules, keeping official dates separate from release times."""

import calendar
import io
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pdfplumber
from bs4 import BeautifulSoup
from icalendar import Calendar
from requests import RequestException

from ..common import csvio, net

ET = ZoneInfo("America/New_York")
OUT = Path(__file__).parent / "data/out/events.csv"
BLS = "https://www.bls.gov/schedule/news_release/"
BEA = "https://www.bea.gov/news/schedule"
FED = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
OMB = "https://www.whitehouse.gov/omb/information-resources/guidance/us-principal-federal-economic-indicators/"
BLS_REPORTS = {"empsit": "The Employment Situation", "cpi": "Consumer Price Index", "ppi": "Producer Price Indexes"}


@dataclass(frozen=True)
class Event:
    series: str
    start: date
    end: date
    agency: str
    url: str
    period: str = ""
    release_at: str = ""
    checked_on: str = ""
    kind: str = ""
    title_zh: str = ""
    title_en: str = ""
    detail_zh: str = ""
    detail_en: str = ""


def nvidia_events():
    notices = json.loads(Path(__file__).with_name("nvidia_notices.json").read_text(encoding="utf-8"))
    for notice in notices["events"]:
        day = date.fromisoformat(notice["date"])
        when = ""
        if "time_et" in notice:
            when = datetime.fromisoformat(f"{day}T{notice['time_et']}").replace(tzinfo=ET).isoformat()
        yield Event("nvidia", day, day, notice["agency"], notice["url"], release_at=when,
                    checked_on=notices["reviewed_on"], kind=notice["kind"],
                    title_zh=notice["title_zh"], title_en=notice["title_en"],
                    detail_zh=notice["detail_zh"], detail_en=notice["detail_en"])


def release(series, when, agency, url, period):
    local = when.astimezone(ET)
    return Event(series, local.date(), local.date(), agency, url, period, local.isoformat())


def bls_events(html, series, url):
    page = BeautifulSoup(html, "html.parser")
    for table in page.select("table"):
        if "Reference Month" not in table.get_text(" ", strip=True):
            continue
        for row in table.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.select("th, td")]
            if len(cells) != 3 or cells[0] == "Reference Month":
                continue
            period, day, clock = cells
            # BLS uses both full and abbreviated English month names, including "Sept.".
            month, rest = day.split(" ", 1)
            when = datetime.strptime(f"{month[:3]} {rest} {clock}", "%b %d, %Y %I:%M %p")
            yield release(series, when.replace(tzinfo=ET), "BLS", url,
                          datetime.strptime(period, "%B %Y").strftime("%Y-%m"))


def annual_events(content, year, url):
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            body = page.extract_text() or ""
            if "BUREAU OF LABOR STATISTICS" not in body or f"INDICATORS FOR {year}" not in body:
                continue
            for series, label in BLS_REPORTS.items():
                match = re.search(rf"^{label}\s+((?:\d{{1,2}} +){{11}}\d{{1,2}}) *$", body, re.M)
                if not match:
                    raise ValueError(f"Missing {label} row in {url}")
                for month, value in enumerate(match[1].split(), 1):
                    day = date(year, month, int(value))
                    period = day.replace(day=1) - timedelta(days=1)
                    yield Event(series, day, day, "OMB", url, period.strftime("%Y-%m"))
            return
    raise ValueError(f"Missing BLS schedule for {year} in {url}")


def annual_plans(today):
    index = BeautifulSoup(net.get(OMB).content, "html.parser")
    for link in index.select("a[href]"):
        year = re.fullmatch(r"Schedule of Release Dates for Principal Federal Economic Indicators for (\d{4})",
                            link.get_text(" ", strip=True))
        if year and today.year <= int(year[1]) <= today.year + 1:
            url = urljoin(OMB, link["href"])
            yield from annual_events(net.get(url).content, int(year[1]), url)


def bea_events(content):
    for entry in Calendar.from_ical(content).walk("VEVENT"):
        title = str(entry.get("SUMMARY", "")).strip()
        if not title.startswith("Personal Income and Outlays,") or entry.get("STATUS") == "CANCELLED":
            continue
        when = entry.decoded("DTSTART")
        if not isinstance(when, datetime) or when.tzinfo is None:
            raise ValueError(f"Missing BEA release time for {title}")
        # A combined release can cover multiple months. Only label unambiguous periods.
        period = re.fullmatch(r"Personal Income and Outlays, (\w+ \d{4})", title)
        month = datetime.strptime(period[1], "%B %Y").strftime("%Y-%m") if period else ""
        yield release("pce", when, "BEA", BEA, month)


def fed_events(html, today):
    page = BeautifulSoup(html, "html.parser")
    for panel in page.select(".panel"):
        heading = panel.select_one("h4")
        year = heading and re.fullmatch(r"(\d{4}) FOMC Meetings", heading.get_text(strip=True))
        if not year or int(year[1]) < today.year - 1:
            continue
        for row in panel.select(".fomc-meeting"):
            months = row.select_one(".fomc-meeting__month").get_text(strip=True).split("/")
            days = row.select_one(".fomc-meeting__date").get_text(strip=True)
            if "notation vote" in days.lower():
                continue
            match = re.fullmatch(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\*?", days)
            if not match:
                raise ValueError(f"Unrecognised FOMC meeting dates: {months} {days}")
            first, last = [list(calendar.month_abbr).index(name.strip()[:3]) for name in (months[0], months[-1])]
            start = date(int(year[1]), first, int(match[1]))
            end = date(start.year + (last < first), last, int(match[2] or match[1]))
            if end < start:
                raise ValueError(f"Invalid FOMC meeting dates: {start} to {end}")
            yield Event("fomc", start, end, "Fed", FED)


def collect_bls(today):
    events = []
    month_start = today.replace(day=1)
    saved = {series: [] for series in BLS_REPORTS}
    for row in csvio.read_rows(OUT):
        if row["agency"] == "BLS" and row["end"] >= month_start.isoformat():
            series = row["series"]
            saved[series].append(Event(series, date.fromisoformat(row["start"]), date.fromisoformat(row["end"]),
                                       "BLS", row["url"], row["period"], row["release_at"], row["checked_on"]))
    unavailable = set()
    for series in BLS_REPORTS:
        url = f"{BLS}{series}.htm"
        try:
            live = list(bls_events(net.get(url, retries=1).content, series, url))
        except RequestException as exc:
            unavailable.add(series)
            events.extend(saved[series])
            print(f"BLS {series} unavailable ({exc}). Checking saved dates and annual plans.", file=sys.stderr)
            continue
        if not live:
            raise ValueError(f"Missing BLS release schedule in {url}")
        events.extend(live)
        # The live schedule can roll past a release earlier in the displayed month.
        first_period = min(e.period for e in live)
        events.extend(e for e in saved[series] if e.end < today and e.period < first_period)
    if unavailable:
        # Fill either side of the saved agency schedule without undoing its revisions.
        for event in annual_plans(today):
            if event.series in unavailable:
                periods = [e.period for e in saved[event.series]]
                if not periods or not min(periods) <= event.period <= max(periods):
                    events.append(event)
    return events


def run():
    today = datetime.now(ET).date()
    events = collect_bls(today)
    events.extend(bea_events(net.get(f"{BEA}/ics/online-calendar-subscription.ics").content))
    events.extend(fed_events(net.get(FED).content, today))
    missing = (set(BLS_REPORTS) | {"fomc", "pce"}) - {e.series for e in events if e.end >= today}
    if missing:
        raise ValueError(f"No upcoming dates for {', '.join(sorted(missing))}. Keeping existing calendar.")
    events.extend(nvidia_events())
    month_start = today.replace(day=1)
    schedule = sorted({e for e in events if e.end >= month_start}, key=lambda e: (e.start, e.release_at, e.series, e.title_en))
    rows = [{"as_of": today, **asdict(e), "checked_on": e.checked_on or today} for e in schedule]
    csvio.atomic_csv(OUT, rows, list(rows[0]))
    return len(rows)
