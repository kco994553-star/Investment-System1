"""Synthetic bundle for EXP-STOCK-INDICATOR-DECILES-v1 (runner, handoff and CLI tests, and the CLI `synthetic` command).

Every security, CIK, filing, price and event here is invented: nothing is downloaded or read from a provider, and no real
price appears. Codex can rebuild the same bundle and runs from the code alone (`exp_stock_indicator_deciles.py synthetic`).
Prices are 4-decimal sentinels (each ends in 7) so a test can look for them in CLI output.


Issuers (CIK 101..119, security XQnnn):
  1..14  COMMON, 100,000,000 shares; caps 2018 from 173m to 30bn (five of them >= 10bn, U-B)
  15     REIT (eligible), cap 2018 ~ 400m
  16     ADR, 600,000,000 ordinary shares, adr_ratio 2 (ordinary shares per ADS) -> cap = 300,000,000 x ADS price
  17     ADR without adr_ratio -> UNKNOWN (ADR_RATIO_UNCONFIRMED)
  18     ETF -> EXCLUDED (NOT_ELIGIBLE_SECURITY_TYPE)
  19     'LP' (not a canonical type name) -> UNKNOWN (SECURITY_TYPE_NOT_CANONICAL)
2019 moves: issuer 2 falls to 220m (stays, >= 200m stay threshold), issuer 1 rises to 230m (no entry, < 250m), issuer 3
falls to 190m (leaves).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from . import schedule

SHARES = D('100000000')
PRICE_2018 = {1: '1.7317', 2: '3.0127', 3: '5.4417', 4: '8.1237', 5: '12.0057', 6: '18.2297', 7: '27.5147',
              8: '41.3307', 9: '66.0907', 10: '99.1117', 11: '104.2207', 12: '151.7737', 13: '220.4447',
              14: '300.5537', 15: '4.0017', 16: '30.2207', 17: '15.5557', 18: '50.1237', 19: '22.2227'}
PRICE_2019 = {**PRICE_2018, 1: '2.3007', 2: '2.2017', 3: '1.9007', 10: '101.0107', 11: '96.6607'}
TYPES = {**{i: 'COMMON' for i in range(1, 15)}, 15: 'REIT', 16: 'ADR', 17: 'ADR', 18: 'ETF', 19: 'LP'}
SIC = {**{i: '3571' for i in range(1, 20)}, 15: '6798'}
SPLIT_DAY = date(2018, 9, 4)


def sid(i):
    return f'XQ{i:03d}'


def cik(i):
    return str(100 + i)


def records(year):
    prices = PRICE_2018 if year == 2018 else PRICE_2019
    out = []
    for i in range(1, 20):
        rec = {'security_id': sid(i), 'cik': cik(i), 'listed': True, 'security_type': TYPES[i],
               'shares_outstanding': SHARES, 'shares_filed': f'{year}-01-31', 'shares_period_end': f'{year - 1}-12-31',
               'share_price_basis': 'CONFIRMED', 'price': D(prices[i]), 'price_label': 'SYNTHETIC_CLOSE_AT_S'}
        if i in (16, 17):
            rec['shares_outstanding'] = D('600000000')
        if i == 16:
            rec['adr_ratio'] = D('2')
        out.append(rec)
    return out


def _annual(year, val, filed, accn):
    return {'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': val, 'accn': accn, 'fy': year, 'fp': 'FY',
            'form': '10-K', 'filed': filed}


def companyfacts(i):
    """10-Ks FY2012..FY2018 (filed on 1 February of the next year), each with two comparative years; revenue only."""
    growth = 0.01 * i + (0.03 if i % 3 == 0 else 0.0)
    rows = []
    for fy in range(2012, 2019):
        filed = f'{fy + 1}-02-01'
        for year in (fy, fy - 1, fy - 2):
            rows.append(_annual(year, round(100.0 * (1 + growth) ** (year - 2009), 6), filed, f'K{cik(i)}{fy}'))
    return {'cik': int(cik(i)), 'entityName': f'SYNTHETIC ISSUER {i}',
            'facts': {'us-gaap': {'Revenues': {'label': 'Revenues', 'units': {'USD': rows}}}}}


def companyfacts_by_cik():
    return {cik(i): companyfacts(i) for i in range(1, 20) if TYPES[i] in ('COMMON', 'REIT', 'ADR')}


def filing_rows():
    return [{'cik': cik(i), 'accn': f'F{cik(i)}', 'filed': '2017-02-01', 'sic': SIC[i]} for i in range(1, 20)]


def quotes(year):
    prices = PRICE_2018 if year == 2018 else PRICE_2019
    return {sid(i): {'price': D(prices[i]), 'currency': 'USD', 'month_closes': {f'{year - 1}-12': D(prices[i])}}
            for i in range(1, 20)}


def sessions(start, end):
    out, day = [], schedule.session_on_or_after(start)
    while day <= end:
        out.append(day)
        day = schedule.next_session(day)
    return out


def price_rows(start=date(2018, 2, 16), end=date(2019, 3, 29)):
    """Raw USD open/close for every security on every session; XQ013 splits 2-for-1 on SPLIT_DAY (raw prices halve)."""
    rows = []
    for t, day in enumerate(sessions(start, end)):
        for i in range(1, 20):
            base = D(PRICE_2018[i]) if day < date(2019, 1, 1) else D(PRICE_2019[i])
            drift = D(1) + D(i % 5 - 2) * D('0.0004') * D(t % 60)
            close = (base * drift).quantize(D('0.0001'))
            opening = (base * (drift - D('0.0002'))).quantize(D('0.0001'))
            if i == 13 and day >= SPLIT_DAY:
                close, opening = (close / 2).quantize(D('0.0001')), (opening / 2).quantize(D('0.0001'))
            rows.append({'date': day, 'security_id': sid(i), 'open': opening, 'close': close, 'suspended': False,
                         'price_basis': 'RAW'})
    return rows


def event_rows():
    return [{'type': 'DIVIDEND', 'event_id': 'DIV-XQ014-1', 'effective_date': '2018-06-01', 'security_id': sid(14),
             'cash_per_share': '0.2517', 'pay_date': '2018-06-15'},
            {'type': 'SPLIT', 'event_id': 'SPLIT-XQ013-1', 'effective_date': SPLIT_DAY.isoformat(),
             'security_id': sid(13), 'ratio': '2'}]


def tr_rows(start=date(2018, 2, 16), end=date(2019, 3, 29)):
    rows = []
    for t, day in enumerate(sessions(start, end)):
        level = (D('5000.0007') * (D(1) + D('0.0003') * D(t))).quantize(D('0.0001'))
        rows.append({'date': day.isoformat(), 'total_return_index': level,
                     'open_total_return_index': (level - D('1.0007')), 'currency': 'USD'})
    return rows


def sentinel_prices():
    """Every price-like decimal text the bundle carries (for the stdout check)."""
    texts = set(PRICE_2018.values()) | set(PRICE_2019.values())
    for row in price_rows():
        texts.update((str(row['open']), str(row['close'])))
    return texts




PERIOD = '2018-02-16..2019-03-29'
RIGHTS_NOTE = 'synthetic test data, no third-party rights'


def dumps(value):
    """JSON with Decimals written as exact JSON numbers (the CLI reads them without float); sorted keys, stable bytes."""
    import json
    import re

    def encode(o):
        if isinstance(o, D):
            return f'@@D{o}@@'
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        raise TypeError(type(o).__name__)
    return re.sub(r'"@@D([-0-9.E+]+)@@"', r'\1', json.dumps(value, default=encode, sort_keys=True)).encode()


def bundle_files():
    """{resource name: (file name, payload)} of the synthetic input bundle (two signal years, 2018 and 2019)."""
    files = {
        'records:2018': ('records_2018.json', {'signal_day': '2018-02-16', 'records': records(2018)}),
        'records:2019': ('records_2019.json', {'signal_day': '2019-02-15', 'records': records(2019)}),
        'quotes:2018': ('quotes_2018.json', {'signal_day': '2018-02-16', 'quotes': quotes(2018)}),
        'quotes:2019': ('quotes_2019.json', {'signal_day': '2019-02-15', 'quotes': quotes(2019)}),
        'filings': ('filings.json', filing_rows()),
        'prices': ('prices.json', price_rows()),
        'events': ('events.json', event_rows()),
        # Owner 11/01: SPY total return is an ETF supplementary comparison only, never labelled S&P 500 index TR.
        'tr_series': ('tr.json', {'label': 'SPY total return (ETF, synthetic)', 'claim': 'OTHER_TR', 'is_etf': True,
                                  'source': 'synthetic', 'rows': tr_rows()}),
    }
    facts = companyfacts_by_cik()
    for key in sorted(facts)[:3]:                      # three issuers as one-CIK files, the rest as one mapping file
        files[f'companyfacts:{key}'] = (f'cf_{key}.json', facts.pop(key))
    files['companyfacts:rest'] = ('cf_rest.json', facts)
    return files


def bundle_bytes():
    """[(file name, bytes)] of the bundle files, then ('manifest.json', bytes) of its input manifest (last)."""
    import hashlib
    import json

    out, resources = [], []
    for name, (filename, payload) in bundle_files().items():
        data = dumps(payload)
        out.append((filename, data))
        resources.append({'name': name, 'path': filename, 'sha256': hashlib.sha256(data).hexdigest(),
                          'source': 'synthetic generator', 'period': PERIOD, 'rights_note': RIGHTS_NOTE})
    manifest = {'schema': 'exp-deciles-input-manifest/1', 'experiment_id': 'EXP-STOCK-INDICATOR-DECILES-v1',
                'resources': resources}
    out.append(('manifest.json', json.dumps(manifest, sort_keys=True).encode()))
    return out
