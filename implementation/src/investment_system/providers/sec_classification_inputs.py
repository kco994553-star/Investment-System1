"""Parsers for SIC/theme v0 evidence: submissions SIC + latest 10-K, 10-K Item 1, ETF series binding,
series NPORT-P filing list and N-PORT holdings identifiers.

No network or IO. Returned values stay in RAM. N-PORT balances, values, percentages and units are never
read; only security identifiers of long common-equity rows leave the parser. Item 1 text is returned to
the caller for literal keyword counting only and must not be persisted or published.
"""
from __future__ import annotations

from datetime import date
import html
import json
import re
from xml.etree import ElementTree as ET

MAX_XML_BYTES = 32 * 1024 * 1024
MIN_ITEM1_CHARS = 500
_ISIN = re.compile(r'[A-Z]{2}[A-Z0-9]{9}[0-9]')
_CUSIP = re.compile(r'[0-9A-Z]{9}')
_SERIES = re.compile(r'S[0-9]{9}')
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_DOC = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.html?')


class EvidenceError(ValueError):
    """Fixed, value-free reason code."""


def _json(body):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError()
            out[k] = v
        return out

    def reject(_):
        raise ValueError()
    try:
        if type(body) is not bytes:
            raise ValueError()
        return json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)
    except (ValueError, UnicodeError, RecursionError):
        raise EvidenceError('JSON_INVALID') from None


def _iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def security_identifiers(isin=None, cusip=None):
    """Exact identifiers used for the ETF join. A CUSIP is derived only from a US-prefixed ISIN."""
    out = set()
    if isinstance(isin, str) and _ISIN.fullmatch(isin):
        out.add('ISIN:' + isin)
        if isin.startswith('US'):
            out.add('CUSIP:' + isin[2:11])
    if isinstance(cusip, str) and _CUSIP.fullmatch(cusip) and cusip != '000000000':
        out.add('CUSIP:' + cusip)
    return frozenset(out)


def submissions_profile(body, expected_cik):
    """SIC (raw string) and the latest original 10-K from SEC submissions 'recent' filings."""
    payload = _json(body)
    if not isinstance(payload, dict):
        raise EvidenceError('SUBMISSIONS_INVALID')
    cik = payload.get('cik')
    if str(cik).zfill(10) != expected_cik:
        raise EvidenceError('SUBMISSIONS_CIK_MISMATCH')
    sic = payload.get('sic')
    recent = (payload.get('filings') or {}).get('recent') if isinstance(payload.get('filings'), dict) else None
    latest = None
    if isinstance(recent, dict):
        cols = [recent.get(k) for k in ('form', 'accessionNumber', 'filingDate', 'reportDate', 'primaryDocument')]
        if all(isinstance(c, list) for c in cols) and len({len(c) for c in cols}) == 1:
            for form, accession, filed, report, doc in zip(*cols):
                if form != '10-K' or not isinstance(accession, str) or not _ACCESSION.fullmatch(accession):
                    continue
                filed = _iso_day(filed)
                if filed is None or not isinstance(doc, str) or not _DOC.fullmatch(doc):
                    continue
                if latest is None or filed > latest['filing_date']:
                    latest = {'accession': accession, 'filing_date': filed, 'report_date': _iso_day(report), 'primary_document': doc}
    return {'sic': sic if isinstance(sic, (str, int)) and not isinstance(sic, bool) else None, 'latest_10k': latest}


_DROP = re.compile(r'<(script|style|head|ix:header)\b[^>]*>.*?</\1\s*>', re.I | re.S)
_BLOCK = re.compile(r'<\s*(?:br|/p|/div|/tr|/li|/h[1-6]|/td|/table)\b[^>]*>', re.I)
_TAG = re.compile(r'<[^>]*>', re.S)
_SEP = r'\s*[.:\-–—]?\s*'
_START = re.compile(r'\bitem\s*1' + _SEP + r'business\b', re.I)
_ENDS = (re.compile(r'\bitem\s*1a' + _SEP + r'risk\s+factors\b', re.I), re.compile(r'\bitem\s*2' + _SEP + r'properties\b', re.I))


def html_text(body):
    text = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else body
    text = _DROP.sub(' ', text)
    text = _BLOCK.sub('\n', text)
    text = html.unescape(_TAG.sub(' ', text)).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text)


def extract_item1(body):
    """Longest 'Item 1. Business' .. 'Item 1A. Risk Factors' (or 'Item 2. Properties') span; skips the table of contents.

    Returns None when no plausible section exists. Item 1A, other items and HTML navigation are excluded.
    """
    if type(body) is not bytes or len(body) > MAX_XML_BYTES:
        raise EvidenceError('TEN_K_INVALID')
    text = html_text(body)
    best = ''
    for end_pattern in _ENDS:
        ends = [m.start() for m in end_pattern.finditer(text)]
        for start in _START.finditer(text):
            stop = next((e for e in ends if e > start.end()), None)
            if stop is not None and stop - start.end() > len(best):
                best = text[start.end():stop]
        if len(best) >= MIN_ITEM1_CHARS:
            return best.strip()
    return None


def bind_etf_series(body, tickers):
    """SEC company_tickers_mf.json: exact symbol -> one (registrant CIK, series ID); ambiguity stays unbound."""
    payload = _json(body)
    try:
        fields, rows = payload['fields'], payload['data']
        if not isinstance(fields, list) or not isinstance(rows, list) or len(rows) > 200000:
            raise ValueError()
        i_cik, i_series, i_symbol = fields.index('cik'), fields.index('seriesId'), fields.index('symbol')
    except (KeyError, ValueError, TypeError):
        raise EvidenceError('MF_TICKERS_INVALID') from None
    wanted = set(tickers)
    found = {t: set() for t in wanted}
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields):
            continue
        symbol, cik, series = row[i_symbol], row[i_cik], row[i_series]
        if symbol in wanted and type(cik) is int and 0 < cik < 10 ** 10 and isinstance(series, str) and _SERIES.fullmatch(series):
            found[symbol].add((str(cik).zfill(10), series))
    return {t: ({'cik': next(iter(v))[0], 'series_id': next(iter(v))[1]} if len(v) == 1 else None) for t, v in found.items()}


def _local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _xml(body):
    if type(body) is not bytes or len(body) > MAX_XML_BYTES or b'<!DOCTYPE' in body[:4096].upper() or b'<!ENTITY' in body.upper():
        raise EvidenceError('XML_INVALID')
    try:
        return ET.fromstring(body)
    except (ET.ParseError, ValueError):
        raise EvidenceError('XML_INVALID') from None


def series_filings(body):
    """EDGAR browse (atom) for one series: original NPORT-P filings, newest first."""
    root = _xml(body)
    out = []
    for entry in root.iter():
        if _local(entry.tag) != 'entry':
            continue
        fields = {}
        for el in entry.iter():
            name = _local(el.tag)
            if name in ('accession-number', 'accession-nunber', 'filing-date', 'filing-type') and name not in fields:
                fields[name] = (el.text or '').strip()
        accession = fields.get('accession-number') or fields.get('accession-nunber')
        filed = _iso_day(fields.get('filing-date'))
        if fields.get('filing-type') == 'NPORT-P' and accession and _ACCESSION.fullmatch(accession) and filed:
            out.append({'accession': accession, 'filing_date': filed})
    out.sort(key=lambda f: f['filing_date'], reverse=True)
    return out


def nport_securities(body, expected_series_id):
    """Identifiers of long common-equity (assetCat EC, payoffProfile Long) rows of one NPORT-P report.

    Balances, values, percentages, units and names are not read. The report must be an original NPORT-P
    for the expected series. Returns {'series_id', 'report_date', 'securities': frozenset}.
    """
    root = _xml(body)
    kind = series = report = None
    securities = set()
    for el in root.iter():
        name = _local(el.tag)
        if name == 'submissionType' and kind is None:
            kind = (el.text or '').strip()
        elif name == 'seriesId' and series is None:
            series = (el.text or '').strip()
        elif name == 'repPdDate' and report is None:
            report = _iso_day((el.text or '').strip())
        elif name == 'invstOrSec':
            row = {'assetCat': None, 'payoffProfile': None, 'cusip': None, 'isin': None}
            for child in el.iter():
                cn = _local(child.tag)
                if cn in ('assetCat', 'payoffProfile', 'cusip') and row[cn] is None:
                    row[cn] = (child.text or '').strip()
                elif cn == 'isin' and row['isin'] is None:
                    row['isin'] = (child.get('value') or child.text or '').strip()
            if row['assetCat'] == 'EC' and row['payoffProfile'] == 'Long':
                securities |= security_identifiers(row['isin'], row['cusip'])
    if kind != 'NPORT-P':
        raise EvidenceError('NPORT_NOT_ORIGINAL')
    if series != expected_series_id:
        raise EvidenceError('NPORT_SERIES_MISMATCH')
    if report is None:
        raise EvidenceError('NPORT_REPORT_DATE_MISSING')
    return {'series_id': series, 'report_date': report, 'securities': frozenset(securities)}
