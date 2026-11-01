"""ONE-TIME MEASUREMENT (owner decision 2026-11-01, item 2: "그다음 소표본 수집만 승인한다. 대량 수집은 그 결과를 본 뒤 정한다").
Not part of any pipeline. It runs once from .github/workflows/alpaca-sample-once.yml on the push to the run branch
claude/alpaca-sample-once-run. Research EXP-STOCK-INDICATOR-DECILES-v1 (settings doc sections 5, 6.2, 7).

Question: can Alpaca SIP daily bars supply what the annual-reselection engine needs for the whole historical U-A / U-B
candidate set? (a) the consolidated OPEN on each T (2016-02-16, 2017-02-21, 2018-02-20, 2019-02-19); (b) the CLOSE on each
S (2016-02-12, 2017-02-17, 2018-02-16, 2019-02-15); (c) month-end closes 2018-02..2019-02; (d) the hard cases: delisted /
acquired names (history up to the last trading day?), ticker changes (which symbol returns which period, and does the
`asof` symbol mapping follow the issuer?), symbol reuse, multi-class issuers (each class separately), ADRs, REITs, small
caps near the $250m entry threshold and names that listed inside the window. The answer decides the bulk-collection go /
no-go and which hard cases need another source. It never decides a weight, a selection or a result.

Sample: SAMPLE below, 40 securities in 10 categories, chosen by rule from documented public events (never by price or
performance). Each entry carries its public event and date and how the date was checked: WEB_CHECKED (a public source
excerpt read on 2026-11-01, named in the note), RECALL (well-known, not re-checked) or UNVERIFIED (Main checks before the
run). The repository holds no price.

Requests (Alpaca market data v2, historical bars, single symbol): GET https://data.alpaca.markets/v2/stocks/{symbol}/bars
with timeframe=1Day, start=2016-01-01 (New York), end=2019-03-31 (New York), adjustment=raw, feed=sip, limit=10000,
sort=asc, and asof='-' (RAW: the bars traded under exactly that symbol, no mapping) for every symbol; for the lineage cases
also asof=<a date inside the security's listing> (the issuer as of that date, followed through renames) and
asof=CURRENT_ASOF (what today's symbol maps to). Pagination by next_page_token (bounded). Exact URL allow-list, redirects
refused, keys only from env APCA_API_KEY_ID / APCA_API_SECRET_KEY (sent as headers, never printed), a fixed pause before
every request (<= 100 per minute, Alpaca's free limit is 200), bounded retries, request / wall-clock caps.

Prices stay in RAM. Output: fixed ALPSAMPLE_* lines of categories, counts, public dates and day differences between a bar
date and a listed event date. Never a price, volume, per-symbol count, key, token, URL, response text or exception text
(fixed codes and exception class names only). No decimal number is printed at all.

Raw storage (owner decision 5 route, settings doc 6.3): the exact response bytes and a sha256 manifest are zipped in RAM and
written ONLY to a NEW release `alpaca-sample-v1-<GITHUB_RUN_ID>` of the private raw repository (secret RAW_REPO_TOKEN):
the repository must answer private, the tag must not exist (create-only, checked before any Alpaca request and again before
creating), then one release with two assets, downloaded back and compared by sha256. No other release is listed, read,
changed or deleted. Alpaca terms: personal, non-commercial use; public posting needs prior written consent, so nothing
from this run is published.

    python implementation/tools/measure_once/alpaca_sample_once.py          # the run (GitHub Actions only)
    python implementation/tools/measure_once/alpaca_sample_once.py --plan   # request plan counts, no network, no key

Exit 0 complete and stored, 3 stopped early or storage failed (lines so far printed), 2 configuration stop before any
request, 1 unexpected.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import http.client  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402
import zipfile  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import date, datetime, timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import raw_store_release  # noqa: E402  (stdlib-only GitHub transport; the token comes from env RAW_REPO_TOKEN)

NY = ZoneInfo('America/New_York')

# ---- fixed measurement window and checkpoints (settings doc section 2; checked against research.pit_filings in tests) ----
WINDOW_START = date(2016, 1, 1)
WINDOW_END = date(2019, 3, 31)
WINDOW_AFTER = WINDOW_END + timedelta(days=1)
FIRST_SESSION = date(2016, 1, 4)
LAST_SESSION = date(2019, 3, 29)
START_PARAM = '2016-01-01T00:00:00-05:00'
END_PARAM = '2019-03-31T23:59:59-04:00'
T_DAYS = ((2016, date(2016, 2, 16)), (2017, date(2017, 2, 21)), (2018, date(2018, 2, 20)), (2019, date(2019, 2, 19)))
S_DAYS = ((2016, date(2016, 2, 12)), (2017, date(2017, 2, 17)), (2018, date(2018, 2, 16)), (2019, date(2019, 2, 15)))
MONTH_ENDS = (date(2018, 2, 28), date(2018, 3, 29), date(2018, 4, 30), date(2018, 5, 31), date(2018, 6, 29),
              date(2018, 7, 31), date(2018, 8, 31), date(2018, 9, 28), date(2018, 10, 31), date(2018, 11, 30),
              date(2018, 12, 31), date(2019, 1, 31), date(2019, 2, 28))
CURRENT_ASOF = '2026-10-30'   # "today's symbol" mapping, fixed so the run is reproducible (last day of the existing release)

CATEGORIES = ('CONTROL_LARGE', 'ETF_AUX', 'DELISTED_ACQUIRED', 'DELISTED_OTHER', 'TICKER_CHANGE', 'MULTI_CLASS', 'ADR',
              'REIT', 'SMALL_CAP_NEAR_THRESHOLD', 'IPO_IN_WINDOW')
CHECKS = ('WEB_CHECKED', 'RECALL', 'UNVERIFIED')

# ---- the fixed sample ------------------------------------------------------------------------------------------------------
# (sid, category, legs, public event note, check). A leg (symbol, first, end) says the security traded under `symbol` on
# days d with first <= d < end (None = before / after the window). `end` is the documented event day (merger effective,
# exchange suspension or delisting, rename effective), so its last bar under the symbol is expected on or just before it.
# Selection rules per category (never price or performance):
#   CONTROL_LARGE      two of the largest U.S. common stocks, listed throughout, no symbol change;
#   ETF_AUX            SPY, the "ETF auxiliary comparison" of the settings doc (bars only; distributions need another source);
#   DELISTED_ACQUIRED  acquisitions of then-listed U.S. issuers that closed inside the window, one or more per period
#                      (listed at T2016 / T2017 / T2018, gone before the next T), two of them with a later symbol reuse;
#   DELISTED_OTHER     bankruptcy suspensions / delistings inside the window (one relisted under the same symbol);
#   TICKER_CHANGE      renames of continuously listed issuers, four inside the window and one after it (FB -> META);
#   MULTI_CLASS        issuers with two listed common classes, each class requested; one with an in-window symbol swap;
#   ADR                two large ADRs listed throughout and one acquired inside the window;
#   REIT               two large equity REITs listed throughout and one acquired inside the window;
#   SMALL_CAP_NEAR_THRESHOLD  small issuers recalled near USD 200-400m issuer value around 2018-02 (level UNVERIFIED: no
#                      market cap is in the repository; check with SEC shares x close once collected), one acquired;
#   IPO_IN_WINDOW      well-known first trading days spread over 2016..2019, the last on the window's last session.
SAMPLE = (
    ('CL01', 'CONTROL_LARGE', (('AAPL', None, None),), 'Apple Inc. common, Nasdaq, listed throughout, no symbol change',
     'RECALL'),
    ('CL02', 'CONTROL_LARGE', (('MSFT', None, None),), 'Microsoft Corp. common, Nasdaq, listed throughout, no symbol change',
     'RECALL'),
    ('EA01', 'ETF_AUX', (('SPY', None, None),), 'SPDR S&P 500 ETF Trust, NYSE Arca, listed throughout (ETF auxiliary '
     'comparison only; distributions are not in bars)', 'RECALL'),

    ('DA01', 'DELISTED_ACQUIRED', (('EMC', None, '2016-09-07'),), 'EMC Corp. (NYSE) acquired by Dell Technologies; '
     'merger closed 2016-09-07', 'RECALL'),
    ('DA02', 'DELISTED_ACQUIRED', (('WFM', None, '2017-08-28'),), 'Whole Foods Market (Nasdaq) acquired by Amazon; '
     'closed 2017-08-28', 'RECALL'),
    ('DA03', 'DELISTED_ACQUIRED', (('DOW', None, '2017-08-31'),), 'The Dow Chemical Co. (NYSE) merged into DowDuPont '
     '(DWDP from 2017-09-01), merger effective 2017-08-31; symbol DOW reused by Dow Inc. (new issuer) from 2019-04-02, '
     'after the window', 'RECALL'),
    ('DA04', 'DELISTED_ACQUIRED', (('MON', None, '2018-06-07'),), 'Monsanto Co. (NYSE) acquired by Bayer; closed '
     '2018-06-07', 'RECALL'),
    ('DA05', 'DELISTED_ACQUIRED', (('TWX', None, '2018-06-14'),), 'Time Warner Inc. (NYSE) acquired by AT&T; closed '
     '2018-06-14', 'RECALL'),
    ('DA06', 'DELISTED_ACQUIRED', (('DNB', None, '2019-02-08'),), 'Dun & Bradstreet (NYSE) taken private by an investor '
     'group (Cannae, CC Capital, Thomas H. Lee); completion confirmed by the buyer release, day 2019-02-08 not re-checked',
     'UNVERIFIED'),
    ('DA07', 'DELISTED_ACQUIRED', (('FOXA', None, '2019-03-19'),), 'Twenty-First Century Fox class A (Nasdaq) acquired by '
     'Disney, merger effective 2019-03-20 00:02 ET; Fox Corporation (new issuer) regular-way trading as FOXA from 2019-03-19 '
     '(Nasdaq trader notice ECA2019-26); the last day 21CF itself traded as FOXA is UNVERIFIED', 'UNVERIFIED'),

    ('DO01', 'DELISTED_OTHER', (('SUNE', None, '2016-04-21'),), 'SunEdison (NYSE) Chapter 11; NYSE suspended trading '
     'immediately 2016-04-21 (ICE notice)', 'WEB_CHECKED'),
    ('DO02', 'DELISTED_OTHER', (('BTU', None, '2016-04-13'), ('BTU', '2017-04-04', None)), 'Peabody Energy (NYSE) Chapter 11; '
     'NYSE suspended trading immediately 2016-04-13 (ICE notice); old shares OTC, cancelled at emergence; reorganized common '
     'began trading on NYSE as BTU 2017-04-04 (SEC 424B5): same symbol, new equity, about one year apart', 'WEB_CHECKED'),
    ('DO03', 'DELISTED_OTHER', (('SHLD', None, '2018-10-24'),), 'Sears Holdings (Nasdaq) Chapter 11 2018-10-15; delisted '
     'from Nasdaq effective 2018-10-24, then OTC as SHLDQ (Cboe circular IC12-017)', 'WEB_CHECKED'),
    ('DO04', 'DELISTED_OTHER', (('WIN', None, '2019-03-06'),), 'Windstream Holdings (Nasdaq) Chapter 11 2019-02-25; '
     'suspended and removed from Nasdaq 2019-03-06 (company 10-K)', 'WEB_CHECKED'),

    ('TC01', 'TICKER_CHANGE', (('PCLN', None, '2018-02-27'), ('BKNG', '2018-02-27', None)), 'The Priceline Group renamed '
     'Booking Holdings; Nasdaq symbol PCLN -> BKNG effective 2018-02-27 (one week after T2018)', 'RECALL'),
    ('TC02', 'TICKER_CHANGE', (('YHOO', None, '2017-06-19'), ('AABA', '2017-06-19', None)), 'Yahoo! Inc. sold its operating '
     'business to Verizon (closed 2017-06-13) and became Altaba, a registered closed-end investment company (security type '
     'change); YHOO traded through 2017-06-16, AABA from 2017-06-19 (company releases)', 'WEB_CHECKED'),
    ('TC03', 'TICKER_CHANGE', (('DPS', None, '2018-07-10'), ('KDP', '2018-07-10', None)), 'Dr Pepper Snapple Group combined '
     'with Keurig Green Mountain (closed 2018-07-09) and became Keurig Dr Pepper; NYSE symbol DPS -> KDP from 2018-07-10',
     'RECALL'),
    ('TC04', 'TICKER_CHANGE', (('VRX', None, '2018-07-16'), ('BHC', '2018-07-16', None)), 'Valeant Pharmaceuticals '
     'International renamed Bausch Health Companies 2018-07-13; NYSE/TSX symbol BHC from 2018-07-16 (company release)',
     'WEB_CHECKED'),
    ('TC05', 'TICKER_CHANGE', (('FB', None, '2022-06-09'), ('META', '2022-06-09', None)), 'Facebook / Meta Platforms; Nasdaq '
     'symbol FB -> META 2022-06-09, after the window: are window bars filed under the historical or the current symbol '
     '(Alpaca market data FAQ example)', 'WEB_CHECKED'),

    ('MC01', 'MULTI_CLASS', (('GOOGL', None, None),), 'Alphabet class A (Nasdaq), listed throughout', 'RECALL'),
    ('MC02', 'MULTI_CLASS', (('GOOG', None, None),), 'Alphabet class C (Nasdaq), listed throughout', 'RECALL'),
    ('MC03', 'MULTI_CLASS', (('BRK.A', None, None),), 'Berkshire Hathaway class A (NYSE), listed throughout; the dotted '
     'symbol form at Alpaca is UNVERIFIED', 'UNVERIFIED'),
    ('MC04', 'MULTI_CLASS', (('BRK.B', None, None),), 'Berkshire Hathaway class B (NYSE), listed throughout; the dotted '
     'symbol form at Alpaca is UNVERIFIED', 'UNVERIFIED'),
    ('MC05', 'MULTI_CLASS', (('UA', None, '2016-12-07'), ('UAA', '2016-12-07', None)), 'Under Armour class A (NYSE): symbol '
     'UA until the start of trading 2016-12-07, then UAA (company release)', 'WEB_CHECKED'),
    ('MC06', 'MULTI_CLASS', (('UA.C', '2016-04-08', '2016-12-07'), ('UA', '2016-12-07', None)), 'Under Armour class C (NYSE): '
     'distributed on or about 2016-04-07 and traded as UA.C (first trading day 2016-04-08 UNVERIFIED), symbol UA from '
     '2016-12-07; so UA means class A before 2016-12-07 and class C after (in-window symbol swap)', 'UNVERIFIED'),

    ('AD01', 'ADR', (('BABA', None, None),), 'Alibaba Group ADS (NYSE), listed throughout', 'RECALL'),
    ('AD02', 'ADR', (('TSM', None, None),), 'Taiwan Semiconductor Manufacturing ADS (NYSE), listed throughout', 'RECALL'),
    ('AD03', 'ADR', (('SHPG', None, '2019-01-08'),), 'Shire plc ADS (Nasdaq) acquired by Takeda; scheme effective 2019-01-08 '
     '(Nasdaq trader notice ECA2018-236)', 'WEB_CHECKED'),

    ('RE01', 'REIT', (('O', None, None),), 'Realty Income (NYSE), equity REIT, listed throughout', 'RECALL'),
    ('RE02', 'REIT', (('PLD', None, None),), 'Prologis (NYSE), equity REIT, listed throughout', 'RECALL'),
    ('RE03', 'REIT', (('DCT', None, '2018-08-22'),), 'DCT Industrial Trust (NYSE) acquired by Prologis (all stock); '
     'completed 2018-08-22 (Prologis release)', 'WEB_CHECKED'),

    ('SC01', 'SMALL_CAP_NEAR_THRESHOLD', (('KIRK', None, None),), "Kirkland's Inc. (Nasdaq), listed throughout; issuer value "
     'near the threshold UNVERIFIED', 'UNVERIFIED'),
    ('SC02', 'SMALL_CAP_NEAR_THRESHOLD', (('LCUT', None, None),), 'Lifetime Brands (Nasdaq), listed throughout; issuer value '
     'near the threshold UNVERIFIED', 'UNVERIFIED'),
    ('SC03', 'SMALL_CAP_NEAR_THRESHOLD', (('BGFV', None, None),), 'Big 5 Sporting Goods (Nasdaq), listed throughout; issuer '
     'value near the threshold UNVERIFIED', 'UNVERIFIED'),
    ('SC04', 'SMALL_CAP_NEAR_THRESHOLD', (('RT', None, '2017-12-21'),), 'Ruby Tuesday (NYSE) acquired by NRD Capital; closed '
     '2017-12-21 (GlobeNewswire release); issuer value near the threshold UNVERIFIED', 'UNVERIFIED'),

    ('IP01', 'IPO_IN_WINDOW', (('TWLO', '2016-06-23', None),), 'Twilio (NYSE) IPO, first trading day 2016-06-23', 'RECALL'),
    ('IP02', 'IPO_IN_WINDOW', (('SNAP', '2017-03-02', None),), 'Snap Inc. class A (NYSE) IPO, first trading day 2017-03-02 '
     '(non-voting class, the only listed one)', 'RECALL'),
    ('IP03', 'IPO_IN_WINDOW', (('DBX', '2018-03-23', None),), 'Dropbox (Nasdaq) IPO, first trading day 2018-03-23', 'RECALL'),
    ('IP04', 'IPO_IN_WINDOW', (('SPOT', '2018-04-03', None),), 'Spotify Technology (NYSE) direct listing of ordinary shares '
     '(not an ADR), first trading day 2018-04-03', 'RECALL'),
    ('IP05', 'IPO_IN_WINDOW', (('LYFT', '2019-03-29', None),), 'Lyft class A (Nasdaq) IPO, first trading day 2019-03-29 = '
     'the last session of the window', 'RECALL'),
)
# Other issuers that use a sample symbol (symbol reuse). They explain RAW bars of that symbol; they are never a sample
# security. (symbol, first, end, note)
OTHER_ISSUER_LEGS = (
    ('FOXA', '2019-03-19', None, 'Fox Corporation class A (new issuer), regular-way from 2019-03-19'),
    ('DOW', '2019-04-02', None, 'Dow Inc. (new issuer), regular-way from 2019-04-02 (after the window)'),
)
# Mapped requests (asof = a date): (sid, symbol, asof, expectation). LINEAGE: the security's own legs; OTHER_ISSUER: the
# reusing issuer's legs, so bars of the sample security under today's mapping count as outside.
MAPPED_REQUESTS = (
    ('TC01', 'PCLN', '2018-02-20', 'LINEAGE'), ('TC01', 'BKNG', CURRENT_ASOF, 'LINEAGE'),
    ('TC02', 'YHOO', '2017-02-21', 'LINEAGE'),
    ('TC03', 'DPS', '2018-02-20', 'LINEAGE'), ('TC03', 'KDP', CURRENT_ASOF, 'LINEAGE'),
    ('TC04', 'VRX', '2018-02-20', 'LINEAGE'), ('TC04', 'BHC', CURRENT_ASOF, 'LINEAGE'),
    ('TC05', 'FB', '2018-02-20', 'LINEAGE'), ('TC05', 'META', CURRENT_ASOF, 'LINEAGE'),
    ('MC05', 'UA', '2016-02-16', 'LINEAGE'), ('MC05', 'UAA', CURRENT_ASOF, 'LINEAGE'),
    ('MC06', 'UA', '2018-02-20', 'LINEAGE'), ('MC06', 'UA', CURRENT_ASOF, 'LINEAGE'),
    ('DA03', 'DOW', '2017-02-21', 'LINEAGE'), ('DA03', 'DOW', CURRENT_ASOF, 'OTHER_ISSUER'),
    ('DA07', 'FOXA', '2018-02-20', 'LINEAGE'), ('DA07', 'FOXA', CURRENT_ASOF, 'OTHER_ISSUER'),
    ('DO02', 'BTU', '2016-02-16', 'LINEAGE'), ('DO02', 'BTU', '2018-02-20', 'LINEAGE'), ('DO02', 'BTU', CURRENT_ASOF, 'LINEAGE'),
)
CLASS_PAIRS = (('GOOGL', 'GOOG'), ('BRK.A', 'BRK.B'), ('UAA', 'UA'))
CONTROL_SYMBOLS = ('AAPL', 'MSFT', 'SPY')   # union of their bar days = the reference session list for gap checks

# ---- Alpaca route and client limits ------------------------------------------------------------------------------------
ALPACA_HOST = 'data.alpaca.markets'
KEY_ENV, SECRET_ENV = 'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY'
SLEEP_S = 0.6                  # fixed pause before every request, retries included: <= 100 requests per minute
BACKOFF_S = (2.0, 6.0)         # 5xx and network errors: at most two retries
BACKOFF_429_S = (10.0, 30.0, 60.0)
RETRY_AFTER_MAX_S = 60.0
STOP_AFTER_429 = 8             # 429s in the whole run
TIMEOUT_S = 30
MAX_REQUESTS = 150             # every HTTP attempt counts; the plan needs one page per series (66)
MAX_PAGES = 5                  # per series (one page holds 10000 bars; the window has about 815 sessions)
WALL_CLOCK_S = 12 * 60
PAGE_CAP = 8 * 1024 * 1024
CHUNK = 64 * 1024
TOLERANCE = timedelta(days=4)  # around a leg boundary, bars are not called outside

# ---- private raw store -------------------------------------------------------------------------------------------------
RAW_REPO = 'kco994553-star/investment-system1-raw'
RAW_TOKEN_ENV = 'RAW_REPO_TOKEN'
TAG_PREFIX = 'alpaca-sample-v1-'
GH_API = raw_store_release.API
GH_UPLOADS = raw_store_release.UPLOADS
MANIFEST_SCHEMA = 'alpaca-sample-v1-manifest/1'
RELEASE_BODY = ('One-time Alpaca SIP small-sample raw daily bars for EXP-STOCK-INDICATOR-DECILES-v1 (owner decision '
                '2026-11-01 item 2). Private. Alpaca terms: personal, non-commercial use; never publish. Exact response bytes '
                'with a sha256 manifest.')
ZIP_TIME = (2026, 11, 1, 0, 0, 0)

STOP_REASONS = ('NONE', 'REQUEST_CAP', 'WALL_CLOCK', 'AUTH_REJECTED', 'HTTP429_REPEATED', 'UNEXPECTED')
_SYMBOL = re.compile(r'[A-Z]{1,5}(?:\.[A-Z])?')
_PATH = re.compile(r'/v2/stocks/([A-Z]{1,5}(?:\.[A-Z])?)/bars')
_PAGE_TOKEN = re.compile(r'[A-Za-z0-9+/=_-]{1,1024}')
_KEY = re.compile(r'[\x21-\x7e]{8,256}')
_CODE = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,47}')
_RUN_ID = re.compile(r'[0-9]{1,20}')
_TOKEN = re.compile(r'[A-Za-z0-9_.:+/,=-]{1,200}')


class Stop(Exception):
    """Ends the collection (budget, wall clock, refused key, repeated 429); the lines printed so far stay valid."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason if reason in STOP_REASONS else 'UNEXPECTED'


class FetchError(Exception):
    """One request failed; `code` is a fixed token (HTTP status, check name or exception class name)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code if isinstance(code, str) and _CODE.fullmatch(code) else 'OTHER'


class StorageError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code if isinstance(code, str) and _CODE.fullmatch(code) else 'OTHER'


# ---- sample ------------------------------------------------------------------------------------------------------------
def _day(value):
    return None if value is None else date.fromisoformat(value)


def load_sample(sample=SAMPLE, others=OTHER_ISSUER_LEGS, mapped=MAPPED_REQUESTS):
    """Validated securities {sid: {category, legs[(symbol, first, end)], note, check}} and symbol legs
    {symbol: [(first, end, owner)]} (owner = sid or 'OTHER'). Raises ValueError on any inconsistency."""
    securities, by_symbol = {}, {}
    for sid, category, legs, note, check in sample:
        if not re.fullmatch(r'[A-Z]{2}[0-9]{2}', sid) or sid in securities or category not in CATEGORIES or check not in CHECKS:
            raise ValueError('sample_entry')
        if not isinstance(note, str) or not note or not legs:
            raise ValueError('sample_note')
        parsed, previous_end = [], None
        for i, (symbol, first, end) in enumerate(legs):
            first, end = _day(first), _day(end)
            if not _SYMBOL.fullmatch(symbol) or (first and end and first >= end):
                raise ValueError('sample_leg')
            if i and (previous_end is None or first is None or first < previous_end):
                raise ValueError('sample_leg_order')
            parsed.append((symbol, first, end))
            by_symbol.setdefault(symbol, []).append((first, end, sid))
            previous_end = end
        if not clip((f, e) for _, f, e in parsed):   # a leg may lie after the window (FB -> META), the security may not
            raise ValueError('sample_outside_window')
        securities[sid] = {'category': category, 'legs': tuple(parsed), 'note': note, 'check': check}
    for symbol, first, end, note in others:
        if symbol not in by_symbol or not note:
            raise ValueError('other_issuer')
        by_symbol[symbol].append((_day(first), _day(end), 'OTHER'))
    for symbol, legs in by_symbol.items():   # one symbol never means two securities on the same day
        legs.sort(key=lambda leg: leg[0] or date.min)
        for (a1, b1, _), (a2, _, _) in zip(legs, legs[1:]):
            if b1 is None or (a2 or date.min) < b1:
                raise ValueError('symbol_overlap')
    for sid, symbol, asof, expect in mapped:
        if sid not in securities or expect not in ('LINEAGE', 'OTHER_ISSUER') or not re.fullmatch(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}', asof):
            raise ValueError('mapped')
        if symbol not in {leg[0] for leg in securities[sid]['legs']}:
            raise ValueError('mapped_symbol')
        if expect == 'OTHER_ISSUER' and not any(o[0] == symbol for o in others):
            raise ValueError('mapped_other')
    return securities, by_symbol


def series_mode(asof):
    return 'RAW' if asof == '-' else 'ASOF_CURRENT' if asof == CURRENT_ASOF else 'ASOF_PIT'


def plan(securities=None, mapped=MAPPED_REQUESTS):
    """Request series in a fixed order: one RAW series per symbol (sample order), then the mapped series."""
    securities = securities if securities is not None else load_sample()[0]
    series, raw = [], {}
    for sid, info in securities.items():
        for symbol, _, _ in info['legs']:
            if symbol in raw:
                if sid not in raw[symbol]['sids']:
                    raw[symbol]['sids'].append(sid)
                continue
            raw[symbol] = {'id': 'RAW:' + symbol, 'symbol': symbol, 'asof': '-', 'mode': 'RAW', 'sids': [sid],
                           'expect': 'SYMBOL'}
            series.append(raw[symbol])
    for sid, symbol, asof, expect in mapped:
        series.append({'id': 'ASOF' + asof.replace('-', '') + ':' + symbol, 'symbol': symbol, 'asof': asof,
                       'mode': series_mode(asof), 'sids': [sid], 'expect': expect})
    if len({s['id'] for s in series}) != len(series):
        raise ValueError('series_id')
    return series


# ---- routes ----------------------------------------------------------------------------------------------------------
def build_url(symbol, asof, page_token=None):
    params = [('timeframe', '1Day'), ('start', START_PARAM), ('end', END_PARAM), ('adjustment', 'raw'), ('feed', 'sip'),
              ('limit', '10000'), ('sort', 'asc'), ('asof', asof)]
    if page_token is not None:
        params.append(('page_token', page_token))
    return f'https://{ALPACA_HOST}/v2/stocks/{symbol}/bars?' + urllib.parse.urlencode(params)


def checked_alpaca_url(url, allowed):
    """Exact allow-list: https, exactly data.alpaca.markets, /v2/stocks/<planned symbol>/bars, the fixed query with a planned
    asof and an optional well-formed page_token, and nothing else (the URL must equal its canonical form)."""
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        raise ValueError('URL_NOT_ALLOWED')
    parts = urllib.parse.urlsplit(url)
    match = _PATH.fullmatch(parts.path)
    if parts.scheme != 'https' or parts.netloc != ALPACA_HOST or parts.fragment or match is None:
        raise ValueError('URL_NOT_ALLOWED')
    try:
        query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise ValueError('URL_NOT_ALLOWED') from None
    values = dict(query)
    token = values.get('page_token')
    if (len(values) != len(query) or (match.group(1), values.get('asof')) not in allowed
            or (token is not None and not _PAGE_TOKEN.fullmatch(token))
            or url != build_url(match.group(1), values['asof'], token)):
        raise ValueError('URL_NOT_ALLOWED')
    return url


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FetchError('REDIRECT_REJECTED')


def build_opener():
    return urllib.request.build_opener(_RejectRedirects())


def valid_key(value):
    return isinstance(value, str) and _KEY.fullmatch(value) is not None


# ---- Alpaca client -----------------------------------------------------------------------------------------------------
class AlpacaClient:
    def __init__(self, key_id, secret, allowed, *, opener=None, sleep=time.sleep, clock=time.monotonic):
        self._headers = {'APCA-API-KEY-ID': key_id, 'APCA-API-SECRET-KEY': secret, 'Accept': 'application/json'}
        self._allowed = frozenset(allowed)
        self._opener = opener if opener is not None else build_opener()
        self._sleep, self._clock = sleep, clock
        self._start = clock()
        self.counts = Counter()

    def elapsed(self):
        return self._clock() - self._start

    def _deadline(self):
        if self.elapsed() >= WALL_CLOCK_S:
            raise Stop('WALL_CLOCK')

    def get(self, url):
        """Body of one allow-listed GET. 429 / 5xx / network errors are retried within fixed budgets; 401 / 403 stop."""
        checked_alpaca_url(url, self._allowed)
        retries = Counter()
        while True:
            if self.counts['total'] >= MAX_REQUESTS:
                raise Stop('REQUEST_CAP')
            self._deadline()
            self._sleep(SLEEP_S)
            self.counts['total'] += 1
            try:
                request = urllib.request.Request(url, headers=self._headers)
                with self._opener.open(request, timeout=TIMEOUT_S) as response:
                    return self._read(response)
            except urllib.error.HTTPError as exc:
                status = exc.code if type(exc.code) is int else 0
                retry_after = exc.headers.get('Retry-After') if exc.headers is not None else None
                exc.close()
                if status in (401, 403):
                    self.counts[f'http{status}'] += 1
                    raise Stop('AUTH_REJECTED') from None
                if status == 429:
                    self.counts['http429'] += 1
                    if self.counts['http429'] >= STOP_AFTER_429:
                        raise Stop('HTTP429_REPEATED') from None
                    if retries['429'] >= len(BACKOFF_429_S):
                        raise FetchError('HTTP429') from None
                    wait = BACKOFF_429_S[retries['429']]
                    if isinstance(retry_after, str) and retry_after.strip().isdigit():
                        wait = max(wait, min(float(retry_after.strip()), RETRY_AFTER_MAX_S))
                    retries['429'] += 1
                elif 500 <= status <= 599:
                    self.counts['http5xx'] += 1
                    if retries['5xx'] >= len(BACKOFF_S):
                        raise FetchError(f'HTTP{status}') from None
                    wait = BACKOFF_S[retries['5xx']]
                    retries['5xx'] += 1
                else:
                    self.counts[f'http{status}' if status in (400, 404, 422) else 'http_other'] += 1
                    raise FetchError(f'HTTP{status}' if 100 <= status <= 599 else 'HTTP_OTHER') from None
            except FetchError:
                raise
            except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
                self.counts['network'] += 1
                if retries['net'] >= len(BACKOFF_S):
                    raise FetchError(type(exc).__name__) from None
                wait = BACKOFF_S[retries['net']]
                retries['net'] += 1
            self.counts['retries'] += 1
            self._sleep(wait)

    def _read(self, response):
        encoding = (response.headers.get('Content-Encoding') or 'identity').strip().lower()
        if encoding != 'identity':
            raise FetchError('ENCODING_NOT_SUPPORTED')
        parts, size = [], 0
        while True:
            self._deadline()
            chunk = response.read(CHUNK)
            if not chunk:
                return b''.join(parts)
            size += len(chunk)
            if size > PAGE_CAP:
                raise FetchError('SIZE_CAP')
            parts.append(chunk)


# ---- parsing (prices stay in RAM) ----------------------------------------------------------------------------------------
def _price(value):
    """A positive finite number, else None (never 0: NA is not filled)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def parse_page(body, symbol, *, mapped=False):
    """[(New York day, (o, h, l, c))], next_page_token, echo ('SAME' or, for a mapped request only, 'OTHER' when the answer
    names another symbol). Raises ValueError(<fixed code>)."""
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('JSON') from None
    if not isinstance(data, dict):
        raise ValueError('SCHEMA')
    echo = data.get('symbol')
    if not isinstance(echo, str) or not _SYMBOL.fullmatch(echo) or (echo != symbol and not mapped):
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
        if not WINDOW_START <= day <= WINDOW_END:
            raise ValueError('OUT_OF_WINDOW')
        rows.append((day, tuple(_price(bar.get(k)) for k in ('o', 'h', 'l', 'c'))))
    return rows, token, 'SAME' if echo == symbol else 'OTHER'


def fetch_series(client, series):
    """{'status', 'bars', 'pages', 'echo'}: status DATA | NO_DATA | ERR_<code> | BAD_<code>; on any failure the bars are
    dropped (the raw pages are kept for the private store)."""
    bars, pages, token, seen, last, echoes = {}, [], None, set(), None, set()

    def failed(status):
        return {'status': status, 'bars': {}, 'pages': pages, 'echo': '-'}

    for _ in range(MAX_PAGES):
        try:
            body = client.get(build_url(series['symbol'], series['asof'], token))
        except FetchError as exc:
            return failed('ERR_' + exc.code)
        pages.append(body)
        try:
            rows, next_token, echo = parse_page(body, series['symbol'], mapped=series['asof'] != '-')
        except ValueError as exc:
            code = str(exc)
            return failed('BAD_' + (code if _CODE.fullmatch(code) else 'OTHER'))
        echoes.add(echo)
        for day, values in rows:
            if last is not None and day <= last:
                return failed('BAD_ORDER')
            bars[day], last = values, day
        if not next_token:
            return {'status': 'DATA' if bars else 'NO_DATA', 'bars': bars, 'pages': pages,
                    'echo': 'OTHER' if 'OTHER' in echoes else 'SAME'}
        if next_token in seen or not rows:
            return failed('BAD_PAGINATION')
        seen.add(next_token)
        token = next_token
    return failed('BAD_PAGE_CAP')


def collect(client, series_plan):
    results, stopped = {}, 'NONE'
    try:
        for series in series_plan:
            results[series['id']] = fetch_series(client, series)
    except Stop as stop:
        stopped = stop.reason
    except Exception:  # noqa: BLE001 - a bug must not hide the results gathered so far; nothing of it is printed
        stopped = 'UNEXPECTED'
    for series in series_plan:
        results.setdefault(series['id'], {'status': 'NOT_RUN', 'bars': {}, 'pages': [], 'echo': '-'})
    return results, stopped


# ---- evaluation ----------------------------------------------------------------------------------------------------------
def clip(legs):
    """Half-open [a, b) spans inside the window from (first, end) pairs."""
    spans = []
    for first, end in legs:
        a, b = max(first or WINDOW_START, WINDOW_START), min(end or WINDOW_AFTER, WINDOW_AFTER)
        if a < b:
            spans.append((a, b))
    return sorted(spans)


def inside(day, spans):
    return any(a <= day < b for a, b in spans)


def series_spans(series, securities, by_symbol):
    if series['expect'] == 'SYMBOL':
        return clip((first, end) for first, end, _ in by_symbol[series['symbol']])
    if series['expect'] == 'OTHER_ISSUER':
        return clip((first, end) for first, end, owner in by_symbol[series['symbol']] if owner == 'OTHER')
    return clip((first, end) for _, first, end in securities[series['sids'][0]]['legs'])


def point_state(result, spans, day, field):
    """OK | MISS | BAD (bar without a valid value) | UNEXP (bar where none is expected) | - | ERR."""
    if result['status'] not in ('DATA', 'NO_DATA'):
        return 'ERR'
    bar = result['bars'].get(day)
    if not inside(day, spans):
        return 'UNEXP' if bar is not None else '-'
    if bar is None:
        return 'MISS'
    return 'OK' if bar[field] is not None else 'BAD'


def monthend_state(states):
    if 'ERR' in states:
        return 'ERR'
    expected = [s for s in states if s in ('OK', 'MISS', 'BAD')]
    ok = sum(s == 'OK' for s in expected)
    base = 'NA' if not expected else 'FULL' if ok == len(expected) else 'NONE' if ok == 0 else 'PARTIAL'
    return base + ('+UNEXP' if 'UNEXP' in states else '')


def fit(days, spans):
    """How the bar days sit against the expected spans: NO_DATA, MATCH (every span has bars, none outside), PARTIAL (a span
    without bars), +OUTSIDE (bars more than TOLERANCE away from every span); NONE_EXPECTED / OUTSIDE_ONLY without spans."""
    if not spans:
        return 'NONE_EXPECTED' if not days else 'OUTSIDE_ONLY'
    if not days:
        return 'NO_DATA'
    covered = all(any(a <= d < b for d in days) for a, b in spans)
    outside = any(not any(a - TOLERANCE <= d < b + TOLERANCE for a, b in spans) for d in days)
    return ('MATCH' if covered else 'PARTIAL') + ('+OUTSIDE' if outside else '')


def gaps(days, spans, reference):
    """NONE | SOME | NA: reference sessions missing between the first and last bar of each span."""
    if not reference or not days:
        return 'NA'
    for a, b in spans:
        own = sorted(d for d in days if a <= d < b)
        if own and any(r not in days for r in reference if own[0] <= r <= own[-1]):
            return 'SOME'
    return 'NONE'


def edge(days, which):
    if not days:
        return 'NONE'
    if which == 'first':
        return 'AT_START' if min(days) == FIRST_SESSION else 'LATER'
    return 'AT_END' if max(days) == LAST_SESSION else 'EARLIER'


def overlap(a_bars, b_bars):
    common = sorted(set(a_bars) & set(b_bars))
    if not common:
        return 'NO_OVERLAP'
    same = sum(a_bars[d] == b_bars[d] for d in common)
    return 'SAME_BARS' if same == len(common) else 'DIFFERENT_BARS' if same == 0 else 'PARTLY_SAME'


def security_state(info, raw, by_symbol, day, field):
    """Primary engine view: the RAW series of the security's point-in-time symbol on `day`."""
    for symbol, first, end in info['legs']:
        if (first or date.min) <= day < (end or date.max):
            result = raw[symbol]
            if result['status'] not in ('DATA', 'NO_DATA'):
                return 'ERR'
            bar = result['bars'].get(day)
            return 'MISS' if bar is None else 'OK' if bar[field] is not None else 'BAD'
    for symbol in {leg[0] for leg in info['legs']}:
        result = raw[symbol]
        if day in result['bars'] and not inside(day, clip((f, e) for f, e, _ in by_symbol[symbol])):
            return 'UNEXP'
    return '-'


def events(sid, info, raw, by_symbol):
    """(symbol, kind, event day, bar_vs_event_days|None|'ERR') for every leg boundary inside the window. The bar is the
    symbol's last RAW bar before the next use of the symbol (END / RENAME_OUT) or its first RAW bar after the previous use
    (START / RENAME_IN / RELIST)."""
    out, legs = [], info['legs']
    for i, (symbol, first, end) in enumerate(legs):
        result = raw[symbol]
        days = sorted(result['bars']) if result['status'] in ('DATA', 'NO_DATA') else None
        others = [(f, e) for f, e, owner in by_symbol[symbol] if (f, e) != (first, end) or owner != sid]
        if first is not None and WINDOW_START < first <= WINDOW_END:
            kind = 'START' if i == 0 else 'RELIST' if legs[i - 1][0] == symbol else 'RENAME_IN'
            low = max([e for f, e in others if e is not None and e <= first] + [WINDOW_START])
            found = None if days is None else next((d for d in days if d >= low), None)
            out.append((symbol, kind, first, 'ERR' if days is None else None if found is None else (found - first).days))
        if end is not None and WINDOW_START < end <= WINDOW_END:
            kind = 'RENAME_OUT' if i + 1 < len(legs) and legs[i + 1][0] != symbol else 'END'
            high = min([f for f, e in others if f is not None and f >= end] + [WINDOW_AFTER])
            found = None if days is None else next((d for d in reversed(days) if d < high), None)
            out.append((symbol, kind, end, 'ERR' if days is None else None if found is None else (found - end).days))
    return out


def lineage_code(info, raw, by_symbol):
    """RAW behaviour of a security with more than one leg: PIT_SYMBOLS (each symbol has bars only in its own legs),
    CURRENT_SYMBOL_ONLY (only the last symbol has bars, also before its first day), MISSING_SYMBOL, OVERLAPPING_SYMBOLS,
    ERR, NO_DATA."""
    symbols = list(dict.fromkeys(leg[0] for leg in info['legs']))
    if any(raw[s]['status'] not in ('DATA', 'NO_DATA') for s in symbols):
        return 'ERR'
    fits = {s: fit(set(raw[s]['bars']), clip((f, e) for f, e, _ in by_symbol[s])) for s in symbols}
    own = {s: clip((f, e) for sym, f, e in info['legs'] if sym == s) for s in symbols}
    if all(not raw[s]['bars'] for s in symbols):
        return 'NO_DATA'
    if all(f in ('MATCH', 'NONE_EXPECTED') for f in fits.values()):
        return 'PIT_SYMBOLS'
    last = symbols[-1]
    last_start = own[last][0][0] if own[last] else WINDOW_AFTER   # a rename after the window: every window day is before
    if all(not raw[s]['bars'] for s in symbols[:-1]) and any(d < last_start for d in raw[last]['bars']):
        return 'CURRENT_SYMBOL_ONLY'
    if any(f.startswith('PARTIAL') or f == 'NO_DATA' for f in fits.values()):
        return 'MISSING_SYMBOL'
    return 'OVERLAPPING_SYMBOLS'


def summarize(securities, by_symbol, series_plan, results):
    """Fixed summary lines (categories, counts, public dates, day differences). Never a price, volume or key."""
    raw = {s['symbol']: results[s['id']] for s in series_plan if s['mode'] == 'RAW'}
    reference = set()
    for symbol in CONTROL_SYMBOLS:
        reference |= set(raw[symbol]['bars'])
    lines = []
    for series in series_plan:
        result = results[series['id']]
        spans = series_spans(series, securities, by_symbol)
        days = set(result['bars'])
        ok = result['status'] in ('DATA', 'NO_DATA')
        t = ','.join(point_state(result, spans, d, 0) for _, d in T_DAYS)
        s = ','.join(point_state(result, spans, d, 3) for _, d in S_DAYS)
        me = monthend_state([point_state(result, spans, d, 3) for d in MONTH_ENDS])
        cats = sorted({securities[sid]['category'] for sid in series['sids']})
        lines.append(f"ALPSAMPLE_SERIES id={series['id']} sid={'+'.join(series['sids'])} cat={'+'.join(cats)} "
                     f"mode={series['mode']} expect={series['expect']} status={result['status']} "
                     f"fit={fit(days, spans) if ok else 'ERR'} first={edge(days, 'first') if ok else 'ERR'} "
                     f"last={edge(days, 'last') if ok else 'ERR'} gaps={gaps(days, spans, reference) if ok else 'ERR'} "
                     f"t_open={t} s_close={s} monthend={me} echo={result['echo']}")
    for sid, info in securities.items():
        for symbol, kind, day, diff in events(sid, info, raw, by_symbol):
            shown = 'NONE' if diff is None else diff if isinstance(diff, str) else str(int(diff))
            lines.append(f"ALPSAMPLE_EVENT sid={sid} cat={info['category']} sym={symbol} event={kind} "
                         f"event_day={day.isoformat()} bar_vs_event_days={shown}")
    mapped = {}
    for series in series_plan:
        if series['mode'] != 'RAW':
            result = results[series['id']]
            code = fit(set(result['bars']), series_spans(series, securities, by_symbol)) \
                if result['status'] in ('DATA', 'NO_DATA') else 'ERR'
            mapped.setdefault((series['sids'][0], series['mode']), []).append(code)
    for sid, info in securities.items():
        symbols = list(dict.fromkeys(leg[0] for leg in info['legs']))
        if len(info['legs']) < 2 and not any(key[0] == sid for key in mapped):
            continue
        pairs = list(zip(symbols, symbols[1:]))
        ov = ','.join(overlap(raw[a]['bars'], raw[b]['bars']) for a, b in pairs) or '-'
        lines.append(f"ALPSAMPLE_LINEAGE sid={sid} cat={info['category']} "
                     f"raw={lineage_code(info, raw, by_symbol) if len(info['legs']) > 1 else 'SINGLE_LEG'} "
                     f"asof_pit={','.join(mapped.get((sid, 'ASOF_PIT'), ['-']))} "
                     f"asof_current={','.join(mapped.get((sid, 'ASOF_CURRENT'), ['-']))} overlap={ov}")
    for a, b in CLASS_PAIRS:
        both = raw[a]['status'] in ('DATA', 'NO_DATA') and raw[b]['status'] in ('DATA', 'NO_DATA')
        lines.append(f"ALPSAMPLE_CLASSES pair={a}+{b} overlap={overlap(raw[a]['bars'], raw[b]['bars']) if both else 'ERR'}")
    checkpoints = [(f'T{y}', d, 0) for y, d in T_DAYS] + [(f'S{y}', d, 3) for y, d in S_DAYS] + \
                  [('ME' + d.strftime('%Y%m'), d, 3) for d in MONTH_ENDS]
    per_security = {sid: {cp: security_state(info, raw, by_symbol, d, f) for cp, d, f in checkpoints}
                    for sid, info in securities.items()}
    for category in CATEGORIES:
        sids = [sid for sid, info in securities.items() if info['category'] == category]
        symbols = sorted({leg[0] for sid in sids for leg in securities[sid]['legs']})
        status = Counter('DATA' if raw[s]['status'] == 'DATA' else 'NO_DATA' if raw[s]['status'] == 'NO_DATA' else 'ERR'
                         for s in symbols)
        count = Counter()
        for sid in sids:
            states = per_security[sid]
            for cp, value in states.items():
                group = cp[0] if cp[0] in 'TS' else 'M'
                count[group + '_exp'] += value in ('OK', 'MISS', 'BAD', 'ERR')
                count[group + '_ok'] += value == 'OK'
                count[group + '_unexp'] += value == 'UNEXP'
            count['complete'] += all(v in ('OK', '-') for v in states.values())
            legs_gaps = [gaps(set(raw[sym]['bars']), clip([(f, e)]), reference) for sym, f, e in securities[sid]['legs']
                         if raw[sym]['status'] in ('DATA', 'NO_DATA') and clip([(f, e)])]
            judged = [g for g in legs_gaps if g != 'NA']
            count['gap_judged'] += bool(judged)
            count['gapless'] += bool(judged) and all(g == 'NONE' for g in judged)
        lines.append(f"ALPSAMPLE_CATEGORY cat={category} securities={len(sids)} symbols={len(symbols)} "
                     f"symbols_with_data={status['DATA']} symbols_no_data={status['NO_DATA']} symbols_error={status['ERR']} "
                     f"t_open={count['T_ok']}/{count['T_exp']} t_unexpected={count['T_unexp']} "
                     f"s_close={count['S_ok']}/{count['S_exp']} s_unexpected={count['S_unexp']} "
                     f"monthend={count['M_ok']}/{count['M_exp']} monthend_unexpected={count['M_unexp']} "
                     f"complete={count['complete']} gapless={count['gapless']}/{count['gap_judged']}")
    for cp, day, field in checkpoints:
        values = Counter(per_security[sid][cp] for sid in securities)
        expected = values['OK'] + values['MISS'] + values['BAD'] + values['ERR']
        lines.append(f"ALPSAMPLE_CHECKPOINT cp={cp} day={day.isoformat()} field={'open' if field == 0 else 'close'} "
                     f"expected={expected} ok={values['OK']} missing={values['MISS']} bad={values['BAD']} "
                     f"error={values['ERR']} unexpected={values['UNEXP']}")
    return [checked_line(line) for line in lines]


def checked_line(line):
    """Every printed line: fixed prefix, key=value tokens from a closed character set, no decimal number."""
    words = line.split(' ')
    if not re.fullmatch(r'ALPSAMPLE_[A-Z_]+', words[0]) or re.search(r'[0-9]\.[0-9]', line):
        raise ValueError('line')
    for word in words[1:]:
        key, sep, value = word.partition('=')
        if not sep or not re.fullmatch(r'[a-z][a-z0-9_]*', key) or not _TOKEN.fullmatch(value):
            raise ValueError('line')
    return line


# ---- private raw store (create-only) -------------------------------------------------------------------------------------
def release_tag(run_id):
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise StorageError('RUN_ID_INVALID')
    return TAG_PREFIX + run_id


class RawStore:
    """The only GitHub routes this tool may call, for one fixed tag. `call` has raw_store_release.http's signature."""

    def __init__(self, tag, call=None):
        if not re.fullmatch(re.escape(TAG_PREFIX) + r'[0-9]{1,20}', tag or ''):
            raise StorageError('TAG_INVALID')
        self.tag = tag
        self._call = call or raw_store_release.http
        self._repo = f'{GH_API}/repos/{RAW_REPO}'
        self._asset = re.compile(re.escape(f'{GH_UPLOADS}/repos/{RAW_REPO}/releases/') + r'[1-9][0-9]{0,15}/assets\?name='
                                 + re.escape(tag) + r'\.zip(?:\.sha256)?')
        self._download = re.compile(re.escape(f'{self._repo}/releases/assets/') + r'[1-9][0-9]{0,15}')

    def allowed(self, method, url):
        return ((method, url) in {('GET', self._repo), ('GET', f'{self._repo}/releases/tags/{self.tag}'),
                                  ('POST', f'{self._repo}/releases')}
                or (method == 'POST' and self._asset.fullmatch(url) is not None)
                or (method == 'GET' and self._download.fullmatch(url) is not None))

    def http(self, method, url, **kwargs):
        if not self.allowed(method, url):
            raise StorageError('ROUTE_NOT_ALLOWED')
        try:
            return self._call(method, url, **kwargs)
        except raw_store_release.ReleaseError:
            raise StorageError('TOKEN_MISSING') from None
        except (OSError, http.client.HTTPException, ValueError):
            raise StorageError('NETWORK') from None

    def _tag_absent(self):
        status, _, _ = self.http('GET', f'{self._repo}/releases/tags/{self.tag}')
        if status == 200:
            raise StorageError('RELEASE_TAG_EXISTS')
        if status != 404:
            raise StorageError('RELEASE_LOOKUP_FAILED')

    def preflight(self):
        """Before any Alpaca request: the raw repository answers private and the run's tag does not exist."""
        status, _, body = self.http('GET', self._repo)
        try:
            private = status == 200 and json.loads(body).get('private') is True
        except (ValueError, AttributeError):
            private = False
        if not private:
            raise StorageError('PRIVATE_STORAGE_PREFLIGHT_FAILED')
        self._tag_absent()

    def store(self, archive):
        """Create the release (never reuse one), upload the zip and its .sha256, download the zip back and compare."""
        self._tag_absent()
        digest = hashlib.sha256(archive).hexdigest()
        payload = json.dumps({'tag_name': self.tag, 'name': self.tag, 'body': RELEASE_BODY, 'draft': False,
                              'prerelease': False}).encode()
        status, _, body = self.http('POST', f'{self._repo}/releases', data=payload,
                                    headers={'Content-Type': 'application/json'})
        release = _json_dict(body) if status == 201 else {}
        release_id = release.get('id')
        if type(release_id) is not int or release_id <= 0 or release.get('tag_name') != self.tag:
            raise StorageError('RELEASE_CREATE_FAILED')
        asset_id = None
        name = self.tag + '.zip'
        for asset, data, kind in ((name, archive, 'application/zip'),
                                  (name + '.sha256', f'{digest}  {name}\n'.encode(), 'text/plain')):
            url = f'{GH_UPLOADS}/repos/{RAW_REPO}/releases/{release_id}/assets?name={urllib.parse.quote(asset)}'
            status, _, body = self.http('POST', url, data=data, headers={'Content-Type': kind})
            if status != 201:
                raise StorageError('ASSET_UPLOAD_FAILED')
            if asset == name:
                asset_id = _json_dict(body).get('id')
        if type(asset_id) is not int or asset_id <= 0:
            raise StorageError('ASSET_UPLOAD_FAILED')
        status, headers, body = self.http('GET', f'{self._repo}/releases/assets/{asset_id}',
                                          headers={'Accept': 'application/octet-stream'})
        if status in (301, 302, 303, 307, 308):
            location = (headers or {}).get('Location') or (headers or {}).get('location') or ''
            parts = urllib.parse.urlsplit(location)
            if parts.scheme != 'https' or not (parts.hostname or '').endswith('.githubusercontent.com'):
                raise StorageError('ASSET_REDIRECT_INVALID')
            try:   # the signed download URL gets no token
                status, _, body = self._call('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False)
            except (OSError, http.client.HTTPException, ValueError):
                raise StorageError('NETWORK') from None
        if status != 200 or hashlib.sha256(body or b'').hexdigest() != digest:
            raise StorageError('ROUNDTRIP_MISMATCH')
        return digest


def _json_dict(body):
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def build_archive(securities, series_plan, results, lines, *, run_id, code_sha, stopped, created_at):
    """Deterministic zip (in RAM): manifest.json + raw/<series>/page-NN.json (exact response bytes)."""
    files, entries = [], []
    for series in series_plan:
        result = results[series['id']]
        pages = []
        for n, body in enumerate(result['pages']):
            path = f"raw/{series['id'].replace(':', '_')}/page-{n:02d}.json"
            files.append((path, body))
            pages.append({'file': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
        entries.append({'series': series['id'], 'symbol': series['symbol'], 'asof': series['asof'], 'mode': series['mode'],
                        'expect': series['expect'], 'sids': series['sids'], 'status': result['status'], 'pages': pages})
    manifest = {
        'schema': MANIFEST_SCHEMA, 'run_id': run_id, 'code_sha': code_sha, 'created_at': created_at, 'stopped': stopped,
        'source': {'endpoint': f'https://{ALPACA_HOST}/v2/stocks/{{symbol}}/bars', 'timeframe': '1Day', 'start': START_PARAM,
                   'end': END_PARAM, 'adjustment': 'raw', 'feed': 'sip', 'limit': 10000, 'sort': 'asc',
                   'terms': 'Alpaca market data: personal, non-commercial use; public posting needs prior written consent; '
                            'nothing from this archive is published'},
        'sample': [{'sid': sid, 'category': info['category'], 'check': info['check'], 'note': info['note'],
                    'legs': [[s, f.isoformat() if f else None, e.isoformat() if e else None] for s, f, e in info['legs']]}
                   for sid, info in securities.items()],
        'other_issuer_legs': [list(leg) for leg in OTHER_ISSUER_LEGS],
        'series': entries, 'summary_lines': lines,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, data in [('manifest.json', json.dumps(manifest, indent=1, sort_keys=True).encode())] + files:
            info = zipfile.ZipInfo(path, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, data)
    return buffer.getvalue(), len(files) + 1


# ---- run -----------------------------------------------------------------------------------------------------------------
def plan_lines(securities, series_plan):
    modes = Counter(s['mode'] for s in series_plan)
    lines = [f"ALPSAMPLE_PLAN securities={len(securities)} symbols={modes['RAW']} series={len(series_plan)} "
             f"raw={modes['RAW']} asof_pit={modes['ASOF_PIT']} asof_current={modes['ASOF_CURRENT']} "
             f"pages_expected={len(series_plan)} max_requests={MAX_REQUESTS} pace_ms={int(SLEEP_S * 1000)}"]
    for category in CATEGORIES:
        sids = [sid for sid, info in securities.items() if info['category'] == category]
        unverified = sum(securities[sid]['check'] == 'UNVERIFIED' for sid in sids)
        lines.append(f"ALPSAMPLE_PLAN_CATEGORY cat={category} securities={len(sids)} "
                     f"symbols={len({leg[0] for sid in sids for leg in securities[sid]['legs']})} unverified={unverified}")
    return [checked_line(line) for line in lines]


def stop_line(reason):
    return f'ALPSAMPLE_STOP reason={reason if _CODE.fullmatch(reason or "") else "OTHER"}'


def main(argv=None, *, environ=None, opener=None, github_call=None, sleep=time.sleep, clock=time.monotonic, out=None,
         now=None):
    environ = os.environ if environ is None else environ
    out = out if out is not None else (lambda line: print(line, flush=True))
    argv = sys.argv[1:] if argv is None else argv
    try:
        securities, by_symbol = load_sample()
        series_plan = plan(securities)
    except ValueError:
        out(stop_line('SAMPLE_INVALID'))
        return 2
    if argv == ['--plan']:
        for line in plan_lines(securities, series_plan):
            out(line)
        return 0
    if argv:
        out(stop_line('USAGE'))
        return 2
    if environ.get('GITHUB_ACTIONS') != 'true':
        out(stop_line('RUNNER_REQUIRED'))
        return 2
    key_id, secret = environ.get(KEY_ENV) or '', environ.get(SECRET_ENV) or ''
    if not key_id.strip() or not secret.strip():
        out(stop_line('ALPACA_KEYS_MISSING'))
        return 2
    if not valid_key(key_id) or not valid_key(secret):
        out(stop_line('ALPACA_KEYS_INVALID'))
        return 2
    if not (environ.get(RAW_TOKEN_ENV) or '').strip():
        out(stop_line('RAW_REPO_TOKEN_MISSING'))
        return 2
    try:
        run_id = environ.get('GITHUB_RUN_ID') or ''
        store = RawStore(release_tag(run_id), github_call)
        store.preflight()
    except StorageError as exc:
        out(stop_line(exc.code))
        return 2
    allowed = {(s['symbol'], s['asof']) for s in series_plan}
    client = AlpacaClient(key_id, secret, allowed, opener=opener, sleep=sleep, clock=clock)
    out(checked_line(f'ALPSAMPLE_START securities={len(securities)} symbols={sum(s["mode"] == "RAW" for s in series_plan)} '
                     f'series={len(series_plan)} categories={len(CATEGORIES)} window={WINDOW_START}..{WINDOW_END} '
                     f'feed=sip adjustment=raw timeframe=1Day max_requests={MAX_REQUESTS} pace_ms={int(SLEEP_S * 1000)} '
                     f'release={store.tag}'))
    results, stopped = collect(client, series_plan)
    try:
        lines = summarize(securities, by_symbol, series_plan, results)
    except Exception as exc:  # noqa: BLE001 - class name only; the raw pages are still stored below
        lines = [stop_line('SUMMARY_FAILED_' + type(exc).__name__)]
    for line in lines:
        out(line)
    c = client.counts
    out(checked_line(
        f"ALPSAMPLE_REQUESTS series={len(series_plan)} series_done="
        f"{sum(results[s['id']]['status'] != 'NOT_RUN' for s in series_plan)} total={c['total']} "
        f"pages={sum(len(r['pages']) for r in results.values())} retries={c['retries']} http400={c['http400']} "
        f"http401={c['http401']} http403={c['http403']} http404={c['http404']} http422={c['http422']} "
        f"http429={c['http429']} http5xx={c['http5xx']} http_other={c['http_other']} network={c['network']} "
        f"elapsed_s={int(client.elapsed())} stopped={stopped}"))
    sha = environ.get('GITHUB_SHA') or ''
    created = (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    archive, n_files = build_archive(securities, series_plan, results, lines, run_id=run_id,
                                     code_sha=sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None, stopped=stopped,
                                     created_at=created)
    for result in results.values():   # the prices leave RAM only inside the archive
        result['bars'] = {}
    try:
        store.store(archive)
    except StorageError as exc:
        out(f'ALPSAMPLE_STORAGE status=FAILED code={exc.code}')
        return 3
    out(checked_line(f'ALPSAMPLE_STORAGE status=STORED release={store.tag} files={n_files} roundtrip=SHA256_MATCH'))
    return 0 if stopped == 'NONE' else 3


if __name__ == '__main__':
    try:
        code = main()
    except (Exception, KeyboardInterrupt) as exc:
        name = type(exc).__name__
        print(f'ALPSAMPLE_STOP reason=UNEXPECTED class={name if _CODE.fullmatch(name) else "OTHER"}', flush=True)
        code = 1
    sys.exit(code)
