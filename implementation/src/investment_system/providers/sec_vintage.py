"""PIT Fundamental Vintage Resolver. NEW IMPLEMENTATION.

Selection rule (deterministic):
1. Drop rows with filed > as_of (future filings and later amendments).
2. Apply form_filter when form is present.
3. Group remaining rows by (fy, fp, end).
4. Inside a group pick the latest filed (amendment only if already filed).
5. Across groups pick latest period end, then latest filed, then latest accn.
Do not interpolate missing values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .sec_companyfacts import _form_ok, _parse_iso


@dataclass(frozen=True)
class FactVintage:
    taxonomy: str
    concept: str
    unit: str
    value: float
    filed: datetime
    form: str
    fy: Any
    fp: str
    start: str
    end: str
    accn: str
    amended: bool
    labeled: bool


def _row_filed(row: dict[str, Any]) -> datetime | None:
    filed = row.get("filed") or row.get("end")
    if not filed:
        return None
    try:
        return _parse_iso(str(filed) + ("T00:00:00+00:00" if "T" not in str(filed) else ""))
    except ValueError:
        return None


def iter_fact_rows(payload: dict[str, Any], taxonomy: str, concept: str, unit: str) -> list[dict[str, Any]]:
    node = payload.get("facts", {}).get(taxonomy, {}).get(concept, {})
    return list(node.get("units", {}).get(unit, []) or [])


def _duration_ok(row: dict[str, Any], form_filter: str | None) -> bool:
    start = row.get("start")
    end = row.get("end")
    if not start or not end:
        return True
    try:
        days = (date.fromisoformat(str(end)[:10]) - date.fromisoformat(str(start)[:10])).days
    except ValueError:
        return True
    if form_filter and str(form_filter).upper().startswith("10-K"):
        return days >= 300
    if form_filter and str(form_filter).upper().startswith("10-Q"):
        return 60 <= days <= 140
    return True


def resolve_vintages(
    payload: dict[str, Any],
    taxonomy: str,
    concept: str,
    unit: str,
    as_of: datetime,
    form_filter: str | None = "10-K",
) -> list[FactVintage]:
    out: list[FactVintage] = []
    for row in iter_fact_rows(payload, taxonomy, concept, unit):
        filed = _row_filed(row)
        if filed is None or filed > as_of or row.get("val") is None:
            continue
        if not _form_ok(row, form_filter):
            continue
        if not _duration_ok(row, form_filter):
            continue
        form = str(row.get("form") or "")
        out.append(
            FactVintage(
                taxonomy=taxonomy,
                concept=concept,
                unit=unit,
                value=float(row["val"]),
                filed=filed,
                form=form,
                fy=row.get("fy"),
                fp=str(row.get("fp") or ""),
                start=str(row.get("start") or ""),
                end=str(row.get("end") or ""),
                accn=str(row.get("accn") or ""),
                amended=form.endswith("/A"),
                labeled=bool(form.strip()),
            )
        )
    return out


def select_latest(vintages: list[FactVintage]) -> FactVintage | None:
    if not vintages:
        return None
    groups: dict[tuple, list[FactVintage]] = {}
    for v in vintages:
        groups.setdefault((v.fy, v.fp, v.end), []).append(v)
    winners = []
    for rows in groups.values():
        rows.sort(key=lambda x: (x.filed, x.accn))
        winners.append(rows[-1])
    winners.sort(key=lambda x: (x.end, x.filed, x.accn))
    return winners[-1]


def select_previous(vintages: list[FactVintage], latest: FactVintage | None) -> FactVintage | None:
    if latest is None:
        return None
    rest = [v for v in vintages if (v.fy, v.fp, v.end) != (latest.fy, latest.fp, latest.end)]
    return select_latest(rest)


def select_across_concepts(payload: dict, concepts: tuple[tuple[str, str, str], ...], as_of, form_filter: str | None = "10-K") -> FactVintage | None:
    best = None
    for tax, concept, unit in concepts:
        hit = select_latest(resolve_vintages(payload, tax, concept, unit, as_of, form_filter))
        if hit is None:
            continue
        if best is None or (hit.end, hit.filed.isoformat()) > (best.end, best.filed.isoformat()):
            best = hit
    return best
