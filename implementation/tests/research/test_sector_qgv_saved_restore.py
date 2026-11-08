"""Saved-setting replay boundaries only; no retained real-data recalculation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.research.sector_qgv import (
    default_config, preset, preview_qgv, save_user_config,
)

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'docs/research/sector_qgv/synthetic-input.json'
CLI = ROOT / 'tools/sector_qgv.py'


def pinned(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return pinned(path)


def custom_config():
    config = default_config()
    config.update(config_id='saved-custom', owner_scope='PRIVATE',
                  display_preferences={'label': '내 설정', 'lynch': ['관찰']})
    selected = preset(config, 'INFORMATION_TECHNOLOGY', 'GENERAL')
    selected['axis_weights'] = {'Q': 6000, 'G': 2500, 'V': 1500}
    config['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL'] = selected
    return config


@pytest.fixture
def record():
    snapshot = json.loads(FIX.read_text())
    config = custom_config()
    preview = preview_qgv(config, snapshot, 'saved-original')
    saved = save_user_config(config, preview, request_id='saved-original',
                             expected_preview_id=preview['preview_id'])
    return saved, preview, snapshot


def test_cli_replays_saved_custom_settings_without_replacing_history(tmp_path):
    original_job = {'mode': 'normalized', 'data_kind': 'SYNTHETIC',
                    'request_id': 'saved-original', 'config': custom_config(),
                    'snapshot': pinned(FIX)}
    write_json(tmp_path / 'original-job.json', original_job)
    original = tmp_path / 'original'
    first = subprocess.run([sys.executable, str(CLI), '--job', str(tmp_path / 'original-job.json'),
                            '--output', str(original), '--synthetic'], capture_output=True, text=True)
    assert first.returncode == 0, first.stdout
    saved_path, preview_path = original / 'saved-config.json', original / 'preview.json'
    history = {p.name: p.read_bytes() for p in original.iterdir()}
    replay_job = {'mode': 'normalized', 'data_kind': 'SYNTHETIC', 'request_id': 'saved-replay',
                  'snapshot': pinned(original / 'snapshot.json'),
                  'saved_config': pinned(saved_path), 'retained_preview': pinned(preview_path)}
    write_json(tmp_path / 'replay-job.json', replay_job)
    command = [sys.executable, str(CLI), '--job', str(tmp_path / 'replay-job.json'),
               '--output', str(tmp_path / 'replay'), '--synthetic']
    replay = subprocess.run(command, capture_output=True, text=True)
    assert replay.returncode == 0, replay.stdout
    restored = json.loads((tmp_path / 'replay/saved-config.json').read_text())
    old = json.loads(saved_path.read_text())
    assert restored['config'] == old['config']
    assert restored['canonical_config_hash'] == old['canonical_config_hash']
    assert restored['preview_id'] != old['preview_id']
    assert json.loads((tmp_path / 'replay/preview.json').read_text())['result_rows'] == json.loads(preview_path.read_text())['result_rows']
    refused = subprocess.run(command, capture_output=True, text=True)
    assert refused.returncode == 2
    assert json.loads(refused.stdout)['reason'] == 'OUTPUT_ALREADY_EXISTS'
    assert history == {p.name: p.read_bytes() for p in original.iterdir()}


def test_api_replay_preserves_all_settings_and_versions(record):
    from investment_system.research.sector_qgv_restore import replay_saved_config
    saved, retained, snapshot = record
    untouched = copy.deepcopy(record)
    result = replay_saved_config(saved, retained, snapshot, 'restored-request')
    assert result['config'] == saved['config']
    assert result['preview']['result_rows'] == retained['result_rows']
    for key in ('config_hash', 'input_hash', 'cache_key', 'model_version', 'engine_version',
                'normalization_version', 'mapping_version', 'input_version', 'snapshot_id',
                'universe_id', 'universe_version', 'valuation_date', 'as_of'):
        assert result['preview'][key] == retained[key]
    assert record == untouched


@pytest.mark.parametrize('case', ['default', 'strict-missing', 'peer-19', 'gate-unknown', 'type-tag'])
def test_restored_settings_keep_version_specific_null_and_type_policy(case):
    from investment_system.research.sector_qgv_restore import replay_saved_config
    config = default_config() if case == 'default' else custom_config()
    snapshot = json.loads(FIX.read_text())
    if case == 'strict-missing':
        snapshot['rows'][0]['observations'].pop('operating_margin_ttm')
    elif case == 'peer-19':
        snapshot['members'].pop()
        snapshot['rows'].pop()
    elif case == 'gate-unknown':
        snapshot['rows'][0]['gate'] = None
    elif case == 'type-tag':
        snapshot['rows'][0]['lynch_tags'] = ['FAST_GROWER']
    before = preview_qgv(config, snapshot, 'old-policy-context')
    saved = save_user_config(config, before, request_id=before['request_id'],
                             expected_preview_id=before['preview_id'])
    restored = replay_saved_config(saved, before, snapshot, 'restored-policy-context')['preview']
    assert restored['result_rows'] == before['result_rows']
    first = restored['result_rows'][0]
    if case in ('strict-missing', 'peer-19', 'gate-unknown'):
        assert first['total'] is None and first['rank'] is None
    if case == 'strict-missing':
        assert first['axes']['Q'] is None
    elif case == 'peer-19':
        assert first['factors']['operating_margin_ttm']['score_status'] == 'PEER_SAMPLE_SMALL'
    elif case == 'gate-unknown':
        assert first['gate_status'] == 'UNKNOWN'
    elif case == 'type-tag':
        assert first['nominal_axis_weights'] == {'Q': 6000, 'G': 2500, 'V': 1500}
        assert first['post_gate_axis_weights'] == {'Q': .6, 'G': .25, 'V': .15}


@pytest.mark.parametrize('conflict', ['missing-preview', 'missing-saved', 'explicit-config',
                                    'main-request', 'comparisons', 'other-mode'])
def test_cli_refuses_ambiguous_restore_jobs_before_writing(record, tmp_path, conflict):
    saved, retained, snapshot = record
    job = {'mode': 'normalized', 'data_kind': 'SYNTHETIC', 'request_id': 'refused-restore',
           'snapshot': write_json(tmp_path / 'snapshot.json', snapshot),
           'saved_config': write_json(tmp_path / 'saved.json', saved),
           'retained_preview': write_json(tmp_path / 'preview.json', retained)}
    if conflict == 'missing-preview':
        del job['retained_preview']
    elif conflict == 'missing-saved':
        del job['saved_config']
    elif conflict == 'explicit-config':
        job['config'] = default_config()
    elif conflict == 'main-request':
        job['main_request'] = {}
    elif conflict == 'comparisons':
        job['comparisons'] = True
    else:
        job['mode'] = 'v-resume'
    write_json(tmp_path / 'job.json', job)
    result = subprocess.run([sys.executable, str(CLI), '--job', str(tmp_path / 'job.json'),
                             '--output', str(tmp_path / 'refused'), '--synthetic'], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)['reason'] == 'SAVED_REPLAY_JOB_CONFLICT'
    assert not (tmp_path / 'refused').exists()


@pytest.mark.parametrize('key', ['model_version', 'engine_version', 'normalization_version',
                                'mapping_version', 'input_version', 'snapshot_id',
                                'universe_id', 'universe_version', 'valuation_date', 'as_of',
                                'config_hash', 'input_hash', 'cache_key', 'preview_id'])
def test_changed_retained_identity_cannot_be_replayed(record, key):
    from investment_system.research.sector_qgv_restore import replay_saved_config
    saved, retained, snapshot = record
    retained[key] += '-other'
    with pytest.raises(ValueError):
        replay_saved_config(saved, retained, snapshot, 'restore-refused')


@pytest.mark.parametrize('change', ['formula', 'input-version', 'same-id-value', 'filtered-members',
                                   'weights', 'preset', 'missing-policy', 'normalization', 'saved-context',
                                   'retained-result'])
def test_changed_saved_input_or_result_is_not_silently_rebased(record, change):
    from investment_system.research.sector_qgv_restore import replay_saved_config
    saved, retained, snapshot = record
    if change == 'formula':
        snapshot['rows'][0]['observations']['operating_margin_ttm']['formula_version'] = 'future'
    elif change == 'input-version':
        snapshot['input_version'] = 'new-version'
    elif change == 'same-id-value':
        snapshot['rows'][0]['observations']['operating_margin_ttm']['value'] += 1
    elif change == 'filtered-members':
        snapshot['members'].pop()
        snapshot['rows'].pop()
    elif change == 'weights':
        saved['config']['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']['axis_weights'] = {'Q': 3000, 'G': 4000, 'V': 3000}
    elif change == 'preset':
        saved['config']['base_preset_id'] = 'user-preset/balanced@0.1'
    elif change == 'missing-policy':
        saved['config']['missing_policy'] = 'legacy-renormalize'
    elif change == 'normalization':
        saved['config']['normalization_policy'] = 'legacy-industry-8'
    elif change == 'saved-context':
        saved['universe_version'] = 'other'
    else:
        retained['result_rows'][0]['total'] = 999
    with pytest.raises(ValueError):
        replay_saved_config(saved, retained, snapshot, 'restore-refused')


def test_legacy_profiles_restore_with_their_existing_api_and_remain_outside_sector(record):
    from investment_system.research.sector_qgv_restore import replay_saved_config
    script = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const root=process.argv[1],V=require(root+'/src/investment_system/product/web_assets/qgv-v2.js');
const D=require(root+'/src/investment_system/product/web_assets/device-profiles.js');
const input=JSON.parse(fs.readFileSync(root+'/tests/fixtures/qgv_v2_vectors_v1.json')).cases[0].input;
const ids=['user-preset/aggressive@0.1','user-preset/balanced@0.1','user-preset/defensive@0.1'];
const data=new Map(),storage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};
let doc=D.emptyV2();const results=[];
for(const [n,id] of ids.entries()){
 const candidate=V.userPreset(id);
 doc=D.saveV2(doc,{name:id,weights:candidate.weights,type_weights:n!==2,gate:n!==2},new Date('2026-11-01T00:00:0'+n+'Z'));
 const profile=doc.profiles.at(-1);
 results.push(V.scoreUniverse(input.companies,input.synthetic_market,{weights:profile.weights,typeWeights:profile.type_weights,gate:profile.gate}));
}
D.writeV2(storage,doc);const raw=storage.getItem(D.V2_KEY),restored=D.readV2(storage);
assert.deepEqual(restored,doc);assert.equal(storage.getItem(D.V2_KEY),raw);
for(const [n,p] of restored.profiles.entries()){
 assert.equal(p.name,ids[n]);assert.equal(p.version,1);
 assert.deepEqual(V.scoreUniverse(input.companies,input.synthetic_market,{weights:p.weights,typeWeights:p.type_weights,gate:p.gate}),results[n]);
}
process.stdout.write(JSON.stringify({ids,profiles:restored,unchanged:storage.getItem(D.V2_KEY)===raw}));
"""
    result = subprocess.run(['node', '-e', script, str(ROOT)], capture_output=True, text=True, check=True)
    restored = json.loads(result.stdout)
    assert restored['unchanged'] is True
    assert len(restored['profiles']['profiles']) == 3
    saved, retained, snapshot = record
    for candidate_id in restored['ids']:
        legacy = copy.deepcopy(saved)
        legacy['config']['base_preset_id'] = candidate_id
        with pytest.raises(ValueError, match='CONFIG_VERSION_MISMATCH:base_preset_id'):
            replay_saved_config(legacy, retained, snapshot, 'legacy-not-sector')
