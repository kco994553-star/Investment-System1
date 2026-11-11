"""Offline ownership observations projected into the common RIG identity namespace.

This adapter neither infers control from percentages nor changes operating RIG,
QGV, classification or selection. Source text and unresolved names stay evidence;
only explicit reviewed assertions can become relationships.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from urllib.parse import urlsplit

from investment_system.providers.sec_classification_inputs import html_text
from investment_system.rig.model import IdentityRef, Node, stable_id

INPUT_SCHEMA = "company-ownership-input/1"
VIEW_SCHEMA = "company-ownership-view/1"
MAX_VIEW_BYTES = 2 * 1024 * 1024
TYPES = {"OWNERSHIP", "PARENT_SUBSIDIARY"}
STATUSES = {"UNREVIEWED", "VERIFIED", "PLANNED", "COMPLETED", "DISPOSED", "CONFLICT"}
PUBLICATIONS = {"PUBLIC_APPROVED", "PRIVATE", "UNKNOWN"}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _text(value, code):
    _require(isinstance(value, str) and bool(value.strip()), code)
    return value


def _day(value, nullable=False):
    if value is None and nullable:
        return None
    _require(isinstance(value, str) and len(value) == 10, "DATE")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("DATE") from None
    _require(parsed.isoformat() == value, "DATE")
    return parsed


def _instant(value):
    _require(isinstance(value, str) and "T" in value, "TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("TIMESTAMP") from None
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "TIMESTAMP")
    return parsed


def _precision(value):
    _require(isinstance(value, dict) and set(value) == {"value", "precision"}, "TIME_PRECISION")
    kind, raw = value["precision"], value["value"]
    _require(kind in {"DATE", "DATETIME", "UNKNOWN"}, "TIME_PRECISION")
    if kind == "DATE":
        _day(raw)
    elif kind == "DATETIME":
        _instant(raw)
    else:
        _require(raw is None, "UNKNOWN_TIME_VALUE")


def _available(value, cutoff):
    if value["precision"] == "DATETIME":
        return _instant(value["value"]) <= cutoff
    if value["precision"] == "DATE":
        # The exact release time on that date is not known. Never invent midnight.
        return _day(value["value"]) < cutoff.date()
    return False


def _unique(rows, key, code):
    _require(isinstance(rows, list), code)
    index = {}
    for row in rows:
        _require(isinstance(row, dict), code)
        identifier = key(row)
        _require(identifier not in index, code)
        index[identifier] = row
    return index


def _refs(ids, index):
    _require(isinstance(ids, list) and bool(ids) and len(ids) == len(set(ids)), "REFERENCE")
    _require(all(identifier in index for identifier in ids), "REFERENCE")


def _percent(value):
    if value is None:
        return None
    _require(isinstance(value, str) and value.strip() == value and bool(value), "PERCENT_DECIMAL_STRING")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise ValueError("PERCENT") from None
    _require(parsed.is_finite() and Decimal(0) <= parsed <= Decimal(100), "PERCENT_RANGE")
    return parsed


def _observation(o, target, securities):
    _text(o.get("observation_id"), "OBSERVATION_ID")
    _require(o.get("metric") in {"SHARE_CAPITAL", "VOTING_POWER", "MANAGED_HOLDINGS"}, "METRIC")
    _require(o.get("unit") == "PERCENT", "PERCENT_UNIT")
    value, lower, upper = (_percent(o.get(k)) for k in ("value", "lower", "upper"))
    qualifier = o.get("qualifier")
    if qualifier in {"EXACT", "APPROX"}:
        _require(value is not None and lower is None and upper is None, "PERCENT_QUALIFIER")
    elif qualifier == "RANGE":
        _require(value is None and lower is not None and upper is not None and lower <= upper, "PERCENT_RANGE")
    elif qualifier == "AT_LEAST":
        _require(value is None and lower is not None and upper is None, "PERCENT_BOUND")
    elif qualifier == "AT_MOST":
        _require(value is None and upper is not None and lower is None, "PERCENT_BOUND")
    elif qualifier == "NOT_DISCLOSED":
        _require(value is None and lower is None and upper is None, "PERCENT_NOT_DISCLOSED")
        _text(o.get("missing_reason"), "PERCENT_MISSING_REASON")
    else:
        raise ValueError("PERCENT_QUALIFIER")
    if qualifier != "NOT_DISCLOSED":
        _require(o.get("missing_reason") is None, "PERCENT_MISSING_REASON")
    _text(o.get("denominator_basis"), "DENOMINATOR")
    _day(o.get("observed_as_of"), nullable=True)
    if o.get("denominator_basis") == "CLASS_OUTSTANDING":
        _text(o.get("share_class"), "SHARE_CLASS")
    security = o.get("security_id")
    if security is not None:
        _require(target is not None and securities.get(security) == target, "SECURITY_IDENTITY")


def normalize_packet(packet, identity_document, artifacts):
    """Verify retained bytes and references. No network, inference, or implicit ID creation."""
    p = deepcopy(packet)
    _require(isinstance(p, dict) and p.get("schema_version") == INPUT_SCHEMA, "SCHEMA")
    _text(p.get("dataset_id"), "DATASET_ID")
    _text(p.get("version"), "VERSION")
    _require(p.get("data_kind") in {"SYNTHETIC", "RETAINED"}, "DATA_KIND")
    _require(p.get("publication") in PUBLICATIONS, "PUBLICATION")
    context = p.get("identity_context", {})
    _require(context.get("namespace") == "COMMON_ISSUER", "IDENTITY_NAMESPACE")
    _text(context.get("version"), "IDENTITY_VERSION")
    _require(hashlib.sha256(identity_document).hexdigest() == context.get("registry_hash"), "IDENTITY_HASH")
    try:
        upstream = json.loads(identity_document)
    except (ValueError, UnicodeError):
        raise ValueError("IDENTITY_DOCUMENT") from None
    rows = upstream.get("rows")
    _require(isinstance(rows, list), "IDENTITY_ROWS")
    issuers, codes, securities, listings = set(), {}, {}, {}
    for row in rows:
        issuer = row.get("issuer_id")
        if issuer is None:  # An unresolved upstream row proves no issuer identity.
            continue
        _text(issuer, "IDENTITY_ISSUER")
        issuers.add(issuer)
        for field, index in (("company_id", codes), ("security_id", securities), ("listing_id", listings)):
            key = row.get(field)
            if key is not None:
                _text(key, "IDENTITY_KEY")
                _require(key not in index or index[key] == issuer, "IDENTITY_CONFLICT")
                index[key] = issuer
    entities = _unique(p.get("entities"), lambda x: _text(x.get("entity_id"), "IDENTITY"), "IDENTITY_DUPLICATE")
    evidence = _unique(p.get("evidence"), lambda x: _text(x.get("evidence_id"), "EVIDENCE_ID"), "EVIDENCE_DUPLICATE")
    mentions = _unique(p.get("mentions"), lambda x: _text(x.get("mention_id"), "MENTION_ID"), "MENTION_DUPLICATE")
    for entity_id, entity in entities.items():
        ref = IdentityRef(**entity.get("identity_ref", {}))
        _require(entity_id == ref.issuer_id and entity_id in issuers, "IDENTITY_NOT_UPSTREAM")
        _require(ref.security_id is None or securities.get(ref.security_id) == entity_id, "SECURITY_IDENTITY")
        _require(ref.listing_id is None or listings.get(ref.listing_id) == entity_id, "LISTING_IDENTITY")
        _text(entity.get("display_name"), "ENTITY_NAME")
        _require(entity.get("kind") == "LEGAL_ENTITY", "ENTITY_KIND")
        ids = entity.get("company_ids")
        _require(isinstance(ids, list) and len(ids) == len(set(ids)), "IDENTITY_CODES")
        _require(all(codes.get(c) == entity_id for c in ids), "IDENTITY_CODES")
        _require(entity.get("publication") in PUBLICATIONS, "PUBLICATION")
        entity["company_ids"] = sorted(ids)
        entity["node_id"] = Node.for_issuer(entity_id).node_id
        entity["identity_status"] = "UPSTREAM_REFERENCE_VERIFIED"
    for item in evidence.values():
        sha = item.get("artifact_hash")
        raw = artifacts.get(sha)
        _require(isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == sha, "ARTIFACT_HASH")
        _text(item.get("locator"), "LOCATOR")
        _text(item.get("document_id"), "DOCUMENT_ID")
        url = urlsplit(_text(item.get("url"), "SOURCE_URL"))
        _require(url.scheme in {"https", "http"} and bool(url.netloc) and url.username is None and url.password is None, "SOURCE_URL")
        excerpt = _text(item.get("excerpt"), "EXCERPT")
        _require(" ".join(excerpt.split()) in html_text(raw), "EXCERPT_NOT_FOUND")
        _require(item.get("source_kind") in {"PRIMARY_DISCLOSURE", "FORM_13F", "NEWS", "OTHER"}, "SOURCE_KIND")
        _require(item.get("publication") in PUBLICATIONS, "PUBLICATION")
        for field in ("published", "available", "acquired"):
            _precision(item.get(field))
        _require(item["acquired"]["precision"] != "UNKNOWN", "ACQUISITION_UNKNOWN")
    for mention in mentions.values():
        _text(mention.get("name"), "MENTION_NAME")
        _refs(mention.get("evidence_ids"), evidence)
    assertions = _unique(p.get("assertions"), lambda x: (_text(x.get("assertion_id"), "ASSERTION_ID"), x.get("version")), "ASSERTION_DUPLICATE")
    for (identifier, version), assertion in assertions.items():
        _require(type(version) is int and version >= 1, "ASSERTION_VERSION")
        previous = assertion.get("previous_version")
        _require((version == 1 and previous is None) or (type(previous) is int and previous == version - 1 and (identifier, previous) in assertions), "PREVIOUS_VERSION")
        for side in ("source", "target"):
            entity, mention = assertion.get(f"{side}_entity_id"), assertion.get(f"{side}_mention_id")
            _require((entity in entities and mention is None) or (entity is None and mention in mentions), "ENDPOINT_REFERENCE")
        _require(assertion.get("source_entity_id") is None or assertion.get("source_entity_id") != assertion.get("target_entity_id"), "SELF_RELATIONSHIP")
        _require(assertion.get("type") in TYPES, "RELATIONSHIP_TYPE")
        _require(assertion.get("directness") in {"DIRECT", "INDIRECT", "UNKNOWN"}, "DIRECTNESS")
        _require(assertion.get("capacity") in {"CORPORATE_INVESTMENT", "LEGAL_OWNERSHIP", "BENEFICIAL_OWNERSHIP", "INVESTMENT_DISCRETION", "UNKNOWN"}, "CAPACITY")
        _require(assertion.get("status") in STATUSES, "STATUS")
        _require(assertion.get("publication") in PUBLICATIONS, "PUBLICATION")
        _text(assertion.get("statement"), "STATEMENT")
        _refs(assertion.get("evidence_ids"), evidence)
        obs = assertion.get("observations")
        _unique(obs, lambda x: _text(x.get("observation_id"), "OBSERVATION_ID"), "OBSERVATION_DUPLICATE")
        for observation in obs:
            _observation(observation, assertion.get("target_entity_id"), securities)
        if any(evidence[e]["source_kind"] == "FORM_13F" for e in assertion["evidence_ids"]):
            _require(assertion["type"] == "OWNERSHIP" and assertion["capacity"] == "INVESTMENT_DISCRETION" and all(o["metric"] == "MANAGED_HOLDINGS" for o in obs), "13F_CAPACITY")
        temporal = assertion.get("temporal", {})
        start, end = (_day(temporal.get(k), nullable=True) for k in ("valid_from", "valid_to"))
        _require(start is None or end is None or start < end, "VALID_INTERVAL")
        _day(temporal.get("observed_on"), nullable=True)
        known, reviewed = (_instant(temporal.get(k)) for k in ("system_known_at", "reviewed_at"))
        _require(known <= reviewed, "REVIEW_BEFORE_KNOWLEDGE")
        _require(all(_available(evidence[e]["acquired"], known) for e in assertion["evidence_ids"]), "KNOWLEDGE_BEFORE_ACQUISITION")
        if previous:
            prior = assertions[(identifier, previous)]
            _require(_instant(prior["temporal"]["system_known_at"]) <= known, "VERSION_TIME")
            _require(all(prior.get(k) == assertion.get(k) for k in ("source_entity_id", "target_entity_id", "source_mention_id", "target_mention_id", "type")), "VERSION_IDENTITY_CHANGE")
    _require(isinstance(p.get("paths"), list), "PATHS")
    identifiers = {a[0] for a in assertions}
    for path in p["paths"]:
        _require(isinstance(path, list) and len(path) >= 2 and all(i in identifiers for i in path), "PATH_REFERENCE")
    collection = p.get("collection", {})
    for field in ("target_entity_ids", "reviewed_entity_ids"):
        ids = collection.get(field)
        _require(isinstance(ids, list) and len(ids) == len(set(ids)) and all(i in entities for i in ids), "COLLECTION_IDS")
        collection[field] = sorted(ids)
    _require(set(collection["reviewed_entity_ids"]) <= set(collection["target_entity_ids"]), "REVIEW_SCOPE")
    _text(collection.get("scope"), "COLLECTION_SCOPE")
    _require(collection.get("completeness") in {"PARTIAL", "COMPLETE", "UNKNOWN"}, "COMPLETENESS")
    if collection.get("last_success_at") is not None:
        _instant(collection["last_success_at"])
    zero_refs = collection.get("zero_relationships_evidence_ids", [])
    if zero_refs:
        _refs(zero_refs, evidence)
        _require(collection["completeness"] == "COMPLETE" and not p["assertions"], "ZERO_SCOPE_CONFLICT")
        _day(collection.get("zero_observed_on"))
    # Stable ordering affects no factual content. Unknown interval/ratio values stay null.
    for field, key in (("entities", "entity_id"), ("mentions", "mention_id"), ("evidence", "evidence_id")):
        p[field] = sorted(p[field], key=lambda x: x[key])
    p["assertions"] = sorted(p["assertions"], key=lambda x: (x["assertion_id"], x["version"]))
    for assertion in p["assertions"]:
        assertion["evidence_ids"] = sorted(assertion["evidence_ids"])
        assertion["observations"] = sorted(assertion["observations"], key=lambda x: x["observation_id"])
    return p


def _known(assertion, evidence, cutoff):
    t = assertion["temporal"]
    return (_instant(t["system_known_at"]) <= cutoff and _instant(t["reviewed_at"]) <= cutoff
            and all(_available(evidence[e][field], cutoff) for e in assertion["evidence_ids"]
                    for field in ("published", "available", "acquired")))


def _state(assertion, valid_day):
    temporal = assertion["temporal"]
    start, end = (_day(temporal[k], nullable=True) for k in ("valid_from", "valid_to"))
    observed = _day(temporal["observed_on"], nullable=True)
    if any(o.get("observed_as_of") and _day(o["observed_as_of"]) > valid_day for o in assertion["observations"]):
        return None
    if observed and observed > valid_day:
        return None
    if start and start > valid_day and assertion["status"] != "PLANNED":
        return None
    if end and valid_day >= end:
        return "DISPOSED" if assertion["status"] == "DISPOSED" else "HISTORICAL"
    if assertion["status"] in {"PLANNED", "UNREVIEWED", "CONFLICT"}:
        return assertion["status"]
    if observed != valid_day:
        return "REVIEW_REQUIRED"
    return assertion["status"]


def _observation_conflict(observations):
    seen = {}
    for o in observations:
        basis = tuple(o.get(k) for k in ("metric", "denominator_basis", "security_id", "share_class", "observed_as_of"))
        measurement = tuple(o.get(k) for k in ("value", "lower", "upper", "qualifier"))
        if o["qualifier"] == "NOT_DISCLOSED":
            continue
        if basis in seen and seen[basis] != measurement:
            return True
        seen[basis] = measurement
    return False


def _projection(row, fields):
    return {field: deepcopy(row.get(field)) for field in fields.split()}


OBSERVATION_FIELDS = "observation_id metric value lower upper qualifier unit denominator_basis security_id share_class observed_as_of missing_reason"
TEMPORAL_FIELDS = "valid_from valid_to observed_on system_known_at reviewed_at"
ASSERTION_FIELDS = "assertion_id version previous_version source_entity_id target_entity_id source_mention_id target_mention_id type directness capacity status statement evidence_ids publication"


def _claim_projection(assertion):
    out = _projection(assertion, ASSERTION_FIELDS)
    out["temporal"] = _projection(assertion["temporal"], TEMPORAL_FIELDS)
    out["observations"] = [_projection(o, OBSERVATION_FIELDS) for o in assertion["observations"]]
    return out


def _claims_conflict(claims, day):
    return (_observation_conflict([o for a in claims for o in a["observations"]])
            or len({a["directness"] for a in claims}) > 1
            or len({a["capacity"] for a in claims}) > 1
            or len({_state(a, day) for a in claims}) > 1)


def company_view(bundle, *, entity_id, valid_on, knowledge_at, generated_at,
                 relationship_type=None, public=False, max_bytes=MAX_VIEW_BYTES):
    """Project a validated packet. Filters never change stored facts or other engines."""
    _require(bundle.get("schema_version") == INPUT_SCHEMA, "SCHEMA")
    day, cutoff, generated = _day(valid_on), _instant(knowledge_at), _instant(generated_at)
    _require(cutoff <= generated, "GENERATION_BEFORE_KNOWLEDGE")
    _require(relationship_type is None or relationship_type in TYPES, "RELATIONSHIP_TYPE")
    entities = {e["entity_id"]: e for e in bundle["entities"]}
    evidence = {e["evidence_id"]: e for e in bundle["evidence"]}
    _require(entity_id in entities, "QUERY_IDENTITY")
    if public:
        _require(bundle.get("publication") == "PUBLIC_APPROVED", "PUBLIC_NOT_APPROVED")
    latest, unavailable = {}, 0
    for assertion in bundle["assertions"]:
        if not _known(assertion, evidence, cutoff):
            if entity_id in (assertion["source_entity_id"], assertion["target_entity_id"]):
                unavailable += 1
            continue
        old = latest.get(assertion["assertion_id"])
        if old is None or old["version"] < assertion["version"]:
            latest[assertion["assertion_id"]] = assertion
    visible = {key: value for key, value in latest.items() if _state(value, day) is not None}
    global_groups = {}
    for assertion in visible.values():
        key = (assertion["type"], assertion["source_entity_id"], assertion["target_entity_id"])
        global_groups.setdefault(key, []).append(assertion)
    conflicting_ids = {a["assertion_id"] for claims in global_groups.values()
                       if _claims_conflict(claims, day) for a in claims}
    grouped, unresolved = {}, []
    used_entities, used_evidence = {entity_id}, set()
    for assertion in sorted(visible.values(), key=lambda a: a["assertion_id"]):
        source, target = assertion["source_entity_id"], assertion["target_entity_id"]
        if entity_id not in (source, target):
            continue
        used_evidence.update(assertion["evidence_ids"])
        if public:
            _require(assertion["publication"] == "PUBLIC_APPROVED", "PUBLIC_ASSERTION")
        if source is None or target is None:
            unresolved.append(_claim_projection(assertion))
            continue
        used_entities.update((source, target))
        key = (assertion["type"], source, target)
        grouped.setdefault(key, []).append(assertion)
    relationships = []
    for (kind, source, target), claims in sorted(grouped.items()):
        observations = [_projection(o, OBSERVATION_FIELDS) for a in claims for o in a["observations"]]
        states = {_state(a, day) for a in claims}
        conflict = _claims_conflict(claims, day)
        first = claims[0]
        state = "CONFLICT" if conflict else next(iter(states))
        relationship = {
            "relationship_id": stable_id("ownership", kind, source, target),
            "source_entity_id": source, "target_entity_id": target, "type": kind,
            "direction": "SOURCE_TO_TARGET", "relative_direction": "OUTGOING" if source == entity_id else "INCOMING",
            "directness": first["directness"] if not conflict else "UNKNOWN",
            "capacity": first["capacity"] if not conflict else "UNKNOWN", "state": state,
            "version": digest([_claim_projection(a) for a in claims]),
            "assertions": [_claim_projection(a) for a in claims],
            "observations": observations, "temporal": _projection(first["temporal"], TEMPORAL_FIELDS),
            "validity_status": "OBSERVED_ON_QUERY_DATE" if first["temporal"]["observed_on"] == valid_on else "VALIDITY_UNCONFIRMED",
            "positive_ownership": any(o["metric"] == "SHARE_CAPITAL" and
                ((o.get("value") is not None and Decimal(o["value"]) > 0) or
                 (o.get("lower") is not None and Decimal(o["lower"]) > 0)) for o in observations)
        }
        if (kind != "OWNERSHIP" or state not in {"VERIFIED", "COMPLETED"}
                or not any(o["metric"] == "SHARE_CAPITAL" and o["qualifier"] != "NOT_DISCLOSED" for o in observations)):
            relationship["positive_ownership"] = None
        relationship["history"] = [_claim_projection(a) for a in bundle["assertions"]
            if a["assertion_id"] in {c["assertion_id"] for c in claims} and _known(a, evidence, cutoff)]
        used_evidence.update(e for a in relationship["history"] for e in a["evidence_ids"])
        if public:
            _require(all(a["publication"] == "PUBLIC_APPROVED" for a in relationship["history"]), "PUBLIC_HISTORY")
        relationships.append(relationship)
    paths, seen_paths, cyclic, duplicate = [], set(), 0, 0
    for path in bundle["paths"]:
        key = tuple(path)
        if key in seen_paths:
            duplicate += 1
            continue
        seen_paths.add(key)
        if any(i not in visible or i in conflicting_ids for i in path):
            continue
        claims = [visible[i] for i in path]
        if any(_state(a, day) not in {"VERIFIED", "COMPLETED"} or a["directness"] != "DIRECT" for a in claims):
            continue
        nodes = [claims[0]["source_entity_id"]] + [a["target_entity_id"] for a in claims]
        if None in nodes or any(claims[i]["target_entity_id"] != claims[i+1]["source_entity_id"] for i in range(len(claims)-1)):
            continue
        if len(nodes) != len(set(nodes)):
            cyclic += 1
            continue
        if entity_id not in nodes:
            continue
        if public:
            _require(all(a["publication"] == "PUBLIC_APPROVED" for a in claims), "PUBLIC_PATH")
        used_entities.update(nodes)
        used_evidence.update(e for a in claims for e in a["evidence_ids"])
        paths.append({"assertion_ids": path[:], "entity_ids": nodes, "economic_ownership_percent": None, "assertions": [_claim_projection(a) for a in claims]})
    all_count = len(relationships)
    filtered = [r for r in relationships if relationship_type is None or r["type"] == relationship_type]
    collection = _projection(bundle["collection"], "target_entity_ids reviewed_entity_ids scope completeness last_success_at")
    # A later review batch is not historical system knowledge.
    if collection["last_success_at"] is None or _instant(collection["last_success_at"]) > cutoff:
        collection["reviewed_entity_ids"] = []
        collection["last_success_at"] = None
    collection["last_failure"] = None  # Attempt receipts are separate; no arbitrary log/error text in views.
    used_mentions = {a[k] for a in unresolved for k in ("source_mention_id", "target_mention_id") if a[k]}
    mentions = [_projection(m, "mention_id name evidence_ids") for m in bundle["mentions"] if m["mention_id"] in used_mentions]
    used_evidence.update(e for m in mentions for e in m["evidence_ids"])
    _require(all(_available(evidence[e][field], cutoff) for m in mentions for e in m["evidence_ids"]
                 for field in ("published", "available", "acquired")), "MENTION_NOT_AVAILABLE")
    reviewed = entity_id in collection["reviewed_entity_ids"]
    zero_refs = bundle["collection"].get("zero_relationships_evidence_ids", [])
    zero_verified = (reviewed and bool(zero_refs) and bundle["collection"].get("zero_observed_on") == valid_on
                     and all(_available(evidence[e][field], cutoff) for e in zero_refs
                             for field in ("published", "available", "acquired")))
    if zero_verified:
        used_evidence.update(zero_refs)
        collection["zero_relationships_evidence_ids"] = zero_refs[:]
        collection["zero_observed_on"] = valid_on
    if not reviewed:
        collection_state = "NOT_COLLECTED"
    elif relationship_type and all_count and not filtered:
        collection_state = "FILTER_EMPTY"
    elif zero_verified:
        collection_state = "VERIFIED_ZERO_IN_SCOPE"
    elif not relationships and not unresolved:
        collection_state = "NOT_FOUND_IN_REVIEWED_SCOPE"
    else:
        collection_state = "PARTIAL_REVIEW" if collection["completeness"] != "COMPLETE" else "REVIEWED_SCOPE"
    if public:
        _require(all(entities[i]["publication"] == "PUBLIC_APPROVED" for i in used_entities | set(collection["target_entity_ids"])), "PUBLIC_ENTITY")
        _require(all(evidence[i]["publication"] == "PUBLIC_APPROVED" for i in used_evidence), "PUBLIC_EVIDENCE")
    evidence_fields = "evidence_id source_kind url document_id locator artifact_hash published available acquired source_period publication"
    out = {
        "schema_version": VIEW_SCHEMA, "dataset_id": bundle["dataset_id"], "dataset_version": bundle["version"],
        "dataset_hash": digest(bundle), "identity_context": _projection(bundle["identity_context"], "namespace version registry_hash"),
        "query_as_of": {"valid_on": valid_on, "knowledge_at": knowledge_at}, "generated_at": generated_at,
        "entity_context": {"entity_id": entity_id, "node_id": entities[entity_id]["node_id"]},
        "entities": [_projection(entities[i], "entity_id display_name kind company_ids identity_ref node_id identity_status publication") for i in sorted(used_entities)],
        "relationships": filtered, "unresolved_assertions": unresolved, "mentions": mentions,
        "evidence": [_projection(evidence[i], evidence_fields) for i in sorted(used_evidence)],
        "confirmed_paths": sorted(paths, key=lambda p: p["assertion_ids"]),
        "diagnostics": {"not_available_assertions": unavailable, "cyclic_paths": cyclic, "duplicate_paths": duplicate},
        "collection": collection,
        "collection_state": collection_state, "publication": bundle["publication"],
        "counts": {"legal_entities": len(used_entities), "code_rows": sum(len(entities[i]["company_ids"]) for i in used_entities),
                   "relationships": all_count, "filtered_relationships": len(filtered),
                   "ownership_observations": sum(len(r["observations"]) for r in relationships),
                   "unresolved_assertions": len(unresolved)},
        "relationship_denominator": None, "relationship_coverage": None,
        "historical_system_pit": False,
        "pit_reason": "UPSTREAM_IDENTITY_HISTORY_NOT_PROVEN",
        "query_mode": "RETROSPECTIVE" if cutoff.date() > day else "SYSTEM_ASOF_QUERY",
    }
    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_VIEW_BYTES and len(json_bytes(out)) <= max_bytes, "VIEW_SIZE")
    return out


def merge_update(previous, incoming, *, outcome, attempted_at):
    """A separate attempt receipt cannot rewrite the last good dataset or its clocks."""
    _instant(attempted_at)
    _require(outcome in {"SUCCESS", "FAILED", "PARTIAL", "PARSE_FAILED"}, "COLLECTION_OUTCOME")
    attempt = {"outcome": outcome, "attempted_at": attempted_at}
    if outcome != "SUCCESS":
        return {"dataset": deepcopy(previous), "attempt": attempt}
    _require(isinstance(incoming, dict), "UPDATE_REQUIRED")
    _require(all(previous.get(k) == incoming.get(k) for k in ("schema_version", "dataset_id", "identity_context", "data_kind")), "UPDATE_CONTEXT")
    merged = deepcopy(previous)
    for field, keys in (("entities", ("entity_id",)), ("mentions", ("mention_id",)), ("evidence", ("evidence_id",)), ("assertions", ("assertion_id", "version"))):
        index = {tuple(row[k] for k in keys): row for row in previous[field]}
        for row in incoming[field]:
            key = tuple(row[k] for k in keys)
            _require(key not in index or index[key] == row, "IMMUTABLE_RECORD")
            index[key] = row
        merged[field] = [deepcopy(index[k]) for k in sorted(index)]
    merged["paths"] = [list(p) for p in sorted({tuple(p) for p in previous["paths"] + incoming["paths"]})]
    merged["collection"] = deepcopy(incoming["collection"])
    merged["version"] = incoming["version"]
    return {"dataset": merged, "attempt": attempt}
