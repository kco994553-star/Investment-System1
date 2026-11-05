"""Build the SYNTHETIC technical-offline-display/1 fixture for the 기술적 분석 per-company indicator block.

Development check only. The values are produced by Codex's own offline tool (#478 head 419add34,
tools/technical_display_offline.py) run on hand-made SYNTHETIC daily bars; no provider, no network, no
real price. Main does not compute any indicator (DC-42): this script only writes the synthetic input,
runs Codex's CLI from an extracted copy of the PR tree and wraps the output with data_kind SYNTHETIC.

Series (one signal day, the 250th NYSE session from 2017-01-03; symbols are SYN_* and never a company):
  SYN_VALUE     the contract example: close 1..250, high close+1, low close-0.5, open close, volume 100,
                full identity / no-split / currency evidence -> every component VALUE
  SYN_SPLIT120  same bars, no-split evidence only for the last 120 bars -> rolling VALUE, recursive DIAGNOSTIC
  SYN_IDENTITY  closes offset by 0.3125, identity UNKNOWN -> every component DIAGNOSTIC (raw kept, value null)
  SYN_FLAT35    the last 35 sessions at a flat close 10 -> RSI NOT_COMPUTED (ZERO_TOTAL_CHANGE), SMA60/120 WARMUP,
                MACD a real 0 VALUE
  SYN_NOHIGH    SYN_VALUE with the last high missing -> ATR NOT_COMPUTED, warm-up NOT_EVALUATED
  SYN_EMPTY     no rows -> every component NOT_COMPUTED

Usage (CODEX = a folder holding `git archive refs/remotes/pr/478 implementation/src implementation/tools/technical_display_offline.py`):
  python3 -I tools/build_tech_display_fixture.py --codex CODEX --out tests/fixtures/technical_offline_display_synthetic.json

--adjusted (Codex #498 head 5597e25e, TECHNICAL_ADJUSTED_LINK_20261105.md; CODEX = a checkout of that head incl. implementation/tests):
the same direct-kernel tool, now with price_basis SPLIT_ADJUSTED, on #498's own synthetic contract
(tests/research/test_adjusted_technical_link.py case(): one confirmed 2:1 split on 2016-07-01, price 100 after rebasing). The rows
and evidence are the ones kis_price_bridge.analyze hands to measure_display (price_rows, basis_evidence); the KIS wrapper fields
(kis-bars/1/analysis) are not used. Series (signal day 2017-01-06; SYN_* only):
  SYN_ADJ_FULL      adjusted, action coverage for the whole input -> CONFIRMED_SPLITS_ONLY, RSI NOT_COMPUTED (ZERO_TOTAL_CHANGE)
  SYN_RAW_REF       the unsplit RAW reference path (no_split_* evidence) -> DOCUMENTED_NO_SPLIT, the same adopted values
  SYN_ADJ_LAST120   adjusted, coverage for the last 120 sessions only -> rolling adopted, recursive UNCONFIRMED (diagnostic)
  SYN_ADJ_NOCOVER   adjusted, no coverage range -> every window UNCONFIRMED, evidence null
  python3 -I tools/build_tech_display_fixture.py --adjusted --codex CODEX --out tests/fixtures/technical_offline_display_adjusted_synthetic.json
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

CODEX_HEAD = '419add34'
ADJUSTED_HEAD = '5597e25e'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--codex', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--adjusted', action='store_true')
    args = parser.parse_args()
    codex = args.codex.resolve()
    sys.path.insert(0, str(codex / 'implementation/src'))
    if args.adjusted:
        return adjusted(codex, args.out)
    from investment_system.research.exp_deciles import schedule  # Codex's NYSE calendar, read only

    days, d = [], date(2017, 1, 3)
    while len(days) < 250:
        if schedule.is_session(d):
            days.append(d.isoformat())
        d += timedelta(days=1)

    def ts(day: str) -> str:
        return datetime.combine(date.fromisoformat(day), time(), ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()

    def rows(symbol: str, dates: list[str], close) -> list[dict]:
        out = []
        for i, day in enumerate(dates):
            c = close(i)
            out.append(dict(date=day, close=str(c), open=str(c), high=str(c + 1), low=str(c - 0.5), volume='100', price_basis='RAW',
                            quality_reasons=[], requested_symbol=symbol, returned_symbol=symbol, asof='-', source_sha256='a' * 64,
                            source_timestamp=ts(day)))
        return out

    def evidence(start: str, **change) -> dict:
        e = dict(identity_status='DOCUMENT_RECONSTRUCTED', identity_reference='synthetic', no_split_start=start, no_split_end=days[-1],
                 no_split_reference='synthetic', currency='USD', currency_reference='synthetic')
        e.update(change)
        return e

    series = []

    def add(symbol: str, r: list[dict], e: dict) -> None:
        series.append(dict(series_id='SYNTHETIC:' + symbol, symbol=symbol, source_kind='NORMALIZED_PROVIDER_DAILY_BARS', rows=r, evidence=e))

    add('SYN_VALUE', rows('SYN_VALUE', days, lambda i: i + 1), evidence(days[0]))
    add('SYN_SPLIT120', rows('SYN_SPLIT120', days, lambda i: i + 1), evidence(days[-120]))
    add('SYN_IDENTITY', rows('SYN_IDENTITY', days, lambda i: i + 1.3125), evidence(days[0], identity_status='UNKNOWN'))
    flat = rows('SYN_FLAT35', days[-35:], lambda i: 10)
    for r in flat:
        r.update(high='11', low='9')
    add('SYN_FLAT35', flat, evidence(days[-35]))
    nohigh = rows('SYN_NOHIGH', days, lambda i: i + 1)
    nohigh[-1].update(high=None, quality_reasons=['HIGH_MISSING'])
    add('SYN_NOHIGH', nohigh, evidence(days[0]))
    add('SYN_EMPTY', [], evidence(days[0]))

    display = run(codex, days[-1], series)
    fixture = {
        'data_kind': 'SYNTHETIC',
        'description': 'SYNTHETIC bars only (no company, no real price). Output of Codex tools/technical_display_offline.py at #478 '
                       + CODEX_HEAD + ', unchanged; built by tools/build_tech_display_fixture.py.',
        'symbols': [s['symbol'] for s in series],
        'display': display,
    }
    args.out.write_text(json.dumps(fixture, indent=1, allow_nan=False) + '\n')


def run(codex: Path, signal_day: str, series: list[dict]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        source, out = Path(tmp) / 'input.json', Path(tmp) / 'out' / 'display.json'
        source.write_text(json.dumps({'signal_day': signal_day, 'series': series}))
        subprocess.run([sys.executable, '-I', str(codex / 'implementation/tools/technical_display_offline.py'), '--input', str(source), '--output', str(out)],
                       check=True, stdout=subprocess.DEVNULL)
        return json.loads(out.read_text())


def adjusted(codex: Path, target: Path) -> None:
    sys.path.insert(0, str(codex / 'implementation/tests/research'))
    from test_adjusted_technical_link import case  # Codex's synthetic contract, read only
    from investment_system.research import kis_price_bridge as kb
    signal = '2017-01-06'
    series = []

    def add(symbol: str, c: dict, cover_from: str | None) -> None:
        # As kis_price_bridge.analyze builds the direct-kernel input (rows through S, coverage range -> basis evidence).
        c['confirmed_ranges'] = [] if cover_from is None else [{'from': cover_from, 'to': signal, 'evidence': 'SYNTHETIC_COMPLETE_ACTION_COVERAGE'}]
        kb.validate_contract(c)
        rows = kb.price_rows(c, signal)
        evidence = {**c['identity'], 'security_id': c['security_id'], 'currency': c['currency'], 'currency_reference': c['currency_reference']}
        if c['confirmed_ranges']:
            r = c['confirmed_ranges'][0]
            evidence.update(no_split_start=r['from'], no_split_end=r['to'], no_split_reference=r['evidence'])
        kb.basis_evidence(evidence, c)
        bars = [{'date': r['date'], **{f: r[f] for f in kb.FIELDS[:5]}, 'returned_symbol': symbol, 'requested_symbol': symbol,
                 'price_basis': c['basis'], 'asof': '-', 'source_timestamp': kb._stamp(r['date']).isoformat(),
                 'source_sha256': r['source_sha256'], 'quality_reasons': []} for r in rows]
        series.append(dict(series_id='SYNTHETIC:' + symbol, symbol=symbol, source_kind='NORMALIZED_PROVIDER_DAILY_BARS', rows=bars, evidence=evidence))

    first = case()['raw_bars'][0]['date']
    add('SYN_ADJ_FULL', case(), first)
    add('SYN_RAW_REF', case(False), first)
    add('SYN_ADJ_LAST120', case(), case()['raw_bars'][-120]['date'])
    add('SYN_ADJ_NOCOVER', case(), None)
    display = run(codex, signal, series)
    fixture = {
        'data_kind': 'SYNTHETIC',
        'description': 'SYNTHETIC bars only (no company, no real price): Codex #498 test_adjusted_technical_link case(). Output of Codex '
                       'tools/technical_display_offline.py at #498 ' + ADJUSTED_HEAD + ', unchanged; built by tools/build_tech_display_fixture.py --adjusted.',
        'symbols': [s['symbol'] for s in series],
        'display': display,
    }
    target.write_text(json.dumps(fixture, indent=1, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
