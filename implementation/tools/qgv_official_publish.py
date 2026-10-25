#!/usr/bin/env python3
"""Central QGV publication step (GSQ-024; design CENTRAL_V_PUBLICATION_DESIGN_20261018.md §3, §6): writes `qgv-official.json`
(only when a new publication passed every check) and `qgv-official-status.json` (always) into the Pages artifact directory.

Order (design §3-1):
 1. the live publication (--previous PATH|URL) is strictly validated and copied byte for byte first (last good; a broken live copy
    is not copied, D-CV16). It is read like every daily tool reads its live Pages copy (sec_universe_shares._fetch_body: no
    cache, no redirect, exact URL with a run nonce; 404 -> no live publication) with retries. A live copy that cannot be read
    (any other failure) is LIVE_UNREACHABLE: nothing is computed (the older-basis check could not run), the status is
    NOT_RUN / LIVE_UNREACHABLE (never NO_OFFICIAL_YET: whether a publication exists is not known), and the artifact carries
    no publication that day;
 2. the same run's final sec-qgv2.json (in --out) is read and strictly validated (require_qgv2);
 3. one IEX HIST TOPS day (latest <= the run's New York shard day) is streamed and parsed in RAM (providers/iex_hist.py);
 4. the private month-end store (V4) is read with the token named by --raw-token-env (providers/iex_monthend.py);
 5. qgv_v2.score_universe over the whole Universe (qgv/qgv_official.py) -> the public projection;
 6. verification: strict validator + the JS twin (tools/qgv_official_js_check.js) on the same RAM input through a pipe;
 7. pass -> atomic replace of qgv-official.json (unless the publication_id is unchanged: then the live bytes stay);
 8. qgv-official-status.json records the attempt; 9. prices are dropped with the process.

Stdout: ONE line of fixed codes and counts. Never a price, yield, month-end value, per-code hash, URL with a token or key.
After a build the line ends with the D6 (b) split-check counts (qgv_official.price_status_counts; owner decision CV-SPLIT (ii)
2026-10-24): split_checked / split_flagged / split_unchecked (of which split_unchecked_no_period) rows, split_gap_skipped pairs,
split_lead_unchecked rows (of split_checked: the stretch from the count's period-end month to the first store point not compared).
When an IEX stream ran, iex_attempts=1|2 follows supplied=, then (only when the first attempt failed) iex_first=<its fixed code>
and, for a first DOWNLOAD_FAILED, iex_curl_rc=<curl exit code> (2026-10-25; never in a public file).
Time budget: the workflow runs this process under `timeout -k 30s 12m`; the IEX stream gets the deadline STEP_LIMIT_S after this
process started (iex_hist.fetch_day `deadline`: curl --max-time per attempt, a second attempt only when it is predicted to fit),
so a slow transfer ends as a SUPPLY_FAILED status file instead of the step's kill. After the stream, each month-end store
request and the JS twin wait at most the time left before that deadline less FINAL_RESERVE_S (`wait_s`), so a hang there ends
as MONTHEND_STORE_UNAVAILABLE / JS_TWIN_UNAVAILABLE with a status file. Not bounded: a store response that keeps trickling
(the timeout is per socket read), and the CPU work between the waits (build, validator, encode), which FINAL_RESERVE_S covers.
Exit 0 for every supply/verify outcome (the workflow step stays green; the status file carries the result); 2 = usage error.
The two Secrets are popped from the environment at start (no child process inherits them).
A missing Secret (HMAC key or raw-repo read token) or a sec-qgv2.json older than calc_version 2026-10-23.1 is NOT_RUN: nothing is
downloaded and the last good copy stays.

    python implementation/tools/qgv_official_publish.py --out DIR --parser BIN --monthend-stamp YYYYMMDD \
        [--monthend-shards 6] [--previous PATH|URL] [--raw-token-env RAW_REPO_READ_TOKEN] [--hmac-key-env QGV_OFFICIAL_HMAC_KEY]
    python implementation/tools/qgv_official_publish.py --out DIR --preserve-only     # manual deploy path: copy, no prices
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

STARTED = time.monotonic()           # this process's start (before the project imports): the step limit counts from here
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.providers import iex_hist, iex_monthend  # noqa: E402
from investment_system.qgv import qgv_official as qo  # noqa: E402
from investment_system.universe import sec_qgv2  # noqa: E402
from investment_system.universe.sec_universe_shares import shard_day  # noqa: E402
from sec_universe_shares import _fetch_body  # noqa: E402  - the daily tools' live Pages reader (404 -> None, else OSError)

PAGES = 'https://kco994553-star.github.io/Investment-System1/'
LIVE_URL = PAGES + qo.FILENAME
LIVE_STATUS_URL = PAGES + qo.STATUS_FILENAME
JS_CHECK = ROOT / 'tools' / 'qgv_official_js_check.js'
DEFAULT_RAW_TOKEN_ENV = 'RAW_REPO_READ_TOKEN'
DEFAULT_HMAC_ENV = 'QGV_OFFICIAL_HMAC_KEY'
LIVE_UNREACHABLE = qo.LIVE_UNREACHABLE
LIVE_READ_ATTEMPTS = 3
LIVE_READ_BACKOFF = (5, 15)          # seconds between attempts (each attempt has _fetch_body's own 20 s timeout)
# The V step's `timeout -k 30s 12m` around this process (sec-daily-public-inputs.yml): TERM after 12 minutes, with nothing
# written after it. main() hands the IEX stream the deadline STARTED + STEP_LIMIT_S (iex_hist time budget).
STEP_LIMIT_S = 12 * 60
# After the stream (review 2026-10-25): every month-end store request and the JS twin get at most the time left before that
# deadline less FINAL_RESERVE_S (the build between them, the encode and both files), at least 1 s, never above their own caps.
FINAL_RESERVE_S = 30
JS_CHECK_TIMEOUT_S = 600


def wait_s(cap: int, deadline, monotonic=time.monotonic) -> int:
    """Seconds one post-stream wait may take: `cap`, or the time left before `deadline` less FINAL_RESERVE_S when that is
    shorter (at least 1). No deadline (tests, tools): `cap`."""
    return cap if deadline is None else max(1, min(cap, int(deadline - FINAL_RESERVE_S - monotonic())))


def _timed_store(call, deadline, monotonic=time.monotonic):
    """A month-end store `call` whose every request waits at most wait_s(REQUEST_TIMEOUT_S)."""
    return lambda method, url, **kw: call(method, url, timeout=wait_s(iex_monthend.REQUEST_TIMEOUT_S, deadline, monotonic), **kw)


class LiveUnreachable(OSError):
    """The live copy could not be read (not a 404): fixed code only."""


def _run_nonce(environ=None) -> str:
    environ = os.environ if environ is None else environ
    run_id, attempt = environ.get('GITHUB_RUN_ID', ''), environ.get('GITHUB_RUN_ATTEMPT', '')
    return f'{run_id}-{attempt}' if run_id.isdigit() and attempt.isdigit() else str(time.time_ns())


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


def load_previous(source: str | None, *, open_response=None, sleep=time.sleep, attempts=LIVE_READ_ATTEMPTS,
                  nonce=None) -> bytes | None:
    """Live publication bytes from a Pages URL (or a local path in tests); None only when there is none (Pages 404, no source,
    no such local file). Any other failure is retried and then raises LiveUnreachable: a network fault, a 5xx, a redirect or a
    source outside the Pages site never looks like "no publication"."""
    if not source:
        return None
    if not source.startswith('https://'):
        path = Path(source)
        return path.read_bytes()[:qo.MAX_BYTES + 1] if path.is_file() else None
    if not source.startswith(PAGES) or urllib.parse.urlsplit(source).query:
        raise LiveUnreachable('SOURCE_NOT_ALLOWED')
    url = f'{source}?qgv-official-step={nonce or _run_nonce()}'
    for attempt in range(attempts):
        try:
            return _fetch_body(url, qo.MAX_BYTES, open_response)
        except OSError:
            if attempt + 1 < attempts:
                sleep(LIVE_READ_BACKOFF[min(attempt, len(LIVE_READ_BACKOFF) - 1)])
    raise LiveUnreachable(LIVE_UNREACHABLE)


def preserve(out: Path, previous: str | None, previous_status: str | None, *, open_response=None, sleep=time.sleep) -> str:
    """Manual deploy path (cockpit-pages.yml preservation, no prices there): copy the live publication and status bytes as they
    are, each only when it passes its strict validator. Nothing is recomputed. A live publication that cannot be read (not a
    404) is LIVE_UNREACHABLE: neither file is copied then (a kept status would name a publication the artifact lacks)."""
    kept = []
    for name, source, check in ((qo.FILENAME, previous, qo.parse),
                                (qo.STATUS_FILENAME, previous_status, lambda b: qo.require_status(json.loads(b)))):
        try:
            body = load_previous(source, open_response=open_response, sleep=sleep)
        except LiveUnreachable:
            (out / name).unlink(missing_ok=True)
            if name == qo.FILENAME:
                (out / qo.STATUS_FILENAME).unlink(missing_ok=True)
                return LIVE_UNREACHABLE
            continue
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


def js_check(companies: dict, quotes: dict, results: dict, *, node='node', run=subprocess.run, timeout=JS_CHECK_TIMEOUT_S) -> None:
    """D-CV12: the JS engine on the same RAM input must give the same public projection. Prices go through the pipe only.
    `timeout` (seconds): over it, JS_TWIN_UNAVAILABLE."""
    spec = json.dumps({'companies': companies, 'quotes': quotes, 'preset': qo.PRESET, 'gate': qo.GATE}, allow_nan=False)
    try:
        p = run([node, str(JS_CHECK)], input=spec, capture_output=True, text=True, timeout=timeout)
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
        read_store=None, check=js_check, clock=None, open_response=None, sleep=time.sleep, deadline=None,
        monotonic=time.monotonic) -> dict:
    """One attempt. Returns a summary of fixed codes and counts (printed by main). `deadline` (a time.monotonic() value, main:
    the step limit; the IEX stream gets it through fetch_day) bounds the month-end store requests and the JS twin (`wait_s`)."""
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    summary = {'attempt': None, 'reason': None, 'published': 'NONE', 'basis': '-', 'rows': 0, 'ranked': 0, 'supplied': '-',
               'split': None, 'iex_attempts': None, 'iex_first': None, 'iex_curl_rc': None}
    # 1. last good copy first
    live, live_unknown = None, False
    try:
        body = load_previous(previous, open_response=open_response, sleep=sleep)
    except LiveUnreachable:
        body, live_unknown = None, True
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
            inputs_sha, inputs_as_of = qo.sha256_bytes(raw), payload['as_of']
        except (OSError, ValueError):
            payload = None
        if live_unknown:          # the last good copy and the older-basis check depend on the live read: nothing is computed
            raise qo.OfficialError('NOT_RUN', LIVE_UNREACHABLE)
        if payload is None:
            raise qo.OfficialError('NOT_RUN', 'SEC_QGV2_NOT_AVAILABLE')
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
            # full IEX stream attempts and the first attempt's fixed code / curl exit code (None before any stream)
            summary.update(iex_attempts=e.attempts, iex_first=e.first_code, iex_curl_rc=e.first_curl_rc)
            raise qo.OfficialError('SUPPLY_FAILED', 'IEX_' + str(e)) from None
        summary.update(iex_attempts=getattr(day, 'attempts', None), iex_first=getattr(day, 'first_code', None),
                       iex_curl_rc=getattr(day, 'first_curl_rc', None))
        if live is not None and day.day < live['times']['price_basis_date']:
            raise qo.OfficialError('SUPPLY_FAILED', 'BASIS_OLDER_THAN_OFFICIAL')
        # 4. month-end store (RAM), every request inside the deadline
        try:
            months = (read_store or (lambda s, n: iex_monthend.read_store(
                s, n, _timed_store(iex_monthend.github_call(raw_token), deadline, monotonic))))(monthend_stamp, monthend_shards)
        except iex_monthend.MonthEndError as e:
            raise qo.OfficialError('SUPPLY_FAILED', 'MONTHEND_' + str(e)) from None
        # 5. score
        new, internal = qo.build(payload, inputs_sha, now=now, day=day, months=months, monthend_stamp=monthend_stamp,
                                 hmac_key=hmac_key, generated_at=clock())
        del day, months
        summary.update(basis=new['times']['price_basis_date'], rows=len(new['rows']), ranked=new['coverage']['ranked'],
                       supplied=f"{new['price_source']['supply']['supplied']}/{new['price_source']['supply']['eligible']}",
                       split={k: internal['split'][k] for k in qo.SPLIT_COUNT_KEYS})
        if live is not None and live['publication_id'] == new['publication_id']:
            summary['published'] = 'KEPT_SAME_ID'
        else:
            # 6. verify: strict validator, JS twin on the same RAM input
            try:
                qo.require_qgv_official(new)
            except ValueError as e:
                raise qo.OfficialError('VERIFY_FAILED', str(e)) from None
            check(internal['ctx']['companies'], qo.qi.priced_quotes(internal['quotes'], internal['ctx']['blocked']),
                  internal['results'], node=node, timeout=wait_s(JS_CHECK_TIMEOUT_S, deadline, monotonic))
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
                               inputs_as_of=inputs_as_of, live_unknown=live_unknown)
    qo.require_status(status)
    atomic_write(out, qo.STATUS_FILENAME, json.dumps(status, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode())
    summary['attempt'], summary['reason'] = status['attempt_state'], reason
    return summary


def summary_line(s) -> str:
    """The one stdout line: fixed codes and counts only (`iex_attempts` only after an IEX stream ran, 1 or 2; `iex_first` only
    when its first attempt failed, an upper-case fixed code, and `iex_curl_rc` a small integer; the split counts only after a
    build)."""
    line = (f"QGV_OFFICIAL attempt={s['attempt']} reason={s['reason'] or '-'} published={s['published']} basis={s['basis']} "
            f"rows={s['rows']} ranked={s['ranked']} supplied={s['supplied']}")
    if s.get('iex_attempts'):
        line += f" iex_attempts={int(s['iex_attempts'])}"
        first, rc = s.get('iex_first'), s.get('iex_curl_rc')
        if isinstance(first, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,39}', first):
            line += f" iex_first={first}"
            if type(rc) is int and -64 < rc < 256:
                line += f" iex_curl_rc={rc}"
    if s.get('split'):
        line += ''.join(f" split_{k}={int(s['split'][k])}" for k in qo.SPLIT_COUNT_KEYS)
    return line


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
    # The two Secrets are read once and removed from this process's environment before anything else runs, so no child
    # (curl, gzip, the C parser, node) inherits them: only this Python process holds them, as arguments.
    key = os.environ.pop(a.hmac_key_env, '')
    raw_token = os.environ.pop(a.raw_token_env, '') or None
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
    deadline = STARTED + STEP_LIMIT_S
    s = run(out=out, parser=a.parser, monthend_stamp=a.monthend_stamp, monthend_shards=a.monthend_shards, previous=a.previous or None,
            raw_token=raw_token, hmac_key=key.encode() if key else None, now=now,
            workdir=Path(a.workdir) / 'qgv-official', node=a.node,
            fetch_day=functools.partial(iex_hist.fetch_day, deadline=deadline), deadline=deadline)
    print(summary_line(s))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
