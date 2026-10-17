#!/usr/bin/env python3
"""Daily Universe504 SEC shard -> public price-free `sec-universe-shares.json` + `sec-universe-qg.json`.

User decision 2026-10-11 (M3 shares option a). One shard per New York calendar day
(day ordinal mod the fixed v0 shard count) is collected through the paced SEC
client and merged into the previously published Pages copy, so every code keeps
its last collected row with its own acquired_at until a new collection of the
code replaces it (also with NOT_AVAILABLE); rows past the v0 stale window are
STALE. Raw SEC bytes never reach Pages. If RAW_REPO_TOKEN is set they are
uploaded as a dated private release asset; otherwise RAW_UPLOAD_NOT_CONFIGURED.
Only fixed codes and counts are printed: no names, values, URLs or secrets.

Shard day (owner instruction 2026-10-17, fallback runs): the New York date is the UTC date for any start from
04:00 UTC (EDT) / 05:00 UTC (EST) to 24:00 UTC, so the scheduled 22:17 UTC run keeps its shard and raw tag date; a late
or fallback run started after 00:00 UTC keeps the intended day's shard instead of taking the next day's shard twice.

User queue 2.1: the SAME fetched companyfacts/submissions bytes also produce the
price-free Q·G factor scores (`sec-universe-qg.json`, the TARGET sec-qg-factors path)
in-process: no extra SEC request. That file merges with its own previous Pages copy
by the same rules; the shares output format is unchanged.

QGV v2 (user decision 2026-10-13, GSQ-022 pending): the same bytes also give the v2 Q·G raw
metrics and `v_inputs_v2` (`sec-qgv2.json`). TARGET rows staged earlier in the same output
folder by tools/public_screens_pipeline.py --live are carried in; percentiles are recomputed at
publication over all current LIVE/STALE Universe rows. A v2 failure never changes the other files.

`--all-shards` (one-off, owner instruction 2026-10-15): every shard 0..shard_count-1 in one run with one registry
fetch and the same serial paced client, so all 504 codes are recalculated under the current rules and published at
once. Each shard prints its own counts line and uploads its own private raw release; a shard that fails entirely keeps
its previous rows. Every collected code follows the same merge rule as a daily run (owner rule 2026-10-17): this run's
row replaces the kept one in all three files, a row without data being NOT_AVAILABLE with its reason (never an older
rule's value or 0). The daily default (one shard per New York calendar day) is unchanged. Because a run with failed
shards still exits 0, the run ends with one `SEC_UNIVERSE_SHARD_REPORT` line per shard and one `SEC_UNIVERSE_ALL_SHARDS`
total line: issuers collected/failed and the published LIVE/STALE rows still taken from the previous file (shares, Q·G
and QGV v2 separately; counts only).
"""
# Owner decision 2026-10-17 (option a): every merge applies `previous_decision` (universe/sec_universe_shares.py). A code
# whose symbol is unresolved today, or whose row records no verified collection (shares identity unconfirmed, a builder
# failure, a row the strict check rejects, a shares row without a count after the cover fetch failed), keeps its
# verified previous row of the same CIK unchanged. Identity conflicts (another CIK for the code, a ticker claimed by
# several CIKs, an SEC response naming another CIK) never keep an earlier row: a ticker claimed by several CIKs has no
# row this run. Owner decision UNI-WITHDRAWN (a) 2026-10-17: such a code whose kept row in a file has a collection record
# is published there as a withdrawal row (IDENTITY_CONFLICT_WITHDRAWN, detected_at, withdrawn_acquired_at, withdrawn_cik,
# no values), kept unchanged until a confirmed new collection; without a kept record it is CIK_UNRESOLVED without
# acquired_at (nothing invented). Each summary line counts withdrawn rows. Owner rule 2026-10-17 (later): a row of a successful
# collection replaces the kept row also when it is NOT_AVAILABLE or INVALID_INPUT (daily and --all-shards alike).
# `SEC_UNIVERSE_COLLECTION` counts new collections, failures and published rows of an earlier run.
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from investment_system.providers.sec_collection import MAX_BODY_BYTES, SecCollectionClient, SecCollectionError
from investment_system.providers.sec_universe_collection import (
    UniverseSecClient, collect_partition, daily_partition, fetch_ticker_exchange, universe_registry,
)
from investment_system.universe.sec_universe_shares import (
    FILENAME, MAX_BYTES, build_issuer_records, empty_record, encode, is_withdrawal, load_config, merge, parse_json,
    require_universe_shares, select_cover_filing, shard_day, shard_index_for, universe_codes, upgrade_legacy,
)
from investment_system.universe import sec_universe_qg as qg
from investment_system.universe import sec_qgv2 as qgv2

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + FILENAME
QG_SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + qg.FILENAME
QGV2_SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + qgv2.FILENAME
RAW_REPO = 'kco994553-star/investment-system1-raw'
# Issuer failures that are identity conflicts (never transient): the SEC response named another CIK, or the issuer
# is outside the registry scope of the client.
IDENTITY_FAILURES = frozenset({'SEC_CIK_MISMATCH', 'SEC_ISSUER_NOT_ALLOWED'})
RAW_TOKEN_ENV = 'RAW_REPO_TOKEN'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('SEC_UNIVERSE_SHARES CONFIG_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def _fetch_body(source, limit, open_response):
    """Live Pages copy bytes, None on 404. Other failures raise OSError."""
    request = urllib.request.Request(source, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != source:
                raise OSError('PREVIOUS_FETCH_FAILED')
            return response.read(limit + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None


def fetch_previous(*, open_response=None):
    """Live Pages copy -> validated payload, None on 404. Other failures raise.

    A copy published before `unlisted_classes` existed is upgraded (NOT_COLLECTED entries, rows unchanged)."""
    body = _fetch_body(SOURCE, MAX_BYTES, open_response)
    return None if body is None else require_universe_shares(upgrade_legacy(parse_json(body)))


def fetch_previous_qg(*, open_response=None):
    """Live Pages `sec-universe-qg.json` -> validated payload, None on 404 (start fresh). Invalid -> ValueError."""
    body = _fetch_body(QG_SOURCE, qg.MAX_BYTES, open_response)
    return None if body is None else qg.require_universe_qg(qg.parse_json(body))


def fetch_previous_qgv2(*, open_response=None):
    """Live Pages `sec-qgv2.json` -> validated payload, None on 404 (start fresh). Invalid -> ValueError."""
    body = _fetch_body(QGV2_SOURCE, qgv2.MAX_BYTES, open_response)
    return None if body is None else qgv2.require_qgv2(qgv2.parse_json(body))


def read_staged_target(directory):
    """TARGET rows staged in this output folder by the TARGET daily step ({} when absent). Invalid -> ValueError."""
    path = Path(directory) / qgv2.FILENAME
    if path.is_symlink():
        raise ValueError('SEC_QGV2_INVALID')
    if not path.is_file():
        return {}
    return qgv2.target_updates_from(qgv2.require_qgv2(qgv2.parse_json(path.read_bytes())))


def write(directory, payload, *, name=FILENAME, encoder=encode):
    directory = Path(directory)
    destination = directory / name
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('SEC_UNIVERSE_SHARES_OUTPUT_INVALID')
    body = encoder(payload)
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.sec-universe-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return body


def write_qg(directory, payload):
    return write(directory, payload, name=qg.FILENAME, encoder=qg.encode)


def write_qgv2(directory, payload):
    return write(directory, payload, name=qgv2.FILENAME, encoder=qgv2.encode)


def open_registry(*, user_agent, client_kwargs=None):
    """SEC ticker/exchange registry (one paced request) and the paced Universe client bound to it."""
    kwargs = dict(client_kwargs or {})
    base = SecCollectionClient(user_agent, **kwargs)
    registry = universe_registry(fetch_ticker_exchange(base))
    return registry, UniverseSecClient(user_agent, registry=registry, **kwargs)


def collect(*, user_agent, now=_utc_now, client_kwargs=None, raw_dir=None, config=None, qg_updates=None, qgv2_updates=None,
            shard_index=None, registry=None, client=None):
    """Collect one shard. Returns (updates, unlisted_updates, unresolved_codes, registry_sha256, shard_index, counts).

    The shard is today's (New York date ordinal mod shard_count, see `shard_day`) unless `shard_index` names one
    explicitly. `registry` and `client` (from open_registry) let one run collect several shards with one registry fetch and one paced client.
    With `qg_updates` (a dict), the same fetched bytes also fill that dict with this shard's Q·G rows (no extra request)."""
    cfg = config or load_config()
    started = now()
    if shard_index is None:
        index = shard_index_for(shard_day(started), cfg['shard_count'])
    elif type(shard_index) is int and 0 <= shard_index < cfg['shard_count']:
        index = shard_index
    else:
        raise SecCollectionError('SEC_UNIVERSE_CONFIG_INVALID')
    if registry is None or client is None:
        registry, client = open_registry(user_agent=user_agent, client_kwargs=client_kwargs)
    issuers = daily_partition(registry, shard_count=cfg['shard_count'], shard_index=index)
    bound = {code for issuer in registry.issuers for code in issuer.codes}
    unresolved = set(universe_codes()) - bound
    updates, unlisted_updates, manifest, covers = {}, {}, [], [0]
    # Codes whose cover filing fetch failed after their SEC bytes arrived (a transient failure of this collection).
    transient = set()

    def save(issuer, facts, submissions, acquired):
        if qg_updates is not None:
            # Same bytes, same issuer binding. A Q·G failure never reaches the shares path below.
            try:
                rows = qg.build_issuer_records(codes=issuer.codes, cik=issuer.cik, companyfacts_body=facts,
                                               submissions_body=submissions, acquired_at=acquired)
            except Exception:
                rows = {code: qg.empty_record(cik=issuer.cik, reasons=('INVALID_INPUT',)) for code in issuer.codes}
            qg_updates.update(rows)
        if qgv2_updates is not None:
            # QGV v2 from the same bytes; a failure is INVALID_INPUT for this issuer only.
            try:
                rows = qgv2.build_issuer_records(codes=issuer.codes, cik=issuer.cik, companyfacts_body=facts,
                                                 submissions_body=submissions, acquired_at=acquired)
            except Exception:
                rows = {code: qgv2.empty_record(cik=issuer.cik, reasons=('INVALID_INPUT',)) for code in issuer.codes}
            qgv2_updates.update(rows)
        filing = select_cover_filing(submissions, acquired)
        cover = cover_at = None
        if filing is not None:
            try:
                cover, cover_at = client.collect_cover(issuer.cik, filing['accession'], filing['primary_document'])
                covers[0] += 1
            except Exception:
                cover = cover_at = None
                transient.update(issuer.codes)
        as_of = max(acquired, cover_at) if cover_at is not None else acquired
        records, unlisted = build_issuer_records(codes=issuer.codes, cik=issuer.cik, companyfacts_body=facts, submissions_body=submissions,
                                                 acquired_at=acquired, as_of=as_of, cover_xml=cover,
                                                 cover_accession=filing['accession'] if filing else None, cover_acquired_at=cover_at)
        updates.update(records)
        unlisted_updates.update(unlisted)
        if raw_dir is not None:
            folder = Path(raw_dir) / issuer.cik
            folder.mkdir(parents=True, exist_ok=True)
            files = {'companyfacts.json': facts, 'submissions.json': submissions}
            if cover is not None:
                files['cover-' + filing['accession'] + '.xml'] = cover
            for name, body in files.items():
                (folder / name).write_bytes(body)
            manifest.append({'cik': issuer.cik, 'codes': list(issuer.codes), 'acquired_at': acquired.isoformat(),
                             'cover_acquired_at': cover_at.isoformat() if cover_at else None,
                             'sha256': {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}})

    result = collect_partition(client, issuers, on_success=save)
    # Owner decision 2026-10-17: an issuer whose SEC response named another CIK (or that the client refused as outside
    # the registry scope) is an identity conflict, not a transient failure. Its codes get NOT_AVAILABLE rows with the
    # reason and are passed to the merges as conflicts, so no earlier row is carried for them.
    conflicts = set(getattr(registry, 'conflicting_codes', ()))
    for company_index, code in result.failures:
        if code not in IDENTITY_FAILURES:
            continue
        issuer = issuers[company_index - 1]
        reason = 'CIK_MISMATCH' if code == 'SEC_CIK_MISMATCH' else 'IDENTITY_UNCONFIRMED'
        for listing in issuer.codes:
            updates[listing] = empty_record(cik=issuer.cik, reasons=(reason,))
            if qg_updates is not None:
                qg_updates[listing] = qg.empty_record(cik=issuer.cik, reasons=('INVALID_INPUT',))
            if qgv2_updates is not None:
                qgv2_updates[listing] = qgv2.empty_record(cik=issuer.cik, reasons=('INVALID_INPUT',))
            conflicts.add(listing)
    if raw_dir is not None:
        (Path(raw_dir) / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'role': 'PRIVATE_RAW_SEC_BYTES',
            'shard_count': cfg['shard_count'], 'shard_index': index, 'registry_sha256': registry.source_sha256,
            'companies': manifest}, sort_keys=True))
    counts = {'companies': len(issuers), 'collected': result.collected, 'failed': result.failed, 'covers': covers[0],
              'failures': result.failures, 'unresolved_codes': len(unresolved), 'all_failed': result.all_failed,
              'codes': {code for issuer in issuers for code in issuer.codes}, 'conflicts': conflicts, 'transient': transient}
    return updates, unlisted_updates, unresolved, registry.source_sha256, index, counts


def _archive(raw_dir, name):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz', format=tarfile.PAX_FORMAT) as tar:
        def fixed(info):
            info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = 0, 0o644, 0, 0, '', ''
            return info
        for path in sorted(Path(raw_dir).rglob('*')):
            if path.is_file() and not path.is_symlink():
                tar.add(path, arcname=name + '/' + path.relative_to(raw_dir).as_posix(), recursive=False, filter=fixed)
    return buffer.getvalue()


def upload_raw(raw_dir, *, tag, token, open_response=None):
    """Dated private release asset (tar.gz + sha256). Returns a fixed status code; never echoes the token."""
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'investment-system-raw-archive'}
    def call(url, body, content_type):
        request = urllib.request.Request(url, data=body, method='POST', headers={**headers, 'Content-Type': content_type})
        with fetch(request, timeout=120) as response:
            if response.status not in (200, 201):
                raise urllib.error.HTTPError(url, response.status, '', {}, None)
            return json.loads(response.read(1024 * 1024))
    try:
        archive = _archive(raw_dir, tag)
        digest = hashlib.sha256(archive).hexdigest()
        release = call(f'https://api.github.com/repos/{RAW_REPO}/releases', json.dumps(
            {'tag_name': tag, 'name': tag, 'body': 'Private raw SEC bytes for one Universe shard (not published).',
             'draft': False, 'prerelease': False}).encode(), 'application/json')
        release_id = release.get('id') if isinstance(release, dict) else None
        if type(release_id) is not int or release_id <= 0:
            return 'RAW_UPLOAD_FAILED code=RELEASE_INVALID'
        base = f'https://uploads.github.com/repos/{RAW_REPO}/releases/{release_id}/assets?name='
        call(base + tag + '.tar.gz', archive, 'application/gzip')
        call(base + tag + '.tar.gz.sha256', (digest + '  ' + tag + '.tar.gz\n').encode(), 'text/plain')
        return f'RAW_UPLOADED bytes={len(archive)} sha256={digest}'
    except urllib.error.HTTPError as error:
        return f'RAW_UPLOAD_FAILED code=HTTP_{int(error.code)}' if isinstance(error.code, int) else 'RAW_UPLOAD_FAILED'
    except Exception:
        return 'RAW_UPLOAD_FAILED'


def _summary(payload):
    rows = payload['records'].values()
    count = lambda key, value: sum(1 for r in rows if r[key] == value)
    return (f"live={count('state', 'LIVE')} stale={count('state', 'STALE')} not_available={count('state', 'NOT_AVAILABLE')} "
            f"withdrawn={sum(1 for r in rows if is_withdrawal(r))} single_class={count('share_class_basis', 'SINGLE_CLASS_CONFIRMED')} share_class_basis={count('share_class_basis', 'SHARE_CLASS_BASIS')} "
            f"basis_unconfirmed={count('share_class_basis', 'BASIS_UNCONFIRMED')}")


def _qg_summary(payload):
    rows = payload['records'].values()
    count = lambda value: sum(1 for r in rows if r['state'] == value)
    scored = sum(1 for r in rows for score in r['factors'].values() if score is not None)
    return (f"live={count('LIVE')} stale={count('STALE')} not_available={count('NOT_AVAILABLE')} "
            f"withdrawn={sum(1 for r in rows if is_withdrawal(r))} factor_scores={scored}")


def run(out, *, live, preserve_only=False, environ=None, now=_utc_now, client_kwargs=None,
        open_previous=None, open_upload=None, all_shards=False):
    environ = os.environ if environ is None else environ
    try:
        cfg = load_config()
    except Exception:
        print('SEC_UNIVERSE_SHARES CONFIG_INVALID')
        return 1
    try:
        previous = fetch_previous(open_response=open_previous)
    except ValueError:
        print('SEC_UNIVERSE_SHARES PREVIOUS_DISCARDED')
        previous = None
    except Exception:
        print('SEC_UNIVERSE_SHARES PREVIOUS_FETCH_FAILED')
        return 1
    # Both previous copies are read before anything is written: a network failure on either writes nothing.
    try:
        previous_qg = fetch_previous_qg(open_response=open_previous)
    except ValueError:
        print('SEC_UNIVERSE_QG PREVIOUS_DISCARDED')
        previous_qg = None
    except Exception:
        print('SEC_UNIVERSE_QG PREVIOUS_FETCH_FAILED')
        return 1
    # QGV v2: the TARGET rows staged in this folder are read before anything here is written.
    try:
        staged_target = read_staged_target(out)
    except Exception:
        print('SEC_QGV2 STAGED_TARGET_DISCARDED')
        staged_target = {}
    try:
        previous_qgv2 = fetch_previous_qgv2(open_response=open_previous)
    except ValueError:
        print('SEC_QGV2 PREVIOUS_DISCARDED')
        previous_qgv2 = None
    except Exception:
        print('SEC_QGV2 PREVIOUS_FETCH_FAILED')
        return 1
    try:
        if previous is not None:
            write(out, merge(previous, {}, as_of=now(), shard_index=previous['last_shard_index'], config=cfg))
            print('SEC_UNIVERSE_SHARES PREVIOUS_RESTORED')
        elif preserve_only:
            print('SEC_UNIVERSE_SHARES PREVIOUS_NOT_AVAILABLE')
    except Exception:
        print('SEC_UNIVERSE_SHARES OUTPUT_FAILED')
        return 1
    try:
        if previous_qg is not None:
            write_qg(out, qg.merge(previous_qg, {}, as_of=now(), shard_index=previous_qg['last_shard_index'], config=cfg))
            print('SEC_UNIVERSE_QG PREVIOUS_RESTORED')
        elif preserve_only:
            print('SEC_UNIVERSE_QG PREVIOUS_NOT_AVAILABLE')
    except Exception:
        print('SEC_UNIVERSE_QG OUTPUT_FAILED')
        return 1
    # A v2 failure is reported with a fixed code and never fails the other files (the last valid v2 copy stays).
    try:
        if previous_qgv2 is not None or staged_target:
            write_qgv2(out, qgv2.merge(previous_qgv2, {}, as_of=now(), config=cfg, target_updates=staged_target,
                                       shard_index=previous_qgv2['last_shard_index'] if previous_qgv2 else None))
            print('SEC_QGV2 PREVIOUS_RESTORED' + (f' staged_target={len(staged_target)}' if staged_target else ''))
        elif preserve_only:
            print('SEC_QGV2 PREVIOUS_NOT_AVAILABLE')
    except Exception:
        print('SEC_QGV2 OUTPUT_FAILED')
    if preserve_only:
        return 0
    if not live:
        print('SEC_UNIVERSE_SHARES LIVE_OPT_IN_REQUIRED')
        return 1
    token = environ.get(RAW_TOKEN_ENV) or None
    if all_shards:
        return _run_all_shards(out, cfg=cfg, environ=environ, now=now, client_kwargs=client_kwargs, token=token,
                               open_upload=open_upload, previous=previous, previous_qg=previous_qg,
                               previous_qgv2=previous_qgv2, staged_target=staged_target)
    with tempfile.TemporaryDirectory(prefix='sec-universe-raw-') as private:
        raw_dir = Path(private) / 'raw' if token else None
        qg_updates, qgv2_updates = {}, {}
        stats = {'shares': {}, 'qg': {}, 'qgv2': {}}
        try:
            updates, unlisted_updates, unresolved, registry_sha, index, counts = collect(
                user_agent=environ.get('SEC_USER_AGENT', ''), now=now, client_kwargs=client_kwargs, raw_dir=raw_dir, config=cfg,
                qg_updates=qg_updates, qgv2_updates=qgv2_updates)
        except SecCollectionError as error:
            code = error.args[0] if error.args and error.args[0] in {'SEC_USER_AGENT_INVALID', 'SEC_UNIVERSE_INPUT_INVALID',
                'SEC_UNIVERSE_CONFIG_INVALID', 'SEC_CONFIG_INVALID', 'SEC_HTTP_RETRIES_EXHAUSTED', 'SEC_TRANSPORT_RETRIES_EXHAUSTED'} else 'SEC_UNIVERSE_FAILED'
            print('SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN code=' + code + (' previous_kept' if previous is not None else ''))
            return 0 if previous is not None else 1
        except Exception:
            print('SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN code=SEC_UNIVERSE_FAILED' + (' previous_kept' if previous is not None else ''))
            return 0 if previous is not None else 1
        for company_index, code in counts['failures']:
            print(f'SEC_UNIVERSE_FAILURE company_index={company_index} code={code}')
        try:
            payload = merge(previous, updates, as_of=now(), shard_index=index, registry_sha256=registry_sha,
                            unresolved=unresolved, config=cfg, unlisted_updates=unlisted_updates,
                            conflicts=counts['conflicts'], stats=stats['shares'], transient=counts['transient'])
            write(out, payload)
        except Exception:
            print('SEC_UNIVERSE_SHARES OUTPUT_FAILED')
            return 1
        print(f"SEC_UNIVERSE_SHARES shard={index}/{cfg['shard_count']} companies={counts['companies']} "
              f"collected={counts['collected']} failed={counts['failed']} covers={counts['covers']} "
              f"unresolved_codes={counts['unresolved_codes']} {_summary(payload)}")
        try:
            qg_payload = qg.merge(previous_qg, qg_updates, as_of=now(), shard_index=index, registry_sha256=registry_sha,
                                  unresolved=unresolved, config=cfg, conflicts=counts['conflicts'], stats=stats['qg'])
            write_qg(out, qg_payload)
        except Exception:
            print('SEC_UNIVERSE_QG OUTPUT_FAILED')
            return 1
        shard_rows = [qg_updates[code] for code in sorted(qg_updates)]
        print(f"SEC_UNIVERSE_QG shard={index}/{cfg['shard_count']} codes={len(shard_rows)} "
              f"scored_codes={sum(1 for r in shard_rows if r['state'] != 'NOT_AVAILABLE')} {_qg_summary(qg_payload)}")
        qgv2_payload = None
        try:
            qgv2_payload = qgv2.merge(previous_qgv2, qgv2_updates, as_of=now(), shard_index=index, registry_sha256=registry_sha,
                                      unresolved=unresolved, config=cfg, target_updates=staged_target,
                                      conflicts=counts['conflicts'], stats=stats['qgv2'])
            write_qgv2(out, qgv2_payload)
            v2_rows = [qgv2_updates[code] for code in sorted(qgv2_updates)]
            print(qgv2.summary_line(qgv2_payload, prefix=f"SEC_QGV2 shard={index}/{cfg['shard_count']} codes={len(v2_rows)} "
                                    f"with_data={sum(1 for r in v2_rows if r['fiscal_year_end'] is not None)}"))
        except Exception:
            qgv2_payload = None
            print('SEC_QGV2 OUTPUT_FAILED previous_kept')
        print(collection_line(f"shard={index}/{cfg['shard_count']}", issuers=counts['companies'], collected=counts['collected'],
                              failed=counts['failed'], unresolved=unresolved, attempted=counts['codes'],
                              files=(('shares', payload, updates), ('qg', qg_payload, qg_updates),
                                     ('qgv2', qgv2_payload, qgv2_updates)), stats=stats))
        print(withdrawal_line(f"shard={index}/{cfg['shard_count']}", stats))
        if counts['all_failed']:
            print('SEC_UNIVERSE_SHARES SHARD_ALL_FAILED previous_kept')
        if token is None:
            print('RAW_UPLOAD_NOT_CONFIGURED')
        elif counts['collected']:
            tag = f"sec-universe-raw-{shard_day(now()).isoformat()}-shard{index}"
            print(upload_raw(raw_dir, tag=tag, token=token, open_response=open_upload))
        else:
            print('RAW_UPLOAD_SKIPPED no_collected_companies')
    return 0


def _kept_previous(payload, updates, codes):
    """Rows of `codes` whose published value (LIVE/STALE) is the previous file's row, not this run's. None if no file."""
    if payload is None:
        return None
    kept = 0
    for code in codes:
        row = payload['records'][code]
        if row['state'] == 'NOT_AVAILABLE':
            continue
        new = updates.get(code)
        if new is not None and row['acquired_at'] == new.get('acquired_at'):
            continue
        kept += 1
    return kept


def _count(value):
    return 'NA' if value is None else str(value)


def preserved_previous(payload, updates, codes):
    """Codes of `codes` whose published row carries a collection record of an earlier run, not this run's (kept over a
    failed collection, an unresolved symbol or a row without data). None if the file was not written."""
    if payload is None:
        return None
    kept = 0
    for code in codes:
        row = payload['records'].get(code)
        if row is None or row['acquired_at'] is None:
            continue
        new = updates.get(code)
        if new is not None and row['acquired_at'] == new.get('acquired_at'):
            continue
        kept += 1
    return kept


def collection_line(scope, *, issuers, collected, failed, unresolved, attempted, files, stats):
    """Owner decision 2026-10-17: new collections, failed collections and published rows kept from an earlier run are
    counted separately (a preserved row is never today's collection success). Counts only.

    preserved_previous_<file>: codes attempted by this run (its shards plus today's unresolved codes) whose published
    row is an earlier run's collection record. preserved_unconfirmed / identity_not_preserved: distinct codes the
    merges kept across a collection/identification failure, and codes whose earlier record of another identity was not
    carried (any of the three files)."""
    codes = set(attempted) | set(unresolved)
    union = lambda key: len(set().union(*(s.get(key, set()) for s in stats.values())))
    return (f"SEC_UNIVERSE_COLLECTION {scope} issuers={issuers} collected={collected} failed={failed} "
            f"unresolved_codes={len(unresolved)} "
            + ' '.join(f'preserved_previous_{name}={_count(preserved_previous(p, u, codes))}' for name, p, u in files)
            + f" preserved_unconfirmed={union('preserved')} identity_not_preserved={union('identity_not_preserved')}")


def withdrawal_line(scope, stats):
    """UNI-WITHDRAWN run log (owner decision 2026-10-17, #289 item 2): per file, codes withdrawn this run and live
    withdrawals that persist (re-checked by this run). The rows keep their first detected_at; nothing here is published."""
    count = lambda name, key: len(stats.get(name, {}).get(key, ()))
    return (f'SEC_UNIVERSE_WITHDRAWALS {scope} '
            + ' '.join(f'new_{name}={count(name, "withdrawn_new")} kept_{name}={count(name, "withdrawal_kept")}'
                       for name in ('shares', 'qg', 'qgv2')))


def _run_all_shards(out, *, cfg, environ, now, client_kwargs, token, open_upload, previous, previous_qg, previous_qgv2,
                    staged_target):
    """One-off: every shard 0..shard_count-1 in one run, one registry fetch, one paced client (serial requests)."""
    count = cfg['shard_count']
    try:
        registry, client = open_registry(user_agent=environ.get('SEC_USER_AGENT', ''), client_kwargs=client_kwargs)
    except SecCollectionError as error:
        code = error.args[0] if error.args and error.args[0] in {'SEC_USER_AGENT_INVALID', 'SEC_UNIVERSE_INPUT_INVALID',
            'SEC_UNIVERSE_CONFIG_INVALID', 'SEC_CONFIG_INVALID', 'SEC_HTTP_RETRIES_EXHAUSTED', 'SEC_TRANSPORT_RETRIES_EXHAUSTED'} else 'SEC_UNIVERSE_FAILED'
        print('SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN mode=all_shards code=' + code + (' previous_kept' if previous is not None else ''))
        return 0 if previous is not None else 1
    except Exception:
        print('SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN mode=all_shards code=SEC_UNIVERSE_FAILED' + (' previous_kept' if previous is not None else ''))
        return 0 if previous is not None else 1
    updates, unlisted_updates, qg_updates, qgv2_updates = {}, {}, {}, {}
    conflicts, transient = set(registry.conflicting_codes), set()
    stats = {'shares': {}, 'qg': {}, 'qgv2': {}}
    registry_sha = registry.source_sha256
    unresolved = set(universe_codes()) - {code for issuer in registry.issuers for code in issuer.codes}
    ok_shards, failed_shards, totals = [], [], {'companies': 0, 'collected': 0, 'failed': 0, 'covers': 0}
    partitions = {index: daily_partition(registry, shard_count=count, shard_index=index) for index in range(count)}
    shard_codes = {index: {code for issuer in issuers for code in issuer.codes} for index, issuers in partitions.items()}
    shard_report = {}
    day = shard_day(now()).isoformat()
    for index in range(count):
        s_updates, s_unlisted, s_qg, s_qgv2 = {}, {}, {}, {}
        with tempfile.TemporaryDirectory(prefix='sec-universe-raw-') as private:
            raw_dir = Path(private) / 'raw' if token else None
            try:
                s_updates, s_unlisted, _, _, _, counts = collect(
                    user_agent=environ.get('SEC_USER_AGENT', ''), now=now, raw_dir=raw_dir, config=cfg,
                    qg_updates=s_qg, qgv2_updates=s_qgv2, shard_index=index, registry=registry, client=client)
            except Exception:
                failed_shards.append(index)
                shard_report[index] = ('SHARD_FAILED', 0, len(partitions[index]))
                print(f'SEC_UNIVERSE_SHARD shard={index}/{count} status=SHARD_FAILED code=SEC_UNIVERSE_FAILED previous_kept')
                continue
            for company_index, code in counts['failures']:
                print(f'SEC_UNIVERSE_FAILURE shard={index} company_index={company_index} code={code}')
            for key in totals:
                totals[key] += counts[key]
            if counts['all_failed']:
                # Nothing of this shard is merged: every code of the shard keeps its previous published row.
                failed_shards.append(index)
                status = 'SHARD_ALL_FAILED previous_kept'
            else:
                ok_shards.append(index)
                conflicts |= counts['conflicts']
                transient |= counts['transient']
                updates.update(s_updates)
                unlisted_updates.update(s_unlisted)
                qg_updates.update(s_qg)
                qgv2_updates.update(s_qgv2)
                status = 'OK'
            shard_report[index] = (status.split()[0], counts['collected'], counts['failed'])
            v2_rows = list(s_qgv2.values())
            print(f"SEC_UNIVERSE_SHARD shard={index}/{count} companies={counts['companies']} collected={counts['collected']} "
                  f"failed={counts['failed']} covers={counts['covers']} share_codes={len(s_updates)} "
                  f"shares_with_value={sum(1 for r in s_updates.values() if r['shares'] is not None)} qg_codes={len(s_qg)} "
                  f"qg_scored_codes={sum(1 for r in s_qg.values() if r['state'] != 'NOT_AVAILABLE')} qgv2_codes={len(v2_rows)} "
                  f"qgv2_with_data={sum(1 for r in v2_rows if r['fiscal_year_end'] is not None)} status={status}")
            if token is None:
                print(f'RAW_UPLOAD_NOT_CONFIGURED shard={index}')
            elif counts['collected']:
                tag = f'sec-universe-raw-{day}-all-shard{index}'
                print(f'shard={index} ' + upload_raw(raw_dir, tag=tag, token=token, open_response=open_upload))
            else:
                print(f'RAW_UPLOAD_SKIPPED shard={index} no_collected_companies')
    last = max(ok_shards) if ok_shards else (previous or {}).get('last_shard_index')
    scope = (f"shard=all/{count} shards_ok={len(ok_shards)} shards_failed={len(failed_shards)}"
             + (' failed_shards=' + ','.join(str(i) for i in failed_shards) if failed_shards else ''))
    # The daily merges themselves (owner rule 2026-10-17): a collected code's new row replaces its kept row in every
    # file, also without data, so the same observation publishes the same row here and in a daily run.
    try:
        payload = merge(previous, updates, as_of=now(), shard_index=last, registry_sha256=registry_sha,
                        unresolved=unresolved, config=cfg, unlisted_updates=unlisted_updates, conflicts=conflicts,
                        stats=stats['shares'], transient=transient)
        write(out, payload)
    except Exception:
        print('SEC_UNIVERSE_SHARES OUTPUT_FAILED')
        return 1
    print(f"SEC_UNIVERSE_SHARES {scope} companies={totals['companies']} collected={totals['collected']} "
          f"failed={totals['failed']} covers={totals['covers']} unresolved_codes={len(unresolved)} {_summary(payload)}")
    try:
        last_qg = max(ok_shards) if ok_shards else (previous_qg or {}).get('last_shard_index')
        qg_payload = qg.merge(previous_qg, qg_updates, as_of=now(), shard_index=last_qg, registry_sha256=registry_sha,
                              unresolved=unresolved, config=cfg, conflicts=conflicts, stats=stats['qg'])
        write_qg(out, qg_payload)
    except Exception:
        print('SEC_UNIVERSE_QG OUTPUT_FAILED')
        return 1
    rows = list(qg_updates.values())
    print(f"SEC_UNIVERSE_QG {scope} codes={len(rows)} scored_codes={sum(1 for r in rows if r['state'] != 'NOT_AVAILABLE')} "
          f"{_qg_summary(qg_payload)}")
    qgv2_payload = None
    try:
        last_v2 = max(ok_shards) if ok_shards else (previous_qgv2 or {}).get('last_shard_index')
        qgv2_payload = qgv2.merge(previous_qgv2, qgv2_updates, as_of=now(), shard_index=last_v2, registry_sha256=registry_sha,
                                  unresolved=unresolved, config=cfg, target_updates=staged_target, conflicts=conflicts,
                                  stats=stats['qgv2'])
        write_qgv2(out, qgv2_payload)
        v2_rows = list(qgv2_updates.values())
        print(qgv2.summary_line(qgv2_payload, prefix=f"SEC_QGV2 {scope} codes={len(v2_rows)} "
                                f"with_data={sum(1 for r in v2_rows if r['fiscal_year_end'] is not None)}"))
    except Exception:
        qgv2_payload = None
        print('SEC_QGV2 OUTPUT_FAILED previous_kept')
    # A run can end with exit 0 while some shards failed: per shard and in total, how many issuers were collected and how
    # many published rows (LIVE/STALE) still come from the previous file instead of this run (owner, 2026-10-15 evening).
    files = (('shares', payload, updates), ('qg', qg_payload, qg_updates), ('qgv2', qgv2_payload, qgv2_updates))
    for index in range(count):
        status, collected, failed = shard_report[index]
        kept = [_kept_previous(p, u, shard_codes[index]) for _, p, u in files]
        print(f"SEC_UNIVERSE_SHARD_REPORT shard={index}/{count} status={status} issuers={len(partitions[index])} "
              f"issuers_collected={collected} issuers_failed={failed} "
              + ' '.join(f'kept_previous_{name}={_count(k)}' for (name, _, _), k in zip(files, kept)))
    kept = [_kept_previous(p, u, universe_codes()) for _, p, u in files]
    print(f"SEC_UNIVERSE_ALL_SHARDS shards_ok={len(ok_shards)} shards_failed={len(failed_shards)} "
          f"issuers={sum(len(i) for i in partitions.values())} issuers_collected={sum(r[1] for r in shard_report.values())} "
          f"issuers_failed={sum(r[2] for r in shard_report.values())} "
          f"kept_previous_rows={sum(k for k in kept if k is not None)} "
          + ' '.join(f'kept_previous_{name}={_count(k)}' for (name, _, _), k in zip(files, kept)))
    print(collection_line(f'shard=all/{count}', issuers=sum(len(i) for i in partitions.values()),
                          collected=totals['collected'], failed=totals['failed'], unresolved=unresolved,
                          attempted=set().union(*shard_codes.values()), files=files, stats=stats))
    print(withdrawal_line(f'shard=all/{count}', stats))
    if failed_shards:
        print('SEC_UNIVERSE_SHARES ALL_SHARDS_PARTIAL failed_shards=' + ','.join(str(i) for i in failed_shards) + ' previous_kept')
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--preserve-only', action='store_true')
    parser.add_argument('--all-shards', action='store_true',
                        help='one-off: collect every shard 0..shard_count-1 in this run (default: today\'s shard only)')
    args = parser.parse_args(argv)
    if args.all_shards:
        return run(args.out, live=args.live, preserve_only=args.preserve_only, all_shards=True)
    return run(args.out, live=args.live, preserve_only=args.preserve_only)


if __name__ == '__main__':
    raise SystemExit(main())
