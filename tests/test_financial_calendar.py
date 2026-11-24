"""Regressions for financial calendar dates and fallback provenance."""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from requests import ConnectionError

from investdiy.financial_calendar import earnings, fetch


class CalendarTests(unittest.TestCase):
    def test_cross_month_meeting_keeps_both_dates(self):
        page = '''
        <div class="panel"><h4>2027 FOMC Meetings</h4><div class="fomc-meeting">
        <div class="fomc-meeting__month">Apr/May</div>
        <div class="fomc-meeting__date">30-1*</div></div></div>
        '''
        meeting, = fetch.fed_events(page, date(2027, 1, 1))
        self.assertEqual((meeting.start, meeting.end), (date(2027, 4, 30), date(2027, 5, 1)))
        self.assertFalse(meeting.release_at)

    def test_bls_uses_reference_month_and_seasonal_offset(self):
        page = '''
        <table><tr><th>Reference Month</th><th>Release Date</th><th>Release Time</th></tr>
        <tr><th>August 2026</th><td>Sep. 11, 2026</td><td>08:30 AM</td></tr>
        <tr><th>December 2026</th><td>Jan. 13, 2027</td><td>08:30 AM</td></tr></table>
        '''
        summer, winter = fetch.bls_events(page, 'cpi', 'source')
        self.assertEqual((summer.period, summer.release_at), ('2026-08', '2026-09-11T08:30:00-04:00'))
        self.assertEqual((winter.period, winter.release_at), ('2026-12', '2027-01-13T08:30:00-05:00'))

    def test_outage_preserves_revised_agency_date_and_check_date(self):
        revised = dict(series='cpi', agency='BLS', start='2027-02-12', end='2027-02-12',
                       period='2027-01', checked_on='2027-01-28', url='source',
                       release_at='2027-02-12T08:30:00-05:00')
        earlier = date(2027, 2, 11)
        later = date(2027, 3, 10)
        past = date(2027, 2, 2)
        plan = [fetch.Event('cpi', past, past, 'OMB', 'annual', '2026-12'),
                fetch.Event('cpi', earlier, earlier, 'OMB', 'annual', '2027-01'),
                fetch.Event('cpi', later, later, 'OMB', 'annual', '2027-02')]
        with patch.object(fetch.net, 'get', side_effect=ConnectionError('offline')), \
             patch.object(fetch.csvio, 'read_rows', return_value=[revised]), \
             patch.object(fetch, 'annual_plans', return_value=plan):
            retained, backfilled, added = fetch.collect_bls(date(2027, 2, 15))
        self.assertEqual((retained.start, retained.checked_on), (date(2027, 2, 12), '2027-01-28'))
        self.assertEqual(backfilled, plan[0])
        self.assertEqual(added, plan[2])
        self.assertFalse(added.release_at)


class EarningsTests(unittest.TestCase):
    def test_local_dates_memberships_and_revised_mainland_disclosures(self):
        def stamp(day):
            return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())

        period = stamp("2026-09-30")
        release = stamp("2026-11-02T01:00")
        next_period = stamp("2026-12-31")
        next_release = stamp("2027-02-26T08:00")
        us = {"s": "NASDAQ:AAA", "d": ["Company Class A", release, period, next_release, next_period]}
        us_b = {"s": "NASDAQ:AAB", "d": ["Company Class B", release, period, None, None]}
        cn = {"s": "SSE:600000", "d": ["Bank", release, period, next_release, next_period]}
        hk = {"s": "HKEX:10", "d": ["HK Corp", None, None, None, None]}
        lists = {"sp500": [us, us_b], "ndx": [us], "csi300": [cn], "hsi": [hk]}
        disclosures = [
            dict(SECUCODE="600000.SH", SECURITY_NAME_ABBR="银行", REPORT_DATE="2026-09-30",
                 ACTUAL_PUBLISH_DATE="2026-10-31", APPOINT_PUBLISH_DATE="2026-11-02"),
            dict(SECUCODE="600000.SH", SECURITY_NAME_ABBR="银行", REPORT_DATE="2026-12-31",
                 ACTUAL_PUBLISH_DATE=None, APPOINT_PUBLISH_DATE="2027-02-28"),
        ]
        with patch.object(earnings, "constituents", side_effect=lists.__getitem__), \
             patch.object(earnings, "appointments", return_value=disclosures), \
             patch.object(earnings, "chinese_names", return_value={}):
            snapshot = earnings.collect(date(2026, 11, 24), {})
        self.assertEqual(snapshot["counts"], {"sp500": 2, "ndx": 1, "hsi": 1, "csi300": 1})
        actual, estimate, appointment = snapshot["events"]
        self.assertEqual((actual["start"], actual["status"]), ("2026-11-01", "reported"))
        self.assertEqual(actual["symbols"], ["NASDAQ:AAA", "NASDAQ:AAB"])
        self.assertEqual(actual["indices"], ["sp500", "ndx"])
        self.assertEqual((estimate["start"], estimate["status"]), ("2027-02-26", "expected"))
        self.assertEqual((appointment["start"], appointment["status"], appointment["agency"]),
                         ("2027-02-28", "scheduled", "Eastmoney"))
