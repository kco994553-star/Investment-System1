"""U8 one-off backfill: V4 month-end prices from IEX HIST TOPS files (owner decision GSQ-024, 2026-10-23).

For the months of matrix shard i of n (monthend_plan.shard_months), streams each file curl | (md5 + size check) | gzip -dc |
iex_last_trade (nothing written to disk but the ticker list), keeps the last regular-session trade per requested symbol in RAM and,
after every month of the shard succeeded, writes ONE gzip JSON as a new private release asset in the raw repository
(sec_universe_shares.upload_raw_bytes, the same path and headers as the daily raw SEC upload; tag iex-v4-monthend-YYYYMMDD-shardI):

    {schema: 'iex-monthend/1', months: {YYYY-MM: {date, symbols: {SYM: {status, price_e4, ts_ns, n}}, codes: {code: SYM}}}, ...}

Stdout: counts only (per month: symbols requested / ROUND / ODD_ONLY / NO_TRADE, minutes). No price, yield or per-symbol hash is
printed, logged, cached or uploaded anywhere but that private asset (GSQ-010). Any failure exits non-zero before the upload.

    python implementation/tools/iex_hist/monthend_backfill.py --parser BIN --plan plan.json --shard I --shards N --stamp YYYYMMDD
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from monthend_plan import SCHEMA as PLAN_SCHEMA, shard_months  # noqa: E402
from probe import session_ns  # noqa: E402

SCHEMA = 'iex-monthend/1'
TAG_PREFIX = 'iex-v4-monthend-'
RELEASE_BODY = 'Private IEX HIST month-end last regular-session trades for the V4 backfill, one shard (not published).'
ATTRIBUTION = ('Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data '
               'Terms of Use.')
STATUSES = ('ROUND', 'ODD_ONLY', 'NO_TRADE')
ATTEMPTS = 2
CHUNK = 1 << 22


class BackfillError(RuntimeError):
    """Fixed code only (never a price, URL token or response body)."""


def tag_for(stamp: str, shard: int) -> str:
    if len(stamp) != 8 or not stamp.isdigit():
        raise BackfillError('STAMP_INVALID')
    return f'{TAG_PREFIX}{stamp}-shard{shard}'


def asset_name(tag: str) -> str:
    return tag + '.json.gz'


def load_plan(path: str | None, b64: str | None) -> dict:
    if path:
        plan = json.loads(Path(path).read_text(encoding='utf-8'))
    elif b64:
        plan = json.loads(gzip.decompress(base64.b64decode(b64)))
    else:
        raise BackfillError('PLAN_MISSING')
    if not isinstance(plan, dict) or plan.get('schema') != PLAN_SCHEMA or not plan.get('months'):
        raise BackfillError('PLAN_INVALID')
    return plan


def parse_rows(text: str, symbols) -> dict:
    """Parser stdout -> {SYM: {status, price_e4, ts_ns, n}} for exactly the requested symbols."""
    rows = {}
    for line in text.splitlines():
        cols = line.split('\t')
        if len(cols) < 5 or cols[1] not in STATUSES:
            raise BackfillError('PARSER_OUTPUT_INVALID')
        sym, status, px, ts, n = cols[0], cols[1], int(cols[2]), int(cols[3]), int(cols[4])
        if status != 'NO_TRADE' and px <= 0:
            raise BackfillError('PARSER_PRICE_INVALID')
        rows[sym] = {'status': status, 'price_e4': px if status != 'NO_TRADE' else None,
                     'ts_ns': ts if status != 'NO_TRADE' else None, 'n': n}
    if set(rows) != set(symbols):
        raise BackfillError('PARSER_SYMBOLS_MISMATCH')
    return rows


def stream_month(month: dict, parser: str, workdir: Path, *, max_bytes: int | None = None, popen=subprocess.Popen) -> dict:
    """One file: curl | md5/size pump | gzip -dc | parser. Returns {SYM: row}; raises BackfillError on any check failure."""
    symfile = workdir / f'symbols-{month["month"]}.txt'
    symfile.write_text('\n'.join(month['symbols']) + '\n', encoding='ascii')  # public tickers only
    t0, t1 = session_ns(month['date'])
    curl = ['curl', '-sS', '--fail', '--retry', '3', '--retry-delay', '10', '-o', '-']
    if max_bytes:
        curl += ['-r', f'0-{max_bytes - 1}']
    curl.append(month['link'])
    p1 = popen(curl, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p2 = popen(['gzip', '-dc'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p3 = popen([parser, str(symfile), str(t0), str(t1)], stdin=p2.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p2.stdout.close()
    out: list[bytes] = []
    reader = threading.Thread(target=lambda: out.append(p3.stdout.read()), daemon=True)
    reader.start()
    md5, size, broken = hashlib.md5(), 0, False
    try:
        while True:
            chunk = p1.stdout.read(CHUNK)
            if not chunk:
                break
            md5.update(chunk)
            size += len(chunk)
            p2.stdin.write(chunk)
    except BrokenPipeError:
        broken = True
    except BaseException:
        for p in (p1, p2, p3):
            p.kill()
        raise
    finally:
        try:
            p2.stdin.close()
        except BrokenPipeError:
            broken = True
    if broken:  # gzip or the parser stopped early: stop the download instead of blocking on its full pipe
        p1.kill()
    codes = (p1.wait(), p2.wait(), p3.wait())
    reader.join()
    symfile.unlink(missing_ok=True)
    if max_bytes:  # local smoke only: truncated input, nothing verified, nothing kept by the caller
        if codes[2] != 0:
            raise BackfillError('PARSER_FAILED')
        return parse_rows(out[0].decode('ascii'), month['symbols'])
    if broken:
        raise BackfillError('GZIP_FAILED')
    if codes[0] != 0:
        raise BackfillError('DOWNLOAD_FAILED')
    if size != month['size']:
        raise BackfillError('SIZE_MISMATCH')
    if month.get('md5') and md5.hexdigest() != month['md5']:
        raise BackfillError('MD5_MISMATCH')
    if codes[1] != 0:
        raise BackfillError('GZIP_FAILED')
    if codes[2] != 0:
        raise BackfillError('PARSER_FAILED')
    return parse_rows(out[0].decode('ascii'), month['symbols'])


def counts_line(month: dict, rows: dict, minutes: float) -> str:
    by = {s: sum(1 for r in rows.values() if r['status'] == s) for s in STATUSES}
    no_trade = sorted(c for c, s in month['codes'].items() if rows[s]['status'] == 'NO_TRADE')
    return (f"month={month['month']} date={month['date']} gb={month['size'] / 1e9:.1f} requested={len(month['symbols'])} "
            f"round={by['ROUND']} odd={by['ODD_ONLY']} no_trade={by['NO_TRADE']} minutes={minutes:.1f} "
            f"no_trade_codes={','.join(no_trade) or '-'}")


def payload(plan: dict, shard: int, shards: int, results: dict) -> bytes:
    by_month = {m['month']: m for m in plan['months']}
    body = {'schema': SCHEMA, 'feed': plan['feed'], 'source': 'IEX HIST last regular-session trade (not an official close)',
            'attribution': ATTRIBUTION, 'shard': shard, 'shards': shards, 'qgv2_as_of': plan.get('qgv2_as_of'),
            'aliases': plan.get('aliases', {}),
            'months': {m: {'date': by_month[m]['date'], 'md5': by_month[m].get('md5'), 'size': by_month[m]['size'],
                           'codes': by_month[m]['codes'], 'symbols': rows} for m, rows in sorted(results.items())}}
    return gzip.compress(json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8'), mtime=0)


def run(plan: dict, *, shard: int, shards: int, parser: str, stamp: str, token: str | None, workdir: Path,
        stream=stream_month, upload=None, max_bytes: int | None = None, clock=time.monotonic) -> int:
    if not 0 <= shard < shards:
        raise BackfillError('SHARD_INVALID')
    tag = tag_for(stamp, shard)
    if not max_bytes and not token:
        raise BackfillError('RAW_UPLOAD_NOT_CONFIGURED')  # fail before any download
    wanted = shard_months(plan, shards)[shard]
    by_month = {m['month']: m for m in plan['months']}
    results = {}
    for name in wanted:
        month = by_month[name]
        started = clock()
        for attempt in range(1, ATTEMPTS + 1):
            try:
                rows = stream(month, parser, workdir, max_bytes=max_bytes)
                break
            except BackfillError as error:
                print(f'month={name} attempt={attempt} failed code={error}')
                if attempt == ATTEMPTS:
                    raise
        print(counts_line(month, rows, (clock() - started) / 60), flush=True)
        if not max_bytes:
            results[name] = rows
        del rows
    if max_bytes:
        print(f'IEX_V4_MONTHEND shard={shard}/{shards} months={len(wanted)} SMOKE_ONLY nothing_uploaded')
        return 0
    body = payload(plan, shard, shards, results)
    if upload is None:
        sys.path.insert(0, str(HERE.parent))
        from sec_universe_shares import upload_raw_bytes as upload  # noqa: PLC0415 (shared raw-upload path)
    status = upload(body, tag=tag, name=asset_name(tag), content_type='application/gzip', token=token, body=RELEASE_BODY)
    del body, results
    print(f'IEX_V4_MONTHEND shard={shard}/{shards} months={len(wanted)} tag={tag} ' + status.split(' sha256=')[0])
    return 0 if status.startswith('RAW_UPLOADED') else 1


def read_shard(tag: str, *, call=None) -> dict:
    """Read one shard asset back from the private release (sha256 asset verified). Raises BackfillError with a fixed code."""
    import urllib.parse  # noqa: PLC0415
    import raw_store_release as rsr  # noqa: PLC0415 (tools/raw_store_release.py: token from RAW_REPO_TOKEN, never printed)
    from sec_universe_shares import RAW_REPO  # noqa: PLC0415
    call = call or rsr.http
    try:
        release = rsr.release_for_tag(RAW_REPO, tag, create=False, call=call)
    except rsr.ReleaseError:
        raise BackfillError('RELEASE_NOT_FOUND') from None

    def asset(name):
        found = next((a for a in release.get('assets', []) if isinstance(a, dict) and a.get('name') == name), None)
        if not found or type(found.get('id')) is not int:
            raise BackfillError('ASSET_MISSING')
        status, headers, data = call('GET', f'{rsr.API}/repos/{RAW_REPO}/releases/assets/{found["id"]}',
                                     headers={'Accept': 'application/octet-stream'})
        if status in (301, 302, 303, 307, 308):
            location = (headers or {}).get('Location') or (headers or {}).get('location')
            if not location or urllib.parse.urlparse(location).scheme != 'https':
                raise BackfillError('ASSET_REDIRECT_INVALID')
            status, _, data = call('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False)
        if status != 200:
            raise BackfillError('ASSET_UNREADABLE')
        return bytes(data)

    name = asset_name(tag)
    data = asset(name)
    if asset(name + '.sha256') != f'{hashlib.sha256(data).hexdigest()}  {name}\n'.encode('ascii'):
        raise BackfillError('SHA256_MISMATCH')
    body = json.loads(gzip.decompress(data))
    if not isinstance(body, dict) or body.get('schema') != SCHEMA or not isinstance(body.get('months'), dict):
        raise BackfillError('SHARD_INVALID')
    return body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--parser', required=True)
    ap.add_argument('--plan', help='plan JSON file (else env PLAN_B64: base64 gzip plan JSON)')
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--shards', type=int, required=True)
    ap.add_argument('--stamp', required=True, help='YYYYMMDD of the run (tag iex-v4-monthend-YYYYMMDD-shardI)')
    ap.add_argument('--workdir', default=os.environ.get('RUNNER_TEMP') or tempfile.gettempdir())
    ap.add_argument('--max-bytes', type=int, help='local smoke test only: N compressed bytes per file, no checks, no upload')
    a = ap.parse_args(argv)
    try:
        plan = load_plan(a.plan, os.environ.get('PLAN_B64'))
        work = Path(a.workdir) / 'iex-v4-backfill'
        work.mkdir(parents=True, exist_ok=True)
        return run(plan, shard=a.shard, shards=a.shards, parser=a.parser, stamp=a.stamp,
                   token=os.environ.get('RAW_REPO_TOKEN') or None, workdir=work, max_bytes=a.max_bytes)
    except BackfillError as error:
        print(f'IEX_V4_MONTHEND shard={a.shard}/{a.shards} FAILED code={error} nothing_uploaded')
        return 1
    except Exception as error:  # noqa: BLE001 - fixed code only, never the message (it could carry a URL or value)
        print(f'IEX_V4_MONTHEND shard={a.shard}/{a.shards} FAILED code={type(error).__name__} nothing_uploaded')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
