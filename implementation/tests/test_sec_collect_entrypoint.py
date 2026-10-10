"""No provider requests or real credentials: entrypoint uses a supplied factory."""
import importlib.util
import json
from pathlib import Path

import pytest

from tests.test_sec_m1_receipts import AT, payloads


def tool():
    path = Path(__file__).resolve().parents[1] / 'tools/sec_collect_inputs.py'
    spec = importlib.util.spec_from_file_location('sec_collect_entrypoint_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mock_entrypoint_preserves_existing_store_without_credential_output(tmp_path, capsys):
    m = tool()
    seen = []

    class Client:
        def __init__(self, user_agent):
            seen.append(bool(user_agent))

        def collect(self, company_id, cik):
            return *payloads(), AT

    assert m.main(['--companies', 'nvda', '--store', str(tmp_path), '--live'],
                  environ={'SEC_USER_AGENT': 'synthetic-credential-canary'}, client_factory=Client) == 0
    output = capsys.readouterr()
    assert 'synthetic-credential-canary' not in output.out + output.err
    assert seen == [True]
    assert json.loads(output.out)['n_ready'] == 1


def test_live_opt_in_and_approved_scope_precede_requests(tmp_path, capsys):
    m = tool()

    def forbidden(*args):
        pytest.fail('Invalid execution reached client')

    for extra in ([], ['--live', '--companies', 'hanmi']):
        args = ['--store', str(tmp_path)]
        args += ['--companies', 'nvda'] if not extra else []
        with pytest.raises(SystemExit) as caught:
            m.main(args + extra, environ={}, client_factory=forbidden)
        assert caught.value.code == 2
    assert not list(tmp_path.iterdir())


def test_missing_setting_has_static_error_and_no_fallback(tmp_path, capsys):
    m = tool()
    with pytest.raises(SystemExit) as caught:
        m.main(['--companies', 'nvda', '--store', str(tmp_path), '--live'], environ={})
    assert caught.value.code == 2
    assert 'SEC_USER_AGENT' in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_unsupported_credential_flag_does_not_echo_its_value(tmp_path, capsys):
    m = tool()
    with pytest.raises(SystemExit):
        m.main(['--companies', 'nvda', '--store', str(tmp_path), '--live',
                '--user-agent', 'synthetic-cli-secret-canary'], environ={})
    output = capsys.readouterr()
    assert 'synthetic-cli-secret-canary' not in output.out + output.err


def test_all_us17_is_explicit_and_company_failures_are_isolated(tmp_path, capsys):
    m = tool()
    companies = []

    class Client:
        def __init__(self, user_agent):
            pass

        def collect(self, company_id, cik):
            companies.append(company_id)
            raise ValueError('synthetic-private-error-canary')

    assert m.main(['--all-us17', '--store', str(tmp_path), '--live'], environ={}, client_factory=Client) == 1
    output = capsys.readouterr()
    assert len(companies) == 17 and companies == list(m.US_LISTINGS)
    assert 'synthetic-private-error-canary' not in output.out + output.err
    assert json.loads(output.out)['n_failed'] == 17
