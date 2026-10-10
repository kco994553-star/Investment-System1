"""Observed SEC filing timing for display; not a confirmed earnings calendar.

Pure supplied-data processing. The acquisition bound does not prove historical
first publication. No future filing/earnings date, fiscal-quarter assignment,
network request, local storage, or model input is generated here.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any

from ..markets.us import US_LISTINGS


ROLE = "ESTIMATED_PATTERN_NOT_CONFIRMED"
LABEL = "제출 패턴 기반 예상 시기 · 확정 실적 발표일 아님"
BASIS = "OBSERVED_PUBLIC_API_UPPER_BOUND"
_COLUMNS = ("form", "filingDate", "reportDate", "accessionNumber")
_PERIODIC = {"10-Q", "10-K"}
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_ACCN = re.compile(r"(?:[0-9]{10}-[0-9]{2}-[0-9]{6}|[0-9]{18})\Z")
_ACCEPTANCE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} requires a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _cik(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    text = str(value)
    if not text.isascii() or not text.isdigit() or not 0 < len(text) <= 10:
        return None
    return text.zfill(10)


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _accn(value: Any) -> str | None:
    return value.replace("-", "") if isinstance(value, str) and _ACCN.fullmatch(value) else None


def _accepted(value: Any) -> datetime | None:
    if not isinstance(value, str) or not _ACCEPTANCE.fullmatch(value):
        raise ValueError("invalid acceptance time")
    return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")), "accepted_at")


def build_filing_timing_pattern(
    company_id: str,
    submissions: Mapping[str, Any],
    acquired_at: datetime,
    as_of: datetime,
) -> dict[str, Any]:
    """Summarize all supplied recent original 10-Q/10-K filing observations.

    Invalid call arguments raise ValueError. Invalid source content is unavailable
    with fixed reason codes. Valid observations may survive malformed independent
    rows as PARTIAL, but conflicting accessions or multiple originals for a report
    fail the whole pattern instead of selecting an earlier/latest candidate.
    """
    if not isinstance(company_id, str) or company_id not in US_LISTINGS:
        raise ValueError("company_id must belong to the existing US17 TARGET")
    acquired_at = _aware(acquired_at, "acquired_at")
    as_of = _aware(as_of, "as_of")
    cik = US_LISTINGS[company_id]["cik"]
    result: dict[str, Any] = {
        "contract": "SEC_FILING_TIMING_PATTERN", "version": 1,
        "company_id": company_id, "cik": cik, "status": "NOT_AVAILABLE",
        "role": ROLE, "label": LABEL, "source_kind": "SEC_SUBMISSIONS_RECENT",
        "coverage": "SUPPLIED_RECENT_ONLY", "input_row_count": 0,
        "as_of": as_of.isoformat(), "acquired_at": acquired_at.isoformat(),
        "availability": {"available_at": None, "published_at": None,
                         "basis": BASIS, "precision": "CONSERVATIVE",
                         "historical_first_publication": False},
        "confirmed_earnings_date": None, "estimated_exact_date": None,
        "groups": [], "observations": [], "excluded": [], "reason_codes": [],
    }

    def unavailable(reason: str) -> dict[str, Any]:
        result["reason_codes"] = [reason]
        return result

    if acquired_at > as_of:
        return unavailable("NOT_AVAILABLE_AT_AS_OF")
    if not isinstance(submissions, Mapping):
        return unavailable("INVALID_PAYLOAD")
    if "cik" not in submissions:
        return unavailable("MISSING_CIK")
    if _cik(submissions["cik"]) != cik:
        return unavailable("CIK_MISMATCH")
    filings = submissions.get("filings")
    recent = filings.get("recent") if isinstance(filings, Mapping) else None
    if not isinstance(recent, Mapping):
        return unavailable("MISSING_RECENT_FILINGS")
    if any(not isinstance(recent.get(key), list) for key in _COLUMNS):
        return unavailable("INVALID_RECENT_ARRAYS")
    count = len(recent["form"])
    result["input_row_count"] = count
    keys = list(_COLUMNS)
    if "acceptanceDateTime" in recent:
        if not isinstance(recent["acceptanceDateTime"], list):
            return unavailable("INVALID_RECENT_ARRAYS")
        keys.append("acceptanceDateTime")
    if any(len(recent[key]) != count for key in keys):
        return unavailable("MISALIGNED_RECENT_ARRAYS")

    seen: dict[str, dict[str, Any]] = {}
    report_accessions: dict[tuple[str, str], set[str]] = defaultdict(set)
    conflicts: set[str] = set()
    invalid_reasons: set[str] = set()
    observations: list[dict[str, Any]] = []

    def exclude(index: int, reason: str, *, invalid: bool = True) -> None:
        result["excluded"].append({"row": index, "reason": reason})
        if invalid:
            invalid_reasons.add(reason)

    for index in range(count):
        row = {key: recent[key][index] for key in keys}
        row.setdefault("acceptanceDateTime", None)
        form, accn = row["form"], _accn(row["accessionNumber"])
        if accn is not None:
            # SEC's dashed/compact spellings denote the same accession.
            row["accessionNumber"] = f"{accn[:10]}-{accn[10:12]}-{accn[12:]}"
            if accn in seen:
                if seen[accn] != row:
                    conflicts.add("CONFLICTING_ACCESSION")
                continue
            seen[accn] = row
        if not isinstance(form, str):
            exclude(index, "INVALID_FORM")
            continue
        if form not in _PERIODIC:
            exclude(index, "UNSUPPORTED_FORM", invalid=False)
            continue
        filed, reported = _day(row["filingDate"]), _day(row["reportDate"])
        if reported is not None and accn is not None:
            report_accessions[(form, reported.isoformat())].add(accn)
        reasons = []
        if accn is None:
            reasons.append("INVALID_ACCESSION")
        if filed is None:
            reasons.append("INVALID_FILING_DATE")
        if reported is None:
            reasons.append("INVALID_REPORT_DATE")
        if filed is not None and filed > acquired_at.date():
            reasons.append("FILING_AFTER_ACQUISITION")
        if filed is not None and reported is not None and reported > filed:
            reasons.append("REPORT_AFTER_FILING")
        accepted = None
        if row["acceptanceDateTime"] not in (None, ""):
            try:
                accepted = _accepted(row["acceptanceDateTime"])
            except ValueError:
                reasons.append("INVALID_ACCEPTANCE_TIME")
            if accepted is not None and accepted > acquired_at:
                reasons.append("ACCEPTANCE_AFTER_ACQUISITION")
        if reasons:
            for reason in reasons:
                exclude(index, reason)
            continue
        observations.append({
            "form": form, "accession_number": row["accessionNumber"], "accn": accn,
            "report_date": reported.isoformat(), "filing_date": filed.isoformat(),
            "accepted_at": None if accepted is None else accepted.isoformat(),
        })

    if any(len(accessions) > 1 for accessions in report_accessions.values()):
        conflicts.add("AMBIGUOUS_ORIGINAL_FILINGS")
    if conflicts:
        result["reason_codes"] = sorted(conflicts)
        return result
    if not observations:
        result["reason_codes"] = sorted(invalid_reasons) or ["NO_ELIGIBLE_10Q_10K"]
        return result

    observations.sort(key=lambda row: (row["form"], row["report_date"], row["filing_date"], row["accn"]))
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        groups[(observation["form"], observation["report_date"][5:])].append(observation)
    for (form, month_day), rows in sorted(groups.items()):
        days_by_month: dict[int, list[int]] = defaultdict(list)
        for row in rows:
            filed = date.fromisoformat(row["filing_date"])
            days_by_month[filed.month].append(filed.day)
        result["groups"].append({
            "form": form, "report_month_day": month_day,
            "observation_count": len(rows),
            "observed_filing_windows": [
                {"month": month, "day_min": min(days), "day_max": max(days), "count": len(days)}
                for month, days in sorted(days_by_month.items())
            ],
        })
    result["observations"] = observations
    result["status"] = "PARTIAL" if invalid_reasons else "READY"
    result["reason_codes"] = sorted(invalid_reasons)
    result["availability"]["available_at"] = acquired_at.isoformat()
    return result
