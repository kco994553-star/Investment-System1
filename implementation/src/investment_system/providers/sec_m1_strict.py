"""Offline SEC input audit; no fetching, scoring, or publication authority.

Observation receipts are operator-supplied evidence. Hash and provenance checks
verify their bindings, not SEC authenticity or an exact first-public timestamp.
The pure coordinator uses the pinned current TARGET identity projection; it
does not claim that those identities were available at a historical cutoff.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from ..markets.us import US_LISTINGS
from . import sec_submissions, sec_vintage

VERSION = "SEC_M1_OFFLINE/1"
IDENTITY_MAP_SHA256 = "5b68c5a884e54ae4aefaa18de935efb12f2dabeb0109d5c6039d9c5736a280ce"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000
MAX_ISSUERS = 3
UTC = timezone.utc
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
ACCN_RE = re.compile(r"(?:[0-9]{10}-[0-9]{2}-[0-9]{6}|[0-9]{18})\Z")


class M1Error(ValueError):
    """A fixed code only: never include payload, paths, or exception text."""

    def __init__(self, code: str):
        self.code = code if re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", code) else "INVALID_INPUT"
        super().__init__(self.code)


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise M1Error("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise M1Error("NONFINITE_JSON_NUMBER")
    return number


def _nonfinite(_value):
    raise M1Error("NONFINITE_JSON_NUMBER")


def strict_json(body: bytes, *, max_bytes: int = MAX_INPUT_BYTES) -> dict:
    if not isinstance(body, bytes) or not body or len(body) > max_bytes:
        raise M1Error("INPUT_SIZE_LIMIT")
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_float=_number, parse_constant=_nonfinite)
    except M1Error:
        raise
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise M1Error("INVALID_JSON") from None
    if not isinstance(value, dict):
        raise M1Error("MALFORMED_SHAPE")
    return value


def aware_datetime(value: datetime | str) -> datetime:
    try:
        if isinstance(value, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
                raise M1Error("AWARE_TIMESTAMP_REQUIRED")
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise M1Error("AWARE_TIMESTAMP_REQUIRED")
        return value.astimezone(UTC)
    except (ValueError, OverflowError):
        raise M1Error("AWARE_TIMESTAMP_REQUIRED") from None


def _cik(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not re.fullmatch(r"[0-9]{1,10}", str(value)):
        raise M1Error("INVALID_CIK")
    return str(value).zfill(10)


def canonical_source_url(kind: str, cik: str) -> str:
    cik = _cik(cik)
    if kind == "SEC_SUBMISSIONS":
        return f"https://data.sec.gov/submissions/CIK{cik}.json"
    if kind == "SEC_COMPANYFACTS":
        return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    raise M1Error("INVALID_SOURCE_KIND")


@dataclass(frozen=True)
class M1Identity:
    company_id: str
    ticker: str
    cik: str
    security_scheme: str
    security_value: str


# Identity-only projection of the reviewed map, including stry=SYK and ASML.
TARGET_US17 = tuple(M1Identity(*row) for row in (
    ("asml", "ASML", "0000937966", "ISIN", "USN070592100"),
    ("lrcx", "LRCX", "0000707549", "ISIN", "US5128073062"),
    ("klac", "KLAC", "0000319201", "ISIN", "US4824801009"),
    ("nvda", "NVDA", "0001045810", "ISIN", "US67066G1040"),
    ("amd", "AMD", "0000002488", "ISIN", "US0079031078"),
    ("avgo", "AVGO", "0001730168", "ISIN", "US11135F1012"),
    ("qcom", "QCOM", "0000804328", "ISIN", "US7475251036"),
    ("intc", "INTC", "0000050863", "ISIN", "US4581401001"),
    ("msft", "MSFT", "0000789019", "ISIN", "US5949181045"),
    ("googl", "GOOGL", "0001652044", "ISIN", "US02079K3059"),
    ("amzn", "AMZN", "0001018724", "ISIN", "US0231351067"),
    ("rtx", "RTX", "0000101829", "ISIN", "US75513E1010"),
    ("stry", "SYK", "0000310764", "ISIN", "US8636671013"),
    ("etn", "ETN", "0001551182", "ISIN", "IE00B8KQN827"),
    ("hubb", "HUBB", "0000048898", "ISIN", "US4435106079"),
    ("gev", "GEV", "0001996810", "ISIN", "US36828A1016"),
    ("rok", "ROK", "0001024478", "ISIN", "US7739031091"),
))


def _check_catalog():
    if len(TARGET_US17) != 17 or set(US_LISTINGS) != {i.company_id for i in TARGET_US17}:
        raise M1Error("IDENTITY_CATALOG_MISMATCH")
    for identity in TARGET_US17:
        listing = US_LISTINGS[identity.company_id]
        if (listing["cik"], listing["yahoo"]) != (identity.cik, identity.ticker):
            raise M1Error("IDENTITY_CATALOG_MISMATCH")


def load_target_identities(path: Path | None = None) -> tuple[M1Identity, ...]:
    """Verify only the pinned public identity map; never load weights or datasets."""
    if path is None:
        path = Path(__file__).resolve().parents[3] / "docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json"
    try:
        raw = Path(path).read_bytes()
        if sha256(raw) != IDENTITY_MAP_SHA256:
            raise M1Error("IDENTITY_MAP_SHA_MISMATCH")
        mapping = strict_json(raw)
        projected = []
        for row in mapping["rows"]:
            if row["current_listing_observation"].get("currency") != "USD":
                continue
            projected.append(M1Identity(row["legacy_company_reference"], row["target_row"]["ticker_hint"],
                                        row["issuer_ref"]["value"], row["security_ref"]["scheme"],
                                        row["security_ref"]["value"]))
        if tuple(projected) != TARGET_US17:
            raise M1Error("IDENTITY_CATALOG_MISMATCH")
        _check_catalog()
        return TARGET_US17
    except M1Error:
        raise
    except (OSError, KeyError, TypeError, ValueError):
        raise M1Error("IDENTITY_CATALOG_MISMATCH") from None


@dataclass(frozen=True)
class M1Request:
    issuer_ids: tuple[str, ...]
    as_of: datetime
    now: datetime
    synthetic: bool = True


@dataclass(frozen=True)
class M1Artifact:
    issuer_id: str
    cik: str
    source_kind: str
    source_url: str
    body: bytes
    expected_sha256: str
    expected_bytes: int


@dataclass(frozen=True)
class M1ObservationReceipt:
    body: bytes
    expected_sha256: str
    expected_bytes: int


@dataclass(frozen=True)
class M1Fact:
    issuer_id: str
    taxonomy: str
    concept: str
    unit: str
    accession: str | None
    form: str | None
    value: int | float | None
    filing_date: str | None
    submissions_filing_date: str | None
    period_start: str | None
    period_end: str | None
    fiscal_year: int | None
    fiscal_period: str | None
    frame: str | None
    accepted_at: datetime | None
    acceptance_state: str
    source_observed_at: datetime | None
    submissions_observed_at: datetime | None
    available_at: datetime | None
    availability_basis: str
    first_public_at: None
    status: str
    reason: str
    lineage_state: str
    replaces_accession: None
    companyfacts_sha256: str
    submissions_sha256: str
    observation_receipt_sha256s: tuple[str, ...]

    def to_dict(self):
        return {key: value.isoformat() if isinstance(value, datetime) else list(value) if isinstance(value, tuple) else value
                for key, value in asdict(self).items()}


@dataclass(frozen=True)
class M1Audit:
    request: M1Request
    identities: tuple[M1Identity, ...]
    artifacts: tuple[M1Artifact, ...]
    observation_receipts: tuple[M1ObservationReceipt, ...]
    facts: tuple[M1Fact, ...]
    counts: dict[str, int]
    coverage: str = "RECENT_SUPPLIED_ONLY"

    def to_dict(self):
        return {"schema": VERSION, "scope": "INPUT_AUDIT_ONLY", "coverage": self.coverage,
                "identity_scope": "CURRENT_TARGET_ONLY_NO_HISTORICAL_IDENTITY_CLAIM",
                "observation_evidence": "OPERATOR_SUPPLIED_HASH_BOUND_NOT_EXTERNALLY_AUTHENTICATED",
                "synthetic": self.request.synthetic, "full_pit_pass": False,
                "real_data_verified": False, "publication_approved": False,
                "facts": [f.to_dict() for f in self.facts], "counts": dict(sorted(self.counts.items()))}

    def semantic_dict(self):
        return {"version": VERSION, "identity_map_sha256": IDENTITY_MAP_SHA256,
                "request": {"issuer_ids": sorted(self.request.issuer_ids),
                            "as_of": aware_datetime(self.request.as_of).isoformat(), "synthetic": self.request.synthetic},
                "identities": [asdict(i) for i in self.identities],
                "artifacts": [{"issuer_id": a.issuer_id, "cik": a.cik, "source_kind": a.source_kind,
                               "source_url": a.source_url, "sha256": a.expected_sha256, "bytes": a.expected_bytes}
                              for a in self.artifacts],
                "observation_receipts": [{"sha256": p.expected_sha256, "bytes": p.expected_bytes}
                                         for p in self.observation_receipts], "result": self.to_dict()}

    @property
    def semantic_sha256(self):
        return sha256(canonical_json(self.semantic_dict()))


def validate_expected_binding(expected_sha, expected_bytes, *, prefix="ARTIFACT", max_bytes=None):
    """Preflight declarations before reading caller-supplied local body paths."""
    max_bytes = MAX_INPUT_BYTES if max_bytes is None else max_bytes
    if type(expected_bytes) is not int or expected_bytes <= 0:
        raise M1Error(prefix + "_SIZE_MISMATCH")
    if expected_bytes > max_bytes:
        raise M1Error("INPUT_SIZE_LIMIT")
    if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
        raise M1Error(prefix + "_SHA_MISMATCH")


def _verify_body(body, expected_sha, expected_bytes, prefix="ARTIFACT"):
    if not isinstance(body, bytes) or len(body) > MAX_INPUT_BYTES or not body:
        raise M1Error("INPUT_SIZE_LIMIT")
    validate_expected_binding(expected_sha, expected_bytes, prefix=prefix)
    if expected_bytes != len(body):
        raise M1Error(prefix + "_SIZE_MISMATCH")
    if sha256(body) != expected_sha:
        raise M1Error(prefix + "_SHA_MISMATCH")


def _day(value) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise M1Error("INVALID_DATE")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise M1Error("INVALID_DATE") from None
    return value


def _accession(value) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not ACCN_RE.fullmatch(value):
        raise M1Error("INVALID_ACCESSION")
    digits = value.replace("-", "")
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


def _text(value) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > 256:
        raise M1Error("MALFORMED_SHAPE")
    return value


def _acceptance(value):
    if value is None or value == "":
        return None, "MISSING"
    if not isinstance(value, str):
        raise M1Error("INVALID_ACCEPTANCE_TIMESTAMP")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise M1Error("INVALID_ACCEPTANCE_TIMESTAMP") from None
    if dt.tzinfo is None:
        return None, "UNKNOWN_NAIVE"
    return aware_datetime(value), "EXPLICIT_OFFSET"


def _submissions(payload):
    try:
        filings = payload["filings"]
        recent = filings["recent"]
        if not isinstance(filings, dict) or not isinstance(recent, dict):
            raise M1Error("MALFORMED_SHAPE")
        required = ("form", "filingDate", "accessionNumber")
        if any(key not in recent for key in required) or any(not isinstance(v, list) for v in recent.values()):
            raise M1Error("MALFORMED_SHAPE")
        lengths = {len(v) for v in recent.values()}
        if len(lengths) != 1:
            raise M1Error("UNEQUAL_SUBMISSIONS_ARRAYS")
        count = len(recent["form"])
        if count > MAX_ROWS:
            raise M1Error("ROW_LIMIT")
        history = filings.get("files", [])
        if not isinstance(history, list) or any(not isinstance(r, dict) for r in history):
            raise M1Error("MALFORMED_SHAPE")
        result = {}
        acceptance_values = recent.get("acceptanceDateTime", [None] * count)
        for index in range(count):
            accession = _accession(recent["accessionNumber"][index])
            if accession is None:
                raise M1Error("MISSING_SUBMISSIONS_ACCESSION")
            accepted, state = _acceptance(acceptance_values[index])
            item = (_text(recent["form"][index]), _day(recent["filingDate"][index]), accepted, state)
            if accession in result and result[accession] != item:
                raise M1Error("CONFLICTING_ACCESSION")
            result[accession] = item
        return result
    except (KeyError, TypeError, IndexError):
        raise M1Error("MALFORMED_SHAPE") from None


def _fact_rows(payload, counts):
    facts = payload.get("facts")
    if facts is None or facts == {}:
        counts["MISSING_FACTS"] += 1
        return []
    if not isinstance(facts, dict):
        raise M1Error("MALFORMED_SHAPE")
    result, seen = [], {}
    total = 0
    for taxonomy, concepts in facts.items():
        if not isinstance(concepts, dict):
            raise M1Error("MALFORMED_SHAPE")
        _text(taxonomy)
        for concept, node in concepts.items():
            _text(concept)
            if not isinstance(node, dict):
                raise M1Error("MALFORMED_SHAPE")
            units = node.get("units")
            if units is None or units == {}:
                counts["MISSING_UNITS"] += 1
                continue
            if not isinstance(units, dict):
                raise M1Error("MALFORMED_SHAPE")
            for unit, rows in units.items():
                _text(unit)
                if not isinstance(rows, list):
                    raise M1Error("MALFORMED_SHAPE")
                total += len(rows)
                if total > MAX_ROWS:
                    raise M1Error("ROW_LIMIT")
                for row in rows:
                    if not isinstance(row, dict):
                        raise M1Error("MALFORMED_SHAPE")
                    value = row.get("val")
                    if value is not None:
                        try:
                            valid_numeric = type(value) in (int, float) and math.isfinite(value)
                        except OverflowError:
                            valid_numeric = False
                        if not valid_numeric:
                            raise M1Error("INVALID_NUMERIC_FACT")
                    fy = row.get("fy")
                    if fy is not None and type(fy) is not int:
                        raise M1Error("MALFORMED_SHAPE")
                    normalized = {"accn": _accession(row.get("accn")), "form": _text(row.get("form")),
                                  "filed": _day(row.get("filed")), "start": _day(row.get("start")),
                                  "end": _day(row.get("end")), "val": value, "fy": fy,
                                  "fp": _text(row.get("fp")), "frame": _text(row.get("frame"))}
                    if normalized["start"] and normalized["end"] and normalized["start"] > normalized["end"]:
                        raise M1Error("INVALID_PERIOD")
                    key = (taxonomy, concept, unit, normalized["accn"], normalized["start"],
                           normalized["end"], normalized["fy"], normalized["fp"], normalized["frame"])
                    if key in seen:
                        if seen[key] != normalized:
                            raise M1Error("CONFLICTING_FACT_KEY")
                        counts["IDENTICAL_FACT_DUPLICATE"] += 1
                        continue
                    seen[key] = normalized
                    result.append((taxonomy, concept, unit, normalized))
    return result


def _observations(receipts, artifacts, now):
    observations = {}
    if len(receipts) > MAX_ISSUERS * 2:
        raise M1Error("OBSERVATION_LIMIT")
    fields = {"schema", "issuer_id", "cik", "source_kind", "source_url", "artifact_sha256",
              "artifact_bytes", "http_status", "observed_at"}
    for receipt in receipts:
        if not isinstance(receipt, M1ObservationReceipt):
            raise M1Error("INVALID_OBSERVATION_RECEIPT")
        _verify_body(receipt.body, receipt.expected_sha256, receipt.expected_bytes, "OBSERVATION")
        proof = strict_json(receipt.body, max_bytes=16_384)
        if set(proof) != fields or proof["schema"] != "SEC_M1_OFFICIAL_OBSERVATION/1":
            raise M1Error("INVALID_OBSERVATION_RECEIPT")
        if any(not isinstance(proof[k], str) for k in ("issuer_id", "cik", "source_kind", "source_url", "artifact_sha256", "observed_at")):
            raise M1Error("INVALID_OBSERVATION_RECEIPT")
        key = (proof["issuer_id"], proof["source_kind"])
        artifact = artifacts.get(key)
        if (artifact is None or proof["cik"] != artifact.cik or proof["source_url"] != artifact.source_url
                or proof["artifact_sha256"] != artifact.expected_sha256
                or type(proof["artifact_bytes"]) is not int or proof["artifact_bytes"] != artifact.expected_bytes
                or type(proof["http_status"]) is not int or proof["http_status"] != 200):
            raise M1Error("OBSERVATION_BINDING_MISMATCH")
        observed = aware_datetime(proof["observed_at"])
        if observed > now:
            raise M1Error("OBSERVATION_AFTER_EVALUATION")
        if key in observations:
            raise M1Error("CONFLICTING_OBSERVATION")
        observations[key] = (observed, receipt.expected_sha256)
    return observations


def validate_m1_request(request: M1Request) -> M1Request:
    """Validate clocks and explicit identity scope without reading inputs."""
    if not isinstance(request, M1Request):
        raise M1Error("INVALID_REQUEST")
    as_of, now = aware_datetime(request.as_of), aware_datetime(request.now)
    if as_of > now:
        raise M1Error("AS_OF_AFTER_EVALUATION")
    if not isinstance(request.issuer_ids, tuple) or not request.issuer_ids:
        raise M1Error("ISSUER_SUBSET_REQUIRED")
    if len(request.issuer_ids) > MAX_ISSUERS:
        raise M1Error("ISSUER_LIMIT")
    if any(not isinstance(cid, str) for cid in request.issuer_ids):
        raise M1Error("UNKNOWN_ISSUER")
    if len(set(request.issuer_ids)) != len(request.issuer_ids):
        raise M1Error("DUPLICATE_ISSUER")
    _check_catalog()
    catalog = {i.company_id: i for i in TARGET_US17}
    if not set(request.issuer_ids).issubset(catalog):
        raise M1Error("UNKNOWN_ISSUER")
    if type(request.synthetic) is not bool:
        raise M1Error("INVALID_SYNTHETIC_FLAG")
    return M1Request(tuple(sorted(request.issuer_ids)), as_of, now, request.synthetic)


def validate_m1_input_bindings(request: M1Request, artifacts: tuple[M1Artifact, ...]) -> dict:
    """Validate all artifact metadata (bodies are not examined by this helper)."""
    request = validate_m1_request(request)
    catalog = {i.company_id: i for i in TARGET_US17}
    if not isinstance(artifacts, tuple):
        raise M1Error("MALFORMED_SHAPE")
    if len(artifacts) != 2 * len(request.issuer_ids):
        raise M1Error("REQUIRED_ARTIFACT_PAIR")
    pairs = {}
    for artifact in artifacts:
        if not isinstance(artifact, M1Artifact):
            raise M1Error("INVALID_ARTIFACT")
        canonical = canonical_source_url(artifact.source_kind, artifact.cik)
        if artifact.issuer_id not in request.issuer_ids or artifact.cik != catalog[artifact.issuer_id].cik:
            raise M1Error("ISSUER_CIK_MISMATCH")
        if artifact.source_url != canonical:
            raise M1Error("INVALID_SOURCE_URL")
        validate_expected_binding(artifact.expected_sha256, artifact.expected_bytes)
        key = (artifact.issuer_id, artifact.source_kind)
        if key in pairs:
            raise M1Error("CONFLICTING_ARTIFACT")
        pairs[key] = artifact
    if set(pairs) != {(cid, kind) for cid in request.issuer_ids for kind in ("SEC_SUBMISSIONS", "SEC_COMPANYFACTS")}:
        raise M1Error("REQUIRED_ARTIFACT_PAIR")
    return pairs


def audit_sec_m1(request: M1Request, artifacts: tuple[M1Artifact, ...],
                 observation_receipts: tuple[M1ObservationReceipt, ...] = ()) -> M1Audit:
    """Pure, deterministic input audit, preserving eligible and withheld vintages."""
    request = validate_m1_request(request)
    as_of, now = request.as_of, request.now
    catalog = {i.company_id: i for i in TARGET_US17}
    if not isinstance(observation_receipts, tuple):
        raise M1Error("MALFORMED_SHAPE")
    pairs = validate_m1_input_bindings(request, artifacts)
    # Verify ALL byte/source bindings before parsing any payload.
    for artifact in artifacts:
        _verify_body(artifact.body, artifact.expected_sha256, artifact.expected_bytes)
    payloads = {}
    observations = _observations(observation_receipts, pairs, now)
    for key, artifact in pairs.items():
        payload = strict_json(artifact.body)
        if _cik(payload.get("cik")) != artifact.cik:
            raise M1Error("ISSUER_CIK_MISMATCH")
        payloads[key] = payload
    counts, facts = Counter(), []
    for cid in sorted(request.issuer_ids):
        submissions = pairs[cid, "SEC_SUBMISSIONS"]
        companyfacts = pairs[cid, "SEC_COMPANYFACTS"]
        index = _submissions(payloads[cid, "SEC_SUBMISSIONS"])
        cf_proof = observations.get((cid, "SEC_COMPANYFACTS"))
        sub_proof = observations.get((cid, "SEC_SUBMISSIONS"))
        for _form, _filed, accepted, _state in index.values():
            if accepted is not None and sub_proof and accepted > sub_proof[0]:
                raise M1Error("ACCEPTED_AFTER_OBSERVATION")
        for taxonomy, concept, unit, row in _fact_rows(payloads[cid, "SEC_COMPANYFACTS"], counts):
            accession, form, filed = row["accn"], row["form"], row["filed"]
            matched = index.get(accession)
            accepted, state = (matched[2], matched[3]) if matched else (None, "MISSING")
            if accepted is not None and cf_proof and accepted > cf_proof[0]:
                raise M1Error("ACCEPTED_AFTER_OBSERVATION")
            bound = max(cf_proof[0], sub_proof[0]) if cf_proof and sub_proof else None
            reason = "ELIGIBLE"
            if accession is None: reason = "MISSING_ACCESSION"
            elif not matched: reason = "UNMATCHED_ACCESSION"
            elif filed is None or matched[1] is None: reason = "MISSING_FILED"
            elif form is None: reason = "MISSING_FORM"
            elif form != matched[0] or filed != matched[1]: raise M1Error("ACCESSION_FACT_CONFLICT")
            elif row["val"] is None: reason = "MISSING_VALUE"
            elif row["end"] is None: reason = "MISSING_PERIOD_END"
            elif row["end"] > filed: reason = "PERIOD_AFTER_FILED"
            elif form not in sec_submissions.FORMS: reason = "UNSUPPORTED_FORM"
            elif filed > as_of.date().isoformat(): reason = "FILED_AFTER_CUTOFF"
            elif accepted is not None and accepted > as_of: reason = "ACCEPTED_AFTER_CUTOFF"
            elif bound is None: reason = "AVAILABILITY_UNPROVEN"
            elif bound > as_of: reason = "OBSERVATION_AFTER_CUTOFF"
            if reason == "ELIGIBLE":
                # Isolated rows only. Legacy stamps/selection never become availability evidence.
                filtered_index = {"filings": {"recent": {"form": [form], "filingDate": [filed],
                                                           "accessionNumber": [accession]}}}
                isolated = {"facts": {taxonomy: {concept: {"units": {unit: [row]}}}}}
                if (not sec_submissions.parse_filings(filtered_index, as_of)
                        or not sec_vintage.resolve_vintages(isolated, taxonomy, concept, unit, as_of, form.removesuffix("/A"))):
                    reason = "PROVIDER_FORM_DURATION_EXCLUDED"
            counts[reason] += 1
            facts.append(M1Fact(cid, taxonomy, concept, unit, accession, form, row["val"], filed,
                matched[1] if matched else None, row["start"], row["end"], row["fy"], row["fp"], row["frame"],
                accepted, state, cf_proof[0] if cf_proof else None, sub_proof[0] if sub_proof else None,
                bound, "FIRST_VERIFIED_OBSERVATION_UPPER_BOUND" if bound else "AVAILABILITY_UNPROVEN",
                None, "ELIGIBLE" if reason == "ELIGIBLE" else "NOT_AVAILABLE", reason,
                "UNPROVEN" if form and form.endswith("/A") else "ORIGINAL" if form else "UNKNOWN", None,
                companyfacts.expected_sha256, submissions.expected_sha256,
                tuple(sorted(p[1] for p in (cf_proof, sub_proof) if p))))
    facts.sort(key=lambda f: canonical_json(f.to_dict()))
    normalized = M1Request(tuple(sorted(request.issuer_ids)), as_of, now, request.synthetic)
    return M1Audit(normalized, tuple(catalog[cid] for cid in sorted(request.issuer_ids)),
                   tuple(sorted(artifacts, key=lambda a: (a.issuer_id, a.source_kind))),
                   tuple(sorted(observation_receipts, key=lambda p: p.expected_sha256)), tuple(facts), dict(counts))
