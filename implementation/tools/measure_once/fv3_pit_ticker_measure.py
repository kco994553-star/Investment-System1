"""ONE-TIME MEASUREMENT (decision FV3-PIT-TICKER; owner approval 2026-10-31, "workflow ② 승인"). Not part of any pipeline.
It ran once (run 41255597310, 2026-11-01) from the push-only workflow of branch claude/fv3-pit-ticker-measure (commit
ead5ffdd, never merged). The tool is moved here unchanged in behaviour so that branch can be deleted; the workflow is not
carried over. Its functions are the base of the SEC one-time collection's ticker-mismatch classifier
(sec_once_ticker_mismatch.py, run from .github/workflows/sec-once-collect.yml; plan
docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md). Run on its own it still measures exactly as it did on 2026-11-01.

Question (forward validation v3 design, section 12): how often do the 10-K / 10-Q filings of 2016-2019 carry the cover-page
`dei:TradingSymbol`, and how often does the XBRL instance file name prefix equal the ticker? The answer decides how the
point-in-time ticker -> CIK intervals are built (TradingSymbol first, instance-name prefix second, then the venue's quotes
or trades on the rebalance day).

Sample (deterministic, small): the CIKs of today's Universe504 codes, read from the reviewed in-repo registry binding
(product/web_assets/company-names-ko.json: universe_code -> cik, for every code of universe/universe_codes_v1.json),
ordered by sha256 of the 10-digit CIK. The first 120 form one panel that is used for every year 2016, 2017, 2018 and 2019.
The repository holds no list of historical or delisted names with CIKs, so none is added. Per year, the four quarterly
EDGAR full-index form.idx files give each panel CIK's first original 10-K of the year (else its first 10-Q).

Per picked filing: the filing directory listing (index.json; the -index.htm page when that is missing or no listing), the
XBRL instance (the *.xml that is not a schema or linkbase; for inline XBRL the EDGAR-extracted *_htm.xml, else the
inline document named like the schema), and in it:
- `dei:TradingSymbol` present: XBRL element or inline `ix:nonNumeric name="dei:TradingSymbol"`, tags matched
  case-insensitively, any value (also nil); the dei prefix also comes from the instance's own dei namespace declaration;
- the instance name prefix (text before the first '-' or '_') and whether it equals a TradingSymbol value
  (case-insensitive; `_loose`: letters and digits only) or one of today's Universe504 tickers of the CIK (letters and
  digits only);
- `dei:DocumentPeriodEndDate`, to split filings for periods ending on/after 2019-06-15 (TradingSymbol mandatory for large
  accelerated filers) from earlier ones (voluntary).

SEC fair access: the User-Agent comes only from env SEC_USER_AGENT and is never printed (missing -> one fixed STOP line,
exit 2, no network); only https://www.sec.gov/Archives/edgar/ is requested and redirects are refused; a fixed sleep before
every request (at most 1 / 0.15 s = 6.7 requests per second); 429, 5xx and network errors retried at most twice with
backoff; caps on requests, wall clock and response sizes. Everything stays in RAM; nothing is written to disk.
Output: fixed count lines only. Never a ticker, CIK, company name, URL, User-Agent or exception text (fixed codes and
exception class names only):
  PITTICKER_START pool=<CIKs> panel=<n> years=2016-2019 per_year=120 max_requests=2500 wall_clock_s=1200
  PITTICKER year=<y>|overall sampled form_idx_ok filed form10k instance no_instance inline trading_symbol symbol_multi
      prefix prefix_eq_symbol prefix_eq_symbol_loose prefix_eq_today period_known post_mandate post_mandate_symbol errors
      (each as key=<count>; filed = instance + no_instance + errors when not stopped)
  PITTICKER_ERRORS year=<y>|overall codes=<CODE:n,...>|-
  PITTICKER_REQUESTS total form_idx filing_index instance retries http403 http429 http5xx idx_early_stop idx_unsorted
      idx_rows idx_bad_rows (key=<count>) mb_wire=<MB> mb_body=<MB> elapsed_s=<s> stopped=NONE|<reason>
  PITTICKER_STOP reason=<code>   (configuration stop before any request)
Exit 0 complete, 3 stopped early (counts so far still printed), 2 configuration stop, 1 unexpected.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import html  # noqa: E402
import http.client  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402
import zlib  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402

IMPLEMENTATION = Path(__file__).resolve().parents[2]
REGISTRY = IMPLEMENTATION / 'src/investment_system/product/web_assets/company-names-ko.json'
CODES = IMPLEMENTATION / 'src/investment_system/universe/universe_codes_v1.json'
UNIVERSE_SIZE = 504

YEARS = (2016, 2017, 2018, 2019)
PER_YEAR = 120
TARGET_FORMS = (b'10-K', b'10-Q')
MANDATE_DAY = date(2019, 6, 15)

HOST = 'www.sec.gov'
PATH_PREFIX = '/Archives/edgar/'
SLEEP_S = 0.15                 # fixed sleep before every request (also before each retry): <= 6.7 requests per second
MAX_RETRIES = 2                # 429 / 5xx / network errors: at most two retries
BACKOFF_S = (2.0, 6.0)
RETRY_AFTER_MAX_S = 30.0
TIMEOUT_S = 20
MAX_REQUESTS = 2500            # every HTTP attempt counts, retries included
WALL_CLOCK_S = 20 * 60
STOP_AFTER_403 = 5             # consecutive 403s: a refused User-Agent or a block, so stop
STOP_AFTER_429 = 10            # 429s in the whole run: back off for good
CHUNK = 64 * 1024
FORM_IDX_CAP = 256 * 1024 * 1024   # streamed line by line, never held whole
INDEX_CAP = 4 * 1024 * 1024
INSTANCE_CAP = 96 * 1024 * 1024

STOP_MISSING = 'PITTICKER_STOP reason=SEC_USER_AGENT_MISSING'
STOP_INVALID = 'PITTICKER_STOP reason=SEC_USER_AGENT_INVALID'
STOP_SAMPLE = 'PITTICKER_STOP reason=SAMPLE_INPUT_INVALID'
STOP_REASONS = ('NONE', 'REQUEST_CAP', 'WALL_CLOCK', 'HTTP403_REPEATED', 'HTTP429_REPEATED', 'UNEXPECTED')

FIELDS = ('sampled', 'form_idx_ok', 'filed', 'form10k', 'instance', 'no_instance', 'inline', 'trading_symbol',
          'symbol_multi', 'prefix', 'prefix_eq_symbol', 'prefix_eq_symbol_loose', 'prefix_eq_today', 'period_known',
          'post_mandate', 'post_mandate_symbol', 'errors')
REQUEST_FIELDS = ('total', 'form_idx', 'filing_index', 'instance', 'retries', 'http403', 'http429', 'http5xx',
                  'idx_early_stop', 'idx_unsorted', 'idx_rows', 'idx_bad_rows')

_CIK10 = re.compile(r'[0-9]{10}')
_CODE_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,47}')
_LABEL = re.compile(r'year=20[0-9]{2}|overall')
_IDX_DAY = re.compile(rb'([0-9]{4})-?([0-9]{2})-?([0-9]{2})')
_IDX_PATH = re.compile(rb'edgar/data/([0-9]{1,10})/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt')
_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}')
_HREF = re.compile(rb'href="(?:/ix\?doc=)?/Archives/edgar/data/[0-9]{1,10}/[0-9]{18}/([A-Za-z0-9][A-Za-z0-9._-]{0,199})"',
                   re.I)
_LINKBASE = ('_cal.xml', '_def.xml', '_lab.xml', '_pre.xml', '_ref.xml')
_NOT_INSTANCE = ('filingsummary.xml', 'primary_doc.xml')
_DEI_NS = re.compile(r'xmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*["\']http://xbrl\.sec\.gov/dei/', re.I)
_TAGS = re.compile(r'<[^>]*>')
_MONTHS = {m: i for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov',
                                       'dec'), 1)}


class Stop(Exception):
    """Ends the whole run (budget, wall clock, repeated 403 / 429); the summary printed so far stays valid."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason if reason in STOP_REASONS else 'UNEXPECTED'


class FetchError(Exception):
    """One request or one filing failed; `code` is a fixed token (HTTP status, check name or exception class name)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code if isinstance(code, str) and _CODE_TOKEN.fullmatch(code) else 'OTHER'


# ---- routes ----------------------------------------------------------------------------------------------------------
def checked_url(url):
    """Allow-list: https, exactly www.sec.gov (no userinfo, no port), path under /Archives/edgar/, no query."""
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        raise ValueError('URL_NOT_ALLOWED')
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc != HOST or parts.hostname != HOST or not parts.path.startswith(PATH_PREFIX)
            or '..' in parts.path or '\\' in parts.path or parts.query or parts.fragment):
        raise ValueError('URL_NOT_ALLOWED')
    return url


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FetchError('REDIRECT_REJECTED')


def build_opener():
    return urllib.request.build_opener(_RejectRedirects())


def valid_user_agent(agent):
    """Same rule as the repository's SEC client: printable ASCII, a contact and some other text, not a placeholder."""
    if not isinstance(agent, str) or not re.fullmatch(r'[\x20-\x7e]{1,512}', agent):
        return False
    contact = re.search(r'\S+@\S+\.\S+', agent)
    return (contact is not None and bool((agent[:contact.start()] + agent[contact.end():]).strip())
            and '.invalid' not in agent.lower())


# ---- client ----------------------------------------------------------------------------------------------------------
class SecClient:
    def __init__(self, user_agent, *, opener=None, sleep=time.sleep, clock=time.monotonic):
        self._headers = {'User-Agent': user_agent, 'Accept-Encoding': 'gzip'}
        self._opener = opener if opener is not None else build_opener()
        self._sleep, self._clock = sleep, clock
        self._start = clock()
        self._refused_in_a_row = 0
        self.counts = Counter()

    def elapsed(self):
        return self._clock() - self._start

    def _deadline(self):
        if self.elapsed() >= WALL_CLOCK_S:
            raise Stop('WALL_CLOCK')

    def fetch(self, url, *, kind, cap, consume):
        """GET one allow-listed URL and hand its (decompressed, size-capped) body chunks to `consume`. A failed attempt
        (429, 5xx, network error) is retried at most MAX_RETRIES times; the whole call restarts, so `consume` starts over."""
        checked_url(url)
        for attempt in range(MAX_RETRIES + 1):
            if self.counts['total'] >= MAX_REQUESTS:
                raise Stop('REQUEST_CAP')
            self._deadline()
            self._sleep(SLEEP_S)
            self.counts['total'] += 1
            self.counts[kind] += 1
            try:
                request = urllib.request.Request(url, headers=self._headers)
                with self._opener.open(request, timeout=TIMEOUT_S) as response:
                    self._refused_in_a_row = 0
                    return consume(self._chunks(response, cap))
            except urllib.error.HTTPError as exc:
                status = exc.code if type(exc.code) is int else 0
                retry_after = exc.headers.get('Retry-After') if exc.headers is not None else None
                exc.close()
                self._refused_in_a_row = self._refused_in_a_row + 1 if status == 403 else 0
                if status == 403:
                    self.counts['http403'] += 1
                elif status == 429:
                    self.counts['http429'] += 1
                elif 500 <= status <= 599:
                    self.counts['http5xx'] += 1
                if self._refused_in_a_row >= STOP_AFTER_403:
                    raise Stop('HTTP403_REPEATED') from None
                if self.counts['http429'] >= STOP_AFTER_429:
                    raise Stop('HTTP429_REPEATED') from None
                if not (status == 429 or 500 <= status <= 599) or attempt == MAX_RETRIES:
                    raise FetchError(f'HTTP{status}' if 100 <= status <= 599 else 'HTTP_OTHER') from None
                wait = BACKOFF_S[attempt]
                if status == 429 and isinstance(retry_after, str) and retry_after.strip().isdigit():
                    wait = max(wait, min(float(retry_after.strip()), RETRY_AFTER_MAX_S))
            except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
                if attempt == MAX_RETRIES:
                    raise FetchError(type(exc).__name__) from None
                wait = BACKOFF_S[attempt]
            self.counts['retries'] += 1
            self._sleep(wait)
        raise FetchError('RETRIES_EXHAUSTED')  # not reached

    def _chunks(self, response, cap):
        encoding = (response.headers.get('Content-Encoding') or 'identity').strip().lower()
        if encoding not in ('identity', 'gzip', 'x-gzip', 'deflate'):
            raise FetchError('ENCODING_NOT_SUPPORTED')
        # gzip only is requested; a zlib 'deflate' body is read too (wbits 47: zlib or gzip header)
        inflate = None if encoding == 'identity' else zlib.decompressobj(47 if encoding == 'deflate' else 31)
        wire = body = 0
        while True:
            self._deadline()
            raw = response.read(CHUNK)
            if not raw:
                break
            wire += len(raw)
            self.counts['wire_bytes'] += len(raw)
            if wire > cap:
                raise FetchError('SIZE_CAP')
            for piece in ((raw,) if inflate is None else _inflate(inflate, raw)):
                body += len(piece)
                self.counts['body_bytes'] += len(piece)
                if body > cap:
                    raise FetchError('SIZE_CAP')
                yield piece
        if inflate is not None:
            try:
                tail = inflate.flush()
            except zlib.error:
                raise FetchError('BAD_GZIP') from None
            body += len(tail)
            self.counts['body_bytes'] += len(tail)
            if body > cap:
                raise FetchError('SIZE_CAP')
            if tail:
                yield tail


def _inflate(inflate, raw):
    """Bounded pieces (at most 1 MiB each), so the size cap is checked before a compressed chunk can expand far."""
    data = raw
    try:
        while data:
            piece = inflate.decompress(data, 16 * CHUNK)
            data = inflate.unconsumed_tail
            if piece:
                yield piece
    except zlib.error:
        raise FetchError('BAD_GZIP') from None


# ---- consumers -------------------------------------------------------------------------------------------------------
def read_all(chunks):
    return b''.join(chunks)


def iter_lines(chunks):
    rest = b''
    for chunk in chunks:
        lines = (rest + chunk).split(b'\n')
        rest = lines.pop()
        for line in lines:
            yield line.rstrip(b'\r')
    if rest:
        yield rest.rstrip(b'\r')


def form_idx_rows(chunks, wanted):
    """Rows (cik, form, date_filed, accession) of 10-K / 10-Q filings of the `wanted` CIKs in one form.idx.

    Each row is read from the right: file name (edgar/data/<cik>/<accession>.txt, which also gives the CIK, so a long
    company name glued to the CIK column cannot hide a row), date filed (YYYY-MM-DD or YYYYMMDD), and the form type as
    the first field of the rest. form.idx is sorted by form type, so the 10-K and 10-Q blocks come before every form type
    that does not start with '1'. Reading stops at the first such row once a 10-K / 10-Q row was seen, unless a row ever
    came out of order, in which case the whole file is read (up to the size cap).
    Returns (rows, early_stop, unsorted, parsed_rows, bad_rows)."""
    rows, header_done, previous, seen, unsorted, parsed, bad = [], False, None, False, False, 0, 0
    for line in iter_lines(chunks):
        if not header_done:
            header_done = line.startswith(b'-----')
            continue
        parts = line.rsplit(None, 2)
        path = _IDX_PATH.fullmatch(parts[2]) if len(parts) == 3 else None
        day = _IDX_DAY.fullmatch(parts[1]) if path else None
        if day is None:
            bad += int(bool(line.strip()))
            continue
        parsed += 1
        form = parts[0].split(b'  ', 1)[0].strip()
        if previous is not None and form < previous:
            unsorted = True
        previous = form
        if form in TARGET_FORMS:
            seen = True
            cik = int(path.group(1))
            if cik in wanted:
                rows.append((cik, form.decode('ascii'), b'-'.join(day.groups()).decode('ascii'), path.group(2).decode('ascii')))
        elif seen and not unsorted and not form.startswith(b'1'):
            return rows, True, unsorted, parsed, bad
    if not header_done:
        raise FetchError('BAD_FORM_IDX')
    return rows, False, unsorted, parsed, bad


def directory_names_json(chunks):
    """{name: size} from an EDGAR directory index.json; names restricted to one plain path segment."""
    try:
        items = json.loads(b''.join(chunks))['directory']['item']
    except (ValueError, KeyError, TypeError):
        raise FetchError('BAD_INDEX') from None
    if not isinstance(items, list):
        raise FetchError('BAD_INDEX')
    names = {}
    for item in items:
        name = item.get('name') if isinstance(item, dict) else None
        if isinstance(name, str) and _NAME.fullmatch(name):
            size = item.get('size')
            names[name] = int(size) if isinstance(size, str) and size.isdigit() else size if type(size) is int else 0
    return names


def directory_names_html(chunks):
    """{name: 0} from the links of a filing's -index.htm page (fallback when index.json is missing)."""
    names = {m.group(1).decode('ascii'): 0 for m in _HREF.finditer(b''.join(chunks))}
    if not names:
        raise FetchError('BAD_INDEX')
    return names


# ---- filing checks ---------------------------------------------------------------------------------------------------
def pick_instance(names):
    """(file name, inline) of the XBRL instance among a filing's file names, or (None, False)."""
    def size_order(candidates):
        return sorted(candidates, key=lambda n: (-(names.get(n) or 0), n))[0]

    lower = {n: n.lower() for n in names}
    xml = [n for n, low in lower.items() if low.endswith('.xml') and not low.endswith(_LINKBASE)
           and low not in _NOT_INSTANCE and not re.fullmatch(r'r[0-9]+\.xml', low)]
    extracted = [n for n in xml if lower[n].endswith('_htm.xml')]
    if extracted:
        return size_order(extracted), True
    schema_bases = sorted(n[:-4] for n, low in lower.items() if low.endswith('.xsd'))
    same_base = [n for n in xml if n[:-4] in schema_bases]
    if same_base:
        return size_order(same_base), False
    if xml:
        return size_order(xml), False
    for base in schema_bases:
        for name in names:
            if name.lower() in (base.lower() + '.htm', base.lower() + '.html'):
                return name, True
    return None, False


def name_prefix(name):
    """Text before the first '-' or '_' of a file name; None when there is no such separator or the text is empty."""
    match = re.match(r'([^-_]*)[-_]', name or '')
    return match.group(1) if match and match.group(1) else None


def _clean(value):
    return ' '.join(html.unescape(_TAGS.sub('', value)).split())


def dei_values(text, local, prefixes):
    """(present, values) of dei:<local> in an XBRL instance or an inline XBRL document (tags case-insensitive)."""
    alt = '|'.join(re.escape(p) for p in sorted(prefixes))
    element = re.compile(rf'<(?:{alt}):{local}\b[^>]*?(/?)>', re.I)
    inline = re.compile(rf'<(?:[A-Za-z_][A-Za-z0-9_.-]*:)?nonNumeric\b[^>]*?\bname\s*=\s*["\'](?:{alt}):{local}["\']'
                        rf'[^>]*?(/?)>', re.I)
    present, values = False, []
    for pattern, close in ((element, re.compile(rf'</(?:{alt}):{local}\s*>', re.I)),
                           (inline, re.compile(r'</(?:[A-Za-z_][A-Za-z0-9_.-]*:)?nonNumeric\s*>', re.I))):
        for match in pattern.finditer(text):
            present = True
            if match.group(1) == '/':
                continue
            window = text[match.end():match.end() + 4096]
            end = close.search(window)
            if end is not None:
                value = _clean(window[:end.start()])
                if value:
                    values.append(value)
    return present, values


def parse_day(value):
    """A period end date from an ISO value or an inline display text ('September 28, 2019', '28 September 2019',
    '09/28/2019'); None when it cannot be read."""
    text = value or ''
    try:
        if m := re.search(r'([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})', text):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := re.search(r'([A-Za-z]{3,9})\.?\s+([0-9]{1,2})(?:st|nd|rd|th)?\s*,?\s*([0-9]{4})', text):
            return date(int(m[3]), _MONTHS[m[1][:3].lower()], int(m[2]))
        if m := re.search(r'([0-9]{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?\s*,?\s*([0-9]{4})', text):
            return date(int(m[3]), _MONTHS[m[2][:3].lower()], int(m[1]))
        if m := re.search(r'([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})', text):
            return date(int(m[3]), int(m[1]), int(m[2]))
    except (KeyError, ValueError):
        return None
    return None


def scan_instance(body):
    text = body.decode('utf-8', 'replace') if isinstance(body, (bytes, bytearray)) else str(body)
    prefixes = {'dei'} | {p.lower() for p in _DEI_NS.findall(text)}
    present, symbols = dei_values(text, 'TradingSymbol', prefixes)
    _, periods = dei_values(text, 'DocumentPeriodEndDate', prefixes)
    period = next((d for d in map(parse_day, periods) if d is not None), None)
    return {'present': present, 'symbols': symbols, 'period': period}


def _alnum(value):
    return re.sub(r'[^a-z0-9]', '', (value or '').lower())


def evaluate(name, inline, facts, today_tickers):
    """Flags (0/1) of one filing whose instance was read. Values stay here; only the flags are counted."""
    symbols = [s for s in facts['symbols'] if s]
    prefix = name_prefix(name)
    period = facts['period']
    post = period is not None and period >= MANDATE_DAY
    flags = {'instance': 1, 'inline': int(bool(inline)), 'trading_symbol': int(bool(facts['present'])),
             'symbol_multi': int(len({s.lower() for s in symbols}) >= 2), 'prefix': int(prefix is not None),
             'period_known': int(period is not None), 'post_mandate': int(post),
             'post_mandate_symbol': int(post and bool(facts['present']))}
    if prefix is not None:
        flags['prefix_eq_symbol'] = int(any(prefix.lower() == s.lower() for s in symbols))
        flags['prefix_eq_symbol_loose'] = int(any(_alnum(s) and _alnum(prefix) == _alnum(s) for s in symbols))
        flags['prefix_eq_today'] = int(_alnum(prefix) in {_alnum(t) for t in today_tickers if _alnum(t)})
    return flags


def measure_filing(client, cik, accession, today_tickers):
    base = f'https://{HOST}/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/'
    try:
        try:
            names = client.fetch(base + 'index.json', kind='filing_index', cap=INDEX_CAP, consume=directory_names_json)
        except FetchError as exc:
            if exc.code not in ('HTTP404', 'BAD_INDEX'):
                raise
            names = client.fetch(base + accession + '-index.htm', kind='filing_index', cap=INDEX_CAP,
                                 consume=directory_names_html)
        name, inline = pick_instance(names)
        if name is None:
            return {'no_instance': 1}
        body = client.fetch(base + name, kind='instance', cap=INSTANCE_CAP, consume=read_all)
    except FetchError as exc:
        return {'error': exc.code}
    except Stop:
        raise
    except Exception as exc:  # one odd filing never ends the one run; class name only
        return {'error': 'UNEXPECTED_' + type(exc).__name__}
    try:
        return evaluate(name, inline, scan_instance(body), today_tickers)
    except Exception as exc:
        return {'error': 'PARSE_' + type(exc).__name__}


# ---- sample ----------------------------------------------------------------------------------------------------------
def load_pool(registry=REGISTRY, codes_path=CODES):
    """{10-digit CIK: {today's ticker, ...}} for every Universe504 code, from the reviewed registry binding."""
    codes = json.loads(Path(codes_path).read_text(encoding='utf-8'))
    if not isinstance(codes, list) or len(codes) != UNIVERSE_SIZE or len(set(codes)) != UNIVERSE_SIZE:
        raise ValueError('codes')
    wanted, seen, pool = set(codes), set(), {}
    for record in json.loads(Path(registry).read_text(encoding='utf-8'))['records']:
        code, cik = record.get('universe_code'), record.get('cik')
        if not isinstance(code, str) or code not in wanted:
            continue
        if not (isinstance(cik, str) and _CIK10.fullmatch(cik) and int(cik) > 0):
            raise ValueError('cik')
        pool.setdefault(cik, set()).add(code.split(':', 1)[1])
        seen.add(code)
    if seen != wanted:
        raise ValueError('coverage')
    return pool


def sample_panel(pool):
    return sorted(pool, key=lambda cik: hashlib.sha256(cik.encode('ascii')).hexdigest())[:PER_YEAR]


def pick_filings(rows):
    """{cik: (form, accession)}: the first original 10-K of the year by filing date, else the first 10-Q."""
    best = {}
    for cik, form, filed, accession in rows:
        rank = (0 if form == '10-K' else 1, filed, accession)
        if cik not in best or rank < best[cik]:
            best[cik] = rank
    return {cik: ('10-K' if rank[0] == 0 else '10-Q', rank[2]) for cik, rank in best.items()}


def measure_year(client, year, panel, pool, counts, errors):
    order = {int(cik): i for i, cik in enumerate(panel)}
    counts['sampled'] = len(panel)
    rows = []
    for quarter in (1, 2, 3, 4):
        url = f'https://{HOST}/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx'
        try:
            got, early, unsorted, parsed, bad = client.fetch(url, kind='form_idx', cap=FORM_IDX_CAP,
                                                             consume=lambda chunks: form_idx_rows(chunks, order))
        except FetchError as exc:
            errors['FORM_IDX_' + exc.code] += 1
            continue
        counts['form_idx_ok'] += 1
        client.counts['idx_early_stop'] += int(early)
        client.counts['idx_unsorted'] += int(unsorted)
        client.counts['idx_rows'] += parsed
        client.counts['idx_bad_rows'] += bad
        rows.extend(got)
    picks = pick_filings(rows)
    counts['filed'] = len(picks)
    counts['form10k'] = sum(1 for form, _ in picks.values() if form == '10-K')
    for cik in sorted(picks, key=order.__getitem__):
        result = measure_filing(client, cik, picks[cik][1], pool[f'{cik:010d}'])
        if 'error' in result:
            counts['errors'] += 1
            errors[result['error']] += 1
        else:
            counts.update(result)


# ---- output ----------------------------------------------------------------------------------------------------------
def format_counts(label, counts):
    if not _LABEL.fullmatch(label):
        raise ValueError('label')
    return 'PITTICKER ' + label + ' ' + ' '.join(f'{k}={int(counts.get(k, 0))}' for k in FIELDS)


def format_errors(label, errors):
    if not _LABEL.fullmatch(label):
        raise ValueError('label')
    merged = Counter()
    for code, n in errors.items():
        merged[code if isinstance(code, str) and _CODE_TOKEN.fullmatch(code) else 'OTHER'] += int(n)
    codes = ','.join(f'{code}:{merged[code]}' for code in sorted(merged) if merged[code]) or '-'
    return f'PITTICKER_ERRORS {label} codes={codes}'


def format_requests(counts, elapsed_s, stopped):
    stopped = stopped if stopped in STOP_REASONS else 'UNEXPECTED'
    parts = [f'{k}={int(counts.get(k, 0))}' for k in REQUEST_FIELDS]
    parts += [f'mb_wire={counts.get("wire_bytes", 0) / 1e6:.1f}', f'mb_body={counts.get("body_bytes", 0) / 1e6:.1f}',
              f'elapsed_s={int(elapsed_s)}', f'stopped={stopped}']
    return 'PITTICKER_REQUESTS ' + ' '.join(parts)


def run(client, pool, out):
    panel = sample_panel(pool)
    out(f'PITTICKER_START pool={len(pool)} panel={len(panel)} years={YEARS[0]}-{YEARS[-1]} per_year={PER_YEAR} '
        f'max_requests={MAX_REQUESTS} wall_clock_s={WALL_CLOCK_S}')
    totals, total_errors, stopped = Counter(), Counter(), 'NONE'
    try:
        for year in YEARS:
            counts, errors = Counter(), Counter()
            try:
                measure_year(client, year, panel, pool, counts, errors)
            finally:
                out(format_counts(f'year={year}', counts))
                out(format_errors(f'year={year}', errors))
                totals.update(counts)
                total_errors.update(errors)
    except Stop as stop:
        stopped = stop.reason
    except Exception as exc:  # a bug must not hide the counts gathered so far; class name only
        stopped = 'UNEXPECTED'
        total_errors['UNEXPECTED_' + type(exc).__name__] += 1
    out(format_counts('overall', totals))
    out(format_errors('overall', total_errors))
    out(format_requests(client.counts, client.elapsed(), stopped))
    return stopped


def main(*, environ=None, opener=None, sleep=time.sleep, clock=time.monotonic, out=None):
    environ = os.environ if environ is None else environ
    out = out if out is not None else (lambda line: print(line, flush=True))
    agent = environ.get('SEC_USER_AGENT') or ''
    if not agent.strip():
        out(STOP_MISSING)
        return 2
    if not valid_user_agent(agent):
        out(STOP_INVALID)
        return 2
    try:
        pool = load_pool()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        out(STOP_SAMPLE)
        return 2
    client = SecClient(agent, opener=opener, sleep=sleep, clock=clock)
    stopped = run(client, pool, out)
    return 0 if stopped == 'NONE' else 3


if __name__ == '__main__':
    try:
        code = main()
    except (Exception, KeyboardInterrupt) as exc:
        name = type(exc).__name__
        print(f'PITTICKER_STOP reason=UNEXPECTED class={name if _CODE_TOKEN.fullmatch(name) else "OTHER"}', flush=True)
        code = 1
    sys.exit(code)
