"""Shared offline Alpaca parsing/normalization extracted from #461 (6d6fd7fa).
No network, credentials, storage or price acquisition. Bare-directory provenance stays unrecorded.
"""
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
NY = ZoneInfo('America/New_York')
_SYMBOL = re.compile(r'[A-Z]{1,5}(?:\.[A-Z])?')
_PAGE_TOKEN = re.compile(r'[A-Za-z0-9+/=_-]{1,1024}')

def _parsed_page(body, symbol, *, mapped=False, start=date(2016, 1, 1), end=date(2019, 3, 31), exact=False):
    """Validated [(New York day, original bar)], next page token, returned symbol.
    Exact decimal decoding is available to offline normalization; raises ValueError(<fixed code>)."""
    try:
        data = json.loads(body, parse_float=Decimal, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON'))) if exact else json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('JSON') from None
    if not isinstance(data, dict):
        raise ValueError('SCHEMA')
    echo = data.get('symbol')
    if not isinstance(echo, str) or (symbol is not None and not _SYMBOL.fullmatch(echo)) or (echo != symbol and not mapped):
        raise ValueError('SYMBOL_MISMATCH')
    bars = data.get('bars')
    if bars is None:
        bars = []                       # Alpaca answers bars:null for an authenticated window without data
    if not isinstance(bars, list):
        raise ValueError('SCHEMA')
    token = data.get('next_page_token')
    if token is not None and (not isinstance(token, str) or not _PAGE_TOKEN.fullmatch(token)):
        raise ValueError('PAGE_TOKEN')
    rows = []
    for bar in bars:
        if not isinstance(bar, dict) or not isinstance(bar.get('t'), str):
            raise ValueError('BAR_SCHEMA')
        try:
            at = datetime.fromisoformat(bar['t'].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('BAR_TIME') from None
        if at.tzinfo is None:
            raise ValueError('BAR_TIME')
        day = at.astimezone(NY).date()
        if not start <= day <= end:
            raise ValueError('OUT_OF_WINDOW')
        rows.append((day, bar))
    return rows, token, echo


def _normal_number(value, *, positive=False, integral=False):
    """Exact numeric source -> JSON-safe number text, or null with a reason."""
    if value is None:
        return None, 'MISSING'
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None, 'INVALID_NUMBER'
    n = Decimal(value)
    if not n.is_finite() or (n <= 0 if positive else n < 0) or (integral and n != n.to_integral_value()):
        return None, 'INVALID_NUMBER'
    return (int(n) if integral else str(n)), None


def normalize_pages(pages, *, request):
    return _normalize_pages(pages, request=request, unrecorded=False)


def normalize_unrecorded_pages(pages):
    """Legacy bare directory: source request/receipt are unknown, never inferred from bar timestamps."""
    return _normalize_pages(pages, request=None, unrecorded=True)


def _normalize_pages(pages, *, request, unrecorded):
    """Offline normalization of retained SIP raw daily pages; no I/O, HTTP or execution approval.

    pages: [{body: original bytes, sha256: recorded digest, request_page_token: token or None,
             acquired_at: timezone-aware receipt timestamp}]. Never infer receipt/publication from a bar timestamp.
    request: {symbol, asof, feed, adjustment, timeframe, start, end}. An unrecorded historical asof may be None;
    that is NOT asof='-' and proves no security identity. Different periods are allowed offline only; the collector's
    fixed URL allow-list is unchanged. The returned candidates are NOT engine-ready prices: identity, currency,
    session-open suitability and input rights require separate evidence before Main's adapter may connect them.
    Hash, page order and request-token chain are checked; partial pages never become a complete response.
    """
    if unrecorded:
        symbol, asof, start, end = None, None, date.min, date.max
    else:
        if not isinstance(request, dict) or any(request.get(k) != v for k, v in
                (('feed', 'sip'), ('adjustment', 'raw'), ('timeframe', '1Day'))):
            raise ValueError('REQUEST_BASIS')
        symbol, asof = request.get('symbol'), request.get('asof')
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol) or 'asof' not in request:
            raise ValueError('REQUEST_BASIS')
        try:
            def request_day(value):
                at = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return at.astimezone(NY).date() if at.tzinfo else date.fromisoformat(value)
            start, end = request_day(request['start']), request_day(request['end'])
            if start > end or (asof not in (None, '-') and date.fromisoformat(asof).isoformat() != asof):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError('REQUEST_BASIS') from None
    rows, source_pages, expected_token, seen, last = [], [], None, set(), None
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict) or not isinstance(page.get('body'), bytes):
            raise ValueError('RAW_PAGE')
        body, digest = page['body'], page.get('sha256')
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError('RAW_HASH_MISMATCH')
        if not unrecorded and ('request_page_token' not in page or page['request_page_token'] != expected_token or (page_index and expected_token is None)):
            raise ValueError('PAGE_CHAIN')
        if page_index and expected_token is None:
            raise ValueError('PAGE_CHAIN')
        acquired = page.get('acquired_at')
        if not unrecorded:
            try:
                at = datetime.fromisoformat(acquired.replace('Z', '+00:00'))
                if at.tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise ValueError('ACQUIRED_AT') from None
        parsed, token, echo = _parsed_page(body, symbol, mapped=asof != '-', start=start, end=end, exact=True)
        if token and (token in seen or not parsed):
            raise ValueError('PAGE_CHAIN')
        if token:
            seen.add(token)
        source_pages.append(dict(sha256=digest, bytes=len(body), request_page_token=expected_token,
                                 next_page_token=token, acquired_at=acquired, returned_symbol=echo))
        expected_token = token
        for source_row, (day, bar) in enumerate(parsed):
            if last is not None and day <= last:
                raise ValueError('ORDER')
            last = day
            normalized, missing, quality = {}, {}, []
            for source, field in (('o','open'),('h','high'),('l','low'),('c','close'),
                                  ('v','volume'),('n','trade_count'),('vw','vwap')):
                value, reason = _normal_number(bar.get(source), positive=source in ('o','h','l','c','vw'), integral=source=='n')
                normalized[field] = value
                if reason:
                    missing[field] = reason
                    if source in ('o','h','l','c','v'):
                        quality.append(field.upper()+'_'+reason)
            if all(normalized[k] is not None for k in ('open','high','low','close')):
                o,h,l,c = (Decimal(normalized[k]) for k in ('open','high','low','close'))
                if not l <= min(o,c) <= max(o,c) <= h:
                    quality.append('OHLC_INCONSISTENT')
            rows.append(dict(date=day.isoformat(), source_timestamp=bar['t'], time_zone='America/New_York',
                             requested_symbol=symbol, returned_symbol=echo, asof=asof, security_id=None, currency=None,
                             price_basis='RAW', acquired_at=acquired, available_at=None, published_at=None,
                             source_page=page_index, source_row=source_row, source_sha256=digest,
                             null_reasons=missing, quality_reasons=quality, **normalized))
    complete = bool(source_pages) and expected_token is None
    status = ('NOT_COLLECTED' if not source_pages else 'INCOMPLETE' if not complete else
              'EMPTY_RESPONSE' if not rows else 'QUALITY_FAILED' if any(r['quality_reasons'] for r in rows) else 'FETCHED')
    return dict(schema='alpaca-normalized-candidates/1', request=None if unrecorded else dict(request), source_pages=source_pages,
                status=status, pages_complete=complete, rows=rows, identity_status='UNVERIFIED',
                listing_status='UNKNOWN', execution_open_status='UNVERIFIED_SESSION_OPEN',
                corporate_actions_status='NOT_IN_BARS', pit_status='NOT_VERIFIED', rights_status='NOT_EVALUATED')

