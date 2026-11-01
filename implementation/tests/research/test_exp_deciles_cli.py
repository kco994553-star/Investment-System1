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
import subprocess
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
    """The synthetic bundle (research/exp_deciles/synthetic.py) written with its input manifest."""
    root.mkdir()
    for filename, data in syn.bundle_bytes():
        (root / filename).write_bytes(data)
    return root / 'manifest.json'


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
    assert 'stage=select' in out and 'first_build=true' in out and 'U_A=candidate:36 eligible:30 excluded:2 unknown:4' in out
    assert 'U_B=candidate:36 eligible:13 excluded:19 unknown:4' in out and 'strategy_cells_run=14' in out
    assert 'files=selection_inputs.json,manifest.json' in out
    assert_clean_stdout(out)
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a',
                         str(out18 / 'selection_inputs.json'), '--out', str(out19), '--generated-at', WHEN)
    assert code == 0, err
    assert 'first_build=false' in out and 'U_A=candidate:35 eligible:28 excluded:3 unknown:4' in out
    assert_clean_stdout(out)
    code, out, err = run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection',
                         str(out19 / 'selection_inputs.json'), '--selection', str(out18 / 'selection_inputs.json'),
                         '--out', str(ledger_dir), '--end', '2019-03-29', '--generated-at', WHEN)
    assert code == 0, err
    assert 'portfolios=30' in out and 'portfolios_run=30' in out and 'ledger_runs_by_status=COMPLETE:120' in out
    assert 'daily_coverage=DAILY_COVERAGE_COMPLETE:30' in out and 'settlement_conflicts=0' in out
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


def test_synthetic_bundle_runs_end_to_end_and_replays_byte_identically(cli, capsys, tmp_path):
    first, second = tmp_path / 'syn1', tmp_path / 'syn2'
    code, out1, err = run(cli, capsys, 'synthetic', '--out', str(first), '--generated-at', WHEN)
    assert code == 0, err
    assert 'synthetic=OK' in out1 and out1.count('verify=OK') == 4
    assert 'end_rule=NEXT_RESELECTION_T_OPEN' in out1 and 'end_valuation=OPEN' in out1
    assert_clean_stdout(out1)
    code, out2, err = run(cli, capsys, 'synthetic', '--out', str(second), '--generated-at', WHEN)
    assert code == 0, err
    hashes1 = [line for line in out1.splitlines() if 'manifest_sha256=' in line]
    hashes2 = [line for line in out2.splitlines() if 'manifest_sha256=' in line]
    assert len(hashes1) == 5 and hashes1 == hashes2
    for name in ('bundle', 'select-2018', 'select-2019', 'ledger-2018', 'ledger'):
        a, b = first / name, second / name
        assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir())
        for child in a.iterdir():
            assert child.read_bytes() == (b / child.name).read_bytes(), (name, child.name)
            assert stat.S_IMODE(os.stat(child).st_mode) == 0o600
    # a second run into the same directory is refused (never overwrites)
    code, _, err = run(cli, capsys, 'synthetic', '--out', str(first), '--generated-at', WHEN)
    assert code == 2 and 'OUTPUT_EXISTS' in err


def _select_2018(cli, capsys, manifest, out_dir):
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out', str(out_dir),
                       '--generated-at', WHEN)
    assert code == 0, err
    return out_dir / 'selection_inputs.json'


# ---- review F7: a selection file must verify against its select run's manifest ------------------------------------
def test_ledger_refuses_an_edited_or_unverified_selection_file(cli, capsys, tmp_path):
    """Review d9: a copy of the 2018 selection with AXIS_G/U_A's top pick replaced was replayed silently."""
    manifest = write_bundle(tmp_path / 'bundle')
    original = _select_2018(cli, capsys, manifest, tmp_path / 's18')
    payload = json.loads(original.read_text())
    sel = payload['selections']['AXIS_G']['U_A']
    sel['top'][0]['security_id'] = sel['order'][len(sel['order']) // 2]
    edited = tmp_path / 'edited'
    edited.mkdir(mode=0o700)
    (edited / 'selection_inputs.json').write_text(json.dumps(payload))
    (edited / 'manifest.json').write_bytes((tmp_path / 's18' / 'manifest.json').read_bytes())
    code, out, err = run(cli, capsys, 'verify', '--run', str(edited))
    assert code == 1 and 'verify=FAILED' in out
    args = ['ledger', '--manifest', str(manifest), '--out', str(tmp_path / 'led'), '--end', '2019-02-15']
    code, out, err = run(cli, capsys, *args, '--selection', str(edited / 'selection_inputs.json'))
    assert (code, out, err.strip()) == (2, '', 'REFUSED SELECTION_MANIFEST_MISMATCH')
    loose = tmp_path / 'loose'
    loose.mkdir(mode=0o700)
    (loose / 'selection_inputs.json').write_bytes(original.read_bytes())
    code, _, err = run(cli, capsys, *args, '--selection', str(loose / 'selection_inputs.json'))
    assert code == 2 and err.strip() == 'REFUSED SELECTION_MANIFEST_MISSING'
    assert not (tmp_path / 'led').exists()
    code, out, err = run(cli, capsys, *args, '--selection', str(original))
    assert code == 0, err


def test_ledger_flags_another_input_manifest_and_refuses_mixed_selection_code(cli, capsys, tmp_path, monkeypatch):
    manifest = write_bundle(tmp_path / 'bundle')
    s18 = _select_2018(cli, capsys, manifest, tmp_path / 's18')
    other = write_bundle(tmp_path / 'other')                     # same files, one more resource: another manifest
    body = json.loads(other.read_text())
    body['resources'].append(dict(body['resources'][0], name='records:2017'))
    other.write_text(json.dumps(body))
    code, out, err = run(cli, capsys, 'ledger', '--manifest', str(other), '--selection', str(s18), '--out',
                         str(tmp_path / 'led'), '--end', '2019-02-15', '--generated-at', WHEN)
    assert code == 0, err
    assert 'SELECTION_INPUT_MANIFEST_DIFFERS' in out
    assert 'SELECTION_INPUT_MANIFEST_DIFFERS' in json.loads((tmp_path / 'led' / 'ledger_outputs.json').read_text())[
        'flags']
    monkeypatch.setattr(cli, 'code_state', lambda: ('f' * 40, []))
    code, _, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a', str(s18),
                       '--out', str(tmp_path / 's19'), '--generated-at', WHEN)
    assert code == 0, err
    code, _, err = run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection', str(s18), '--selection',
                       str(tmp_path / 's19' / 'selection_inputs.json'), '--out', str(tmp_path / 'led2'),
                       '--end', '2019-03-29')
    assert code == 2 and err.strip() == 'REFUSED SELECTION_CODE_SHA_MISMATCH'


# ---- review F10: outputs never inside any git working tree --------------------------------------------------------
def _git(*args, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    ident = ['-c', 'user.name=synthetic', '-c', 'user.email=' + '@'.join(['synthetic', 'example.invalid'])]
    subprocess.run(['git', *ident, *args], cwd=cwd, env=env, check=True, capture_output=True)


def test_output_inside_any_git_working_tree_is_refused(cli, capsys, tmp_path, monkeypatch):
    """Review d5: run from a worktree, an --out inside the main checkout (another working tree) was accepted."""
    main_tree, worktree, unrelated = tmp_path / 'main', tmp_path / 'wt', tmp_path / 'unrelated'
    for tree in (main_tree, unrelated):
        tree.mkdir()
        _git('init', '-q', cwd=tree)
        _git('commit', '-q', '--allow-empty', '-m', 'synthetic', cwd=tree)
    _git('worktree', 'add', '-q', str(worktree), cwd=main_tree)
    (main_tree / 'implementation').mkdir()
    monkeypatch.setattr(cli, 'REPO_ROOT', worktree)
    with pytest.raises(cli.CliError, match='OUTPUT_INSIDE_REPO'):
        cli._output_dir(str(worktree / 'out'))
    with pytest.raises(cli.CliError, match='OUTPUT_INSIDE_REPO'):
        cli._output_dir(str(main_tree / 'implementation' / 'exp_private_out'))
    with pytest.raises(cli.CliError, match='OUTPUT_INSIDE_GIT_WORKTREE'):
        cli._output_dir(str(unrelated / 'out'))
    with pytest.raises(cli.CliError, match='OUTPUT_INSIDE_GIT_WORKTREE'):
        cli._output_dir(str(unrelated / '.git' / 'out'))
    assert cli._output_dir(str(tmp_path / 'outside')) == (tmp_path / 'outside').resolve()


# ---- review F11: settings body and reproduction command in the run block and the output manifest -----------------
def test_run_block_and_manifest_carry_settings_and_a_reproduction_command(cli, capsys, tmp_path):
    """Review d12: only settings_sha256 and no reproduction command were recorded."""
    manifest = write_bundle(tmp_path / 'bundle')
    s18 = _select_2018(cli, capsys, manifest, tmp_path / 's18')
    payload, written = json.loads(s18.read_text()), json.loads((tmp_path / 's18' / 'manifest.json').read_text())
    for block in (payload['run'], written):
        assert hashlib.sha256(json.dumps(block['settings'], sort_keys=True, separators=(',', ':'),
                                         ensure_ascii=True).encode()).hexdigest() == block['settings_sha256']
        assert block['reproduction']['argv'] == [
            'python', 'implementation/tools/exp_stock_indicator_deciles.py', 'select', '--manifest', '<INPUT_MANIFEST>',
            '--year', '2018', '--out', '<NEW_PRIVATE_OUTPUT_DIR>', '--generated-at', WHEN]
        assert block['reproduction']['placeholders']['INPUT_MANIFEST'] == {
            'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
        assert str(tmp_path) not in json.dumps(block['reproduction'])
    assert payload['run']['settings'] == written['settings'] and payload['settings_sha256'] == written['settings_sha256']
    code, out, _ = run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection', str(s18), '--out',
                       str(tmp_path / 'led'), '--generated-at', WHEN, '--daily-positions')
    assert code == 0 and 'end_rule=NEXT_RESELECTION_T_OPEN' in out and 'end_valuation=OPEN' in out
    led = json.loads((tmp_path / 'led' / 'manifest.json').read_text())
    digest = hashlib.sha256(s18.read_bytes()).hexdigest()
    assert led['reproduction']['argv'][5:] == ['--selection', '<SELECTION_2018>', '--daily-positions', '--out',
                                               '<NEW_PRIVATE_OUTPUT_DIR>', '--generated-at', WHEN]
    assert led['reproduction']['placeholders']['SELECTION_2018'] == {'sha256': digest}
    code, out, _ = run(cli, capsys, 'verify', '--run', str(tmp_path / 'led'))
    assert code == 0 and 'settings_ok=true' in out
    led['settings']['account']['cost_bps_per_side'] = '0'          # a changed settings body no longer verifies
    (tmp_path / 'led' / 'manifest.json').chmod(0o600)
    (tmp_path / 'led' / 'manifest.json').write_text(json.dumps(led))
    code, out, _ = run(cli, capsys, 'verify', '--run', str(tmp_path / 'led'))
    assert code == 1 and 'settings_ok=false' in out


# ---- review F3: the previous U-A state forms ----------------------------------------------------------------------
def test_previous_u_a_as_object_or_bare_list(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    s18 = json.loads(_select_2018(cli, capsys, manifest, tmp_path / 's18').read_text())
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'members': s18['universe']['U_A']['members'],
                                 'unknown': s18['universe']['U_A']['unknown']}))
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a',
                         str(state), '--out', str(tmp_path / 'a'), '--generated-at', WHEN)
    assert code == 0 and 'PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED' not in out, err
    bare = tmp_path / 'bare.json'
    bare.write_text(json.dumps(s18['universe']['U_A']['members']))
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2019', '--previous-u-a',
                         str(bare), '--out', str(tmp_path / 'b'), '--generated-at', WHEN)
    assert code == 0 and 'flags=PREVIOUS_U_A_UNKNOWN_SET_NOT_SUPPLIED' in out, err


# ---- review d8: CLI text never carries a security ID or a price, refusals included ---------------------------------
def test_cli_text_never_carries_security_ids_or_prices_including_refusals(cli, capsys, tmp_path):
    manifest = write_bundle(tmp_path / 'bundle')
    texts = []
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out',
                         str(tmp_path / 's18'), '--generated-at', WHEN)
    texts.append(out + err)
    code, out, err = run(cli, capsys, 'select', '--manifest', str(manifest), '--year', '2018', '--out',
                         str(tmp_path / 's18'), '--generated-at', WHEN)
    assert code == 2 and err.strip() == 'REFUSED OUTPUT_EXISTS'
    texts.append(out + err)
    prices = tmp_path / 'bundle' / 'prices.json'
    prices.write_bytes(prices.read_bytes()[:-2] + bytes([prices.read_bytes()[-2] ^ 1]) + prices.read_bytes()[-1:])
    code, out, err = run(cli, capsys, 'ledger', '--manifest', str(manifest), '--selection',
                         str(tmp_path / 's18' / 'selection_inputs.json'), '--out', str(tmp_path / 'led'))
    assert code == 2 and err.strip() == 'REFUSED MANIFEST_HASH_MISMATCH'
    texts.append(out + err)
    for text in texts:
        assert_clean_stdout(text)
