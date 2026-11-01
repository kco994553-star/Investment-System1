"""CLI (implementation/tools/exp_stock_indicator_deciles.py): manifest hash refusal, output location and O_EXCL refusals,
byte-identical replay, verify, and stdout that never carries prices or security IDs. Synthetic bundle in tmp_path only."""
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import uuid

import pytest

import exp_deciles_synthetic as syn

IMPL = Path(__file__).resolve().parents[2]
TOOL = IMPL / 'tools' / 'exp_stock_indicator_deciles.py'
WHEN = '2026-11-01T00:00:00Z'


@pytest.fixture(scope='module')
def cli():
    spec = importlib.util.spec_from_file_location('exp_stock_indicator_deciles_cli', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dumps(value):
    """JSON with Decimals written as exact JSON numbers (the CLI must read them without float)."""
    def encode(o):
        if isinstance(o, Decimal):
            return f'@@D{o}@@'
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        raise TypeError(type(o).__name__)
    return re.sub(r'"@@D([-0-9.E+]+)@@"', r'\1', json.dumps(value, default=encode, sort_keys=True)).encode()


def write_bundle(root):
    root.mkdir()
    files = {
        'records:2018': ('records_2018.json', {'signal_day': '2018-02-16', 'records': syn.records(2018)}),
        'records:2019': ('records_2019.json', {'signal_day': '2019-02-15', 'records': syn.records(2019)}),
        'quotes:2018': ('quotes_2018.json', {'signal_day': '2018-02-16', 'quotes': syn.quotes(2018)}),
        'quotes:2019': ('quotes_2019.json', {'signal_day': '2019-02-15', 'quotes': syn.quotes(2019)}),
        'filings': ('filings.json', syn.filing_rows()),
        'prices': ('prices.json', syn.price_rows()),
        'events': ('events.json', syn.event_rows()),
        'tr_series': ('tr.json', {'label': 'S&P 500 Total Return Index', 'claim': 'SP500_TR', 'source': 'synthetic',
                                  'rows': syn.tr_rows()}),
    }
    facts = syn.companyfacts_by_cik()
    for key in sorted(facts)[:3]:                      # three issuers as one-CIK files, the rest as one mapping file
        files[f'companyfacts:{key}'] = (f'cf_{key}.json', facts.pop(key))
    files['companyfacts:rest'] = ('cf_rest.json', facts)
    resources = []
    for name, (filename, payload) in files.items():
        data = _dumps(payload)
        (root / filename).write_bytes(data)
        resources.append({'name': name, 'path': filename, 'sha256': hashlib.sha256(data).hexdigest(),
                          'source': 'synthetic generator', 'period': '2018-02-16..2019-03-29',
                          'rights_note': 'synthetic test data, no third-party rights'})
    manifest = root / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'exp-deciles-input-manifest/1',
                                    'experiment_id': 'EXP-STOCK-INDICATOR-DECILES-v1', 'resources': resources}))
    return manifest


def run(cli, capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def assert_clean_stdout(out):
    assert not any(text in out for text in syn.sentinel_prices())
    assert 'XQ' not in out and not re.search(r'\d\.\d', out)


def test_schedule_prints_dates_only_and_exits_zero(cli, capsys):
    code, out, _ = run(cli, capsys, 'schedule')
    assert code == 0 and 'schedule=OK' in out and 'rows=10' in out
    assert '2018 third_monday=2018-02-19 S=2018-02-16 T=2018-02-20 filing_cutoff=2018-02-08' in out
    assert not re.search(r'\d\.\d', out)


def test_schedule_mismatch_exits_one(cli, capsys, monkeypatch):
    monkeypatch.setattr(cli.schedule, 'verify_frozen', lambda: {
        'ok': False, 'rows': [], 'sha256': '0' * 64,
        'mismatches': [{'year': 2018, 'field': 'S', 'frozen': '2018-02-15', 'computed': '2018-02-16'}]})
    code, out, _ = run(cli, capsys, 'schedule')
    assert code == 1 and 'schedule=MISMATCH' in out and 'mismatches=1' in out


def test_select_ledger_verify_end_to_end_with_byte_identical_replay(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    out18, out19, ledger_dir = tmp_path / 'sel2018', tmp_path / 'sel2019', tmp_path / 'ledger'
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out18),
                         '--generated-at', WHEN)
    assert code == 0, err
    assert 'stage=select' in out and 'first_build=true' in out and 'U_A=candidate:19 eligible:15 excluded:2 unknown:2' in out
    assert 'files=selection_inputs.json,manifest.json' in out
    assert_clean_stdout(out)
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a',
                         str(out18 / 'selection_inputs.json'), '--out', str(out19), '--generated-at', WHEN)
    assert code == 0, err
    assert 'first_build=false' in out and 'U_A=candidate:19 eligible:14 excluded:3 unknown:2' in out
    assert_clean_stdout(out)
    code, out, err = run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection',
                         str(out19 / 'selection_inputs.json'), '--selection', str(out18 / 'selection_inputs.json'),
                         '--out', str(ledger_dir), '--end', '2019-03-29', '--generated-at', WHEN)
    assert code == 0, err
    assert 'portfolios=30' in out and 'portfolios_run=6' in out and 'ledger_runs_by_status=COMPLETE:24' in out
    assert 'external_total_return=COMPLETE' in out
    assert_clean_stdout(out)
    # private modes: directory 0700, files 0600
    for directory in (out18, out19, ledger_dir):
        assert stat.S_IMODE(os.stat(directory).st_mode) == 0o700
        for child in directory.iterdir():
            assert stat.S_IMODE(os.stat(child).st_mode) == 0o600
    # manifests: run identity, inputs, extra inputs, files
    m18 = json.loads((out18 / 'manifest.json').read_text())
    m19 = json.loads((out19 / 'manifest.json').read_text())
    sel19 = json.loads((out19 / 'selection_inputs.json').read_text())
    assert m18['generated_at'] == WHEN and len(m18['run_id']) == 24 and m18['run_id'] != m19['run_id']
    assert m18['input_manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}|UNKNOWN', m18['code_sha'])
    assert m18['outputs'][0]['file'] == 'selection_inputs.json'
    assert m18['outputs'][0]['sha256'] == hashlib.sha256((out18 / 'selection_inputs.json').read_bytes()).hexdigest()
    assert {r['name'] for r in m18['inputs']} >= {'records:2018', 'prices', 'companyfacts:rest'}
    assert m19['extra_inputs'] == [{'role': 'previous_u_a', 'sha256': hashlib.sha256(
        (out18 / 'selection_inputs.json').read_bytes()).hexdigest()}]
    assert sel19['run']['run_id'] == m19['run_id'] and sel19['previous_u_a'] == json.loads(
        (out18 / 'selection_inputs.json').read_text())['universe']['U_A']['members']
    # replay with the same --generated-at: byte-identical files and run_id
    replay18, replay_ledger = tmp_path / 'replay2018', tmp_path / 'replay_ledger'
    assert run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(replay18),
               '--generated-at', WHEN)[0] == 0
    assert run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection', str(out18 / 'selection_inputs.json'),
               '--selection', str(out19 / 'selection_inputs.json'), '--out', str(replay_ledger), '--end', '2019-03-29',
               '--generated-at', WHEN)[0] == 0
    for a, b in ((out18, replay18), (ledger_dir, replay_ledger)):
        assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir())
        for child in a.iterdir():
            assert child.read_bytes() == (b / child.name).read_bytes(), child.name
    # verify: OK, then a changed output is found
    code, out, _ = run(cli, capsys, 'verify', '--run', str(ledger_dir))
    assert code == 0 and 'verify=OK' in out and 'run_id_ok=true' in out
    target = ledger_dir / 'ledger_outputs.json'
    target.write_bytes(target.read_bytes().replace(b'"COMPLETE"', b'"INCOMPLETE"', 1))
    code, out, _ = run(cli, capsys, 'verify', '--run', str(ledger_dir))
    assert code == 1 and 'verify=FAILED' in out and 'file ledger_outputs.json HASH_MISMATCH' in out


def test_manifest_hash_mismatch_is_refused_before_any_output(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    prices = tmp_path / 'bundle' / 'prices.json'
    prices.write_bytes(prices.read_bytes().replace(b'"RAW"', b'"ADJ"', 1))       # changed after the manifest
    out_dir = tmp_path / 'out'
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out_dir))
    assert (code, out, err.strip()) == (2, '', 'REFUSED MANIFEST_HASH_MISMATCH')
    assert not out_dir.exists()
    missing = write_bundle(tmp_path / 'bundle2')
    (tmp_path / 'bundle2' / 'events.json').unlink()
    code, _, err = run(cli, capsys, 'select', '--manifest', str(missing), '--year', '2018', '--out', str(out_dir))
    assert code == 2 and err.strip() == 'REFUSED MANIFEST_RESOURCE_MISSING'


def test_output_inside_the_repository_is_refused(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    inside = IMPL / f'exp-deciles-out-{uuid.uuid4().hex}'
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(inside))
    assert (code, out, err.strip()) == (2, '', 'REFUSED OUTPUT_INSIDE_REPO')
    assert not inside.exists()
    code, _, err = run(cli, capsys, 'verify', '--run', str(tmp_path / 'nowhere'))
    assert code == 2 and err.strip() == 'REFUSED RUN_DIR_MISSING'


def test_existing_output_files_are_never_overwritten(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    out_dir = tmp_path / 'out'
    assert run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out_dir),
               '--generated-at', WHEN)[0] == 0
    before = {p.name: p.read_bytes() for p in out_dir.iterdir()}
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out_dir),
                       '--generated-at', '2026-11-02T00:00:00Z')
    assert code == 2 and err.strip() == 'REFUSED OUTPUT_EXISTS'
    assert {p.name: p.read_bytes() for p in out_dir.iterdir()} == before
    # the write itself is O_EXCL: a file appearing after the early check is still not replaced
    with pytest.raises(cli.CliError, match='OUTPUT_EXISTS'):
        cli._write_outputs(out_dir, [('manifest.json', b'other')])
    assert (out_dir / 'manifest.json').read_bytes() == before['manifest.json']
    # an existing directory open to others is refused
    shared = tmp_path / 'shared'
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(shared))
    assert code == 2 and err.strip() == 'REFUSED OUTPUT_DIR_UNSAFE' and not any(shared.iterdir())


def test_previous_u_a_of_another_year_and_bad_arguments_are_refused(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    wrong = tmp_path / 'previous.json'
    wrong.write_text(json.dumps({'schema': 'exp-deciles-selection-inputs/1', 'year': 2017}))
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a',
                       str(wrong), '--out', str(tmp_path / 'out'))
    assert code == 2 and err.strip() == 'REFUSED PREVIOUS_U_A_YEAR_MISMATCH'
    secret = str(tmp_path / 'private-location')
    code, out, err = run(cli, capsys, 'select', '--manifest', secret)            # --year and --out missing
    assert (code, out, err.strip()) == (2, '', 'REFUSED INVALID_ARGUMENTS') and secret not in err
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2016', '--out',
                       str(tmp_path / 'out'))
    assert code == 2 and err.strip() == 'REFUSED YEAR_NOT_IN_FROZEN_SCHEDULE'


def test_unknown_code_sha_is_flagged_and_missing_inputs_are_refused(cli, capsys, tmp_path, monkeypatch):
    manifest = write_bundle(tmp_path / 'bundle')
    monkeypatch.setattr(cli, 'code_state', lambda: (None, []))
    out_dir = tmp_path / 'out'
    code, out, _ = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out_dir),
                       '--generated-at', WHEN)
    assert code == 0 and 'flags=CODE_SHA_UNKNOWN' in out
    written = json.loads((out_dir / 'manifest.json').read_text())
    assert (written['code_sha'], written['code_sha_flags']) == ('UNKNOWN', ['CODE_SHA_UNKNOWN'])
    body = json.loads(manifest.read_text())
    body['resources'] = [r for r in body['resources'] if r['name'] != 'prices']
    no_prices = tmp_path / 'bundle' / 'no_prices.json'
    no_prices.write_text(json.dumps(body))
    code, _, err = run(cli, capsys, 'ledger', '--manifest', str(no_prices), '--selection',
                       str(out_dir / 'selection_inputs.json'), '--out', str(tmp_path / 'ledger'))
    assert code == 2 and err.strip() == 'REFUSED PRICES_NOT_SUPPLIED'
