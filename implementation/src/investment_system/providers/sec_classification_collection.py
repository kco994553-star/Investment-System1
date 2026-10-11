"""Live SEC collection for SIC/theme v0 (runs in GitHub Actions only; sec.gov is not reachable elsewhere).

Fixed URL shapes only, same serial pacing/retry budget as SecCollectionClient. Importing performs no
request or environment lookup. Every per-item failure becomes a fixed reason code and a NOT_AVAILABLE
input; nothing is guessed. Bodies stay in RAM: the caller receives identifier sets, SIC strings, Item 1
text for keyword counting and SHA-256 digests, never ETF weights, values or quantities.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from .sec_collection import (MAX_ATTEMPTS, MAX_BODY_BYTES, REQUEST_TIMEOUT, RETRY_STATUSES, SecCollectionClient,
                             SecCollectionError, SecResponse, _RejectRedirects, _validate_body)
from . import sec_classification_inputs as parse

URLS = {
    'MF_TICKERS': 'https://www.sec.gov/files/company_tickers_mf.json',
    'SUBMISSIONS': 'https://data.sec.gov/submissions/CIK{cik}.json',
    'SERIES_FILINGS': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={series}&type=NPORT-P&dateb=&owner=include&count=10&output=atom',
    'NPORT': 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/primary_doc.xml',
    'TEN_K': 'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}',
}
PATTERNS = {
    'MF_TICKERS': r'https://www\.sec\.gov/files/company_tickers_mf\.json',
    'SUBMISSIONS': r'https://data\.sec\.gov/submissions/CIK[0-9]{10}\.json',
    'SERIES_FILINGS': r'https://www\.sec\.gov/cgi-bin/browse-edgar\?action=getcompany&CIK=S[0-9]{9}&type=NPORT-P&dateb=&owner=include&count=10&output=atom',
    'NPORT': r'https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/primary_doc\.xml',
    'TEN_K': r'https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.html?',
}
ACCEPT = {'MF_TICKERS': 'application/json', 'SUBMISSIONS': 'application/json', 'SERIES_FILINGS': 'application/atom+xml',
          'NPORT': 'application/xml', 'TEN_K': 'text/html'}
MAX_NPORT_TRIES = 3


def _require(kind, url):
    if kind not in PATTERNS or not isinstance(url, str) or re.fullmatch(PATTERNS[kind], url) is None:
        raise SecCollectionError('SEC_URL_NOT_ALLOWED') from None


def classification_transport(url, *, headers: Mapping[str, str], timeout: float, max_body_bytes: int) -> SecResponse:
    """Bounded, redirect-free GET restricted to the fixed classification URL shapes."""
    if not any(re.fullmatch(p, url) for p in PATTERNS.values()):
        raise SecCollectionError('SEC_URL_NOT_ALLOWED') from None
    if (type(max_body_bytes) is not int or not 0 < max_body_bytes <= MAX_BODY_BYTES
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


class ClassificationSecClient(SecCollectionClient):
    """Shares the inherited 0.2 s serial pacer and Retry-After budget; different URL allowlist."""

    def __init__(self, user_agent, *, transport: Callable = classification_transport, **kwargs):
        super().__init__(user_agent, transport=transport, **kwargs)

    def fetch(self, kind, url, *, expected_cik=None):
        _require(kind, url)
        with self._lock:
            for attempt in range(MAX_ATTEMPTS):
                self._pace()
                try:
                    response = self._transport(url, headers={'User-Agent': self._user_agent, 'Accept': ACCEPT[kind]},
                                               timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_BODY_BYTES)
                except SecCollectionError as error:
                    code = error.args[0] if len(error.args) == 1 else None
                    allowed = {'SEC_URL_NOT_ALLOWED', 'SEC_CONFIG_INVALID', 'SEC_REDIRECT_REJECTED', 'SEC_RESPONSE_TOO_LARGE'}
                    raise SecCollectionError(code if code in allowed else 'SEC_TRANSPORT_FAILED') from None
                except HTTPError as error:
                    response = SecResponse(error.code, b'', error.headers.get('Retry-After') if error.headers else None, error.geturl())
                except (URLError, OSError):
                    if attempt == MAX_ATTEMPTS - 1:
                        raise SecCollectionError('SEC_TRANSPORT_RETRIES_EXHAUSTED') from None
                    self._pause(2.0 ** (attempt + 1))
                    continue
                except Exception:
                    raise SecCollectionError('SEC_TRANSPORT_FAILED') from None
                if (not isinstance(response, SecResponse) or type(response.status) is not int
                        or not 100 <= response.status <= 599 or not isinstance(response.body, bytes)):
                    raise SecCollectionError('SEC_RESPONSE_INVALID') from None
                if response.final_url != url:
                    raise SecCollectionError('SEC_RESPONSE_URL_MISMATCH') from None
                if len(response.body) > MAX_BODY_BYTES:
                    raise SecCollectionError('SEC_RESPONSE_TOO_LARGE') from None
                if response.status == 200:
                    if kind == 'SUBMISSIONS':
                        _validate_body(response.body, expected_cik)
                    return response.body, self._utc()
                if response.status not in RETRY_STATUSES:
                    raise SecCollectionError(f'SEC_HTTP_{response.status}') from None
                if attempt == MAX_ATTEMPTS - 1:
                    raise SecCollectionError('SEC_HTTP_RETRIES_EXHAUSTED') from None
                self._pause(self._retry_wait(response.retry_after, 2.0 ** (attempt + 1)))
        raise SecCollectionError('SEC_TRANSPORT_FAILED') from None


def _code(error):
    code = error.args[0] if isinstance(error, (SecCollectionError, parse.EvidenceError)) and error.args else None
    return code if isinstance(code, str) and re.fullmatch(r'[A-Z0-9_]{1,64}', code) else 'COLLECTION_FAILED'


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def collect_etf_inputs(client, tickers):
    """{ticker: {'state','reason_code','securities','report_date','sha256','acquired_at'}} for every basket ETF."""
    out = {t: {'state': 'NOT_AVAILABLE', 'reason_code': 'SOURCE_NOT_AVAILABLE', 'securities': None,
               'report_date': None, 'sha256': None, 'acquired_at': None} for t in tickers}
    mf = None
    try:
        body, mf_at = client.fetch('MF_TICKERS', URLS['MF_TICKERS'])
        bindings = parse.bind_etf_series(body, tickers)
        mf = {'sha256': _sha(body), 'acquired_at': mf_at}
    except Exception:
        for t in tickers:
            out[t]['reason_code'] = 'ETF_SERIES_BINDING_NOT_AVAILABLE'
        return out, mf
    for ticker in tickers:
        bound = bindings.get(ticker)
        if bound is None:
            out[ticker]['reason_code'] = 'ETF_SERIES_UNBOUND'
            continue
        try:
            body, _ = client.fetch('SERIES_FILINGS', URLS['SERIES_FILINGS'].format(series=bound['series_id']))
            filings = parse.series_filings(body)
        except Exception:
            out[ticker]['reason_code'] = 'NPORT_FILING_LIST_NOT_AVAILABLE'
            continue
        if not filings:
            out[ticker]['reason_code'] = 'NPORT_NOT_FOUND'
            continue
        reason = 'NPORT_INVALID'
        for filing in filings[:MAX_NPORT_TRIES]:
            url = URLS['NPORT'].format(cik=int(bound['cik']), accession=filing['accession'].replace('-', ''))
            try:
                body, acquired = client.fetch('NPORT', url)
                report = parse.nport_securities(body, bound['series_id'])
            except Exception as error:
                reason = 'NPORT_SERIES_MISMATCH' if _code(error) == 'NPORT_SERIES_MISMATCH' else 'NPORT_INVALID'
                continue
            out[ticker] = {'state': 'AVAILABLE', 'reason_code': None, 'securities': report['securities'],
                           'report_date': report['report_date'], 'sha256': _sha(body), 'acquired_at': acquired}
            break
        else:
            out[ticker]['reason_code'] = reason
    return out, mf


def collect_company_inputs(client, ciks):
    """{company_id: {'submissions': {...}|None, 'ten_k': {...}}} for SEC registrants (company_id -> CIK10)."""
    out = {}
    for cid, cik in ciks.items():
        row = {'submissions': None, 'ten_k': {'state': 'NOT_AVAILABLE', 'reason_code': 'SOURCE_NOT_AVAILABLE'}}
        out[cid] = row
        try:
            body, acquired = client.fetch('SUBMISSIONS', URLS['SUBMISSIONS'].format(cik=cik), expected_cik=cik)
            profile = parse.submissions_profile(body, cik)
        except Exception:
            continue
        row['submissions'] = {'sic': profile['sic'], 'sha256': _sha(body), 'acquired_at': acquired}
        latest = profile['latest_10k']
        if latest is None:
            row['ten_k'] = {'state': 'TEN_K_NOT_FILED', 'reason_code': 'TEN_K_NOT_FILED'}
            continue
        url = URLS['TEN_K'].format(cik=int(cik), accession=latest['accession'].replace('-', ''), document=latest['primary_document'])
        try:
            body, acquired = client.fetch('TEN_K', url)
            text = parse.extract_item1(body)
        except Exception:
            continue
        if text is None:
            row['ten_k'] = {'state': 'NOT_AVAILABLE', 'reason_code': 'ITEM1_NOT_FOUND'}
            continue
        row['ten_k'] = {'state': 'AVAILABLE', 'reason_code': None, 'item1_text': text, 'report_date': latest['report_date'],
                        'filing_date': latest['filing_date'], 'sha256': _sha(body), 'acquired_at': acquired}
    return out
