#!/usr/bin/env python3
"""EXP-STOCK-INDICATOR-DECILES-v1 private-run CLI: the only IO layer of research/exp_deciles. RESEARCH ONLY.

Subcommands
  schedule                 verify the frozen schedule (exp_deciles/schedule_v1.json) against the rule calendar and print
                           its rows (dates only); exit 0 when it verifies, 1 otherwise
  select   --manifest M --year Y [--previous-u-a FILE] --out DIR [--generated-at ISO]
                           selection stage of one frozen signal year -> DIR/selection_inputs.json + DIR/manifest.json.
                           FILE is the previous year's selection_inputs.json (its U-A members and U-A UNKNOWN units; its
                           year must be Y - 1; its run directory's manifest.json must verify), or a JSON object
                           {"members": [CIK, ...], "unknown": [CIK or "SECURITY:<id>", ...]}, or a JSON list of the
                           previous member CIKs (then no UNKNOWN set is known: flag PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED).
                           Without it the U-A is a first build.
  ledger   --manifest M --selection FILE [--selection FILE ...] --out DIR [--generated-at ISO] [--end YYYY-MM-DD]
           [--daily-positions]
                           ledger stage over consecutive yearly selection_inputs.json files
                           -> DIR/ledger_outputs.json + DIR/manifest.json. Each FILE must sit in its select run
                           directory, whose manifest.json must verify and list FILE's sha256 (review F7); every selection
                           must share one code SHA (SELECTION_CODE_SHA_MISMATCH); a selection made from another input
                           manifest or another code SHA than this ledger run is flagged (SELECTION_INPUT_MANIFEST_DIFFERS,
                           SELECTION_CODE_SHA_DIFFERS_FROM_LEDGER). Without --end the run is held to the next
                           reselection T open; an --end past it is refused (END_PAST_NEXT_RESELECTION)
  verify   --run DIR       re-hash a run directory against its manifest.json; exit 0 when every file matches
  synthetic --out DIR [--generated-at ISO]
                           synthetic run bundle for interface / settings / ledger checks (no real data): writes the
                           invented input bundle and its manifest to DIR/bundle, then runs select 2018 -> DIR/select-2018,
                           select 2019 (previous U-A from 2018) -> DIR/select-2019, ledger over both years to 2019-03-29
                           -> DIR/ledger, and verify on each run directory; prints each run's run_id and manifest sha256

Input manifest: see research/exp_deciles/handoff.py (resources {name, path, sha256, source, period, rights_note}; a path is
relative to the manifest's directory or absolute). Every resource file is hashed before anything is computed and again
when it is parsed; any mismatch is refused (MANIFEST_HASH_MISMATCH).

Bundle files (JSON), by resource name:
  records:<year>      {"signal_day": "<the frozen S of that year>", "records": [record, ...], "terminations"?: [...]}
                      record (universe.py module doc): security_id, cik, listed (true / false / null), security_type
                      (COMMON, COMMON_CLASS, ADR, REIT, ETF, CLOSED_END_FUND, PREFERRED, WARRANT, RIGHT, UNIT, or null),
                      shares_outstanding (for an ADR: ordinary shares), shares_filed (NY filing date of the filing the
                      count comes from; usable at S under the 6th-session rule, else the issuer is UNKNOWN
                      SHARES_NOT_USABLE_AT_S), shares_period_end (the date the count is as of), share_price_basis
                      ("CONFIRMED" when the count and the S price are on one split basis; anything else leaves the
                      issuer UNKNOWN, never excluded), price (at S; for an ADR: per ADS), price_label?, representative?,
                      median_dollar_volume?, same_economic_rights?, adr_ratio? (ADR: ordinary shares per ADS)
                      terminations: evidenced terminations of previous U-A members / UNKNOWN issuers that have no record
                      at S: [{"cik", "evidence", "filed" (NY filing date of the evidence), "effective_date"?}]; without
                      one such an issuer stays an UNKNOWN candidate (NOT_IN_RECORDS_AT_S)
  quotes:<year>       {"signal_day": "<S>", "quotes": {security_id: {"price", "currency", "month_closes": {"YYYY-MM":
                      close}, "withheld_reason"?: UPPER_SNAKE}}}; a quote is per traded security (an ADR quote is per
                      ADS; the runner divides it by adr_ratio). Optional: without it V is NA for every name and the
                      output carries the flag QUOTES_NOT_SUPPLIED.
  companyfacts:<CIK>  one SEC companyfacts JSON ({"cik", "facts", ...}); read only when that CIK is a U-A member
  companyfacts[:x]    (x not all digits) one SEC companyfacts JSON, or {"<cik>": companyfacts, ...}; read whole
  filings[:x]         [{"cik", "accn", "filed": "YYYY-MM-DD", "sic"}, ...]: filing rows for the as-filed SIC
  prices[:x]          [{"date", "security_id", "open", "close", "suspended", "price_basis": "RAW", "currency"?: "USD"}]
                      raw (unadjusted) USD session prices for the ledger
  events[:x]          [{"type": "SPLIT", "event_id", "effective_date", "security_id", "ratio"},
                       {"type": "DIVIDEND", "event_id", "effective_date" (ex-date), "security_id", "cash_per_share",
                        "pay_date"?, "depositary_fee_per_share"? (ADR: fee per ADS deducted from the cash; recorded as
                        an instrument fee; a fee above the cash is refused)},
                       {"type": "SETTLEMENT", "event_id", "effective_date", "security_id", "kind" (CASH_MERGER,
                        STOCK_MERGER, DELISTING or SPINOFF), "available_at", "evidence", "settlement_date"?,
                        "cash_per_share"?, "new_security_id"?, "stock_ratio"?},
                       {"type": "SETTLEMENT_CONFIRMATION", "event_id", "available_at", "evidence", "settlement_date",
                        "cash_per_share", "new_security_id"?, "stock_ratio"?}]
  tr_series           optional external total-return series: {"label", "claim"? (SP500_TR | OTHER_TR), "source"?,
                      "is_etf"?, "entry_basis"? (OPEN | PREVIOUS_CLOSE), "rows": [{"date", "total_return_index",
                      "open_total_return_index"?, "currency": "USD"}]}
  Numbers in records, quotes, prices, events and tr_series are read exactly (JSON numbers become Decimal, never float;
  decimal text is accepted). companyfacts and filings are read as the SEC publishes them. Dates are ISO text.

Outputs: DIR must be outside this repository checkout and every working tree of it ('git worktree list';
OUTPUT_INSIDE_REPO) and outside any other git working tree or git directory ('git -C <parent> rev-parse --git-dir'
must fail; OUTPUT_INSIDE_GIT_WORKTREE), and its parent must exist (review F10). A new DIR is created with mode 0700; an
existing DIR must be a private (0700-type) directory of this user. The payload's run block and manifest.json carry the
settings body and a reproduction command whose private file locations are placeholders with their sha256 (review F11). Every file is created with
O_CREAT|O_EXCL|O_NOFOLLOW, mode 0600, so an existing file is never overwritten (OUTPUT_EXISTS); manifest.json is written
last. --generated-at fixes the UTC timestamp so a replay of the same inputs and code is byte-identical.
stdout carries counts, statuses, the run_id and file names only: never a price, a score of a named security or a security
ID. A refusal prints 'REFUSED <CODE>' to stderr and exits 2.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from investment_system.research.exp_deciles import handoff, runner, schedule, settings, synthetic  # noqa: E402

SELECTION_FILE = 'selection_inputs.json'
LEDGER_FILE = 'ledger_outputs.json'
MANIFEST_FILE = handoff.MANIFEST_FILE
CODE_TREE_DIRTY = 'CODE_TREE_DIRTY'
QUOTES_NOT_SUPPLIED = 'QUOTES_NOT_SUPPLIED'
PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED = 'PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED'
SELECTION_INPUT_MANIFEST_DIFFERS = 'SELECTION_INPUT_MANIFEST_DIFFERS'
SELECTION_CODE_SHA_DIFFERS_FROM_LEDGER = 'SELECTION_CODE_SHA_DIFFERS_FROM_LEDGER'
_CODE = re.compile(r'[A-Z][A-Z0-9_]{2,63}')
_CHUNK = 1 << 20


class CliError(Exception):
    """Refusal; the message is an UPPER_SNAKE code."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's own message repeats argv (paths); only a fixed code is printed.
        raise CliError('INVALID_ARGUMENTS')


# ---- reading --------------------------------------------------------------------------------------------------------
def _read_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError:
        raise CliError('INPUT_NOT_READABLE') from None


def _hash_file(path):
    digest = hashlib.sha256()
    try:
        with open(path, 'rb') as handle:
            for block in iter(lambda: handle.read(_CHUNK), b''):
                digest.update(block)
    except OSError:
        raise CliError('MANIFEST_RESOURCE_MISSING') from None
    return digest.hexdigest()


def _refuse_constant(_value):
    raise CliError('NON_FINITE_NUMBER_IN_INPUT')


def _json(data, *, exact):
    try:
        return json.loads(data.decode('utf-8'), parse_float=Decimal if exact else float,
                          parse_constant=_refuse_constant)
    except (UnicodeDecodeError, ValueError):
        raise CliError('INPUT_NOT_JSON') from None


class Bundle:
    """The verified input manifest and lazy, re-verified access to its resources."""

    def __init__(self, manifest_path):
        data = _read_bytes(manifest_path)
        self.manifest = handoff.parse_input_manifest(data)
        self.base = Path(manifest_path).absolute().parent
        for resource in self.manifest['resources']:            # every file before any use
            if _hash_file(self.path(resource)) != resource['sha256']:
                raise handoff.HandoffError('MANIFEST_HASH_MISMATCH')

    def path(self, resource):
        path = Path(resource['path'])
        return path if path.is_absolute() else self.base / path

    def read(self, resource, *, exact=True):
        data = _read_bytes(self.path(resource))
        handoff.verify_resource(resource, data)                 # the parsed bytes are the hashed bytes
        return _json(data, exact=exact)

    def of(self, kind, qualifier=None):
        return handoff.resources_of(self.manifest, kind, qualifier)

    def concat(self, kind, *, exact=True):
        rows = []
        for resource in self.of(kind):
            payload = self.read(resource, exact=exact)
            if not isinstance(payload, list):
                raise CliError(f'{kind.upper()}_MUST_BE_A_LIST')
            rows.extend(payload)
        return rows


def _cik_key(value):
    text = str(value).strip() if isinstance(value, (str, int)) and not isinstance(value, bool) else ''
    if not text.isdigit() or len(text) > 10 or int(text) == 0:
        raise CliError('COMPANYFACTS_CIK_INVALID')
    return text.zfill(10)


def _companyfacts_loader(bundle):
    per_cik, merged = {}, {}
    for resource in bundle.of('companyfacts'):
        _, qualifier = handoff.resource_kind(resource['name'])
        if qualifier is not None and qualifier.isdigit():
            cik = _cik_key(qualifier)
            if cik in per_cik:
                raise CliError('DUPLICATE_COMPANYFACTS_CIK')
            per_cik[cik] = resource
            continue
        payload = bundle.read(resource, exact=False)
        if not isinstance(payload, dict):
            raise CliError('COMPANYFACTS_INVALID')
        items = {payload.get('cik'): payload} if 'facts' in payload else payload
        for key, facts in items.items():
            cik = _cik_key(key)
            if cik in merged or not isinstance(facts, dict):
                raise CliError('DUPLICATE_COMPANYFACTS_CIK' if cik in merged else 'COMPANYFACTS_INVALID')
            merged[cik] = facts
    if set(per_cik) & set(merged):
        raise CliError('DUPLICATE_COMPANYFACTS_CIK')

    def load(cik):
        if cik in merged:
            return merged[cik]
        resource = per_cik.get(cik)
        if resource is None:
            return None
        payload = bundle.read(resource, exact=False)
        if not isinstance(payload, dict) or 'facts' not in payload or _cik_key(payload.get('cik')) != cik:
            raise CliError('COMPANYFACTS_CIK_MISMATCH')
        return payload

    return load


def _per_year(bundle, kind, year, key, signal_day, *, required, optional=()):
    """payload[key] of the kind:<year> file, or (payload[key], {optional key: value}) when optional keys are named."""
    found = bundle.of(kind, str(year))
    if not found:
        if required:
            raise CliError(f'{kind.upper()}_FOR_YEAR_MISSING')
        return None
    payload = bundle.read(found[0], exact=True)
    if not isinstance(payload, dict) or not {'signal_day', key} <= set(payload) or \
            set(payload) - {'signal_day', key, *optional}:
        raise CliError(f'{kind.upper()}_FILE_INVALID')
    if payload['signal_day'] != signal_day:
        raise CliError(f'{kind.upper()}_SIGNAL_DAY_MISMATCH')
    if optional:
        return payload[key], {k: payload[k] for k in optional if k in payload}
    return payload[key]


def _cik_list(value):
    return isinstance(value, list) and all(isinstance(c, (str, int)) and not isinstance(c, bool) for c in value)


def _previous_u_a(path, year):
    """({'members', 'unknown'}, sha256, flags) of a --previous-u-a file (see the module doc)."""
    data = _read_bytes(path)
    payload = _json(data, exact=False)
    flags = []
    if isinstance(payload, dict) and 'schema' in payload:
        if payload.get('schema') != runner.SELECTION_SCHEMA:
            raise CliError('PREVIOUS_U_A_INVALID')
        if payload.get('year') != year - 1:
            raise CliError('PREVIOUS_U_A_YEAR_MISMATCH')
        _verify_selection_file(Path(path), data, payload)
        state = runner.u_a_state(payload)
    elif isinstance(payload, dict) and set(payload) == {'members', 'unknown'} and _cik_list(payload['members']) \
            and all(isinstance(u, str) for u in payload['unknown']):
        state = {'members': payload['members'], 'unknown': payload['unknown']}
    elif _cik_list(payload):
        state = {'members': payload, 'unknown': []}
        flags.append(PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED)
    else:
        raise CliError('PREVIOUS_U_A_INVALID')
    return state, handoff.sha256_hex(data), flags


def _run_files(directory):
    """({file name: bytes} of the regular files of a run directory except manifest.json, irregular entry count)."""
    files, irregular = {}, 0
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if entry.name == MANIFEST_FILE:
            continue
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            irregular += 1
            continue
        files[entry.name] = _read_bytes(entry.path)
    return files, irregular


def _verify_selection_file(path, data, payload):
    """A selection_inputs.json must verify against its select run's manifest.json (review F7): the run directory
    verifies, the manifest is a 'select' run listing this file's exact sha256, and the payload's run block names the same
    run, input manifest and code SHA. Returns the manifest."""
    directory = Path(path).absolute().parent
    manifest_path = directory / MANIFEST_FILE
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise CliError('SELECTION_MANIFEST_MISSING')
    manifest = _json(_read_bytes(manifest_path), exact=False)
    if not isinstance(manifest, dict):
        raise CliError('SELECTION_MANIFEST_MISMATCH')
    files, irregular = _run_files(directory)
    if not handoff.verify_output_manifest(manifest, files)['ok'] or irregular:
        raise CliError('SELECTION_MANIFEST_MISMATCH')
    listed = {item.get('file'): item.get('sha256') for item in manifest.get('outputs') or [] if isinstance(item, dict)}
    run = payload.get('run') if isinstance(payload.get('run'), dict) else {}
    if (not isinstance(manifest.get('stage'), dict) or manifest['stage'].get('name') != 'select'
            or listed.get(Path(path).name) != handoff.sha256_hex(data) or run.get('run_id') != manifest.get('run_id')
            or run.get('input_manifest_sha256') != manifest.get('input_manifest_sha256')
            or run.get('code_sha') != manifest.get('code_sha')):
        raise CliError('SELECTION_MANIFEST_MISMATCH')
    return manifest


# ---- code state -----------------------------------------------------------------------------------------------------
def _git(*args):
    try:
        done = subprocess.run(['git', '-C', str(REPO_ROOT), *args], capture_output=True, text=True, timeout=60,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _clean_env():
    return {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}


def _inside_git(directory):
    """True when `directory` lies in any git working tree or git directory (git -C <dir> rev-parse --git-dir)."""
    try:
        done = subprocess.run(['git', '-C', str(directory), 'rev-parse', '--git-dir'], capture_output=True, text=True,
                              timeout=60, check=False, env=_clean_env())
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _worktrees():
    """Every working tree of this repository ('git worktree list --porcelain'), the main checkout included."""
    out = _git('worktree', 'list', '--porcelain') or ''
    return [Path(line[len('worktree '):]).resolve() for line in out.splitlines() if line.startswith('worktree ')]


def code_state():
    """(git HEAD of the checkout or None, flags). CODE_TREE_DIRTY when implementation/src or tools differ from HEAD."""
    head = _git('rev-parse', 'HEAD')
    if head is None:
        return None, []
    status = _git('status', '--porcelain', '--', 'implementation/src', 'implementation/tools')
    return head.strip(), ([CODE_TREE_DIRTY] if status is None or status.strip() else [])


# ---- writing --------------------------------------------------------------------------------------------------------
def _output_dir(value):
    raw = Path(value)
    if '..' in raw.parts:
        raise CliError('OUTPUT_PATH_INVALID')
    target = raw.absolute()
    if not target.parent.is_dir():
        raise CliError('OUTPUT_PARENT_MISSING')
    target = target.parent.resolve() / target.name
    for tree in [REPO_ROOT.resolve()] + _worktrees():
        if target == tree or target.is_relative_to(tree):
            raise CliError('OUTPUT_INSIDE_REPO')
    if _inside_git(target.parent):
        raise CliError('OUTPUT_INSIDE_GIT_WORKTREE')
    if os.path.lexists(target):
        info = os.lstat(target)
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077 or info.st_uid != os.getuid():
            raise CliError('OUTPUT_DIR_UNSAFE')
    return target


def _refuse_existing(directory, names):
    for name in names:
        if os.path.lexists(directory / name):
            raise CliError('OUTPUT_EXISTS')


def _write_outputs(directory, files):
    """files: [(name, bytes)] in write order. mkdir 0700 when absent; each file O_CREAT|O_EXCL|O_NOFOLLOW 0600."""
    if not os.path.lexists(directory):
        os.mkdir(directory, 0o700)
    info = os.lstat(directory)
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise CliError('OUTPUT_DIR_UNSAFE')
    dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, data in files:
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
            except FileExistsError:
                raise CliError('OUTPUT_EXISTS') from None
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _generated_at(value):
    return handoff.generated_at_text(value if value is not None else datetime.now(timezone.utc))


def _emit(pairs):
    for key, value in pairs:
        print(f'{key}={value}')


# ---- subcommands ----------------------------------------------------------------------------------------------------
def cmd_schedule(_args):
    check = schedule.verify_frozen()
    for row in check['rows']:
        if isinstance(row, dict):
            print(f"{row.get('year')} third_monday={row.get('third_monday')} S={row.get('S')} T={row.get('T')} "
                  f"filing_cutoff={row.get('filing_cutoff')}")
    _emit([('schedule', 'OK' if check['ok'] else 'MISMATCH'), ('rows', len(check['rows'])),
           ('mismatches', len(check['mismatches']))])
    return 0 if check['ok'] else 1


def cmd_select(args):
    out_dir = _output_dir(args.out)
    _refuse_existing(out_dir, (SELECTION_FILE, MANIFEST_FILE))
    generated_at = _generated_at(args.generated_at)
    bundle = Bundle(args.manifest)
    try:
        frozen = schedule.frozen_row(year=args.year)
    except ValueError:
        raise CliError('YEAR_NOT_IN_FROZEN_SCHEDULE') from None
    for kind in ('companyfacts', 'filings'):
        if not bundle.of(kind):
            raise CliError(f'{kind.upper()}_NOT_SUPPLIED')
    records, more = _per_year(bundle, 'records', args.year, 'records', frozen['S'], required=True,
                              optional=('terminations',))
    quotes = _per_year(bundle, 'quotes', args.year, 'quotes', frozen['S'], required=False)
    previous, extra, previous_flags = None, [], []
    if args.previous_u_a is not None:
        previous, digest, previous_flags = _previous_u_a(args.previous_u_a, args.year)
        extra.append({'role': 'previous_u_a', 'sha256': digest})
    code_sha, code_flags = code_state()
    stage = {'name': 'select', 'year': args.year, 'previous_u_a_sha256': extra[0]['sha256'] if extra else None}
    run = handoff.run_metadata(input_manifest=bundle.manifest, code_sha=code_sha, stage=stage,
                               generated_at=generated_at, extra_inputs=extra, code_flags=code_flags)
    payload = runner.selection_stage(records, year=args.year, companyfacts=_companyfacts_loader(bundle),
                                     filing_rows=bundle.concat('filings', exact=False), quotes=quotes,
                                     previous_u_a=None if previous is None else previous['members'],
                                     previous_u_a_unknown=None if previous is None else previous['unknown'],
                                     terminations=more.get('terminations'), run=run)
    payload['flags'] = payload['flags'] + previous_flags
    if quotes is None:
        payload['flags'] = payload['flags'] + [QUOTES_NOT_SUPPLIED]
    body = handoff.canonical_bytes(payload)
    manifest = handoff.build_output_manifest(run, bundle.manifest, {SELECTION_FILE: body})
    _write_outputs(out_dir, [(SELECTION_FILE, body), (MANIFEST_FILE, handoff.canonical_bytes(manifest))])
    counts = payload['counts']
    strategies = [sel for by_group in counts['strategies'].values() for sel in by_group.values()]
    pairs = [('stage', 'select'), ('run_id', run['run_id']), ('year', args.year),
             ('first_build', str(payload['first_build']).lower()),
             ('flags', ','.join(payload['flags'] + run['code_sha_flags']) or '-')]
    for group in settings.GROUPS:
        c = counts[group]
        pairs.append((group, f"candidate:{c['candidate']} eligible:{c['eligible']} excluded:{c['excluded']} "
                             f"unknown:{c['unknown']}"))
    pairs += [('strategy_cells_run', sum(1 for s in strategies if s['status'] == 'RUN')),
              ('strategy_cells_not_run', sum(1 for s in strategies if s['status'] != 'RUN')),
              ('files', f'{SELECTION_FILE},{MANIFEST_FILE}')]
    _emit(pairs)
    return 0


def cmd_ledger(args):
    out_dir = _output_dir(args.out)
    _refuse_existing(out_dir, (LEDGER_FILE, MANIFEST_FILE))
    generated_at = _generated_at(args.generated_at)
    bundle = Bundle(args.manifest)
    if not bundle.of('prices'):
        raise CliError('PRICES_NOT_SUPPLIED')
    selections, hashes, manifests = [], [], []
    for path in args.selection:
        data = _read_bytes(path)
        payload = _json(data, exact=False)
        if not isinstance(payload, dict) or payload.get('schema') != runner.SELECTION_SCHEMA:
            raise CliError('SELECTION_SCHEMA_INVALID')
        manifests.append(_verify_selection_file(Path(path), data, payload))
        selections.append(payload)
        hashes.append((payload.get('year'), handoff.sha256_hex(data)))
    if len({year for year, _ in hashes}) != len(hashes) or not all(type(y) is int for y, _ in hashes):
        raise CliError('SELECTION_YEAR_DUPLICATE')
    hashes.sort()
    selection_code = {m['code_sha'] for m in manifests}
    if len(selection_code) != 1:
        raise CliError('SELECTION_CODE_SHA_MISMATCH')
    tr = bundle.of('tr_series')
    tr_series = bundle.read(tr[0], exact=True) if tr else None
    extra = [{'role': f'selection:{year}', 'sha256': digest} for year, digest in hashes]
    code_sha, code_flags = code_state()
    stage = {'name': 'ledger', 'selection_sha256': [digest for _, digest in hashes], 'end': args.end,
             'daily_positions': bool(args.daily_positions)}
    run = handoff.run_metadata(input_manifest=bundle.manifest, code_sha=code_sha, stage=stage,
                               generated_at=generated_at, extra_inputs=extra, code_flags=code_flags)
    payload = runner.ledger_stage(selections, prices=bundle.concat('prices'), events=bundle.concat('events'),
                                  end=args.end, tr_series=tr_series, daily_positions=args.daily_positions, run=run)
    if any(m['input_manifest_sha256'] != bundle.manifest['sha256'] for m in manifests):
        payload['flags'].append(SELECTION_INPUT_MANIFEST_DIFFERS)
    if selection_code != {run['code_sha']}:
        payload['flags'].append(SELECTION_CODE_SHA_DIFFERS_FROM_LEDGER)
    body = handoff.canonical_bytes(payload)
    manifest = handoff.build_output_manifest(run, bundle.manifest, {LEDGER_FILE: body})
    _write_outputs(out_dir, [(LEDGER_FILE, body), (MANIFEST_FILE, handoff.canonical_bytes(manifest))])
    counts = payload['counts']
    by_status = counts['ledger_runs_by_status']
    _emit([('stage', 'ledger'), ('run_id', run['run_id']), ('years', len(payload['selection_years'])),
           ('end_rule', payload['end_rule']), ('end_valuation', payload['end_valuation']),
           ('sessions', payload['session_count']), ('flags', ','.join(payload['flags'] + run['code_sha_flags']) or '-'),
           ('portfolios', counts['portfolios']), ('portfolios_run', counts['portfolios_run']),
           ('portfolios_all_cash', counts['portfolios_all_cash']), ('cash_years', counts['cash_years']),
           ('ledger_runs', counts['ledger_runs']),
           ('ledger_runs_by_status', ','.join(f'{k}:{v}' for k, v in sorted(by_status.items())) or '-'),
           ('daily_coverage', ','.join(f'{k}:{v}' for k, v in sorted(counts['daily_coverage'].items())) or '-'),
           ('settlement_conflicts', counts['settlement_conflicts']),
           ('external_total_return', counts['external_total_return'] or '-'),
           ('files', f'{LEDGER_FILE},{MANIFEST_FILE}')])
    return 0


def cmd_verify(args):
    directory = Path(args.run)
    try:
        info = os.lstat(directory)
    except OSError:
        raise CliError('RUN_DIR_MISSING') from None
    if not stat.S_ISDIR(info.st_mode):
        raise CliError('RUN_DIR_MISSING')
    manifest = _json(_read_bytes(directory / MANIFEST_FILE), exact=False)
    files, irregular = _run_files(directory)
    result = handoff.verify_output_manifest(manifest, files)
    ok = result['ok'] and irregular == 0
    _emit([('stage', 'verify'), ('run_id', result['run_id']), ('run_id_ok', str(result['run_id_ok']).lower()),
           ('settings_ok', str(result['settings_ok']).lower()),
           ('files', len(result['files'])),
           ('statuses', ','.join(f'{k}:{v}' for k, v in sorted(result['counts'].items())) or '-'),
           ('irregular_entries', irregular), ('verify', 'OK' if ok else 'FAILED')])
    for row in result['files']:
        print(f"file {row['file']} {row['status']}")
    return 0 if ok else 1


SYNTHETIC_END = '2019-03-29'


def cmd_synthetic(args):
    root = _output_dir(args.out)
    if not os.path.lexists(root):
        os.mkdir(root, 0o700)
    bundle_dir = _output_dir(str(root / 'bundle'))
    _refuse_existing(bundle_dir, tuple(name for name, _ in synthetic.bundle_bytes()))
    _write_outputs(bundle_dir, synthetic.bundle_bytes())
    manifest = str(bundle_dir / 'manifest.json')
    when = ['--generated-at', args.generated_at] if args.generated_at is not None else []
    steps = [
        ['select', '--manifest', manifest, '--year', '2018', '--out', str(root / 'select-2018')] + when,
        ['select', '--manifest', manifest, '--year', '2019', '--previous-u-a',
         str(root / 'select-2018' / SELECTION_FILE), '--out', str(root / 'select-2019')] + when,
        ['ledger', '--manifest', manifest, '--selection', str(root / 'select-2018' / SELECTION_FILE), '--selection',
         str(root / 'select-2019' / SELECTION_FILE), '--out', str(root / 'ledger'), '--end', SYNTHETIC_END] + when,
    ]
    for argv in steps:
        args_i = build_parser().parse_args(argv)
        if args_i.func(args_i) != 0:
            raise CliError('SYNTHETIC_STEP_FAILED')
    status = 0
    for name in ('select-2018', 'select-2019', 'ledger'):
        if cmd_verify(build_parser().parse_args(['verify', '--run', str(root / name)])) != 0:
            status = 1
        print(f"run {name} manifest_sha256={handoff.sha256_hex(_read_bytes(root / name / MANIFEST_FILE))}")
    print(f"bundle manifest_sha256={handoff.sha256_hex(_read_bytes(bundle_dir / 'manifest.json'))}")
    _emit([('stage', 'synthetic'), ('synthetic', 'OK' if status == 0 else 'VERIFY_FAILED')])
    return status


def build_parser():
    parser = _Parser(prog='exp_stock_indicator_deciles', description='EXP-STOCK-INDICATOR-DECILES-v1 private runs',
                     allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True, parser_class=_Parser)
    p = sub.add_parser('schedule', allow_abbrev=False)
    p.set_defaults(func=cmd_schedule)
    p = sub.add_parser('select', allow_abbrev=False)
    p.add_argument('--manifest', required=True)
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--previous-u-a')
    p.add_argument('--out', required=True)
    p.add_argument('--generated-at')
    p.set_defaults(func=cmd_select)
    p = sub.add_parser('ledger', allow_abbrev=False)
    p.add_argument('--manifest', required=True)
    p.add_argument('--selection', action='append', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--generated-at')
    p.add_argument('--end')
    p.add_argument('--daily-positions', action='store_true')
    p.set_defaults(func=cmd_ledger)
    p = sub.add_parser('verify', allow_abbrev=False)
    p.add_argument('--run', required=True)
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser('synthetic', allow_abbrev=False)
    p.add_argument('--out', required=True)
    p.add_argument('--generated-at')
    p.set_defaults(func=cmd_synthetic)
    return parser


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (CliError, handoff.HandoffError, runner.RunnerError) as exc:
        code = str(exc)
    except (ValueError, TypeError, KeyError, OSError) as exc:     # engine refusals carry UPPER_SNAKE codes
        code = str(exc) if _CODE.fullmatch(str(exc)) else 'PROCESSING_FAILED'
    print(f'REFUSED {code if _CODE.fullmatch(code) else "PROCESSING_FAILED"}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
