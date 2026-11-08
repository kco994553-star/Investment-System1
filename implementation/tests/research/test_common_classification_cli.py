from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from test_common_classification_qgv import inputs
from investment_system.research.sector_qgv import default_config,preview_qgv,save_user_config
from investment_system.research.sector_qgv_restore import replay_saved_config

SPEC=importlib.util.spec_from_file_location('common_classification_cli',Path(__file__).parents[2]/'tools/common_classification.py')
CLI=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(CLI)


def job(tmp):
    snapshot,store,view=inputs();config=default_config();before=preview_qgv(config,snapshot,'retained-synthetic')
    saved=save_user_config(config,before,request_id=before['request_id'],expected_preview_id=before['preview_id'])
    specs={}
    for key,value in [('snapshot',snapshot),('classification_store',store),('retained_preview',before),('saved_config',saved)]:
        body=json.dumps(value).encode();p=tmp/(key+'.json');p.write_bytes(body)
        specs[key]={'path':str(p),'sha256':hashlib.sha256(body).hexdigest()}
    return {'schema_version':'common-classification-job/1','data_kind':'SYNTHETIC','request_id':'synthetic-projection',
            'knowledge_as_of':view['knowledge_as_of'],**specs}


def test_offline_end_to_end_keeps_denominator_reuses_baseline_and_is_private_by_default(tmp_path):
    spec=job(tmp_path); output=tmp_path/'output'
    summary=CLI.run(spec,output,synthetic=True)
    assert summary['classification']['member_codes']==20
    assert summary['qg_comparison']['Q']['changed_common']==0
    assert summary['qg_comparison']['G']['changed_common']==0
    assert summary['technical']['verified_security_ids']==0
    assert summary['price_availability']['valid'] is None
    assert summary['gate_alternative']['applied'] is False
    read=lambda name:json.loads((output/name).read_text())
    restored=replay_saved_config(read('saved-config.json'),read('qgv-preview.json'),read('qgv-input.json'),'synthetic-restored')
    assert restored['preview']['result_rows']==read('qgv-preview.json')['result_rows']
    assert read('reference-saved-config.json')==json.loads(Path(spec['saved_config']['path']).read_text())
    links=read('qgv-classification-links.json')
    assert links['preview_identity']['input_hash']==read('qgv-preview.json')['input_hash']
    assert {r['classification_record_id'] for r in links['rows']}=={r['record_id'] for r in read('classification-view.json')['rows']}
    for f in json.loads((output/'manifest.json').read_text())['files']:
        p=output/f['path']; assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256']
        assert p.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'): CLI.run(spec,output,synthetic=True)


def test_hash_and_data_kind_fail_before_any_output(tmp_path):
    spec=job(tmp_path)
    with pytest.raises(ValueError,match='JOB_DATA_KIND_MISMATCH'): CLI.run(spec,tmp_path/'wrong')
    spec['snapshot']['sha256']='0'*64
    with pytest.raises(ValueError,match='INPUT_HASH_MISMATCH'): CLI.run(spec,tmp_path/'bad',synthetic=True)
    assert not (tmp_path/'bad').exists()


def test_saved_configuration_not_silently_migrated(tmp_path):
    spec=job(tmp_path);p=Path(spec['saved_config']['path'])
    data=json.loads(p.read_text());data['universe_version']='changed'
    p.write_text(json.dumps(data));spec['saved_config']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='SAVED_CONFIG_REFERENCE_MISMATCH'):
        CLI.run(spec,tmp_path/'changed',synthetic=True)
