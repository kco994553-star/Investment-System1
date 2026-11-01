"""Synthetic bundle for EXP-STOCK-INDICATOR-DECILES-v1 (runner, handoff and CLI tests, and the CLI `synthetic` command).

Every security, CIK, filing, price and event here is invented: nothing is downloaded or read from a provider, and no real
price appears. Codex can rebuild the same bundle and runs from the code alone (`exp_stock_indicator_deciles.py synthetic`).
Every price-like decimal (records, quotes, month closes, session opens and closes, dividends, settlement cash, TR levels)
is a 4-decimal sentinel ending in 7, so a test can look for them in CLI output.

Issuers (CIK 100 + i, security XQnnn), signal days S 2018-02-16 and S 2019-02-15:
  1..12  COMMON, 100,000,000 shares, price >= 100: issuer caps >= 10bn at both S; with 13 the U-B has 13 names, so
         every U-B strategy runs. 9 has no open on T 2018-02-20 (an AXIS_G U-A top pick: unfilled, its slot cash is
         held, no next-rank substitute). 12 pays a dividend. U-B has no hysteresis: 1 falls to 9.99997bn in 2019 and
         leaves U-B (it stays in U-A) while the ADR 26 rises to 10.2bn and enters.
  13..24 COMMON (13 is a 22bn U-B name, the rest U-A only). 13 splits 2-for-1 on 2018-09-04 (raw prices halve; the 2019
         record has 200,000,000 shares at the post-split price). 15 (an AXIS_G U-A bottom pick) is delisted (DELISTING
         effective 2018-10-01, no terms: LOSS and CARRY diverge) and has no 2019 record and no termination evidence:
         UNKNOWN NOT_IN_RECORDS_AT_S in 2019 (review F3). 21 (a QGV_BALANCED and AXIS_V U-A top pick) is cash-merged
         (CASH_MERGER with confirmed terms, then a Form 25 DELISTING of the same security that is supporting evidence,
         review F5) and has a usable termination record in the 2019 records file (TERMINATION_EVIDENCED). 23's FY2017
         10-K is filed on the 2018 filing cutoff (2018-02-08: usable at S), 24's one day later (2018-02-09: not usable
         at S, FY2016 is used).
  25     REIT (eligible), cap ~ 400m
  26     ADR, 600,000,000 ordinary shares, adr_ratio 2 (ordinary shares per ADS): cap = 300,000,000 x ADS price; pays a
         dividend with a depositary fee
  27     ADR without adr_ratio -> UNKNOWN (ADR_RATIO_UNCONFIRMED)
  28     ETF -> EXCLUDED (NOT_ELIGIBLE_SECURITY_TYPE)
  29     'LP' (not a canonical type name) -> UNKNOWN (SECURITY_TYPE_NOT_CANONICAL)
  30     an exact copy of issuer 14 (facts, shares, price, quotes): every score ties with 14 and the security ID orders
         them (XQ014 before XQ030)
  31     U-A stay: 301m (2018) -> 220m (2019), a previous member >= 200m stays
  32     U-A leave: 280m -> 190m, below the stay threshold
  33     no entry: 230m -> 240m, never a member (below 250m)
  34     UNKNOWN carried (review F3): 2018 share count on an unconfirmed split basis (UNKNOWN), 2019 cap 220m ->
         UNKNOWN PREVIOUS_U_A_STATUS_UNKNOWN
  35     share count filed on the 2018 cutoff (2018-02-08): usable, ELIGIBLE
  36     share count filed 2018-02-09: SHARES_NOT_USABLE_AT_S (UNKNOWN) in 2018; 2019 cap 500m -> ELIGIBLE (entry)
Companyfacts: 10-Ks FY2011..FY2018 (filed 1 February of the next year unless stated) with revenue, gross profit,
operating income, pretax income, tax, net income, operating cash flow, capex, D&A, interest, diluted EPS and shares,
assets, equity, debt and cash, and the cover share count, so Q, G and V are computed for every U-A member.
External TR: 'SPY total return', is_etf true, claim OTHER_TR (owner 11/01: an ETF supplementary comparison, never the
S&P 500 index TR).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal as D, ROUND_DOWN

from . import schedule

S_2018, T_2018 = date(2018, 2, 16), date(2018, 2, 20)
S_2019, T_2019 = date(2019, 2, 15), date(2019, 2, 19)
SPLIT_DAY = date(2018, 9, 4)
DELIST_DAY = date(2018, 10, 1)
MERGER_DAY = date(2018, 7, 2)
FORM25_DAY = date(2018, 7, 12)
SHARES = D('100000000')
N_ISSUERS = 36
U_B_ISSUERS = tuple(range(1, 13))
SPLIT_ISSUER, DELISTED, MERGED, NO_T_OPEN, PIT_ON_CUTOFF, PIT_LATE = 13, 15, 21, 9, 23, 24
REIT, ADR, ADR_NO_RATIO, ETF, LP, TWIN, TWIN_OF = 25, 26, 27, 28, 29, 30, 14
STAY, LEAVE, NO_ENTRY, UNKNOWN_CARRY, SHARES_ON_CUTOFF, SHARES_LATE = 31, 32, 33, 34, 35, 36
DIVIDEND_ISSUER = 12

PRICE_2018 = {
    1: '101.2347', 2: '112.4567', 3: '123.1237', 4: '134.5677', 5: '145.0037', 6: '156.7897', 7: '167.3457',
    8: '178.9017', 9: '189.4567', 10: '201.1117', 11: '255.5557', 12: '300.5537',
    13: '220.4447', 14: '41.3307', 15: '27.5147', 16: '18.2297', 17: '12.0057', 18: '8.1237', 19: '66.0907',
    20: '5.4417', 21: '9.9997', 22: '15.1517', 23: '33.3337', 24: '48.8887',
    25: '4.0017', 26: '30.2207', 27: '15.5557', 28: '50.1237', 29: '22.2227', 30: '41.3307',
    31: '3.0127', 32: '2.8017', 33: '2.3007', 34: '3.5007', 35: '4.5007', 36: '5.0007'}
PRICE_2019 = {i: p for i, p in {**PRICE_2018, 1: '99.9997', 5: '139.9997', 26: '34.0007', 11: '262.2227', 13: '115.3337',
                                  14: '43.4347', 30: '43.4347', 31: '2.2017', 32: '1.9007', 33: '2.4007',
                                  34: '2.2007', 36: '5.0007'}.items() if i not in (DELISTED, MERGED)}
TYPES = {**{i: 'COMMON' for i in range(1, N_ISSUERS + 1)}, REIT: 'REIT', ADR: 'ADR', ADR_NO_RATIO: 'ADR', ETF: 'ETF',
         LP: 'LP'}
SIC = {**{i: '3571' for i in range(1, N_ISSUERS + 1)}, REIT: '6798'}


def sid(i):
    return f'XQ{i:03d}'


def cik(i):
    return str(100 + i)


def sentinel(value):
    """A 4-decimal price-like Decimal ending in 7 (truncate to 3 decimals, then add 0.0007)."""
    return D(value).quantize(D('0.001'), rounding=ROUND_DOWN) + D('0.0007')


# ---- universe records -----------------------------------------------------------------------------------------------
def _shares(i, year):
    if i in (ADR, ADR_NO_RATIO):
        return D('600000000')
    if i == SPLIT_ISSUER and year == 2019:
        return SHARES * 2
    return SHARES


def records(year):
    prices = PRICE_2018 if year == 2018 else PRICE_2019
    out = []
    for i in range(1, N_ISSUERS + 1):
        if i not in prices:
            continue                                    # delisted / merged: no record at the 2019 S
        rec = {'security_id': sid(i), 'cik': cik(i), 'listed': True, 'security_type': TYPES[i],
               'shares_outstanding': _shares(i, year), 'shares_filed': f'{year}-01-31',
               'shares_period_end': f'{year - 1}-12-31', 'share_price_basis': 'CONFIRMED', 'price': D(prices[i]),
               'price_label': 'SYNTHETIC_CLOSE_AT_S'}
        if i == ADR:
            rec['adr_ratio'] = D('2')
        if year == 2018 and i == UNKNOWN_CARRY:
            rec['share_price_basis'] = 'SPLIT_AFTER_SHARE_COUNT'
        if year == 2018 and i == SHARES_ON_CUTOFF:
            rec['shares_filed'] = '2018-02-08'
        if year == 2018 and i == SHARES_LATE:
            rec['shares_filed'] = '2018-02-09'
        out.append(rec)
    return out


def terminations(year):
    """Evidenced terminations for the records file of `year` (the merged issuer; the delisted one has none)."""
    if year != 2019:
        return []
    return [{'cik': cik(MERGED), 'evidence': 'synthetic 8-K merger completion', 'filed': '2018-07-03',
             'effective_date': MERGER_DAY.isoformat()}]


# ---- companyfacts and as-filed SIC ---------------------------------------------------------------------------------
def _facts_params(i):
    base = TWIN_OF if i == TWIN else i
    growth = 0.01 * ((base * 7) % 13) - 0.02
    margin = 0.04 + 0.01 * ((base * 5) % 11)
    return growth, margin


def _filed(i, fiscal_year):
    if fiscal_year == 2017 and i == PIT_ON_CUTOFF:
        return '2018-02-08'
    if fiscal_year == 2017 and i == PIT_LATE:
        return '2018-02-09'
    return f'{fiscal_year + 1}-02-01'


def companyfacts(i):
    """10-Ks FY2011..FY2018 with the Q / G / V inputs (one row per fiscal year and concept)."""
    growth, margin = _facts_params(i)
    facts = {}

    def add(taxonomy, concept, unit, value, end, filed, accn, fy, start=None):
        row = {'end': end, 'val': value, 'accn': accn, 'form': '10-K', 'filed': filed, 'fp': 'FY', 'fy': fy}
        if start:
            row['start'] = start
        facts.setdefault(taxonomy, {}).setdefault(concept, {'label': concept, 'units': {}})['units'] \
            .setdefault(unit, []).append(row)

    for year in range(2011, 2019):
        rev = round(100.0 * (1 + growth) ** (year - 2011), 6)
        filed, accn = _filed(i, year), f'00000{100 + i:05d}-{(year + 1) % 100:02d}-000001'
        start, end = f'{year}-01-01', f'{year}-12-31'
        for concept, unit, value in (
                ('Revenues', 'USD', rev), ('GrossProfit', 'USD', 0.5 * rev),
                ('OperatingIncomeLoss', 'USD', margin * rev),
                ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'USD',
                 margin * rev),
                ('IncomeTaxExpenseBenefit', 'USD', 0.25 * margin * rev), ('NetIncomeLoss', 'USD', 0.75 * margin * rev),
                ('NetCashProvidedByUsedInOperatingActivities', 'USD', 0.9 * margin * rev),
                ('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 0.03 * rev),
                ('DepreciationDepletionAndAmortization', 'USD', 0.05 * rev), ('InterestExpense', 'USD', 2.0),
                ('EarningsPerShareDiluted', 'USD/shares', 0.75 * margin * rev / 10),
                ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 10.0)):
            add('us-gaap', concept, unit, round(value, 6), end, filed, accn, year, start)
        for concept, value in (('Assets', 200.0), ('StockholdersEquity', 100.0), ('LongTermDebtNoncurrent', 40.0),
                               ('LongTermDebtCurrent', 10.0), ('CashAndCashEquivalentsAtCarryingValue', 30.0)):
            add('us-gaap', concept, 'USD', value, end, filed, accn, year)
        add('dei', 'EntityCommonStockSharesOutstanding', 'shares', 10.0, f'{year + 1}-01-20', filed, accn, year)
    return {'cik': int(cik(i)), 'entityName': f'SYNTHETIC ISSUER {i}', 'facts': facts}


def companyfacts_by_cik():
    return {cik(i): companyfacts(i) for i in range(1, N_ISSUERS + 1) if TYPES[i] in ('COMMON', 'REIT', 'ADR')}


def filing_rows():
    return [{'cik': cik(i), 'accn': f'F{cik(i)}', 'filed': '2017-02-01', 'sic': SIC[i]} for i in range(1, N_ISSUERS + 1)]


# ---- quotes at S ---------------------------------------------------------------------------------------------------
def _month_closes(base, year):
    """60 month-end closes before S's month (YYYY-MM), rising to the S price level."""
    out, y, m = {}, year - 5, 2
    for k in range(60):
        out[f'{y:04d}-{m:02d}'] = sentinel(D(base) * (D('0.6') + D('0.4') * D(k) / D(60)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def quotes(year):
    prices = PRICE_2018 if year == 2018 else PRICE_2019
    return {sid(i): {'price': D(prices[i]), 'currency': 'USD', 'month_closes': _month_closes(prices[i], year)}
            for i in range(1, N_ISSUERS + 1) if i in prices}


# ---- session prices, events, external TR ---------------------------------------------------------------------------
def sessions(start, end):
    out, day = [], schedule.session_on_or_after(start)
    while day <= end:
        out.append(day)
        day = schedule.next_session(day)
    return out


def _last_price_day(i):
    return {DELISTED: date(2018, 9, 28), MERGED: date(2018, 6, 29)}.get(i)


def price_rows(start=S_2018, end=date(2019, 3, 29)):
    """Raw USD open/close for every security on every session (sentinels ending in 7). From each S the path restarts at
    that year's S price (drift 0 on the S day); XQ013's raw prices halve from SPLIT_DAY; the delisted and merged
    issuers stop trading; XQ009 has no open on T 2018-02-20."""
    rows, t, year_start = [], 0, None
    for day in sessions(start, end):
        year = 2019 if day >= S_2019 else 2018
        if year_start != year:
            year_start, t = year, 0
        for i in range(1, N_ISSUERS + 1):
            last = _last_price_day(i)
            if last is not None and day > last:
                continue
            base = D((PRICE_2018 if year == 2018 else PRICE_2019)[i])
            drift = D(1) + D(i % 5 - 2) * D('0.0004') * D(t % 60)
            close, opening = base * drift, base * (drift - D('0.0002'))
            if i == SPLIT_ISSUER and year == 2018 and day >= SPLIT_DAY:
                close, opening = close / 2, opening / 2
            row = {'date': day, 'security_id': sid(i), 'open': sentinel(opening), 'close': sentinel(close),
                   'suspended': False, 'price_basis': 'RAW'}
            if i == NO_T_OPEN and day == T_2018:
                row['open'] = None
            rows.append(row)
        t += 1
    return rows


def event_rows():
    return [
        {'type': 'DIVIDEND', 'event_id': 'DIV-XQ012-1', 'effective_date': '2018-06-01', 'security_id': sid(12),
         'cash_per_share': '0.2517', 'pay_date': '2018-06-15'},
        {'type': 'DIVIDEND', 'event_id': 'DIV-XQ026-1', 'effective_date': '2018-08-01', 'security_id': sid(ADR),
         'cash_per_share': '0.4007', 'pay_date': '2018-08-15', 'depositary_fee_per_share': '0.0207'},
        {'type': 'SPLIT', 'event_id': 'SPLIT-XQ013-1', 'effective_date': SPLIT_DAY.isoformat(),
         'security_id': sid(SPLIT_ISSUER), 'ratio': '2'},
        {'type': 'SETTLEMENT', 'event_id': f'MERGER-{sid(MERGED)}-1', 'effective_date': MERGER_DAY.isoformat(),
         'security_id': sid(MERGED), 'kind': 'CASH_MERGER', 'available_at': '2018-06-25',
         'evidence': 'synthetic 8-K merger agreement and completion', 'settlement_date': '2018-07-05',
         'cash_per_share': '10.5007'},
        {'type': 'SETTLEMENT', 'event_id': f'FORM25-{sid(MERGED)}-1', 'effective_date': FORM25_DAY.isoformat(),
         'security_id': sid(MERGED), 'kind': 'DELISTING', 'available_at': FORM25_DAY.isoformat(),
         'evidence': 'synthetic Form 25 after the merger'},
        {'type': 'SETTLEMENT', 'event_id': f'DELIST-{sid(DELISTED)}-1', 'effective_date': DELIST_DAY.isoformat(),
         'security_id': sid(DELISTED), 'kind': 'DELISTING', 'available_at': DELIST_DAY.isoformat(),
         'evidence': 'synthetic Form 25, consideration unknown'},
    ]


def tr_rows(start=S_2018, end=date(2019, 3, 29)):
    rows = []
    for t, day in enumerate(sessions(start, end)):
        level = sentinel(D('5000.0007') * (D(1) + D('0.0003') * D(t)))
        rows.append({'date': day.isoformat(), 'total_return_index': level,
                     'open_total_return_index': sentinel(level * D('0.9998')), 'currency': 'USD'})
    return rows


TR_SERIES_LABEL = 'SPY total return'


def tr_series():
    # Owner 11/01: SPY total return is an ETF supplementary comparison only, never labelled S&P 500 index TR.
    return {'label': TR_SERIES_LABEL, 'claim': 'OTHER_TR', 'is_etf': True,
            'source': 'synthetic SPY closes plus synthetic distributions', 'rows': tr_rows()}


def sentinel_prices():
    """Every price-like decimal text the bundle carries (for the stdout check)."""
    texts = set(PRICE_2018.values()) | set(PRICE_2019.values())
    for year in (2018, 2019):
        for quote in quotes(year).values():
            texts.update(str(v) for v in quote['month_closes'].values())
    for row in price_rows():
        texts.update(str(row[k]) for k in ('open', 'close') if row[k] is not None)
    for row in tr_rows():
        texts.update((str(row['total_return_index']), str(row['open_total_return_index'])))
    for row in event_rows():
        texts.update(str(row[k]) for k in ('cash_per_share', 'depositary_fee_per_share') if k in row)
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
        'records:2019': ('records_2019.json', {'signal_day': '2019-02-15', 'records': records(2019),
                                               'terminations': terminations(2019)}),
        'quotes:2018': ('quotes_2018.json', {'signal_day': '2018-02-16', 'quotes': quotes(2018)}),
        'quotes:2019': ('quotes_2019.json', {'signal_day': '2019-02-15', 'quotes': quotes(2019)}),
        'filings': ('filings.json', filing_rows()),
        'prices': ('prices.json', price_rows()),
        'events': ('events.json', event_rows()),
        'tr_series': ('tr.json', tr_series()),
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
