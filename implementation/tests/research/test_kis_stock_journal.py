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
    daily = json.loads((tmp_path/head['path']).read_bytes())
    assert daily['schema'] == 'kis-stock-journal/1' and len(daily['parts']) == 1
    assert 'parts_index' not in daily
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


def test_large_parented_append_uses_pinned_parts_index_and_replays(monkeypatch, tmp_path):
    req, _ = inputs(tmp_path/'ingest')
    config = json.loads(req.read_bytes())
    _, parent = make_capture({}, {}, config, tmp_path)
    # Reproduce the real append's 16-way split with small, disjoint fixtures.
    patches = {f'SYN{i}': dict(header={}, remove=[], rows=[]) for i in range(16)}
    parts = [gzip.compress(json_bytes({code: patch}), mtime=0) for code, patch in patches.items()]
    monkeypatch.setattr(journal, 'patch_files', lambda *a, **kw: iter(parts))
    files, child = journal.archive_files(config, patches, parent, 'SYNTHETIC_REVIEW')
    stage(tmp_path, files.items())
    frame = json.loads(files[child['path']])
    assert child['bytes'] <= 3072 and len(files) == 18
    index = frame['parts_index']
    saved = json.loads(gzip.decompress(files[index['path']]))
    assert len(saved) == 16 and len({part['sha256'] for part in saved}) == 16
    _, restored = journal.replay(tmp_path, child)
    assert set(restored) == set(patches)
    # A subsequent small capture stays inline and can replay an indexed ancestor.
    monkeypatch.setattr(journal, 'patch_files', lambda *a, **kw: iter(()))
    next_files, next_head = journal.archive_files(config, {}, child)
    assert json.loads(next_files[next_head['path']])['schema'] == 'kis-stock-journal/1'
    assert len(next_files) == 1
    stage(tmp_path, next_files.items())
    assert journal.replay(tmp_path, next_head)[1] == restored
    index_path = tmp_path / index['path']
    index_path.write_bytes(index_path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='STOCK_ARCHIVE_PIN'):
        journal.replay(tmp_path, next_head)


def test_document_and_consecutive_raw_step_set_chart_basis(tmp_path, monkeypatch):
    from investment_system.research import kis_chart_actions as actions
    req, c = inputs(tmp_path/'ingest')
    day = '2026-10-23'
    for r in c['raw_bars'][:-1]:
        r.update(open='30', high='36', low='27', close='33')
    c['raw_bars'][-1]['open'] = '11'
    c['bars'] = deepcopy(c['raw_bars'])
    event = dict(kind='SPLIT', cik='0000000001', date=day, new_shares=3, old_shares=1,
                 url='https://example.invalid/filing', sha256='a'*64)
    monkeypatch.setattr(actions, 'reviewed_actions', lambda: {'NASDAQ:SYN':[event]})
    original = deepcopy(c)
    view, _ = journal.project_stock(c, json.loads(req.read_bytes()), 'NASDAQ:SYN')
    assert c == original
    assert view['coverage'] == dict(scope='ALL_RETAINED_SESSIONS', retained_sessions=5,
        retained_start='2026-10-19', retained_end=day,
        applied_splits=[dict(effective_day=day, new_per_old='3', evidence=event)])
    evidence = view['latest']['technical']['evidence']
    assert (evidence['adjustment_start'], evidence['adjustment_end'], evidence['adjustment_reference']) == (
        '2026-10-22', day, event['url'])
    assert evidence['adjustment_range_scope'] == 'LATEST_REVIEWED_EVENT_STEP'
    assert view['chart']['confirmed_ranges'] == original['confirmed_ranges'] == []
    assert all(m['value'] is None for m in view['latest']['technical']['metrics'].values())
    assert view['rows'][0][1:7] == ['10','12','9','11','300','1100']
    assert view['raw_rows'][0][4:6] == ['33','100']
    assert view['rows'][-1][:7] == view['raw_rows'][-1]
    assert actions.chart_basis(c,'NASDAQ:SYN','2026-10-22')[0]['basis'] == 'RAW'
    wrong_class, marks = actions.chart_basis(c,'NASDAQ:SYN.B',day)
    assert wrong_class['basis'] == 'RAW' and marks[0]['state'] == 'EVIDENCE_OR_RAW_STEP_UNCONFIRMED'
    event['new_shares'] = 10
    assert actions.chart_basis(c,'NASDAQ:SYN',day)[0]['basis'] == 'RAW'
    event['kind'] = 'SPINOFF_PARENT_UNCHANGED'
    base, marks = actions.chart_basis(c,'NASDAQ:SYN',day)
    assert base['basis'] == 'RAW' and marks[0]['state'] == 'NON_SPLIT_DISTRIBUTION'
    c['source_query']['MODP'] = '1'
    with pytest.raises(ValueError,match='RAW_DAILY_SOURCE_REQUIRED'):
        actions.chart_basis(c,'NASDAQ:SYN',day)


def test_reverse_split_exact_fraction_and_declared_raw_boundary(tmp_path, monkeypatch):
    from investment_system.research import kis_chart_actions as actions
    from decimal import Decimal, localcontext
    _, c = inputs(tmp_path/'ingest')
    for r in c['raw_bars'][:-1]:
        r.update(open='3',high='4',low='2',close='3.5',volume='300')
    c['bars'] = deepcopy(c['raw_bars'])
    day = c['price_basis_date']
    c['splits'] = [dict(date=day, ratio='2', status='CONFIRMED', evidence='SYNTHETIC')]
    monkeypatch.setattr(actions,'reviewed_actions',lambda:{})
    assert actions.chart_basis(c,'NASDAQ:SYN',day)[0]['basis'] == 'RAW'
    event = dict(kind='SPLIT', cik='0000000001', date=day, new_shares=1, old_shares=3, url='https://example.invalid/reverse')
    monkeypatch.setattr(actions,'reviewed_actions',lambda:{'NASDAQ:SYN':[event]})
    with pytest.raises(ValueError,match='SPLIT_RATIO_CONFLICT'):
        actions.chart_basis(c,'NASDAQ:SYN',day)
    c['splits'] = []
    out, _ = actions.chart_basis(c,'NASDAQ:SYN',day)
    assert out['bars'][0]['close'] == '10.5' and out['bars'][0]['volume'] == '100'
    with localcontext() as ctx:
        ctx.prec = 50
        assert out['splits'][0]['ratio'] == str(Decimal(1)/3)
    for name in ('bars','raw_bars'):
        del c[name][-2]
    base, marks = actions.chart_basis(c,'NASDAQ:SYN',day)
    assert base['basis'] == 'RAW' and marks[0]['state'] == 'EVIDENCE_OR_RAW_STEP_UNCONFIRMED'


def test_supplemental_fund_split_requires_its_provider_venue(tmp_path):
    from investment_system.research.kis_chart_actions import chart_basis, merge_reviewed_actions

    _, contract = inputs(tmp_path / 'input')
    day = contract['price_basis_date']
    for bar in contract['raw_bars'][:-1]:
        bar.update(open='20', high='22', low='18', close='20')
    contract['bars'] = deepcopy(contract['raw_bars'])
    code = 'ETF:SYN'
    event = dict(kind='SPLIT', date=day, new_shares=2, old_shares=1, cik='0000000001',
                 provider_excd='NAS', url='https://example.invalid/split', sha256='a'*64, locator='Synthetic fund notice')
    register = dict(schema='reviewed-chart-actions/1', listings={code: [event]})
    catalog = merge_reviewed_actions(register)
    chart, _ = chart_basis(contract, code, day, entries=catalog[code])
    assert chart['basis'] == 'SPLIT_ADJUSTED'
    for wrong_code, wrong_event in [('ETF:OTHER', event), (code, dict(event, provider_excd='AMS'))]:
        assert chart_basis(contract, wrong_code, day, entries=[wrong_event])[0]['basis'] == 'RAW'
    contract['issuer_id'] = '0000000002'
    assert chart_basis(contract, code, day, entries=[event])[0]['basis'] == 'RAW'
    with pytest.raises(ValueError, match='REVIEWED_ACTION_DATE'):
        merge_reviewed_actions(dict(register, listings={code: [event, event]}))
    with pytest.raises(ValueError, match='REVIEWED_ACTION_RATIO'):
        merge_reviewed_actions(dict(register, listings={code: [dict(event, old_shares=0)]}))


def test_documented_price_move_releases_only_matching_step_in_stock_reference(tmp_path):
    req, contract = inputs(tmp_path / 'input')
    config = json.loads(req.read_bytes())
    day = contract['price_basis_date']
    bar = contract['raw_bars'][-1]
    bar.update(open='16', high='25', low='14', close='22')
    contract['bars'] = deepcopy(contract['raw_bars'])
    old = contract['raw_bars'][-2]
    event = dict(kind='DOCUMENTED_MARKET_MOVE', date=day, cik='0000000001', provider_excd='NAS',
                 raw_step_sha256=journal.digest([old['date'], old['close'], day, bar['open'], bar['close']]),
                 url='https://example.invalid/report', sha256='b'*64, locator='Synthetic issuer notice')
    view, _ = journal.project_stock(contract, config, 'NASDAQ:SYN', entries=[event])
    assert view['chart']['display']['state'] == 'AVAILABLE'
    assert view['chart']['action_markers'][-1]['state'] == 'DOCUMENTED_MARKET_MOVE'
    assert view['chart']['basis'] == 'RAW' and view['coverage']['applied_splits'] == []
    assert all(metric['value'] is None for metric in view['latest']['technical']['metrics'].values())
    contract['held_ranges'] = [dict(**{'from':day, 'to':day}, reason='INDEPENDENT_HOLD', evidence='SYNTHETIC')]
    view, _ = journal.project_stock(contract, config, 'NASDAQ:SYN', entries=[event])
    assert view['chart']['display']['hold_reasons'] == ['INDEPENDENT_HOLD']
    contract['raw_bars'][-1]['open'] = '17'
    contract['bars'] = deepcopy(contract['raw_bars'])
    view, _ = journal.project_stock(contract, config, 'NASDAQ:SYN', entries=[event])
    assert 'RAW_SPLIT_LIKE_JUMP_REVIEW_REQUIRED' in view['chart']['display']['hold_reasons']


def test_supplemental_register_is_pinned_and_changes_cached_generation(tmp_path, capsys):
    req, contract = inputs(tmp_path / 'input')
    config = json.loads(req.read_bytes())
    code = 'ETF:SYN'
    for bar in contract['raw_bars'][:-1]:
        bar.update(open='20', high='22', low='18', close='20')
    contract['bars'] = deepcopy(contract['raw_bars'])
    source = req.parent
    _, head = make_capture({code:contract}, {}, config, source)
    common = ['restore', '--source-root', str(source), '--head', head['path'], '--head-sha256', head['sha256']]
    old = tmp_path / 'old'
    baseline = dict(journal.generation({code:contract}, config, head, source))
    stage(old, baseline.items())
    event = dict(kind='SPLIT', date=config['evaluation_day'], new_shares=2, old_shares=1,
                 provider_excd='NAS', cik='0000000001', url='https://example.invalid/notice',
                 sha256='c'*64, locator='Synthetic issuer notice')
    path = tmp_path / 'register.json'
    path.write_bytes(json_bytes(dict(schema='reviewed-chart-actions/1', listings={code:[event]})))
    failed = common + ['--check-only', '--reviewed-actions', str(path), '--reviewed-actions-sha256', '0'*64]
    assert journal.main(failed) == 2
    assert 'REVIEWED_ACTIONS_PIN' in capsys.readouterr().out
    manifest = old / 'generation.json'
    assert journal.main(common + ['--check-only', '--reviewed-actions', str(path),
        '--reviewed-actions-sha256', sha(path.read_bytes()), '--previous-view', str(manifest),
        '--previous-view-sha256', sha(manifest.read_bytes())]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats['stock_written'] == 1 and stats['stock_full_history'] == 1 and stats['stock_unchanged'] == 0
    # Reusing the unchanged QGV emits one stock, one manifest and one query reference.
    assert stats['files'] == 3
