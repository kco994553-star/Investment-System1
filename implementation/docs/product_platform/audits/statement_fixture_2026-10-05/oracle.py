"""Audit-only raw admission / statement oracle; not Product implementation."""
from datetime import datetime
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "storage_auth_2026-10-05"
spec = importlib.util.spec_from_file_location("prior_statement_probes", PRIOR / "owner_probes.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
c, unused_tests, OWNER_MANIFEST = prior.load_owner()
SOURCE_SHA = next(x["sha256"] for x in OWNER_MANIFEST if x["path"].endswith("platform/contracts.py"))
assert SOURCE_SHA == "b13686d8ce134ccb61ef78c51d178597404e7a3401e7b22240dcc47c01d0aa7b"


class FixtureRejected(ValueError):
    pass


def fixture():
    metadata = json.loads((HERE / "fixture.json").read_text())
    times = {k: datetime.fromisoformat(v) for k, v in metadata["source_times"].items()}
    records, raw = [], {}
    for item in metadata["records"]:
        ref = "fixture://statement/" + item["record_id"] + "/" + item["source_version"]
        raw[ref] = (HERE / item["raw_path"]).read_bytes()
        records.append(c.SourceRecord(
            metadata["tenant_id"], metadata["connection_id"], metadata["account_id"],
            item["record_id"], item["source_version"], item["record_type"],
            **times, source="SYNTHETIC_STATEMENT", raw_payload_ref=ref,
            payload_sha256=item["payload_sha256"]))
    return metadata, tuple(records), raw


def admit(ctx, records, raw, decision_time):
    ledger = c.ImportLedger()
    admitted = []
    for record in records:
        c.require_tenant(ctx, record.tenant_id)
        if record.available_at > decision_time or record.observed_at > decision_time:
            raise FixtureRejected("FUTURE_SOURCE")
        body = raw.get(record.raw_payload_ref)
        if not isinstance(body, bytes) or hashlib.sha256(body).hexdigest() != record.payload_sha256.lower():
            raise FixtureRejected("RAW_HASH_MISSING_OR_CHANGED")
        data = decode(body)
        for field, value in (
            ("tenant_id", record.tenant_id), ("connection_id", record.connection_id),
            ("account_id", record.account_id), ("record_id", record.source_record_id),
            ("source_version", record.source_version), ("record_type", record.record_type),
        ):
            if data[field] != value:
                raise FixtureRejected("RAW_METADATA_BINDING")
        if ledger.ingest(ctx, record) == c.ImportStatus.INSERTED:
            admitted.append(record)
    return tuple(admitted)


COMMON = {"fixture_schema", "data_state", "tenant_id", "connection_id", "account_id",
          "currency", "security_id", "source_version", "record_id", "record_type"}
FIELDS = {
    "OPENING": {"cash", "quantity"},
    "TRANSACTION": {"historical_kind", "cash_delta", "quantity_delta"},
    "STATEMENT": {"cash", "quantity", "price", "market_value", "total", "included_record_ids"},
}


def decode(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise FixtureRejected("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        data = json.loads(body.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise FixtureRejected("FIXTURE_JSON_REJECTED") from None
    if not isinstance(data, dict) or data.get("record_type") not in FIELDS:
        raise FixtureRejected("FIXTURE_SHAPE_REJECTED")
    if set(data) != COMMON | FIELDS[data["record_type"]]:
        raise FixtureRejected("FIXTURE_SHAPE_REJECTED")
    if data["fixture_schema"] != "statement-fixture-v1" or data["data_state"] != "DEMO":
        raise FixtureRejected("FIXTURE_ONLY")
    return data


def number(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        raise FixtureRejected("FINITE_DECIMAL_TEXT_REQUIRED")
    # Exact rational arithmetic for this test oracle; no rounding/tolerance.
    return Fraction(value)


def statement(ctx, records, raw, decision_time):
    records = admit(ctx, records, raw, decision_time)
    data = [decode(raw[record.raw_payload_ref]) for record in records]
    opening = [x for x in data if x["record_type"] == "OPENING"]
    closing = [x for x in data if x["record_type"] == "STATEMENT"]
    if len(opening) != 1 or len(closing) != 1:
        raise FixtureRejected("OPENING_AND_STATEMENT_REQUIRED")
    opening, closing = opening[0], closing[0]
    scope = (opening[k] for k in ("connection_id", "account_id", "currency", "security_id"))
    scope = tuple(scope)
    if any(tuple(x[k] for k in ("connection_id", "account_id", "currency", "security_id")) != scope for x in data):
        raise FixtureRejected("MIXED_ACCOUNT_CURRENCY_OR_SECURITY")
    ids = [x["record_id"] for x in data]
    included = closing["included_record_ids"]
    if (not isinstance(included, list) or any(not isinstance(x, str) for x in included)
            or len(set(included)) != len(included) or len(set(ids)) != len(ids)
            or set(included) != set(ids) - {closing["record_id"]}):
        raise FixtureRejected("STATEMENT_COVERAGE_NOT_ESTABLISHED")
    cash, quantity = number(opening["cash"]), number(opening["quantity"])
    for movement in (x for x in data if x["record_type"] == "TRANSACTION"):
        if movement["historical_kind"] not in {"BUY", "DIVIDEND"}:
            raise FixtureRejected("UNSUPPORTED_FIXTURE_EVENT")
        # Consume explicitly reported deltas; never derive execution or prices.
        cash += number(movement["cash_delta"])
        quantity += number(movement["quantity_delta"])
    market_value = quantity * number(closing["price"])
    computed = {"cash": cash, "quantity": quantity, "market_value": market_value, "total": cash + market_value}
    mismatches = tuple(k for k, value in computed.items() if value != number(closing[k]))
    rows = tuple(c.NormalizedFinancialRecord(ctx.tenant_id, "fixture-" + str(index), record.record_type, (record.ref,))
                 for index, record in enumerate(records))
    lineage = c.reconcile_records(ctx, records, rows)
    return {"passed": lineage["passed"] and not mismatches, "lineage_passed": lineage["passed"],
            "computed": {k: str(v) for k, v in computed.items()}, "mismatches": mismatches,
            "admitted_unique": len(records), "scope": "DEMO_FIXTURE_ONLY", "execution": "NOT_RUN"}
