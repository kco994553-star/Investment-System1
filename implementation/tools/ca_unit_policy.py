"""CA-UNIT-v1.0: reviewed primary evidence, independent of ticker/rank/cutoff.

Provider adjustment events are discovery signals, not share-count authority.
Only contemporaneously public evidence can change share quantities. All input
quantities and source dates survive in the candidate's reconciliation record.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import math
import re
from datetime import datetime, timezone


def dt(value):
    value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def document_errors(store, doc, as_of):
    errors = []
    aid = doc.get("artifact_id")
    if not aid or not store.has(aid):
        return ["PRIMARY_DOCUMENT_MISSING"]
    body = store.get_bytes(aid)
    manifest = store.get_manifest(aid)
    if hashlib.sha256(body).hexdigest() != doc.get("sha256") or manifest.get("sha256") != doc.get("sha256"):
        errors.append("PRIMARY_DOCUMENT_HASH_MISMATCH")
    if manifest.get("source_url") != doc.get("url"):
        errors.append("PRIMARY_DOCUMENT_URL_MISMATCH")
    if not doc.get("published_at") or dt(doc["published_at"]) > as_of:
        errors.append("PRIMARY_DOCUMENT_NOT_PUBLIC_AT_AS_OF")
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", text)).replace("\xa0", " ")).strip()
    if not doc.get("quotes") or any(q not in text for q in doc["quotes"]):
        errors.append("PRIMARY_DOCUMENT_QUOTE_MISMATCH")
    return errors


def provider_events(store, symbol, chart_range):
    """Read event discovery independently of whether the price feed is raw-close."""
    aid = f"yahoo_events:{symbol}:{chart_range}"
    if not store.has(aid):
        return []
    result = json.loads(store.get_bytes(aid))["chart"]["result"][0]
    out = []
    for e in (result.get("events") or {}).get("splits", {}).values():
        factor = float(e["numerator"]) / float(e["denominator"])
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("INVALID_PROVIDER_EVENT_FACTOR")
        out.append((datetime.fromtimestamp(e["date"], timezone.utc), factor))
    return sorted(out)


def reconcile(store, candidates, overrides, policy, as_of, chart_range="5y"):
    """Apply verified events BEFORE any ranking; unresolved candidates block Official.

    A reviewed event scopes a CIK and exact security symbols (including classes
    without a quotation). Measurement and publication dates remain separate.
    A filing published after an event with a pre-event measurement date has
    ambiguous units until its filing evidence is reviewed; never assume that
    publication alone proves a retrospective adjustment.
    """
    applied, unresolved = [], []
    policy_ok = (policy or {}).get("policy_version") == "CA-UNIT-v1.0" and (policy or {}).get("approved") is True
    for original in candidates:
        cid, cik = original["company_id"], str(original.get("cik") or "").zfill(10)
        if original.get("ca_unit"):
            applied.extend(original["ca_unit"]["events"])
            continue  # idempotent: normalized candidate carries its original provenance
        available = original.get("shares_available_at")
        if not available:
            unresolved.append({"company_id": cid, "reason": "SHARE_PUBLICATION_DATE_MISSING"})
            continue
        available = dt(available)
        relevant = []
        measurements = [dt(x["measurement_date"]) for x in original.get("security_components", [])
                        if x.get("measurement_date")]
        discovery_start = min([available] + measurements)
        symbols = {original["ticker"]} | {c.get("symbol") for c in original.get("security_components", []) if c.get("symbol")}
        for symbol in sorted(symbols):
            for when, factor in provider_events(store, symbol, chart_range):
                if discovery_start < when <= as_of and factor != 1:
                    relevant.append((symbol, when, factor))
        # Primary events also apply when the vendor omitted the event entirely.
        reviewed = [e for e in (policy or {}).get("events", []) if str(e.get("cik")).zfill(10) == cik
                    and discovery_start < dt(e["unit_effective_at"]) <= as_of]
        for e in reviewed:
            for symbol in symbols & set(e.get("symbols", [])):
                if not any(s == symbol and w.date() == dt(e["provider_event_date"]).date() for s, w, _ in relevant):
                    relevant.append((symbol, dt(e["provider_event_date"]), None))
        if not relevant:
            continue
        c = copy.deepcopy(original)
        records, failures, used = [], [], set()
        for symbol, when, provider_factor in relevant:
            matches = [e for e in reviewed if symbol in e.get("symbols", [])
                       and e["provider_event_date"][:10] == when.date().isoformat()]
            errors = [] if policy_ok else ["CA_UNIT_POLICY_NOT_APPROVED"]
            if len(matches) != 1:
                failures.append({"symbol": symbol, "event_date": when.isoformat(),
                                 "provider_factor": provider_factor, "errors": errors + ["UNREVIEWED_OR_AMBIGUOUS_EVENT"]})
                continue
            event = matches[0]
            if event["event_id"] in used:
                continue
            used.add(event["event_id"])
            if available >= dt(event["unit_effective_at"]) and event.get("kind") != "SPINOFF_PARENT_UNCHANGED":
                errors.append("POST_EVENT_FILING_UNIT_AMBIGUOUS")
            if not original.get("price_observed_at") or dt(original["price_observed_at"]) < dt(event["unit_effective_at"]):
                errors.append("POST_ACTION_QUOTE_REQUIRED")
            for doc in event.get("documents", []):
                errors.extend(document_errors(store, doc, as_of))
            if not event.get("documents") or not event.get("security_basis"):
                errors.append("SECURITY_OR_PRIMARY_EVIDENCE_MISSING")
            kind = event.get("kind")
            if kind not in {"SPLIT", "STOCK_DIVIDEND", "SPINOFF_PARENT_UNCHANGED", "SUCCESSOR_ACTUAL_SHARES"}:
                errors.append("UNAPPROVED_EVENT_TYPE")
            factor = event.get("share_factor")
            if kind in {"SPLIT", "STOCK_DIVIDEND"} and (not isinstance(factor, (int, float)) or not math.isfinite(factor) or factor <= 0):
                errors.append("INVALID_PRIMARY_SHARE_FACTOR")
            if kind == "SPINOFF_PARENT_UNCHANGED" and factor != 1:
                errors.append("SPINOFF_PARENT_FACTOR_MUST_BE_ONE")
            components = c.get("security_components") or []
            if not components or any(not x.get("measurement_date") for x in components):
                errors.append("SHARE_MEASUREMENT_DATE_MISSING")
            if kind == "SUCCESSOR_ACTUAL_SHARES":
                if not event.get("actual_shares") or not event.get("actual_measurement_date") or not event.get("issuer_transition"):
                    errors.append("SUCCESSOR_COUNT_OR_TRANSITION_MISSING")
                elif not math.isfinite(event["actual_shares"]) or event["actual_shares"] <= 0 or dt(event["actual_measurement_date"]) > as_of:
                    errors.append("INVALID_SUCCESSOR_ACTUAL_COUNT")
            if errors:
                failures.append({"symbol": symbol, "event_id": event["event_id"], "errors": errors})
                continue
            before = copy.deepcopy(components)
            if kind in {"SPLIT", "STOCK_DIVIDEND"}:
                for component in components:
                    # All share classes must be explicitly covered, even when unpriced.
                    key = component.get("symbol") or component.get("member")
                    if key not in event["security_scope"]:
                        failures.append({"event_id": event["event_id"], "errors": ["SHARE_CLASS_NOT_COVERED"], "security": key})
                        continue
                    if dt(component["measurement_date"]) >= dt(event["unit_effective_at"]):
                        failures.append({"event_id": event["event_id"], "errors": ["AMBIGUOUS_OR_ALREADY_ADJUSTED_SHARE_UNIT"]})
                        continue
                    component["shares"] *= factor
                    component["unit_effective_at"] = event["unit_effective_at"]
            elif kind == "SUCCESSOR_ACTUAL_SHARES":
                if len(components) != 1:
                    failures.append({"event_id": event["event_id"], "errors": ["SUCCESSOR_CLASS_MAPPING_REQUIRED"]})
                    continue
                components[0]["shares"] = event["actual_shares"]
                components[0]["measurement_date"] = event["actual_measurement_date"]
                components[0]["unit_effective_at"] = event["unit_effective_at"]
            # A spin-off keeps parent quantities unchanged. Provider price
            # adjustment factors are not substituted for the primary share ratio.
            records.append({"event_id": event["event_id"], "company_id": cid, "ticker": original["ticker"],
                            "kind": kind, "provider_factor": provider_factor, "applied_share_factor": factor,
                            "original_components": before, "normalized_components": copy.deepcopy(components),
                            "documents": event["documents"], "unit_effective_at": event["unit_effective_at"]})
        if failures:
            unresolved.append({"company_id": cid, "ticker": original["ticker"], "cik": cik, "failures": failures})
            continue  # transactional per issuer; never apply a partially checked event chain
        c["gate_mcap"] = sum(x["shares"] * x["price"] for x in c["security_components"] if x.get("price"))
        c["shares"] = c["gate_mcap"] / c["price"]
        c["shares_available_at"] = max([available] + [dt(d["published_at"]) for r in records for d in r["documents"]])
        c["shares_basis"] = "CA_UNIT_NORMALIZED:" + str(original.get("shares_basis") or "PIT_SHARES")
        c["ca_unit"] = {"policy": "CA-UNIT-v1.0", "original_shares": original["shares"],
                        "original_shares_basis": original.get("shares_basis"),
                        "original_shares_available_at": available.isoformat(), "events": records}
        ov = copy.deepcopy(overrides.get(cid) or {})
        ov.update(mcap=c["gate_mcap"], status=ov.get("status", "CA_UNIT_NORMALIZED"),
                  classes=c["security_components"], unit_candidate=c)
        overrides[cid] = ov
        applied.extend(records)
    return {"passed": not unresolved, "policy": "CA-UNIT-v1.0", "n_candidates": len(candidates),
            "applied": applied, "unresolved": unresolved,
            "rank_and_cutoff_used": False, "future_evidence_allowed": False}
