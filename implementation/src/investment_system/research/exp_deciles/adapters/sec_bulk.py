"""SEC one-time collection assets -> EXP-STOCK-INDICATOR-DECILES-v1 SEC inputs for one signal day S. Offline, read only.

Source files (the stored asset names and formats of the planned SEC one-time collection, PR #460 branch
claude/sec-once-collect-plan: implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md section 5 and
tools/measure_once/sec_once_collect.py plan_items):
  companyfacts.zip                      SEC bulk XBRL facts, one member CIK##########.json per issuer ({"cik", "entityName",
                                        "facts": {taxonomy: {concept: {"units": {unit: [row, ...]}}}}}, row {"end", "val",
                                        "accn", "fy", "fp", "form", "filed", "frame"?, "start"?})
  submissions.zip                       SEC bulk submissions, member CIK##########.json ({"tickers": [...], ...}; today's
                                        values) -- read only for the multi-class check below
  full-index-<y>-QTR<n>-form.idx.gz     EDGAR full-index form.idx (stored gzip; a plain form.idx is read too): header, a
                                        '-----' line, then fixed-width rows read from the right (file name
                                        edgar/data/<cik>/<accession>.txt, date filed, form type = first field)
  fsds-<y>q<n>.zip                      Financial Statement Data Sets quarter; its sub.txt (tab separated, header row) has
                                        adsh, cik, sic, form, filed (YYYYMMDD) among other columns

Outputs for S (each per-CIK item is SUPPLIED or UNKNOWN with fixed reason codes; nothing is filled with 0):
  (a) pit_companyfacts   {cik: companyfacts payload keeping only rows usable at S} -- pit.filter_companyfacts, i.e.
                         filed <= schedule.compute_cutoff(S) (6th-session rule), the hindsight `frame` tag removed; the
                         engine filters again with the same rule, so the bundle never carries a fact filed after the cutoff
  (b) as_filed_sic       engine filing rows {cik, accn, filed, sic} from FSDS sub.txt (the SIC assigned as of the filing),
                         rows filed after the cutoff left out; per CIK the SIC pit.as_filed_sic would pick at S. A current
                         SIC (submissions) is never used
  (c) cover_shares       F2 share-count fields from the non-dimensional dei:EntityCommonStockSharesOutstanding of the
                         latest filing usable at S: shares_outstanding, shares_filed (its NY filing date),
                         shares_period_end (the count's as-of date). SINGLE-CLASS ONLY: companyfacts drops dimensional
                         facts, so a class count cannot be told from a total. Any multi-class evidence -> UNKNOWN:
                         MULTI_CLASS_SECURITIES_AT_S (the caller's security map has more than one security of the CIK at S),
                         MULTI_TICKER_IN_SUBMISSIONS (today's submissions list more than one ticker: used only to withhold,
                         never to include), COVER_SHARES_AMBIGUOUS_IN_FILING (more than one count in that filing).
                         share_price_basis is always 'UNCONFIRMED' (SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK): no corporate
                         action source is part of these files, so the engine keeps the issuer UNKNOWN until a confirmed
                         basis is supplied from elsewhere. No single-class status is proven: a SUPPLIED count only means
                         no multi-class evidence was found (single_class_basis NO_MULTI_CLASS_EVIDENCE)
  (d) terminations       engine termination records {cik, evidence, filed, effective_date?} from form.idx rows of Form
                         25 / 25-NSE / 15-12B / 15-12G / 15-15D / 15F-12B / 15F-12G / 15F-15D filed on or before the cutoff
                         (usable at S). An index row carries no effective date and no security class (a Form 25 can delist a
                         note or a preferred class), so effective_date is set only from a caller-supplied confirmed date
                         per accession (`effective_dates`); otherwise it is absent and the engine treats the termination as
                         not effective (TERMINATION_EFFECTIVE_DATE_MISSING). Amendments are counted, not used

Cannot be supplied from these files (settings doc section 5, plan section 3.1): listing status at S, security type and
exchange, ADR ratio, tradability, per-class share counts of multi-class issuers, split basis of the share count,
dividends / splits / merger terms, point-in-time ticker <-> CIK spans, any price.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import zipfile
from collections import Counter
from decimal import Decimal

from .. import pit, schedule
from ....qgv.sic_industry import normalize_sic
from .common import SUPPLIED, UNKNOWN, AdapterError, cik10, compact_day, item, iso_day

SOURCE_COMPANYFACTS = 'SEC companyfacts.zip'
SOURCE_SUBMISSIONS = 'SEC submissions.zip'
SOURCE_FORM_IDX = 'SEC EDGAR full-index form.idx'
SOURCE_FSDS = 'SEC Financial Statement Data Sets sub.txt'
COVER_CONCEPT = ('dei', 'EntityCommonStockSharesOutstanding', 'shares')
TERMINATION_FORMS = ('25', '25-NSE', '15-12B', '15-12G', '15-15D', '15F-12B', '15F-12G', '15F-15D')
BASIS_UNCONFIRMED = 'UNCONFIRMED'
SINGLE_CLASS_BASIS = 'NO_MULTI_CLASS_EVIDENCE'

# reason codes
COMPANYFACTS_ARCHIVE_NOT_SUPPLIED = 'COMPANYFACTS_ARCHIVE_NOT_SUPPLIED'
COMPANYFACTS_NOT_IN_ARCHIVE = 'COMPANYFACTS_NOT_IN_ARCHIVE'
COMPANYFACTS_INVALID = 'COMPANYFACTS_INVALID'
COMPANYFACTS_CIK_MISMATCH = 'COMPANYFACTS_CIK_MISMATCH'
COMPANYFACTS_NO_ROWS_USABLE_AT_S = 'COMPANYFACTS_NO_ROWS_USABLE_AT_S'
FSDS_NOT_SUPPLIED = 'FSDS_NOT_SUPPLIED'
SIC_AS_FILED_NOT_IN_FSDS = 'SIC_AS_FILED_NOT_IN_FSDS'
COVER_SHARES_NOT_IN_COMPANYFACTS = 'COVER_SHARES_NOT_IN_COMPANYFACTS'
COVER_SHARES_NOT_USABLE_AT_S = 'COVER_SHARES_NOT_USABLE_AT_S'
COVER_SHARES_AMBIGUOUS_IN_FILING = 'COVER_SHARES_AMBIGUOUS_IN_FILING'
COVER_SHARES_INVALID = 'COVER_SHARES_INVALID'
MULTI_CLASS_SECURITIES_AT_S = 'MULTI_CLASS_SECURITIES_AT_S'
MULTI_TICKER_IN_SUBMISSIONS = 'MULTI_TICKER_IN_SUBMISSIONS'
SUBMISSIONS_TICKER_CHECK_NOT_RUN = 'SUBMISSIONS_TICKER_CHECK_NOT_RUN'
SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK = 'SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK'
EFFECTIVE_DATE_NOT_IN_INDEX_ROW = 'EFFECTIVE_DATE_NOT_IN_INDEX_ROW'
TERMINATION_CLASS_NOT_IN_INDEX_ROW = 'TERMINATION_CLASS_NOT_IN_INDEX_ROW'
EFFECTIVE_DATE_CONFIRMED_BY_CALLER = 'EFFECTIVE_DATE_CONFIRMED_BY_CALLER'

_IDX_PATH = re.compile(rb'edgar/data/([0-9]{1,10})/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt')
_IDX_DAY = re.compile(rb'[0-9]{4}-?[0-9]{2}-?[0-9]{2}')
_ACCN = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')


def _cutoff(signal_day):
    return schedule.compute_cutoff(iso_day(signal_day))


def _cik_set(ciks):
    out = set()
    for value in ciks:
        key = cik10(value)
        if key is None:
            raise AdapterError('CIK_INVALID')
        out.add(key)
    return sorted(out)


def _member(archive, key):
    try:
        return archive.read(f'CIK{key}.json')
    except KeyError:
        return None


# ---- (a) companyfacts ----------------------------------------------------------------------------------------------
def load_companyfacts(zip_path, ciks):
    """({cik: raw companyfacts payload}, {cik: UNKNOWN item}) for the requested CIKs (floats as the SEC publishes them)."""
    payloads, problems = {}, {}
    keys = _cik_set(ciks)
    if zip_path is None:
        return {}, {k: item(UNKNOWN, [COMPANYFACTS_ARCHIVE_NOT_SUPPLIED]) for k in keys}
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile):
        raise AdapterError('COMPANYFACTS_ARCHIVE_NOT_READABLE') from None
    with archive:
        for key in keys:
            data = _member(archive, key)
            if data is None:
                problems[key] = item(UNKNOWN, [COMPANYFACTS_NOT_IN_ARCHIVE])
                continue
            try:
                payload = json.loads(data.decode('utf-8'))
            except (UnicodeDecodeError, ValueError):
                payload = None
            if not isinstance(payload, dict) or not isinstance(payload.get('facts'), dict):
                problems[key] = item(UNKNOWN, [COMPANYFACTS_INVALID])
                continue
            if cik10(payload.get('cik')) != key:
                problems[key] = item(UNKNOWN, [COMPANYFACTS_CIK_MISMATCH])
                continue
            payloads[key] = payload
    return payloads, problems


def pit_companyfacts(raw_payloads, problems, signal_day):
    """({cik: PIT payload}, {cik: item}) -- (a) of the module doc."""
    signal = iso_day(signal_day)
    out, items = {}, dict(problems)
    for key in sorted(raw_payloads):
        try:
            view = pit.filter_companyfacts(raw_payloads[key], signal)
        except ValueError:
            items[key] = item(UNKNOWN, [COMPANYFACTS_INVALID])
            continue
        if not view.filings:
            items[key] = item(UNKNOWN, [COMPANYFACTS_NO_ROWS_USABLE_AT_S], rejected=dict(sorted(view.rejected.items())))
            continue
        out[key] = view.payload
        items[key] = item(SUPPLIED, filings=len(view.filings), latest_filed=view.filings[-1]['filed'],
                          compute_cutoff=view.compute_cutoff.isoformat(), rejected=dict(sorted(view.rejected.items())))
    return out, dict(sorted(items.items()))


# ---- (b) as-filed SIC from FSDS sub.txt -------------------------------------------------------------------------------
def _sub_rows(zip_path):
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile):
        raise AdapterError('FSDS_ARCHIVE_NOT_READABLE') from None
    with archive:
        try:
            data = archive.read('sub.txt')
        except KeyError:
            raise AdapterError('FSDS_SUB_TXT_MISSING') from None
    reader = csv.reader(io.StringIO(data.decode('utf-8', errors='replace')), delimiter='\t', quoting=csv.QUOTE_NONE)
    header = next(reader, None)
    if header is None or not {'adsh', 'cik', 'sic', 'form', 'filed'} <= set(header):
        raise AdapterError('FSDS_SUB_TXT_HEADER_INVALID')
    index = {name: header.index(name) for name in ('adsh', 'cik', 'sic', 'form', 'filed')}
    for row in reader:
        if len(row) < len(header):
            yield None
            continue
        yield {name: row[i] for name, i in index.items()}


def as_filed_sic(fsds_paths, ciks, signal_day):
    """(engine filing rows, {cik: item}, counts) -- (b) of the module doc."""
    signal = iso_day(signal_day)
    cutoff = _cutoff(signal)
    keys = _cik_set(ciks)
    wanted = set(keys)
    counts = Counter()
    rows = set()
    for path in sorted(fsds_paths or (), key=str):
        for row in _sub_rows(path):
            counts['sub_rows'] += 1
            if row is None:
                counts['sub_rows_malformed'] += 1
                continue
            key = cik10(row['cik'])
            if key not in wanted:
                continue
            filed = compact_day(row['filed'])
            accn = row['adsh'].strip()
            if filed is None or not _ACCN.fullmatch(accn):
                counts['candidate_rows_invalid'] += 1
                continue
            if filed > cutoff:
                counts['candidate_rows_not_usable_at_s'] += 1
                continue
            sic = normalize_sic(row['sic'])
            if sic is None:
                counts['candidate_rows_sic_missing'] += 1
                continue
            rows.add((key, accn, filed.isoformat(), sic))
    filing_rows = [{'cik': k, 'accn': a, 'filed': f, 'sic': s} for k, a, f, s in sorted(rows)]
    counts['filing_rows'] = len(filing_rows)
    items = {}
    for key in keys:
        if not fsds_paths:
            items[key] = item(UNKNOWN, [FSDS_NOT_SUPPLIED])
            continue
        record = pit.as_filed_sic(filing_rows, signal, key)
        if record['sic'] is None:
            items[key] = item(UNKNOWN, [SIC_AS_FILED_NOT_IN_FSDS])
        else:
            items[key] = item(SUPPLIED, sic=record['sic'], accn=record['accn'], filed=record['filed'],
                              usable_from=record['usable_from'])
    return filing_rows, items, dict(sorted(counts.items()))


# ---- (c) single-class cover share counts -------------------------------------------------------------------------------
def submissions_ticker_counts(zip_path, ciks):
    """{cik: number of tickers in today's submissions JSON, or None when the CIK is not in the archive}."""
    keys = _cik_set(ciks)
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile):
        raise AdapterError('SUBMISSIONS_ARCHIVE_NOT_READABLE') from None
    out = {}
    with archive:
        for key in keys:
            data = _member(archive, key)
            try:
                payload = json.loads(data.decode('utf-8')) if data is not None else None
            except (UnicodeDecodeError, ValueError):
                payload = None
            tickers = payload.get('tickers') if isinstance(payload, dict) else None
            out[key] = len({t for t in tickers if isinstance(t, str) and t.strip()}) if isinstance(tickers, list) else None
    return out


def _share_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and value > 0:
        return Decimal(value)
    return None


def _empty_shares(reasons, **extra):
    return item(UNKNOWN, reasons, shares_outstanding=None, shares_filed=None, shares_period_end=None,
                share_price_basis=BASIS_UNCONFIRMED, **extra)


def cover_shares(raw_payloads, problems, ciks, signal_day, *, securities_per_cik=None, ticker_counts=None):
    """{cik: share item} -- (c) of the module doc. securities_per_cik: {cik: number of securities of that CIK in the
    caller's security map at S}; ticker_counts: submissions_ticker_counts(...) or None (check not run, flagged)."""
    cutoff = _cutoff(signal_day)
    out = {}
    for key in _cik_set(ciks):
        flags = [] if ticker_counts is not None else [SUBMISSIONS_TICKER_CHECK_NOT_RUN]
        multi = []
        if (securities_per_cik or {}).get(key, 0) > 1:
            multi.append(MULTI_CLASS_SECURITIES_AT_S)
        if ticker_counts is not None and (ticker_counts.get(key) or 0) > 1:
            multi.append(MULTI_TICKER_IN_SUBMISSIONS)
        if multi:
            out[key] = _empty_shares(multi, flags=flags)
            continue
        if key not in raw_payloads:
            reason = problems.get(key, {}).get('reasons') or [COMPANYFACTS_NOT_IN_ARCHIVE]
            out[key] = _empty_shares(list(reason), flags=flags)
            continue
        taxonomy, concept, unit = COVER_CONCEPT
        fact = ((raw_payloads[key].get('facts') or {}).get(taxonomy) or {}).get(concept)
        rows = ((fact or {}).get('units') or {}).get(unit) if isinstance(fact, dict) else None
        if not isinstance(rows, list) or not rows:
            out[key] = _empty_shares([COVER_SHARES_NOT_IN_COMPANYFACTS], flags=flags)
            continue
        usable = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            filed, end = compact_day(row.get('filed')), compact_day(row.get('end'))
            accn = str(row.get('accn') or '').strip()
            if filed is None or end is None or not accn or filed > cutoff:
                continue
            usable.append((filed, accn, end, row.get('val')))
        if not usable:
            out[key] = _empty_shares([COVER_SHARES_NOT_USABLE_AT_S], flags=flags)
            continue
        filed, accn = max((f, a) for f, a, _, _ in usable)
        values = {(end, repr(val)): (end, val) for f, a, end, val in usable if (f, a) == (filed, accn)}
        if len(values) != 1:
            out[key] = _empty_shares([COVER_SHARES_AMBIGUOUS_IN_FILING], flags=flags, accn=accn, filed=filed.isoformat())
            continue
        end, val = next(iter(values.values()))
        shares = _share_value(val)
        if shares is None:
            out[key] = _empty_shares([COVER_SHARES_INVALID], flags=flags, accn=accn, filed=filed.isoformat())
            continue
        out[key] = item(SUPPLIED, shares_outstanding=shares, shares_filed=filed.isoformat(),
                        shares_period_end=end.isoformat(), share_price_basis=BASIS_UNCONFIRMED,
                        basis_reason=SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK, single_class_basis=SINGLE_CLASS_BASIS,
                        accn=accn, flags=flags)
    return out


# ---- (d) termination evidence from form.idx -------------------------------------------------------------------------
def _idx_lines(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    try:
        with opener(path, 'rb') as handle:
            data = handle.read()
    except (OSError, EOFError):
        raise AdapterError('FORM_IDX_NOT_READABLE') from None
    return data.split(b'\n')


def form_idx_rows(path, forms):
    """[(cik10, form, filed date, accession)] of the rows whose form type is in `forms`, plus counts."""
    wanted = {f.encode('ascii') for f in forms}
    amended = {f + b'/A' for f in wanted}
    out, counts, header_done = [], Counter(), False
    for raw in _idx_lines(path):
        line = raw.rstrip(b'\r')
        if not header_done:
            header_done = line.startswith(b'-----')
            continue
        parts = line.rsplit(None, 2)
        found = _IDX_PATH.fullmatch(parts[2]) if len(parts) == 3 else None
        if found is None or not _IDX_DAY.fullmatch(parts[1]):
            counts['rows_unreadable'] += int(bool(line.strip()))
            continue
        counts['rows'] += 1
        form = parts[0].split(b'  ', 1)[0].strip()
        if form in amended:
            counts['amendments_not_used'] += 1
            continue
        if form not in wanted:
            continue
        filed = compact_day(parts[1].decode('ascii'))
        if filed is None:
            counts['rows_unreadable'] += 1
            continue
        out.append((found.group(1).decode('ascii').zfill(10), form.decode('ascii'), filed,
                    found.group(2).decode('ascii')))
    if not header_done:
        raise AdapterError('FORM_IDX_HEADER_MISSING')
    return out, counts


def terminations(form_idx_paths, ciks, signal_day, *, effective_dates=None):
    """(engine termination records, provenance rows, counts) -- (d) of the module doc.

    effective_dates: {accession: ISO date} confirmed by the caller from the filing documents (never derived here); a date
    before the filing date is refused (EFFECTIVE_DATE_BEFORE_FILING)."""
    cutoff = _cutoff(signal_day)
    wanted = set(_cik_set(ciks))
    confirmed = {}
    for accn, value in (effective_dates or {}).items():
        if not isinstance(accn, str) or not _ACCN.fullmatch(accn):
            raise AdapterError('EFFECTIVE_DATE_ACCESSION_INVALID')
        confirmed[accn] = iso_day(value)
    counts, found = Counter(), {}
    for path in sorted(form_idx_paths or (), key=str):
        rows, row_counts = form_idx_rows(path, TERMINATION_FORMS)
        counts.update(row_counts)
        for key, form, filed, accn in rows:
            if key not in wanted:
                continue
            if filed > cutoff:
                counts['candidate_rows_not_usable_at_s'] += 1
                continue
            found[(key, accn)] = (form, filed)
    records, provenance = [], []
    for (key, accn), (form, filed) in sorted(found.items(), key=lambda kv: (kv[0][0], kv[1][1], kv[0][1])):
        record = {'cik': key, 'evidence': f'SEC full-index form.idx Form {form} accession {accn}',
                  'filed': filed.isoformat()}
        reasons = [TERMINATION_CLASS_NOT_IN_INDEX_ROW]
        effective = confirmed.get(accn)
        if effective is not None:
            if effective < filed:
                raise AdapterError('EFFECTIVE_DATE_BEFORE_FILING')
            record['effective_date'] = effective.isoformat()
            reasons.insert(0, EFFECTIVE_DATE_CONFIRMED_BY_CALLER)
        else:
            reasons.insert(0, EFFECTIVE_DATE_NOT_IN_INDEX_ROW)
        records.append(record)
        provenance.append({'cik': key, 'accn': accn, 'form': form, 'filed': filed.isoformat(),
                           'effective_date': record.get('effective_date'), 'reasons': reasons})
    counts['termination_records'] = len(records)
    counts['with_effective_date'] = sum(1 for r in records if 'effective_date' in r)
    counts['without_effective_date'] = len(records) - counts['with_effective_date']
    return records, provenance, dict(sorted(counts.items()))
