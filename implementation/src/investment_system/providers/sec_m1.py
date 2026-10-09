"""Offline, bounded SEC inputs with conservative observation availability.

This M1 format is not a historical first-publication proof or a QGV snapshot.
It retains eligible input facts, not an exact per-normalized-field extraction trace.
The JSON stamp permits unknown published_at; it is not a legacy DataStamp consumer.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any

from ..contracts.models import _to_json
from ..markets.us import US_LISTINGS
from .sec_companyfacts import facts_to_raw


BASIS = "OBSERVED_PUBLIC_API_UPPER_BOUND"
SUPPORTED_FORMS = {
    "10-K": {"10-K", "10-K/A", "20-F", "20-F/A", "40-F"},
    "10-Q": {"10-Q", "10-Q/A", "6-K"},
}
# Exact duration concepts consumed by facts_to_raw; balance-sheet/share counts
# are instant facts and intentionally do not require a start date.
DURATION_CONCEPTS = {
    ("us-gaap", concept) for concept in (
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "NetIncomeLoss", "OperatingIncomeLoss", "FreeCashFlow",
        "NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment",
        "EarningsPerShareDiluted", "EarningsPerShareBasic",
    )
} | {("ifrs-full", "Revenue"), ("ifrs-full", "ProfitLoss")}


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} requires a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _cik(value: Any) -> str | None:
    text = str(value).strip()
    return text.zfill(10) if text.isascii() and text.isdigit() and 0 < len(text) <= 10 else None


def _safe(value: Any) -> Any:
    """Keep malformed source values auditable without producing NaN JSON."""
    value = _to_json(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sort_key(value: dict) -> str:
    return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def build_input(
    company_id: str, companyfacts: dict, submissions: dict, acquired_at: datetime, as_of: datetime,
    *, form_filter: str = "10-K",
) -> dict:
    """Validate retained payloads, restrict facts, then reuse the existing converter.

    Invalid call arguments raise ValueError. Untrusted or insufficient source
    content returns NOT_AVAILABLE with retained exclusion/lineage candidates.
    Every availability bound is at least acquired_at. Acceptance is metadata,
    never exact source publication; acceptance after acquisition is inconsistent.
    """
    if company_id not in US_LISTINGS:
        raise ValueError("company_id must belong to the existing US17 TARGET")
    if form_filter not in {"10-K", "10-Q"}:
        raise ValueError("form_filter must be 10-K or 10-Q")
    acquired_at, as_of = _aware(acquired_at, "acquired_at"), _aware(as_of, "as_of")
    cik = US_LISTINGS[company_id]["cik"]
    result = {
        "contract": "SEC_M1_INPUT", "version": 1, "company_id": company_id, "cik": cik,
        "form_filter": form_filter,
        "status": "NOT_AVAILABLE", "as_of": as_of.isoformat(), "acquired_at": acquired_at.isoformat(),
        "availability": {"available_at": None, "basis": BASIS, "precision": "CONSERVATIVE",
                         "published_at": None, "historical_first_publication": False},
        "raw_fundamentals": None, "filings": [], "selected_input_facts": [],
        "excluded": [], "revision_candidates": [],
    }
    for source, payload in (("companyfacts", companyfacts), ("submissions", submissions)):
        if not isinstance(payload, dict):
            result["excluded"].append({"source": source, "reason": "INVALID_PAYLOAD"})
        elif "cik" not in payload:
            result["excluded"].append({"source": source, "reason": "MISSING_CIK"})
        elif _cik(payload["cik"]) != cik:
            result["excluded"].append({"source": source, "reason": "CIK_MISMATCH"})
    if result["excluded"]:
        return result

    filings_container = submissions.get("filings")
    rec = filings_container.get("recent") if isinstance(filings_container, dict) else None
    if not isinstance(rec, dict):
        result["excluded"].append({"source": "submissions", "reason": "MISSING_RECENT_FILINGS"})
        return result
    columns = {k: v for k, v in rec.items() if isinstance(v, list)}
    count = max((len(columns.get(k, [])) for k in ("form", "filingDate", "accessionNumber")), default=0)
    filing_index: dict[str, list[dict]] = {}
    for i in range(count):
        original = {k: values[i] for k, values in columns.items() if i < len(values)}
        form = str(original.get("form") or "").strip().upper()
        accn = str(original.get("accessionNumber") or "").strip().replace("-", "")
        filed = _day(original.get("filingDate"))
        reasons = []
        if not accn:
            reasons.append("MISSING_ACCESSION")
        if filed is None:
            reasons.append("INVALID_FILING_DATE")
        if form not in SUPPORTED_FORMS[form_filter]:
            reasons.append("UNSUPPORTED_FORM")
        accepted = None
        acceptance = original.get("acceptanceDateTime")
        if acceptance not in (None, ""):
            try:
                if not isinstance(acceptance, str):
                    raise ValueError("invalid acceptance")
                accepted = _aware(datetime.fromisoformat(acceptance.replace("Z", "+00:00")), "acceptance")
            except ValueError:
                reasons.append("INVALID_ACCEPTANCE_TIME")
        if accepted is not None and accepted > acquired_at:
            reasons.append("ACCEPTANCE_AFTER_ACQUISITION")
        if filed is not None and filed > acquired_at.date():
            reasons.append("FILING_AFTER_ACQUISITION")
        available = max(acquired_at, accepted) if accepted is not None else acquired_at
        if available > as_of:
            reasons.append("NOT_AVAILABLE_AT_AS_OF")
        filing = {
            "accn": accn, "accession_number": original.get("accessionNumber"), "form": form,
            "filing_date": original.get("filingDate"),
            "accepted_at": None if accepted is None else accepted.isoformat(),
            "published_at": None, "available_at": available.isoformat(),
            "availability_basis": BASIS, "formal_amendment": form.endswith("/A"),
            "parent_accession": None, "eligible": not reasons,
            "exclusion_reasons": reasons, "source_row": _safe(original),
        }
        result["filings"].append(filing)
        filing_index.setdefault(accn, []).append(filing)
        for reason in reasons:
            result["excluded"].append({"source": "filing", "accn": accn, "reason": reason})
    result["filings"].sort(key=_sort_key)

    winners: dict[tuple, dict] = {}
    candidates = result["revision_candidates"]
    facts = companyfacts.get("facts") or {}
    if not isinstance(facts, dict):
        result["excluded"].append({"source": "companyfacts", "reason": "INVALID_FACTS"})
        return result
    for taxonomy, concepts in sorted(facts.items()):
        if not isinstance(concepts, dict):
            continue
        for concept, node in sorted(concepts.items()):
            if not isinstance(node, dict) or not isinstance(node.get("units"), dict):
                continue
            for unit, rows in sorted(node["units"].items()):
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        result["excluded"].append({"source": "fact", "reason": "INVALID_FACT_ROW"})
                        continue
                    accn = str(row.get("accn") or "").strip().replace("-", "")
                    form = str(row.get("form") or "").strip().upper()
                    filed, end = _day(row.get("filed")), _day(row.get("end"))
                    start = _day(row.get("start")) if row.get("start") else None
                    reasons = []
                    if not accn:
                        reasons.append("MISSING_ACCESSION")
                    if filed is None or end is None:
                        reasons.append("MISSING_OR_INVALID_FACT_DATE")
                    if form not in SUPPORTED_FORMS[form_filter]:
                        reasons.append("UNSUPPORTED_FORM")
                    if (taxonomy, concept) in DURATION_CONCEPTS and start is None:
                        reasons.append("MISSING_DURATION_START")
                    if row.get("fy") is not None and type(row["fy"]) not in (int, str):
                        reasons.append("INVALID_FISCAL_YEAR")
                    try:
                        if row.get("val") is None or isinstance(row.get("val"), bool):
                            raise ValueError("invalid value")
                        value = float(row["val"])
                        if not math.isfinite(value):
                            raise ValueError("nonfinite value")
                    except (TypeError, ValueError, OverflowError):
                        value = None
                        reasons.append("INVALID_FACT_VALUE")
                    if row.get("start") and start is None:
                        reasons.append("INVALID_DURATION")
                    if start is not None and end is not None:
                        days = (end - start).days
                        if (form_filter == "10-K" and days < 300) or (form_filter == "10-Q" and not 60 <= days <= 140):
                            reasons.append("INVALID_DURATION")
                    if filed is not None and end is not None and end > filed:
                        reasons.append("PERIOD_AFTER_FILING")
                    matches = filing_index.get(accn, [])
                    distinct = {_sort_key(f) for f in matches}
                    filing = matches[0] if len(distinct) == 1 else None
                    if not matches:
                        reasons.append("ACCESSION_NOT_INDEXED")
                    elif filing is None:
                        reasons.append("AMBIGUOUS_FILING")
                    elif form != filing["form"] or row.get("filed") != filing["filing_date"]:
                        reasons.append("FILING_IDENTITY_MISMATCH")
                    elif not filing["eligible"]:
                        reasons.extend(filing["exclusion_reasons"])
                    candidate = {
                        "taxonomy": taxonomy, "concept": concept, "unit": unit,
                        "start": row.get("start") or "", "end": row.get("end"),
                        "value": value, "accn": accn, "form": form, "filed": row.get("filed"),
                        "accepted_at": None if filing is None else filing["accepted_at"],
                        "available_at": None if filing is None else filing["available_at"],
                        "formal_amendment": form.endswith("/A"), "parent_accession": None,
                        "eligible": not reasons, "exclusion_reasons": sorted(set(reasons)),
                        "source_row": _safe(copy.deepcopy(row)),
                    }
                    candidates.append(candidate)

    # A same-filing contradiction has no defensible deterministic value winner.
    groups: dict[tuple, list[dict]] = {}
    for candidate in candidates:
        if candidate["eligible"]:
            key = tuple(candidate[k] for k in ("taxonomy", "concept", "unit", "start", "end", "accn"))
            groups.setdefault(key, []).append(candidate)
    for rows in groups.values():
        if len({r["value"] for r in rows}) > 1:
            for row in rows:
                row["eligible"] = False
                row["exclusion_reasons"].append("AMBIGUOUS_FACT_VALUES")
    periods: dict[tuple, list[dict]] = {}
    for candidate in candidates:
        if candidate["eligible"] or "AMBIGUOUS_FACT_VALUES" in candidate["exclusion_reasons"]:
            key = tuple(candidate[k] for k in ("taxonomy", "concept", "unit", "start", "end"))
            periods.setdefault(key, []).append(candidate)
    for rows in periods.values():
        eligible = [r for r in rows if r["eligible"]]
        if not eligible:
            continue
        latest_day = max(r["filed"] for r in eligible)
        latest = {r["accn"]: r for r in eligible if r["filed"] == latest_day}
        times = [r["accepted_at"] for r in latest.values()]
        if len(latest) > 1 and (None in times or len(set(times)) != len(times)):
            for row in eligible:
                row["eligible"] = False
                row["exclusion_reasons"].append("AMBIGUOUS_REVISION_ORDER")
            continue
        winner = max(latest.values(), key=lambda r: r["accepted_at"] or "")
        conflicts = [r for r in rows if "AMBIGUOUS_FACT_VALUES" in r["exclusion_reasons"]]
        resolves_conflicts = all(
            winner["filed"] > conflict["filed"] or (
                winner["filed"] == conflict["filed"]
                and winner["accepted_at"] is not None and conflict["accepted_at"] is not None
                and winner["accepted_at"] > conflict["accepted_at"]
            ) for conflict in conflicts
        )
        if not resolves_conflicts:
            for row in eligible:
                row["eligible"] = False
                row["exclusion_reasons"].append("AMBIGUOUS_FACT_VALUES")
    for candidate in candidates:
        if not candidate["eligible"]:
            for reason in candidate["exclusion_reasons"]:
                result["excluded"].append({"source": "fact", "accn": candidate["accn"],
                                           "taxonomy": candidate["taxonomy"], "concept": candidate["concept"],
                                           "reason": reason})
            continue
        key = tuple(candidate[k] for k in ("taxonomy", "concept", "unit", "start", "end"))
        rank = lambda r: (r["filed"], r["accepted_at"] or "", r["accn"], _sort_key(r))
        if key not in winners or rank(candidate) > rank(winners[key]):
            winners[key] = candidate
    candidates.sort(key=_sort_key)
    result["excluded"].sort(key=_sort_key)
    selected = sorted(winners.values(), key=_sort_key)
    result["selected_input_facts"] = copy.deepcopy(selected)
    if not selected:
        return result

    filtered = {k: copy.deepcopy(v) for k, v in companyfacts.items() if k != "facts"}
    filtered["facts"] = {}
    for row in selected:
        units = filtered["facts"].setdefault(row["taxonomy"], {}).setdefault(row["concept"], {"units": {}})["units"]
        units.setdefault(row["unit"], []).append(copy.deepcopy(row["source_row"]))
    raw = _to_json(asdict(facts_to_raw(company_id, cik, filtered, as_of, synthetic=False, form_filter=form_filter)))
    if not any(raw.get(k) is not None for k in ("revenue", "ebit", "fcf", "net_income", "equity", "cash", "total_debt", "shares", "eps")):
        result["excluded"].append({"source": "companyfacts", "reason": "NO_SUPPORTED_NORMALIZED_FACTS"})
        return result
    available = max(row["available_at"] for row in selected)
    binding = hashlib.sha256(_sort_key({"company_id": company_id, "as_of": as_of.isoformat(),
                                      "acquired_at": acquired_at.isoformat(), "facts": selected}).encode()).hexdigest()
    raw["source_kind"] = "OBSERVED_RAW_INPUT"
    raw["stamp"].update({
        "data_stamp_id": f"sec_m1_{company_id}_{binding}", "source_provider": "sec-m1-input",
        "published_at": None, "available_at": available, "observed_at": acquired_at.isoformat(),
        "estimated": True, "estimation_method": BASIS,
        "quality_flags": sorted(set(raw["stamp"]["quality_flags"]) | {"CONSERVATIVE_AVAILABILITY", "FIRST_PUBLICATION_UNKNOWN"}),
    })
    result["availability"]["available_at"] = available
    result["status"], result["raw_fundamentals"] = "READY", raw
    return _safe(result)
