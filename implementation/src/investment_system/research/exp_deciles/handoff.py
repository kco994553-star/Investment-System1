"""Input and output manifests of EXP-STOCK-INDICATOR-DECILES-v1 private runs. New for this experiment (nothing ported).

Settings doc section 6.1: every handoff carries the run ID, the full code SHA, the settings, the reproduction command and a
private manifest of the inputs (location, source, period, sha256, rights). This module is pure: it takes bytes and dicts
and returns dicts and bytes. The CLI (implementation/tools/exp_stock_indicator_deciles.py) reads and writes the files.

Input manifest (JSON object, schema INPUT_MANIFEST_SCHEMA):
  {"schema": "exp-deciles-input-manifest/1", "experiment_id": "EXP-STOCK-INDICATOR-DECILES-v1",
   "resources": [{"name", "path", "sha256", "source", "period", "rights_note"}, ...]}
  - name = KIND or KIND:QUALIFIER (unique). KIND is one of RESOURCE_KINDS. records and quotes need a 4-digit year as
    the qualifier (records:2018). companyfacts:<digits> is one issuer's companyfacts (the qualifier is its CIK); any
    other qualifier is a free label of one part of a split bundle. tr_series appears at most once.
  - path: the file, relative to the manifest's directory or absolute; sha256: 64 lowercase hex of the file's bytes;
    source, period, rights_note: non-empty text. No other key is accepted.
  Every file is hashed before use and a mismatch is refused (MANIFEST_HASH_MISMATCH).

Output manifest (written last, schema OUTPUT_MANIFEST_SCHEMA): experiment_id, settings_sha256, code_sha (git HEAD of the
checkout, or 'UNKNOWN' with the flag CODE_SHA_UNKNOWN), code_sha_flags, input_manifest_sha256, the input resources,
extra_inputs (selection / previous U-A files with their sha256), stage, run_id, generated_at (UTC, injectable so a
replay is byte-identical) and the output files with their sha256 and size.

run_id = the first 24 hex characters of sha256(canonical JSON of {experiment_id, settings_sha256, code_sha,
input_manifest_sha256, stage}). stage is the stage name with its parameters (year and previous U-A hash for 'select';
selection hashes, end and daily_positions for 'ledger'), so two different runs of one manifest never share a run_id;
generated_at is not part of it.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import re

from . import settings

INPUT_MANIFEST_SCHEMA = 'exp-deciles-input-manifest/1'
OUTPUT_MANIFEST_SCHEMA = 'exp-deciles-output-manifest/1'
RESOURCE_KEYS = ('name', 'path', 'sha256', 'source', 'period', 'rights_note')
RESOURCE_KINDS = ('records', 'quotes', 'companyfacts', 'filings', 'prices', 'events', 'tr_series')
YEAR_KINDS = ('records', 'quotes')
SINGLE_KINDS = ('tr_series',)
STAGES = ('select', 'ledger')
CODE_SHA_UNKNOWN = 'UNKNOWN'
CODE_SHA_UNKNOWN_FLAG = 'CODE_SHA_UNKNOWN'
RUN_ID_HEX = 24
MANIFEST_FILE = 'manifest.json'

_HEX64 = re.compile(r'[0-9a-f]{64}')
_GIT_SHA = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_NAME = re.compile(r'([a-z_]+)(?::([A-Za-z0-9._-]{1,64}))?')
_FILE = re.compile(r'[a-z0-9_]{1,64}\.json')
_FLAG = re.compile(r'[A-Z][A-Z0-9_]{0,63}')
_YEAR = re.compile(r'[0-9]{4}')


class HandoffError(ValueError):
    """Refused manifest or output. The message is an UPPER_SNAKE reason code."""


def sha256_hex(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise HandoffError('BYTES_REQUIRED')
    return hashlib.sha256(bytes(data)).hexdigest()


def jsonable(value):
    """A JSON-ready copy: Decimal -> str, date -> ISO, dataclass -> dict, tuple/set -> list, keys -> str.
    Non-finite floats are refused (NON_FINITE_NUMBER)."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise HandoffError('NON_FINITE_NUMBER')
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise HandoffError('NON_FINITE_NUMBER')
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {_key(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(jsonable(v) for v in value)
    raise HandoffError('NOT_JSON_SERIALIZABLE')


def _key(key):
    if isinstance(key, str):
        return key
    if isinstance(key, (date, datetime)):
        return key.isoformat()
    if isinstance(key, (int, Decimal)) and not isinstance(key, bool):
        return str(key)
    raise HandoffError('NOT_JSON_SERIALIZABLE_KEY')


def canonical_bytes(value) -> bytes:
    """Sorted keys, compact separators, ASCII, one trailing newline: the exact bytes written and hashed."""
    return (json.dumps(jsonable(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('ascii')


def _text(value, code):
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise HandoffError(code)
    return value


def resource_kind(name):
    """(kind, qualifier | None) of a resource name; HandoffError('MANIFEST_RESOURCE_NAME_INVALID') otherwise."""
    match = _NAME.fullmatch(name) if isinstance(name, str) else None
    if match is None or match.group(1) not in RESOURCE_KINDS:
        raise HandoffError('MANIFEST_RESOURCE_NAME_INVALID')
    kind, qualifier = match.group(1), match.group(2)
    if kind in YEAR_KINDS and (qualifier is None or not _YEAR.fullmatch(qualifier)):
        raise HandoffError('MANIFEST_RESOURCE_NAME_INVALID')
    if kind in SINGLE_KINDS and qualifier is not None:
        raise HandoffError('MANIFEST_RESOURCE_NAME_INVALID')
    return kind, qualifier


def parse_input_manifest(data: bytes) -> dict:
    """Validated input manifest {'schema', 'experiment_id', 'resources', 'sha256'} from the manifest file's bytes."""
    digest = sha256_hex(data)
    try:
        raw = json.loads(bytes(data).decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise HandoffError('MANIFEST_NOT_JSON') from None
    if not isinstance(raw, dict) or set(raw) != {'schema', 'experiment_id', 'resources'}:
        raise HandoffError('MANIFEST_KEYS_INVALID')
    if raw['schema'] != INPUT_MANIFEST_SCHEMA:
        raise HandoffError('MANIFEST_SCHEMA_INVALID')
    if raw['experiment_id'] != settings.EXPERIMENT_ID:
        raise HandoffError('MANIFEST_EXPERIMENT_MISMATCH')
    if not isinstance(raw['resources'], list) or not raw['resources']:
        raise HandoffError('MANIFEST_RESOURCES_INVALID')
    resources, names = [], set()
    singles = set()
    for item in raw['resources']:
        if not isinstance(item, dict) or set(item) != set(RESOURCE_KEYS):
            raise HandoffError('MANIFEST_RESOURCE_KEYS_INVALID')
        kind, qualifier = resource_kind(item['name'])
        if item['name'] in names:
            raise HandoffError('MANIFEST_RESOURCE_DUPLICATE')
        names.add(item['name'])
        if kind in SINGLE_KINDS:
            if kind in singles:
                raise HandoffError('MANIFEST_RESOURCE_DUPLICATE')
            singles.add(kind)
        if not isinstance(item['sha256'], str) or not _HEX64.fullmatch(item['sha256']):
            raise HandoffError('MANIFEST_SHA256_INVALID')
        for key in ('path', 'source', 'period', 'rights_note'):
            _text(item[key], f'MANIFEST_{key.upper()}_INVALID')
        resources.append({key: item[key] for key in RESOURCE_KEYS})
    return {'schema': INPUT_MANIFEST_SCHEMA, 'experiment_id': raw['experiment_id'], 'resources': resources,
            'sha256': digest}


def resources_of(manifest, kind, qualifier=None):
    """Resources of one kind (and qualifier when given), in manifest order."""
    out = []
    for item in manifest['resources']:
        k, q = resource_kind(item['name'])
        if k == kind and (qualifier is None or q == qualifier):
            out.append(item)
    return out


def verify_resource(resource, data: bytes) -> None:
    """Refuse bytes whose sha256 differs from the manifest entry."""
    if sha256_hex(data) != resource['sha256']:
        raise HandoffError('MANIFEST_HASH_MISMATCH')


def code_sha_record(value):
    """(code_sha, flags): a 40/64-hex git object name, else 'UNKNOWN' with CODE_SHA_UNKNOWN."""
    if isinstance(value, str) and _GIT_SHA.fullmatch(value.strip()):
        return value.strip(), []
    return CODE_SHA_UNKNOWN, [CODE_SHA_UNKNOWN_FLAG]


def generated_at_text(value) -> str:
    """UTC 'YYYY-MM-DDTHH:MM:SSZ' from an aware datetime or an ISO text with an offset (sub-seconds dropped)."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError:
            raise HandoffError('GENERATED_AT_INVALID') from None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise HandoffError('GENERATED_AT_INVALID')
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')


def _stage(stage):
    if not isinstance(stage, dict) or stage.get('name') not in STAGES:
        raise HandoffError('STAGE_INVALID')
    return jsonable(stage)


def run_id(*, experiment_id, settings_sha256, code_sha, input_manifest_sha256, stage) -> str:
    body = {'experiment_id': experiment_id, 'settings_sha256': settings_sha256, 'code_sha': code_sha,
            'input_manifest_sha256': input_manifest_sha256, 'stage': _stage(stage)}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()[:RUN_ID_HEX]


def run_metadata(*, input_manifest, code_sha, stage, generated_at, extra_inputs=(), code_flags=()):
    """The 'run' block every output payload carries (and the output manifest repeats). code_flags: extra UPPER_SNAKE
    flags about the code state (e.g. CODE_TREE_DIRTY from the CLI)."""
    sha, flags = code_sha_record(code_sha)
    flags = flags + [flag(code) for code in code_flags if code not in flags]
    stage = _stage(stage)
    extras = []
    for item in extra_inputs:
        if not isinstance(item, dict) or set(item) != {'role', 'sha256'} or not _HEX64.fullmatch(str(item['sha256'])):
            raise HandoffError('EXTRA_INPUT_INVALID')
        extras.append({'role': _text(item['role'], 'EXTRA_INPUT_INVALID'), 'sha256': item['sha256']})
    settings_sha = settings.settings_sha256()
    return {'experiment_id': settings.EXPERIMENT_ID, 'settings_sha256': settings_sha, 'code_sha': sha,
            'code_sha_flags': flags, 'input_manifest_sha256': input_manifest['sha256'],
            'run_id': run_id(experiment_id=settings.EXPERIMENT_ID, settings_sha256=settings_sha, code_sha=sha,
                             input_manifest_sha256=input_manifest['sha256'], stage=stage),
            'stage': stage, 'generated_at': generated_at_text(generated_at), 'extra_inputs': extras}


def build_output_manifest(run, input_manifest, outputs) -> dict:
    """Output manifest for the run block `run` and output files {file name: bytes} (manifest.json itself excluded)."""
    if not isinstance(outputs, dict) or not outputs:
        raise HandoffError('OUTPUTS_REQUIRED')
    files = []
    for name in sorted(outputs):
        if not isinstance(name, str) or not _FILE.fullmatch(name) or name == MANIFEST_FILE:
            raise HandoffError('OUTPUT_NAME_INVALID')
        data = outputs[name]
        files.append({'file': name, 'sha256': sha256_hex(data), 'bytes': len(data)})
    if run.get('input_manifest_sha256') != input_manifest['sha256']:
        raise HandoffError('RUN_INPUT_MANIFEST_MISMATCH')
    return {'schema': OUTPUT_MANIFEST_SCHEMA, 'experiment_id': run['experiment_id'],
            'settings_sha256': run['settings_sha256'], 'code_sha': run['code_sha'],
            'code_sha_flags': list(run['code_sha_flags']), 'input_manifest_sha256': run['input_manifest_sha256'],
            'inputs': [dict(item) for item in input_manifest['resources']],
            'extra_inputs': [dict(item) for item in run['extra_inputs']], 'stage': run['stage'],
            'run_id': run['run_id'], 'generated_at': run['generated_at'], 'outputs': files}


def verify_output_manifest(manifest, files) -> dict:
    """Re-hash a run directory. files = {file name: bytes} of every regular file in it except manifest.json.

    Returns {'ok', 'run_id', 'run_id_ok', 'files': [{'file', 'status' OK | HASH_MISMATCH | MISSING | UNLISTED}],
    'counts': {status: n}}."""
    if not isinstance(manifest, dict) or manifest.get('schema') != OUTPUT_MANIFEST_SCHEMA:
        raise HandoffError('OUTPUT_MANIFEST_SCHEMA_INVALID')
    expected = run_id(experiment_id=manifest.get('experiment_id'), settings_sha256=manifest.get('settings_sha256'),
                      code_sha=manifest.get('code_sha'), input_manifest_sha256=manifest.get('input_manifest_sha256'),
                      stage=manifest.get('stage'))
    rows, listed = [], set()
    for item in manifest.get('outputs') or []:
        name = item.get('file') if isinstance(item, dict) else None
        if not isinstance(name, str) or not _FILE.fullmatch(name) or name in listed:
            raise HandoffError('OUTPUT_MANIFEST_FILES_INVALID')
        listed.add(name)
        data = files.get(name)
        if data is None:
            status = 'MISSING'
        elif sha256_hex(data) != item.get('sha256') or len(data) != item.get('bytes'):
            status = 'HASH_MISMATCH'
        else:
            status = 'OK'
        rows.append({'file': name, 'status': status})
    for name in sorted(set(files) - listed):
        rows.append({'file': name, 'status': 'UNLISTED'})
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    run_ok = manifest.get('run_id') == expected
    return {'ok': run_ok and bool(rows) and all(r['status'] == 'OK' for r in rows), 'run_id': manifest.get('run_id'),
            'run_id_ok': run_ok, 'files': rows, 'counts': counts}


def flag(code):
    """Validate an UPPER_SNAKE flag."""
    if not isinstance(code, str) or not _FLAG.fullmatch(code):
        raise HandoffError('FLAG_INVALID')
    return code
