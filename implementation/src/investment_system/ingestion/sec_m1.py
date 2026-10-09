"""Immutable SEC M1 custody receipts; no network, scoring or publication.

Custody verification proves byte integrity, not first-publication timestamps or
Full PIT historical coverage. Old RawDatasetStore replay remains separate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from ..markets.us import US_LISTINGS
from ..providers.sec_companyfacts import SEC_FACTS_URL
from ..providers.sec_submissions import URL as SUBMISSIONS_URL
from ..providers.sec_m1 import build_input
from .raw_store import RawDatasetStore

CONTRACT = 'SEC_M1_RETENTION'
VERSION = 1
CORE = ('contract', 'version', 'input', 'inputs')
KINDS = {'companyfacts': ('SEC_M1_COMPANYFACTS', SEC_FACTS_URL),
         'submissions': ('SEC_M1_SUBMISSIONS', SUBMISSIONS_URL)}


def _encoded(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value: dict) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _company(company_id: str) -> str:
    if company_id not in US_LISTINGS:
        raise ValueError('M1 requires an approved US17 company')
    return US_LISTINGS[company_id]['cik']


def _descriptor(company_id: str, kind: str, body: bytes) -> dict:
    cik = _company(company_id)
    sha = hashlib.sha256(body).hexdigest()
    source_kind, template = KINDS[kind]
    return {'artifact_id': f'sec_m1_{kind}:{cik}:{sha}', 'sha256': sha,
            'bytes': len(body), 'source_kind': source_kind,
            'source_url': template.format(cik=cik)}


def _verify_snapshot(store: RawDatasetStore, descriptor: dict) -> bytes:
    try:
        if (not isinstance(descriptor, dict)
                or not isinstance(descriptor.get('artifact_id'), str)
                or not re.fullmatch(r'sec_m1_(companyfacts|submissions):[0-9]{10}:[0-9a-f]{64}',
                                    descriptor['artifact_id'])
                or not isinstance(descriptor.get('sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', descriptor['sha256'])
                or type(descriptor.get('bytes')) is not int or descriptor['bytes'] < 0
                or not isinstance(descriptor.get('source_kind'), str)
                or not isinstance(descriptor.get('source_url'), str)):
            raise ValueError('invalid snapshot binding')
        body = store.get_bytes(descriptor['artifact_id'])
        manifest = store.get_manifest(descriptor['artifact_id'])
        for key in ('artifact_id', 'sha256', 'bytes', 'source_kind', 'source_url'):
            if manifest[key] != descriptor[key]:
                raise ValueError('manifest does not match receipt')
        if len(body) != descriptor['bytes'] or hashlib.sha256(body).hexdigest() != descriptor['sha256']:
            raise ValueError('blob does not match receipt')
        return body
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('SEC M1 snapshot integrity failure') from exc


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            tmp = Path(handle.name)
            handle.write(_encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def load_receipt(root: Path | str, receipt_id: str) -> dict:
    if not isinstance(receipt_id, str) or not re.fullmatch(r'[0-9a-f]{64}', receipt_id):
        raise ValueError('SEC M1 receipt integrity failure: invalid ID')
    root = Path(root)
    try:
        receipt = json.loads((root / 'm1' / 'receipts' / f'{receipt_id}.json').read_bytes())
        if not isinstance(receipt, dict):
            raise ValueError('receipt must be an object')
        if not isinstance(receipt.get('input'), dict) or not isinstance(receipt.get('inputs'), dict):
            raise ValueError('receipt input bindings must be objects')
        content = {k: v for k, v in receipt.items() if k != 'receipt_sha256'}
        core = {k: receipt[k] for k in CORE}
        if (receipt['contract'] != CONTRACT or receipt['version'] != VERSION
                or receipt['receipt_id'] != receipt_id or _digest(core) != receipt_id
                or _digest(content) != receipt['receipt_sha256']):
            raise ValueError('receipt digest mismatch')
        company_id = receipt['input']['company_id']
        cik = _company(company_id)
        if receipt['input']['cik'] != cik or set(receipt['inputs']) != set(KINDS):
            raise ValueError('receipt issuer mismatch')
        store = RawDatasetStore(root)
        for kind, descriptor in receipt['inputs'].items():
            if not isinstance(descriptor, dict):
                raise ValueError('snapshot descriptor must be an object')
            body = _verify_snapshot(store, descriptor)
            if _descriptor(company_id, kind, body) != descriptor:
                raise ValueError('receipt snapshot identity mismatch')
        return receipt
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('SEC M1 receipt integrity failure') from exc


def load_latest(root: Path | str, company_id: str) -> dict:
    _company(company_id)
    path = Path(root) / 'm1' / 'latest' / f'{company_id}.json'
    if not path.exists():
        raise FileNotFoundError('No READY SEC M1 receipt')
    try:
        pointer = json.loads(path.read_bytes())
        receipt = load_receipt(root, pointer['receipt_id'])
        if (pointer['company_id'] != company_id or receipt['input']['company_id'] != company_id
                or receipt['input']['status'] != 'READY'):
            raise ValueError('pointer issuer/status mismatch')
        return receipt
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError('SEC M1 pointer integrity failure') from exc


def _changes(previous: dict | None, current: dict) -> list[dict]:
    def rows(value):
        return {tuple(r.get(k) for k in ('taxonomy', 'concept', 'unit', 'start', 'end')): r
                for r in value.get('selected_input_facts', [])}
    old = rows(previous['input']) if previous else {}
    new = rows(current)
    changes = []
    for key in sorted(set(old) | set(new), key=repr):
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        changes.append({'identity': list(key), 'before': before, 'after': after,
                        'formal_amendment': bool(after and str(after.get('form', '')).endswith('/A')),
                        'parent_accession': None})
    return changes


def retain_input(root: Path | str, company_id: str, companyfacts_body: bytes,
                 submissions_body: bytes, acquired_at: datetime, as_of: datetime,
                 *, form_filter: str = '10-K') -> dict:
    _company(company_id)
    parsed = build_input(company_id, json.loads(companyfacts_body), json.loads(submissions_body),
                         acquired_at, as_of, form_filter=form_filter)
    bindings = {kind: _descriptor(company_id, kind, body) for kind, body in
                (('companyfacts', companyfacts_body), ('submissions', submissions_body))}
    core = {'contract': CONTRACT, 'version': VERSION, 'input': parsed, 'inputs': bindings}
    receipt_id = _digest(core)
    root = Path(root)
    folder = root / 'm1'
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / f'{company_id}.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        previous = load_latest(root, company_id) if (folder / 'latest' / f'{company_id}.json').exists() else None
        current = previous is None or (
            acquired_at >= datetime.fromisoformat(previous['input']['acquired_at'])
            and as_of >= datetime.fromisoformat(previous['input']['as_of']))
        parent = previous if current else None
        path = folder / 'receipts' / f'{receipt_id}.json'
        if path.exists():
            receipt = load_receipt(root, receipt_id)
        else:
            store = RawDatasetStore(root)
            for kind, body in (('companyfacts', companyfacts_body), ('submissions', submissions_body)):
                desc = bindings[kind]
                # Never refresh a content-addressed snapshot. Partial/corrupt
                # leftovers fail closed rather than overwrite custody evidence.
                if not store.has(desc['artifact_id']) and not store._manifest_path(desc['artifact_id']).exists():
                    store.put(desc['artifact_id'], body, desc['source_url'], desc['source_kind'],
                              'application/json', 'SEC M1 custody v1',
                              notes='Supplied SEC bytes; acquisition bound is separately recorded, not first publication.')
                _verify_snapshot(store, desc)
            changed = parent and any(parent['inputs'][k]['sha256'] != bindings[k]['sha256'] for k in KINDS)
            receipt = {**core, 'receipt_id': receipt_id,
                       'revision_parent_receipt_id': parent['receipt_id'] if parent else None,
                       'change_kind': 'UNAVAILABLE_ATTEMPT' if parsed['status'] != 'READY' else
                           'INITIAL' if parent is None else 'PAYLOAD_REVISION' if changed else 'CUTOFF_OR_OBSERVATION',
                       'changes': _changes(parent, parsed), 'real_data_verified': False,
                       'full_pit_historical': False}
            receipt['receipt_sha256'] = _digest(receipt)
            _atomic_json(path, receipt)
            load_receipt(root, receipt_id)
        if parsed['status'] == 'READY' and current:
            _atomic_json(folder / 'latest' / f'{company_id}.json',
                         {'company_id': company_id, 'receipt_id': receipt_id})
        return receipt
    finally:
        lock.unlink(missing_ok=True)


def replay_receipt(root: Path | str, receipt_id: str, as_of: datetime) -> dict:
    receipt = load_receipt(root, receipt_id)
    store = RawDatasetStore(root)
    payloads = {kind: json.loads(_verify_snapshot(store, descriptor))
                for kind, descriptor in receipt['inputs'].items()}
    original = receipt['input']
    return build_input(original['company_id'], payloads['companyfacts'], payloads['submissions'],
                       datetime.fromisoformat(original['acquired_at']), as_of,
                       form_filter=original.get('form_filter', '10-K'))
