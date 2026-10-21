#!/usr/bin/env python3
"""Restore only the audited 10/20 public JSON into a freshly built cockpit.

Restore uses one fixed source with no network, collection, scoring or ledger
generation. Check-deploy reads only live Pages and must run under the existing
deploy lock, after the strict SEC/ledger freshness guard and immediately before
deploy. The caller retains the existing Pages guard and browser tests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import time
import urllib.error
import urllib.request


REPOSITORY = 'kco994553-star/Investment-System1'
RUN_ID = 39522288311
ARTIFACT_ID = 12311543375
SOURCE_SHA = '8c671ae4859bc509be228ec59b4d923f1bb2af43'
SOURCE_BRANCH = 'claude/investment-system-top500-validation-alrugm'
ZIP_SHA256 = '16a0af04725323edc624bc0ce503ab3700224c38d7df55cd604a9e42b22d0826'
TAR_SHA256 = 'e1ba05bf5ff43d5bf76e46a4525884e6a886b2c86e33f1b82f7e2f8cfc7b5912'
LEDGER_SHA256 = '1f355c259277f855d961ad4b7d653bf2ab61bc46c2ad423f8ab638fc2b4eeb72'
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_METADATA_BYTES = 512 * 1024
MAX_ENTRIES = 192
DATA_FILES = (
    'actual-catalog.json', 'company-classification.json', 'company-logos.json',
    'company-names-ko.json', 'company-types-pricefree.json', 'dart-disclosures.json',
    'dart-financials.json', 'data.json', 'entities.json', 'forward-validation-ledger.json',
    'macro-evidence.json', 'macro-screen.json', 'news-signals.json', 'sec-13f-changes.json',
    'sec-disclosures.json', 'sec-filing-windows.json', 'sec-m2-candidates.json',
    'sec-public-inputs.json', 'sec-qg-factors.json', 'sec-qgv2.json', 'sec-universe-qg.json',
    'sec-universe-shares.json', 'sec-valuation-inputs.json', 'universe-codes.json',
    'universe-domains.json',
)


# Audited official baseline: run 39455397782, commit afb06868a97cc823580480566b9a4e998953f567,
# artifact 12283130828 ZIP SHA256 467f14440b8bbc70e11fb1dd971e7f0b9090b3969948b820872fcfff674e0822.
# Each pair is (audited baseline, fixed 10/20 source). Hashes only; no collected payloads.
DATA_HASHES = {
    'actual-catalog.json': (
        'fb10ebc8506de85ac7b210ead9a47d0f7fe69c69e4ba86f17bc3b3eea3b93b49',
        'fb10ebc8506de85ac7b210ead9a47d0f7fe69c69e4ba86f17bc3b3eea3b93b49'),
    'company-classification.json': (
        '431d024de2b497ba44119c9f7790d6e1a1c85280cd2bff039e7304a78d40a1ab',
        '872f7fd78bf5dd735dfcfd2209a6b079f62ab21a34ad53212f58e87641d4a391'),
    'company-logos.json': (
        '656cd7a076923ce2498c97b6775b481045125214333d11002ffee79bbe26da5d',
        '656cd7a076923ce2498c97b6775b481045125214333d11002ffee79bbe26da5d'),
    'company-names-ko.json': (
        '74489ef7d67073a1cea3d60d019581e91f79df8164c2ed29cdb566072a301e4b',
        '74489ef7d67073a1cea3d60d019581e91f79df8164c2ed29cdb566072a301e4b'),
    'company-types-pricefree.json': (
        '8301f28290a5201c0d790e732a1a18378f17f0a25f9284b680287a9efa556361',
        '52c4eb141c7614f47fc61fe328d8aa99743108be4be5c8b8ab383ce8b2649c5e'),
    'dart-disclosures.json': (
        '514d1514a14253b9b46ab61db4f8bbda7aac3816dd2a095a0f6141956faefbdc',
        '0d4ead442e3e04f90b94b7d81a64799bc394625f055c54bc9c697f90c94b87f4'),
    'dart-financials.json': (
        '5e87c9e1fcad9bff67660412595bfcc1d7f39a1461e8a882ad4ad4231ab1978c',
        'b4e954fb350a8884260f92be8d58594704fe969f171f8aaa3afb2bb35d499809'),
    'data.json': (
        'c3365b11e217760e2f3a008aaf660baade4494f01b5a255be3cfb6405a451cf9',
        'c3365b11e217760e2f3a008aaf660baade4494f01b5a255be3cfb6405a451cf9'),
    'entities.json': (
        'b085478e6f45797bed32fd9204dc9e8f72c9a452f621a4d3338b99c89ccdc78f',
        'b085478e6f45797bed32fd9204dc9e8f72c9a452f621a4d3338b99c89ccdc78f'),
    'forward-validation-ledger.json': (
        'ef4478d0be907d5f05e37094c41848ce542a54bcbeece3cccf43f8d55c526a5f',
        '1f355c259277f855d961ad4b7d653bf2ab61bc46c2ad423f8ab638fc2b4eeb72'),
    'macro-evidence.json': (
        'e6339afffdb795e5ca350900aadeefa2ae50ed570da8fb4df93d82ac574617a6',
        'e9a3869d7f4996fc211fe5b230c9eb0ae3b16bb37d1c31d41589ca06ea5d3e51'),
    'macro-screen.json': (
        '1a534529093895d2ecca6617504a396ad5a98ea7310a2a201e2fbc398f173758',
        'e936c295ddc76cf7de68b8608ec174b24f5bbb19eb408b60d7e80cea506e5618'),
    'news-signals.json': (
        'bbf6318e8a5420f4d3a64bbb1b00e83397b91ad56be2108e057442f7bc741102',
        'ddebde7a2d5c0dcbcf5f12f8f40e97ed7a2476e4d04a81a71ea771271e3b61ae'),
    'sec-13f-changes.json': (
        'f291873651ac7deaef9d0d70808c959fb2ee1a8a67c43ffba65a9e9740484988',
        'a698593a86db348e35a87d9399c2390057acb58e9ccbd3870e7e9263d65e4bdb'),
    'sec-disclosures.json': (
        '45b29def798b6960b09cd8edde562c9851916c3549d85d47086ed64e0f142b73',
        '374124876829cdaa4d1a0f9b8c5bf5bd8e8fda7244005ac4589ab4a937b1dd67'),
    'sec-filing-windows.json': (
        'fba6c6824e47b8c1e167a4c57138c36ee3abbc40ecec3719f4cc9fb14053f86c',
        'd5f7bb87e11df2d83fd1dbaa28c9f5d49bc2bd7d64b8198fa8a56bd43a336781'),
    'sec-m2-candidates.json': (
        '64108ed836970fbbe09e08624fbd92469ce49168d7d875530f156306ed32f649',
        '64108ed836970fbbe09e08624fbd92469ce49168d7d875530f156306ed32f649'),
    'sec-public-inputs.json': (
        '554a2487b869331acb4bf649ebad2a42910b90b8f367370dfc08898eaa98bb96',
        '08a4753e0f5eac1c721370b4d306bc88b9ec37f5b9b75e5f1f0f0051ae8ea57f'),
    'sec-qg-factors.json': (
        '9ae4031396e6449ef4f1518a09530cbbf468980d8497fa7b9dd5693bfe71e9f7',
        '6102d99a0bb69a9ed580496e0a4e787cece5be2d6dd291d2fdcefe9cff12288f'),
    'sec-qgv2.json': (
        '3802276b211a3955e46e9f8cb8183883392f6f8889d41896412353125d2d36e1',
        '322b3206d36df15305edf8bf459a715d02229822fcbef935c663c80e2b15a3bf'),
    'sec-universe-qg.json': (
        '7dfe79a502499e964a4fd9b2b5c3e8da2afdc749130c825520229c6e8e7c4585',
        '2efc5007a07002aae4431f076406825c62ed88729d422e336800b73f48ba4b37'),
    'sec-universe-shares.json': (
        '199f0fb169c6db09395db8ac077639851aed17cb9d9055ed992c955c57697e53',
        '65190b248eda82f129dcd76d6d69ebf337b232757834096185d85445e080df7b'),
    'sec-valuation-inputs.json': (
        'fe60a99b61179335bb97703ebf6b1eecbb96ea596c97244fa1865a35c405c314',
        'f1d6a305d84b0f7814f92ac23f85fe08e3dc674ca2346f397a7f5b78862a5d30'),
    'universe-codes.json': (
        'b4a06c40e702bfb376dc06973cffccb0ff636cd86935905a9cd7ce57f28bf45a',
        'b4a06c40e702bfb376dc06973cffccb0ff636cd86935905a9cd7ce57f28bf45a'),
    'universe-domains.json': (
        '0faa371bcb69c1ad73fed930713867dce1c1cc52a721c0c0462f2659e663bfd6',
        '33cb0add559efe23ec8d75c3df8419016b2c635bb11ed1d7dc9b09529bac9562'),
}

class ReplayError(ValueError):
    """Only fixed, value-free codes may reach the CLI log."""


def _json(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReplayError('JSON_INVALID')
            result[key] = value
        return result

    def invalid_constant(_value):
        raise ReplayError('JSON_INVALID')

    try:
        result = json.loads(body.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise ReplayError('JSON_INVALID') from None
    if not isinstance(result, dict):
        raise ReplayError('JSON_INVALID')
    return result


def _read(path, limit):
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            raise ReplayError('INPUT_INVALID')
        with path.open('rb') as handle:
            body = handle.read(limit + 1)
        if len(body) > limit:
            raise ReplayError('INPUT_INVALID')
        return body
    except OSError:
        raise ReplayError('INPUT_UNREADABLE') from None


def _matches(data, expected):
    return isinstance(data, dict) and all(data.get(key) == value for key, value in expected.items())


def verify_source(run, artifact, *, now=None):
    """Validate GET responses for the exact audited run and artifact; no API calls."""
    linked = {'id': RUN_ID, 'head_sha': SOURCE_SHA, 'head_branch': SOURCE_BRANCH}
    expected_run = {**linked, 'event': 'schedule', 'status': 'completed', 'conclusion': 'failure',
                    'path': '.github/workflows/sec-daily-public-inputs.yml'}
    expected_artifact = {'id': ARTIFACT_ID, 'name': 'github-pages', 'size_in_bytes': 1862217,
                         'digest': 'sha256:' + ZIP_SHA256}
    if not _matches(run, expected_run) or not _matches(artifact, expected_artifact):
        raise ReplayError('SOURCE_METADATA_INVALID')
    if not all(_matches(run.get(key), {'full_name': REPOSITORY}) for key in ('repository', 'head_repository')):
        raise ReplayError('SOURCE_METADATA_INVALID')
    if not _matches(artifact.get('workflow_run'), linked) or artifact.get('expired') is not False:
        raise ReplayError('SOURCE_METADATA_INVALID')
    try:
        expires = datetime.fromisoformat(artifact['expires_at'].replace('Z', '+00:00'))
        if expires.tzinfo is None:
            raise ValueError
        if expires <= (now or datetime.now(timezone.utc)):
            raise ReplayError('SOURCE_EXPIRED')
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        if isinstance(error, ReplayError):
            raise
        raise ReplayError('SOURCE_METADATA_INVALID') from None


def _data_from_tar(body):
    """Read a flat tar into memory. Never extract paths or old frontend code."""
    if hashlib.sha256(body).hexdigest() != TAR_SHA256:
        raise ReplayError('TAR_DIGEST_MISMATCH')
    selected, seen = {}, set()
    try:
        with tarfile.open(fileobj=io.BytesIO(body), mode='r:') as archive:
            for count, member in enumerate(archive, 1):
                if count > MAX_ENTRIES:
                    raise ReplayError('ARCHIVE_INVALID')
                if member.isdir() and member.name in ('.', './'):
                    continue
                name = member.name.removeprefix('./')
                if (not member.isreg() or member.issparse() or not name or name in ('.', '..')
                        or '/' in name or '\\' in name or name in seen
                        or member.size < 0 or member.size > MAX_FILE_BYTES):
                    raise ReplayError('ARCHIVE_INVALID')
                seen.add(name)
                if name in DATA_FILES:
                    with archive.extractfile(member) as handle:
                        data = handle.read(MAX_FILE_BYTES + 1)
                    if len(data) != member.size:
                        raise ReplayError('ARCHIVE_INVALID')
                    _json(data)
                    selected[name] = data
    except (tarfile.TarError, OSError, EOFError):
        raise ReplayError('ARCHIVE_INVALID') from None
    if set(selected) != set(DATA_FILES) or {name for name in seen if name.endswith('.json')} != set(DATA_FILES) | {'manifest.json'}:
        raise ReplayError('DATA_SET_MISMATCH')
    if hashlib.sha256(selected['forward-validation-ledger.json']).hexdigest() != LEDGER_SHA256:
        raise ReplayError('LEDGER_DIGEST_MISMATCH')
    return selected


def restore(archive, run_metadata, artifact_metadata, out, *, now=None):
    """All source/target validation precedes writes; only the 25 fixed JSON paths change."""
    verify_source(_json(_read(run_metadata, MAX_METADATA_BYTES)),
                  _json(_read(artifact_metadata, MAX_METADATA_BYTES)), now=now)
    data = _data_from_tar(_read(archive, MAX_ARCHIVE_BYTES))
    out = Path(out)
    if out.is_symlink() or not out.is_dir():
        raise ReplayError('OUTPUT_INVALID')
    for name in DATA_FILES:
        destination = out / name
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise ReplayError('OUTPUT_INVALID')
    try:
        # A write failure stops the workflow; no partially restored build is uploaded.
        with tempfile.TemporaryDirectory(prefix='.replay-20261020-', dir=out.parent) as temporary:
            stage = Path(temporary)
            for name, body in data.items():
                (stage / name).write_bytes(body)
            for name in DATA_FILES:
                (stage / name).replace(out / name)
            if any((out / name).read_bytes() != data[name] for name in DATA_FILES):
                raise ReplayError('OUTPUT_MISMATCH')
    except OSError:
        raise ReplayError('OUTPUT_FAILED') from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def check_deploy(out, *, open_response=None):
    """Fail closed on any unknown live data or changed candidate; never write data.

    Only the two audited byte sequences per file are accepted from live Pages.
    Even a harmless reserialization/new timestamp is unknown and stops recovery.
    Candidate bytes must all be the fixed 10/20 source, not the older baseline.
    """
    out = Path(out)
    if out.is_symlink() or not out.is_dir():
        raise ReplayError('OUTPUT_INVALID')
    if set(DATA_HASHES) != set(DATA_FILES):
        raise ReplayError('DATA_SET_MISMATCH')
    # Verify every candidate file before the first network read.
    for name in DATA_FILES:
        if hashlib.sha256(_read(out / name, MAX_FILE_BYTES)).hexdigest() != DATA_HASHES[name][1]:
            raise ReplayError('CANDIDATE_DATA_MISMATCH')
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    nonce = str(time.time_ns())
    for name in DATA_FILES:
        url = f'https://kco994553-star.github.io/Investment-System1/{name}?replay-check={nonce}'
        request = urllib.request.Request(url, headers={
            'Accept': 'application/json', 'Accept-Encoding': 'identity',
            'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache',
        })
        try:
            with fetch(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ReplayError('LIVE_FETCH_FAILED')
                body = response.read(MAX_FILE_BYTES + 1)
        except (urllib.error.URLError, OSError, ValueError):
            # Includes 404: recovery is never a first-publication exception.
            raise ReplayError('LIVE_FETCH_FAILED') from None
        if len(body) > MAX_FILE_BYTES or hashlib.sha256(body).hexdigest() not in DATA_HASHES[name]:
            raise ReplayError('LIVE_DATA_UNEXPECTED')


class SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, 'REPLAY_20261020_FAILED reason=ARGUMENTS_INVALID\n')


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--check-deploy', action='store_true')
    for name in ('archive', 'run-metadata', 'artifact-metadata', 'out'):
        parser.add_argument('--' + name, required=name == 'out', type=Path)
    args = parser.parse_args(argv)
    source_args = (args.archive, args.run_metadata, args.artifact_metadata)
    if (args.check_deploy and any(source_args)) or (not args.check_deploy and not all(source_args)):
        parser.error('invalid mode')
    try:
        if args.check_deploy:
            check_deploy(args.out)
        else:
            restore(*source_args, args.out)
    except ReplayError as error:
        print('REPLAY_20261020_FAILED reason=' + str(error))
        return 1
    except Exception:
        print('REPLAY_20261020_FAILED reason=UNEXPECTED_ERROR')
        return 1
    action = 'DEPLOY_CHECKED' if args.check_deploy else 'RESTORED'
    print(f'REPLAY_20261020_{action} files=25 source_run={RUN_ID} artifact={ARTIFACT_ID}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
