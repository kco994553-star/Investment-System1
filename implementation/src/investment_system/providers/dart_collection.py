"""Bounded OpenDART (금융감독원 전자공시) collection for the Korean TARGET (한미반도체, KRX 042700).

Importing this module performs no request and reads no environment. The caller
passes the API key value read from the env slot ``DART_API_KEY``. The key is
sent only as the ``crtfc_key`` query parameter OpenDART requires; request URLs
are built inside the client and are never returned, printed or put into an
exception. Every failure is a fixed, value-free ``DartCollectionError`` code.

Every request spends one unit of a per-run ``CallBudget`` *before* it is sent.
The hard ceiling is ``HARD_MAX_CALLS`` (50) per run, far below OpenDART's
documented personal limit of 20,000 calls/day; when the budget is spent the
client refuses further calls (fail closed) with ``DART_CALL_BUDGET_EXCEEDED``.

Endpoints (https://opendart.fss.or.kr/api/):
- ``corpCode.xml``: zip of CORPCODE.xml; the corp_code of stock 042700 is taken
  only from this official file (exactly one listed row with the expected name),
  otherwise ``CORP_CODE_UNCONFIRMED``. No corp_code is pinned or guessed.
- ``list.json``: disclosure list (title, receipt number, date). Body text is
  never requested.
- ``fnlttSinglAcntAll.json``: single-company full financial statements of a
  periodic report (CFS preferred, OFS fallback labelled).
- ``stockTotqySttus.json``: share totals of the same periodic report.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import io
import json
import math
import re
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

DART_API_KEY_SLOT = 'DART_API_KEY'
KEY_PARAMETER = 'crtfc_key'  # OpenDART's documented authentication parameter name.
BASE_URL = 'https://opendart.fss.or.kr/api/'
ENDPOINTS = frozenset({'corpCode.xml', 'list.json', 'fnlttSinglAcntAll.json', 'stockTotqySttus.json'})
HARD_MAX_CALLS = 50
DEFAULT_MAX_CALLS = 30
DOCUMENTED_DAILY_LIMIT = 20_000
REQUEST_TIMEOUT = 30.0
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ZIP_BYTES = 32 * 1024 * 1024
MAX_XML_BYTES = 256 * 1024 * 1024
LIST_PAGE_COUNT = 100
MAX_LIST_PAGES = 3
KST = timezone(timedelta(hours=9))

# Korean TARGET. corp_code is resolved from corpCode.xml on every run; nothing is pinned.
KR_TARGETS = {'hanmi': {'stock_code': '042700', 'corp_name': '한미반도체'}}

# OpenDART status -> fixed reason code.
STATUS_REASONS = {
    '010': 'DART_KEY_NOT_REGISTERED', '011': 'DART_KEY_DISABLED', '012': 'DART_IP_NOT_ALLOWED',
    '013': 'DART_NO_DATA', '014': 'DART_FILE_NOT_FOUND', '020': 'DART_LIMIT_EXCEEDED',
    '021': 'DART_COMPANY_LIMIT_EXCEEDED', '100': 'DART_INVALID_FIELD', '101': 'DART_INVALID_ACCESS',
    '800': 'DART_MAINTENANCE', '900': 'DART_UNDEFINED_ERROR', '901': 'DART_KEY_EXPIRED',
}
# After these no further request is sent in the run.
FATAL_CODES = frozenset({
    'DART_KEY_NOT_REGISTERED', 'DART_KEY_DISABLED', 'DART_IP_NOT_ALLOWED', 'DART_LIMIT_EXCEEDED',
    'DART_INVALID_ACCESS', 'DART_MAINTENANCE', 'DART_KEY_EXPIRED', 'DART_CALL_BUDGET_EXCEEDED',
    'DART_TRANSPORT_FAILED', 'DART_REDIRECT_REJECTED', 'DART_API_KEY_MISSING', 'DART_API_KEY_INVALID_FORMAT',
    'CORP_CODE_UNCONFIRMED', 'DART_UNKNOWN_STATUS', 'DART_UNDEFINED_ERROR',
})
ERROR_CODES = frozenset(STATUS_REASONS.values()) | FATAL_CODES | {
    'DART_HTTP_ERROR', 'DART_RESPONSE_TOO_LARGE', 'DART_JSON_INVALID', 'DART_ZIP_INVALID', 'DART_CONFIG_INVALID',
    'DART_IDENTITY_MISMATCH', 'DART_LIST_INVALID', 'DART_LIST_TRUNCATED', 'DART_FINANCIALS_INVALID',
}

REPORT_CODES = {'11011': 'ANNUAL', '11012': 'HALF', '11013': 'Q1', '11014': 'Q3'}
_REPORT_NAMES = {'사업보고서': 'ANNUAL', '반기보고서': 'HALF', '분기보고서': 'QUARTER'}


class DartCollectionError(Exception):
    """A fixed, printable code. Never carries a URL, key, body or upstream message."""

    def __init__(self, code):
        code = code if code in ERROR_CODES else 'DART_CONFIG_INVALID'
        super().__init__(code)
        self.code = code

    def __str__(self):
        return self.code

    @property
    def fatal(self):
        return self.code in FATAL_CODES


def mask_secret(text, secret):
    """Replace every occurrence of the secret value; used on anything that might be printed."""
    text = str(text)
    if isinstance(secret, str) and secret:
        text = text.replace(secret, '***')
    return text


def valid_key_format(key):
    return isinstance(key, str) and re.fullmatch(r'[0-9A-Za-z]{40}', key) is not None


class CallBudget:
    """Per-run call counter. ``spend`` is called before a request is sent and fails closed."""

    def __init__(self, limit=DEFAULT_MAX_CALLS):
        if type(limit) is not int or not 1 <= limit <= HARD_MAX_CALLS:
            raise DartCollectionError('DART_CONFIG_INVALID')
        self.limit = limit
        self.used = 0

    def spend(self):
        if self.used >= self.limit:
            raise DartCollectionError('DART_CALL_BUDGET_EXCEEDED')
        self.used += 1


@dataclass(frozen=True)
class DartResponse:
    status: int
    body: bytes


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect would re-send the key to another location.
        raise DartCollectionError('DART_REDIRECT_REJECTED')


def default_transport(url, *, timeout, max_bytes):
    """HTTPS GET without redirects and with a bounded read. HTTP error bodies are not read."""
    request = Request(url, headers={'Accept': '*/*'})
    try:
        with build_opener(_RejectRedirects()).open(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            return DartResponse(response.status, body)
    except HTTPError as error:
        status = error.code
        error.close()
        return DartResponse(status, b'')


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate')
        out[key] = value
    return out


def _reject_constant(_):
    raise ValueError('constant')


def parse_json(body):
    try:
        payload = json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=_unique, parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise DartCollectionError('DART_JSON_INVALID') from None
    if not isinstance(payload, dict):
        raise DartCollectionError('DART_JSON_INVALID')
    return payload


def status_code(payload):
    """'000' ok; anything else -> fixed reason code (never the upstream message)."""
    status = payload.get('status')
    if status == '000':
        return None
    if isinstance(status, str) and status in STATUS_REASONS:
        return STATUS_REASONS[status]
    return 'DART_UNKNOWN_STATUS'


class DartClient:
    """Sends fixed OpenDART requests with the key as ``crtfc_key`` only. Never exposes URLs."""

    __slots__ = ('_key', '_transport', 'budget')

    def __init__(self, key, *, budget, transport=None):
        if not isinstance(key, str) or not key.strip():
            raise DartCollectionError('DART_API_KEY_MISSING')
        if not valid_key_format(key):
            raise DartCollectionError('DART_API_KEY_INVALID_FORMAT')
        if not isinstance(budget, CallBudget):
            raise DartCollectionError('DART_CONFIG_INVALID')
        self._key = key
        self._transport = transport or default_transport
        self.budget = budget

    def __repr__(self):
        return f'DartClient(key=***, calls={self.budget.used}/{self.budget.limit})'

    __str__ = __repr__

    def _get(self, endpoint, params, max_bytes):
        if endpoint not in ENDPOINTS or not isinstance(params, dict):
            raise DartCollectionError('DART_CONFIG_INVALID')
        for name, value in params.items():
            if name == KEY_PARAMETER or not isinstance(value, str) or not re.fullmatch(r'[0-9A-Za-z_]{1,32}', value):
                raise DartCollectionError('DART_CONFIG_INVALID')
        self.budget.spend()
        url = BASE_URL + endpoint + '?' + urlencode({KEY_PARAMETER: self._key, **params})
        failed, response = None, None
        try:
            response = self._transport(url, timeout=REQUEST_TIMEOUT, max_bytes=max_bytes)
        except DartCollectionError as error:
            failed = error.code if error.code == 'DART_REDIRECT_REJECTED' else 'DART_TRANSPORT_FAILED'
        except Exception:  # noqa: BLE001 - upstream text may contain the URL; replace it entirely.
            failed = 'DART_TRANSPORT_FAILED'
        del url
        if failed is not None:
            # Raised outside the handler: no __context__ chain that could carry the URL.
            raise DartCollectionError(failed)
        if not isinstance(response, DartResponse) or type(response.status) is not int or type(response.body) is not bytes:
            raise DartCollectionError('DART_TRANSPORT_FAILED')
        if response.status != 200:
            raise DartCollectionError('DART_HTTP_ERROR')
        if len(response.body) > max_bytes:
            raise DartCollectionError('DART_RESPONSE_TOO_LARGE')
        return response.body

    def json(self, endpoint, params):
        """Parsed payload with status 000, or ``None`` for 013 (no data). Other statuses raise."""
        payload = parse_json(self._get(endpoint, params, MAX_JSON_BYTES))
        code = status_code(payload)
        if code == 'DART_NO_DATA':
            return None
        if code is not None:
            raise DartCollectionError(code)
        return payload

    def corp_code_zip(self):
        body = self._get('corpCode.xml', {}, MAX_ZIP_BYTES)
        if not body.startswith(b'PK\x03\x04'):
            # Errors come back as a small JSON/XML status document instead of a zip.
            match = re.search(rb'<status>\s*(\d{3})\s*</status>|"status"\s*:\s*"(\d{3})"', body[:4096])
            status = (match.group(1) or match.group(2)).decode() if match else None
            raise DartCollectionError(STATUS_REASONS.get(status, 'DART_ZIP_INVALID'))
        return body


# ---------------------------------------------------------------- corp_code


class _BoundedReader(io.RawIOBase):
    def __init__(self, handle, limit):
        self._handle, self._left = handle, limit

    def readable(self):
        return True

    def readinto(self, buffer):
        if self._left <= 0:
            raise DartCollectionError('DART_ZIP_INVALID')
        data = self._handle.read(min(len(buffer), self._left))
        self._left -= len(data)
        buffer[:len(data)] = data
        return len(data)


def resolve_corp_code(zip_body, *, stock_code, corp_name):
    """corp_code of exactly one CORPCODE.xml row with this stock code and name, else CORP_CODE_UNCONFIRMED."""
    import xml.etree.ElementTree as ET
    if type(zip_body) is not bytes or len(zip_body) > MAX_ZIP_BYTES:
        raise DartCollectionError('DART_ZIP_INVALID')
    if not re.fullmatch(r'\d{6}', stock_code or '') or not isinstance(corp_name, str) or not corp_name:
        raise DartCollectionError('DART_CONFIG_INVALID')
    try:
        with zipfile.ZipFile(io.BytesIO(zip_body)) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if len(members) != 1 or members[0].filename.upper() != 'CORPCODE.XML' or members[0].file_size > MAX_XML_BYTES:
                raise DartCollectionError('DART_ZIP_INVALID')
            with archive.open(members[0]) as raw:
                stream = io.BufferedReader(_BoundedReader(raw, MAX_XML_BYTES))
                head = stream.peek(4096)[:4096]
                if b'<!DOCTYPE' in head.upper() or b'<!ENTITY' in head.upper():
                    raise DartCollectionError('DART_ZIP_INVALID')
                matches, rows = [], 0
                for _, element in ET.iterparse(stream, events=('end',)):
                    if element.tag != 'list':
                        continue
                    rows += 1
                    fields = {child.tag: (child.text or '').strip() for child in element}
                    if fields.get('stock_code') == stock_code:
                        matches.append((fields.get('corp_code', ''), fields.get('corp_name', '')))
                    element.clear()
    except DartCollectionError:
        raise
    except (zipfile.BadZipFile, ET.ParseError, OSError, ValueError, EOFError, RuntimeError, UnicodeError):
        raise DartCollectionError('DART_ZIP_INVALID') from None
    if rows == 0:
        raise DartCollectionError('DART_ZIP_INVALID')
    if len(matches) != 1 or matches[0][1] != corp_name or not re.fullmatch(r'\d{8}', matches[0][0]):
        raise DartCollectionError('CORP_CODE_UNCONFIRMED')
    return matches[0][0]


# ---------------------------------------------------------------- disclosures

LIST_ROW_KEYS = ('corp_code', 'stock_code', 'report_nm', 'rcept_no', 'rcept_dt')


def _ymd(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{8}', value):
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def clean_title(value):
    """Report name only (never body text): trimmed, single-spaced, bounded, no markup/control characters."""
    if not isinstance(value, str):
        return None
    title = re.sub(r'\s+', ' ', value).strip()
    if not 0 < len(title) <= 200 or any(ord(ch) < 32 or ch in '<>' for ch in title):
        return None
    return title


def list_disclosures(client, corp_code, *, stock_code, begin, end, pblntf_ty=None, last_report_only=False):
    """Rows (dicts with LIST_ROW_KEYS) for one company. Returns (rows, truncated)."""
    params = {'corp_code': corp_code, 'bgn_de': begin.strftime('%Y%m%d'), 'end_de': end.strftime('%Y%m%d'),
              'last_reprt_at': 'Y' if last_report_only else 'N', 'page_count': str(LIST_PAGE_COUNT)}
    if pblntf_ty is not None:
        if pblntf_ty not in tuple('ABCDEFGHIJ'):
            raise DartCollectionError('DART_CONFIG_INVALID')
        params['pblntf_ty'] = pblntf_ty
    rows, page, total_pages = [], 1, 1
    while page <= min(total_pages, MAX_LIST_PAGES):
        payload = client.json('list.json', {**params, 'page_no': str(page)})
        if payload is None:
            return rows, False
        items, total_pages = payload.get('list'), payload.get('total_page')
        if isinstance(total_pages, str) and re.fullmatch(r'[0-9]{1,5}', total_pages):
            total_pages = int(total_pages)
        if not isinstance(items, list) or type(total_pages) is not int or not 0 <= total_pages <= 10_000 or len(items) > LIST_PAGE_COUNT:
            raise DartCollectionError('DART_LIST_INVALID')
        for item in items:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in LIST_ROW_KEYS):
                raise DartCollectionError('DART_LIST_INVALID')
            # Every row must belong to the resolved company (identity cross-check).
            if item['corp_code'] != corp_code or item['stock_code'].strip() != stock_code:
                raise DartCollectionError('DART_IDENTITY_MISMATCH')
            rows.append({k: item[k] for k in LIST_ROW_KEYS})
        page += 1
    return rows, total_pages > MAX_LIST_PAGES


def periodic_report(report_nm):
    """('ANNUAL'|'HALF'|'Q1'|'Q3', bsns_year, reprt_code) from a periodic report name, else None.

    December fiscal year only (한미반도체): 사업보고서 (YYYY.12), 반기보고서 (YYYY.06),
    분기보고서 (YYYY.03 -> Q1, YYYY.09 -> Q3). Leading bracket tags such as [기재정정] are ignored.
    """
    title = clean_title(report_nm)
    if title is None:
        return None
    match = re.fullmatch(r'(?:\[[^\]]{1,20}\]\s*)*(사업보고서|반기보고서|분기보고서)\s*\((\d{4})\.(\d{2})\)', title)
    if not match:
        return None
    kind, year, month = _REPORT_NAMES[match.group(1)], match.group(2), match.group(3)
    code = {('ANNUAL', '12'): '11011', ('HALF', '06'): '11012', ('QUARTER', '03'): '11013', ('QUARTER', '09'): '11014'}.get((kind, month))
    if code is None:
        return None
    return REPORT_CODES[code], year, code


# ---------------------------------------------------------------- financial statements

# account_id (IFRS / DART standard taxonomy) -> normalized input. Ordered alternatives, first present wins;
# account names are never matched. Missing -> None (NOT_AVAILABLE), never 0.
INCOME_SJ = ('IS', 'CIS')
CONCEPTS = {
    'revenue': (INCOME_SJ, ('ifrs-full_Revenue',)),
    'operating_income': (INCOME_SJ, ('dart_OperatingIncomeLoss',)),
    'net_income': (INCOME_SJ, ('ifrs-full_ProfitLoss',)),
    'eps': (INCOME_SJ, ('ifrs-full_DilutedEarningsLossPerShare', 'ifrs-full_BasicEarningsLossPerShare')),
    'operating_cash_flow': (('CF',), ('ifrs-full_CashFlowsFromUsedInOperatingActivities',)),
    'capex': (('CF',), ('ifrs-full_PurchaseOfPropertyPlantAndEquipment',)),
    'cash_and_equivalents': (('BS',), ('ifrs-full_CashAndCashEquivalents',)),
    'equity': (('BS',), ('ifrs-full_EquityAttributableToOwnersOfParent', 'ifrs-full_Equity')),
    'total_debt': (('BS',), ('ifrs-full_LongtermBorrowings',)),
}
WITH_PREVIOUS = ('revenue', 'operating_income', 'eps')
FS_ROW_KEYS = ('sj_div', 'account_id', 'thstrm_amount', 'currency')


def parse_amount(value):
    """OpenDART amount string -> float; '', '-' or malformed -> None (never 0)."""
    if not isinstance(value, str):
        return None
    text = value.replace(',', '').strip()
    if not re.fullmatch(r'-?\d{1,18}(?:\.\d{1,6})?', text):
        return None
    number = float(text)
    return number if math.isfinite(number) else None


def _pick(rows, sj_divs, account_ids, field):
    for account in account_ids:
        matched = [parse_amount(r.get(field)) for r in rows if r['sj_div'] in sj_divs and r['account_id'] == account]
        if not matched:
            continue
        values = {v for v in matched if v is not None}
        if not values:
            return None, account, 'UNPARSEABLE'
        if len(values) != 1:
            return None, account, 'AMBIGUOUS'  # Same concept with different values: withheld.
        return values.pop(), account, None
    return None, None, 'MISSING'


def _interim_field(sj_divs, reprt_code):
    # Interim income statements: year-to-date column; Q1 has only the quarter (= YTD). Cash flow is YTD already.
    if 'CF' in sj_divs or 'BS' in sj_divs or reprt_code == '11011':
        return 'thstrm_amount'
    return 'thstrm_amount' if reprt_code == '11013' else 'thstrm_add_amount'


def extract_financials(payload, *, reprt_code):
    """Normalized inputs of one fnlttSinglAcntAll payload: ({name: value|None}, {name: concept|None}, missing_reasons)."""
    items = payload.get('list') if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items or len(items) > 5000:
        raise DartCollectionError('DART_FINANCIALS_INVALID')
    rows = []
    for item in items:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ('sj_div', 'account_id')):
            raise DartCollectionError('DART_FINANCIALS_INVALID')
        if item.get('reprt_code', reprt_code) != reprt_code:
            raise DartCollectionError('DART_IDENTITY_MISMATCH')
        rows.append(item)
    currencies = {r.get('currency') for r in rows if r['sj_div'] in ('BS', 'IS', 'CIS', 'CF')}
    if currencies != {'KRW'}:
        raise DartCollectionError('DART_FINANCIALS_INVALID')
    values, concepts, reasons = {}, {}, {}
    for name, (sj_divs, accounts) in CONCEPTS.items():
        field = _interim_field(sj_divs, reprt_code)
        values[name], concepts[name], reason = _pick(rows, sj_divs, accounts, field)
        if reason:
            reasons[name] = reason
        if name in WITH_PREVIOUS:
            prev_name = name + '_prev'
            if reprt_code == '11011':
                values[prev_name], _, reason = _pick(rows, sj_divs, (concepts[name],) if concepts[name] else accounts, 'frmtrm_amount')
                concepts[prev_name] = concepts[name] if values[prev_name] is not None else None
                if reason:
                    reasons[prev_name] = reason
            else:
                values[prev_name], concepts[prev_name] = None, None
                reasons[prev_name] = 'NOT_IN_INTERIM_SCOPE'
    return values, concepts, reasons


def extract_shares(payload):
    """Common shares outstanding (유통주식수, issued less treasury) of the 보통주 row, else None."""
    items = payload.get('list') if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    hits = [parse_amount(r.get('distb_stock_co')) for r in items if isinstance(r, dict) and isinstance(r.get('se'), str) and r['se'].strip() == '보통주']
    if len(hits) != 1 or hits[0] is None or hits[0] <= 0 or not float(hits[0]).is_integer():
        return None
    return int(hits[0])


def fetch_statements(client, corp_code, *, bsns_year, reprt_code):
    """(payload, 'CFS'|'OFS') — consolidated first, separate statements only when CFS has no data."""
    if reprt_code not in REPORT_CODES or not re.fullmatch(r'\d{4}', bsns_year):
        raise DartCollectionError('DART_CONFIG_INVALID')
    for fs_div in ('CFS', 'OFS'):
        payload = client.json('fnlttSinglAcntAll.json', {'corp_code': corp_code, 'bsns_year': bsns_year,
                                                          'reprt_code': reprt_code, 'fs_div': fs_div})
        if payload is not None:
            return payload, fs_div
    raise DartCollectionError('DART_NO_DATA')


def fetch_shares(client, corp_code, *, bsns_year, reprt_code):
    payload = client.json('stockTotqySttus.json', {'corp_code': corp_code, 'bsns_year': bsns_year, 'reprt_code': reprt_code})
    return None if payload is None else extract_shares(payload)


def canonical_body(payload):
    """Deterministic bytes of a parsed OpenDART payload (for the published source hash)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def kst_today(now):
    return now.astimezone(KST).date()


def utc_now():
    return datetime.now(timezone.utc)


TransportType = Callable[..., DartResponse]
