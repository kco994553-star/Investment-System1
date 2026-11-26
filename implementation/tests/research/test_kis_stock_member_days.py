"""Source-clock replay and complete generation materialization with synthetic listings."""
from copy import deepcopy
import gzip
import json

import pytest

from investment_system.research import kis_stock_journal as journal
from investment_system.research._private_artifacts import json_bytes
from investment_system.universe.sec_universe_shares import universe_codes
from test_kis_rebuild import inputs, sha
from test_kis_stock_journal import make_capture, stage


def files_at(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_append_pins_member_clocks_and_cli_restores_complete_generation(tmp_path, capsys, monkeypatch):
    req, _ = inputs(tmp_path / 'inputs')
    source = req.parent
    code = universe_codes()[0]
    conf = json.loads(req.read_bytes())
    day = conf['evaluation_day']
    path = tmp_path / 'days.json'
    path.write_bytes(json_bytes({code: day}))

    def append(head, *, mode=True, expected=None):
        args = ['append', '--source-root', str(source), '--request', str(req), '--request-sha256', sha(req.read_bytes())]
        if head:
            args.extend(['--head', head['path'], '--head-sha256', head['sha256']])
        if mode:
            args.extend(['--per-code-days', str(path), '--per-code-days-sha256', sha(path.read_bytes())])
        if expected:
            assert journal.main(args + ['--check-only']) == 2
            assert json.loads(capsys.readouterr().out)['reason'] == expected
            return
        dest = tmp_path / 'incoming' / str(len(list(source.glob('captures/*'))))
        assert journal.main(args + ['--output-dir', str(dest)]) == 0
        stage(source, files_at(dest).items())
        return json.loads(capsys.readouterr().out)['capture']

    def restore(head, dest, cache=None):
        args = ['restore', '--source-root', str(source), '--head', head['path'], '--head-sha256', head['sha256']]
        if cache:
            manifest = cache / 'generation.json'
            args.extend(['--previous-view', str(manifest), '--previous-view-sha256', sha(manifest.read_bytes())])
        assert journal.main(args + ['--output-dir', str(dest)]) == 0
        return json.loads(capsys.readouterr().out)

    bad_pin = ['append', '--source-root', str(source), '--request', str(req), '--request-sha256', sha(req.read_bytes()),
               '--per-code-days', str(path), '--per-code-days-sha256', '0' * 64, '--check-only']
    assert journal.main(bad_pin) == 2 and 'STOCK_DAY_MAP_PIN' in capsys.readouterr().out
    path.write_bytes(b'{"X":"2026-10-23","X":"2026-10-26"}')
    append(None, expected='STOCK_DAY_ROSTER')
    path.write_bytes(json_bytes({code: day}))
    legacy = append(None, mode=False)
    restore(legacy, tmp_path / 'legacy')
    enrolled = append(legacy)
    assert journal.parse(source, enrolled)['schema'] == journal.MEMBER_JOURNAL
    first = tmp_path / 'first'
    assert restore(enrolled, first, tmp_path / 'legacy')['stock_written'] == 1
    conf.update(evaluation_day='2026-10-26', calculated_at='2026-10-27T04:00:00Z')
    req.write_bytes(json_bytes(conf))
    append(enrolled, mode=False, expected='JOURNAL_MEMBER_CLOCK_REQUIRED')
    for invalid, reason in [({}, 'STOCK_DAY_ROSTER'), (None, 'STOCK_DAY_ROSTER'),
                            ({code: '2026-10-22'}, 'STOCK_MEMBER_DAY_BOUNDS'),
                            ({code: '2026-10-27'}, 'STOCK_MEMBER_DAY_BOUNDS'),
                            ({code: '2026-10-25'}, 'STOCK_MEMBER_DAY_SESSION')]:
        path.write_bytes(json_bytes(invalid))
        append(enrolled, expected=reason)
    path.write_bytes(json_bytes({code: day}))
    later = append(enrolled)
    assert journal.parse(source, later)['parts'] == []  # No duplicate clock or data patch.
    path.unlink()  # The source checkout alone now binds the complete clocks.
    cold = tmp_path / 'cold'
    restore(later, cold)
    warm = tmp_path / 'warm'
    real_compress = gzip.compress

    def forbid_stock_compression(raw, **kwargs):
        assert json.loads(raw)['schema'] != 'kis-stock-view/1'
        return real_compress(raw, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(journal.gzip, 'compress', forbid_stock_compression)
        patch.setattr(journal, 'project_stock', lambda *a, **kw: pytest.fail('cached member recalculated'))
        stats = restore(later, warm, first)
    assert (stats['stock_written'], stats['stock_unchanged']) == (0, 1)
    assert files_at(warm) == files_at(cold)
    manifest = json.loads((cold / 'generation.json').read_bytes())
    entry = manifest['stocks']['SYN']
    old_entry = json.loads((first / 'generation.json').read_bytes())['stocks']['SYN']
    assert entry == old_entry
    assert entry['code'] == code and entry['evaluation_day'] == entry['retained_end'] == day
    assert manifest['evaluation_day'] == '2026-10-26'
    assert json.loads(gzip.decompress((warm / manifest['qgv']['path']).read_bytes()))['price_basis_date'] == '2026-10-26'

    # Advance a time-sensitive member without changing any original bar.
    path.write_bytes(json_bytes({code: conf['evaluation_day']}))
    recalc = append(later)
    dest = tmp_path / 'recalculated'
    assert restore(recalc, dest, warm)['stock_written'] == 1
    entry = json.loads((dest / 'generation.json').read_bytes())['stocks']['SYN']
    member = json.loads(gzip.decompress((dest / entry['path']).read_bytes()))
    assert member['evaluation_day'] == conf['evaluation_day'] and entry['retained_end'] == day
    assert member['input_sha256'] != old_entry['input_sha256']


def test_changed_inputs_never_substitute_stale_member(tmp_path, monkeypatch):
    req, first = inputs(tmp_path / 'inputs')
    second = deepcopy(first)
    second['symbol'] = second['source_query']['SYMB'] = 'SYNB'
    source = req.parent
    config = json.loads(req.read_bytes())
    day = config['evaluation_day']
    contracts = {'NASDAQ:SYN': first, 'NASDAQ:SYNB': second}
    config['stock_evaluation_days'] = {code: day for code in contracts}
    _, head = make_capture(contracts, {}, config, source)
    old = tmp_path / 'old'
    prior = dict(journal.generation(contracts, config, head, source))
    stage(old, prior.items())
    previous = old, journal.ref('generation.json', prior['generation.json'])
    original = json.loads(prior['generation.json'])['stocks']

    def verify(current, cfg=config, catalog=None, written=1):
        stats = {}
        args = (current, cfg, head, source)
        warm = dict(journal.generation(*args, previous=previous, stats=stats, catalog=catalog))
        assert stats['stock_written'] == written and stats['stock_unchanged'] == len(contracts) - written
        assert warm == dict(journal.generation(*args, catalog=catalog))
        stocks = json.loads(warm['generation.json'])['stocks']
        if written == 1:
            assert stocks['SYNB'] == original['SYNB'] and warm[stocks['SYNB']['path']] == prior[original['SYNB']['path']]
        assert stocks['SYN']['input_sha256'] != original['SYN']['input_sha256']
        return json.loads(gzip.decompress(warm[stocks['SYN']['path']]))

    correction = deepcopy(contracts)
    for field in ('raw_bars', 'bars'):
        correction['NASDAQ:SYN'][field][0]['close'] = '10'
    assert verify(correction)['rows'][0][4] == '10'
    identity = deepcopy(contracts)
    identity['NASDAQ:SYN']['identity']['identity_reference'] = 'SYNTHETIC_REVIEW'
    assert verify(identity)['chart']['identity']['identity_reference'] == 'SYNTHETIC_REVIEW'
    event = dict(kind='SPINOFF_PARENT_UNCHANGED', date=day, cik='0000000001', url='https://example.invalid/notice')
    assert verify(contracts, catalog={'NASDAQ:SYN': [event]})['chart']['action_markers'][0]['evidence'] == event
    newer = deepcopy(contracts)
    series = newer['NASDAQ:SYN']
    series['collected_at'] = '2026-10-27T04:00:00Z'
    row = dict(series['raw_bars'][-1], date='2026-10-26', collected_at=series['collected_at'])
    series['raw_bars'].append(row)
    series['bars'] = deepcopy(series['raw_bars'])
    series['price_basis_date'] = row['date']
    cfg = dict(config, evaluation_day=row['date'], calculated_at=series['collected_at'],
               stock_evaluation_days={'NASDAQ:SYN': row['date'], 'NASDAQ:SYNB': day})
    assert verify(newer, cfg)['rows'][-1][0] == row['date']
    monkeypatch.setitem(journal.JUMP_POLICY, 'version', 'synthetic-policy/2')
    assert verify(contracts, written=2)['chart']['display']['screen_policy']['version'] == 'synthetic-policy/2'


@pytest.mark.parametrize('damage, reason', [('gzip', 'STOCK_ARCHIVE_PIN'), ('json', 'STOCK_MEMBER_JSON_PIN'),
                                           ('day', 'STOCK_MEMBER_BINDING'), ('stale', 'STOCK_MEMBER_BINDING')])
def test_invalid_cached_object_cannot_enter_new_generation(tmp_path, damage, reason):
    req, contract = inputs(tmp_path / 'inputs')
    config = json.loads(req.read_bytes())
    contracts = {'NASDAQ:SYN': contract}
    config['stock_evaluation_days'] = {'NASDAQ:SYN': config['evaluation_day']}
    _, head = make_capture(contracts, {}, config, req.parent)
    output = dict(journal.generation(contracts, config, head, req.parent))
    manifest = json.loads(output['generation.json'])
    entry = manifest['stocks']['SYN']
    if damage == 'gzip':
        output[entry['path']] += b'!'
    elif damage == 'json':
        entry['json_sha256'] = '0' * 64
    elif damage == 'day':
        entry['evaluation_day'] = '2026-10-22'
    else:
        # Even if a cache entry advertises today's hash, yesterday's member binds its own inputs.
        contracts['NASDAQ:SYN'] = dict(contract, issuer_id='0000000002')
        current = dict(journal.generation(contracts, config, head, req.parent))
        entry['input_sha256'] = json.loads(current['generation.json'])['stocks']['SYN']['input_sha256']
    output['generation.json'] = json_bytes(manifest)
    old = tmp_path / 'old'
    stage(old, output.items())
    previous = old, journal.ref('generation.json', output['generation.json'])
    with pytest.raises(ValueError, match=reason):
        list(journal.generation(contracts, config, head, req.parent, previous=previous))


def test_cached_empty_member_requires_explicit_retained_end(tmp_path, capsys):
    req, contract = inputs(tmp_path / 'inputs')
    config = json.loads(req.read_bytes())
    code = universe_codes()[0]
    config['stock_evaluation_days'] = {code: config['evaluation_day']}
    contract.update(bars=[], raw_bars=[], price_basis_date=None)
    _, head = make_capture({code: contract}, {}, config, req.parent)
    restore = ['restore', '--source-root', str(req.parent), '--head', head['path'], '--head-sha256', head['sha256']]
    cache = tmp_path / 'cache'
    assert journal.main(restore + ['--output-dir', str(cache)]) == 0
    capsys.readouterr()
    path = cache / 'generation.json'
    manifest = json.loads(path.read_bytes())
    entry = manifest['stocks']['SYN']
    view = json.loads(gzip.decompress((cache / entry['path']).read_bytes()))
    assert view['coverage']['retained_end'] is entry['retained_end'] is None
    previous = ['--previous-view', str(path), '--previous-view-sha256']
    assert journal.main(restore + previous + [sha(path.read_bytes()), '--check-only']) == 0
    assert json.loads(capsys.readouterr().out)['stock_unchanged'] == 1

    del view['coverage']
    for fields in [{}, {'coverage': {}}, {'coverage': None}, {'coverage': []}]:
        # Re-pin the changed bytes to reach the member binding check during restore.
        raw = json_bytes({**view, **fields})
        compressed = gzip.compress(raw, mtime=0)
        member_path = f'stock/{sha(compressed)}.json.gz'
        (cache / member_path).write_bytes(compressed)
        entry.update(journal.ref(member_path, compressed), json_bytes=len(raw), json_sha256=sha(raw))
        path.write_bytes(json_bytes(manifest))
        dest = tmp_path / 'rejected'
        assert journal.main(restore + previous + [sha(path.read_bytes()), '--output-dir', str(dest)]) == 2
        assert json.loads(capsys.readouterr().out)['reason'] == 'STOCK_MEMBER_BINDING'
        assert not dest.exists()


def test_complete_manifest_is_the_only_larger_staged_file(tmp_path, monkeypatch, capsys):
    req, contract = inputs(tmp_path / 'inputs')
    config = json.loads(req.read_bytes())
    config['stock_evaluation_days'] = {'NASDAQ:SYN': config['evaluation_day']}
    _, head = make_capture({'NASDAQ:SYN': contract}, {}, config, req.parent)
    args = ['restore', '--source-root', str(req.parent), '--head', head['path'], '--head-sha256', head['sha256']]
    large = b'x' * (journal.MAX_BYTES + 1)
    for name, status in [('generation.json', 0), ('stock/object.json.gz', 2)]:
        monkeypatch.setattr(journal, 'generation', lambda *a, **kw: iter([(name, large)]))
        assert journal.main(args + ['--check-only']) == status
        dest = tmp_path / ('stage' + str(status))
        assert journal.main(args + ['--output-dir', str(dest)]) == status
        assert dest.exists() == (status == 0)
    assert 'OUTPUT_FILE_LIMIT' in capsys.readouterr().out
