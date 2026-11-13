"""Independent retained-input pins, not self-consistency of delivered results."""
from copy import deepcopy
import hashlib
import json
import pytest
from investment_system.research.dual_qgv import json_bytes
from investment_system.research.dual_qgv_input_anchors import (
    input_anchors, validate_anchored_delivery, delivery_clocks)


def sha(b): return hashlib.sha256(b).hexdigest()
def descriptor(path, raw): return dict(path=path, size=len(raw), sha256=sha(raw))


def fixture():
    ref = dict(schema_version='sector-qgv-input/1', universe_id='SYN:reference',
        universe_version='1', snapshot_id='SYN:ref', input_version='review/1',
        mapping_version='SYN:map/1', valuation_date='2026-11-04',
        as_of='2026-11-13T11:00:00Z', members=['A', 'B'],
        rows=[dict(company_id=k, issuer_id=k, observations={}) for k in ('A', 'B')],
        review_context={'original_snapshot_hash': 'a'*64})
    ev = deepcopy(ref)
    ev.update(universe_id='SYN:evaluation', universe_version='2', snapshot_id='SYN:ev',
        members=['A'], rows=ev['rows'][:1], review_context={'original_snapshot_hash':'b'*64})
    a, b = json_bytes(ev), json_bytes(ref)
    bundle = json_bytes(dict(schema_version='qgv-q-input-private-bundle/1', execution_sha='c'*40,
        files=[descriptor('ev.json', a), descriptor('ref.json', b)]))
    location = dict(repo='SYN:private', ref='SYN:retained', path='SYN:run', commit='d'*40)
    handoff = json_bytes(dict(schema_version='qgv-q-input-handoff/1', **location,
        files=[descriptor('bundle-manifest.json', bundle)]))
    return dict(scope='held1057', preservation=location, handoff_raw=handoff, bundle_raw=bundle,
        expected_handoff_sha256=sha(handoff), evaluation_raw=a, evaluation_path='ev.json',
        reference_raw=b, reference_path='ref.json')


def delivery(a):
    ev, ref = a['expected_evaluation'], a['expected_reference']
    return (dict(boards={'U2-333':dict(evaluation_population=deepcopy(ev),
        bindings=dict(evaluation=deepcopy(ev), reference=deepcopy(ref)),
        reference_population=dict(candidate_population=deepcopy(ref),
            **{k:ref[k] for k in ('input_hash','valuation_date','as_of')}))}),
        dict(evaluation_population=deepcopy(ev)))


def test_separate_input_hashes_and_real_review_context_difference():
    a = input_anchors(**fixture()); s, i = delivery(a)
    assert a['expected_evaluation']['input_hash'] != a['expected_reference']['input_hash']
    assert a['projection']['changed_top_level_fields'] == [
        'members','review_context','rows','snapshot_id','universe_id','universe_version']
    assert a['projection']['review_context_equal'] is False
    raw = json_bytes(a)
    assert validate_anchored_delivery(s,i,anchor_raw=raw,expected_anchor_sha256=sha(raw))['status']=='VERIFIED_BOTH_INPUT_BINDINGS'


@pytest.mark.parametrize('part',['handoff_raw','bundle_raw','evaluation_raw','reference_raw'])
def test_cannot_replace_either_input_or_preserved_root(part):
    f=fixture();f[part]+=b' '
    with pytest.raises(ValueError,match='HASH'):input_anchors(**f)


@pytest.mark.parametrize('side',['evaluation','reference'])
@pytest.mark.parametrize('field',['input_hash','members_hash','valuation_date','as_of','snapshot_id','version'])
def test_consistently_changed_delivery_does_not_pass_independent_pin(side,field):
    a=input_anchors(**fixture());s,i=delivery(a);board=s['boards']['U2-333']
    board['bindings'][side][field]='FORGED'
    if side=='evaluation':
        board['evaluation_population'][field]='FORGED';i['evaluation_population'][field]='FORGED'
    else:
        board['reference_population']['candidate_population'][field]='FORGED'
        if field in board['reference_population']:board['reference_population'][field]='FORGED'
    raw=json_bytes(a)
    with pytest.raises(ValueError,match=side.upper()+'_INPUT_BINDING'):
        validate_anchored_delivery(s,i,anchor_raw=raw,expected_anchor_sha256=sha(raw))


def test_runtime_lineage_is_not_accepted_as_proof():
    a=input_anchors(**fixture());s,i=delivery(a)
    raw=json_bytes(dict(evaluation=a['expected_evaluation'],reference_source=a['expected_reference']))
    with pytest.raises(ValueError,match='INPUT_ANCHOR_SCHEMA'):
        validate_anchored_delivery(s,i,anchor_raw=raw,expected_anchor_sha256=sha(raw))


def test_delivery_generation_time_cannot_become_calculation_time():
    c=delivery_clocks(generated_at='2026-11-13T14:00:00Z',execution_sha='c'*40,
        inspected_record_refs=[dict(path='SYN:run.log',sha256='a'*64)])
    assert c['calculated_at'] is None and c['calculated_at_reason']=='EXECUTION_TIMESTAMP_NOT_RECORDED'
    assert c['delivery_generated_at']=='2026-11-13T14:00:00Z'


def test_independent_input_version_chains_need_not_be_identical():
    f=fixture();ev=json.loads(f['evaluation_raw']);ev['input_version']='separate-evaluation-build/2'
    f['evaluation_raw']=json_bytes(ev)
    bundle=json.loads(f['bundle_raw']);bundle['files'][0]=descriptor('ev.json',f['evaluation_raw'])
    f['bundle_raw']=json_bytes(bundle)
    handoff=json.loads(f['handoff_raw']);handoff['files']=[descriptor('bundle-manifest.json',f['bundle_raw'])]
    f['handoff_raw']=json_bytes(handoff);f['expected_handoff_sha256']=sha(f['handoff_raw'])
    a=input_anchors(**f)
    assert 'input_version' in a['projection']['changed_top_level_fields']


@pytest.mark.parametrize('change,code',[
    ('row','TARGET_ROW_PROJECTION'), ('date','INPUT_CONTEXT'),
    ('cutoff','INPUT_CONTEXT'), ('duplicate','REFERENCE_DUPLICATE_MEMBER')])
def test_retained_bytes_still_require_valid_projection_and_time(change,code):
    f=fixture();ev=json.loads(f['evaluation_raw'])
    if change=='row':ev['rows'][0]['issuer_id']='WRONG'
    elif change=='date':ev['valuation_date']='2026-11-05'
    elif change=='cutoff':ev['as_of']='2026-11-14T11:00:00Z'
    else:ev['members'].append('A')
    f['evaluation_raw']=json_bytes(ev)
    bundle=json.loads(f['bundle_raw']);bundle['files'][0]=descriptor('ev.json',f['evaluation_raw'])
    f['bundle_raw']=json_bytes(bundle)
    handoff=json.loads(f['handoff_raw']);handoff['files']=[descriptor('bundle-manifest.json',f['bundle_raw'])]
    f['handoff_raw']=json_bytes(handoff);f['expected_handoff_sha256']=sha(f['handoff_raw'])
    with pytest.raises(ValueError,match=code):input_anchors(**f)
