"""Offline RAW monthly gzip journal and bounded chart projection.

No collection, indicator/scoring engine, adjustment, Worker or publication code.
Only new/reviewed-revised provider rows enter the journal. Response bodies are
verified in RAM and discarded; their hashes and original receipts are retained.
"""
from copy import deepcopy
from datetime import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from ._private_artifacts import canonical_bytes, digest, json_bytes, MAX_BYTES
from .kis_price_bridge import normalize_page, validate_contract, _ts

SCHEMA = 'retained-month-store/1'
SCOPE = 'OWNER_PRIVATE_ONLY'
_EVIDENCE = ('security_id', 'issuer_id', 'identity', 'currency_reference',
             'splits', 'confirmed_ranges', 'held_ranges', 'session_scope',
             'price_scope_status', 'volume_basis', 'amount_basis')


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _path(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    _need(p.is_relative_to(root) and p != root, 'STORE_PATH_ESCAPE')
    return p


def _bounded(value, reason):
    b = json_bytes(value)
    _need(len(b) <= MAX_BYTES, reason)
    return b


def _atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()
    _sync_directory(path.parent)


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _immutable(path, value):
    if path.exists():
        _need(path.read_bytes() == value, 'IMMUTABLE_FILE_MISMATCH')
    else:
        _atomic(path, value)


def _check_manifest(m):
    _need(m.get('schema') == SCHEMA and m.get('publication_scope') == SCOPE,
          'STORE_SCHEMA_OR_SCOPE')
    _need(m.get('manifest_sha256') == digest({k: v for k, v in m.items()
                                            if k != 'manifest_sha256'}), 'MANIFEST_HASH')


def load_manifest(root, series_id):
    _need(isinstance(series_id, str) and re.fullmatch('[0-9a-f]{64}', series_id), 'SERIES_ID')
    pointer = json.loads(_path(root, f'series/{series_id}/latest.json').read_bytes())
    b = _path(root, pointer['path']).read_bytes()
    _need(_sha(b) == pointer['sha256'] and len(b) == pointer['bytes'], 'MANIFEST_POINTER_HASH')
    m = json.loads(b)
    _check_manifest(m)
    _need(m['series_id'] == series_id, 'MANIFEST_SERIES_MISMATCH')
    return m


def read_records(root, manifest):
    """Read only the committed prefix; old manifest versions remain replayable."""
    _check_manifest(manifest)
    result = []
    for month, item in sorted(manifest['months'].items()):
        _need(re.fullmatch(r'\d{4}-\d{2}', month) is not None, 'MONTH_KEY')
        expected = f"series/{manifest['series_id']}/months/{month}.jsonl.gz"
        _need(item['path'] == expected, 'MONTH_PATH')
        with _path(root, item['path']).open('rb') as f:
            b = f.read(item['bytes'])
        _need(len(b) == item['bytes'] and _sha(b) == item['sha256'], 'MONTH_HASH')
        rows = [json.loads(line) for line in gzip.decompress(b).splitlines()]
        _need(len(rows) == item['records'] and all(r['date'][:7] == month for r in rows),
              'MONTH_RECORD_MISMATCH')
        result.extend(rows)
    return result


def _latest(records):
    result = {}
    for r in records:
        prior = result.get(r['date'])
        _need(r.get('supersedes') == (digest(prior) if prior else None), 'REVISION_CHAIN')
        result[r['date']] = r
    return result


def retained_metadata(root, manifest):
    """Receipt/header metadata, checked against the independently pinned manifest."""
    _check_manifest(manifest)
    item = manifest['receipt']
    b = _path(root, item['path']).read_bytes()
    _need(_sha(b) == item['sha256'] and len(b) == item['bytes'], 'RECEIPT_ARCHIVE_HASH')
    return json.loads(gzip.decompress(b))


def retained_contract(root, manifest):
    """Reconstitute input values; never claim original JSON whitespace/key order."""
    records = _latest(read_records(root, manifest))
    meta = retained_metadata(root, manifest)
    c = deepcopy(meta['contract_header'])
    raw = [r['bar'] for _, r in sorted(records.items()) if r['bar'] is not None]
    c.update(raw_bars=deepcopy(raw), bars=deepcopy(raw),
             price_basis_date=raw[-1]['date'] if raw else None)
    validate_contract(c)
    return c


def query_contract(root, manifest):
    c = retained_contract(root, manifest)
    # The latest source hash identifies that response only. Each older row retains
    # its own original source hash/time; history_store pins the combined journal.
    c['history_store'] = dict(schema=SCHEMA, manifest_sha256=manifest['manifest_sha256'],
                              original_response_bodies_retained=False,
                              source_hash_scope='LATEST_RESPONSE_HEADER_AND_PER_ROW_ORIGINALS',
                              revision_count=manifest['revision_count'],
                              latest_response_rows=manifest['latest_response_rows'],
                              latest_response_state=manifest['latest_response_state'])
    c['display'] = dict(state='WITHHELD', hold_reasons=['SAVED_DISPLAY_REVIEW_REQUIRED'],
                        validation_tier='UNVERIFIED_REFERENCE', label='검증 전(참고)', official=False)
    validate_contract(c)
    return c


def project_query(contract, *, saved_chart_bytes=None, expected_saved_chart_sha256=None):
    """Reuse a pinned saved display decision only for exactly the same input.

    A storage operation must not drop a previous hold or rerun its split screen.
    Without the matching saved decision the raw query remains explicitly held.
    """
    c = deepcopy(contract)
    _need((saved_chart_bytes is None) == (expected_saved_chart_sha256 is None),
          'SAVED_CHART_AND_PIN_REQUIRED')
    if saved_chart_bytes is not None:
        _need(_sha(saved_chart_bytes) == expected_saved_chart_sha256, 'SAVED_CHART_PIN')
        saved = json.loads(saved_chart_bytes)
        keys = ('schema', 'symbol', 'security_id', 'issuer_id', 'exchange', 'currency',
                'basis', 'dividend_adjustment', 'price_basis_date', 'source_sha256',
                'collected_at', 'source_query', 'identity', 'raw_bars', 'bars',
                'splits', 'held_ranges', 'confirmed_ranges', 'timestamp_basis', 'publication_scope',
                'currency_reference', 'session_scope', 'price_scope_status', 'volume_basis',
                'amount_basis', 'calendar', 'timezone', 'historical_available_at', 'corrected_at',
                'rejected_rows', 'suspensions', 'source_query_context', 'source')
        _need(all(c.get(k) == saved.get(k) for k in keys), 'SAVED_CHART_CONTEXT_MISMATCH')
        display = saved.get('display') or {}
        _need(display.get('validation_tier') == 'UNVERIFIED_REFERENCE' and
              display.get('official') is False and display.get('state') in ('AVAILABLE', 'WITHHELD'),
              'SAVED_REFERENCE_DISPLAY_REQUIRED')
        c['display'] = deepcopy(display)
        c['history_store']['saved_display_sha256'] = expected_saved_chart_sha256
    return _bounded(c, 'QUERY_FILE_LIMIT')


def query_bytes(root, manifest, *, saved_chart_bytes=None, expected_saved_chart_sha256=None):
    """One JSON for the existing chart reader; never inflate archives in Worker."""
    return project_query(query_contract(root, manifest), saved_chart_bytes=saved_chart_bytes,
                         expected_saved_chart_sha256=expected_saved_chart_sha256)


def _commit(root, manifest):
    b = _bounded(manifest, 'MANIFEST_FILE_LIMIT')
    path = f"series/{manifest['series_id']}/manifests/{manifest['manifest_sha256']}.json"
    _immutable(_path(root, path), b)
    pointer = dict(path=path, sha256=_sha(b), bytes=len(b))
    _atomic(_path(root, f"series/{manifest['series_id']}/latest.json"), json_bytes(pointer))


def ingest(root, *, contract_bytes, body, receipt_bytes, expected_contract_sha256,
           expected_receipt_sha256, revision_reference=None):
    """Pinned, serializable ingestion; original body is NOT written anywhere.

    Monthly concatenated gzip members contain only new/reviewed-revised rows.
    latest.json is committed last. A failed/interrupted append leaves the previous
    committed prefix usable. An exact retry reuses a matching complete/partial
    tail; a different uncommitted tail fails closed rather than silently dropping
    evidence. All readers/writers must honor the manifest prefix, not EOF.
    """
    _need(_sha(contract_bytes) == expected_contract_sha256, 'CONTRACT_PIN')
    _need(_sha(receipt_bytes) == expected_receipt_sha256, 'RECEIPT_PIN')
    c, receipt = json.loads(contract_bytes), json.loads(receipt_bytes)
    _need(c.get('publication_scope') == SCOPE and c.get('basis') == 'RAW' and
          c.get('source_query', {}).get('MODP') == '0', 'RAW_DAILY_PRIVATE_REQUIRED')
    validate_contract(c)
    _need(c['bars'] == c['raw_bars'] and c.get('dividend_adjustment') == 'NONE',
          'RAW_ROWS_REQUIRED')
    _need(receipt.get('request') == c['source_query'], 'RECEIPT_QUERY_MISMATCH')
    evidence = {k: c.get(k) for k in ('security_id', 'issuer_id', 'currency_reference',
                                    'splits', 'confirmed_ranges', 'held_ranges',
                                    'session_scope', 'price_scope_status')}
    evidence.update(c['identity'], currency=c['currency'])
    rebuilt = normalize_page(body, receipt=receipt, request=c['source_query'], evidence=evidence)
    _need(rebuilt['raw_bars'] == c['raw_bars'] and
          rebuilt['rejected_rows'] == c['rejected_rows'] and
          rebuilt['source_sha256'] == c['source_sha256'] and
          rebuilt['collected_at'] == c['collected_at'], 'NORMALIZED_SOURCE_MISMATCH')
    source = json.loads(body)
    series = dict(symbol=c['symbol'], exchange=c['exchange'], currency=c['currency'],
                  calendar=c['calendar'], timezone=c['timezone'],
                  basis=c['basis'], lane='KIS_GUBN0_MODP0')
    series_id = digest(series)
    directory = _path(root, f'series/{series_id}')
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _ingest_locked(root, c, source, receipt, receipt_bytes, series, series_id,
                              expected_contract_sha256, revision_reference)


def _committed_receipt(root, latest, receipt_path):
    """Resolve only a receipt in the verified committed chain."""
    current = latest
    sid = latest['series_id']
    seen = set()
    while current is not None:
        pin = current['manifest_sha256']
        _need(pin not in seen, 'MANIFEST_CHAIN_CYCLE')
        seen.add(pin)
        if current['receipt']['path'] == receipt_path:
            return current
        prior = current['previous_manifest']
        if prior is None:
            break
        _need(isinstance(prior, str) and re.fullmatch('[0-9a-f]{64}', prior), 'MANIFEST_PREDECESSOR_PIN')
        path = f'series/{sid}/manifests/{prior}.json'
        current = json.loads(_path(root, path).read_bytes())
        _check_manifest(current)
        _need(current['manifest_sha256'] == prior and current['series_id'] == sid, 'MANIFEST_PREDECESSOR_PIN')
    return None


def _economic_bar(row):
    return {key: value for key, value in (row or {}).items()
            if key not in ('source_sha256', 'collected_at')}


def _verify_committed_replay(root, manifest, received, source, bars):
    saved = retained_metadata(root, manifest)
    # JSON whitespace/encoding in the derived contract is not source evidence.
    # The original contract hash remains pinned in the existing receipt object.
    _need({k:v for k,v in saved.items() if k != 'input_contract_sha256'} ==
          {k:v for k,v in received.items() if k != 'input_contract_sha256'}, 'RECEIPT_REPLAY_MISMATCH')
    historical = _latest(read_records(root, manifest))
    for row in source['output2']:
        day = datetime.strptime(row['xymd'], '%Y%m%d').date().isoformat()
        existing = historical.get(day)
        _need(existing is not None and existing['provider'] == row and
              _economic_bar(existing['bar']) == _economic_bar(bars.get(day)), 'RECEIPT_REPLAY_MISMATCH')


def _ingest_locked(root, c, source, receipt, receipt_bytes, series, sid, contract_hash, review):
    previous = load_manifest(root, sid) if _path(root, f'series/{sid}/latest.json').exists() else None
    evidence = {k: c.get(k) for k in _EVIDENCE}
    if previous:
        _need(previous['series'] == series and previous['evidence'] == evidence, 'SERIES_EVIDENCE_CHANGE')
    receipt_hash = _sha(receipt_bytes)
    receipt_path = f'series/{sid}/receipts/{receipt_hash}.json.gz'
    header = {k: v for k, v in c.items() if k not in ('raw_bars', 'bars')}
    meta = dict(receipt=receipt, original_receipt_utf8=receipt_bytes.decode('utf-8'),
                contract_header=header, source_header={k: v for k, v in source.items() if k != 'output2'},
                input_contract_sha256=contract_hash, original_body_sha256=receipt['sha256'],
                original_body_bytes=receipt['bytes'], raw_body_retained=False,
                original_body_reconstructable=False)
    bars = {r['date']: r for r in c['raw_bars']}
    if previous and (_path(root, receipt_path).exists() or
                     _ts(c['collected_at']) <= _ts(previous['collected_at'])):
        committed = _committed_receipt(root, previous, receipt_path)
        if committed is not None:
            _verify_committed_replay(root, committed, meta, source, bars)
            return dict(series_id=sid, manifest_sha256=previous['manifest_sha256'],
                        new_rows=0, revised_rows=0, unchanged_rows=len(source['output2']), appended_bytes=0)
    if previous:
        _need(_ts(c['collected_at']) >= _ts(previous['collected_at']), 'CAPTURE_REGRESSION')
    existing = _latest(read_records(root, previous)) if previous else {}
    rb = gzip.compress(json_bytes(meta), mtime=0)
    pending, counts = {}, dict(new_rows=0, revised_rows=0, unchanged_rows=0)
    for row in source['output2']:
        day = datetime.strptime(row['xymd'], '%Y%m%d').date().isoformat()
        prior = existing.get(day)
        # Capture/source hashes alone must never turn overlapping rows into revisions.
        old_bar = _economic_bar(prior['bar']) if prior else None
        bar = bars.get(day)
        new_bar = _economic_bar(bar)
        if prior and prior['provider'] == row and old_bar == new_bar:
            counts['unchanged_rows'] += 1
            continue
        if prior:
            _need(isinstance(review, str) and bool(review.strip()), 'ROW_REVISION_REVIEW_REQUIRED')
        record = dict(date=day, provider=row, bar=bar, receipt_sha256=receipt_hash,
                      supersedes=digest(prior) if prior else None,
                      revision_reference=review if prior else None)
        pending.setdefault(day[:7], []).append(record)
        counts['revised_rows' if prior else 'new_rows'] += 1
    months = deepcopy(previous['months']) if previous else {}
    additions = []
    for month, rows in sorted(pending.items()):
        rows.sort(key=lambda r: r['date'])
        addition = gzip.compress(b''.join(json_bytes(r) for r in rows), mtime=0)
        old = months.get(month, {})
        path = f'series/{sid}/months/{month}.jsonl.gz'
        prior_bytes = old.get('bytes', 0)
        months[month] = dict(path=path, bytes=prior_bytes+len(addition),
                            records=old.get('records', 0)+len(rows))
        additions.append((month, path, prior_bytes, addition, old))
    # Validate all existing tails before mutating any file. The exact retry is safe
    # even when the previous process stopped partway through a gzip member.
    for month, path, offset, addition, old in additions:
        p = _path(root, path)
        content = p.read_bytes() if p.exists() else b''
        prefix, tail = content[:offset], content[offset:]
        _need(len(prefix) == offset and (not old or _sha(prefix) == old['sha256']), 'MONTH_HASH')
        _need(addition.startswith(tail), 'DIFFERENT_UNCOMMITTED_TAIL')
        months[month]['sha256'] = _sha(prefix + addition)
    _immutable(_path(root, receipt_path), rb)
    for month, path, offset, addition, old in additions:
        p = _path(root, path); p.parent.mkdir(parents=True, exist_ok=True)
        have = p.stat().st_size-offset if p.exists() else 0
        with p.open('ab') as f:
            f.write(addition[have:]); f.flush(); os.fsync(f.fileno())
        _sync_directory(p.parent)
    manifest = dict(schema=SCHEMA, publication_scope=SCOPE, series_id=sid, series=series,
                    evidence=evidence, collected_at=c['collected_at'], months=months,
                    receipt=dict(path=receipt_path, bytes=len(rb), sha256=_sha(rb)),
                    previous_manifest=previous['manifest_sha256'] if previous else None,
                    row_count=len(existing)+counts['new_rows'],
                    revision_count=(previous['revision_count'] if previous else 0)+counts['revised_rows'],
                    latest_response_rows=len(source['output2']),
                    latest_response_state='ROWS_RECEIVED' if source['output2'] else 'EMPTY_SUCCESS',
                    raw_body_retained=False, original_body_reconstructable=False,
                    prices_adjusted=False, verification_promoted=False)
    manifest['manifest_sha256'] = digest(manifest)
    # Construct/reopen the bounded query before publishing this manifest pointer.
    query_bytes(root, manifest)
    _commit(root, manifest)
    return dict(series_id=sid, manifest_sha256=manifest['manifest_sha256'], **counts,
                appended_bytes=sum(len(item[3]) for item in additions))


def main(argv=None):
    """Network-free CLI; retain the existing outside-Git writer boundary."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--expected-contract-sha256', required=True)
    parser.add_argument('--expected-receipt-sha256', required=True)
    parser.add_argument('--query-output', type=Path, required=True)
    parser.add_argument('--revision-reference')
    parser.add_argument('--saved-chart', type=Path)
    parser.add_argument('--expected-saved-chart-sha256')
    args = parser.parse_args(argv)
    for p in (args.store, args.query_output):
        resolved = p.resolve()
        _need(not any((d / '.git').exists() for d in (resolved, *resolved.parents)),
              'PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED')
    result = ingest(args.store, contract_bytes=args.contract.read_bytes(), body=args.body.read_bytes(),
                    receipt_bytes=args.receipt.read_bytes(),
                    expected_contract_sha256=args.expected_contract_sha256,
                    expected_receipt_sha256=args.expected_receipt_sha256,
                    revision_reference=args.revision_reference)
    m = load_manifest(args.store, result['series_id'])
    _atomic(args.query_output, query_bytes(args.store, m,
            saved_chart_bytes=args.saved_chart.read_bytes() if args.saved_chart else None,
            expected_saved_chart_sha256=args.expected_saved_chart_sha256))
    # Only aggregate operation counts; no prices, symbols or raw source text.
    print(json.dumps({k: result[k] for k in ('new_rows', 'revised_rows', 'unchanged_rows', 'appended_bytes')}))


if __name__ == '__main__':
    main()
