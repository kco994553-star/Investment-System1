"""Git-only recovery, isolated corrections and byte-stable appended views."""
from copy import deepcopy
import gzip
import json

import pytest

from investment_system.research import kis_stock_journal as journal
from investment_system.research._private_artifacts import json_bytes
from investment_system.universe.sec_universe_shares import universe_codes
from test_kis_rebuild import inputs, sha


def stage(root, files):
    for path, value in files:
        target = root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == value
        else:
            target.write_bytes(value)


def make_capture(source, state, config, root, head=None, revision=None):
    patch = journal.changes(source, state, config, revision)
    files, head = journal.archive_files(config, patch, head, revision)
    stage(root, files.items())
    return patch, head


def test_restore_from_git_objects_after_loss_of_every_serving_file(tmp_path):
    req, contract = inputs(tmp_path/'ingest')
    root = tmp_path/'source'
    config = json.loads(req.read_bytes())
    for key in ('financial','symbols'):
        stage(root, [(config[key]['path'], (req.parent/config[key]['path']).read_bytes())])
    code = universe_codes()[0]
    assert journal.main(['append','--source-root',str(root),'--request',str(req),
                         '--request-sha256',sha(req.read_bytes()),'--check-only']) == 0
    _, bootstrap = make_capture({code:contract}, {}, config, root)
    config, state = journal.replay(root, bootstrap)
    assert journal.Contracts(state,'RAW')[code] == contract
    first = dict(journal.generation(journal.Contracts(state,'RAW'), config, bootstrap, root))
    # Publication files never enter the source checkout; CLI restore has no --request.
    rebuilt = tmp_path/'restored'
    assert journal.main(['restore','--source-root',str(root),'--head',bootstrap['path'],
                         '--head-sha256',bootstrap['sha256'],'--check-only']) == 0
    journal.write_bundle(journal.generation(journal.Contracts(state,'RAW'), config, bootstrap, root), rebuilt)
    assert {str(p.relative_to(rebuilt)):p.read_bytes() for p in rebuilt.rglob('*') if p.is_file()} == first
    manifest = json.loads(first['generation.json'])
    data = json.loads(gzip.decompress(first[manifest['stocks']['SYN']['path']]))
    assert len(data['rows']) == 5 and data['rows'][-1][:7] == ['2026-10-23','10','12','9','11','100','1100']
    assert len(data['rows'][-1]) == 17 and all(v is None for v in data['rows'][-1][7:])
    pointer = json.loads(next(b for k,b in first.items() if k.startswith('query-refs/')))
    assert len(json_bytes(pointer)) < 3072 and pointer['generation']['sha256'] == sha(first['generation.json'])
    blob = root / json.loads((root/bootstrap['path']).read_bytes())['parts'][0]['path']
    blob.write_bytes(blob.read_bytes()+b' ')
    with pytest.raises(ValueError, match='STOCK_ARCHIVE_PIN'):
        journal.replay(root, bootstrap)


def test_appending_ignores_repeated_history_and_reuses_past_view_rows(tmp_path):
    req, contract = inputs(tmp_path/'ingest')
    config = json.loads(req.read_bytes())
    code = universe_codes()[0]
    _, bootstrap = make_capture({code:contract}, {}, config, tmp_path)
    config, state = journal.replay(tmp_path, bootstrap)
    previous,_ = journal.project_stock(contract,config,code)
    config.update(evaluation_day='2026-10-26',calculated_at='2026-10-27T04:00:00Z')
    more = deepcopy(contract)
    more['collected_at'] = config['calculated_at']
    more['raw_bars'][0]['source_sha256'] = '1'*64  # repeated provider window
    row = dict(more['raw_bars'][-1],date=config['evaluation_day'],collected_at=more['collected_at'])
    more['raw_bars'].append(row)
    more['bars'] = deepcopy(more['raw_bars'])
    more['price_basis_date'] = row['date']
    old_objects = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    patch, head = make_capture({code:more}, state, config, tmp_path, bootstrap)
    assert len(patch[code]['rows']) == 1
    assert all(p.read_bytes() == value for p,value in old_objects.items())
    assert (tmp_path/head['path']).stat().st_size < 3072
    _, merged = journal.replay(tmp_path, head)
    actual = journal.Contracts(merged,'RAW')[code]
    assert actual['raw_bars'][0] == contract['raw_bars'][0]
    appended, reused = journal.project_stock(actual, config, code, previous=previous)
    recovered,_ = journal.project_stock(actual, config, code)
    assert reused == 5 and appended == recovered


def test_correction_rebuilds_one_response_and_requires_review(tmp_path):
    req, contract = inputs(tmp_path/'ingest')
    config = json.loads(req.read_bytes())
    code = universe_codes()[0]
    original = deepcopy(contract)
    second = deepcopy(contract)
    second['symbol'] = 'SYNB'
    second['source_query']['SYMB'] = 'SYNB'
    both = {code:original,'SECOND':second}
    source = req.parent
    _, head = make_capture(both, {}, config, source)
    _, state = journal.replay(source, head)
    views = dict(journal.generation(journal.Contracts(state,'RAW'),config,head,source))
    old = tmp_path/'views'
    stage(old,views.items())
    correction = deepcopy(both)
    correction[code]['raw_bars'][0]['close'] = '10'
    correction[code]['bars'] = deepcopy(correction[code]['raw_bars'])
    with pytest.raises(ValueError,match='JOURNAL_REVISION_REFERENCE_REQUIRED'):
        journal.changes(correction,state,config,None)
    _, revised = make_capture(correction,state,config,source,head,'SYNTHETIC_REVIEW')
    _, state = journal.replay(source,revised)
    counts = {}
    output = dict(journal.generation(journal.Contracts(state,'RAW'),config,revised,source,
        previous=(old,journal.ref('generation.json',views['generation.json'])),stats=counts))
    assert counts['stock_written'] == 1 and counts['stock_full_history'] == 1 and counts['stock_unchanged'] == 1
    manifest = json.loads(output['generation.json'])
    corrected = json.loads(gzip.decompress(output[manifest['stocks']['SYN']['path']]))
    assert corrected['rows'][0][4] == '10'
    before = json.loads(views['generation.json'])
    assert before['stocks']['SYNB'] == manifest['stocks']['SYNB']

def test_confirmed_split_keeps_raw_rows_and_rebuilds_affected_history(tmp_path):
    req, contract = inputs(tmp_path/'ingest')
    config = json.loads(req.read_bytes())
    code = universe_codes()[0]
    _, head = make_capture({code:contract}, {}, config, tmp_path)
    _, state = journal.replay(tmp_path, head)
    before, _ = journal.project_stock(contract, config, code)
    adjusted = deepcopy(contract)
    adjusted['splits'] = [dict(date=config['evaluation_day'], ratio='2', status='CONFIRMED',
                               evidence='SYNTHETIC_FILE', security_id=adjusted['security_id'])]
    adjusted['basis'] = 'SPLIT_ADJUSTED'
    adjusted['bars'] = journal.price_rows(adjusted, config['evaluation_day'])
    config['price_basis'] = 'SPLIT_ADJUSTED'
    patches, revised = make_capture({code:adjusted}, state, config, tmp_path, head, 'SYNTHETIC_SPLIT')
    assert patches[code]['rows'] == []
    _, state = journal.replay(tmp_path, revised)
    response, reused = journal.project_stock(journal.Contracts(state, 'SPLIT_ADJUSTED')[code], config,
                                             code, previous=before)
    assert reused == 0
    assert response['rows'][0][4] == '5.5' and response['raw_rows'][0][4] == '11'
    assert response['rows'][-1][4] == response['raw_rows'][-1][4] == '11'
