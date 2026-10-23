"""IEX HIST feasibility probe (owner decision 2026-10-23: IEX HIST as the central V price source; validate first).

Streams one trading day's TOPS 1.6 file (curl | gzip -dc | iex_last_trade, nothing written to disk) and reports, counts only:
download+parse time, peak disk use, symbols with a regular-session last trade, odd-lot-only and no-trade symbols (codes only).
Prices stay in this process's memory and are dropped: never printed, logged, written or uploaded (GSQ-010).

    python implementation/tools/iex_hist/probe.py --parser <iex_last_trade binary> [--date YYYYMMDD] [--max-bytes N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import resource
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from investment_system.universe.universe_codes import public_payload  # noqa: E402

HIST = 'https://iextrading.com/api/1.0/hist'
EXTRA = ('SPY', 'HYG', 'IEF')  # benchmark and macro-light ETFs
FEED = ('TOPS', '1.6')
LIMITS = {'max_minutes': 45, 'max_disk_gb': 10, 'max_missing_ratio': 0.05}
NY = ZoneInfo('America/New_York')


def hist_index(date: str | None):
    url = HIST + (f'?date={date}' if date else '')
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    if date:
        return date, data
    days = sorted(d for d, feeds in data.items() if any((f['feed'], f['version']) == FEED for f in feeds))
    return days[-1], data[days[-1]]


def symbols():
    codes = public_payload()['codes']
    return codes, [c.split(':', 1)[1] for c in codes] + list(EXTRA)


def session_ns(day: str):
    d = dt.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    start = dt.datetime.combine(d, dt.time(9, 30), NY)
    end = dt.datetime.combine(d, dt.time(16, 0), NY)
    return int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--parser', required=True)
    ap.add_argument('--date')
    ap.add_argument('--max-bytes', type=int, help='local smoke test only: stop after N compressed bytes')
    ap.add_argument('--workdir', default=os.environ.get('RUNNER_TEMP', '/tmp'))
    ap.add_argument('--extra', default=os.environ.get('PROBE_EXTRA', ''), help='comma-separated extra symbols (listing diagnostics)')
    a = ap.parse_args()
    day, feeds = hist_index(a.date)
    feed = next(f for f in feeds if (f['feed'], f['version']) == FEED)
    codes, syms = symbols()
    extra_syms = [x.strip().upper() for x in a.extra.split(',') if x.strip()]
    syms = syms + [x for x in extra_syms if x not in syms]
    work = Path(a.workdir) / 'iex-probe'
    work.mkdir(parents=True, exist_ok=True)
    symfile = work / 'symbols.txt'
    symfile.write_text('\n'.join(syms) + '\n', encoding='ascii')  # public tickers only
    t0, t1 = session_ns(day)
    disk0 = shutil.disk_usage(a.workdir).used
    peak = [0]
    stop = threading.Event()

    def watch():
        while not stop.wait(2):
            peak[0] = max(peak[0], shutil.disk_usage(a.workdir).used - disk0)
    threading.Thread(target=watch, daemon=True).start()
    curl = ['curl', '-sS', '--fail', '--retry', '3', '-o', '-', '-w', '%{stderr}#CURL bytes=%{size_download} seconds=%{time_total}\n']
    if a.max_bytes:
        curl += ['-r', f'0-{a.max_bytes - 1}']
    curl.append(feed['link'])
    started = time.monotonic()
    p1 = subprocess.Popen(curl, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1.stdout.close()
    p3 = subprocess.Popen([a.parser, str(symfile), str(t0), str(t1)], stdin=p2.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2.stdout.close()
    out, err3 = p3.communicate()
    err2 = p2.communicate()[1]
    err1 = p1.communicate()[1]
    elapsed = time.monotonic() - started
    stop.set()
    peak[0] = max(peak[0], shutil.disk_usage(a.workdir).used - disk0)
    rss_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    rows = {}
    for line in out.decode('ascii').splitlines():
        sym, status, px, _ts, n, dir_seen, last_status, all_trades = line.split('\t')
        rows[sym] = (status, int(px) > 0 if status != 'NO_TRADE' else False, int(n), dir_seen == '1', last_status, int(all_trades))
    del out  # prices are not kept past this point
    by = {s: rows.get(s, ('NO_TRADE', False, 0, False, '-', 0)) for s in syms}
    diag = {s: {'status': by[s][0], 'directory': by[s][3], 'trading_status': by[s][4], 'regular_trades': by[s][2], 'all_trades': by[s][5]}
            for s in [c.split(':', 1)[1] for c in codes if by[c.split(':', 1)[1]][0] != 'ROUND'] + extra_syms}
    # IEX sends Security Directory messages only for IEX-listed securities; a Trading Status message comes for every symbol
    # IEX trades, so a code with neither a status message nor a trade is not traded on IEX under that symbol that day.
    no_status = [c for c in codes if by[c.split(':', 1)[1]][4] == '-' and by[c.split(':', 1)[1]][5] == 0]
    universe = [c for c in codes if by[c.split(':', 1)[1]][0] == 'NO_TRADE']
    odd = [c for c in codes if by[c.split(':', 1)[1]][0] == 'ODD_ONLY']
    extra = {s: by[s][0] for s in EXTRA}
    stats = next((l for l in err3.decode(errors='replace').splitlines() if l.startswith('#STATS')), '')
    curl_line = next((l for l in err1.decode(errors='replace').splitlines() if l.startswith('#CURL')), '')
    missing_ratio = len(universe) / len(codes)
    report = {
        'date': day, 'feed': '/'.join(FEED), 'compressed_gb': round(int(feed['size']) / 1e9, 2), 'smoke_test_bytes': a.max_bytes,
        'elapsed_minutes': round(elapsed / 60, 1), 'curl': curl_line.replace('#CURL ', ''), 'parser': stats.replace('#STATS ', ''),
        'peak_disk_mb': round(peak[0] / 1e6, 1), 'peak_child_rss_mb': round(rss_mb, 1),
        'universe': len(codes), 'universe_round_lot_last_trade': sum(by[c.split(':', 1)[1]][0] == 'ROUND' for c in codes),
        'universe_odd_lot_only': odd, 'universe_no_trade': universe, 'etf': extra,
        'positive_price_count': sum(1 for s in syms if by[s][1]),
        'listing_diagnostics': diag, 'universe_without_iex_status_or_trade': no_status,
        'gzip_stderr_lines': len(err2.splitlines()), 'exit_codes': [p1.returncode, p2.returncode, p3.returncode],
        'limits': LIMITS,
    }
    report['verdict'] = 'PASS' if (a.max_bytes is None and report['elapsed_minutes'] <= LIMITS['max_minutes']
                                    and report['peak_disk_mb'] <= LIMITS['max_disk_gb'] * 1000
                                    and missing_ratio <= LIMITS['max_missing_ratio'] and p3.returncode == 0) else (
        'SMOKE_ONLY' if a.max_bytes else 'FAIL')
    text = json.dumps(report, ensure_ascii=False, indent=1)
    print(text)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write('## IEX HIST probe (counts only, no prices)\n\n```json\n' + text + '\n```\n')
    symfile.unlink()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
