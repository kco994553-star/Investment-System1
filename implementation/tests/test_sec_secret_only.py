"""Legacy convenience fetches use the injected SEC contact only; never send a fallback."""
import pytest


@pytest.mark.parametrize('module,function', [
    ('sec_companyfacts', 'try_fetch_companyfacts'), ('sec_submissions', 'fetch_submissions'),
])
def test_missing_contact_never_sends_a_request(monkeypatch, module, function):
    from importlib import import_module
    provider = import_module('investment_system.providers.' + module)
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    sent = []
    monkeypatch.setattr(provider, 'urlopen', lambda *a, **k: sent.append(a))
    assert getattr(provider, function)('123') is None
    assert sent == []


@pytest.mark.parametrize('module,function', [
    ('sec_companyfacts', 'try_fetch_companyfacts'), ('sec_submissions', 'fetch_submissions'),
])
def test_contact_comes_only_from_secret_slot(monkeypatch, module, function):
    from importlib import import_module
    import io
    provider = import_module('investment_system.providers.' + module)
    monkeypatch.setenv('SEC_USER_AGENT', 'SYNTHETIC_RUNTIME_CONTACT')
    sent = []
    def open_response(request, **kwargs):
        sent.append(request.get_header('User-agent'))
        return io.BytesIO(b'{}')
    monkeypatch.setattr(provider, 'urlopen', open_response)
    assert getattr(provider, function)('123') == {}
    assert sent == ['SYNTHETIC_RUNTIME_CONTACT']
