"""Offline #564 input pairing, request freezing and replay with original pins."""
import json

import pytest

from investment_system.research import kis_request_builder as builder
from investment_system.research.kis_rebuild import load_request
from test_kis_rebuild import inputs, sha


def test_freeze_pins_exact_scope_members_and_is_repeatable(tmp_path):
    req, want = inputs(tmp_path/'original')
    root = req.parent
    old = json.loads(req.read_bytes())
    req.rename(root/'legacy.json')
    params = dict(store_path='store', evaluation_day=old['evaluation_day'], calculated_at=old['calculated_at'],
                  financial=old['financial'], symbols=old['symbols'], expected_series=1)
    prepared = builder.freeze(root, **params)
    assert prepared['series'] == 1 and prepared['rows'] == 5
    value = req.read_bytes()
    assert builder.freeze(root, **params) == prepared and req.read_bytes() == value
    _, _, contracts = load_request(req, prepared['request_sha256'])
    assert contracts[next(iter(contracts))] == want
    with pytest.raises(ValueError, match='SYMBOL_SCOPE_COUNT_MISMATCH'):
        builder.freeze(root, **dict(params, expected_series=2))
    with pytest.raises(ValueError, match='IMMUTABLE_FILE_MISMATCH'):
        builder.freeze(root, **dict(params, calculated_at='2026-10-24T05:00:00Z'))
    assert req.read_bytes() == value


def test_page_ingest_reuses_monthly_dedup_and_holds_hash_boundaries(tmp_path):
    from investment_system.research._private_artifacts import json_bytes
    request = dict(SYMB='SYN', EXCD='NAS', MODP='0', GUBN='0', BYMD='20261023')
    raw = json_bytes(dict(rt_cd='0', output1=dict(rsym='DNASSYN'), output2=[
        dict(xymd='20261023',open='10',high='12',low='9',clos='11',tvol='100',tamt='1100')]))
    receipt = json_bytes(dict(sha256=sha(raw),bytes=len(raw),http_status=200,
                              fetched_at='2026-10-24T04:00:00Z',request=request))
    evidence = dict(currency='USD',currency_reference='SYNTHETIC_NOT_A_COMPANY')
    with pytest.raises(ValueError, match='SOURCE_HASH_OR_SIZE_MISMATCH'):
        builder.ingest_page(tmp_path,raw+b' ',receipt,sha(receipt),evidence)
    assert not (tmp_path/'series').exists()
    first = builder.ingest_page(tmp_path,raw,receipt,sha(receipt),evidence)
    assert first['new_rows'] == 1
    second = builder.ingest_page(tmp_path,raw,receipt,sha(receipt),evidence)
    assert second['appended_bytes'] == 0 and second['unchanged_rows'] == 1


def test_evidence_file_binds_kis_symbol_and_venue(tmp_path):
    req, want = inputs(tmp_path/'original')
    output = tmp_path/'evidence.json'
    frozen = builder.freeze_evidence(req, sha(req.read_bytes()), output)
    data = json.loads(output.read_bytes())
    assert frozen['series'] == 1
    code = next(iter(data['entries']))
    receipt = json.dumps(dict(request=want['source_query'])).encode()
    assert builder.page_evidence(data, code, receipt)['currency_reference'] == want['currency_reference']
    with pytest.raises(ValueError, match='PAGE_EVIDENCE_QUERY_MISMATCH'):
        builder.page_evidence(data, code, json.dumps(dict(request=dict(
            want['source_query'], EXCD='NYS'))).encode())


def test_older_page_cursor_reads_committed_journal_not_the_newest_receipt(tmp_path):
    from investment_system.research import kis_stock_journal as journal
    req, contract = inputs(tmp_path/'original')
    config = json.loads(req.read_bytes())
    source = tmp_path/'source'
    patch = journal.changes({'CODE':contract}, {}, config, None)
    files, head = journal.archive_files(config, patch, None)
    for name, data in files.items():
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = tmp_path/'coverage.json'
    out = builder.plan_coverage(source, head['path'], head['sha256'], result)
    assert out['series'] == 1
    assert json.loads(result.read_bytes())['CODE'] == {'earliest':'20261019','latest':'20261023'}
