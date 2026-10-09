"""SEC M1 contract examples use synthetic bytes generated in memory only."""
import hashlib
import importlib
import importlib.util
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc
OBSERVED = datetime(2024, 2, 22, 15, 4, tzinfo=UTC)
ACCN = "0001193125-24-000001"  # A submitting agent, not NVDA's issuer CIK.


def strict():
    name = "investment_system.providers.sec_m1_strict"
    assert importlib.util.find_spec(name) is not None, "M1 strict coordinator is missing"
    return importlib.import_module(name)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fixture_inputs(m, issuer="nvda", *, form="10-K", accepted="2024-02-22T15:00:00Z",
                   rows=None, observed=OBSERVED, proofs=True):
    identity = next(i for i in m.TARGET_US17 if i.company_id == issuer)
    row = {"accn": ACCN, "form": form, "filed": "2024-02-22", "start": "2023-01-01",
           "end": "2023-12-31", "val": 123, "fy": 2023, "fp": "FY"}
    rows = [row] if rows is None else rows
    accessions = list(dict.fromkeys(r.get("accn", ACCN) for r in rows))
    filings = []
    for accession in accessions:
        sample = next(r for r in rows if r.get("accn", ACCN) == accession)
        filings.append({"form": sample.get("form", form), "filingDate": sample.get("filed"),
                        "accessionNumber": accession, "acceptanceDateTime": accepted})
    recent = {k: [r[k] for r in filings] for k in filings[0]} if filings else {
        "form": [], "filingDate": [], "accessionNumber": [], "acceptanceDateTime": []}
    payloads = {
        "SEC_SUBMISSIONS": {"cik": identity.cik, "filings": {"recent": recent, "files": []}},
        "SEC_COMPANYFACTS": {"cik": int(identity.cik), "facts": {"us-gaap": {
            "Revenues": {"units": {"USD": rows}}}}},
    }
    artifacts, receipts = [], []
    for kind, payload in payloads.items():
        body = encoded(payload)
        artifact = m.M1Artifact(issuer, identity.cik, kind, m.canonical_source_url(kind, identity.cik),
                                body, hashlib.sha256(body).hexdigest(), len(body))
        artifacts.append(artifact)
        proof = encoded({"schema": "SEC_M1_OFFICIAL_OBSERVATION/1", "issuer_id": issuer,
                         "cik": identity.cik, "source_kind": kind, "source_url": artifact.source_url,
                         "artifact_sha256": artifact.expected_sha256, "artifact_bytes": len(body),
                         "http_status": 200, "observed_at": observed.isoformat()})
        receipts.append(m.M1ObservationReceipt(proof, hashlib.sha256(proof).hexdigest(), len(proof)))
    return tuple(artifacts), tuple(receipts) if proofs else ()


def request(m, as_of=OBSERVED, *, issuers=("nvda",), now=None):
    return m.M1Request(issuers, as_of, now or OBSERVED + timedelta(days=3), synthetic=True)


def audit(m, *, as_of=OBSERVED, **kwargs):
    artifacts, proofs = fixture_inputs(m, **kwargs)
    return m.audit_sec_m1(request(m, as_of, issuers=(kwargs.get("issuer", "nvda"),)), artifacts, proofs)


def changed_artifact(m, artifacts, kind, mutate):
    out = []
    for a in artifacts:
        if a.source_kind == kind:
            body = encoded(mutate(json.loads(a.body)))
            a = replace(a, body=body, expected_sha256=hashlib.sha256(body).hexdigest(), expected_bytes=len(body))
        out.append(a)
    return tuple(out)


@pytest.mark.parametrize("delta,eligible", [(-1, False), (0, True), (1, True)])
def test_observation_upper_bound_gates_exact_bytes(delta, eligible):
    m = strict()
    result = audit(m, as_of=OBSERVED + timedelta(seconds=delta))
    fact = result.facts[0]
    assert (fact.status == "ELIGIBLE") is eligible
    assert fact.first_public_at is None
    assert fact.available_at == OBSERVED
    assert fact.availability_basis == "FIRST_VERIFIED_OBSERVATION_UPPER_BOUND"
    assert fact.accepted_at < fact.available_at
    assert fact.reason == ("ELIGIBLE" if eligible else "OBSERVATION_AFTER_CUTOFF")


def test_each_required_artifact_observation_must_be_before_cutoff():
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    payload = json.loads(proofs[1].body)
    payload["observed_at"] = (OBSERVED + timedelta(hours=1)).isoformat()
    body = encoded(payload)
    proofs = (proofs[0], m.M1ObservationReceipt(body, hashlib.sha256(body).hexdigest(), len(body)))
    result = m.audit_sec_m1(request(m), artifacts, proofs)
    assert result.facts[0].reason == "OBSERVATION_AFTER_CUTOFF"
    assert result.facts[0].available_at == OBSERVED + timedelta(hours=1)


@pytest.mark.parametrize("accepted", [None, "2024-02-22", "2024-02-22T15:00:00"])
def test_missing_or_naive_acceptance_without_receipt_never_authorizes(accepted):
    m = strict()
    result = audit(m, accepted=accepted, proofs=False)
    assert result.facts[0].accepted_at is None
    assert result.facts[0].reason == "AVAILABILITY_UNPROVEN"
    assert result.facts[0].available_at is None


@pytest.mark.parametrize("accepted", ["2024-02-22T10:00:00-05:00", "2024-02-22T16:00:00+01:00"])
def test_explicit_offset_acceptance_is_normalized(accepted):
    m = strict()
    fact = audit(m, accepted=accepted).facts[0]
    assert fact.accepted_at == datetime(2024, 2, 22, 15, tzinfo=UTC)


def test_naive_acceptance_can_remain_unknown_with_verified_observation():
    m = strict()
    fact = audit(m, accepted="2024-02-22T10:00:00").facts[0]
    assert fact.accepted_at is None and fact.acceptance_state == "UNKNOWN_NAIVE"
    assert fact.status == "ELIGIBLE"


@pytest.mark.parametrize("case,code", [("future_observation", "OBSERVATION_AFTER_EVALUATION"),
                                       ("accepted_after", "ACCEPTED_AFTER_OBSERVATION"),
                                       ("naive_asof", "AWARE_TIMESTAMP_REQUIRED"),
                                       ("asof_future", "AS_OF_AFTER_EVALUATION")])
def test_impossible_chronology_and_unzoned_request_fail(case, code):
    m = strict()
    artifacts, proofs = fixture_inputs(m, observed=OBSERVED + timedelta(days=5) if case == "future_observation" else OBSERVED,
                                      accepted="2024-02-22T15:05:00Z" if case == "accepted_after" else "2024-02-22T15:00:00Z")
    req = request(m, as_of=OBSERVED.replace(tzinfo=None) if case == "naive_asof" else OBSERVED)
    if case == "asof_future":
        req = replace(req, as_of=req.now + timedelta(seconds=1))
    with pytest.raises(m.M1Error, match=f"^{code}$"):
        m.audit_sec_m1(req, artifacts, proofs)


@pytest.mark.parametrize("issuers,code", [((), "ISSUER_SUBSET_REQUIRED"),
    (("nvda", "msft", "googl", "asml"), "ISSUER_LIMIT"), (("unknown",), "UNKNOWN_ISSUER"),
    (("nvda", "nvda"), "DUPLICATE_ISSUER")])
def test_explicit_small_identity_subset(issuers, code):
    m = strict()
    with pytest.raises(m.M1Error, match=f"^{code}$"):
        m.audit_sec_m1(request(m, issuers=issuers), (), ())


def test_three_issuers_and_identity_catalog_crosscheck():
    m = strict()
    artifacts, proofs = [], []
    for issuer in ("nvda", "msft", "googl"):
        a, p = fixture_inputs(m, issuer)
        artifacts.extend(a)
        proofs.extend(p)
    result = m.audit_sec_m1(request(m, issuers=("nvda", "msft", "googl")), tuple(artifacts), tuple(proofs))
    assert len(result.facts) == 3
    assert m.load_target_identities() == m.TARGET_US17


@pytest.mark.parametrize("issuer,form,ticker", [("asml", "20-F", "ASML"), ("stry", "10-K", "SYK")])
def test_foreign_annual_and_legacy_identity_preserved(issuer, form, ticker):
    m = strict()
    result = audit(m, issuer=issuer, form=form)
    assert result.identities[0].ticker == ticker
    assert result.facts[0].form == form and result.facts[0].status == "ELIGIBLE"
    assert result.facts[0].accession == ACCN


def test_wrong_issuer_cik_and_missing_pair_rejected():
    m = strict()
    artifacts, _ = fixture_inputs(m)
    bad = changed_artifact(m, artifacts, "SEC_COMPANYFACTS", lambda p: dict(p, cik=789019))
    with pytest.raises(m.M1Error, match="^ISSUER_CIK_MISMATCH$"):
        m.audit_sec_m1(request(m), bad, ())
    with pytest.raises(m.M1Error, match="^REQUIRED_ARTIFACT_PAIR$"):
        m.audit_sec_m1(request(m), artifacts[:1], ())


def test_original_and_amendment_preserved_without_inferred_replacement():
    m = strict()
    original = {"accn": ACCN, "form": "10-K", "filed": "2024-02-22", "end": "2023-12-31", "val": 123}
    amended = dict(original, accn="0001193125-24-000002", form="10-K/A", filed="2024-02-23", val=99)
    result = audit(m, rows=[original, amended], accepted=None)
    assert result.facts[0].lineage_state == "ORIGINAL"
    assert result.facts[1].lineage_state == "UNPROVEN"
    assert result.facts[1].replaces_accession is None
    assert result.facts[1].reason == "FILED_AFTER_CUTOFF"
    assert result.facts[0].value == 123 and result.facts[0].status == "ELIGIBLE"


def test_later_body_with_same_accession_does_not_leak_into_old_cutoff():
    m = strict()
    old = audit(m)
    revised = audit(m, rows=[{"accn": ACCN, "form": "10-K", "filed": "2024-02-22", "end": "2023-12-31", "val": 99}],
                    observed=OBSERVED + timedelta(days=1))
    assert old.facts[0].status == "ELIGIBLE" and old.facts[0].value == 123
    assert revised.facts[0].reason == "OBSERVATION_AFTER_CUTOFF"
    assert old.semantic_sha256 != revised.semantic_sha256


@pytest.mark.parametrize("field,reason", [("filed", "MISSING_FILED"), ("val", "MISSING_VALUE"),
                                       ("end", "MISSING_PERIOD_END"), ("accn", "MISSING_ACCESSION")])
def test_missing_fact_fields_remain_missing(field, reason):
    m = strict()
    row = {"accn": ACCN, "form": "10-K", "filed": "2024-02-22", "end": "2023-12-31", "val": 123}
    row.pop(field)
    result = audit(m, rows=[row])
    assert result.facts[0].reason == reason
    assert result.facts[0].status == "NOT_AVAILABLE"
    if field == "val":
        assert result.facts[0].value is None


@pytest.mark.parametrize("mutate,reason", [
    (lambda p: dict(p, facts={}), "MISSING_FACTS"),
    (lambda p: dict(p, facts={"us-gaap": {"Revenues": {}}}), "MISSING_UNITS"),
])
def test_missing_container_count_is_preserved(mutate, reason):
    m = strict()
    artifacts, _ = fixture_inputs(m)
    artifacts = changed_artifact(m, artifacts, "SEC_COMPANYFACTS", mutate)
    result = m.audit_sec_m1(request(m), artifacts, ())
    assert not result.facts and result.counts[reason] == 1


@pytest.mark.parametrize("body,code", [(b'{"cik":1,"cik":2}', "DUPLICATE_JSON_KEY"),
    (b'{"val":NaN}', "NONFINITE_JSON_NUMBER"), (b'{"val":Infinity}', "NONFINITE_JSON_NUMBER"),
    (b'{"val":1e400}', "NONFINITE_JSON_NUMBER"), (b'{bad SECRET_SENTINEL', "INVALID_JSON"),
    (b'[]', "MALFORMED_SHAPE")])
def test_strict_json_failures_are_sanitized(body, code):
    m = strict()
    artifacts, _ = fixture_inputs(m)
    a = replace(artifacts[0], body=body, expected_sha256=hashlib.sha256(body).hexdigest(), expected_bytes=len(body))
    with pytest.raises(m.M1Error, match=f"^{code}$") as error:
        m.audit_sec_m1(request(m), (a, artifacts[1]), ())
    assert "SECRET_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("case,code", [("unequal", "UNEQUAL_SUBMISSIONS_ARRAYS"),
    ("bool_fact", "INVALID_NUMERIC_FACT"), ("conflicting_fact", "CONFLICTING_FACT_KEY"),
    ("conflicting_accn", "CONFLICTING_ACCESSION"), ("malformed_units", "MALFORMED_SHAPE")])
def test_conflicting_or_malformed_inputs_fail_closed(case, code):
    m = strict()
    artifacts, _ = fixture_inputs(m)
    def mutate(p):
        if case in {"unequal", "conflicting_accn"}:
            r = p["filings"]["recent"]
            if case == "unequal":
                r["filingDate"].append("2024-02-23")
            else:
                for key in r:
                    r[key].append(r[key][0])
                r["form"][1] = "10-K/A"
        else:
            node = p["facts"]["us-gaap"]["Revenues"]
            if case == "malformed_units":
                node["units"] = []
            elif case == "bool_fact":
                node["units"]["USD"][0]["val"] = True
            else:
                node["units"]["USD"].append(dict(node["units"]["USD"][0], val=999))
        return p
    kind = "SEC_SUBMISSIONS" if case in {"unequal", "conflicting_accn"} else "SEC_COMPANYFACTS"
    artifacts = changed_artifact(m, artifacts, kind, mutate)
    with pytest.raises(m.M1Error, match=f"^{code}$"):
        m.audit_sec_m1(request(m), artifacts, ())


@pytest.mark.parametrize("case,code", [("sha", "ARTIFACT_SHA_MISMATCH"), ("size", "ARTIFACT_SIZE_MISMATCH"),
    ("credentials", "INVALID_SOURCE_URL"), ("query", "INVALID_SOURCE_URL"),
    ("escape", "INVALID_SOURCE_URL"), ("kind", "INVALID_SOURCE_KIND"), ("proof", "OBSERVATION_BINDING_MISMATCH")])
def test_artifact_and_receipt_bindings(case, code):
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    a = artifacts[0]
    if case == "sha": a = replace(a, expected_sha256="0" * 64)
    elif case == "size": a = replace(a, expected_bytes=a.expected_bytes + 1)
    elif case == "credentials": a = replace(a, source_url=a.source_url.replace("https://", "https://secret@"))
    elif case == "query": a = replace(a, source_url=a.source_url + "?token=SECRET_SENTINEL")
    elif case == "escape": a = replace(a, source_url="https://data.sec.gov/submissions/../CIK0001045810.json")
    elif case == "kind": a = replace(a, source_kind="PRICE")
    else:
        p = json.loads(proofs[0].body)
        p["artifact_sha256"] = "0" * 64
        body = encoded(p)
        proofs = (m.M1ObservationReceipt(body, hashlib.sha256(body).hexdigest(), len(body)), proofs[1])
    with pytest.raises(m.M1Error, match=f"^{code}$"):
        m.audit_sec_m1(request(m), (a, artifacts[1]), proofs)


def test_real_provider_duration_behavior_and_conservative_flags(monkeypatch):
    m = strict()
    from investment_system.providers import sec_submissions, sec_vintage, sec_companyfacts
    def forbidden(*args, **kwargs):
        raise AssertionError("network or scoring must never run")
    for module, name in [(sec_submissions, "fetch_submissions"), (sec_companyfacts, "try_fetch_companyfacts"),
                         (sec_submissions, "urlopen"), (sec_companyfacts, "urlopen")]:
        monkeypatch.setattr(module, name, forbidden)
    real = sec_vintage.resolve_vintages
    calls = []
    def record(*args, **kwargs):
        calls.append(True)
        return real(*args, **kwargs)
    monkeypatch.setattr(sec_vintage, "resolve_vintages", record)
    artifacts, proofs = fixture_inputs(m, rows=[{"accn": ACCN, "form": "10-K", "filed": "2024-02-22",
        "start": "2023-10-01", "end": "2023-12-31", "val": 123}])
    result = m.audit_sec_m1(request(m), artifacts, proofs)
    assert calls and result.facts[0].reason == "PROVIDER_FORM_DURATION_EXCLUDED"
    data = result.to_dict()
    assert data["synthetic"] is True
    assert all(data[k] is False for k in ("full_pit_pass", "real_data_verified", "publication_approved"))
    assert data["scope"] == "INPUT_AUDIT_ONLY" and data["coverage"] == "RECENT_SUPPLIED_ONLY"
    assert not {"price", "score", "qgv", "producer_status"}.intersection(data)


def test_semantic_binding_ignores_input_order_and_retry_clock():
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    first = m.audit_sec_m1(request(m), artifacts, proofs)
    again = m.audit_sec_m1(replace(request(m), now=OBSERVED + timedelta(days=6)), artifacts[::-1], proofs[::-1])
    assert first.semantic_sha256 == again.semantic_sha256


def test_unmatched_accession_is_withheld_and_no_history_claim():
    m = strict()
    artifacts, _ = fixture_inputs(m)
    artifacts = changed_artifact(m, artifacts, "SEC_SUBMISSIONS", lambda p: dict(p, filings={"recent": {
        "form": [], "filingDate": [], "accessionNumber": []}, "files": [{"name": "history.json"}]}))
    result = m.audit_sec_m1(request(m), artifacts, ())
    assert result.facts[0].reason == "UNMATCHED_ACCESSION"
    assert result.coverage == "RECENT_SUPPLIED_ONLY"


@pytest.mark.parametrize("field,value,code", [("end", "2025-12-31", "PERIOD_AFTER_FILED"),
    ("start", "2024-12-31", "INVALID_PERIOD"), ("val", 10 ** 400, "INVALID_NUMERIC_FACT")])
def test_future_inverted_and_unrepresentable_fact_values(field, value, code):
    m = strict()
    row = {"accn": ACCN, "form": "10-K", "filed": "2024-02-22", "start": "2023-01-01",
           "end": "2023-12-31", "val": 123}
    row[field] = value
    if code == "PERIOD_AFTER_FILED":
        fact = audit(m, rows=[row]).facts[0]
        assert fact.reason == code and fact.status == "NOT_AVAILABLE"
    else:
        with pytest.raises(m.M1Error, match=f"^{code}$"):
            audit(m, rows=[row])


def test_input_size_and_row_bounds(monkeypatch):
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    monkeypatch.setattr(m, "MAX_INPUT_BYTES", 10)
    with pytest.raises(m.M1Error, match="^INPUT_SIZE_LIMIT$"):
        m.audit_sec_m1(request(m), artifacts, proofs)
    monkeypatch.setattr(m, "MAX_INPUT_BYTES", 16 * 1024 * 1024)
    monkeypatch.setattr(m, "MAX_ROWS", 0)
    with pytest.raises(m.M1Error, match="^ROW_LIMIT$"):
        m.audit_sec_m1(request(m), artifacts, proofs)


def test_join_rejects_conflicting_fact_filing_metadata():
    m = strict()
    artifacts, _ = fixture_inputs(m)
    def mutate(p):
        p["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["filed"] = "2024-02-21"
        return p
    artifacts = changed_artifact(m, artifacts, "SEC_COMPANYFACTS", mutate)
    with pytest.raises(m.M1Error, match="^ACCESSION_FACT_CONFLICT$"):
        m.audit_sec_m1(request(m), artifacts, ())


def test_malformed_observation_fields_are_sanitized():
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    payload = json.loads(proofs[0].body)
    payload["issuer_id"] = {"SECRET_SENTINEL": "unhashable"}
    body = encoded(payload)
    proof = m.M1ObservationReceipt(body, hashlib.sha256(body).hexdigest(), len(body))
    with pytest.raises(m.M1Error, match="^INVALID_OBSERVATION_RECEIPT$"):
        m.audit_sec_m1(request(m), artifacts, (proof, proofs[1]))


def test_new_unmatched_submission_does_not_invalidate_an_older_companyfacts_copy():
    m = strict()
    artifacts, proofs = fixture_inputs(m)
    def append_later_submission(payload):
        recent = payload["filings"]["recent"]
        for key, value in {"accessionNumber": "0001193125-24-000002", "form": "10-Q",
                           "filingDate": "2024-02-22", "acceptanceDateTime": "2024-02-22T15:06:00Z"}.items():
            recent[key].append(value)
        return payload
    artifacts = changed_artifact(m, artifacts, "SEC_SUBMISSIONS", append_later_submission)
    payload = json.loads(proofs[0].body)
    payload.update(artifact_sha256=artifacts[0].expected_sha256, artifact_bytes=artifacts[0].expected_bytes,
                   observed_at="2024-02-22T15:10:00Z")
    body = encoded(payload)
    proofs = (m.M1ObservationReceipt(body, hashlib.sha256(body).hexdigest(), len(body)), proofs[1])
    cutoff = OBSERVED + timedelta(minutes=6)
    result = m.audit_sec_m1(request(m, cutoff), artifacts, proofs)
    assert len(result.facts) == 1 and result.facts[0].status == "ELIGIBLE"
    assert result.facts[0].available_at == cutoff
