#!/usr/bin/env python3
"""Numbers-only measurement and verdict of the central V rehearsal (GSQ-024 "검증 먼저", owner instruction 2026-10-24 item 3b;
workflow .github/workflows/central-v-rehearsal.yml; doc docs/qgv_scoring_standard/CENTRAL_V_REHEARSAL_20261025.md).

No network, no Secret, no price. Two subcommands:

  sample --path DIR --out FILE [--interval 2]
      Appends "<epoch> <filesystem bytes used> <MemAvailable bytes>" for the filesystem of DIR every interval until it is
      stopped (the workflow starts it in the background right before the V step and kills it right after). Runner numbers only.

  report --metrics-dir DIR --artifact-dir DIR [--now EPOCH]
      Reads what the workflow recorded (values.txt "key=value", stages.txt "<stage> <start> <end> <exit code> <required|optional>",
      samples.txt), this run's sec-qgv2.json and the two V files the publisher left in the artifact directory (qgv-official.json
      carries no price; its strict reader runs first, tools/qgv_official_check.inspect) and prints fixed lines:
        REHEARSAL_STAGE      one per stage, in the order they ran (seconds, exit code or the V step outcome)
        REHEARSAL_JOB        whole-job seconds so far, the allowance for the production steps the rehearsal leaves out
        REHEARSAL_INPUTS     sec-qgv2.json calc_version and row counts (current calc_version / no data / other)
        REHEARSAL_DISK       filesystem bytes used before / after / peak during the V step, artifact and work dir bytes, RAM low
        REHEARSAL_V          attempt, reason, NEW / KEPT / NONE, basis days, rows, ranked, supplied/eligible
        REHEARSAL_PRICE      Universe rows by price status (counts only)
        REHEARSAL_CRITERION  one per failure criterion: value, limit, verdict PASS / FAIL (FAIL reason=NOT_MEASURED when absent)
        REHEARSAL_VERDICT    overall PASS / FAIL
      Exit 0 when every criterion passes, 1 otherwise; 2 = usage error.

Never printed: a price, a ratio, a yield, a per-code value or date, a code list, a URL or a Secret.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
_MODULES = None


def _modules():
    """(qgv_official_check, qgv_official, sec_qgv2), imported on first use only: the sampler must start at once (it is launched
    right before the V step and its first line is written immediately), the report needs the strict readers."""
    global _MODULES
    if _MODULES is None:
        import qgv_official_check as check
        from investment_system.qgv import qgv_official as qo
        from investment_system.universe import sec_qgv2
        _MODULES = (check, qo, sec_qgv2)
    return _MODULES


# Failure criteria (doc section 3). Sources of the limits:
V_STEP_LIMIT_SECONDS = 12 * 60             # the publisher's own limit inside the V step (timeout -k 30s 12m)
JOB_LIMIT_SECONDS = 120 * 60               # collect job limit of an all_shards dispatch (sec-daily-public-inputs.yml)
# Production steps the rehearsal leaves out: OpenDART 4 min 47 s + DART projection 3 s + ledger 8 s (daily run 40045938631,
# 2026-10-24) and the D9 history step (at most its own 5 minute limit): 10 minutes added to the measured job time.
EXCLUDED_STEPS_ALLOWANCE_SECONDS = 10 * 60
STREAM_DISK_LIMIT_BYTES = 10 * 10 ** 9     # GSQ-024 probe limit (CENTRAL_V_PROBE_U8_FACTS_20261024.md section 1: 10 GB)
LAST_TRADE_MIN_SHARE = 0.95                # probe limit: at most 5% of the Universe rows without a regular-session last trade
# Price statuses of a Universe row (the publication's price_source.rejected keys plus SUPPLIED). A row without a regular-session
# round-lot last trade on the IEX day, or without an IEX symbol, is MISSING; a row a publication rule keeps from pricing (ADR,
# split, identity) is RULE_EXCLUDED (whether it traded is not recorded). An unknown status counts as missing.
SUPPLIED = 'SUPPLIED'
MISSING_TRADE = ('NO_IEX_TRADE', 'ODD_LOT_ONLY', 'PRICE_SYMBOL_UNMAPPED')
RULE_EXCLUDED = ('ADR_RATIO_UNCONFIRMED', 'SPLIT_AFTER_SHARE_COUNT', 'PRICE_IDENTITY_CONFLICT', 'IDENTITY_CONFLICT_WITHDRAWN')
OUTCOMES = ('success', 'failure', 'cancelled', 'skipped')
_STAGE = re.compile(r'[a-z][a-z0-9_]{0,39}', re.ASCII)
_VERSION = re.compile(r'[A-Za-z0-9._/\-]{1,64}', re.ASCII)
_DAY = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,63}', re.ASCII)


# ---- sample ---------------------------------------------------------------------------------------------------------------
def sample_once(path) -> str:
    """'<epoch> <bytes used> <MemAvailable bytes or -1>' (df's Used: (blocks - free) * fragment size)."""
    st = os.statvfs(path)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    mem = -1
    try:
        for line in Path('/proc/meminfo').read_text(encoding='ascii').splitlines():
            if line.startswith('MemAvailable:'):
                mem = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError, UnicodeDecodeError):
        mem = -1
    return f'{int(time.time())} {used} {mem}'


def sample(path, out, interval, *, count=None, sleep=time.sleep) -> int:
    n = 0
    while count is None or n < count:
        try:
            line = sample_once(path)
            with open(out, 'a', encoding='ascii') as handle:
                handle.write(line + '\n')
        except OSError:
            pass
        n += 1
        if count is None or n < count:
            sleep(interval)
    return 0


# ---- metric files ---------------------------------------------------------------------------------------------------------
def _lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding='ascii').splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def _int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r'-?\d{1,20}', value.strip()):
        return int(value.strip())
    return None


def read_values(path: Path) -> dict:
    """key=value lines; the last value of a key wins."""
    out = {}
    for line in _lines(path):
        key, sep, value = line.partition('=')
        if sep and re.fullmatch(r'[a-z][a-z0-9_]{0,39}', key.strip()):
            out[key.strip()] = value.strip()
    return out


def read_stages(path: Path) -> list[dict]:
    rows = []
    for line in _lines(path):
        parts = line.split()
        if len(parts) != 5 or not _STAGE.fullmatch(parts[0]) or parts[4] not in ('required', 'optional'):
            continue
        start, end, rc = (_int(p) for p in parts[1:4])
        if None in (start, end, rc):
            continue
        rows.append({'stage': parts[0], 'start': start, 'end': end, 'rc': rc, 'kind': parts[4]})
    return rows


def read_samples(path: Path) -> list[tuple[int, int, int]]:
    rows = []
    for line in _lines(path):
        parts = [_int(p) for p in line.split()]
        if len(parts) == 3 and None not in parts and parts[1] >= 0:
            rows.append(tuple(parts))
    return rows


# ---- facts ----------------------------------------------------------------------------------------------------------------
def inputs_facts(artifact: Path) -> dict:
    """sec-qgv2.json: state, top calc_version, row counts by calc_version (current / no data / other), TARGET rows."""
    _, qo, sec_qgv2 = _modules()
    facts = {'state': 'ABSENT', 'calc_version': None, 'records': 0, 'current': 0, 'no_data': 0, 'other': 0, 'target': 0,
             'sha256': None, 'carries_share_basis': False}
    path = artifact / sec_qgv2.FILENAME
    if not path.exists():
        return facts
    try:
        raw = path.read_bytes()
        payload = sec_qgv2.parse_json(raw)
        sec_qgv2.require_qgv2(payload)
    except Exception:  # noqa: BLE001 - fixed code only
        return dict(facts, state='INVALID')
    top = payload.get('calc_version')
    rows = list(payload['records'].values())
    current = sum(1 for r in rows if isinstance(top, str) and r.get('calc_version') == top)
    no_data = sum(1 for r in rows if r.get('calc_version') is None)
    return {'state': 'VALID', 'calc_version': top if isinstance(top, str) and _VERSION.fullmatch(top) else None,
            'records': len(rows), 'current': current, 'no_data': no_data, 'other': len(rows) - current - no_data,
            'target': len(payload.get('target') or {}), 'sha256': hashlib.sha256(raw).hexdigest(),
            'carries_share_basis': qo.vf.carries_share_basis(top)}


def status_inputs_sha(artifact: Path):
    """latest_inputs.sha256 of a valid status file (the sec-qgv2.json bytes the attempt read), else None."""
    _, qo, _ = _modules()
    try:
        status = json.loads((artifact / qo.STATUS_FILENAME).read_bytes())
        qo.require_status(status)
        return status['latest_inputs']['sha256']
    except (OSError, ValueError, KeyError, TypeError):
        return None


def price_facts(official) -> dict | None:
    """Universe rows by price status from a publication (counts only), or None without one."""
    _, qo, _ = _modules()
    if not isinstance(official, dict):
        return None
    ps = official['price_source']
    rejected = ps['rejected']
    universe_rows = sum(1 for key in official['rows'] if not key.startswith(qo.TARGET_PREFIX))
    known = set(MISSING_TRADE) | set(RULE_EXCLUDED)
    unknown = sum(n for code, n in rejected.items() if code not in known)
    missing = sum(rejected.get(code, 0) for code in MISSING_TRADE) + unknown
    return {'universe_rows': universe_rows, 'universe_code_count': official['population']['universe_code_count'],
            'supplied': ps['supplied'], 'missing': missing, 'unknown': unknown,
            'rule_excluded': sum(rejected.get(code, 0) for code in RULE_EXCLUDED),
            'by_status': {code: rejected.get(code, 0) for code in MISSING_TRADE + RULE_EXCLUDED},
            'consistent': ps['supplied'] + sum(rejected.values()) == universe_rows,
            'supply': ps['supply'], 'basis': ps['basis_date'], 'requested': ps['requested_basis_date']}


def last_trade_needed(rows: int) -> int:
    """Universe rows that must have a regular-session last trade (ceil(95%); 504 -> 479)."""
    return math.ceil(LAST_TRADE_MIN_SHARE * rows - 1e-9)


# ---- report ---------------------------------------------------------------------------------------------------------------
def _n(value) -> str:
    return '-' if value is None else str(value)


def _criterion(name, ok, value, limit, reason=None):
    verdict = 'PASS' if ok is True else 'FAIL'
    if ok is None:
        reason = 'NOT_MEASURED'
    return {'name': name, 'verdict': verdict, 'line': f'REHEARSAL_CRITERION name={name} value={value} limit={limit} verdict={verdict}'
            + (f' reason={reason}' if verdict == 'FAIL' and reason else '')}


def build_report(metrics: Path, artifact: Path, now: int) -> tuple[list[str], bool]:
    check, qo, sec_qgv2 = _modules()
    values = read_values(metrics / 'values.txt')
    stages = read_stages(metrics / 'stages.txt')
    samples = read_samples(metrics / 'samples.txt')
    lines = ['REHEARSAL_SCOPE publication=NONE raw_repo_write=NONE ledger=NONE history=NONE pages_upload=NONE '
             'artifact_upload=NONE cache=NONE job_summary=NONE']

    # stages in the order they ran (the steps append to stages.txt one after the other; the V step's line is written by the
    # measurement step right after it, its outcome comes from values.txt)
    v_start, v_end = _int(values.get('v_start')), _int(values.get('v_end'))
    outcome = values.get('v_outcome', 'none')
    outcome = outcome if outcome in OUTCOMES else 'none'
    v_seconds = v_end - v_start if v_start is not None and v_end is not None and v_end >= v_start else None
    v_line = f'REHEARSAL_STAGE stage=v_step seconds={_n(v_seconds)} outcome={outcome}'
    for s in stages:
        lines.append(v_line if s['stage'] == 'v_step' else
                     f"REHEARSAL_STAGE stage={s['stage']} seconds={s['end'] - s['start']} rc={s['rc']} kind={s['kind']}")
    if not any(s['stage'] == 'v_step' for s in stages):
        lines.append(v_line)
    stages = [s for s in stages if s['stage'] != 'v_step']

    job_start = _int(values.get('job_start'))
    job_seconds = now - job_start if job_start is not None and now >= job_start else None
    lines.append(f'REHEARSAL_JOB seconds={_n(job_seconds)} allowance_excluded_steps={EXCLUDED_STEPS_ALLOWANCE_SECONDS} '
                 f'limit={JOB_LIMIT_SECONDS}')

    inputs = inputs_facts(artifact)
    status_sha = status_inputs_sha(artifact)
    same = '-' if status_sha is None or inputs['sha256'] is None else ('YES' if status_sha == inputs['sha256'] else 'NO')
    lines.append(f"REHEARSAL_INPUTS file={sec_qgv2.FILENAME} state={inputs['state']} calc_version={_n(inputs['calc_version'])} "
                 f"records={inputs['records']} records_current_calc={inputs['current']} records_no_data={inputs['no_data']} "
                 f"records_other_calc={inputs['other']} target={inputs['target']} same_bytes_as_attempt={same}")

    before, after = _int(values.get('df_before_used')), _int(values.get('df_after_used'))
    used = [s[1] for s in samples] + [v for v in (before, after) if v is not None]
    peak = max(used) if used else None
    stream_peak = peak - before if peak is not None and before is not None else None
    mems = [s[2] for s in samples if s[2] >= 0]
    lines.append(f"REHEARSAL_DISK fs_used_before={_n(before)} fs_used_after={_n(after)} fs_used_peak={_n(peak)} "
                 f"stream_peak_bytes={_n(stream_peak)} fs_avail_before={_n(_int(values.get('df_before_avail')))} "
                 f"samples={len(samples)} out_dir_bytes_before={_n(_int(values.get('du_out_before')))} "
                 f"out_dir_bytes_after={_n(_int(values.get('du_out_after')))} "
                 f"workdir_bytes_after={_n(_int(values.get('du_workdir_after')))} mem_available_min={_n(min(mems) if mems else None)}")

    result = check.inspect(artifact)
    official = result['official']
    published = 'NEW' if result['new'] else {'VALID': 'KEPT', 'INVALID': 'INVALID'}.get(result['publication'], 'NONE')
    attempt = result['attempt'] or '-'
    reason = result['reason'] if isinstance(result['reason'], str) and _REASON.fullmatch(result['reason']) else '-'
    prices = price_facts(official)
    supply = prices['supply'] if prices else None
    lines.append(f"REHEARSAL_V attempt={attempt} reason={reason} published={published} "
                 f"basis={prices['basis'] if prices and _DAY.fullmatch(prices['basis']) else '-'} "
                 f"requested_basis={prices['requested'] if prices and _DAY.fullmatch(prices['requested']) else '-'} "
                 f"rows={result['rows']} ranked={result['ranked']} "
                 f"supplied={supply['supplied'] if supply else '-'}/{supply['eligible'] if supply else '-'} "
                 f"supply_met={({True: 'YES', False: 'NO'}.get(supply['met'], '-')) if supply else '-'}")
    if prices:
        lines.append(f"REHEARSAL_PRICE universe_rows={prices['universe_rows']} universe_code_count={prices['universe_code_count']} "
                     f"supplied={prices['supplied']} last_trade_missing={prices['missing']} rule_excluded={prices['rule_excluded']} "
                     + ' '.join(f'{code}={n}' for code, n in prices['by_status'].items())
                     + f" unknown_status={prices['unknown']} consistent={'YES' if prices['consistent'] else 'NO'}")
    else:
        lines.append('REHEARSAL_PRICE state=NO_PUBLICATION')

    # criteria
    crit = []
    crit.append(_criterion('v_step_time', None if v_seconds is None else v_seconds <= V_STEP_LIMIT_SECONDS,
                           f'{_n(v_seconds)}s', f'{V_STEP_LIMIT_SECONDS}s'))
    job_total = None if job_seconds is None else job_seconds + EXCLUDED_STEPS_ALLOWANCE_SECONDS
    crit.append(_criterion('job_time', None if job_total is None else job_total <= JOB_LIMIT_SECONDS,
                           f'{_n(job_total)}s', f'{JOB_LIMIT_SECONDS}s'))
    required = [s for s in stages if s['kind'] == 'required']
    failed = [s['stage'] for s in required if s['rc'] != 0]
    crit.append(_criterion('required_steps', None if not required else not failed,
                           f'{len(required) - len(failed)}/{len(required)}', 'all',
                           'FAILED_' + '_'.join(failed).upper()[:60] if failed else None))
    crit.append(_criterion('inputs_calc_version', None if inputs['state'] != 'VALID' else inputs['carries_share_basis'] is True,
                           _n(inputs['calc_version']), 'qgv2-calc/2026-10-23.1+',
                           None if inputs['state'] == 'VALID' else 'SEC_QGV2_' + inputs['state']))
    crit.append(_criterion('stream_disk_peak', None if stream_peak is None or not samples else stream_peak <= STREAM_DISK_LIMIT_BYTES,
                           f'{_n(stream_peak)}B', f'{STREAM_DISK_LIMIT_BYTES}B'))
    if prices:
        present = prices['universe_rows'] - prices['missing']
        need = last_trade_needed(prices['universe_rows'])
        crit.append(_criterion('universe_last_trade', prices['consistent'] and present >= need,
                               f"{present}/{prices['universe_rows']}", f'>={need}', None if prices['consistent'] else 'COUNTS_INCONSISTENT'))
        met = supply['eligible'] > 0 and supply['supplied'] >= qo.supply_needed(supply['eligible']) and supply['met'] is True
        crit.append(_criterion('supply', met, f"{supply['supplied']}/{supply['eligible']}", f">={qo.supply_needed(supply['eligible'])}"))
    else:
        crit.append(_criterion('universe_last_trade', None, '-', '>=95%'))
        crit.append(_criterion('supply', False if reason == 'SUPPLY_BELOW_THRESHOLD' else None, '-', '>=95%',
                               'SUPPLY_BELOW_THRESHOLD' if reason == 'SUPPLY_BELOW_THRESHOLD' else None))
    check_rc = _int(values.get('check_rc'))
    validator = None if result['publication'] == 'ABSENT' or check_rc is None else (
        check_rc == 0 and result['publication'] == 'VALID' and result['status'] == 'VALID' and result['consistent'] is True)
    crit.append(_criterion('validator', validator, f"{result['publication']}/{result['status']}", 'VALID/VALID'))
    js = True if published == 'NEW' else (False if reason.startswith('JS_TWIN_') else None)
    crit.append(_criterion('js_twin', js, 'MATCH' if js else (reason if js is False else '-'), 'MATCH', reason if js is False else None))
    guard_rc = _int(values.get('guard_rc'))
    guard = None if guard_rc is None or outcome in ('none', 'skipped') else (outcome == 'success' and guard_rc == 0)
    crit.append(_criterion('guard', guard, f'v_step={outcome}/rc={_n(guard_rc)}', 'success/rc=0'))
    crit.append(_criterion('attempt_ok', None if result['status'] != 'VALID' else attempt == 'OK', attempt, 'OK',
                           reason if reason != '-' else None))
    lines += [c['line'] for c in crit]
    failed_names = [c['name'] for c in crit if c['verdict'] != 'PASS']
    ok = not failed_names
    lines.append(f"REHEARSAL_VERDICT overall={'PASS' if ok else 'FAIL'} passed={len(crit) - len(failed_names)}/{len(crit)} "
                 f"failed={','.join(failed_names) or '-'}")
    return lines, ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='command', required=True)
    s = sub.add_parser('sample')
    s.add_argument('--path', required=True)
    s.add_argument('--out', required=True)
    s.add_argument('--interval', type=float, default=2.0)
    s.add_argument('--count', type=int, help='tests only')
    r = sub.add_parser('report')
    r.add_argument('--metrics-dir', required=True)
    r.add_argument('--artifact-dir', required=True)
    r.add_argument('--now', type=int, help='epoch seconds (tests only)')
    a = ap.parse_args(argv)
    if a.command == 'sample':
        return sample(a.path, a.out, max(a.interval, 0.1), count=a.count)
    metrics, artifact = Path(a.metrics_dir), Path(a.artifact_dir)
    if artifact.is_symlink() or not artifact.is_dir():
        print('REHEARSAL_VERDICT overall=FAIL reason=ARTIFACT_DIR_INVALID')
        return 2
    try:
        lines, ok = build_report(metrics, artifact, a.now if a.now is not None else int(time.time()))
    except Exception:  # noqa: BLE001 - fixed code only (a message could carry a value)
        print('REHEARSAL_VERDICT overall=FAIL reason=REPORT_FAILED')
        return 1
    print('\n'.join(lines))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
