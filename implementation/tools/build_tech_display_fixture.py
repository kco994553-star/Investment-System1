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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--codex', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    codex = args.codex.resolve()
    sys.path.insert(0, str(codex / 'implementation/src'))
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

    with tempfile.TemporaryDirectory() as tmp:
        source, out = Path(tmp) / 'input.json', Path(tmp) / 'out' / 'display.json'
        source.write_text(json.dumps({'signal_day': days[-1], 'series': series}))
        subprocess.run([sys.executable, '-I', str(codex / 'implementation/tools/technical_display_offline.py'), '--input', str(source), '--output', str(out)],
                       check=True, stdout=subprocess.DEVNULL)
        display = json.loads(out.read_text())
    fixture = {
        'data_kind': 'SYNTHETIC',
        'description': 'SYNTHETIC bars only (no company, no real price). Output of Codex tools/technical_display_offline.py at #478 '
                       + CODEX_HEAD + ', unchanged; built by tools/build_tech_display_fixture.py.',
        'symbols': [s['symbol'] for s in series],
        'display': display,
    }
    args.out.write_text(json.dumps(fixture, indent=1, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
