"""SEC 8-K current reports for the US TARGET companies (primary disclosure metadata only).

Importing this module performs no requests or environment lookup. Sources are the
submissions JSON (`filings.recent`: form, accessionNumber, filingDate, reportDate,
acceptanceDateTime, items) and the filing index page of each 8-K, read only to find
Exhibit 99.1 (its description/type row and document name). Exhibit and filing bodies
are never requested, parsed or stored. Nothing here scores, ranks or infers sentiment.

Concepts reused from PR #16 (SEC_PRIMARY_DISCLOSURE v1): 8-K and 8-K/A only, dashed
accession identity, exact same-accession dedup (identical rows fold, different rows
conflict), explicit CIK identity (no name/ticker matching), no body or summary text.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import math
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from ..markets.us import US_LISTINGS
from .sec_collection import (MAX_ATTEMPTS, REQUEST_TIMEOUT, RETRY_STATUSES, SecCollectionClient,
                             SecCollectionError, SecResponse, _RejectRedirects)
from .sec_submissions import URL as SUBMISSIONS_URL

FORMS = ('8-K', '8-K/A')
# Official Form 8-K item captions (SEC Form 8-K, General Instructions B / Items), English and Korean.
ITEMS = {
    '1.01': ('Entry into a Material Definitive Agreement', '중요한 확정 계약 체결'),
    '1.02': ('Termination of a Material Definitive Agreement', '중요한 확정 계약 종료'),
    '1.03': ('Bankruptcy or Receivership', '파산 또는 법정관리'),
    '1.04': ('Mine Safety - Reporting of Shutdowns and Patterns of Violations', '광산 안전 - 폐쇄 및 위반 패턴 보고'),
    '1.05': ('Material Cybersecurity Incidents', '중요한 사이버보안 사고'),
    '2.01': ('Completion of Acquisition or Disposition of Assets', '자산 인수·처분 완료'),
    '2.02': ('Results of Operations and Financial Condition', '영업 실적 및 재무 상태'),
    '2.03': ('Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant',
             '직접 금융 채무 또는 부외 약정상 채무의 발생'),
    '2.04': ('Triggering Events That Accelerate or Increase a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement',
             '직접 금융 채무·부외 약정상 채무의 가속·증가 사유 발생'),
    '2.05': ('Costs Associated with Exit or Disposal Activities', '사업 철수·처분 관련 비용'),
    '2.06': ('Material Impairments', '중요한 자산 손상'),
    '3.01': ('Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing',
             '상장폐지 통지 또는 상장 유지 요건 미충족, 상장 이전'),
    '3.02': ('Unregistered Sales of Equity Securities', '미등록 지분증권 매각'),
    '3.03': ('Material Modification to Rights of Security Holders', '증권 보유자 권리의 중요한 변경'),
    '4.01': ("Changes in Registrant's Certifying Accountant", '감사인 변경'),
    '4.02': ('Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review',
             '기존 재무제표·감사보고서·검토 결과에 대한 신뢰 불가'),
    '5.01': ('Changes in Control of Registrant', '지배권 변경'),
    '5.02': ('Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers',
             '이사·특정 임원의 퇴임, 이사 선임, 특정 임원 선임, 특정 임원 보상 약정'),
    '5.03': ('Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year', '정관·내규 변경, 회계연도 변경'),
    '5.04': ("Temporary Suspension of Trading Under Registrant's Employee Benefit Plans", '임직원 복리후생제도상 거래 일시 중지'),
    '5.05': ("Amendment to Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics", '윤리강령 개정 또는 적용 면제'),
    '5.06': ('Change in Shell Company Status', '셸 회사 지위 변경'),
    '5.07': ('Submission of Matters to a Vote of Security Holders', '주주 투표 안건 제출'),
    '5.08': ('Shareholder Director Nominations', '주주의 이사 후보 추천'),
    '6.01': ('ABS Informational and Computational Material', 'ABS 정보·산출 자료'),
    '6.02': ('Change of Servicer or Trustee', '서비서 또는 수탁자 변경'),
    '6.03': ('Change in Credit Enhancement or Other External Support', '신용 보강 또는 기타 외부 지원 변경'),
    '6.04': ('Failure to Make a Required Distribution', '필수 배분 미이행'),
    '6.05': ('Securities Act Updating Disclosure', '증권법상 갱신 공시'),
    '6.06': ('Static Pool', '정적 풀'),
    '6.10': ('Alternative Filings of Asset-Backed Issuers', '자산유동화 발행인의 대체 제출'),
    '7.01': ('Regulation FD Disclosure', '공정공시(Regulation FD)'),
    '8.01': ('Other Events', '기타 사건'),
    '9.01': ('Financial Statements and Exhibits', '재무제표 및 첨부서류'),
}
# Display grouping: the four highlighted kinds, everything else keeps its official item name.
CLASSIFICATION_PRIORITY = (('2.02', 'RESULTS'), ('5.02', 'OFFICERS_DIRECTORS'),
                           ('1.01', 'MATERIAL_AGREEMENT'), ('2.01', 'ACQUISITION_DISPOSITION'))
CLASSIFICATIONS = tuple(name for _, name in CLASSIFICATION_PRIORITY) + ('OTHER',)
EXHIBIT_TYPES = ('EX-99.1', 'EX-99.01')
INDEX_MAX_BYTES = 2 * 1024 * 1024
TITLE_MAX = 200
INDEX_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{accession}-index.htm'
ARCHIVE_URL = 'https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}'
URL_PATTERNS = (
    re.compile(r'https://data\.sec\.gov/submissions/CIK[0-9]{10}\.json'),
    re.compile(r'https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/[0-9]{10}-[0-9]{2}-[0-9]{6}-index\.htm'),
)
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_ITEM_CODE = re.compile(r'[1-9]\.[0-9]{2}')
_DOCUMENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:htm|html|txt|pdf|xml|jpg|gif)', re.I)
_ACCEPTANCE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})')


def classify(items):
    """Item codes -> one display classification (deterministic priority; mirrors sec-disclosures.js)."""
    for code, name in CLASSIFICATION_PRIORITY:
        if code in items:
            return name
    return 'OTHER'


def parse_items(value):
    """Submissions `items` string ("2.02,9.01") -> sorted official codes, unknown codes dropped and counted."""
    if value in (None, ''):
        return [], 0
    if not isinstance(value, str) or len(value) > 200:
        return [], 1
    codes, unknown = set(), 0
    for part in value.split(','):
        code = part.strip()
        if code in ITEMS:
            codes.add(code)
        elif code:
            unknown += 1
    return sorted(codes), unknown


def _require_url(url: str) -> None:
    if not isinstance(url, str) or not any(p.fullmatch(url) for p in URL_PATTERNS):
        raise SecCollectionError('SEC_URL_NOT_ALLOWED') from None


def default_transport(url: str, *, headers: Mapping[str, str], timeout: float, max_body_bytes: int) -> SecResponse:
    """Fixed submissions and 8-K filing-index routes only, no redirects, bounded body; error bodies are not read."""
    _require_url(url)
    if (type(max_body_bytes) is not int or not 0 < max_body_bytes <= 32 * 1024 * 1024
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


class SecDisclosureClient(SecCollectionClient):
    """Same User-Agent rule, 0.2 s pacing, retry budget and redirect refusal as the US17 collection client."""

    def __init__(self, user_agent: str, *, transport: Callable = default_transport, **kwargs) -> None:
        super().__init__(user_agent, transport=transport, **kwargs)

    def submissions(self, company_id: str) -> tuple[bytes, datetime]:
        if not isinstance(company_id, str) or company_id not in US_LISTINGS:
            raise SecCollectionError('SEC_ISSUER_NOT_ALLOWED') from None
        cik = US_LISTINGS[company_id]['cik']
        with self._lock:
            return self._request(SUBMISSIONS_URL.format(cik=cik), cik), self._utc()

    def filing_index(self, company_id: str, accession: str) -> bytes:
        if (not isinstance(company_id, str) or company_id not in US_LISTINGS
                or not isinstance(accession, str) or _ACCESSION.fullmatch(accession) is None):
            raise SecCollectionError('SEC_ISSUER_NOT_ALLOWED') from None
        url = index_url(company_id, accession)
        _require_url(url)
        with self._lock:
            for attempt in range(MAX_ATTEMPTS):
                self._pace()
                try:
                    response = self._transport(url, headers={'User-Agent': self._user_agent, 'Accept': 'text/html'},
                                               timeout=REQUEST_TIMEOUT, max_body_bytes=INDEX_MAX_BYTES)
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
                        or len(response.body) > INDEX_MAX_BYTES):
                    raise SecCollectionError('SEC_RESPONSE_INVALID') from None
                if response.status == 200:
                    if not response.body:
                        raise SecCollectionError('SEC_RESPONSE_INVALID') from None
                    return response.body
                if response.status not in RETRY_STATUSES or attempt == MAX_ATTEMPTS - 1:
                    raise SecCollectionError('SEC_HTTP_FAILED') from None
                self._pause(self._retry_wait(response.retry_after, 2.0 ** (attempt + 1)))
        raise SecCollectionError('SEC_TRANSPORT_FAILED') from None


def _folder(accession):
    return accession.replace('-', '')


def index_url(company_id, accession):
    return INDEX_URL.format(cik=int(US_LISTINGS[company_id]['cik']), folder=_folder(accession), accession=accession)


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _accepted(value):
    if not isinstance(value, str) or _ACCEPTANCE.fullmatch(value) is None:
        return None
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.utcoffset() is not None else None


def current_reports(company_id, submissions, *, acquired_at, since):
    """Recent 8-K/8-K/A rows filed on/after `since` (date) and accepted by `acquired_at`.

    Returns (rows, counts). Rows: accession, form, filing_date, event_date, accepted_at (UTC), items.
    Same accession twice: identical rows fold, different rows are dropped as a conflict.
    """
    counts = {'excluded': 0, 'conflicts': 0, 'unknown_items': 0}
    cik = US_LISTINGS[company_id]['cik']
    if not isinstance(submissions, Mapping) or str(submissions.get('cik', '')).zfill(10) != cik:
        raise ValueError('SEC_8K_SUBMISSIONS_INVALID')
    recent = submissions.get('filings', {}).get('recent') if isinstance(submissions.get('filings'), Mapping) else None
    columns = ('form', 'accessionNumber', 'filingDate', 'reportDate', 'acceptanceDateTime', 'items')
    if not isinstance(recent, Mapping) or any(not isinstance(recent.get(c), list) for c in columns):
        raise ValueError('SEC_8K_SUBMISSIONS_INVALID')
    size = len(recent['form'])
    if any(len(recent[c]) != size for c in columns):
        raise ValueError('SEC_8K_SUBMISSIONS_INVALID')
    seen, conflicts = {}, set()
    for index in range(size):
        if recent['form'][index] not in FORMS:
            continue
        accession = recent['accessionNumber'][index]
        filed, accepted = _day(recent['filingDate'][index]), _accepted(recent['acceptanceDateTime'][index])
        if (not isinstance(accession, str) or _ACCESSION.fullmatch(accession) is None or filed is None
                or accepted is None or accepted > acquired_at or filed > acquired_at.date()):
            counts['excluded'] += 1
            continue
        if filed < since:
            continue
        items, unknown = parse_items(recent['items'][index])
        counts['unknown_items'] += unknown
        event = _day(recent['reportDate'][index])
        row = {'accession': accession, 'form': recent['form'][index], 'filing_date': filed.isoformat(),
               'event_date': event.isoformat() if event is not None and event <= filed else None,
               'accepted_at': accepted.isoformat(), 'items': items}
        if accession in seen:
            if seen[accession] != row:
                conflicts.add(accession)
            continue
        seen[accession] = row
    for accession in conflicts:
        del seen[accession]
    counts['conflicts'] = len(conflicts)
    return list(seen.values()), counts


class _IndexTable(HTMLParser):
    """Rows of the EDGAR filing index 'Document Format Files' table: cell texts and the first link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._table, self._row, self._cell, self._href = [], 0, None, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            if self._table:
                self._table += 1
            elif (attrs.get('summary') or '').strip() == 'Document Format Files':
                self._table = 1
        elif self._table == 1 and tag == 'tr':
            self._row, self._href = [], None
        elif self._table == 1 and tag in ('td', 'th') and self._row is not None:
            self._cell = []
        elif self._table == 1 and tag == 'a' and self._cell is not None and self._href is None:
            self._href = attrs.get('href')

    def handle_endtag(self, tag):
        if tag == 'table' and self._table:
            self._table -= 1
        elif self._table == 1 and tag in ('td', 'th') and self._cell is not None and self._row is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif self._table == 1 and tag == 'tr' and self._row is not None:
            self.rows.append((self._row, self._href))
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _title(text):
    text = ' '.join((text or '').split())
    if not text or len(text) > TITLE_MAX or any(ord(ch) < 32 or ch in '<>' for ch in text):
        return None
    return text


def exhibit_99_1(company_id, accession, body):
    """Filing index HTML -> {'title', 'url'} of Exhibit 99.1, or a fixed reason code string.

    The title is the index row's description (the exhibit type when the description is empty);
    the exhibit document itself is never requested.
    """
    try:
        text = body.decode('utf-8')
    except (UnicodeError, AttributeError):
        return 'INDEX_INVALID'
    parser = _IndexTable()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        return 'INDEX_INVALID'
    if not parser.rows:
        return 'INDEX_INVALID'
    cik = int(US_LISTINGS[company_id]['cik'])
    prefix = f'/Archives/edgar/data/{cik}/{_folder(accession)}/'
    for cells, href in parser.rows:
        if len(cells) < 4 or cells[3].upper() not in EXHIBIT_TYPES:
            continue
        path = (href or '').removeprefix('/ix?doc=')
        name = path[len(prefix):] if path.startswith(prefix) else None
        if name is None or _DOCUMENT.fullmatch(name) is None:
            return 'EXHIBIT_LINK_INVALID'
        title = _title(cells[1]) or _title(cells[3].upper())
        if title is None:
            return 'EXHIBIT_TITLE_INVALID'
        return {'title': title, 'url': ARCHIVE_URL.format(cik=cik, folder=_folder(accession), name=name)}
    return 'NO_EXHIBIT_99_1'


# Earnings date: estimated (filing pattern) -> confirmed (8-K Item 2.02), queue 2.2 a.
CONFIRMATION_BASIS = 'SEC_8K_ITEM_2_02'
CONFIRM_MAX_DAYS = 120


def latest_period_end(groups, today):
    """Latest observed fiscal period end (10-Q/10-K report month-day, this or last year) on/before `today`.

    Mirrors public-screens.js latestPeriodEnd. An estimate from the filing pattern, not a reported date.
    """
    best = None
    for group in groups:
        month, day = (int(x) for x in group['report_month_day'].split('-'))
        for year in (today.year - 1, today.year):
            try:
                candidate = date(year, month, day)
            except ValueError:
                continue
            if candidate <= today and (best is None or candidate > best):
                best = candidate
    return best


def eastern_date(moment):
    from zoneinfo import ZoneInfo
    return moment.astimezone(ZoneInfo('America/New_York')).date()


def earnings_confirmation(company_id, submissions, groups, *, acquired_at, as_of):
    """First original 8-K with Item 2.02 released after the latest estimated period end.

    Returns (confirmed_earnings_date, record) or (None, None). The release date is the Eastern
    date of the SEC acceptance time. Missing `items` or invalid rows mean no confirmation.
    """
    period_end = latest_period_end(groups, as_of.astimezone(timezone.utc).date())
    if period_end is None:
        return None, None
    try:
        rows, _ = current_reports(company_id, submissions, acquired_at=min(acquired_at, as_of), since=period_end)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None, None
    hits = []
    for row in rows:
        accepted = datetime.fromisoformat(row['accepted_at'])
        released = eastern_date(accepted)
        if row['form'] == '8-K' and '2.02' in row['items'] and period_end < released <= period_end + timedelta(days=CONFIRM_MAX_DAYS):
            hits.append((accepted, row['accession'], released))
    if not hits:
        return None, None
    accepted, accession, released = min(hits)
    return released.isoformat(), {'basis': CONFIRMATION_BASIS, 'period_end': period_end.isoformat(), 'accession': accession,
                                  'accepted_at': accepted.replace(microsecond=0).isoformat()}
