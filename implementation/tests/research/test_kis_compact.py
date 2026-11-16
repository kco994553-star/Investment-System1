"""Compact delivery retains states/values, never invents a price or score."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import zlib

import pytest

from investment_system.research._private_artifacts import json_bytes, MAX_BYTES


def api():return importlib.import_module('investment_system.research.kis_compact')


def cases():
    return {f'SYN{i}':dict(technical=dict(metrics=dict(x=dict(value=None,raw_value=i/7,
            reference_value=i/7,null_reasons=['IDENTITY_UNCONFIRMED','ACTION_RANGE_UNCONFIRMED'],
            state='DIAGNOSTIC',unit='ratio')),display=dict(state='AVAILABLE',official=False)),
            measures=dict(metrics=dict(y=dict(value=0,raw_value=0,reference_value=0,
                null_reasons=[],state='VALUE',unit='percent')))) for i in range(20)}


def test_packed_latest_is_lossless_deterministic_and_preserves_zero_null():
    m=api();rows=cases();p=m.pack(rows,kind='INDICATORS')
    assert p==m.pack(dict(reversed(list(rows.items()))),kind='INDICATORS')
    assert {k:m.unpack_row(p,k) for k in rows}==rows
    assert len(json_bytes(p))<len(json_bytes(rows))
    assert m.unpack_row(p,'SYN0')['technical']['metrics']['x']['value'] is None
    assert m.unpack_row(p,'SYN0')['measures']['metrics']['y']['value']==0
    rows['SYN0']['technical']['display']['state']='WITHHELD'
    assert m.unpack_row(m.pack(rows,kind='INDICATORS'),'SYN0')['technical']['display']['state']=='WITHHELD'


def test_bad_shared_reference_and_cycles_are_rejected():
    m=api();p=m.pack(cases(),kind='INDICATORS')
    p['rows']['SYN0']=[2,999999]
    with pytest.raises(ValueError):m.unpack_row(p,'SYN0')
    p['shared']=[[2,0]];p['rows']['SYN0']=[2,0]
    with pytest.raises(ValueError):m.unpack_row(p,'SYN0')


def legacy(days=('2026-10-29','2026-10-30','2026-11-02'),*,alter=None):
    rows=[dict(date=d,open='10',high='12',low='9',close='11',volume='100',amount='1100',
               source_sha256='a'*64,collected_at='2026-11-03T01:00:00Z',corrected=None) for d in days]
    if alter:rows[0]['close']=alter
    c=dict(schema='kis-bars/1',symbol='SYN',basis='RAW',currency='USD',raw_bars=rows,
           bars=deepcopy(rows),price_basis_date=days[-1],splits=[],
           publication_scope='OWNER_PRIVATE_ONLY',display=dict(state='WITHHELD',
           validation_tier='UNVERIFIED_REFERENCE',official=False,hold_reasons=['SYNTHETIC']))
    yield 'chart/S/SYN.json',json_bytes(c)
    yield 'technical/S/SYN.json',json_bytes(cases()['SYN0']['technical'])
    yield 'measures/S/SYN.json',json_bytes(cases()['SYN0']['measures'])
    yield 'manifests/S/SYN.json',b'{}\n'
    yield 'qgv/latest.json',json_bytes(dict(schema='kis-qgv/1',rows={'ROW':{'total':None}},
                                          private_raw_detail={'ROW':{'price':123}},display=c['display']))


def test_chart_closed_pieces_stay_identical_and_latest_has_no_price_series():
    m=api();a=m.compact(legacy(),evaluation_day='2026-11-02')
    b=m.compact(legacy(('2026-10-29','2026-10-30','2026-11-02','2026-11-03')),evaluation_day='2026-11-03')
    closed=[k for k in a if k.startswith('chart/month/')]
    assert closed and all(k in b and a[k]==b[k] for k in closed)
    p=json.loads(a['latest/indicators.json']);entry=m.unpack_row(p,'SYN')
    assert set(entry)=={'technical','measures'}
    header=m.unpack_row(json.loads(a['chart/index.json'])['headers'],'SYN')
    assert 'raw_bars' not in header and 'bars' not in header
    assert header['display']['state']=='WITHHELD'
    assert all(len(v)<=MAX_BYTES for v in b.values())
    q=json.loads(a['qgv/latest.json'])
    assert 'private_raw_detail' not in q['context'] and q['raw_detail_state']=='REBUILDABLE_NOT_IN_VIEW'
    assert m.unpack_row(q,'ROW')['total'] is None


def test_chart_assembly_preserves_decimal_values_and_only_confirmed_splits():
    m=api();f=m.compact(legacy(),evaluation_day='2026-11-02')
    view=m.assemble_chart(f,'SYN')
    assert [r['close'] for r in view['raw_bars']]==['11']*3
    assert view['row_source_scope']=='DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE'
    assert view['display']['state']=='WITHHELD'


def test_immutable_correction_requires_reference_and_has_new_path():
    m=api();old=m.compact(legacy(),evaluation_day='2026-11-02')
    previous=json.loads(old['manifest.json'])
    with pytest.raises(ValueError,match='IMMUTABLE_PIECE_CHANGED'):
        m.compact(legacy(alter='10.5'),evaluation_day='2026-11-02',previous=previous)
    new=m.compact(legacy(alter='10.5'),evaluation_day='2026-11-02',previous=previous,
                  revision_reference='SYNTHETIC_REVIEW')
    assert set(k for k in old if k.startswith('chart/month/')) != set(k for k in new if k.startswith('chart/month/'))
    assert json.loads(new['manifest.json'])['reviewed_revisions']['reference']=='SYNTHETIC_REVIEW'


def test_unknown_or_missing_previous_ledger_cannot_reset_budget():
    m=api()
    with pytest.raises(ValueError,match='PREVIOUS_COMPACT_CONTRACT'):
        m.compact(legacy(),evaluation_day='2026-11-02',previous={})
    previous=json.loads(m.compact(legacy(),evaluation_day='2026-11-02')['manifest.json'])
    previous.pop('growth_ledger')
    with pytest.raises(ValueError,match='PREVIOUS_GROWTH_LEDGER_REQUIRED'):
        m.compact(legacy(),evaluation_day='2026-11-03',previous=previous)


def test_growth_counts_only_changed_blobs_and_fails_budget_without_dropping_rows():
    m=api();a=m.compact(legacy(),evaluation_day='2026-11-02')
    previous=json.loads(a['manifest.json'])
    same=m.growth(a,previous=previous)
    assert same['changed_payload_bytes']==len(a['manifest.json']) or same['changed_payload_bytes']==0
    with pytest.raises(ValueError,match='DAILY_DATA_BUDGET'):
        m.compact(legacy(('2026-10-29','2026-10-30','2026-11-02','2026-11-03')),
                  evaluation_day='2026-11-03',previous=previous,daily_budget=10)


def test_annual_budget_failure_and_no_free_credit_from_removed_files():
    m=api();old=m.compact(legacy(),evaluation_day='2026-11-02')
    previous=json.loads(old['manifest.json'])
    previous['growth_ledger']['charged_bytes']=260000000
    with pytest.raises(ValueError,match='ANNUAL_DATA_BUDGET'):
        m.compact(legacy(('2026-10-29','2026-10-30','2026-11-02','2026-11-03')),
                  evaluation_day='2026-11-03',previous=previous)


def test_growth_uses_default_loose_git_level_one_not_assumed_fourfold_compression():
    m=api();b=b'SYNTHETIC_TEST\n'*100
    expected=len(zlib.compress(b'blob '+str(len(b)).encode()+b'\0'+b,1))
    assert m.growth({'latest/value.json':b})['new_git_loose_blob_bytes']==expected


def test_storage_year_uses_calculation_clock_not_last_december_price_day():
    def source():
        for name,b in legacy():
            if name=='qgv/latest.json':
                q=json.loads(b);q['calculated_at']='2027-01-01T04:00:00Z';b=json_bytes(q)
            yield name,b
    result=api().compact(source(),evaluation_day='2026-12-31')
    assert json.loads(result['manifest.json'])['growth_ledger']['year']=='2027'


def test_node_decoder_matches_python_for_same_wire_and_rejects_cycles():
    if not shutil.which('node'):pytest.skip('Node contract consumer unavailable')
    m=api();p=m.pack(cases(),kind='INDICATORS')
    module=(Path(__file__).parents[2]/'src/investment_system/research/kis_compact_reader.mjs').as_uri()
    script="""import {decodeRecord} from MODULE;
let raw='';for await(const c of process.stdin)raw+=c;
const p=JSON.parse(raw);let failed=false;
const result=decodeRecord(p,'SYN0');
p.shared=[[2,0]];p.rows.SYN0=[2,0];try{decodeRecord(p,'SYN0');}catch{failed=true;}
console.log(JSON.stringify({result,failed}));
""".replace('MODULE',json.dumps(module))
    run=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(p),text=True,capture_output=True)
    assert run.returncode==0,run.stderr
    out=json.loads(run.stdout)
    assert out['result']==cases()['SYN0'] and out['failed'] is True
