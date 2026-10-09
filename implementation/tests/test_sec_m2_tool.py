"""The manually invoked CLI exports only to an explicitly supplied private file."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from investment_system.ingestion.sec_m1 import retain_input

CLOCK = datetime(2025, 5, 4, 12, tzinfo=timezone.utc)
SENTINEL = 'FINANCIAL_SECRET_SENTINEL_987654321'


def tool():
    path = Path(__file__).resolve().parents[1] / 'tools' / 'sec_m2_qg.py'
    assert path.is_file(), 'The explicitly invoked offline SEC M2 CLI is missing'
    spec = importlib.util.spec_from_file_location('sec_m2_tool_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(store):
    # CLI-owned synthetic files with two annual periods and a genuine numeric 0.
    facts = {'cik': 2488, 'facts': {'us-gaap': {}}}
    for concept, values in {'Revenues': [(2024, 880), (2023, 440)],
                            'FreeCashFlow': [(2024, 0)],
                            'EarningsPerShareDiluted': [(2024, 4), (2023, 2)]}.items():
        unit = 'USD/shares' if concept.startswith('Earnings') else 'USD'
        facts['facts']['us-gaap'][concept] = {'units': {unit: [
            {'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': value,
             'filed': '2025-04-01', 'form': '10-K', 'fy': year, 'fp': 'FY',
             'accn': '0000002488-25-000444'} for year, value in values]}}
    submissions = {'cik': '0000002488', 'filings': {'recent': {
        'form': ['10-K'], 'filingDate': ['2025-04-01'], 'accessionNumber': ['0000002488-25-000444'],
        'acceptanceDateTime': ['2025-04-01T19:00:00Z']}}}
    return retain_input(store, 'amd', json.dumps(facts).encode(), json.dumps(submissions).encode(), CLOCK, CLOCK)


def argv(store, receipt, output, *, input_kind='SYNTHETIC', as_of=CLOCK):
    return ['--store', str(store), '--receipt', receipt['receipt_id'], '--as-of', as_of.isoformat(),
            '--input-kind', input_kind, '--output', str(output)]


def freeze(module, monkeypatch):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return CLOCK if tz is not None else CLOCK.replace(tzinfo=None)
    monkeypatch.setattr(module, 'datetime', Frozen)


def test_private_export_0600_has_financial_values_only_in_output_file(tmp_path, capsys, monkeypatch):
    module = tool()
    store, output = tmp_path / 'store', tmp_path / 'private.json'
    receipt = source(store)
    freeze(module, monkeypatch)
    before = {p.relative_to(store): p.read_bytes() for p in store.rglob('*') if p.is_file()}
    assert module.main(argv(store, receipt, output)) == 0
    log = capsys.readouterr()
    summary = json.loads(log.out)
    assert summary['status'] == 'CANDIDATE_WRITTEN'
    assert summary['n_calculated'] == 1 and summary['n_unavailable'] == 0
    assert '880' not in log.out and not log.err
    assert str(output) not in log.out and str(store) not in log.out
    document = json.loads(output.read_bytes())
    assert document['companies']['amd']['normalized_financial_fields']['revenue'] == 880
    assert document['input_kind'] == 'SYNTHETIC'
    assert document['evaluated_at'] == CLOCK.isoformat()
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert before == {p.relative_to(store): p.read_bytes() for p in store.rglob('*') if p.is_file()}


def test_equal_private_output_is_idempotent_and_different_existing_output_is_not_overwritten(tmp_path, capsys, monkeypatch):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'candidate.json'
    freeze(module, monkeypatch)
    arguments = argv(tmp_path / 'store', receipt, output)
    assert module.main(arguments) == 0
    original = output.read_bytes()
    assert module.main(arguments) == 0
    assert output.read_bytes() == original
    output.write_text(SENTINEL)
    assert module.main(arguments) == 2
    assert output.read_text() == SENTINEL
    log = capsys.readouterr()
    assert SENTINEL not in log.out + log.err
    assert 'OUTPUT_EXISTS' in log.out


@pytest.mark.parametrize('marker', ['.git', 'public', 'cockpit', 'artifact'])
def test_git_and_public_cockpit_output_markers_are_rejected(tmp_path, capsys, marker):
    module = tool()
    receipt = source(tmp_path / 'store')
    parent = tmp_path / marker if marker in ('public', 'cockpit') else tmp_path / 'destination'
    parent.mkdir()
    if marker == '.git':
        (parent / '.git').write_text('gitdir: supplied-marker')
    if marker == 'artifact':
        (parent / 'index.html').write_text('cockpit artifact')
        (parent / 'data.json').write_text('{}')
    output = parent / 'candidate.json'
    assert module.main(argv(tmp_path / 'store', receipt, output)) == 2
    assert not output.exists()
    assert json.loads(capsys.readouterr().out)['status'] == 'UNSAFE_OUTPUT'


@pytest.mark.parametrize('kind', ['file_symlink', 'directory_symlink', 'traversal', 'inside_store', 'missing_parent'])
def test_unsafe_output_paths_are_rejected_without_side_effects(tmp_path, capsys, kind):
    module = tool()
    store = tmp_path / 'store'
    receipt = source(store)
    target = tmp_path / 'unchanged.json'
    target.write_text(SENTINEL)
    output = tmp_path / 'candidate.json'
    if kind == 'file_symlink':
        output.symlink_to(target)
    elif kind == 'directory_symlink':
        linked = tmp_path / 'linked'
        linked.symlink_to(tmp_path, target_is_directory=True)
        output = linked / 'candidate.json'
    elif kind == 'traversal':
        (tmp_path / 'sub').mkdir()
        output = tmp_path / 'sub' / '..' / 'candidate.json'
    elif kind == 'inside_store':
        output = store / 'candidate.json'
    else:
        output = tmp_path / 'absent' / 'candidate.json'
    assert module.main(argv(store, receipt, output)) == 2
    assert target.read_text() == SENTINEL
    assert not (tmp_path / 'absent').exists()
    assert 'UNSAFE_OUTPUT' in capsys.readouterr().out


@pytest.mark.parametrize('extra', [['--price', SENTINEL], ['--live'], ['--fetch'], ['--latest'],
                                  ['--now', SENTINEL], ['--token', SENTINEL], ['--unknown=' + SENTINEL]])
def test_unknown_options_are_fixed_code_only_and_never_echo_argv(tmp_path, capsys, extra):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    assert module.main(argv(tmp_path / 'store', receipt, output) + extra) == 2
    log = capsys.readouterr()
    assert json.loads(log.out) == {'status': 'INVALID_ARGUMENTS'}
    assert not log.err and SENTINEL not in log.out and str(tmp_path) not in log.out
    assert not output.exists()


@pytest.mark.parametrize('bad_time', ['2025-05-04', SENTINEL, '2025-05-04T12:00:00'])
def test_timestamp_parse_errors_do_not_expose_supplied_values(tmp_path, capsys, bad_time):
    module = tool()
    receipt = source(tmp_path / 'store')
    arguments = argv(tmp_path / 'store', receipt, tmp_path / 'private.json')
    arguments[arguments.index('--as-of') + 1] = bad_time
    assert module.main(arguments) == 2
    log = capsys.readouterr()
    assert json.loads(log.out) == {'status': 'INVALID_ARGUMENTS'}
    assert bad_time not in log.out + log.err


def test_clock_is_real_utc_and_future_cutoff_cannot_be_supplied_as_now(tmp_path, capsys, monkeypatch):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    freeze(module, monkeypatch)
    assert module.main(argv(tmp_path / 'store', receipt, output, as_of=CLOCK + timedelta(seconds=1))) == 2
    assert not output.exists()
    assert json.loads(capsys.readouterr().out) == {'status': 'INVALID_CLOCK'}


def test_observed_unverified_kind_is_explicit_and_does_not_grant_verification(tmp_path, capsys):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    assert module.main(argv(tmp_path / 'store', receipt, output, input_kind='OBSERVED_UNVERIFIED')) == 0
    result = json.loads(output.read_bytes())
    assert result['input_kind'] == 'OBSERVED_UNVERIFIED' and not result['synthetic_inputs']
    assert not result['real_data_verified'] and not result['publication_approved']
    assert not result['candidate_data']['qgv']['data']['amd']['synthetic']
    assert 'OBSERVED_UNVERIFIED' not in capsys.readouterr().out


def test_missing_required_input_kind_does_not_guess_from_m1_fixture(tmp_path, capsys):
    module = tool()
    receipt = source(tmp_path / 'store')
    arguments = argv(tmp_path / 'store', receipt, tmp_path / 'private.json')
    start = arguments.index('--input-kind')
    del arguments[start:start + 2]
    assert module.main(arguments) == 2
    assert json.loads(capsys.readouterr().out) == {'status': 'INVALID_ARGUMENTS'}


def test_unexpected_exception_does_not_echo_private_details(tmp_path, capsys, monkeypatch):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    def fail(*args, **kwargs):
        raise RuntimeError(SENTINEL + str(tmp_path))
    monkeypatch.setattr(module, 'analyze_receipts', fail)
    assert module.main(argv(tmp_path / 'store', receipt, output)) == 2
    assert json.loads(capsys.readouterr().out) == {'status': 'PROCESSING_FAILED'}
    assert not output.exists()


def test_partial_failure_report_retains_private_candidate_and_only_prints_codes(tmp_path, capsys):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    assert module.main(argv(tmp_path / 'store', receipt, output) + ['--receipt', 'f' * 64]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary['n_calculated'] == 1 and summary['n_unavailable'] == 1
    assert summary['results'][0]['status'] in ('CALCULATED', 'NOT_AVAILABLE')
    assert len(json.loads(output.read_bytes())['failures']) == 1


def test_executable_subprocess_exports_without_network_or_key_inputs(tmp_path):
    module = tool()
    receipt = source(tmp_path / 'store')
    output = tmp_path / 'private.json'
    process = subprocess.run([sys.executable, str(Path(module.__file__)), *argv(tmp_path / 'store', receipt, output)],
                             capture_output=True, text=True, check=False)
    assert process.returncode == 0 and not process.stderr
    assert json.loads(process.stdout)['n_calculated'] == 1
    assert json.loads(output.read_bytes())['prices_used'] is False
