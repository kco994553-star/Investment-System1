"""Synthetic SEC transport contracts; no live requests or environment lookup."""

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.error import HTTPError

import pytest

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import (
    MAX_BODY_BYTES,
    SEC_USER_AGENT_SLOT,
    SecCollectionClient,
    SecCollectionError,
    SecResponse,
    default_transport,
)


START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
UA = "Synthetic collector contact@example.com"
CIK = US_LISTINGS["nvda"]["cik"]
FACTS = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
SUBMISSIONS = f"https://data.sec.gov/submissions/CIK{CIK}.json"


class Clock:
    def __init__(self):
        self.elapsed = 0.0
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds

    def monotonic(self):
        return self.elapsed

    def now(self):
        return START + timedelta(seconds=self.elapsed)


def body(cik=CIK):
    return json.dumps({"cik": cik, "facts": {}, "filings": {"recent": {}}}).encode()


def setup(responses=None, **overrides):
    clock = Clock()
    calls = []
    responses = iter(responses or [])

    def transport(url, **kwargs):
        calls.append((url, clock.elapsed, kwargs))
        value = next(responses, None)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value(url)
        return value if value is not None else SecResponse(200, body(), final_url=url)

    client = SecCollectionClient(
        UA, transport=transport, sleep=clock.sleep,
        monotonic=clock.monotonic, now=clock.now, **overrides,
    )
    return client, clock, calls


def test_fixed_urls_private_headers_and_acquisition_after_both_responses():
    client, clock, calls = setup()
    facts, submissions, acquired = client.collect("nvda", CIK)
    assert facts == submissions == body()
    assert [call[0] for call in calls] == [FACTS, SUBMISSIONS]
    assert [call[1] for call in calls] == pytest.approx([0, 0.2])
    assert acquired == clock.now() and acquired.tzinfo is timezone.utc
    assert calls[0][2] == {"headers": {"User-Agent": UA, "Accept": "application/json"},
                            "timeout": 20.0, "max_body_bytes": MAX_BODY_BYTES}


@pytest.mark.parametrize("company,cik", [("aapl", CIK), ("hanmi", CIK),
                                        ("nvda", "0000320193"), ("NVDA", CIK),
                                        ("nvda", int(CIK))])
def test_company_cik_pair_fails_before_transport(company, cik):
    client, _, calls = setup()
    with pytest.raises(SecCollectionError, match="SEC_ISSUER_NOT_ALLOWED"):
        client.collect(company, cik)
    assert calls == []


@pytest.mark.parametrize("ua", [None, "", "research", "owner@example.com",
                               "Research contact@example.invalid", "Research\ncontact@example.com",
                               "Research\rcontact@example.com", "Research \u2603 contact@example.com"])
def test_user_agent_is_required_descriptive_ascii_and_value_free_on_failure(ua):
    with pytest.raises(SecCollectionError, match="SEC_USER_AGENT_INVALID") as error:
        SecCollectionClient(ua)
    assert str(error.value) == "SEC_USER_AGENT_INVALID"


def test_client_and_response_repr_do_not_expose_contact_or_payload():
    client, _, _ = setup()
    assert UA not in repr(client)
    assert "contact@example.com" not in repr(client)
    assert "SYNTHETIC_SECRET_CANARY" not in repr(SecResponse(200, b"SYNTHETIC_SECRET_CANARY"))


def test_rate_limit_applies_across_issuer_calls():
    client, _, calls = setup()
    client.collect("nvda", CIK)
    client.collect("nvda", CIK)
    assert [call[1] for call in calls] == pytest.approx([0, 0.2, 0.4, 0.6])


@pytest.mark.parametrize("clock_kind", ["unchanged", "backwards"])
def test_clock_or_sleeper_cannot_bypass_minimum_interval(clock_kind):
    client, clock, calls = setup()
    if clock_kind == "unchanged":
        client._sleep = lambda seconds: None
    else:
        client._monotonic = iter([0, -1]).__next__
    with pytest.raises(SecCollectionError, match="SEC_CLOCK_INVALID"):
        client.collect("nvda", CIK)
    assert len(calls) == 1


def test_injected_collection_error_cannot_leak_its_arbitrary_message():
    client, _, calls = setup([SecCollectionError("SYNTHETIC_SECRET_CANARY")])
    with pytest.raises(SecCollectionError, match="SEC_TRANSPORT_FAILED") as error:
        client.collect("nvda", CIK)
    assert "SYNTHETIC_SECRET_CANARY" not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__
    assert len(calls) == 1


def test_http_retry_exhaustion_does_not_request_submissions():
    client, clock, calls = setup([lambda url: SecResponse(429, b"", final_url=url)] * 5)
    with pytest.raises(SecCollectionError, match="SEC_HTTP_RETRIES_EXHAUSTED") as caught:
        client.collect("nvda", CIK)
    assert caught.value.http_status == 429 and caught.value.stage == "fetch"
    assert len(calls) == 5 and all(call[0] == FACTS for call in calls)
    assert clock.sleeps == [2, 4, 8, 16]


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_http_response_retries_and_rate_limits_each_attempt(status):
    client, clock, calls = setup([lambda url: SecResponse(status, b"", final_url=url)])
    client.collect("nvda", CIK)
    assert [call[0] for call in calls] == [FACTS, FACTS, SUBMISSIONS]
    assert clock.sleeps == pytest.approx([2, 0.2])
    assert all(after[1] - before[1] >= 0.199999 for before, after in zip(calls, calls[1:]))


@pytest.mark.parametrize("status", [400, 401, 403, 404, 501])
def test_nontransient_http_status_does_not_retry_or_leak_body(status):
    client, clock, calls = setup([lambda url: SecResponse(status, b"SYNTHETIC_SECRET_CANARY", final_url=url)])
    with pytest.raises(SecCollectionError) as error:
        client.collect("nvda", CIK)
    assert str(error.value) == f"SEC_HTTP_{status}"
    assert len(calls) == 1 and clock.sleeps == []


def test_retry_limit_and_backoff_are_bounded_with_safe_exception():
    client, clock, calls = setup([TimeoutError("SYNTHETIC_SECRET_CANARY")] * 5)
    with pytest.raises(SecCollectionError) as error:
        client.collect("nvda", CIK)
    assert str(error.value) == "SEC_TRANSPORT_RETRIES_EXHAUSTED"
    assert "SYNTHETIC_SECRET_CANARY" not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__
    assert len(calls) == 5 and clock.sleeps == [2, 4, 8, 16]


@pytest.mark.parametrize("retry_after,expected", [("12", 12), ("0", 2), ("1.5", 2),
                                                 ("broken", 2), ("-1", 2)])
def test_retry_after_seconds_or_invalid_header(retry_after, expected):
    client, clock, _ = setup([lambda url: SecResponse(429, b"", retry_after, url)])
    client.collect("nvda", CIK)
    assert clock.sleeps[0] == expected


def test_retry_after_http_date_is_honored():
    header = format_datetime(START + timedelta(seconds=20), usegmt=True)
    client, clock, _ = setup([lambda url: SecResponse(503, b"", header, url)])
    client.collect("nvda", CIK)
    assert clock.sleeps[0] == 20


@pytest.mark.parametrize("header", ["61", format_datetime(START + timedelta(seconds=61), usegmt=True)])
def test_retry_after_above_budget_stops_without_shortened_retry(header):
    client, clock, calls = setup([lambda url: SecResponse(429, b"", header, url)])
    with pytest.raises(SecCollectionError, match="SEC_RETRY_AFTER_EXCEEDS_BUDGET"):
        client.collect("nvda", CIK)
    assert len(calls) == 1 and clock.sleeps == []


@pytest.mark.parametrize("url", [None, "https://data.sec.gov/submissions/CIK0000320193.json",
                                 "https://example.com/private?token=SYNTHETIC_SECRET_CANARY"])
def test_mismatched_final_url_rejected_without_retry(url):
    client, _, calls = setup([SecResponse(200, body(), final_url=url)])
    with pytest.raises(SecCollectionError, match="SEC_RESPONSE_URL_MISMATCH"):
        client.collect("nvda", CIK)
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b'{"cik":true}',
                                     b'{"cik":"0000320193"}',
                                     '{"cik":"０００１０４５８１０"}'.encode(),
                                     b'{"cik":"1045810"}',
                                     b'{"cik":1045810,"value":NaN}',
                                     b'{"cik":1045810,"value":1e999}',
                                     b'{"cik":1045810,"cik":320193}'])
def test_invalid_json_nonfinite_or_unbound_identity_is_rejected(payload):
    client, _, calls = setup([lambda url: SecResponse(200, payload, final_url=url)])
    with pytest.raises(SecCollectionError):
        client.collect("nvda", CIK)
    assert len(calls) == 1


def test_integer_cik_identity_is_accepted():
    client, _, _ = setup([lambda url: SecResponse(200, body(int(CIK)), final_url=url)])
    assert json.loads(client.collect("nvda", CIK)[0])["cik"] == int(CIK)


def test_body_bound_applies_to_injected_transport():
    client, _, calls = setup([lambda url: SecResponse(200, b"x" * (MAX_BODY_BYTES + 1), final_url=url)])
    with pytest.raises(SecCollectionError, match="SEC_RESPONSE_TOO_LARGE"):
        client.collect("nvda", CIK)
    assert len(calls) == 1


def test_timezone_aware_capture_is_required_after_both_requests():
    client, _, calls = setup()
    client._now = lambda: datetime(2026, 1, 1)
    with pytest.raises(SecCollectionError, match="SEC_CLOCK_INVALID"):
        client.collect("nvda", CIK)
    assert len(calls) == 2


def test_module_import_does_not_read_environment_or_send_requests(monkeypatch):
    import os
    import urllib.request
    import investment_system.providers.sec_collection as module

    def forbidden(*args, **kwargs):
        raise AssertionError("import attempted environment/network access")

    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(os.environ, "get", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    spec = importlib.util.spec_from_file_location(
        "investment_system.providers.sec_collection_import_contract", module.__file__)
    fresh = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, fresh)
    spec.loader.exec_module(fresh)
    assert fresh.SEC_USER_AGENT_SLOT == SEC_USER_AGENT_SLOT == "SEC_USER_AGENT"


def test_default_transport_rejects_nonsec_url_before_open(monkeypatch):
    import investment_system.providers.sec_collection as module
    monkeypatch.setattr(module, "build_opener", lambda *args: pytest.fail("blocked URL opened"))
    with pytest.raises(SecCollectionError, match="SEC_URL_NOT_ALLOWED"):
        default_transport("https://example.com/quotes", headers={}, timeout=20, max_body_bytes=32)


def test_default_transport_disallows_redirect_and_limits_response_read(monkeypatch):
    import investment_system.providers.sec_collection as module
    handlers = []

    class Response:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return FACTS

        def read(self, limit):
            assert limit == 33
            return b"x" * limit

    class Opener:
        def open(self, request, timeout):
            assert timeout == 20 and request.full_url == FACTS
            return Response()

    def opener(*args):
        handlers.extend(args)
        return Opener()

    monkeypatch.setattr(module, "build_opener", opener)
    with pytest.raises(SecCollectionError, match="SEC_RESPONSE_TOO_LARGE"):
        default_transport(FACTS, headers={"User-Agent": UA}, timeout=20, max_body_bytes=32)
    with pytest.raises(SecCollectionError, match="SEC_REDIRECT_REJECTED"):
        handlers[0].redirect_request(None, None, 302, "private", {}, "https://example.com")


def test_default_transport_http_error_body_is_not_read_or_exposed(monkeypatch):
    import investment_system.providers.sec_collection as module

    class Opener:
        def open(self, request, timeout):
            raise HTTPError(FACTS, 429, "SYNTHETIC_SECRET_CANARY", {"Retry-After": "7"}, None)

    monkeypatch.setattr(module, "build_opener", lambda *args: Opener())
    response = default_transport(FACTS, headers={}, timeout=20, max_body_bytes=32)
    assert response.status == 429 and response.body == b"" and response.retry_after == "7"
    assert "SYNTHETIC_SECRET_CANARY" not in repr(response)

def test_json_failure_reports_parse_stage():
    from investment_system.providers.sec_collection import SecCollectionClient, SecCollectionError, SecResponse
    # Use the existing synthetic descriptive setting; no real credential lookup.
    bad=SecCollectionClient('Synthetic diagnostics test test@example.test',transport=lambda *args,**kwargs:SecResponse(200,b'{"cik":NaN}',final_url=args[0]),sleep=lambda _:None)
    with pytest.raises(SecCollectionError) as caught:bad.collect('nvda','0001045810')
    assert str(caught.value)=='SEC_JSON_INVALID' and caught.value.stage=='parse'
