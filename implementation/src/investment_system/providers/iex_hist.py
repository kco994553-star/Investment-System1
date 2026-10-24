"""IEX HIST adapter for the central V publication (GSQ-024, owner decision 2026-10-23). RAM only.

Source: IEX HIST TOPS 1.6 (T+1 pcap files listed by https://iextrading.com/api/1.0/hist). The price of a code is the IEX
**last regular-session trade** of its IEX symbol on one trading day (Last Sale Eligible: no extended-hours flag, no odd-lot flag,
timestamp inside 09:30-16:00 New York). It is not an official close and covers trades on IEX only.

Basis day (owner decision D3 2026-10-24): the latest TOPS 1.6 file in the index dated <= the run's New York day (shard_day). The
files are T+1 (generated 04:24-10:22 UTC), so the daily run (~00:37 UTC) normally gets the previous trading day; a weekend or
market holiday has no file, so the last trading day before it is used. A half day (13:00 close) needs no calendar here: the
parser drops every trade with the TOPS sale-condition flag 0x40 (extended hours = outside the regular market session, TOPS 1.6
spec), so the price is the last eligible trade before the early close (spec rule; not yet observed on a real half day, the first
is 2026-11-27).
Both dates are published (price_source.requested_basis_date = the run's day, basis_date = the IEX file's day).

Flow of one day (`fetch_day`): hist index -> the latest TOPS 1.6 day <= the basis date -> GCS object metadata (size, md5) ->
download | md5 + size pump | gzip -dc | iex_last_trade (C, tools/iex_tops/iex_last_trade.c) -> {code: price} held in this
process only. Nothing is written but the public ticker list the parser reads; no price, yield or per-code price hash is printed,
logged, raised or stored (GSQ-010). Errors carry a fixed code only and are raised `from None`.

Price status per code (fixed codes, also published as the row's `price_status`):
  SUPPLIED                     a regular-session round-lot last trade on the day
  ODD_LOT_ONLY                 only odd-lot regular-session trades that day (not Last Sale Eligible: not used)
  NO_IEX_TRADE                 no regular-session trade on IEX that day, or the alias table says the code is not traded on
                               IEX from a date (symbol None); never filled from another day, symbol or source
  PRICE_SYMBOL_UNMAPPED        no IEX symbol for the row (a TARGET outside the US track, an invalid symbol)
  ADR_RATIO_UNCONFIRMED        foreign private issuer row (ifrs-full filer, or a known 20-F / 40-F filer whatever its
                               taxonomy: owner decision D7 2026-10-24): listed security / ADS ratio not confirmed (D-CV10)
  SPLIT_AFTER_SHARE_COUNT      split rules (D-CV11): D6 (a) qgv_official.split_after_share_count, F_k evidence of a split
                               between the count's period end and its filing, or a verified SPLITS window below; D6 (b)
                               qgv_official.split_check (owner decision CV-SPLIT (ii) 2026-10-24), a raw month-end / today
                               price step of at most 45 days since the count's period end inside a split band. A split AFTER
                               the count's filing is covered by D6 (b) where the store has short steps since the count's
                               period end; otherwise residual (V and rank off by the split ratio until the next 10-Q / 10-K)
  PRICE_IDENTITY_CONFLICT      TARGET row whose symbol is a withdrawn Universe code's (existing rule)
  IDENTITY_CONFLICT_WITHDRAWN  withdrawn row (no price is given)
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

PROVIDER = 'IEX_HIST'
FEED = ('TOPS', '1.6')
HIST_URL = 'https://iextrading.com/api/1.0/hist'
BASIS_KIND = 'IEX_LAST_REGULAR_SESSION_TRADE'
ADJUSTMENT_BASIS = 'AS_TRADED'
CURRENCY = 'USD'
ATTRIBUTION = ('Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data '
               'Terms of Use.')
TERMS_URL = 'https://www.iex.io/legal/hist-data-terms'
LABEL_KO = 'IEX 마지막 체결가 기준(공식 종가 아님)'
NY = ZoneInfo('America/New_York')
SESSION = (dt.time(9, 30), dt.time(16, 0))
PARSER_STATUSES = ('ROUND', 'ODD_ONLY', 'NO_TRADE')
CHUNK = 1 << 22
MAX_PRICE_E4 = 10**11   # $10M per share: anything above is a parser/format fault, never a price

SUPPLIED = 'SUPPLIED'
STATUS_CODES = ('SUPPLIED', 'ODD_LOT_ONLY', 'NO_IEX_TRADE', 'PRICE_SYMBOL_UNMAPPED', 'ADR_RATIO_UNCONFIRMED',
                'SPLIT_AFTER_SHARE_COUNT', 'PRICE_IDENTITY_CONFLICT', 'IDENTITY_CONFLICT_WITHDRAWN')
_FROM_PARSER = {'ROUND': SUPPLIED, 'ODD_ONLY': 'ODD_LOT_ONLY', 'NO_TRADE': 'NO_IEX_TRADE'}

# The ONE dated symbol alias table: Universe code -> ((from_date YYYY-MM-DD, IEX symbol or None, evidence), ...). For a day D the
# latest entry with from_date <= D wins; before the first entry the symbol is the code's own ticker ('NYSE:BRK.B' -> 'BRK.B').
# Symbol None = known not traded on IEX from that date: the code is NO_IEX_TRADE and is never filled from another symbol (a
# reused ticker would be another company). Used for the daily price and (via `iex_symbol`) for the month-end store; the U8
# plan tool (tools/iex_hist/monthend_plan.py, commit 7bca307d) carries the same PSKY entry.
SYMBOL_ALIASES: dict[str, tuple[tuple[str, str | None, str], ...]] = {
    # Skydance Corp (CIK 0002041610, formerly Paramount Skydance; Universe code NASDAQ:PSKY). CONFIRMED by the IEX TOPS probe
    # run 39944426209: PSKY trading status T + regular trades on 2026-10-02 and 2026-10-05, none from 2026-10-06; SKYD none
    # through 2026-10-05, status T + trades from 2026-10-06.
    'NASDAQ:PSKY': (('2026-10-06', 'SKYD', 'CONFIRMED IEX TOPS probe run 39944426209: PSKY last 2026-10-05, SKYD from 2026-10-06'),),
    # Warner Bros. Discovery: no IEX status message or trade from 2026-10-06 (traded through 2026-10-05; probe run 39944426209);
    # Form 15-12G filed 2026-10-16. NO_IEX_TRADE, never filled.
    'NASDAQ:WBD': (('2026-10-06', None, 'CONFIRMED IEX TOPS probe run 39944426209: no status/trade from 2026-10-06; Form 15-12G 2026-10-16'),),
}

# Month-end basis cuts for V4 (owner decision 2026-10-23): history months whose fiscal-year-end date is before `from_date` are not
# given a month-end price; when V4 then cannot be computed, its public reason is the cut's reason.
MONTHEND_BASIS_CUTS: dict[str, tuple[str, str, str]] = {
    # Paramount Global + Skydance merger closed 2025-08-07: pre-merger fiscal years are on another listed line/share basis.
    'NASDAQ:PSKY': ('2025-08-07', 'MERGER_PRE_BASIS_UNCONFIRMED', 'merger close 2025-08-07; pre-merger share basis unconfirmed'),
}

# D-CV11: verified split windows after the diluted-share count (code -> ((low, high], ...): split date inside (low, high]).
# Owner decision D6 (a) 2026-10-24: no new split source; qgv_official.split_after_share_count reads the F_k evidence of
# sec-qgv2.json (calc_version 2026-10-23.1). That evidence only covers a split between the share count's period end and the
# annual filing that reports the count, a count the filing already restates (so the rule is conservative only). It cannot
# cover a split after the count's own filing, the one window where count and price disagree: the F_k / SPLIT
# chain is evaluated at collection over companyfacts filed up to then (periodic 10-K / 10-Q XBRL only; a split announced in an
# 8-K or effective after the latest 10-Q leaves no fact until the next periodic filing restates the count), sec-qgv2.json does
# not carry the count's filing date, the run holds companyfacts of one shard only, and IEX HIST carries no corporate actions.
# This table therefore stays EMPTY: it is the hook for a verified source the owner may approve later, never filled by hand
# here. A split after the count's filing is covered by D6 (b) (owner decision CV-SPLIT (ii) 2026-10-24,
# qgv_official.split_check: a RAM-only comparison of the IEX raw month-end trades of the private store and today's raw price,
# on steps of at most 45 days since the count's period end; a hit withholds the price, it never changes one) where the store
# has short steps since the count's period end; otherwise residual: the official V and rank are off by the split ratio until
# the next periodic filing (tests/test_qgv_official.py). The U8 store of stamp 20261023 holds only fiscal-year-end months, so
# D6 (b) covers every code only after recent month-ends of every Universe code are in the store (a separate backfill).
SPLITS: dict[str, tuple[tuple[str, str], ...]] = {}


class IexHistError(RuntimeError):
    """Fixed code only: never a price, URL, token or response body."""


def _fail(code):
    raise IexHistError(code) from None


# ---- symbols ---------------------------------------------------------------------------------------------------------
def _iso(day: str) -> str:
    return day if '-' in day else f'{day[:4]}-{day[4:6]}-{day[6:]}'


def iex_symbol(code: str, day: str, aliases=SYMBOL_ALIASES):
    """IEX symbol of a Universe code ('EXCH:TICKER') on day YYYYMMDD / YYYY-MM-DD; None = not traded on IEX (alias None)."""
    iso = _iso(day)
    symbol = code.split(':', 1)[1]
    for since, alias, _ in sorted(aliases.get(code, ()), key=lambda a: a[0]):
        if iso >= since:
            symbol = alias
    return symbol


def valid_symbol(symbol) -> bool:
    return isinstance(symbol, str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.\-+=^]{0,7}', symbol) is not None


def split_after(code: str, period_end, basis_day: str, splits=SPLITS) -> bool:
    """True when a verified split window (low, high] of the code reaches past the share-count period end, up to the basis day."""
    if not isinstance(period_end, str):
        return False
    basis = _iso(basis_day)
    return any(high > period_end and low < basis for low, high in splits.get(code, ()))


# ---- hist index and file metadata ------------------------------------------------------------------------------------
def _get_json(url: str, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def fetch_json(url: str):
    """GET JSON from an allowed source host only (iextrading.com index, Google Cloud Storage object metadata)."""
    host = urllib.parse.urlsplit(url).hostname
    if not url.startswith('https://') or host not in ('iextrading.com', 'www.googleapis.com', 'storage.googleapis.com'):
        _fail('SOURCE_URL_INVALID')
    try:
        return _get_json(url)
    except Exception:  # noqa: BLE001 - fixed code, the message may carry a URL
        _fail('SOURCE_UNAVAILABLE')


def tops_files(index) -> dict:
    """{YYYYMMDD: TOPS 1.6 entry} of the hist index ({date: [feed entries]})."""
    if not isinstance(index, dict):
        _fail('INDEX_INVALID')
    out = {}
    for day, feeds in index.items():
        if not (isinstance(day, str) and re.fullmatch(r'\d{8}', day)):
            continue
        for f in feeds if isinstance(feeds, list) else ():
            if isinstance(f, dict) and (f.get('feed'), f.get('version')) == FEED and _link_ok(f.get('link')):
                out[day] = f
    return out


def _link_ok(link) -> bool:
    return isinstance(link, str) and urllib.parse.urlsplit(link).scheme == 'https' and \
        urllib.parse.urlsplit(link).hostname in ('www.googleapis.com', 'storage.googleapis.com')


def select_day(index, basis_date: dt.date):
    """(YYYYMMDD, entry): the latest TOPS 1.6 day <= the basis date (T+1: usually the previous trading day)."""
    files = tops_files(index)
    limit = basis_date.strftime('%Y%m%d')
    days = sorted(d for d in files if d <= limit)
    if not days:
        _fail('NO_FILE_FOR_BASIS')
    day = days[-1]
    entry = files[day]
    try:
        size = int(entry['size'])
    except (KeyError, TypeError, ValueError):
        _fail('INDEX_INVALID')
    if size <= 0:
        _fail('INDEX_INVALID')
    return day, dict(entry, size=size)


def gcs_metadata_url(link: str) -> str:
    """The GCS JSON-API object metadata URL (md5Hash, size) of a hist download link."""
    parts = urllib.parse.urlsplit(link)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != 'alt']
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path.replace('/download/storage/', '/storage/', 1),
                                    urllib.parse.urlencode(query), ''))


def file_checks(entry: dict, fetch=fetch_json) -> tuple[int, str]:
    """(size, md5 hex) from the GCS object metadata; the size must equal the index size."""
    meta = fetch(gcs_metadata_url(entry['link']))
    try:
        size, md5 = int(meta['size']), base64.b64decode(meta['md5Hash'], validate=True).hex()
    except Exception:  # noqa: BLE001
        _fail('METADATA_INVALID')
    if size != entry['size'] or len(md5) != 32:
        _fail('SIZE_MISMATCH')
    return size, md5


# ---- streaming parse -------------------------------------------------------------------------------------------------
def session_ns(day: str) -> tuple[int, int]:
    d = dt.date.fromisoformat(_iso(day))
    start = dt.datetime.combine(d, SESSION[0], NY)
    end = dt.datetime.combine(d, SESSION[1], NY)
    return int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9


def parse_rows(text: str, symbols) -> dict:
    """Parser stdout -> {SYM: (status, price_e4 or None)} for exactly the requested symbols."""
    rows = {}
    for line in text.splitlines():
        cols = line.split('\t')
        if len(cols) < 5 or cols[1] not in PARSER_STATUSES or cols[0] in rows:
            _fail('PARSER_OUTPUT_INVALID')
        try:
            px = int(cols[2])
        except ValueError:
            _fail('PARSER_OUTPUT_INVALID')
        if cols[1] != 'NO_TRADE' and not 0 < px < MAX_PRICE_E4:
            _fail('PARSER_PRICE_INVALID')
        rows[cols[0]] = (cols[1], px if cols[1] != 'NO_TRADE' else None)
    if set(rows) != set(symbols):
        _fail('PARSER_SYMBOLS_MISMATCH')
    return rows


def curl_command(link: str) -> list[str]:
    return ['curl', '-sS', '--fail', '--retry', '3', '--retry-delay', '10', '-o', '-', link]


def stream_day(link: str, symbols, *, day: str, size: int, md5: str, parser: str, workdir: Path,
               download=curl_command, popen=subprocess.Popen) -> dict:
    """download | md5 + size pump | gzip -dc | parser. Returns {SYM: (status, price_e4)}; IexHistError on any check failure."""
    symbols = sorted(set(symbols))
    if not symbols or not all(valid_symbol(s) for s in symbols):
        _fail('SYMBOLS_INVALID')
    workdir.mkdir(parents=True, exist_ok=True)
    symfile = workdir / f'iex-symbols-{day}.txt'
    symfile.write_text('\n'.join(symbols) + '\n', encoding='ascii')   # public tickers only
    t0, t1 = session_ns(day)
    procs = []
    try:
        p1 = popen(download(link), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p1)
        p2 = popen(['gzip', '-dc'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p2)
        p3 = popen([parser, str(symfile), str(t0), str(t1)], stdin=p2.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p3)
        p2.stdout.close()
        out: list[bytes] = []
        reader = threading.Thread(target=lambda: out.append(p3.stdout.read()), daemon=True)
        reader.start()
        digest, got, broken = hashlib.md5(), 0, False
        try:
            while True:
                chunk = p1.stdout.read(CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
                got += len(chunk)
                p2.stdin.write(chunk)
        except BrokenPipeError:
            broken = True
        finally:
            try:
                p2.stdin.close()
            except BrokenPipeError:
                broken = True
        if broken:
            p1.kill()
        codes = (p1.wait(), p2.wait(), p3.wait())
        reader.join()
    except IexHistError:
        raise
    except Exception:  # noqa: BLE001 - fixed code only
        for p in procs:
            p.kill()
        _fail('STREAM_FAILED')
    finally:
        symfile.unlink(missing_ok=True)
    if broken or codes[1] != 0:
        _fail('GZIP_FAILED')
    if codes[0] != 0:
        _fail('DOWNLOAD_FAILED')
    if got != size:
        _fail('SIZE_MISMATCH')
    if digest.hexdigest() != md5:
        _fail('MD5_MISMATCH')
    if codes[2] != 0:
        _fail('PARSER_FAILED')
    try:
        text = out[0].decode('ascii')
    except (IndexError, UnicodeDecodeError):
        _fail('PARSER_OUTPUT_INVALID')
    return parse_rows(text, symbols)


# ---- one day for a set of codes ---------------------------------------------------------------------------------------
class IexDay:
    """One IEX day in RAM: `quotes` {key: {price, currency}} for SUPPLIED keys only, `status` {key: code}. Its repr and str
    carry counts only (never a price)."""
    __slots__ = ('day', 'basis_date', 'quotes', 'status', 'collected_from', 'collected_to', 'symbol_of')

    def __init__(self, day, basis_date, quotes, status, collected_from, collected_to, symbol_of):
        self.day, self.basis_date, self.quotes, self.status = day, basis_date, quotes, status
        self.collected_from, self.collected_to, self.symbol_of = collected_from, collected_to, symbol_of

    def counts(self) -> dict:
        out = {}
        for s in self.status.values():
            out[s] = out.get(s, 0) + 1
        return dict(sorted(out.items()))

    def __repr__(self):
        return f'IexDay(day={self.day}, keys={len(self.status)}, statuses={self.counts()})'

    __str__ = __repr__

    def __reduce__(self):  # never pickled/serialized with its prices
        raise TypeError('IexDay is RAM only')


def resolve_symbols(keys: dict, day: str, aliases=SYMBOL_ALIASES) -> dict:
    """{key: IEX symbol or None} for {key: Universe code} (a TARGET key maps to its US listing code)."""
    return {k: (iex_symbol(code, day, aliases) if isinstance(code, str) and ':' in code else None) for k, code in keys.items()}


def fetch_day(keys: dict, basis_date: dt.date, *, parser: str, workdir: Path, fetch=fetch_json, stream=stream_day,
              clock=None, aliases=SYMBOL_ALIASES) -> IexDay:
    """Prices of {key: Universe code} for the latest IEX day <= basis_date. Status per key as in the module doc for the
    parser- and alias-derived codes (SUPPLIED / ODD_LOT_ONLY / NO_IEX_TRADE / PRICE_SYMBOL_UNMAPPED); row-level rules (ADR, split,
    identity) are applied by the caller."""
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    index = fetch(HIST_URL)
    day, entry = select_day(index, basis_date)
    size, md5 = file_checks(entry, fetch)
    symbol_of = resolve_symbols(keys, day, aliases)
    wanted = sorted({s for s in symbol_of.values() if valid_symbol(s)})
    started = clock()
    rows = stream(entry['link'], wanted, day=day, size=size, md5=md5, parser=parser, workdir=workdir) if wanted else {}
    ended = clock()
    quotes, status = {}, {}
    for key, sym in symbol_of.items():
        if sym is None and isinstance(keys.get(key), str):
            status[key] = 'NO_IEX_TRADE'          # alias table: not traded on IEX from that date
            continue
        if not valid_symbol(sym):
            status[key] = 'PRICE_SYMBOL_UNMAPPED'
            continue
        st, px = rows[sym]
        status[key] = _FROM_PARSER[st]
        if st == 'ROUND':
            quotes[key] = {'price': px / 10000, 'currency': CURRENCY}
    del rows
    return IexDay(_iso(day), basis_date.isoformat(), quotes, status, started, ended, symbol_of)
