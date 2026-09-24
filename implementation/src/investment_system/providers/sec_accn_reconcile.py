"""Reconcile submissions accession lock vs companyfacts accn. NEW TOOLING.

Match ≠ XBRL parse. Match ≠ Full PIT.
"""

from __future__ import annotations

from datetime import datetime

from .sec_submissions import latest_annual
from .sec_companyfacts import REVENUE_CONCEPTS
from .sec_vintage import select_across_concepts




def reconcile_revenue_accn(facts: dict, submissions: dict, as_of: datetime) -> dict:
    indexed = latest_annual(submissions, as_of)
    fact = select_across_concepts(facts, REVENUE_CONCEPTS, as_of, "10-K")
    fact_accn = (fact.accn.replace("-", "") if fact and fact.accn else None)
    idx_accn = indexed["accn"] if indexed else None
    match = bool(fact_accn and idx_accn and fact_accn == idx_accn)
    return {
        "kind": "ACCN_RECONCILE",
        "full_pit_pass": False,
        "match": match,
        "concept": None if fact is None else fact.concept,
        "fact_accn": fact_accn,
        "index_accn": idx_accn,
        "fact_filed": None if fact is None else fact.filed.date().isoformat(),
        "fact_end": None if fact is None else fact.end,
        "fact_value": None if fact is None else fact.value,
        "index_filed": None if indexed is None else indexed["filingDate"],
        "note": "latest-end across revenue aliases; match is pointer-only",
    }
