"""Synthetic append/replay tests; no provider requests or actual prices."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from investment_system.research._private_artifacts import canonical_bytes
from investment_system.research.kis_price_bridge import normalize_page


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sample(days=('20261029', '20261030', '20261102'), *, changed=None,
           fetched='2026-11-03T02:00:00Z'):
    rows = [dict(xymd=d, open='10', high='12', low='9', clos='11',
                 tvol='100', tamt='1100', extra='PRESERVE_PROVIDER_FIELD') for d in days]
    if changed:
        rows[0]['clos'] = changed
    body = canonical_bytes(dict(rt_cd='0', output1=dict(rsym='DNASSYN'), output2=rows))
    req = dict(SYMB='SYN', EXCD='NAS', MODP='0', GUBN='0', BYMD='')
    receipt = dict(sha256=sha(body), bytes=len(body), http_status=200,
                   fetched_at=fetched, request=req)
    c = normalize_page(body, receipt=receipt, request=req,
                       evidence=dict(currency='USD', currency_reference='SYNTHETIC'))
    return c, body, canonical_bytes(receipt)


def api():
    return importlib.import_module('investment_system.research.monthly_price_store')


def put(root, sample_value, **kw):
    c, body, receipt = sample_value
    cb = canonical_bytes(c)
    return api().ingest(root, contract_bytes=cb, body=body, receipt_bytes=receipt,
                        expected_contract_sha256=sha(cb),
                        expected_receipt_sha256=sha(receipt), **kw)


def test_migration_reopens_exact_rows_and_all_provider_fields(tmp_path):
    c, body, r = sample()
    out = put(tmp_path, (c, body, r))
    m = api().load_manifest(tmp_path, out['series_id'])
    q = api().query_bytes(tmp_path, m)
    view = json.loads(q)
    assert view['raw_bars'] == c['raw_bars'] and view['bars'] == c['bars']
    assert view['display']['validation_tier'] == 'UNVERIFIED_REFERENCE'
    assert len(m['months']) == 2 and out['new_rows'] == 3
    assert out['revised_rows'] == out['unchanged_rows'] == 0
    records = api().read_records(tmp_path, m)
    assert [x['provider'] for x in records] == json.loads(body)['output2']
    assert all(x['provider']['extra'] == 'PRESERVE_PROVIDER_FIELD' for x in records)
    assert m['raw_body_retained'] is False and m['original_body_reconstructable'] is False
    assert len(q) < api().MAX_BYTES


def test_replay_is_byte_identical_and_changed_capture_only_deduplicates(tmp_path):
    first = put(tmp_path, sample())
    files = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    again = put(tmp_path, sample())
    assert again['manifest_sha256'] == first['manifest_sha256']
    assert files == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    later = put(tmp_path, sample(fetched='2026-11-04T02:00:00Z'))
    assert later['new_rows'] == later['revised_rows'] == 0
    assert later['unchanged_rows'] == 3 and later['appended_bytes'] == 0
    old = json.loads(api().query_bytes(tmp_path, api().load_manifest(tmp_path, first['series_id'])))
    assert old['raw_bars'] == sample()[0]['raw_bars']  # first observation remains attributed


def test_overlap_adds_only_new_row_and_preserves_old_month_bytes(tmp_path):
    first = put(tmp_path, sample())
    before = api().load_manifest(tmp_path, first['series_id'])
    old = deepcopy(before['months']['2026-10'])
    later = put(tmp_path, sample(('20261030', '20261102', '20261103'), fetched='2026-11-04T02:00:00Z'))
    m = api().load_manifest(tmp_path, first['series_id'])
    assert (later['new_rows'], later['unchanged_rows'], later['revised_rows']) == (1, 2, 0)
    assert m['months']['2026-10'] == old
    assert len(api().read_records(tmp_path, m)) == 4
    assert before['months']['2026-11']['bytes'] < m['months']['2026-11']['bytes']
    assert len(api().read_records(tmp_path, before)) == 3  # historical prefix still readable


def test_correction_requires_explicit_review_and_preserves_previous(tmp_path):
    first = put(tmp_path, sample())
    before = api().load_manifest(tmp_path, first['series_id'])
    corrected = sample(changed='10.5', fetched='2026-11-04T02:00:00Z')
    with pytest.raises(ValueError, match='ROW_REVISION_REVIEW_REQUIRED'):
        put(tmp_path, corrected)
    result = put(tmp_path, corrected, revision_reference='SYNTHETIC_REVIEW')
    m = api().load_manifest(tmp_path, first['series_id'])
    records = api().read_records(tmp_path, m)
    assert result['revised_rows'] == 1 and len(records) == 4
    assert next(r for r in records if r['supersedes'])['supersedes'] == sha(canonical_bytes(records[0]))
    assert api().query_contract(tmp_path, m)['raw_bars'][0]['close'] == '10.5'
    assert api().query_contract(tmp_path, before)['raw_bars'][0]['close'] == '11'


@pytest.mark.parametrize('kind', ['contract', 'receipt', 'body', 'modp', 'basis', 'bar'])
def test_bad_pins_and_raw_basis_are_rejected_before_writing(tmp_path, kind):
    c, b, rb = sample()
    if kind == 'contract':
        with pytest.raises(ValueError, match='CONTRACT_PIN'):
            api().ingest(tmp_path, contract_bytes=canonical_bytes(c), body=b, receipt_bytes=rb,
                         expected_contract_sha256='0'*64, expected_receipt_sha256=sha(rb))
        return
    if kind == 'receipt':
        with pytest.raises(ValueError, match='RECEIPT_PIN'):
            api().ingest(tmp_path, contract_bytes=canonical_bytes(c), body=b, receipt_bytes=rb,
                         expected_contract_sha256=sha(canonical_bytes(c)), expected_receipt_sha256='0'*64)
        return
    if kind == 'body': b += b' '
    if kind == 'modp': c['source_query']['MODP'] = '1'
    if kind == 'basis': c['basis'] = 'SPLIT_ADJUSTED'
    if kind == 'bar':
        for rows in (c['bars'], c['raw_bars']): rows[0]['close'] = '10.1'
    with pytest.raises(ValueError): put(tmp_path, (c, b, rb))
    assert not list(tmp_path.rglob('*.gz'))


def test_failed_commit_keeps_previous_query_and_exact_retry_resumes(tmp_path, monkeypatch):
    first = put(tmp_path, sample())
    before = api().load_manifest(tmp_path, first['series_id'])
    expected = api().query_bytes(tmp_path, before)
    original = api()._commit
    monkeypatch.setattr(api(), '_commit', lambda *a: (_ for _ in ()).throw(OSError('SYNTHETIC_DISK_FAILURE')))
    incoming = sample(('20261103',), fetched='2026-11-04T02:00:00Z')
    with pytest.raises(OSError): put(tmp_path, incoming)
    assert api().query_bytes(tmp_path, api().load_manifest(tmp_path, first['series_id'])) == expected
    monkeypatch.setattr(api(), '_commit', original)
    result = put(tmp_path, incoming)
    assert result['new_rows'] == 1
    assert len(api().query_contract(tmp_path, api().load_manifest(tmp_path, first['series_id']))['bars']) == 4


def test_changed_identity_tampered_month_and_view_size_fail_closed(tmp_path, monkeypatch):
    first = put(tmp_path, sample()); m = api().load_manifest(tmp_path, first['series_id'])
    c, b, rb = sample(); c['issuer_id'] = 'SYNTHETIC_DIFFERENT_ISSUER'
    with pytest.raises(ValueError, match='SERIES_EVIDENCE_CHANGE'): put(tmp_path, (c, b, rb))
    monkeypatch.setattr(api(), 'MAX_BYTES', 10)
    with pytest.raises(ValueError, match='QUERY_FILE_LIMIT'): api().query_bytes(tmp_path, m)
    p = tmp_path / next(iter(m['months'].values()))['path']
    with p.open('r+b') as f: f.write(b'CORRUPTED')
    with pytest.raises(ValueError, match='MONTH_HASH'): api().read_records(tmp_path, m)


def test_root_containment_and_manifest_hash(tmp_path):
    first = put(tmp_path, sample())
    with pytest.raises(ValueError, match='SERIES_ID'): api().load_manifest(tmp_path, '../escape')
    m = api().load_manifest(tmp_path, first['series_id']); m['row_count'] += 1
    with pytest.raises(ValueError, match='MANIFEST_HASH'): api().query_bytes(tmp_path, m)


def test_different_uncommitted_tail_is_not_discarded(tmp_path, monkeypatch):
    first = put(tmp_path, sample())
    m = api().load_manifest(tmp_path, first['series_id'])
    old_query = api().query_bytes(tmp_path, m)
    p = tmp_path / m['months']['2026-11']['path']
    with p.open('ab') as f: f.write(b'UNKNOWN_UNCOMMITTED_EVIDENCE')
    with pytest.raises(ValueError, match='DIFFERENT_UNCOMMITTED_TAIL'):
        put(tmp_path, sample(('20261103',), fetched='2026-11-04T02:00:00Z'))
    assert api().query_bytes(tmp_path, api().load_manifest(tmp_path, first['series_id'])) == old_query
    assert p.read_bytes().endswith(b'UNKNOWN_UNCOMMITTED_EVIDENCE')


def test_empty_success_is_explicit_and_http_failure_does_not_create_replacement(tmp_path):
    c,b,r = sample(())
    result = put(tmp_path,(c,b,r));m = api().load_manifest(tmp_path,result['series_id'])
    assert m['row_count'] == 0 and m['months'] == {}
    assert api().query_contract(tmp_path,m)['bars'] == []
    bad = json.loads(r);bad['http_status'] = 429
    with pytest.raises(ValueError, match='SOURCE_HTTP_FAILURE'):
        put(tmp_path,(c,b,canonical_bytes(bad)))
    assert api().load_manifest(tmp_path,result['series_id']) == m


def test_five_year_synthetic_query_remains_one_bounded_file(tmp_path):
    from datetime import date, timedelta
    from investment_system.research.exp_deciles import schedule
    from investment_system.research.pit_filings import session_close
    day=date(2026,11,13);days=[]
    while len(days)<1260:
        if schedule.is_session(day) and session_close(day).close_at is not None:
            days.append(day.strftime('%Y%m%d'))
        day-=timedelta(days=1)
    result=put(tmp_path,sample(tuple(reversed(days)),fetched='2026-11-15T02:00:00Z'))
    m=api().load_manifest(tmp_path,result['series_id']);b=api().query_bytes(tmp_path,m)
    assert len(json.loads(b)['bars']) == 1260 and len(b) <= 1800000
    assert 59 <= len(m['months']) <= 62


def test_cli_preserves_existing_git_output_boundary(tmp_path):
    root=tmp_path/'git';root.mkdir();(root/'.git').mkdir()
    with pytest.raises(ValueError,match='PRIVATE_OUTPUT_OUTSIDE_GIT_REQUIRED'):
        api().main(['--store',str(root/'store'),'--contract','unused','--body','unused',
                    '--receipt','unused','--expected-contract-sha256','0'*64,
                    '--expected-receipt-sha256','0'*64,'--query-output',str(root/'view.json')])
    assert not (root/'store').exists()


def test_saved_display_hold_is_pinned_and_never_silently_dropped(tmp_path):
    c,body,r=sample();out=put(tmp_path,(c,body,r))
    m=api().load_manifest(tmp_path,out['series_id'])
    assert json.loads(api().query_bytes(tmp_path,m))['display']['state']=='WITHHELD'
    c['display']=dict(state='WITHHELD',hold_reasons=['SYNTHETIC_EVENT'],
                      validation_tier='UNVERIFIED_REFERENCE',official=False)
    b=canonical_bytes(c)
    q=api().query_bytes(tmp_path,m,saved_chart_bytes=b,expected_saved_chart_sha256=sha(b))
    assert json.loads(q)['display']==c['display']
    with pytest.raises(ValueError,match='SAVED_CHART_PIN'):
        api().query_bytes(tmp_path,m,saved_chart_bytes=b,expected_saved_chart_sha256='0'*64)
    c['raw_bars'][0]['close']='10.5';c['bars']=deepcopy(c['raw_bars']);b=canonical_bytes(c)
    with pytest.raises(ValueError,match='SAVED_CHART_CONTEXT_MISMATCH'):
        api().query_bytes(tmp_path,m,saved_chart_bytes=b,expected_saved_chart_sha256=sha(b))
