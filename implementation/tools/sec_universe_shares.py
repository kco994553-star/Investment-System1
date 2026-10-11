#!/usr/bin/env python3
"""Daily Universe504 SEC shard -> public price-free `sec-universe-shares.json` + `sec-universe-qg.json`.

User decision 2026-10-11 (M3 shares option a). One shard per UTC day (day
ordinal mod the fixed v0 shard count) is collected through the paced SEC
client and merged into the previously published Pages copy, so every code keeps
its last value with its own acquired_at; rows past the v0 stale window are
STALE. Raw SEC bytes never reach Pages. If RAW_REPO_TOKEN is set they are
uploaded as a dated private release asset; otherwise RAW_UPLOAD_NOT_CONFIGURED.
Only fixed codes and counts are printed: no names, values, URLs or secrets.

User queue 2.1: the SAME fetched companyfacts/submissions bytes also produce the
price-free Q·G factor scores (`sec-universe-qg.json`, the TARGET sec-qg-factors path)
in-process: no extra SEC request. That file merges with its own previous Pages copy
by the same rules; the shares output format is unchanged.
"""
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
    FILENAME, MAX_BYTES, build_issuer_records, encode, load_config, merge, parse_json, require_universe_shares,
    select_cover_filing, shard_index_for, universe_codes, upgrade_legacy,
)
from investment_system.universe import sec_universe_qg as qg

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + FILENAME
QG_SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + qg.FILENAME
RAW_REPO = 'kco994553-star/investment-system1-raw'
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


def collect(*, user_agent, now=_utc_now, client_kwargs=None, raw_dir=None, config=None, qg_updates=None):
    """Collect today's shard. Returns (updates, unlisted_updates, unresolved_codes, registry_sha256, shard_index, counts).

    With `qg_updates` (a dict), the same fetched bytes also fill that dict with this shard's Q·G rows (no extra request)."""
    cfg = config or load_config()
    kwargs = dict(client_kwargs or {})
    started = now()
    index = shard_index_for(started.astimezone(timezone.utc).date(), cfg['shard_count'])
    base = SecCollectionClient(user_agent, **kwargs)
    registry = universe_registry(fetch_ticker_exchange(base))
    issuers = daily_partition(registry, shard_count=cfg['shard_count'], shard_index=index)
    client = UniverseSecClient(user_agent, registry=registry, **kwargs)
    bound = {code for issuer in registry.issuers for code in issuer.codes}
    unresolved = set(universe_codes()) - bound
    updates, unlisted_updates, manifest, covers = {}, {}, [], [0]

    def save(issuer, facts, submissions, acquired):
        if qg_updates is not None:
            # Same bytes, same issuer binding. A Q·G failure never reaches the shares path below.
            try:
                rows = qg.build_issuer_records(codes=issuer.codes, cik=issuer.cik, companyfacts_body=facts,
                                               submissions_body=submissions, acquired_at=acquired)
            except Exception:
                rows = {code: qg.empty_record(cik=issuer.cik, reasons=('INVALID_INPUT',)) for code in issuer.codes}
            qg_updates.update(rows)
        filing = select_cover_filing(submissions, acquired)
        cover = cover_at = None
        if filing is not None:
            try:
                cover, cover_at = client.collect_cover(issuer.cik, filing['accession'], filing['primary_document'])
                covers[0] += 1
            except Exception:
                cover = cover_at = None
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
    if raw_dir is not None:
        (Path(raw_dir) / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'role': 'PRIVATE_RAW_SEC_BYTES',
            'shard_count': cfg['shard_count'], 'shard_index': index, 'registry_sha256': registry.source_sha256,
            'companies': manifest}, sort_keys=True))
    counts = {'companies': len(issuers), 'collected': result.collected, 'failed': result.failed, 'covers': covers[0],
              'failures': result.failures, 'unresolved_codes': len(unresolved), 'all_failed': result.all_failed}
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
            f"single_class={count('share_class_basis', 'SINGLE_CLASS_CONFIRMED')} share_class_basis={count('share_class_basis', 'SHARE_CLASS_BASIS')} "
            f"basis_unconfirmed={count('share_class_basis', 'BASIS_UNCONFIRMED')}")


def _qg_summary(payload):
    rows = payload['records'].values()
    count = lambda value: sum(1 for r in rows if r['state'] == value)
    scored = sum(1 for r in rows for score in r['factors'].values() if score is not None)
    return f"live={count('LIVE')} stale={count('STALE')} not_available={count('NOT_AVAILABLE')} factor_scores={scored}"


def run(out, *, live, preserve_only=False, environ=None, now=_utc_now, client_kwargs=None,
        open_previous=None, open_upload=None):
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
    if preserve_only:
        return 0
    if not live:
        print('SEC_UNIVERSE_SHARES LIVE_OPT_IN_REQUIRED')
        return 1
    token = environ.get(RAW_TOKEN_ENV) or None
    with tempfile.TemporaryDirectory(prefix='sec-universe-raw-') as private:
        raw_dir = Path(private) / 'raw' if token else None
        qg_updates = {}
        try:
            updates, unlisted_updates, unresolved, registry_sha, index, counts = collect(
                user_agent=environ.get('SEC_USER_AGENT', ''), now=now, client_kwargs=client_kwargs, raw_dir=raw_dir, config=cfg,
                qg_updates=qg_updates)
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
                            unresolved=unresolved, config=cfg, unlisted_updates=unlisted_updates)
            write(out, payload)
        except Exception:
            print('SEC_UNIVERSE_SHARES OUTPUT_FAILED')
            return 1
        print(f"SEC_UNIVERSE_SHARES shard={index}/{cfg['shard_count']} companies={counts['companies']} "
              f"collected={counts['collected']} failed={counts['failed']} covers={counts['covers']} "
              f"unresolved_codes={counts['unresolved_codes']} {_summary(payload)}")
        try:
            qg_payload = qg.merge(previous_qg, qg_updates, as_of=now(), shard_index=index, registry_sha256=registry_sha,
                                  unresolved=unresolved, config=cfg)
            write_qg(out, qg_payload)
        except Exception:
            print('SEC_UNIVERSE_QG OUTPUT_FAILED')
            return 1
        shard_rows = [qg_updates[code] for code in sorted(qg_updates)]
        print(f"SEC_UNIVERSE_QG shard={index}/{cfg['shard_count']} codes={len(shard_rows)} "
              f"scored_codes={sum(1 for r in shard_rows if r['state'] != 'NOT_AVAILABLE')} {_qg_summary(qg_payload)}")
        if counts['all_failed']:
            print('SEC_UNIVERSE_SHARES SHARD_ALL_FAILED previous_kept')
        if token is None:
            print('RAW_UPLOAD_NOT_CONFIGURED')
        elif counts['collected']:
            tag = f"sec-universe-raw-{now().astimezone(timezone.utc).date().isoformat()}-shard{index}"
            print(upload_raw(raw_dir, tag=tag, token=token, open_response=open_upload))
        else:
            print('RAW_UPLOAD_SKIPPED no_collected_companies')
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--preserve-only', action='store_true')
    args = parser.parse_args(argv)
    return run(args.out, live=args.live, preserve_only=args.preserve_only)


if __name__ == '__main__':
    raise SystemExit(main())
