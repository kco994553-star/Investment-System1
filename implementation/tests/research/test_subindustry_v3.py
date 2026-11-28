from hashlib import sha256
import json
import re

import pytest

from investment_system.research.common_classification.catalog import dictionary, PARENTS, SECTORS
from investment_system.research.common_classification.market_candidates import classify_market, read_snapshot
from investment_system.research.common_classification.subindustry import STUDY_LABELS, VERSION


def test_taxonomy_preserves_all_old_parents_and_requires_scope():
    d = dictionary(VERSION)
    groups = {g["id"]: g for g in d["industries"]}
    assert len(groups) == len(d["industries"]) == 25
    assert set(groups) == set(STUDY_LABELS)
    assert {g["parent_sector"] for g in groups.values()} == set(SECTORS)
    assert {key: groups[group]["parent_sector"] for key, group in d["legacy_to_broader"].items()} == PARENTS
    for g in groups.values():
        assert all(g[k] for k in ("name_ko", "definition", "includes", "excludes", "sic_codes"))
        assert g["version"] == VERSION
        assert all(re.fullmatch(r"[0-9]{4}", s) for s in g["sic_codes"] + g["sic_requires_activity"])
        assert not set(g["sic_codes"]) & set(g["sic_requires_activity"])


def issuer(i, symbol, sic, exchange="Nasdaq"):
    return dict(cik=str(i).zfill(10), sic=sic, issuer_name="Synthetic", sic_description=None,
                listings=[dict(ticker=symbol, exchange=exchange)], observed_at="2026-11-28T00:00:00Z",
                source_sha256="b"*64, source_url="https://www.sec.gov/example", source_member=None)


def test_candidate_identity_scope_and_bands():
    data = [issuer(1, "A", "7372"), issuer(2, "B", "6770"), issuer(3, "C", "6321"),
            issuer(4, "C", "4813"), issuer(5, "D", None, None), issuer(6, "F", "6798"),
            issuer(7, "G", "6321"), issuer(8, "H.A", "4813"), issuer(9, "I", "7372"),
            issuer(10, "J", "7372"), issuer(11, "J", "7372", None)]
    data[0]["listings"].append({"ticker": "A.B", "exchange": "Nasdaq"})
    keys = ["A", "A.B", "B", "C", "D", "E", "F", "G", "H/A", "I", "I", "J"]
    master = [("NAS", s, "2", "USD", "") for s in keys] + [("NAS", "X", "4", "USD", "")]
    proof = {("NAS", listing["ticker"], r["cik"]): {"COMMON"}
             for r in data for listing in r["listings"]}
    proof["NAS", "F", data[5]["cik"]] = {"UNIT"}
    rows, counts = classify_market(master, data, proof)
    assert [r["reason"] for r in rows] == [None, None, "BLANK_CHECK", "AMBIGUOUS_ISSUER", "VENUE_UNKNOWN",
        "NO_EXACT_ISSUER", "UNIT", "ACTIVITY_REVIEW_REQUIRED", "NO_EXACT_ISSUER",
        "DUPLICATE_MASTER_KEY", "DUPLICATE_MASTER_KEY", "AMBIGUOUS_ISSUER"]
    assert counts["stock_rows"] == 12 and counts["industry_rows"] == 2
    assert counts["issuers_per_industry"]["software_information"] == 1
    assert counts["remaining_rows"] == sum(counts["remaining_reasons"].values())
    assert all(r["grade"] == "CANDIDATE" and r["accounting_model"] == "UNKNOWN" for r in rows)


def test_candidate_boundary_codes():
    codes = ["6798", "4813", "4833", "6324", "6331", None, "0000"]
    data = [issuer(i, str(i), code) for i, code in enumerate(codes, 1)]
    master = [("NAS", str(i), "2", "USD", "") for i in range(1, len(data)+1)]
    proof = {("NAS", str(i), r["cik"]): {"COMMON"} for i, r in enumerate(data, 1)}
    rows, _ = classify_market(master, data, proof)
    assert [r["sector_id"] for r in rows] == ["FINANCIALS", "TELECOMMUNICATIONS",
        "CONSUMER_DISCRETIONARY", None, None, None, None]
    assert [r["reason"] for r in rows][-4:] == ["ACTIVITY_REVIEW_REQUIRED", "ACTIVITY_REVIEW_REQUIRED",
                                                "SIC_MISSING", "SIC_UNMAPPED"]


def test_main_delivery_integrity(tmp_path):
    row = issuer(1, "A", "7372")
    body = (json.dumps(row)+"\n").encode()
    (tmp_path/"issuers.ndjson").write_bytes(body)
    m = dict(schema_version="sec-issuer-sic/1", snapshot_id="test", collected_at=row["observed_at"],
             complete=True, issuers_sha256=sha256(body).hexdigest(), issuer_count=1, listing_count=1,
             missing_sic_count=0, no_listing_count=0, source_url=row["source_url"], source_sha256="a"*64)
    def write_manifest():
        data = json.dumps(m).encode()
        (tmp_path/"manifest.json").write_bytes(data)
        return sha256(data).hexdigest()
    assert read_snapshot(tmp_path, write_manifest()) == [row]
    with pytest.raises(ValueError, match="MANIFEST_HASH"):
        read_snapshot(tmp_path, "0"*64)
    m["listing_count"] = 2
    with pytest.raises(ValueError, match="COUNTS"):
        read_snapshot(tmp_path, write_manifest())
    m["complete"] = False
    with pytest.raises(ValueError, match="PARTIAL"):
        read_snapshot(tmp_path, write_manifest())
