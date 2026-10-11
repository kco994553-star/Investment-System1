"""Verify configured 13F manager CIKs and capture their latest two 13F-HR tables.

Importing this module performs no requests or environment lookup. A candidate
CIK is verified only when the SEC submissions JSON for that CIK carries exactly
the configured legal name (case/whitespace normalization only, no fuzzy match)
and a recent 13F-HR. Anything else is NOT_AVAILABLE with a fixed reason code.

Captures are raw government bytes kept by the caller in a temporary private
directory; only the public generator's reported-quantity projection and the
verification records are published. Nothing here infers trades, current
holdings or values, and eligibility (amendments, confidential omissions,
partial tables) stays with providers.sec_13f.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
from xml.etree import ElementTree as ET

from ..config.manager_styles import normalize_name
from .sec_13f import FilingMetadata, MAX_PAYLOAD_BYTES, compare_quarters, parse_information_table
from .sec_collection import (MAX_ATTEMPTS, REQUEST_TIMEOUT, RETRY_STATUSES, SecCollectionClient,
                             SecCollectionError, SecResponse, _RejectRedirects)

SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
INDEX_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/index.json'
FILE_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}'
URL_PATTERNS = (
    re.compile(r'https://data\.sec\.gov/submissions/CIK[0-9]{10}\.json'),
    re.compile(r'https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/index\.json'),
    re.compile(r'https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/[A-Za-z0-9_.-]{1,100}\.xml'),
)
FORMS = ('13F-HR', '13F-HR/A')
# Quarterly filing deadline is 45 days; two missed quarters exceed this window.
RECENT_13F_DAYS = 200
# Since 2023-01-03 Form 13F values are reported in dollars, before that in thousands.
DOLLAR_VALUES_FROM = date(2023, 1, 3)
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_FILE = re.compile(r'[A-Za-z0-9_.-]{1,100}\.xml', re.I)
_REPORT_TYPES = {'13F HOLDINGS REPORT': 'HOLDINGS', '13F NOTICE': 'NOTICE', '13F COMBINATION REPORT': 'COMBINATION'}
_AMENDMENTS = {'RESTATEMENT': 'RESTATEMENT', 'NEW HOLDINGS': 'NEW_HOLDINGS'}


class CaptureError(ValueError):
    """Fixed capture reason code, never a response value."""


def _require_url(url: str) -> None:
    if not isinstance(url, str) or not any(p.fullmatch(url) for p in URL_PATTERNS):
        raise SecCollectionError('SEC_URL_NOT_ALLOWED') from None


def default_transport(url: str, *, headers: Mapping[str, str], timeout: float, max_body_bytes: int) -> SecResponse:
    """Fixed SEC 13F routes only, no redirects, bounded body; error bodies are not read."""
    _require_url(url)
    if (type(max_body_bytes) is not int or not 0 < max_body_bytes <= MAX_PAYLOAD_BYTES
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= REQUEST_TIMEOUT):
        raise SecCollectionError('SEC_CONFIG_INVALID') from None
    try:
        with build_opener(_RejectRedirects()).open(Request(url, headers=dict(headers)), timeout=timeout) as response:
            body = response.read(max_body_bytes + 1)
            if len(body) > max_body_bytes:
                raise SecCollectionError('SEC_RESPONSE_TOO_LARGE') from None
            return SecResponse(response.status, body, response.headers.get('Retry-After'), response.geturl())
    except HTTPError as error:
        return SecResponse(error.code, b'', error.headers.get('Retry-After') if error.headers else None, error.geturl())


class Sec13FClient(SecCollectionClient):
    """Same User-Agent rule, pacing and retry budget as the US17 collection client."""

    def __init__(self, user_agent: str, *, transport: Callable = default_transport, **kwargs) -> None:
        super().__init__(user_agent, transport=transport, **kwargs)

    def fetch(self, url: str) -> tuple[bytes, datetime]:
        _require_url(url)
        with self._lock:
            for attempt in range(MAX_ATTEMPTS):
                self._pace()
                try:
                    response = self._transport(url, headers={'User-Agent': self._user_agent, 'Accept': '*/*'},
                                               timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_PAYLOAD_BYTES)
                except SecCollectionError:
                    raise SecCollectionError('SEC_TRANSPORT_FAILED') from None
                except (URLError, OSError):
                    if attempt == MAX_ATTEMPTS - 1:
                        raise SecCollectionError('SEC_TRANSPORT_RETRIES_EXHAUSTED') from None
                    self._pause(2.0 ** (attempt + 1))
                    continue
                except Exception:
                    raise SecCollectionError('SEC_TRANSPORT_FAILED') from None
                if (not isinstance(response, SecResponse) or type(response.status) is not int
                        or not isinstance(response.body, bytes) or response.final_url != url
                        or len(response.body) > MAX_PAYLOAD_BYTES):
                    raise SecCollectionError('SEC_RESPONSE_INVALID') from None
                if response.status == 200:
                    return response.body, self._utc()
                if response.status not in RETRY_STATUSES or attempt == MAX_ATTEMPTS - 1:
                    raise SecCollectionError('SEC_HTTP_FAILED') from None
                self._pause(self._retry_wait(response.retry_after, 2.0 ** (attempt + 1)))
        raise SecCollectionError('SEC_TRANSPORT_FAILED') from None


def _json(body: bytes):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('duplicate')
            out[key] = value
        return out

    def reject(_value):
        raise ValueError('constant')
    return json.loads(body.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)


def _filings(submissions: dict) -> list[dict]:
    recent = submissions['filings']['recent']
    columns = ('accessionNumber', 'filingDate', 'reportDate', 'form', 'primaryDocument')
    size = len(recent['accessionNumber'])
    if any(not isinstance(recent[c], list) or len(recent[c]) != size for c in columns):
        raise ValueError('columns')
    rows = []
    for index in range(size):
        row = {c: recent[c][index] for c in columns}
        if row['form'] not in FORMS:
            continue
        if (not isinstance(row['accessionNumber'], str) or _ACCESSION.fullmatch(row['accessionNumber']) is None
                or not isinstance(row['primaryDocument'], str)):
            raise ValueError('row')
        row['filingDate'] = date.fromisoformat(row['filingDate'])
        row['reportDate'] = date.fromisoformat(row['reportDate']) if row['reportDate'] else None
        rows.append(row)
    return rows


def _na(manager: dict, reason: str) -> dict:
    return {'id': manager['id'], 'cik': manager['candidate_cik'], 'state': 'NOT_AVAILABLE', 'reason_code': reason,
            'matched_name': None, 'verified_at': None, 'latest_13f_accession': None,
            'capture_reason': None, 'comparison_reasons': []}


def verify_manager(manager: dict, submissions_body: bytes | None, acquired_at: datetime | None, *, as_of: datetime):
    """Return (public record, 13F filing rows). Exact name and recent 13F-HR or NOT_AVAILABLE.

    The SEC entity name is published only when it matched the configured name.
    """
    cik = manager['candidate_cik']
    if cik is None:
        return _na(manager, 'CIK_NOT_CONFIGURED'), []
    if submissions_body is None or acquired_at is None:
        return _na(manager, 'SUBMISSIONS_UNAVAILABLE'), []
    try:
        payload = _json(submissions_body)
        reported = payload['cik']
        name = payload['name']
        rows = _filings(payload)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError):
        return _na(manager, 'SUBMISSIONS_INVALID'), []
    if not ((type(reported) is int and str(reported).zfill(10) == cik)
            or (isinstance(reported, str) and re.fullmatch(r'[0-9]{1,10}', reported) and reported.zfill(10) == cik)):
        return _na(manager, 'CIK_MISMATCH'), []
    if not isinstance(name, str) or normalize_name(name) != normalize_name(manager['expected_sec_name']):
        return _na(manager, 'NAME_MISMATCH'), []
    cutoff = as_of.astimezone(timezone.utc).date()
    originals = [r for r in rows if r['form'] == '13F-HR' and r['filingDate'] <= cutoff]
    if not originals or max(r['filingDate'] for r in originals) < cutoff - timedelta(days=RECENT_13F_DAYS):
        return _na(manager, 'NO_RECENT_13F_HR'), []
    latest = max((r for r in rows if r['filingDate'] <= cutoff), key=lambda r: (r['filingDate'], r['accessionNumber']))
    record = {'id': manager['id'], 'cik': cik, 'state': 'VERIFIED', 'reason_code': None,
              'matched_name': ' '.join(name.split()), 'verified_at': acquired_at.astimezone(timezone.utc).isoformat(),
              'latest_13f_accession': latest['accessionNumber'], 'capture_reason': None, 'comparison_reasons': []}
    return record, rows


def select_quarters(rows: list[dict]) -> list[dict]:
    """Latest two report quarters with an original 13F-HR, newest first.

    lineage_resolved only when the quarter has exactly one 13F-HR and no
    13F-HR/A in the submissions list; otherwise the comparison stays NA.
    """
    by_quarter: dict[date, list[dict]] = {}
    for row in rows:
        if row['reportDate'] is not None:
            by_quarter.setdefault(row['reportDate'], []).append(row)
    chosen = []
    for quarter in sorted(by_quarter, reverse=True):
        group = by_quarter[quarter]
        originals = [r for r in group if r['form'] == '13F-HR']
        if not originals:
            continue
        filing = dict(max(originals, key=lambda r: (r['filingDate'], r['accessionNumber'])))
        filing['lineage_resolved'] = len(originals) == 1 and len(group) == 1
        chosen.append(filing)
        if len(chosen) == 2:
            break
    return chosen


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _find(element, *path):
    for name in path:
        if element is None:
            return None
        matches = [child for child in element if _local(child.tag) == name]
        if len(matches) > 1:
            raise CaptureError('COVER_INVALID')
        element = matches[0] if matches else None
    return element


def _value(element, *path) -> str | None:
    node = _find(element, *path)
    return None if node is None else (node.text or '').strip()


def _us_date(text: str | None) -> date:
    match = re.fullmatch(r'([0-9]{2})-([0-9]{2})-([0-9]{4})', text or '')
    if match is None:
        raise CaptureError('COVER_INVALID')
    return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))


def _count(text: str | None) -> int | None:
    if text is None:
        return None
    if re.fullmatch(r'[0-9]{1,16}', text) is None:
        raise CaptureError('COVER_INVALID')
    return int(text)


def _flag(text: str | None) -> bool | None:
    if text is None:
        return None
    if text.lower() not in ('true', 'false', 'y', 'n'):
        raise CaptureError('COVER_INVALID')
    return text.lower() in ('true', 'y')


def parse_cover(body: bytes) -> dict:
    """Read only the cover/summary fields Form 13F comparison needs (namespace-agnostic)."""
    upper = body.replace(b'\x00', b'').upper()
    if b'\x00' in body or b'<!DOCTYPE' in upper or b'<!ENTITY' in upper:
        raise CaptureError('COVER_INVALID')
    try:
        root = ET.fromstring(body)
    except (ET.ParseError, ValueError, RecursionError):
        raise CaptureError('COVER_INVALID') from None
    if _local(root.tag) != 'edgarSubmission':
        raise CaptureError('COVER_INVALID')
    try:
        cik = _value(root, 'headerData', 'filerInfo', 'filer', 'credentials', 'cik')
        if cik is None or re.fullmatch(r'[0-9]{1,10}', cik) is None:
            raise CaptureError('COVER_INVALID')
        cover = _find(root, 'formData', 'coverPage')
        if cover is None:
            raise CaptureError('COVER_INVALID')
        report_type = _REPORT_TYPES.get(_value(cover, 'reportType') or '')
        if report_type is None:
            raise CaptureError('COVER_INVALID')
        amendment = _value(cover, 'amendmentInfo', 'amendmentType')
        if amendment is not None and amendment not in _AMENDMENTS:
            raise CaptureError('COVER_INVALID')
        summary = _find(root, 'formData', 'summaryPage')
        others = {}
        holder = _find(summary, 'otherManagers2Info') if summary is not None else None
        for item in (holder if holder is not None else ()):
            if _local(item.tag) != 'otherManager2':
                continue
            sequence = _value(item, 'sequenceNumber')
            other_cik = _value(item, 'otherManager', 'cik')
            if sequence is None or re.fullmatch(r'[0-9]{1,3}', sequence) is None or sequence in others:
                raise CaptureError('COVER_INVALID')
            if other_cik:
                if re.fullmatch(r'[0-9]{1,10}', other_cik) is None or int(other_cik) == 0:
                    raise CaptureError('COVER_INVALID')
                others[sequence] = other_cik.zfill(10)
        return {
            'cik': cik.zfill(10),
            'submission_type': _value(root, 'headerData', 'submissionType'),
            'period': _us_date(_value(root, 'headerData', 'filerInfo', 'periodOfReport')),
            'calendar_quarter': _us_date(_value(cover, 'reportCalendarOrQuarter')),
            'is_amendment': _flag(_value(cover, 'isAmendment')),
            'amendment_type': _AMENDMENTS.get(amendment) if amendment else None,
            'report_type': report_type,
            'entry_total': _count(_value(summary, 'tableEntryTotal')) if summary is not None else None,
            'value_total': _count(_value(summary, 'tableValueTotal')) if summary is not None else None,
            'confidential_omitted': _flag(_value(summary, 'isConfidentialOmitted')) if summary is not None else None,
            'other_manager_ciks': others,
        }
    except ValueError as error:
        if isinstance(error, CaptureError):
            raise
        raise CaptureError('COVER_INVALID') from None


def _folder(accession: str) -> str:
    return accession.replace('-', '')


def capture_filing(fetch: Callable[[str], tuple[bytes, datetime]], cik: str, filing: dict) -> tuple[bytes, dict]:
    """Fetch index, cover and information table; return (table bytes, generator metadata JSON)."""
    folder, cik_path = _folder(filing['accessionNumber']), str(int(cik))
    primary = filing['primaryDocument'].rsplit('/', 1)[-1]
    if _FILE.fullmatch(primary) is None:
        raise CaptureError('COVER_UNAVAILABLE')
    try:
        index_body, _ = fetch(INDEX_URL.format(cik=cik_path, folder=folder))
        items = _json(index_body)['directory']['item']
        names = [item['name'] for item in items]
        if not all(isinstance(name, str) for name in names):
            raise ValueError('names')
    except SecCollectionError:
        raise CaptureError('FILING_INDEX_UNAVAILABLE') from None
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise CaptureError('FILING_INDEX_UNAVAILABLE') from None
    tables = [name for name in names if _FILE.fullmatch(name) and name.lower() != primary.lower()]
    if len(tables) != 1 or primary not in names:
        raise CaptureError('INFOTABLE_NOT_IDENTIFIED')
    try:
        cover_body, _ = fetch(FILE_URL.format(cik=cik_path, folder=folder, name=primary))
    except SecCollectionError:
        raise CaptureError('COVER_UNAVAILABLE') from None
    cover = parse_cover(cover_body)
    try:
        table, acquired = fetch(FILE_URL.format(cik=cik_path, folder=folder, name=tables[0]))
    except SecCollectionError:
        raise CaptureError('INFOTABLE_UNAVAILABLE') from None
    quarter = filing['reportDate']
    bound = (cover['cik'] == cik and cover['period'] == quarter and cover['calendar_quarter'] == quarter
             and cover['submission_type'] == filing['form'] == '13F-HR' and cover['is_amendment'] is False
             and cover['amendment_type'] is None)
    metadata = {
        'manager_cik': cik, 'accession': filing['accessionNumber'], 'quarter_end': quarter.isoformat(),
        'filing_date': filing['filingDate'].isoformat(), 'acquired_at': acquired.astimezone(timezone.utc).isoformat(),
        'value_basis': 'USD_DOLLARS' if filing['filingDate'] >= DOLLAR_VALUES_FROM else 'USD_THOUSANDS',
        'report_type': cover['report_type'], 'amendment_type': cover['amendment_type'],
        'confidential_omitted': cover['confidential_omitted'], 'entry_total': cover['entry_total'],
        'value_total': cover['value_total'], 'complete': True, 'lineage_resolved': bool(filing['lineage_resolved']),
        'cover_binding_confirmed': bound, 'other_manager_ciks': dict(cover['other_manager_ciks']),
    }
    return table, metadata


def comparison_reasons(previous: tuple[bytes, dict], current: tuple[bytes, dict], *, as_of: datetime) -> list[str]:
    """Diagnostic reason codes of the same eligibility rules the public generator applies."""
    results = []
    for body, metadata in (previous, current):
        md = dict(metadata)
        for key in ('quarter_end', 'filing_date'):
            md[key] = date.fromisoformat(md[key])
        md['acquired_at'] = datetime.fromisoformat(md['acquired_at'])
        result = parse_information_table(body, FilingMetadata(**md), selected_manager_ciks=(md['manager_cik'],), as_of=as_of)
        results.append(result)
    reasons = [reason for result in results for reason in result.reasons]
    comparison = compare_quarters(*results)
    reasons.extend(comparison.reasons)
    return list(dict.fromkeys(reasons))[:16]


def collect_managers(config: dict, fetch: Callable[[str], tuple[bytes, datetime]], *, now: Callable[[], datetime]):
    """Verify every configured manager, then capture the latest two 13F-HR filings of verified ones.

    Returns (records, captures, mismatched_names). mismatched_names holds the SEC
    entity name observed for NAME_MISMATCH managers so the operator can correct
    the config; it is a diagnostic only and never enters the public output.
    """
    records, captures, mismatched = [], [], {}
    for manager in config['managers']:
        body = acquired = None
        if manager['candidate_cik'] is not None:
            try:
                body, acquired = fetch(SUBMISSIONS_URL.format(cik=manager['candidate_cik']))
            except SecCollectionError:
                body = acquired = None
        record, rows = verify_manager(manager, body, acquired, as_of=now())
        if record['reason_code'] == 'NAME_MISMATCH':
            try:
                name = _json(body)['name']
                mismatched[manager['id']] = ' '.join(name.split())[:150] if isinstance(name, str) else None
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                mismatched[manager['id']] = None
        if record['state'] == 'VERIFIED':
            quarters = select_quarters(rows)
            if len(quarters) < 2:
                record['capture_reason'] = 'INSUFFICIENT_13F_HISTORY'
            else:
                try:
                    current = capture_filing(fetch, record['cik'], quarters[0])
                    previous = capture_filing(fetch, record['cik'], quarters[1])
                    # One acquisition bound per pair: both tables were held by then.
                    previous[1]['acquired_at'] = current[1]['acquired_at'] = max(previous[1]['acquired_at'], current[1]['acquired_at'])
                    captures.append({'id': manager['id'], 'previous': previous, 'current': current})
                except CaptureError as error:
                    record['capture_reason'] = error.args[0]
        records.append(record)
    return records, captures, mismatched
