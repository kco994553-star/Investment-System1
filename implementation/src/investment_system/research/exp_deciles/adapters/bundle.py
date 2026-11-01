"""One signal day S: adapter outputs -> an EXP-STOCK-INDICATOR-DECILES-v1 input bundle, its manifest and a provenance file.

`build(...)` returns the bundle as bytes in RAM ({'files': [(file name, bytes)], 'counts'}); it writes nothing. The caller
writes the files to a private location (never into the repository) and runs the engine CLI on manifest.json. Files:
  records_<year>.json      records:<year>  {"signal_day", "records", "terminations"} (universe.py record shape)
  quotes_<year>.json       quotes:<year>   {"signal_day", "quotes"} (one S price source, labelled)
  companyfacts_pit.json    companyfacts:pit  {cik: companyfacts payload with only rows usable at S}
  filings.json             filings          as-filed SIC filing rows (FSDS sub.txt)
  prices.json              prices           Alpaca SIP raw daily rows from S to the next reselection T (open / close)
  adapter_provenance.json  not an engine resource: per item the source name, source file sha256 and reason codes, the
                           counts, and what the adapters cannot supply
  manifest.json            exp-deciles-input-manifest/1 over the five engine resources (written last)

Candidates are the caller's security map (plus carried previous-U-A CIKs without a security at S). That map is never a
complete historical population and the bundle says so (population_status); `complete_population=True` is refused
(COMPLETE_HISTORICAL_POPULATION_NOT_CLAIMABLE). A SEC issuer list or one day's IEX symbol list is not a population either:
neither is read to add candidates.

Record fields and where they come from:
  security_id, cik          caller's security map
  listed, security_type,    NOT supplied by any adapter here: null (engine: UNKNOWN) unless `attributes` gives them with
  adr_ratio                 a named source and the source file's sha256
  shares_outstanding,       sec_bulk.cover_shares (single class only; multi-class -> null with the reason)
  shares_filed,
  shares_period_end
  share_price_basis         'UNCONFIRMED' from SEC bulk (no corporate-action source), unless `attributes` confirms it
  price, price_label        s_price_source: IEX_LAST_REGULAR_TRADE_APPROX (default; iex_signal, an approximation of the S
                            signal price) or ALPACA_SIP_CLOSE (the SIP consolidated close at S, label
                            ALPACA_SIP_CONSOLIDATED_CLOSE_RAW); the quotes file uses the same source. Never both, never
                            filled from another source
Ledger prices come only from the Alpaca SIP daily bars (the open is the consolidated T open candidate); an IEX price never
becomes a price row (PRICE_ROW_SOURCE_NOT_ALPACA_SIP).

Counts (adapter view, before the engine): candidates; eligible_input_present = candidates whose record carries every
input the engine's eligibility needs (CIK, listed, security type, a share count usable as filed with its dates, a
CONFIRMED split basis, a price at S, and an ADR ratio for an ADR); unknown_by_reason by first reason;
unknown_reason_occurrences over all reasons. Per input: companyfacts / SIC / shares by status and reason, S price statuses,
T open coverage, termination records with and without an effective date.
"""
from __future__ import annotations

from collections import Counter
import re
from pathlib import Path

from .. import schedule, settings
from . import alpaca_bars, iex_signal, sec_bulk
from .common import (SUPPLIED, UNKNOWN, AdapterError, cik10, counts_by_status, dumps, positive_decimal, sha256_bytes,
                     sha256_file)

PROVENANCE_SCHEMA = 'exp-deciles-adapter-provenance/1'
INPUT_MANIFEST_SCHEMA = 'exp-deciles-input-manifest/1'
POPULATION_STATUS = 'CALLER_SECURITY_MAP_NOT_A_COMPLETE_HISTORICAL_POPULATION'
S_PRICE_IEX = iex_signal.LABEL
S_PRICE_ALPACA = 'ALPACA_SIP_CLOSE'
ALPACA_CLOSE_LABEL = 'ALPACA_SIP_CONSOLIDATED_CLOSE_RAW'
SEC_RIGHTS = 'SEC EDGAR public data (redistribution allowed); kept private with the derived research inputs'
IEX_RIGHTS = 'Data provided for free by IEX; IEX Historical Data Terms of Use'
SECURITY_KEYS = {'security_id', 'cik', 'iex_symbol', 'alpaca_series', 'alpaca_symbol', 'span'}
ATTRIBUTE_KEYS = {'listed', 'security_type', 'adr_ratio', 'share_price_basis'}
CANNOT_SUPPLY = (
    'LISTING_STATUS_AT_S', 'SECURITY_TYPE_AND_EXCHANGE', 'ADR_RATIO', 'TRADABILITY_AT_S',
    'PER_CLASS_SHARE_COUNTS_OF_MULTI_CLASS_ISSUERS', 'SPLIT_BASIS_OF_THE_SHARE_COUNT',
    'CORPORATE_ACTIONS_DIVIDENDS_SPLITS_MERGER_TERMS', 'TERMINATION_EFFECTIVE_DATE_AND_CLASS_FROM_INDEX_ROWS',
    'POINT_IN_TIME_TICKER_CIK_SPANS', 'REPRESENTATIVE_SECURITY_DOLLAR_VOLUME', 'MONTH_END_CLOSES_FOR_V',
    'SPY_TOTAL_RETURN_DISTRIBUTIONS', 'RISK_FREE_RATE', 'COMPLETE_HISTORICAL_POPULATION')

# record-level reason codes
CIK_MISSING = 'CIK_MISSING'
LISTING_STATUS_NOT_SUPPLIED = 'LISTING_STATUS_NOT_SUPPLIED'
SECURITY_TYPE_NOT_SUPPLIED = 'SECURITY_TYPE_NOT_SUPPLIED'
ADR_RATIO_NOT_SUPPLIED = 'ADR_RATIO_NOT_SUPPLIED'
SHARE_PRICE_BASIS_NOT_CONFIRMED = 'SHARE_PRICE_BASIS_NOT_CONFIRMED'
NOT_IN_SECURITY_MAP_AT_S = 'NOT_IN_SECURITY_MAP_AT_S'

_HEX64 = re.compile(r'[0-9a-f]{64}')


def _text(value, error):
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(error)
    return value


def _provided_source(block, error):
    """{'source', 'sha256'} of a caller-supplied block; refused without a named source and a file sha256."""
    if not isinstance(block, dict) or not isinstance(block.get('values'), dict):
        raise AdapterError(error)
    _text(block.get('source'), error)
    if not isinstance(block.get('sha256'), str) or not _HEX64.fullmatch(block['sha256']):
        raise AdapterError(error)
    return {'source': block['source'], 'sha256': block['sha256']}


def _dates(year):
    row = schedule.frozen_row(year=year)
    try:
        next_t = schedule.frozen_row(year=year + 1)['T']
    except ValueError:
        next_t = schedule.annual_dates(year + 1)['T']
    return schedule._day(row['S']), schedule._day(row['T']), schedule._day(next_t)


def _securities(securities):
    out, seen = [], set()
    for entry in securities:
        if not isinstance(entry, dict) or set(entry) - SECURITY_KEYS or 'security_id' not in entry:
            raise AdapterError('SECURITY_MAP_ENTRY_INVALID')
        sid = _text(entry['security_id'], 'SECURITY_MAP_ENTRY_INVALID')
        if sid in seen:
            raise AdapterError('SECURITY_MAP_DUPLICATE_ID')
        seen.add(sid)
        out.append(dict(entry, cik=cik10(entry.get('cik'))))
    if not out:
        raise AdapterError('SECURITY_MAP_EMPTY')
    return sorted(out, key=lambda e: e['security_id'])


def _attributes(attributes, security_ids):
    if attributes is None:
        return {}, None
    source = _provided_source(attributes, 'ATTRIBUTES_PROVENANCE_REQUIRED')
    values = {}
    for sid, fields in attributes['values'].items():
        if sid not in security_ids or not isinstance(fields, dict) or set(fields) - ATTRIBUTE_KEYS:
            raise AdapterError('ATTRIBUTES_INVALID')
        if 'listed' in fields and fields['listed'] not in (True, False, None):
            raise AdapterError('ATTRIBUTES_INVALID')
        for key in ('security_type', 'share_price_basis'):
            if key in fields and fields[key] is not None:
                _text(fields[key], 'ATTRIBUTES_INVALID')
        if 'adr_ratio' in fields and fields['adr_ratio'] is not None and positive_decimal(fields['adr_ratio']) is None:
            raise AdapterError('ATTRIBUTES_INVALID')
        values[sid] = dict(fields)
    return values, source


def _source(sources, name, role, path):
    if path is None:
        return None
    digest = sha256_file(path)
    sources.append({'name': name, 'role': role, 'file': Path(path).name, 'sha256': digest})
    return digest


def build(*, year, securities, sec=None, iex=None, attributes=None, carried_units=(), effective_dates=None,
          s_price_source=S_PRICE_IEX, complete_population=False):
    """The bundle for the frozen signal year `year` (module doc).

    securities: [{'security_id', 'cik'?, 'iex_symbol'?, 'alpaca_series'? (a raw/<series> directory), 'alpaca_symbol'?,
    'span'? ([first session, first day no longer] under that series' symbol)}]; sec: {'companyfacts_zip'?,
    'submissions_zip'?, 'form_idx'?: [paths], 'fsds'?: [paths]}; iex: {'rows', 'iex_day'} (the IEX HIST provider's parse_rows output) or
    {'day_result': IexDay, 'security_of_key': {key: security_id}}; attributes / effective_dates: {'source', 'sha256',
    'values'} (values {security_id: {listed?, security_type?, adr_ratio?, share_price_basis?}} / {accession: date});
    carried_units: CIKs of the previous U-A members and UNKNOWN units (termination evidence is looked up for them)."""
    if complete_population:
        raise AdapterError('COMPLETE_HISTORICAL_POPULATION_NOT_CLAIMABLE')
    if s_price_source not in (S_PRICE_IEX, S_PRICE_ALPACA):
        raise AdapterError('S_PRICE_SOURCE_INVALID')
    signal, execution, next_t = _dates(year)
    entries = _securities(securities)
    ids = {e['security_id'] for e in entries}
    attrs, attrs_source = _attributes(attributes, ids)
    sec = dict(sec or {})
    if set(sec) - {'companyfacts_zip', 'submissions_zip', 'form_idx', 'fsds'}:
        raise AdapterError('SEC_PATHS_INVALID')
    sources = []

    # ---- SEC ----------------------------------------------------------------------------------------------------------
    ciks = sorted({e['cik'] for e in entries if e['cik'] is not None})
    per_cik = Counter(e['cik'] for e in entries if e['cik'] is not None)
    carried = set()
    for unit in carried_units:
        if cik10(unit) is None:
            raise AdapterError('CARRIED_UNIT_INVALID')
        carried.add(cik10(unit))
    carried = sorted(carried)
    _source(sources, sec_bulk.SOURCE_COMPANYFACTS, 'PIT_COMPANYFACTS_AND_COVER_SHARES', sec.get('companyfacts_zip'))
    raw, problems = sec_bulk.load_companyfacts(sec.get('companyfacts_zip'), ciks)
    facts, facts_items = sec_bulk.pit_companyfacts(raw, problems, signal)
    for path in sorted(sec.get('fsds') or (), key=str):
        _source(sources, sec_bulk.SOURCE_FSDS, 'AS_FILED_SIC', path)
    filing_rows, sic_items, sic_counts = sec_bulk.as_filed_sic(sec.get('fsds') or (), ciks, signal)
    tickers = None
    if sec.get('submissions_zip') is not None:
        _source(sources, sec_bulk.SOURCE_SUBMISSIONS, 'MULTI_CLASS_CHECK_TODAY_TICKERS', sec['submissions_zip'])
        tickers = sec_bulk.submissions_ticker_counts(sec['submissions_zip'], ciks)
    shares = sec_bulk.cover_shares(raw, problems, ciks, signal, securities_per_cik=per_cik, ticker_counts=tickers)
    for path in sorted(sec.get('form_idx') or (), key=str):
        _source(sources, sec_bulk.SOURCE_FORM_IDX, 'TERMINATION_EVIDENCE', path)
    confirmed_dates, dates_source = None, None
    if effective_dates is not None:
        dates_source = _provided_source(effective_dates, 'EFFECTIVE_DATES_PROVENANCE_REQUIRED')
        confirmed_dates = effective_dates['values']
    terminations, termination_rows, termination_counts = sec_bulk.terminations(
        sec.get('form_idx') or (), sorted(set(ciks) | set(carried)), signal, effective_dates=confirmed_dates)

    # ---- IEX (S signal price approximation) -----------------------------------------------------------------------------
    if iex is None:
        iex_result = iex_signal.not_supplied(sorted(ids))
    elif isinstance(iex, dict) and set(iex) == {'rows', 'iex_day'}:
        iex_result = iex_signal.signal_quotes(iex['rows'], {e['security_id']: e.get('iex_symbol') for e in entries},
                                              iex_day=iex['iex_day'], signal_day=signal)
    elif isinstance(iex, dict) and set(iex) == {'day_result', 'security_of_key'}:
        iex_result = iex_signal.signal_quotes_from_iex_day(iex['day_result'], iex['security_of_key'], signal_day=signal)
        if set(iex_result['status']) - ids:
            raise AdapterError('IEX_SECURITY_NOT_IN_MAP')
        iex_result = _merge_missing(iex_result, ids - set(iex_result['status']))
    else:
        raise AdapterError('IEX_INPUT_INVALID')

    # ---- Alpaca SIP daily bars (ledger prices) ----------------------------------------------------------------------
    series_cache, alpaca, prices = {}, {}, []
    for entry in entries:
        sid, folder = entry['security_id'], entry.get('alpaca_series')
        if folder is None:
            series = None
        else:
            key = (str(folder), entry.get('alpaca_symbol'))
            if key not in series_cache:
                series_cache[key] = alpaca_bars.read_series(folder, expected_symbol=entry.get('alpaca_symbol'))
            series = series_cache[key]
        span = entry.get('span')
        if span is not None and (not isinstance(span, (list, tuple)) or len(span) != 2):
            raise AdapterError('SECURITY_SPAN_INVALID')
        rows = alpaca_bars.price_rows(series, sid, start=signal, end=next_t, span=span)
        prices.extend(rows)
        alpaca[sid] = {'status': 'NOT_SUPPLIED' if series is None else series['status'],
                       'reason': None if series is None else series['reason'],
                       'pages': [] if series is None else series['pages'], 'rows': len(rows),
                       'coverage': alpaca_bars.coverage(series, signal_day=signal, execution_day=execution, end=next_t,
                                                        span=span),
                       'close_at_s': _close_at(series, signal, span)}
    if any(row.get('source') != alpaca_bars.SOURCE for row in prices):
        raise AdapterError('PRICE_ROW_SOURCE_NOT_ALPACA_SIP')
    prices.sort(key=lambda r: (r['date'], r['security_id']))
    for (folder, _), series in sorted(series_cache.items()):
        for page in series['pages']:
            sources.append({'name': alpaca_bars.SOURCE_NAME, 'role': 'LEDGER_PRICES',
                            'file': f'{Path(folder).name}/{page["file"]}', 'sha256': page['sha256']})

    # ---- records and quotes -----------------------------------------------------------------------------------------
    records, quotes, items = [], {}, {}
    for entry in entries:
        sid, cik = entry['security_id'], entry['cik']
        given = attrs.get(sid, {})
        share = shares.get(cik) if cik is not None else None
        price, label, price_status = _s_price(s_price_source, sid, iex_result, alpaca[sid])
        record = {'security_id': sid, 'cik': cik, 'listed': given.get('listed'),
                  'security_type': given.get('security_type'),
                  'shares_outstanding': share['shares_outstanding'] if share else None,
                  'shares_filed': share['shares_filed'] if share else None,
                  'shares_period_end': share['shares_period_end'] if share else None,
                  'share_price_basis': given.get('share_price_basis',
                                                 share['share_price_basis'] if share else None),
                  'price': price, 'price_label': label}
        if given.get('adr_ratio') is not None:
            record['adr_ratio'] = positive_decimal(given['adr_ratio'])
        records.append(record)
        quotes[sid] = _quote(s_price_source, sid, iex_result, price, price_status)
        reasons = _record_reasons(record, share, price_status, basis_given='share_price_basis' in given)
        items[sid] = {'status': UNKNOWN if reasons else SUPPLIED, 'reasons': reasons,
                      'fields': _field_sources(record, given, attrs_source, share, s_price_source, price_status)}

    # ---- counts -------------------------------------------------------------------------------------------------------
    mapped = set(ciks)
    carried_only = [c for c in carried if c not in mapped]
    candidate_reasons = [i['reasons'] for i in items.values()] + [[NOT_IN_SECURITY_MAP_AT_S] for _ in carried_only]
    counts = {
        'candidates': len(candidate_reasons),
        'candidate_securities': len(items),
        'candidate_carried_units_without_security': len(carried_only),
        'eligible_input_present': sum(1 for r in candidate_reasons if not r),
        'unknown': sum(1 for r in candidate_reasons if r),
        'unknown_by_reason': dict(sorted(Counter(r[0] for r in candidate_reasons if r).items())),
        'unknown_reason_occurrences': dict(sorted(Counter(x for r in candidate_reasons for x in r).items())),
        'companyfacts': counts_by_status(facts_items),
        'as_filed_sic': counts_by_status(sic_items),
        'shares': counts_by_status(shares),
        's_price': dict(sorted(Counter(_price_code(i) for i in items.values()).items())),
        'iex_status': iex_result['counts'],
        't_open': dict(sorted(Counter(a['coverage']['t_open'] for a in alpaca.values()).items())),
        'next_t_open': dict(sorted(Counter(a['coverage']['next_t_open'] for a in alpaca.values()).items())),
        'price_rows': len(prices),
        'filing_rows': len(filing_rows),
        'terminations': {k: termination_counts.get(k, 0)
                         for k in ('termination_records', 'with_effective_date', 'without_effective_date')},
    }
    period = f'{signal.isoformat()}..{next_t.isoformat()}'
    payloads = [
        ('records', f'records:{year}', f'records_{year}.json',
         {'signal_day': signal.isoformat(), 'records': records, 'terminations': terminations},
         'adapters: caller security map, SEC cover shares (companyfacts.zip), S price ' + s_price_source,
         SEC_RIGHTS + '; ' + (IEX_RIGHTS if s_price_source == S_PRICE_IEX else alpaca_bars.RIGHTS_NOTE)),
        ('quotes', f'quotes:{year}', f'quotes_{year}.json', {'signal_day': signal.isoformat(), 'quotes': quotes},
         'adapters: S price ' + s_price_source, IEX_RIGHTS if s_price_source == S_PRICE_IEX else alpaca_bars.RIGHTS_NOTE),
        ('companyfacts', 'companyfacts:pit', 'companyfacts_pit.json', facts,
         'adapters: SEC companyfacts.zip, rows usable at S only', SEC_RIGHTS),
        ('filings', 'filings', 'filings.json', filing_rows, 'adapters: SEC FSDS sub.txt as-filed SIC', SEC_RIGHTS),
        ('prices', 'prices', 'prices.json', prices, 'adapters: ' + alpaca_bars.SOURCE_NAME, alpaca_bars.RIGHTS_NOTE),
    ]
    files, resources = [], []
    for _, name, filename, payload, source, rights in payloads:
        data = dumps(payload)
        files.append((filename, data))
        resources.append({'name': name, 'path': filename, 'sha256': sha256_bytes(data), 'source': source, 'period': period,
                          'rights_note': rights})
    provenance = {
        'schema': PROVENANCE_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID, 'year': year,
        'signal_day': signal.isoformat(), 'execution_day': execution.isoformat(),
        'next_execution_day': next_t.isoformat(), 'population_status': POPULATION_STATUS,
        'candidate_source': 'CALLER_SECURITY_MAP',
        's_price': {'source': s_price_source,
                    'label': iex_signal.LABEL if s_price_source == S_PRICE_IEX else ALPACA_CLOSE_LABEL,
                    'use': iex_signal.USE if s_price_source == S_PRICE_IEX else 'S_CONSOLIDATED_CLOSE'},
        't_open': {'source': alpaca_bars.SOURCE, 'role': alpaca_bars.OPEN_ROLE},
        'sources': sorted(sources, key=lambda s: (s['role'], s['file'])),
        'attributes_source': attrs_source, 'effective_dates_source': dates_source,
        'securities': items,
        'ciks': {c: {'companyfacts': facts_items.get(c), 'as_filed_sic': sic_items.get(c), 'shares': shares.get(c)}
                 for c in ciks},
        'carried_units_without_security': carried_only,
        'terminations': termination_rows, 'termination_counts': termination_counts, 'sic_counts': sic_counts,
        'iex': {'status': iex_result['status'], 'counts': iex_result['counts']},
        'alpaca': {sid: {k: v for k, v in a.items() if k != 'close_at_s'} for sid, a in alpaca.items()},
        'counts': counts, 'cannot_supply': list(CANNOT_SUPPLY),
    }
    files.append(('adapter_provenance.json', dumps(provenance)))
    manifest = {'schema': INPUT_MANIFEST_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID, 'resources': resources}
    files.append(('manifest.json', dumps(manifest)))
    return {'files': files, 'counts': counts}


def _merge_missing(result, missing):
    """Securities of the map that an IexDay mapping does not name are UNMAPPED (never priced)."""
    if not missing:
        return result
    quotes, status = dict(result['quotes']), dict(result['status'])
    for sid in missing:
        status[sid] = iex_signal.UNMAPPED
        quotes[sid] = {'price': None, 'currency': iex_signal.CURRENCY, 'month_closes': {},
                       'price_label': iex_signal.LABEL, 'withheld_reason': iex_signal.UNMAPPED}
    return dict(result, quotes=dict(sorted(quotes.items())), status=dict(sorted(status.items())),
                counts=dict(sorted(Counter(status.values()).items())))


def _close_at(series, day, span):
    if series is None or series['status'] != alpaca_bars.OK or day not in series['bars']:
        return None
    if span is not None and not alpaca_bars._in_span(day, span):
        return None
    return series['bars'][day]['close']


def _s_price(source, sid, iex_result, alpaca_item):
    """(price or None, label, status code) of the S price for one security from the one chosen source."""
    if source == S_PRICE_IEX:
        status = iex_result['status'].get(sid, iex_signal.UNMAPPED)
        price = iex_result['quotes'].get(sid, {}).get('price') if status == iex_signal.SUPPLIED else None
        return price, iex_signal.LABEL, status
    status = alpaca_item['coverage']['s_close']
    price = alpaca_item['close_at_s'] if status == SUPPLIED else None
    return price, ALPACA_CLOSE_LABEL, status


def _quote(source, sid, iex_result, price, status):
    if source == S_PRICE_IEX:
        return dict(iex_result['quotes'][sid])
    quote = {'price': price, 'currency': 'USD', 'month_closes': {}, 'price_label': ALPACA_CLOSE_LABEL}
    if status != SUPPLIED:
        quote['withheld_reason'] = status
    return quote


def _record_reasons(record, share, price_status, *, basis_given):
    """Ordered UNKNOWN reasons of one record (adapter view of the engine's eligibility inputs); [] = inputs present."""
    reasons = []
    if record['cik'] is None:
        reasons.append(CIK_MISSING)
    if record['listed'] is None:
        reasons.append(LISTING_STATUS_NOT_SUPPLIED)
    if record['security_type'] is None:
        reasons.append(SECURITY_TYPE_NOT_SUPPLIED)
    if share is not None and share['status'] != SUPPLIED:
        reasons.extend(share['reasons'])
    if record['shares_outstanding'] is not None and record['share_price_basis'] != 'CONFIRMED':
        reasons.append(SHARE_PRICE_BASIS_NOT_CONFIRMED if basis_given
                       else sec_bulk.SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK)
    if price_status != SUPPLIED:
        reasons.append(price_status)
    if record['security_type'] == settings.ADR_SECURITY_TYPE and record.get('adr_ratio') is None:
        reasons.append(ADR_RATIO_NOT_SUPPLIED)
    return list(dict.fromkeys(reasons))


def _price_code(item):
    return item['fields']['price']['status']


def _field_sources(record, given, attrs_source, share, s_price_source, price_status):
    """{field: {'source', 'status'}} of one record: where each value came from, or why it is missing."""
    out = {}
    for key, missing in (('listed', LISTING_STATUS_NOT_SUPPLIED), ('security_type', SECURITY_TYPE_NOT_SUPPLIED),
                         ('adr_ratio', ADR_RATIO_NOT_SUPPLIED)):
        if key in given and given[key] is not None:
            out[key] = {'source': attrs_source['source'], 'status': SUPPLIED}
        else:
            out[key] = {'source': None, 'status': missing}
    share_status = share['status'] if share else CIK_MISSING
    for key in ('shares_outstanding', 'shares_filed', 'shares_period_end'):
        out[key] = {'source': sec_bulk.SOURCE_COMPANYFACTS if share else None,
                    'status': SUPPLIED if share_status == SUPPLIED else (share['reasons'][0] if share else CIK_MISSING)}
    if 'share_price_basis' in given:
        out['share_price_basis'] = {'source': attrs_source['source'], 'status': record['share_price_basis']}
    elif share is None:
        out['share_price_basis'] = {'source': None, 'status': CIK_MISSING}
    else:
        out['share_price_basis'] = {'source': sec_bulk.SOURCE_COMPANYFACTS,
                                    'status': sec_bulk.SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK}
    out['price'] = {'source': iex_signal.SOURCE if s_price_source == S_PRICE_IEX else alpaca_bars.SOURCE_NAME,
                    'status': price_status}
    return out


def count_lines(counts):
    """'key=value' lines of a counts block (numbers and reason codes only; safe to print)."""
    lines = []
    for key, value in counts.items():
        if isinstance(value, dict):
            flat = ','.join(f'{k}:{_flat(v)}' for k, v in value.items()) or '-'
            lines.append(f'{key}={flat}')
        else:
            lines.append(f'{key}={value}')
    return lines


def _flat(value):
    if isinstance(value, dict):
        return '/'.join(f'{k}:{v}' for k, v in value.items()) or '-'
    return value
