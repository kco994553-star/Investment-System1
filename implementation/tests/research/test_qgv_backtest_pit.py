"""Hand-built synthetic calendars and vintages: no historical market data."""
import copy
from datetime import date, datetime, timedelta
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from investment_system.research.qgv_backtest import calendar_adapter as cal
from investment_system.research.qgv_backtest import pit_adapter as pit

ET = ZoneInfo('America/New_York')


def table(days):
    return cal.VerifiedSessionCalendar(
        [cal.Session(date.fromisoformat(d), datetime.fromisoformat(d + 'T09:30').replace(tzinfo=ET),
                     datetime.fromisoformat(d + 'T' + close).replace(tzinfo=ET)) for d, close in days],
        coverage_start=date.fromisoformat(days[0][0]), coverage_end=date.fromisoformat(days[-1][0]),
        source='SYNTHETIC_HAND_TABLE', verified=True)


class CalendarTest(unittest.TestCase):
    def test_february_roll_and_preceding_signal_without_post2009_clamp(self):
        for year, friday, nominal, tuesday in [(1980, '15', '18', '19'), (2000, '18', '21', '22'),
                                               (2016, '12', '15', '16')]:
            c = table([(f'{year}-02-{friday}', '13:00'), (f'{year}-02-{tuesday}', '16:00')])
            result = cal.rebalance_schedule(c, date(year, 2, int(nominal)), date(year, 2, int(tuesday)))
            self.assertEqual(len(result), 1)
            r = result[0]
            self.assertEqual(r.signal_day, date(year, 2, int(friday)))
            self.assertEqual(r.execution_day, date(year, 2, int(tuesday)))
            self.assertEqual(r.decision_at.hour, 18)  # 13:00 NY winter = 18 UTC
            self.assertEqual(r.execute_at.hour, 14)

    def test_dst_and_unknown_coverage_fail_closed(self):
        c = table([('2016-08-12', '16:00'), ('2016-08-15', '16:00')])
        self.assertEqual(c.session(date(2016, 8, 12)).close_at.hour, 20)
        with self.assertRaisesRegex(ValueError, 'CALENDAR_COVERAGE'):
            c.previous_session(date(1980, 2, 19))
        with self.assertRaisesRegex(ValueError, 'VERIFIED'):
            cal.VerifiedSessionCalendar(c.sessions, coverage_start=c.coverage_start,
                                        coverage_end=c.coverage_end, source='unknown', verified=False)

    def test_no_fixed_weekday_synthesis_or_naive_time(self):
        with self.assertRaisesRegex(ValueError, 'TIMEZONE'):
            cal.Session(date(1980, 2, 19), datetime(1980, 2, 19, 9, 30), datetime(1980, 2, 19, 16))
        c = table([('2016-02-12', '16:00'), ('2016-02-16', '16:00')])
        self.assertFalse(c.is_session(date(2016, 2, 15)))
        self.assertEqual(cal.rebalance_schedule(c, date(2016, 2, 12), date(2016, 2, 16),
                                               rebalance='ANNUAL_FEBRUARY')[0].execution_day, date(2016, 2, 16))

    def test_session_label_must_match_new_york_instant(self):
        with self.assertRaisesRegex(ValueError, 'SESSION_DATE'):
            cal.Session(date(1980, 2, 19), datetime(1980, 2, 20, 14, 30, tzinfo=ET),
                        datetime(1980, 2, 20, 16, tzinfo=ET))


class PITTest(unittest.TestCase):
    def facts(self):
        return {'cik': '0000000001', 'facts': {'us-gaap': {'Revenue': {'units': {'USD': [
            {'filed': '1979-03-01', 'end': '1978-12-31', 'val': 10, 'accn': 'old', 'frame': 'hindsight'},
            {'filed': '1980-02-15', 'end': '1979-12-31', 'val': 20, 'accn': 'signal'},
            {'filed': '1980-02-19', 'end': '1978-12-31', 'val': 999, 'accn': 'amend'},
            {'end': '1977-12-31', 'val': 50},
        ]}}}}}

    def test_strict_filed_boundary_future_mutation_and_frame_removed(self):
        original = self.facts()
        before = pit.filter_companyfacts(original, date(1980, 2, 15))
        self.assertEqual(before.cutoff, date(1980, 2, 14))
        rows = before.payload['facts']['us-gaap']['Revenue']['units']['USD']
        self.assertEqual([r['val'] for r in rows], [10])
        self.assertNotIn('frame', rows[0])
        self.assertIn('frame', original['facts']['us-gaap']['Revenue']['units']['USD'][0])
        mutated = copy.deepcopy(original)
        mutated['facts']['us-gaap']['Revenue']['units']['USD'][2]['val'] = -999999
        self.assertEqual(pit.filter_companyfacts(mutated, date(1980, 2, 15)).payload, before.payload)
        self.assertEqual(before.rejected['MISSING_FILED'], 1)

    def test_sic_as_filed_never_current_or_signal_day(self):
        rows = [{'cik': '1', 'filed': '1979-03-01', 'sic': '3571', 'accn': 'old'},
                {'cik': '1', 'filed': '1980-02-15', 'sic': '6021', 'accn': 'new'}]
        self.assertEqual(pit.as_filed_sic(rows, date(1980, 2, 15), cik='0000000001')['sic'], '3571')
        self.assertIsNone(pit.as_filed_sic([], date(1980, 2, 15))['sic'])

    def test_conflicting_sic_same_accession_stays_unknown_in_built_rows(self):
        c = table([('1980-02-14', '16:00'), ('1980-02-15', '16:00')])
        filings = [{'cik': '1', 'filed': '1979-03-01', 'sic': sic, 'accn': 'old'} for sic in ['3571', '6021']]
        rows = pit.build_pit_rows({'1': self.facts()}, filings,
                                 [{'cik': '1', 'security_id': 'A', 'start': '1970-01-01', 'end': None}],
                                 [], date(1980, 2, 15), c)
        self.assertIsNone(rows['A']['sic'])
        self.assertEqual(rows['A']['state'], 'NOT_AVAILABLE')

    def test_share_class_sixty_completed_sessions_and_permanent_tie(self):
        first = date(2016, 1, 1)
        # Synthetic sessions intentionally include weekends: no actual calendar claim.
        days = [(str(first + timedelta(days=i)), '16:00') for i in range(65)]
        c = table(days)
        signal = date.fromisoformat(days[-1][0])
        members = [{'cik': '1', 'security_id': sid, 'start': '2015-01-01', 'end': None} for sid in ['B', 'A']]
        prices = [{'security_id': sid, 'date': day, 'close': 10, 'volume': 10 if sid == 'A' else 20}
                  for sid in ['A', 'B'] for day, _ in days]
        prices.append({'security_id': 'A', 'date': str(signal + timedelta(days=1)), 'close': 1e9, 'volume': 1e9})
        self.assertEqual(pit.choose_share_classes(members, prices, signal, c)[0]['security_id'], 'B')
        for r in prices:
            if r['date'] <= str(signal):
                r['volume'] = 10
        self.assertEqual(pit.choose_share_classes(members[::-1], prices[::-1], signal, c)[0]['security_id'], 'A')
        fallback = pit.choose_share_classes(members, [], signal, c)[0]
        self.assertEqual(fallback['security_id'], 'A')
        self.assertIn('SHARE_CLASS_LIQUIDITY_UNCONFIRMED', fallback['flags'])

    def test_unknown_basis_price_na_future_price_cannot_change_quote(self):
        prices = [{'security_id': 'A', 'date': '1980-02-15', 'close': 10, 'currency': 'USD'},
                  {'security_id': 'A', 'date': '1980-02-19', 'close': 999, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW'}]
        self.assertEqual(pit.quotes_as_of(prices, date(1980, 2, 15)), {})
        prices[0].update(price_basis='RAW', shares_basis='RAW', basis_alignment={
            'status': 'VERIFIED', 'source': 'SYNTHETIC', 'signal_day': '1980-02-15',
            'shares_period_end': '1978-12-31', 'verified_through': '1980-02-15',
            'price_to_shares_factor': 1.0, 'split_events': []})
        q = pit.quotes_as_of(prices, date(1980, 2, 15))
        self.assertEqual(q['A']['price'], 10)
        prices[1]['close'] = -100
        self.assertEqual(pit.quotes_as_of(prices, date(1980, 2, 15)), q)

    def test_raw_strings_do_not_establish_split_alignment(self):
        prices = [{'security_id': 'A', 'date': '2016-02-12', 'close': 5, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW'}]
        self.assertEqual(pit.quotes_as_of(prices, date(2016, 2, 12)), {})
        receipt = {'status': 'VERIFIED', 'source': 'SYNTHETIC', 'signal_day': '2016-02-12',
                   'shares_period_end': '2015-12-31', 'verified_through': '2016-02-12',
                   'price_to_shares_factor': 2, 'split_events': []}
        prices[0]['basis_alignment'] = receipt
        self.assertEqual(pit.quotes_as_of(prices, date(2016, 2, 12)), {})  # no evidence for factor 2
        receipt['split_events'] = [{'effective_date': '2016-02-01', 'ratio': 2, 'source': 'SYNTHETIC'}]
        quote = pit.quotes_as_of(prices, date(2016, 2, 12))['A']
        self.assertEqual(quote['price'], 10)  # old-basis 100 shares × 10, new-basis 200 × 5

    def test_raw_month_history_is_not_assumed_on_latest_share_basis(self):
        receipt = {'status': 'VERIFIED', 'source': 'SYNTHETIC', 'signal_day': '2016-02-12',
                   'shares_period_end': '2015-12-31', 'verified_through': '2016-02-12',
                   'price_to_shares_factor': 1, 'split_events': []}
        prices = [{'security_id': 'A', 'date': '2015-12-31', 'close': 100, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW', 'is_month_end': True},
                  {'security_id': 'A', 'date': '2016-02-12', 'close': 10, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW', 'basis_alignment': receipt}]
        self.assertEqual(pit.quotes_as_of(prices, date(2016, 2, 12))['A']['month_closes'], {})

    def test_historical_price_supports_two_signal_specific_share_bases(self):
        def receipt(signal, share_day, accn, factor, events=()):
            return {'status': 'VERIFIED', 'source': 'SYNTHETIC', 'signal_day': signal,
                    'verified_through': signal, 'shares_period_end': share_day, 'shares_filing_accn': accn,
                    'price_to_shares_factor': factor, 'split_events': list(events)}
        split = {'effective_date': '2016-02-01', 'ratio': 2, 'source': 'SYNTHETIC'}
        prices = [{'security_id': 'A', 'date': '2016-01-29', 'close': 100, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW', 'is_month_end': True,
                   'basis_alignments': {
                       '2016-02-12': receipt('2016-02-12', '2015-12-31', 'OLD', 1),
                       '2016-05-13': receipt('2016-05-13', '2016-03-31', 'NEW', 0.5, [split])}},
                  {'security_id': 'A', 'date': '2016-02-12', 'close': 50, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW',
                   'basis_alignment': receipt('2016-02-12', '2015-12-31', 'OLD', 2, [split])},
                  {'security_id': 'A', 'date': '2016-05-13', 'close': 50, 'currency': 'USD',
                   'price_basis': 'RAW', 'shares_basis': 'RAW',
                   'basis_alignment': receipt('2016-05-13', '2016-03-31', 'NEW', 1)}]
        feb = pit.quotes_as_of(prices, date(2016, 2, 12))['A']
        may = pit.quotes_as_of(prices, date(2016, 5, 13))['A']
        self.assertEqual(feb['month_closes'], {'2016-01': 100})
        self.assertEqual(may['month_closes'], {'2016-01': 50})
        self.assertEqual((feb['price'], may['price']), (100, 50))
        prices[0]['basis_alignments']['2016-05-13']['price_to_shares_factor'] = 999
        self.assertEqual(pit.quotes_as_of(prices, date(2016, 2, 12))['A'], feb)

    def test_build_calls_operating_compute_with_previous_calendar_date(self):
        c = table([('1980-02-14', '16:00'), ('1980-02-15', '16:00')])
        with patch.object(pit.v2_factors, 'compute', return_value=('GENERAL', '1978-12-31', 'USD', {}, {})) as compute:
            rows = pit.build_pit_rows({'0000000001': self.facts()},
                                     [{'cik': '1', 'filed': '1979-03-01', 'sic': '3571', 'accn': 'old'}],
                                     [{'cik': '1', 'security_id': 'A', 'start': '1970-01-01', 'end': None}],
                                     [], date(1980, 2, 15), c)
        self.assertEqual(compute.call_args.kwargs['cutoff'], date(1980, 2, 14))
        self.assertEqual(rows['A']['provenance']['vintage_status'], 'RECONSTRUCTED_AS_OF')
        self.assertEqual(rows['A']['cik'], '0000000001')

    def test_external_filing_known_at_is_joined_and_duplicate_evidence_conservative(self):
        c = table([('1980-02-14', '16:00'), ('1980-02-15', '16:00')])
        filings = [{'cik': '1', 'filed': '1979-03-01', 'sic': '3571', 'accn': 'old'},
                   {'cik': '1', 'filed': '1980-02-01', 'sic': '3571', 'accn': 'signal',
                    'known_at': '1981-01-01T00:00:00Z'}]
        facts = self.facts()
        facts['facts']['us-gaap']['Revenue']['units']['USD'][1]['filed'] = '1980-02-01'
        captured = []
        def compute(payload, **kwargs):
            captured.append(payload['facts']['us-gaap']['Revenue']['units']['USD'])
            return 'GENERAL', '1978-12-31', 'USD', {}, {}
        members = [{'cik': '1', 'security_id': 'A', 'start': '1970-01-01', 'end': None}]
        with patch.object(pit.v2_factors, 'compute', side_effect=compute):
            pit.build_pit_rows({'1': facts}, filings, members, [], date(1980, 2, 15), c)
        self.assertEqual([r['val'] for r in captured[-1]], [10])
        filings.append(dict(filings[-1], known_at='1979-01-01T00:00:00Z'))
        with patch.object(pit.v2_factors, 'compute', side_effect=compute):
            pit.build_pit_rows({'1': facts}, filings, members, [], date(1980, 2, 15), c)
            pit.build_pit_rows({'1': facts}, filings[::-1], members, [], date(1980, 2, 15), c)
        self.assertEqual(captured[-1], captured[-2])
        self.assertEqual([r['val'] for r in captured[-1]], [10])


if __name__ == '__main__':
    unittest.main()
