#!/usr/bin/env python3
"""Central QGV publication step (GSQ-024; design CENTRAL_V_PUBLICATION_DESIGN_20261018.md §3, §6): writes `qgv-official.json`
(only when a new publication passed every check) and `qgv-official-status.json` (always) into the Pages artifact directory.

Order (design §3-1):
 1. the live publication (--previous PATH|URL) is strictly validated and copied byte for byte first (last good; a broken live copy
    is not copied, D-CV16);
 2. the same run's final sec-qgv2.json (in --out) is read and strictly validated (require_qgv2);
 3. one IEX HIST TOPS day (latest <= the run's New York shard day) is streamed and parsed in RAM (providers/iex_hist.py);
 4. the private month-end store (V4) is read with the token named by --raw-token-env (providers/iex_monthend.py);
 5. qgv_v2.score_universe over the whole Universe (qgv/qgv_official.py) -> the public projection;
 6. verification: strict validator + the JS twin (tools/qgv_official_js_check.js) on the same RAM input through a pipe;
 7. pass -> atomic replace of qgv-official.json (unless the publication_id is unchanged: then the live bytes stay);
 8. qgv-official-status.json records the attempt; 9. prices are dropped with the process.

Stdout: ONE line of fixed codes and counts. Never a price, yield, month-end value, per-code hash, URL with a token or key.
Exit 0 for every supply/verify outcome (the workflow step stays green; the status file carries the result); 2 = usage error.
A missing Secret (HMAC key or raw-repo read token) or a sec-qgv2.json older than calc_version 2026-10-23.1 is NOT_RUN: nothing is
downloaded and the last good copy stays.

    python implementation/tools/qgv_official_publish.py --out DIR --parser BIN --monthend-stamp YYYYMMDD \
        [--monthend-shards 6] [--previous PATH|URL] [--raw-token-env RAW_REPO_READ_TOKEN] [--hmac-key-env QGV_OFFICIAL_HMAC_KEY]
    python implementation/tools/qgv_official_publish.py --out DIR --preserve-only     # manual deploy path: copy, no prices
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.providers import iex_hist, iex_monthend  # noqa: E402
from investment_system.qgv import qgv_official as qo  # noqa: E402
from investment_system.universe import sec_qgv2  # noqa: E402
from investment_system.universe.sec_universe_shares import shard_day  # noqa: E402

PAGES = 'https://kco994553-star.github.io/Investment-System1/'
LIVE_URL = PAGES + qo.FILENAME
LIVE_STATUS_URL = PAGES + qo.STATUS_FILENAME
JS_CHECK = ROOT / 'tools' / 'qgv_official_js_check.js'
DEFAULT_RAW_TOKEN_ENV = 'RAW_REPO_READ_TOKEN'
DEFAULT_HMAC_ENV = 'QGV_OFFICIAL_HMAC_KEY'


def atomic_write(directory: Path, name: str, body: bytes) -> None:
    target = directory / name
    if target.is_symlink():
        raise OSError('OUTPUT_SYMLINK')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.' + name + '.', delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(body)
    try:
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def load_previous(source: str | None) -> bytes | None:
    """Live publication bytes (Pages URL or a local path); None when absent or unreadable (first publication)."""
    if not source:
        return None
    if source.startswith('https://'):
        if urllib.parse.urlsplit(source).hostname != 'kco994553-star.github.io':
            return None
        try:
            with urllib.request.urlopen(source, timeout=60) as r:
                return r.read(qo.MAX_BYTES + 1)
        except Exception:  # noqa: BLE001 - 404 before the first publication, or a network fault: no last good copy
            return None
    path = Path(source)
    return path.read_bytes()[:qo.MAX_BYTES + 1] if path.is_file() else None


def preserve(out: Path, previous: str | None, previous_status: str | None) -> str:
    """Manual deploy path (cockpit-pages.yml preservation, no prices there): copy the live publication and status bytes as they
    are, each only when it passes its strict validator. Nothing is recomputed."""
    kept = []
    for name, source, check in ((qo.FILENAME, previous, qo.parse),
                                (qo.STATUS_FILENAME, previous_status, lambda b: qo.require_status(json.loads(b)))):
        body = load_previous(source)
        try:
            if body is None:
                raise ValueError('ABSENT')
            check(body)
            atomic_write(out, name, body)
            kept.append(name)
        except ValueError:
            (out / name).unlink(missing_ok=True)
    return '+'.join(kept) or 'NONE'


def _diff(a, b) -> bool:
    """True when two JSON values differ (bools are not numbers; ints equal floats by value; exact, no tolerance)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is not b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a != b
    if type(a) is not type(b):
        return True
    if isinstance(a, dict):
        return set(a) != set(b) or any(_diff(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) != len(b) or any(_diff(x, y) for x, y in zip(a, b))
    return a != b


def js_check(companies: dict, quotes: dict, results: dict, *, node='node', run=subprocess.run) -> None:
    """D-CV12: the JS engine on the same RAM input must give the same public projection. Prices go through the pipe only."""
    spec = json.dumps({'companies': companies, 'quotes': quotes, 'preset': qo.PRESET, 'gate': qo.GATE}, allow_nan=False)
    try:
        p = run([node, str(JS_CHECK)], input=spec, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        raise qo.OfficialError('VERIFY_FAILED', 'JS_TWIN_UNAVAILABLE') from None
    finally:
        del spec
    if p.returncode != 0:
        raise qo.OfficialError('VERIFY_FAILED', 'JS_TWIN_FAILED')
    try:
        js = json.loads(p.stdout)
    except ValueError:
        raise qo.OfficialError('VERIFY_FAILED', 'JS_TWIN_FAILED') from None
    py = json.loads(json.dumps({k: qo.projection(r) for k, r in results.items()}, allow_nan=False))
    if set(js) != set(py) or any(_diff(js[k], py[k]) for k in py):
        raise qo.OfficialError('VERIFY_FAILED', 'JS_TWIN_MISMATCH')


def run(*, out: Path, parser: str, monthend_stamp: str, monthend_shards: int, previous: str | None, raw_token: str | None,
        hmac_key: bytes | None, now: dt.datetime, workdir: Path, node='node', fetch_day=iex_hist.fetch_day,
        read_store=None, check=js_check, clock=None) -> dict:
    """One attempt. Returns a summary of fixed codes and counts (printed by main)."""
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    summary = {'attempt': None, 'reason': None, 'published': 'NONE', 'basis': '-', 'rows': 0, 'ranked': 0, 'supplied': '-'}
    # 1. last good copy first
    live = None
    body = load_previous(previous)
    if body is not None:
        try:
            live = qo.parse(body)
            atomic_write(out, qo.FILENAME, body)
            summary['published'] = 'KEPT_LAST_GOOD'
        except ValueError:
            live = None
    if live is None:
        (out / qo.FILENAME).unlink(missing_ok=True)   # never ship an unchecked or broken publication (D-CV16)
    state, reason, official = 'OK', None, live
    inputs_sha = inputs_as_of = None
    try:
        # 2. same-run inputs
        try:
            raw = (out / sec_qgv2.FILENAME).read_bytes()
            payload = sec_qgv2.parse_json(raw)
            sec_qgv2.require_qgv2(payload)
        except (OSError, ValueError):
            raise qo.OfficialError('NOT_RUN', 'SEC_QGV2_NOT_AVAILABLE') from None
        inputs_sha, inputs_as_of = qo.sha256_bytes(raw), payload['as_of']
        if not hmac_key or len(hmac_key) < 16:      # same rule as qo.build, checked before any download
            raise qo.OfficialError('NOT_RUN', 'HMAC_KEY_MISSING')
        if not parser or not Path(parser).is_file():
            raise qo.OfficialError('NOT_RUN', 'PARSER_MISSING')
        if not raw_token:
            raise qo.OfficialError('NOT_RUN', 'MONTHEND_TOKEN_MISSING')   # a missing Secret is NOT_RUN (no download)
        qo.require_rule_version(payload)
        ctx_keys = qo.prepare(payload, now)['keys']
        # 3. one IEX day (RAM)
        try:
            day = fetch_day(ctx_keys, shard_day(now), parser=parser, workdir=workdir)
        except iex_hist.IexHistError as e:
            raise qo.OfficialError('SUPPLY_FAILED', 'IEX_' + str(e)) from None
        if live is not None and day.day < live['times']['price_basis_date']:
            raise qo.OfficialError('SUPPLY_FAILED', 'BASIS_OLDER_THAN_OFFICIAL')
        # 4. month-end store (RAM)
        try:
            months = (read_store or (lambda s, n: iex_monthend.read_store(s, n, iex_monthend.github_call(raw_token))))(monthend_stamp, monthend_shards)
        except iex_monthend.MonthEndError as e:
            raise qo.OfficialError('SUPPLY_FAILED', 'MONTHEND_' + str(e)) from None
        # 5. score
        new, internal = qo.build(payload, inputs_sha, now=now, day=day, months=months, monthend_stamp=monthend_stamp,
                                 hmac_key=hmac_key, generated_at=clock())
        del day, months
        summary.update(basis=new['times']['price_basis_date'], rows=len(new['rows']), ranked=new['coverage']['ranked'],
                       supplied=f"{new['price_source']['supply']['supplied']}/{new['price_source']['supply']['eligible']}")
        if live is not None and live['publication_id'] == new['publication_id']:
            summary['published'] = 'KEPT_SAME_ID'
        else:
            # 6. verify: strict validator, JS twin on the same RAM input
            try:
                qo.require_qgv_official(new)
            except ValueError as e:
                raise qo.OfficialError('VERIFY_FAILED', str(e)) from None
            check(internal['ctx']['companies'], qo.qi.priced_quotes(internal['quotes'], internal['ctx']['blocked']),
                  internal['results'], node=node)
            new['times']['verified_at'] = qo.iso(clock())
            try:
                encoded = qo.encode(new)
            except ValueError as e:
                raise qo.OfficialError('VERIFY_FAILED', str(e)) from None
            # 7. atomic replace
            atomic_write(out, qo.FILENAME, encoded)
            official = new
            summary['published'] = 'NEW'
        del internal
    except qo.OfficialError as e:
        state, reason = e.state, e.code
    except Exception as e:  # noqa: BLE001 - fixed code only (a message could carry a value)
        state, reason = 'VERIFY_FAILED', 'UNEXPECTED_' + type(e).__name__.upper()
    # 8. status (always)
    status = qo.status_payload(attempt_at=now, state=state, reason=reason, official=official, inputs_sha256=inputs_sha,
                               inputs_as_of=inputs_as_of)
    qo.require_status(status)
    atomic_write(out, qo.STATUS_FILENAME, json.dumps(status, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode())
    summary['attempt'], summary['reason'] = status['attempt_state'], reason
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, help='Pages artifact directory holding this run\'s sec-qgv2.json')
    ap.add_argument('--parser', help='compiled tools/iex_tops/iex_last_trade.c')
    ap.add_argument('--monthend-stamp', help='YYYYMMDD of the U8 store (tags iex-v4-monthend-YYYYMMDD-shardI)')
    ap.add_argument('--preserve-only', action='store_true', help='copy the validated live publication + status only')
    ap.add_argument('--previous-status', default=LIVE_STATUS_URL)
    ap.add_argument('--monthend-shards', type=int, default=6)
    ap.add_argument('--previous', default=LIVE_URL, help='live qgv-official.json (Pages URL or path); "" for none')
    ap.add_argument('--raw-token-env', default=DEFAULT_RAW_TOKEN_ENV, help='NAME of the env var holding the read token')
    ap.add_argument('--hmac-key-env', default=DEFAULT_HMAC_ENV, help='NAME of the env var holding the price-set HMAC key')
    ap.add_argument('--node', default='node')
    ap.add_argument('--workdir', default=os.environ.get('RUNNER_TEMP') or tempfile.gettempdir())
    ap.add_argument('--now', help='ISO clock (tests only)')
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.is_symlink() or not out.is_dir():
        print('QGV_OFFICIAL usage=OUT_INVALID')
        return 2
    if a.preserve_only:
        print(f'QGV_OFFICIAL preserve={preserve(out, a.previous or None, a.previous_status or None)}')
        return 0
    if not a.parser or not a.monthend_stamp:
        print('QGV_OFFICIAL usage=PARSER_AND_MONTHEND_STAMP_REQUIRED')
        return 2
    now = dt.datetime.fromisoformat(a.now.replace('Z', '+00:00')) if a.now else dt.datetime.now(dt.timezone.utc)
    key = os.environ.get(a.hmac_key_env, '')
    s = run(out=out, parser=a.parser, monthend_stamp=a.monthend_stamp, monthend_shards=a.monthend_shards, previous=a.previous or None,
            raw_token=os.environ.get(a.raw_token_env) or None, hmac_key=key.encode() if key else None, now=now,
            workdir=Path(a.workdir) / 'qgv-official', node=a.node)
    print(f"QGV_OFFICIAL attempt={s['attempt']} reason={s['reason'] or '-'} published={s['published']} basis={s['basis']} "
          f"rows={s['rows']} ranked={s['ranked']} supplied={s['supplied']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
