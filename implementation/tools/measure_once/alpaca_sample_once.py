"""ONE-TIME MEASUREMENT (owner decision 2026-11-01, item 2: "그다음 소표본 수집만 승인한다. 대량 수집은 그 결과를 본 뒤 정한다").
Not part of any pipeline. It runs once from .github/workflows/alpaca-sample-once.yml on the push to the run branch
claude/alpaca-sample-once-run. Research EXP-STOCK-INDICATOR-DECILES-v1 (settings doc sections 5, 6.2, 7).

Question: can Alpaca SIP daily bars supply what the annual-reselection engine needs for the whole historical U-A / U-B
candidate set? (a) the consolidated OPEN on each T (2016-02-16, 2017-02-21, 2018-02-20, 2019-02-19); (b) the CLOSE on each
S (2016-02-12, 2017-02-17, 2018-02-16, 2019-02-15); (c) month-end closes 2016-02..2019-02 (2016-02..2017-01 and
2017-02..2018-01 for the 2016 / 2017 first-window candidates, 2018-02..2019-02 for the target window); (d) the hard cases:
delisted / acquired names (history up to the last trading day?), ticker changes (which symbol returns which period, and does
the `asof` symbol mapping follow the issuer?), symbol reuse, multi-class issuers (each class separately), ADRs, REITs, small
caps and names that listed inside the window. The answer feeds the bulk-collection go / no-go (owner decision) and the list
of hard cases that need another source. It never decides a weight, a selection or a result. It does not decide the SPY
distribution source (bars carry no distributions). 40 purposively chosen names show behaviour, not coverage rates.

Sample: SAMPLE below, 40 securities in 10 categories, chosen from documented public events (never by price or performance).
Each entry carries its public event and date and how the date was checked: WEB_CHECKED (a public source excerpt read on
2026-11-01, named in the note), RECALL (well-known, not re-checked) or UNVERIFIED (Main checks before the run). The
repository holds no price.

Requests (Alpaca market data v2, historical bars, single symbol): GET https://data.alpaca.markets/v2/stocks/{symbol}/bars
with timeframe=1Day, start=2016-01-01 (New York), end=2019-03-31 (New York), adjustment=raw, feed=sip, limit=10000,
sort=asc, and asof='-' (RAW: the bars traded under exactly that symbol, no mapping) for every symbol; for the lineage cases
also asof=<a date inside the security's listing> (the issuer as of that date, followed through renames) and
asof=CURRENT_ASOF (what today's symbol maps to): 67 series. Pagination by next_page_token (bounded). Exact URL allow-list,
redirects refused, keys only from env APCA_API_KEY_ID / APCA_API_SECRET_KEY (sent as headers, never printed), a fixed pause
before every request (<= 100 per minute, Alpaca's free limit is 200), bounded retries whose waits are capped by the time
left, request / wall-clock caps.

Prices stay in RAM. Two summaries, both value-free codes:
- PUBLIC, the Actions log of this public repository: only the line kinds, ordered keys and value patterns of LINE_SPECS
  (checked_line refuses anything else): fixed code lists, bounded small integers, dates from the fixed checkpoint / event
  set and the release tag. They say only whether a bar EXISTS on a day (presence, a bar with an invalid value still counts
  as a bar), counts of such days, which days a series covers compared with another series of the same run (day sets), and
  day differences between a first / last bar and a public event date. Nothing in them is computed from a price VALUE: no
  price, volume, return, value comparison (same / different bars), value validity, per-symbol bar count, key, token, URL,
  response text or exception text (fixed codes and exception class names only).
- PRIVATE, only inside the raw archive's manifest (`private_lines`, never printed): codes computed by comparing price values
  in RAM: whether a mapped (asof) series equals the plain series of the same symbol (vs_raw SAME_AS_RAW = the mapping is not
  shown) and, per leg, the plain series of that leg's symbol (legs_vs_raw: this separates the Under Armour class swap and the
  old / new Peabody equity); whether two class symbols or consecutive ticker symbols carry the same bars; value validity at
  the checkpoints (OK / BAD).
Alpaca's terms allow personal, non-commercial use and need prior written consent for public posting; whether price-free
derived results may be posted is unconfirmed. So the public lines are presence / coverage only, and the owner confirms before
the run that these lines may appear in the public Actions log (plan sections 4, 6, 9).

Raw storage (owner decision 5 route, settings doc 6.3): the exact response bytes and a sha256 manifest are zipped in RAM and
written ONLY to a NEW release `alpaca-sample-v1-<GITHUB_RUN_ID>` of the private raw repository (secret RAW_REPO_TOKEN):
the repository must answer private and the tag must not exist (create-only), both checked before any Alpaca request and
again right before creating; then one release with two assets, downloaded back and compared by sha256. After the create
call the route guard allows only the created release id and this run's own asset id. Every GitHub call has a short timeout
inside an explicit time budget and bounded retries on 5xx / network errors, so a transient error does not lose the RAM-only
data; a release that appears only after this run's own failed create call is taken over only when it has no asset. No
other release is listed, read, changed or deleted.

    python -I -S implementation/tools/measure_once/alpaca_sample_once.py          # the run (GitHub Actions only)
    python implementation/tools/measure_once/alpaca_sample_once.py --plan         # request plan counts, no network, no key

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
from decimal import Decimal  # noqa: E402
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
# last NYSE session of each month: holding months of the 2016 and 2017 first-window candidates, then the target window
MONTH_ENDS_2016W = (date(2016, 2, 29), date(2016, 3, 31), date(2016, 4, 29), date(2016, 5, 31), date(2016, 6, 30),
                    date(2016, 7, 29), date(2016, 8, 31), date(2016, 9, 30), date(2016, 10, 31), date(2016, 11, 30),
                    date(2016, 12, 30), date(2017, 1, 31))
MONTH_ENDS_2017W = (date(2017, 2, 28), date(2017, 3, 31), date(2017, 4, 28), date(2017, 5, 31), date(2017, 6, 30),
                    date(2017, 7, 31), date(2017, 8, 31), date(2017, 9, 29), date(2017, 10, 31), date(2017, 11, 30),
                    date(2017, 12, 29), date(2018, 1, 31))
MONTH_ENDS = (date(2018, 2, 28), date(2018, 3, 29), date(2018, 4, 30), date(2018, 5, 31), date(2018, 6, 29),
              date(2018, 7, 31), date(2018, 8, 31), date(2018, 9, 28), date(2018, 10, 31), date(2018, 11, 30),
              date(2018, 12, 31), date(2019, 1, 31), date(2019, 2, 28))
MONTH_END_GROUPS = (('monthend', MONTH_ENDS), ('monthend_2016w', MONTH_ENDS_2016W), ('monthend_2017w', MONTH_ENDS_2017W))
CURRENT_ASOF = '2026-10-30'   # "today's symbol" mapping, fixed so the run is reproducible (last day of the existing release)

CATEGORIES = ('CONTROL_LARGE', 'ETF_AUX', 'DELISTED_ACQUIRED', 'DELISTED_OTHER', 'TICKER_CHANGE', 'MULTI_CLASS', 'ADR',
              'REIT', 'SMALL_CAP', 'IPO_IN_WINDOW')
CHECKS = ('WEB_CHECKED', 'RECALL', 'UNVERIFIED')

# ---- the fixed sample ------------------------------------------------------------------------------------------------------
# (sid, category, legs, public event note, check). A leg (symbol, first, end) says the security traded under `symbol` on
# days d with first <= d < end (None = before / after the window). `first` is its first session under the symbol and `end`
# is the FIRST DAY IT NO LONGER TRADED under the symbol (exclusive), whatever the legal event day: for a merger effective
# before the open (EMC, WFM, MON, DNB) it is the effective day, for one effective after the close (DOW, TWX) the next
# session, for a halt from the open (SHPG) the halt day, for a rename the new symbol's first day. So the last bar under the
# symbol is expected on the session before `end` (an EVENT difference of -1, or -3 over a weekend).
# Selection rules per category (never price or performance):
#   CONTROL_LARGE      two of the largest U.S. common stocks, listed throughout, no symbol change;
#   ETF_AUX            SPY, the "ETF auxiliary comparison" of the settings doc (bars only; distributions need another source,
#                      not decided by this run);
#   DELISTED_ACQUIRED  acquisitions of then-listed U.S. issuers that closed inside the window, one or more per period
#                      (listed at T2016 / T2017 / T2018, gone before the next T); three with a later symbol reuse (FOXA
#                      inside the window, DOW and DNB after it);
#   DELISTED_OTHER     bankruptcy suspensions / delistings inside the window (one relisted under the same symbol);
#   TICKER_CHANGE      renames of continuously listed issuers, four inside the window and one after it (FB -> META);
#   MULTI_CLASS        issuers with two listed common classes, each class requested; one with an in-window symbol swap;
#   ADR                two large ADRs listed throughout and one acquired inside the window;
#   REIT               two large equity REITs listed throughout and one acquired inside the window;
#   SMALL_CAP          four small issuers recalled before any check (not chosen inside a value band), one acquired inside
#                      the window; approximate issuer values from SEC 10-K figures (shares outstanding x the 10-K's
#                      quarterly price range) at the checkpoints where each was listed lie roughly in USD 100m-400m, below or
#                      around the USD 250m entry threshold (per entry in the notes);
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
    ('DA03', 'DELISTED_ACQUIRED', (('DOW', None, '2017-09-01'),), 'The Dow Chemical Co. (NYSE) merged into DowDuPont, '
     'merger effective 2017-08-31; DOW ceased trading at the close of 2017-08-31 and DWDP traded from 2017-09-01 (SEC: '
     'DowDuPont exhibit 99-1), so the leg ends 2017-09-01; symbol DOW reused by Dow Inc. (new issuer) from 2019-04-02, '
     'after the window', 'WEB_CHECKED'),
    ('DA04', 'DELISTED_ACQUIRED', (('MON', None, '2018-06-07'),), 'Monsanto Co. (NYSE) acquired by Bayer; closed '
     '2018-06-07', 'RECALL'),
    ('DA05', 'DELISTED_ACQUIRED', (('TWX', None, '2018-06-15'),), 'Time Warner Inc. (NYSE) acquired by AT&T; merger '
     'effective after the close on 2018-06-14, suspended from trading 2018-06-15 (SEC: NYSE Form 25), so 2018-06-14 was the '
     'last session and the leg ends 2018-06-15', 'WEB_CHECKED'),
    ('DA06', 'DELISTED_ACQUIRED', (('DNB', None, '2019-02-08'),), 'Dun & Bradstreet (NYSE) taken private by an investor '
     'group (Cannae, CC Capital, Thomas H. Lee); merger effective 2019-02-08 (SEC 8-K), shares ceased trading before the '
     'NYSE open that day (buyer release), last session 2019-02-07; symbol DNB reused by Dun & Bradstreet Holdings from its '
     'July 2020 IPO, after the window', 'WEB_CHECKED'),
    ('DA07', 'DELISTED_ACQUIRED', (('FOXA', None, '2019-03-19'), ('TFCFA', '2019-03-19', '2019-03-20')),
     'Twenty-First Century Fox class A (Nasdaq) acquired by Disney, merger effective 2019-03-20 00:02 ET; before the open '
     '2019-03-19 its symbol changed FOXA -> TFCFA (OCC memo 44744; SEC 8-K of 21CF: now listed as TFCFA), so its last FOXA '
     'day was 2019-03-18 and its last session 2019-03-19 as TFCFA; Fox Corporation (new issuer) regular-way as FOXA from '
     '2019-03-19 (Nasdaq trader notice ECA2019-26)', 'WEB_CHECKED'),

    ('DO01', 'DELISTED_OTHER', (('SUNE', None, '2016-04-21'),), 'SunEdison (NYSE) Chapter 11; NYSE suspended trading '
     'immediately 2016-04-21 (ICE notice)', 'WEB_CHECKED'),
    ('DO02', 'DELISTED_OTHER', (('BTU', None, '2016-04-13'), ('BTU', '2017-04-04', None)), 'Peabody Energy (NYSE) Chapter 11; '
     'NYSE suspended trading immediately 2016-04-13 (ICE notice); old shares OTC, cancelled at emergence; reorganized common '
     'began trading on NYSE as BTU 2017-04-04 (SEC 424B5): same symbol, new equity, about one year apart, no name change',
     'WEB_CHECKED'),
    ('DO03', 'DELISTED_OTHER', (('SHLD', None, '2018-10-24'),), 'Sears Holdings (Nasdaq) Chapter 11 2018-10-15; trading '
     'suspended at the open 2018-10-24 (formal removal later), then OTC as SHLDQ (Cboe circular IC12-017)', 'WEB_CHECKED'),
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
     'symbol form BRK.A for historical bars at Alpaca is UNVERIFIED (an Alpaca forum staff reply 2021-11-09 advises BRK.A / '
     'BRK.B on the data API, a 2022 forum thread got no BRK.A stream value; no official symbology document)', 'UNVERIFIED'),
    ('MC04', 'MULTI_CLASS', (('BRK.B', None, None),), 'Berkshire Hathaway class B (NYSE), listed throughout; dotted symbol '
     'form BRK.B: an Alpaca staff reply 2021-11-09 advises it and users received BRK.B data in 2021 and 2022 (Alpaca forum '
     'only, no official symbology document)', 'WEB_CHECKED'),
    ('MC05', 'MULTI_CLASS', (('UA', None, '2016-12-07'), ('UAA', '2016-12-07', None)), 'Under Armour class A (NYSE): symbol '
     'UA until 2016-12-06, then UAA from 2016-12-07 (SEC: company 8-K and 10-K)', 'WEB_CHECKED'),
    ('MC06', 'MULTI_CLASS', (('UA.C', '2016-04-08', '2016-12-07'), ('UA', '2016-12-07', None)), 'Under Armour class C (NYSE): '
     'distributed 2016-04-07, listed as UA.C from its initial issuance 2016-04-08 until 2016-12-06 and as UA from 2016-12-07 '
     '(SEC: company 10-K); so UA means class A before 2016-12-07 and class C after (in-window symbol swap); the dotted symbol '
     'form UA.C at Alpaca is UNVERIFIED', 'UNVERIFIED'),

    ('AD01', 'ADR', (('BABA', None, None),), 'Alibaba Group ADS (NYSE), listed throughout', 'RECALL'),
    ('AD02', 'ADR', (('TSM', None, None),), 'Taiwan Semiconductor Manufacturing ADS (NYSE), listed throughout', 'RECALL'),
    ('AD03', 'ADR', (('SHPG', None, '2019-01-07'),), 'Shire plc ADS (Nasdaq) acquired by Takeda, scheme effective '
     '2019-01-08; Nasdaq halts an ADR when its underlying is halted and the London shares were suspended before the open '
     '2019-01-07 (Nasdaq trader notice ECA2018-236; OCC memo 44113: ADS expected to be halted before the open that day), so '
     'the last regular session was 2019-01-04 and the leg ends 2019-01-07; ADS cancelled 2019-01-09', 'WEB_CHECKED'),

    ('RE01', 'REIT', (('O', None, None),), 'Realty Income (NYSE), equity REIT, listed throughout', 'RECALL'),
    ('RE02', 'REIT', (('PLD', None, None),), 'Prologis (NYSE), equity REIT, listed throughout', 'RECALL'),
    ('RE03', 'REIT', (('DCT', None, '2018-08-22'),), 'DCT Industrial Trust (NYSE) acquired by Prologis (all stock); '
     'completed 2018-08-22 (Prologis release; exact last session not re-checked)', 'WEB_CHECKED'),

    ('SC01', 'SMALL_CAP', (('KIRK', None, None),), "Kirkland's Inc. (Nasdaq), listed throughout the window; issuer value "
     'about USD 170m-210m around 2018-02 and about USD 190m-290m around T2016 (SEC 10-K: shares outstanding x quarterly '
     'last-sale range), below the USD 250m threshold at 2018-02; after the window renamed The Brand House Collective (TBHC '
     'from 2025-07-29) and merged into Bed Bath & Beyond in 2026', 'WEB_CHECKED'),
    ('SC02', 'SMALL_CAP', (('LCUT', None, None),), 'Lifetime Brands (Nasdaq), listed throughout; issuer value about USD 205m '
     'before and about USD 280m after the 2018-03-02 share issue for Filament (SEC 10-K), near the USD 250m threshold; the '
     'share count jumps between T2018 and the March month-end', 'WEB_CHECKED'),
    ('SC03', 'SMALL_CAP', (('BGFV', None, None),), 'Big 5 Sporting Goods (Nasdaq), listed throughout the window; issuer value '
     'about USD 130m-170m around 2018-02 and about USD 285m-380m around T2017 (SEC 10-K: shares x quarterly closing range); '
     'after the window merged and delisted from Nasdaq 2025-10-02', 'WEB_CHECKED'),
    ('SC04', 'SMALL_CAP', (('RT', None, '2017-12-21'),), 'Ruby Tuesday (NYSE) acquired by NRD Capital; closed and effective '
     '2017-12-21 (GlobeNewswire release at 12:35 ET: shares will cease trading); whether RT still traded on 2017-12-21 is '
     'UNVERIFIED (no Form 25 found), so its END difference may read 0 or -1; issuer value about USD 110m-225m around T2017 '
     'and about USD 275m-350m around T2016 (SEC 10-K, estimate), gone before T2018', 'UNVERIFIED'),

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
# Mapped requests (asof = a date): (sid, symbol, asof, expectation, legs). LINEAGE: the security's own legs (all, or the
# leg indexes given: old and new Peabody equity are different entities without a name change, so each dated BTU request
# expects only the equity listed on its asof date); OTHER_ISSUER: the reusing issuer's legs, so bars of the sample security
# under today's mapping count as outside. Alpaca answers the plain symbol when it finds no mapping, so every mapped series
# is also compared with the RAW series of the same symbol (days: public; values: private).
MAPPED_REQUESTS = (
    ('TC01', 'PCLN', '2018-02-20', 'LINEAGE', None), ('TC01', 'BKNG', CURRENT_ASOF, 'LINEAGE', None),
    ('TC02', 'YHOO', '2017-02-21', 'LINEAGE', None),
    ('TC03', 'DPS', '2018-02-20', 'LINEAGE', None), ('TC03', 'KDP', CURRENT_ASOF, 'LINEAGE', None),
    ('TC04', 'VRX', '2018-02-20', 'LINEAGE', None), ('TC04', 'BHC', CURRENT_ASOF, 'LINEAGE', None),
    ('TC05', 'FB', '2018-02-20', 'LINEAGE', None), ('TC05', 'META', CURRENT_ASOF, 'LINEAGE', None),
    ('MC05', 'UA', '2016-02-16', 'LINEAGE', None), ('MC05', 'UAA', CURRENT_ASOF, 'LINEAGE', None),
    ('MC06', 'UA', '2018-02-20', 'LINEAGE', None), ('MC06', 'UA', CURRENT_ASOF, 'LINEAGE', None),
    ('DA03', 'DOW', '2017-02-21', 'LINEAGE', None), ('DA03', 'DOW', CURRENT_ASOF, 'OTHER_ISSUER', None),
    ('DA07', 'FOXA', '2018-02-20', 'LINEAGE', None), ('DA07', 'FOXA', CURRENT_ASOF, 'OTHER_ISSUER', None),
    ('DO02', 'BTU', '2016-02-16', 'LINEAGE', (0,)), ('DO02', 'BTU', '2018-02-20', 'LINEAGE', (1,)),
    ('DO02', 'BTU', CURRENT_ASOF, 'LINEAGE', (1,)),
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
MAX_REQUESTS = 150             # every HTTP attempt counts; the plan needs one page per series (67)
MAX_PAGES = 5                  # per series (one page holds 10000 bars; the window has about 815 sessions)
WALL_CLOCK_S = 9 * 60          # collection; waits are capped by the time left, so storage keeps its own budget
PAGE_CAP = 8 * 1024 * 1024
CHUNK = 64 * 1024
TOLERANCE = timedelta(days=4)  # around a leg boundary, bars are not called outside

# ---- private raw store -------------------------------------------------------------------------------------------------
RAW_REPO = 'kco994553-star/investment-system1-raw'
RAW_TOKEN_ENV = 'RAW_REPO_TOKEN'
TAG_PREFIX = 'alpaca-sample-v1-'
GH_API = raw_store_release.API
GH_UPLOADS = raw_store_release.UPLOADS
GH_TIMEOUT_S = 60              # per socket operation (raw_store_release.http alone would allow 600 s)
PREFLIGHT_BUDGET_S = 150       # the two checks before any Alpaca request
STORAGE_BUDGET_S = 300         # re-check, create, two uploads, download-back
STORAGE_RETRY_WAITS_S = (5.0, 15.0)   # 5xx / network errors: at most two retries per call, waits capped by the budget
MANIFEST_SCHEMA = 'alpaca-sample-v1-manifest/2'
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
    for sid, symbol, asof, expect, selected in mapped:
        if (sid not in securities or expect not in ('LINEAGE', 'OTHER_ISSUER')
                or not re.fullmatch(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}', asof)):
            raise ValueError('mapped')
        legs = securities[sid]['legs']
        if selected is not None and (expect != 'LINEAGE' or not selected or len(set(selected)) != len(selected)
                                     or any(not isinstance(i, int) or not 0 <= i < len(legs) for i in selected)):
            raise ValueError('mapped_legs')
        chosen = legs if selected is None else [legs[i] for i in selected]
        if symbol not in {leg[0] for leg in chosen}:
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
                           'expect': 'SYMBOL', 'legs': None}
            series.append(raw[symbol])
    for sid, symbol, asof, expect, selected in mapped:
        series.append({'id': 'ASOF' + asof.replace('-', '') + ':' + symbol, 'symbol': symbol, 'asof': asof,
                       'mode': series_mode(asof), 'sids': [sid], 'expect': expect,
                       'legs': None if selected is None else tuple(selected)})
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
            left = WALL_CLOCK_S - self.elapsed()   # a wait never runs past the collection clock
            if left <= 0:
                raise Stop('WALL_CLOCK')
            self._sleep(min(wait, left))

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


def _parsed_page(body, symbol, *, mapped=False, start=WINDOW_START, end=WINDOW_END, exact=False):
    """Validated [(New York day, original bar)], next page token, returned symbol.
    Exact decimal decoding is available to offline normalization; raises ValueError(<fixed code>)."""
    try:
        data = json.loads(body, parse_float=Decimal) if exact else json.loads(body)
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
        if not start <= day <= end:
            raise ValueError('OUT_OF_WINDOW')
        rows.append((day, bar))
    return rows, token, echo


def parse_page(body, symbol, *, mapped=False):
    """Legacy measurement interface: NY day and OHLC only; raw archive remains complete."""
    rows, token, echo = _parsed_page(body, symbol, mapped=mapped)
    return [(day, tuple(_price(bar.get(k)) for k in ('o', 'h', 'l', 'c'))) for day, bar in rows], token, (
        'SAME' if echo == symbol else 'OTHER')


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
    """Offline normalization of retained SIP raw daily pages; no I/O, HTTP or execution approval.

    pages: [{body: original bytes, sha256: recorded digest, request_page_token: token or None,
             acquired_at: timezone-aware receipt timestamp}]. Never infer receipt/publication from a bar timestamp.
    request: {symbol, asof, feed, adjustment, timeframe, start, end}. An unrecorded historical asof may be None;
    that is NOT asof='-' and proves no security identity. Different periods are allowed offline only; the collector's
    fixed URL allow-list is unchanged. The returned candidates are NOT engine-ready prices: identity, currency,
    session-open suitability and input rights require separate evidence before Main's adapter may connect them.
    Hash, page order and request-token chain are checked; partial pages never become a complete response.
    """
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
        if 'request_page_token' not in page or page['request_page_token'] != expected_token or (page_index and expected_token is None):
            raise ValueError('PAGE_CHAIN')
        acquired = page.get('acquired_at')
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
                                 next_page_token=token, acquired_at=acquired))
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
    return dict(schema='alpaca-normalized-candidates/1', request=dict(request), source_pages=source_pages,
                status=status, pages_complete=complete, rows=rows, identity_status='UNVERIFIED',
                listing_status='UNKNOWN', execution_open_status='UNVERIFIED_SESSION_OPEN',
                corporate_actions_status='NOT_IN_BARS', pit_status='NOT_VERIFIED', rights_status='NOT_EVALUATED')


def fetch_series(client, series):
    """{'status', 'bars', 'pages', 'echo'}: status DATA | NO_DATA | ERR_<code> | INVALID_<code> (response format, never a
    price value); on any failure the bars are dropped (the raw pages are kept for the private store)."""
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
            return failed('INVALID_' + (code if _CODE.fullmatch(code) else 'OTHER'))
        echoes.add(echo)
        for day, values in rows:
            if last is not None and day <= last:
                return failed('INVALID_ORDER')
            bars[day], last = values, day
        if not next_token:
            return {'status': 'DATA' if bars else 'NO_DATA', 'bars': bars, 'pages': pages,
                    'echo': 'OTHER' if 'OTHER' in echoes else 'SAME'}
        if next_token in seen or not rows:
            return failed('INVALID_PAGINATION')
        seen.add(next_token)
        token = next_token
    return failed('INVALID_PAGE_CAP')


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
# Public codes look only at which days have a bar (presence). Codes that compare or check price VALUES (overlap, vs_raw,
# legs_vs_raw, OK / BAD) are computed in RAM for the private manifest and never printed.
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


def _ok(result):
    return result['status'] in ('DATA', 'NO_DATA')


def expected_legs(series, securities, by_symbol):
    """[(symbol, first, end)] the series is expected to carry: SYMBOL every use of the symbol, OTHER_ISSUER the reusing
    issuer's legs, LINEAGE the security's own legs (or the selected ones)."""
    if series['expect'] == 'SYMBOL':
        return [(series['symbol'], f, e) for f, e, _ in by_symbol[series['symbol']]]
    if series['expect'] == 'OTHER_ISSUER':
        return [(series['symbol'], f, e) for f, e, owner in by_symbol[series['symbol']] if owner == 'OTHER']
    legs = securities[series['sids'][0]]['legs']
    return list(legs) if series.get('legs') is None else [legs[i] for i in series['legs']]


def series_spans(series, securities, by_symbol):
    return clip((f, e) for _, f, e in expected_legs(series, securities, by_symbol))


def presence_state(result, spans, day):
    """Public: BAR (a bar exists, whatever its values) | MISS | UNEXP (bar where none is expected) | - | ERR."""
    if not _ok(result):
        return 'ERR'
    there = day in result['bars']
    if not inside(day, spans):
        return 'UNEXP' if there else '-'
    return 'BAR' if there else 'MISS'


def value_state(result, spans, day, field):
    """Private: OK | BAD (bar without a valid value) | MISS | UNEXP | - | ERR."""
    state = presence_state(result, spans, day)
    if state != 'BAR':
        return state
    return 'OK' if result['bars'][day][field] is not None else 'BAD'


def monthend_state(states):
    if 'ERR' in states:
        return 'ERR'
    expected = [s for s in states if s in ('BAR', 'OK', 'MISS', 'BAD')]
    good = sum(s in ('BAR', 'OK') for s in expected)
    base = 'NA' if not expected else 'FULL' if good == len(expected) else 'NONE' if good == 0 else 'PARTIAL'
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


def days_vs(a_days, b_days):
    """Public, presence only: how one day set compares with another of the same run."""
    a_days, b_days = set(a_days), set(b_days)
    if a_days == b_days:
        return 'SAME_DAYS'
    return 'FEWER_DAYS' if a_days < b_days else 'MORE_DAYS' if a_days > b_days else 'OTHER_DAYS'


def common_days(a_result, b_result):
    """Public, presence only: do two series have a bar on any same day."""
    if not _ok(a_result) or not _ok(b_result):
        return 'ERR'
    return 'SOME' if set(a_result['bars']) & set(b_result['bars']) else 'NONE'


def class_days(a_result, b_result):
    if not _ok(a_result) or not _ok(b_result):
        return 'ERR'
    a, b = set(a_result['bars']), set(b_result['bars'])
    if not a or not b:
        return 'BOTH_EMPTY' if not a and not b else 'ONE_EMPTY'
    return 'SAME_DAYS' if a == b else 'OTHER_DAYS'


def overlap(a_bars, b_bars):
    """Private: compares bar VALUES on the common days."""
    common = sorted(set(a_bars) & set(b_bars))
    if not common:
        return 'NO_OVERLAP'
    same = sum(a_bars[d] == b_bars[d] for d in common)
    return 'SAME_BARS' if same == len(common) else 'DIFFERENT_BARS' if same == 0 else 'PARTLY_SAME'


def vs_raw(result, raw_result):
    """Private: a mapped series against the plain series of the same symbol. SAME_AS_RAW (same days and values) means the
    mapping is not shown: Alpaca answers the plain symbol when it finds no mapping."""
    if not _ok(result) or not _ok(raw_result):
        return 'ERR'
    if not result['bars'] and not raw_result['bars']:
        return 'BOTH_EMPTY'
    return 'SAME_AS_RAW' if result['bars'] == raw_result['bars'] else 'DIFFERS'


def leg_vs_raw(result, raw_result, spans):
    """Private: inside one expected leg, the mapped series' bars against the plain series of that leg's symbol."""
    if not spans:
        return '-'
    if not _ok(result) or not _ok(raw_result):
        return 'ERR'
    a = {d: v for d, v in result['bars'].items() if inside(d, spans)}
    b = {d: v for d, v in raw_result['bars'].items() if inside(d, spans)}
    if not a or not b:
        return 'BOTH_EMPTY' if not a and not b else 'NO_RAW_BARS' if a else 'NO_ASOF_BARS'
    code = overlap(a, b)
    return 'SAME_ON_COMMON_DAYS' if code == 'SAME_BARS' and set(a) != set(b) else code


def security_state(info, raw, by_symbol, day, field=None):
    """Primary engine view: the RAW series of the security's point-in-time symbol on `day`. field None: public presence
    (BAR | MISS | UNEXP | - | ERR); field 0 / 3: private value validity (OK | BAD | ...)."""
    for symbol, first, end in info['legs']:
        if (first or date.min) <= day < (end or date.max):
            result = raw[symbol]
            if not _ok(result):
                return 'ERR'
            bar = result['bars'].get(day)
            if bar is None:
                return 'MISS'
            return 'BAR' if field is None else 'OK' if bar[field] is not None else 'BAD'
    for symbol in {leg[0] for leg in info['legs']}:
        result = raw[symbol]
        if day in result['bars'] and not inside(day, clip((f, e) for f, e, _ in by_symbol[symbol])):
            return 'UNEXP'
    return '-'


def events(sid, info, raw, by_symbol):
    """(symbol, kind, event day, bar_vs_event_days|None|'ERR') for every leg boundary inside the window. The event day is
    the leg's first day / end (first day no longer traded under the symbol). The bar is the symbol's last RAW bar before the
    next use of the symbol (END / RENAME_OUT) or its first RAW bar after the previous use (START / RENAME_IN / RELIST)."""
    out, legs = [], info['legs']
    for i, (symbol, first, end) in enumerate(legs):
        result = raw[symbol]
        days = sorted(result['bars']) if _ok(result) else None
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


def lineage_code(sid, info, raw, by_symbol):
    """RAW behaviour of a security with more than one leg (presence only): PIT_SYMBOLS (each symbol has bars only in its
    own legs), CURRENT_SYMBOL_ONLY (only the last symbol has bars, also before its first day on days no other issuer's use of
    that symbol explains), MISSING_SYMBOL, OVERLAPPING_SYMBOLS, ERR, NO_DATA."""
    symbols = list(dict.fromkeys(leg[0] for leg in info['legs']))
    if any(not _ok(raw[s]) for s in symbols):
        return 'ERR'
    fits = {s: fit(set(raw[s]['bars']), clip((f, e) for f, e, _ in by_symbol[s])) for s in symbols}
    own = {s: clip((f, e) for sym, f, e in info['legs'] if sym == s) for s in symbols}
    if all(not raw[s]['bars'] for s in symbols):
        return 'NO_DATA'
    if all(f in ('MATCH', 'NONE_EXPECTED') for f in fits.values()):
        return 'PIT_SYMBOLS'
    last = symbols[-1]
    last_start = own[last][0][0] if own[last] else WINDOW_AFTER   # a rename after the window: every window day is before
    reused = clip((f, e) for f, e, owner in by_symbol[last] if owner != sid)   # e.g. UA = class A before 2016-12-07
    early = [d for d in raw[last]['bars'] if d < last_start and not inside(d, reused)]
    if symbols[:-1] and all(not raw[s]['bars'] for s in symbols[:-1]) and early:
        return 'CURRENT_SYMBOL_ONLY'
    if any(f.startswith('PARTIAL') or f == 'NO_DATA' for f in fits.values()):
        return 'MISSING_SYMBOL'
    return 'OVERLAPPING_SYMBOLS'


def checkpoints():
    """(name, day, field, group): T opens, S closes, month-end closes of the three groups."""
    out = [(f'T{y}', d, 0, 't_bar') for y, d in T_DAYS] + [(f'S{y}', d, 3, 's_bar') for y, d in S_DAYS]
    for group, days in MONTH_END_GROUPS:
        out += [('ME' + d.strftime('%Y%m'), d, 3, group) for d in days]
    return out


def summarize(securities, by_symbol, series_plan, results):
    """(public lines, private lines). Public: presence / coverage only, every line through checked_line. Private: the
    value-comparison codes, only for the manifest in the private release."""
    raw = {s['symbol']: results[s['id']] for s in series_plan if s['mode'] == 'RAW'}
    reference = set()
    for symbol in CONTROL_SYMBOLS:
        reference |= set(raw[symbol]['bars'])
    lines, private = [], []
    for series in series_plan:
        result = results[series['id']]
        spans = series_spans(series, securities, by_symbol)
        days = set(result['bars'])
        ok = _ok(result)
        t = ','.join(presence_state(result, spans, d) for _, d in T_DAYS)
        s = ','.join(presence_state(result, spans, d) for _, d in S_DAYS)
        me = {g: monthend_state([presence_state(result, spans, d) for d in ds]) for g, ds in MONTH_END_GROUPS}
        cats = sorted({securities[sid]['category'] for sid in series['sids']})
        plain = raw[series['symbol']]
        dvr = '-' if series['mode'] == 'RAW' else days_vs(days, plain['bars']) if ok and _ok(plain) else 'ERR'
        lines.append(f"ALPSAMPLE_SERIES id={series['id']} sid={'+'.join(series['sids'])} cat={'+'.join(cats)} "
                     f"mode={series['mode']} expect={series['expect']} status={result['status']} "
                     f"fit={fit(days, spans) if ok else 'ERR'} first={edge(days, 'first') if ok else 'ERR'} "
                     f"last={edge(days, 'last') if ok else 'ERR'} gaps={gaps(days, spans, reference) if ok else 'ERR'} "
                     f"t_bar={t} s_bar={s} monthend={me['monthend']} monthend_2016w={me['monthend_2016w']} "
                     f"monthend_2017w={me['monthend_2017w']} days_vs_raw={dvr} echo={result['echo']}")
        vt = ','.join(value_state(result, spans, d, 0) for _, d in T_DAYS)
        vs = ','.join(value_state(result, spans, d, 3) for _, d in S_DAYS)
        vme = ' '.join(f'{g}={monthend_state([value_state(result, spans, d, 3) for d in ds])}' for g, ds in MONTH_END_GROUPS)
        invalid = sum(any(v is None for v in bar) for bar in result['bars'].values())
        private.append(f"ALPSAMPLE_PRIVATE_SERIES id={series['id']} t_open={vt} s_close={vs} {vme} invalid_bars={invalid}")
        if series['mode'] != 'RAW':
            per_leg = ','.join(leg_vs_raw(result, raw[sym], clip([(f, e)]))
                               for sym, f, e in expected_legs(series, securities, by_symbol))
            private.append(f"ALPSAMPLE_PRIVATE_ASOF id={series['id']} vs_raw={vs_raw(result, plain)} "
                           f"legs_vs_raw={per_leg or '-'}")
    for sid, info in securities.items():
        for symbol, kind, day, diff in events(sid, info, raw, by_symbol):
            shown = 'NONE' if diff is None else diff if isinstance(diff, str) else str(int(diff))
            lines.append(f"ALPSAMPLE_EVENT sid={sid} cat={info['category']} sym={symbol} event={kind} "
                         f"event_day={day.isoformat()} bar_vs_event_days={shown}")
    mapped = {}
    for series in series_plan:
        if series['mode'] != 'RAW':
            result = results[series['id']]
            code = fit(set(result['bars']), series_spans(series, securities, by_symbol)) if _ok(result) else 'ERR'
            mapped.setdefault((series['sids'][0], series['mode']), []).append(code)
    for sid, info in securities.items():
        symbols = list(dict.fromkeys(leg[0] for leg in info['legs']))
        if len(info['legs']) < 2 and not any(key[0] == sid for key in mapped):
            continue
        pairs = list(zip(symbols, symbols[1:]))
        common = ','.join(common_days(raw[a], raw[b]) for a, b in pairs) or '-'
        lines.append(f"ALPSAMPLE_LINEAGE sid={sid} cat={info['category']} "
                     f"raw={lineage_code(sid, info, raw, by_symbol) if len(info['legs']) > 1 else 'SINGLE_LEG'} "
                     f"asof_pit={','.join(mapped.get((sid, 'ASOF_PIT'), ['-']))} "
                     f"asof_current={','.join(mapped.get((sid, 'ASOF_CURRENT'), ['-']))} common_days={common}")
        ov = ','.join(overlap(raw[a]['bars'], raw[b]['bars']) if _ok(raw[a]) and _ok(raw[b]) else 'ERR'
                      for a, b in pairs) or '-'
        private.append(f'ALPSAMPLE_PRIVATE_LINEAGE sid={sid} overlap={ov}')
    for a, b in CLASS_PAIRS:
        lines.append(f"ALPSAMPLE_CLASSES pair={a}+{b} days={class_days(raw[a], raw[b])}")
        same = overlap(raw[a]['bars'], raw[b]['bars']) if _ok(raw[a]) and _ok(raw[b]) else 'ERR'
        private.append(f'ALPSAMPLE_PRIVATE_CLASSES pair={a}+{b} overlap={same}')
    cps = checkpoints()
    per_security = {sid: {cp: security_state(info, raw, by_symbol, d) for cp, d, _, _ in cps}
                    for sid, info in securities.items()}
    groups = [g for g in ('t_bar', 's_bar')] + [g for g, _ in MONTH_END_GROUPS]
    group_of = {cp: g for cp, _, _, g in cps}
    for category in CATEGORIES:
        sids = [sid for sid, info in securities.items() if info['category'] == category]
        symbols = sorted({leg[0] for sid in sids for leg in securities[sid]['legs']})
        status = Counter('DATA' if raw[s]['status'] == 'DATA' else 'NO_DATA' if raw[s]['status'] == 'NO_DATA' else 'ERR'
                         for s in symbols)
        count = Counter()
        for sid in sids:
            states = per_security[sid]
            for cp, value in states.items():
                group = group_of[cp]
                count[group + '_exp'] += value in ('BAR', 'MISS', 'ERR')
                count[group + '_ok'] += value == 'BAR'
                count[group + '_unexp'] += value == 'UNEXP'
            count['complete'] += all(v in ('BAR', '-') for v in states.values())
            legs_gaps = [gaps(set(raw[sym]['bars']), clip([(f, e)]), reference) for sym, f, e in securities[sid]['legs']
                         if _ok(raw[sym]) and clip([(f, e)])]
            judged = [g for g in legs_gaps if g != 'NA']
            count['gap_judged'] += bool(judged)
            count['gapless'] += bool(judged) and all(g == 'NONE' for g in judged)
        cover = ' '.join(f"{g}={count[g + '_ok']}/{count[g + '_exp']} {g.replace('_bar', '')}_unexpected={count[g + '_unexp']}"
                         if g in ('t_bar', 's_bar') else
                         f"{g}={count[g + '_ok']}/{count[g + '_exp']} {g}_unexpected={count[g + '_unexp']}" for g in groups)
        lines.append(f"ALPSAMPLE_CATEGORY cat={category} securities={len(sids)} symbols={len(symbols)} "
                     f"symbols_with_data={status['DATA']} symbols_no_data={status['NO_DATA']} symbols_error={status['ERR']} "
                     f"{cover} complete={count['complete']} gapless={count['gapless']}/{count['gap_judged']}")
    for cp, day, field, _ in cps:
        values = Counter(per_security[sid][cp] for sid in securities)
        expected = values['BAR'] + values['MISS'] + values['ERR']
        lines.append(f"ALPSAMPLE_CHECKPOINT cp={cp} day={day.isoformat()} field={'open' if field == 0 else 'close'} "
                     f"expected={expected} bar={values['BAR']} missing={values['MISS']} error={values['ERR']} "
                     f"unexpected={values['UNEXP']}")
        valid = Counter(security_state(info, raw, by_symbol, day, field) for info in securities.values())
        private.append(f"ALPSAMPLE_PRIVATE_CHECKPOINT cp={cp} ok={valid['OK']} bad={valid['BAD']}")
    return [checked_line(line) for line in lines], [private_line(line) for line in private]


# ---- the public-line allow-table ---------------------------------------------------------------------------------------
# Every printed line is `<kind> key=value ...` with exactly the ordered keys of one entry below, and every value matches
# its pattern: a fixed code list, a bounded small integer (counts, day differences), a date from the fixed checkpoint /
# event set, or the release tag. Anything else (another key, a larger number, another date, a decimal) is refused.
def _sample_dates():
    days = {WINDOW_START, WINDOW_END} | {d for _, d in T_DAYS} | {d for _, d in S_DAYS}
    for _, ds in MONTH_END_GROUPS:
        days |= set(ds)
    for _, _, legs, _, _ in SAMPLE:
        for _, first, end in legs:
            days |= {d for d in (_day(first), _day(end)) if d is not None and WINDOW_START < d <= WINDOW_END}
    return frozenset(d.isoformat() for d in days)


_SIDS = tuple(entry[0] for entry in SAMPLE)
_SYMBOLS = tuple(dict.fromkeys(leg[0] for entry in SAMPLE for leg in entry[2]))
_SERIES_ID = re.compile(r'(?:RAW|ASOF20[0-9]{6}):(?:' + '|'.join(re.escape(s) for s in _SYMBOLS) + ')')
_TAG = re.compile(re.escape(TAG_PREFIX) + r'[0-9]{1,20}')
_DATES = _sample_dates()
_FITS = ('NO_DATA', 'MATCH', 'PARTIAL', 'MATCH+OUTSIDE', 'PARTIAL+OUTSIDE', 'NONE_EXPECTED', 'OUTSIDE_ONLY', 'ERR')
_MONTHEND = tuple(b + u for b in ('FULL', 'PARTIAL', 'NONE', 'NA') for u in ('', '+UNEXP')) + ('ERR',)
_PRESENCE = ('BAR', 'MISS', 'UNEXP', '-', 'ERR')
_STATUS = re.compile(r'DATA|NO_DATA|NOT_RUN|ERR_[A-Za-z][A-Za-z0-9_]{0,40}|INVALID_[A-Z][A-Z_]{0,30}')


def _enum(*values):
    return ('enum', frozenset(values))


def _int(hi, lo=0):
    return ('int', lo, hi)


def _list(item, n_min, n_max, sep=','):
    return ('list', item, n_min, n_max, sep)


def _either(*matchers):
    return ('either', matchers)


_N_SAMPLE = _int(99)
_N_REQ = _int(MAX_REQUESTS)
_RATIO = ('ratio', 999)
_CHECKPOINT_NAMES = frozenset(cp for cp, _, _, _ in checkpoints())
LINE_SPECS = {
    'ALPSAMPLE_PLAN': ((('securities', _N_SAMPLE), ('symbols', _N_SAMPLE), ('series', _int(199)), ('raw', _N_SAMPLE),
                        ('asof_pit', _N_SAMPLE), ('asof_current', _N_SAMPLE), ('pages_expected', _int(199)),
                        ('max_requests', _enum(str(MAX_REQUESTS))), ('pace_ms', _enum(str(int(SLEEP_S * 1000))))),),
    'ALPSAMPLE_PLAN_CATEGORY': ((('cat', _enum(*CATEGORIES)), ('securities', _int(40)), ('symbols', _N_SAMPLE),
                                 ('unverified', _int(40))),),
    'ALPSAMPLE_STOP': ((('reason', ('re', _CODE)),), (('reason', _enum('UNEXPECTED')), ('class', ('re', _CODE)))),
    'ALPSAMPLE_START': ((('securities', _N_SAMPLE), ('symbols', _N_SAMPLE), ('series', _int(199)), ('categories', _int(20)),
                         ('window', _enum(f'{WINDOW_START}..{WINDOW_END}')), ('feed', _enum('sip')),
                         ('adjustment', _enum('raw')), ('timeframe', _enum('1Day')),
                         ('max_requests', _enum(str(MAX_REQUESTS))), ('pace_ms', _enum(str(int(SLEEP_S * 1000)))),
                         ('release', ('re', _TAG))),),
    'ALPSAMPLE_SERIES': ((('id', ('re', _SERIES_ID)), ('sid', _list(_enum(*_SIDS), 1, 3, '+')),
                          ('cat', _list(_enum(*CATEGORIES), 1, 2, '+')), ('mode', _enum('RAW', 'ASOF_PIT', 'ASOF_CURRENT')),
                          ('expect', _enum('SYMBOL', 'LINEAGE', 'OTHER_ISSUER')), ('status', ('re', _STATUS)),
                          ('fit', _enum(*_FITS)), ('first', _enum('AT_START', 'LATER', 'NONE', 'ERR')),
                          ('last', _enum('AT_END', 'EARLIER', 'NONE', 'ERR')), ('gaps', _enum('NONE', 'SOME', 'NA', 'ERR')),
                          ('t_bar', _list(_enum(*_PRESENCE), 4, 4)), ('s_bar', _list(_enum(*_PRESENCE), 4, 4)),
                          ('monthend', _enum(*_MONTHEND)), ('monthend_2016w', _enum(*_MONTHEND)),
                          ('monthend_2017w', _enum(*_MONTHEND)),
                          ('days_vs_raw', _enum('-', 'SAME_DAYS', 'FEWER_DAYS', 'MORE_DAYS', 'OTHER_DAYS', 'ERR')),
                          ('echo', _enum('SAME', 'OTHER', '-'))),),
    'ALPSAMPLE_EVENT': ((('sid', _enum(*_SIDS)), ('cat', _enum(*CATEGORIES)), ('sym', _enum(*_SYMBOLS)),
                         ('event', _enum('START', 'END', 'RENAME_IN', 'RENAME_OUT', 'RELIST')), ('event_day', ('date',)),
                         ('bar_vs_event_days', _either(_int(1200, -1200), _enum('NONE', 'ERR')))),),
    'ALPSAMPLE_LINEAGE': ((('sid', _enum(*_SIDS)), ('cat', _enum(*CATEGORIES)),
                           ('raw', _enum('PIT_SYMBOLS', 'CURRENT_SYMBOL_ONLY', 'MISSING_SYMBOL', 'OVERLAPPING_SYMBOLS', 'ERR',
                                         'NO_DATA', 'SINGLE_LEG')),
                           ('asof_pit', _list(_enum('-', *_FITS), 1, 3)), ('asof_current', _list(_enum('-', *_FITS), 1, 3)),
                           ('common_days', _list(_enum('-', 'NONE', 'SOME', 'ERR'), 1, 3))),),
    'ALPSAMPLE_CLASSES': ((('pair', _enum(*(f'{a}+{b}' for a, b in CLASS_PAIRS))),
                           ('days', _enum('SAME_DAYS', 'OTHER_DAYS', 'ONE_EMPTY', 'BOTH_EMPTY', 'ERR'))),),
    'ALPSAMPLE_CATEGORY': ((('cat', _enum(*CATEGORIES)), ('securities', _int(40)), ('symbols', _N_SAMPLE),
                            ('symbols_with_data', _N_SAMPLE), ('symbols_no_data', _N_SAMPLE), ('symbols_error', _N_SAMPLE),
                            ('t_bar', _RATIO), ('t_unexpected', _int(999)), ('s_bar', _RATIO), ('s_unexpected', _int(999)),
                            ('monthend', _RATIO), ('monthend_unexpected', _int(999)),
                            ('monthend_2016w', _RATIO), ('monthend_2016w_unexpected', _int(999)),
                            ('monthend_2017w', _RATIO), ('monthend_2017w_unexpected', _int(999)),
                            ('complete', _int(40)), ('gapless', ('ratio', 40))),),
    'ALPSAMPLE_CHECKPOINT': ((('cp', _enum(*_CHECKPOINT_NAMES)), ('day', ('date',)), ('field', _enum('open', 'close')),
                              ('expected', _int(40)), ('bar', _int(40)), ('missing', _int(40)), ('error', _int(40)),
                              ('unexpected', _int(40))),),
    'ALPSAMPLE_REQUESTS': ((('series', _int(199)), ('series_done', _int(199)), ('total', _N_REQ), ('pages', _N_REQ),
                            ('retries', _N_REQ), ('http400', _N_REQ), ('http401', _N_REQ), ('http403', _N_REQ),
                            ('http404', _N_REQ), ('http422', _N_REQ), ('http429', _N_REQ), ('http5xx', _N_REQ),
                            ('http_other', _N_REQ), ('network', _N_REQ), ('elapsed_s', _int(3600)),
                            ('stopped', _enum(*STOP_REASONS))),),
    'ALPSAMPLE_STORAGE': ((('status', _enum('STORED')), ('release', ('re', _TAG)), ('files', _int(999)),
                           ('roundtrip', _enum('SHA256_MATCH')), ('retries', _int(99))),
                          (('status', _enum('FAILED')), ('code', ('re', _CODE)), ('retries', _int(99)))),
}
_INT_TEXT = re.compile(r'-?(?:0|[1-9][0-9]{0,3})')


def _matches(matcher, value):
    kind = matcher[0]
    if kind == 'enum':
        return value in matcher[1]
    if kind == 're':
        return matcher[1].fullmatch(value) is not None
    if kind == 'int':
        return _INT_TEXT.fullmatch(value) is not None and matcher[1] <= int(value) <= matcher[2]
    if kind == 'ratio':
        a, sep, b = value.partition('/')
        return (bool(sep) and _matches(_int(matcher[1]), a) and _matches(_int(matcher[1]), b)
                and not a.startswith('-') and not b.startswith('-') and int(a) <= int(b))
    if kind == 'date':
        return value in _DATES
    if kind == 'list':
        items = value.split(matcher[4])
        return matcher[2] <= len(items) <= matcher[3] and all(_matches(matcher[1], item) for item in items)
    if kind == 'either':
        return any(_matches(m, value) for m in matcher[1])
    return False


def checked_line(line):
    """Every printed line: a kind of LINE_SPECS with exactly one of its ordered key lists, each value matching its pattern.
    Raises ValueError('line') otherwise, so a price, a price-derived number or a value comparison can never be printed."""
    if not isinstance(line, str):
        raise ValueError('line')
    words = line.split(' ')
    specs = LINE_SPECS.get(words[0])
    if not specs or re.search(r'[0-9]\.[0-9]', line):
        raise ValueError('line')
    pairs = [word.partition('=') for word in words[1:]]
    if any(not sep for _, sep, _ in pairs):
        raise ValueError('line')
    for spec in specs:
        if [key for key, _, _ in pairs] == [key for key, _ in spec] and \
                all(_matches(matcher, value) for (_, _, value), (_, matcher) in zip(pairs, spec)):
            return line
    raise ValueError('line')


def private_line(line):
    """Private manifest lines: value-free codes too (fixed prefix, closed character set, no decimal); never printed."""
    words = line.split(' ')
    if not re.fullmatch(r'ALPSAMPLE_PRIVATE_[A-Z_]+', words[0]) or re.search(r'[0-9]\.[0-9]', line):
        raise ValueError('private_line')
    for word in words[1:]:
        key, sep, value = word.partition('=')
        if not sep or not re.fullmatch(r'[a-z][a-z0-9_]*', key) or not _TOKEN.fullmatch(value):
            raise ValueError('private_line')
    return line


# ---- private raw store (create-only) -------------------------------------------------------------------------------------
def release_tag(run_id):
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise StorageError('RUN_ID_INVALID')
    return TAG_PREFIX + run_id


class _BudgetOpener:
    """Opener handed to raw_store_release.http: redirects are not followed (as there) and every socket operation waits at
    most GH_TIMEOUT_S and never past the store's time budget (instead of raw_store_release's 600 s)."""

    def __init__(self, remaining):
        self._remaining = remaining
        self._opener = urllib.request.build_opener(raw_store_release._NoRedirect)

    def open(self, request, timeout=None):
        return self._opener.open(request, timeout=max(1.0, min(GH_TIMEOUT_S, self._remaining())))


class RawStore:
    """The only GitHub routes this tool may call, for one fixed tag: the repository, the tag lookup and the release create;
    after the create only uploads to the created release id and the download of this run's own asset id. `call` has
    raw_store_release.http's signature."""

    def __init__(self, tag, call=None, *, sleep=time.sleep, clock=time.monotonic):
        if not re.fullmatch(re.escape(TAG_PREFIX) + r'[0-9]{1,20}', tag or ''):
            raise StorageError('TAG_INVALID')
        self.tag = tag
        self._call = call or raw_store_release.http
        self._sleep, self._clock = sleep, clock
        self._repo = f'{GH_API}/repos/{RAW_REPO}'
        self._tag_url = f'{self._repo}/releases/tags/{tag}'
        self._release_id = None
        self._asset_ids = set()
        self._deadline = None
        self._opener = _BudgetOpener(self._remaining)
        self.retries = 0

    def _remaining(self):
        return GH_TIMEOUT_S if self._deadline is None else self._deadline - self._clock()

    def _upload_url(self, name):
        return f'{GH_UPLOADS}/repos/{RAW_REPO}/releases/{self._release_id}/assets?name={urllib.parse.quote(name)}'

    def allowed(self, method, url):
        if (method, url) in {('GET', self._repo), ('GET', self._tag_url)}:
            return True
        if (method, url) == ('POST', f'{self._repo}/releases'):
            return self._release_id is None
        if method == 'POST' and self._release_id is not None:
            return url in {self._upload_url(self.tag + '.zip'), self._upload_url(self.tag + '.zip.sha256')}
        if method == 'GET':
            return url in {f'{self._repo}/releases/assets/{i}' for i in self._asset_ids}
        return False

    def _wait(self, seconds):
        """One retry wait, capped by the time left; none once the budget is spent."""
        left = self._remaining()
        if left <= 0:
            raise StorageError('TIME_BUDGET')
        self.retries += 1
        self._sleep(min(seconds, left))

    def _send(self, send, retry=True):
        """(status, headers, body); 5xx and network errors are retried (bounded, inside the time budget)."""
        waits = STORAGE_RETRY_WAITS_S if retry else ()
        status = None
        for attempt in range(len(waits) + 1):
            if attempt:
                self._wait(waits[attempt - 1])
            if self._remaining() <= 0:
                raise StorageError('TIME_BUDGET')
            try:
                status, headers, body = send()
            except raw_store_release.ReleaseError:
                raise StorageError('TOKEN_MISSING') from None
            except (OSError, http.client.HTTPException, ValueError):
                status, headers, body = None, {}, b''
            if status is not None and not 500 <= status <= 599:
                return status, headers or {}, body
        raise StorageError('NETWORK' if status is None else 'HTTP5XX')

    def http(self, method, url, *, retry=True, **kwargs):
        if not self.allowed(method, url):
            raise StorageError('ROUTE_NOT_ALLOWED')

        def send():   # a fresh headers dict per attempt (raw_store_release.http pops Accept from it)
            fresh = dict(kwargs, headers=dict(kwargs['headers'])) if kwargs.get('headers') else dict(kwargs)
            return self._call(method, url, opener=self._opener, **fresh)
        return self._send(send, retry)

    def _tag_absent(self):
        status, _, _ = self.http('GET', self._tag_url)
        if status == 200:
            raise StorageError('RELEASE_TAG_EXISTS')
        if status != 404:
            raise StorageError('RELEASE_LOOKUP_FAILED')

    def _checks(self):
        status, _, body = self.http('GET', self._repo)
        try:
            private = status == 200 and json.loads(body).get('private') is True
        except (ValueError, AttributeError, TypeError):
            private = False
        if not private:
            raise StorageError('PRIVATE_STORAGE_PREFLIGHT_FAILED')
        self._tag_absent()

    def preflight(self):
        """Before any Alpaca request: the raw repository answers private and the run's tag does not exist."""
        self._deadline = self._clock() + PREFLIGHT_BUDGET_S
        self._checks()

    def _create(self):
        """The release id. A retried create first looks the tag up again: a release that appeared only after this run's own
        failed create call is this run's creation and is taken over only when it is empty (no asset)."""
        payload = json.dumps({'tag_name': self.tag, 'name': self.tag, 'body': RELEASE_BODY, 'draft': False,
                              'prerelease': False}).encode()
        tries = len(STORAGE_RETRY_WAITS_S) + 1
        for attempt in range(tries):
            if attempt:
                self._wait(STORAGE_RETRY_WAITS_S[attempt - 1])
                status, _, body = self.http('GET', self._tag_url)
                if status == 200:
                    found = _json_dict(body)
                    if found.get('tag_name') != self.tag or found.get('assets') != [] or found.get('draft') is not False:
                        raise StorageError('RELEASE_TAG_EXISTS')
                    return found.get('id')
                if status != 404:
                    raise StorageError('RELEASE_LOOKUP_FAILED')
            try:
                status, _, body = self.http('POST', f'{self._repo}/releases', retry=False, data=payload,
                                            headers={'Content-Type': 'application/json'})
            except StorageError as exc:
                if exc.code in ('NETWORK', 'HTTP5XX') and attempt + 1 < tries:
                    continue
                raise
            release = _json_dict(body) if status == 201 else {}
            if release.get('tag_name') != self.tag:
                raise StorageError('RELEASE_CREATE_FAILED')
            return release.get('id')
        raise StorageError('RELEASE_CREATE_FAILED')

    def store(self, archive):
        """Re-check privacy and tag absence, create the release (never reuse one), upload the zip and its .sha256, download
        the zip back and compare."""
        self._deadline = self._clock() + STORAGE_BUDGET_S
        self._checks()
        digest = hashlib.sha256(archive).hexdigest()
        release_id = self._create()
        if type(release_id) is not int or release_id <= 0:
            raise StorageError('RELEASE_CREATE_FAILED')
        self._release_id = release_id
        asset_id = None
        name = self.tag + '.zip'
        for asset, data, kind in ((name, archive, 'application/zip'),
                                  (name + '.sha256', f'{digest}  {name}\n'.encode(), 'text/plain')):
            status, _, body = self.http('POST', self._upload_url(asset), data=data, headers={'Content-Type': kind})
            if status != 201:
                raise StorageError('ASSET_UPLOAD_FAILED')
            if asset == name:
                asset_id = _json_dict(body).get('id')
        if type(asset_id) is not int or asset_id <= 0:
            raise StorageError('ASSET_UPLOAD_FAILED')
        self._asset_ids.add(asset_id)
        status, headers, body = self.http('GET', f'{self._repo}/releases/assets/{asset_id}',
                                          headers={'Accept': 'application/octet-stream'})
        if status in (301, 302, 303, 307, 308):
            location = headers.get('Location') or headers.get('location') or ''
            parts = urllib.parse.urlsplit(location)
            if parts.scheme != 'https' or not (parts.hostname or '').endswith('.githubusercontent.com'):
                raise StorageError('ASSET_REDIRECT_INVALID')
            status, _, body = self._send(lambda: self._call(   # the signed download URL gets no token
                'GET', location, headers={'Accept': 'application/octet-stream'}, auth=False, opener=self._opener))
        if status != 200 or hashlib.sha256(body or b'').hexdigest() != digest:
            raise StorageError('ROUNDTRIP_MISMATCH')
        return digest


def _json_dict(body):
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def build_archive(securities, series_plan, results, lines, private_lines, *, run_id, code_sha, stopped, created_at):
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
                        'expect': series['expect'], 'legs': list(series['legs']) if series.get('legs') else None,
                        'sids': series['sids'], 'status': result['status'], 'pages': pages})
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
        'private_lines': private_lines,
        'private_lines_note': 'value-comparison codes (vs_raw, legs_vs_raw, overlap, OK/BAD); never printed or published',
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
    return checked_line(f'ALPSAMPLE_STOP reason={reason if _CODE.fullmatch(reason or "") else "OTHER"}')


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
        store = RawStore(release_tag(run_id), github_call, sleep=sleep, clock=clock)
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
        lines, private = summarize(securities, by_symbol, series_plan, results)
    except Exception as exc:  # noqa: BLE001 - class name only; the raw pages are still stored below
        lines, private = [stop_line('SUMMARY_FAILED_' + type(exc).__name__)], []
    for line in lines:
        out(line)
    c = client.counts
    out(checked_line(
        f"ALPSAMPLE_REQUESTS series={len(series_plan)} series_done="
        f"{sum(results[s['id']]['status'] != 'NOT_RUN' for s in series_plan)} total={c['total']} "
        f"pages={sum(len(r['pages']) for r in results.values())} retries={c['retries']} http400={c['http400']} "
        f"http401={c['http401']} http403={c['http403']} http404={c['http404']} http422={c['http422']} "
        f"http429={c['http429']} http5xx={c['http5xx']} http_other={c['http_other']} network={c['network']} "
        f"elapsed_s={min(int(client.elapsed()), 3600)} stopped={stopped}"))
    sha = environ.get('GITHUB_SHA') or ''
    created = (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    archive, n_files = build_archive(securities, series_plan, results, lines, private, run_id=run_id,
                                     code_sha=sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None, stopped=stopped,
                                     created_at=created)
    for result in results.values():   # the prices leave RAM only inside the archive
        result['bars'] = {}
    private = None
    try:
        store.store(archive)
    except StorageError as exc:
        out(checked_line(f'ALPSAMPLE_STORAGE status=FAILED code={exc.code} retries={min(store.retries, 99)}'))
        return 3
    out(checked_line(f'ALPSAMPLE_STORAGE status=STORED release={store.tag} files={n_files} roundtrip=SHA256_MATCH '
                     f'retries={min(store.retries, 99)}'))
    return 0 if stopped == 'NONE' else 3


if __name__ == '__main__':
    try:
        code = main()
    except (Exception, KeyboardInterrupt) as exc:
        name = type(exc).__name__
        print(f'ALPSAMPLE_STOP reason=UNEXPECTED class={name if _CODE.fullmatch(name) else "OTHER"}', flush=True)
        code = 1
    sys.exit(code)
