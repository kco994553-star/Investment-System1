#!/usr/bin/env python3
"""One-off private IEX HIST day store for QGV 555 V (owner approval 2026-11-14: "555 V 연결용으로 2026-11-04 IEX HIST 파일 1회
수집"; route choice 2026-11-14: a one-off tool added to public_price_boundary.ACTIONS_PRICE_ROUTES on the unmerged run branch
claude/iex-day-20261104-once only, like the U8 month-end store of 2026-10-23).

The same IEX functions and checks as the central V publication (providers/iex_hist): hist index -> select_day (NYSE session days
only) -> GCS size + md5 -> stream_attempts(stream_day: download | md5/size count | gzip -dc | tools/iex_tops/iex_last_trade.c).
The parser takes at most 1024 symbols per run, so the request is split into shards (one stream of the whole file per shard). The
day is exact: an index day other than the requested one is refused (NOT_REQUESTED_DAY), never substituted.
Prices exist in this process and in ONE gzip JSON (schema iex-day/1) sent to a private release of the raw repository through
sec_universe_shares.upload_raw (tag iex-day-YYYYMMDD-shardI, asset <tag>.tar.gz + .sha256), then removed from disk. Nothing goes
to a Pages artifact, a job summary, an artifact upload, a cache or the log: stdout is one line of counts, sizes and hashes.
Values are IEX last regular-session trades AS TRADED (no split adjustment), not official closes.

  python implementation/tools/iex_day_private_once.py --day 2026-11-04 --request <iex-day-request/1 JSON> --shard I --shards N \
      --parser <compiled iex_last_trade> [--token-env RAW_REPO_TOKEN]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

STARTED = time.monotonic()
STEP_LIMIT_S = 25 * 60
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.providers import iex_hist  # noqa: E402

SCHEMA = 'iex-day/1'
REQUEST_SCHEMA = 'iex-day-request/1'
MAX_SYMBOLS = 1000          # under the parser's 1024


def private_day(*, day: str, request: Path, shard: int, shards: int, parser: str, workdir: Path, token, deadline,
                fetch=None, stream=None, store=None) -> str:
    fetch = fetch or iex_hist.fetch_json
    stream = stream or iex_hist.stream_day
    if store is None:
        import sec_universe_shares
        store = sec_universe_shares.upload_raw
    if not token:
        return 'IEX_DAY status=NOT_RUN reason=TOKEN_MISSING'
    raw = Path(request).read_bytes()
    req = json.loads(raw)
    if req.get('schema_version') != REQUEST_SCHEMA or req.get('day') != day or not isinstance(req.get('codes'), list):
        return 'IEX_DAY status=REFUSED reason=REQUEST_INVALID'
    mine = sorted(set(req['codes']))[shard::shards]
    index = fetch(iex_hist.HIST_URL)
    got_day, entry = iex_hist.select_day(index, dt.date.fromisoformat(day))
    if iex_hist._iso(got_day) != day:
        return 'IEX_DAY status=REFUSED reason=NOT_REQUESTED_DAY'
    size, md5 = iex_hist.file_checks(entry, fetch)
    symbol_of = iex_hist.resolve_symbols({c: c for c in mine}, got_day)
    wanted = sorted({s for s in symbol_of.values() if iex_hist.valid_symbol(s)})
    if not 0 < len(wanted) <= MAX_SYMBOLS:
        return 'IEX_DAY status=REFUSED reason=SHARD_SIZE'
    rows, trail = iex_hist.stream_attempts(stream, entry['link'], wanted, deadline=deadline, day=got_day, size=size, md5=md5,
                                           parser=parser, workdir=workdir)
    symbols = {sym: {'status': st, 'price_e4': px} for sym, (st, px) in sorted(rows.items())}
    del rows
    counts: dict = {}
    for v in symbols.values():
        counts[v['status']] = counts.get(v['status'], 0) + 1
    payload = {'schema_version': SCHEMA, 'visibility': 'PRIVATE_RESEARCH', 'day': day, 'provider': iex_hist.PROVIDER,
               'feed': list(iex_hist.FEED), 'basis_kind': iex_hist.BASIS_KIND, 'adjustment_basis': iex_hist.ADJUSTMENT_BASIS,
               'currency': iex_hist.CURRENCY, 'label_ko': iex_hist.LABEL_KO, 'attribution': iex_hist.ATTRIBUTION,
               'terms_url': iex_hist.TERMS_URL, 'file': {'size': size, 'md5': md5}, 'shard': shard, 'shards': shards,
               'request_sha256': hashlib.sha256(raw).hexdigest(), 'codes': {c: symbol_of[c] for c in mine},
               'symbols': symbols, 'stream_attempts': trail['attempts']}
    tag = 'iex-day-' + day.replace('-', '') + '-shard' + str(shard)
    out_dir = workdir / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / 'iex-day.json'
    target.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')), 'utf-8')
    del payload, symbols
    try:
        status = store(out_dir, tag=tag, token=token)
    finally:
        target.unlink(missing_ok=True)
    unmapped = len(mine) - sum(1 for c in mine if iex_hist.valid_symbol(symbol_of[c]))
    ok = isinstance(status, str) and status.startswith('RAW_UPLOADED')
    return (f'IEX_DAY status={"OK" if ok else "STORE_FAILED"} day={day} tag={tag} codes={len(mine)} symbols={len(wanted)} '
            f'unmapped={unmapped} statuses={json.dumps(counts, sort_keys=True, separators=(",", ":"))} '
            f'attempts={trail["attempts"]} file_size={size} store={status}')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--day', required=True)
    ap.add_argument('--request', required=True)
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--shards', type=int, required=True)
    ap.add_argument('--parser', required=True)
    ap.add_argument('--token-env', default='RAW_REPO_TOKEN', help='NAME of the env var holding the raw repo write token')
    ap.add_argument('--workdir', default=os.environ.get('RUNNER_TEMP') or tempfile.gettempdir())
    a = ap.parse_args(argv)
    token = os.environ.pop(a.token_env, '') or None     # held by this process only: curl, gzip and the parser never inherit it
    if not 0 <= a.shard < a.shards:
        print('IEX_DAY status=REFUSED reason=USAGE')
        return 2
    try:
        line = private_day(day=a.day, request=Path(a.request), shard=a.shard, shards=a.shards, parser=a.parser,
                           workdir=Path(a.workdir) / 'iex-day', token=token, deadline=STARTED + STEP_LIMIT_S)
    except iex_hist.IexHistError as e:
        line = f'IEX_DAY status=FAILED reason={e}'
    except Exception as e:  # noqa: BLE001 - the class name only, never a value
        line = f'IEX_DAY status=FAILED reason={type(e).__name__}'
    print(line)
    return 0 if ' status=OK ' in line or line.startswith('IEX_DAY status=OK ') else 1


if __name__ == '__main__':
    raise SystemExit(main())
