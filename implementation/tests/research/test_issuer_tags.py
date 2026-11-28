from hashlib import sha256
import json

import pytest

from investment_system.research.common_classification.issuer_tags import summarize_issuer_tags
from investment_system.research.common_classification.market_candidates import classify_market, read_snapshot


def issuer(i, incorporation, business, form):
    return dict(cik=str(i).zfill(10), sic="7372", listings=[dict(ticker=str(i), exchange="Nasdaq")],
                incorporation_code=incorporation, business_address_code=business, recent_reporting_form=form)


def test_independent_tags_and_denominators():
    issuers = [issuer(1, "CA", "A0", "20-F/A"), issuer(2, "DE", "CA", "10-Q"),
               issuer(3, "P8", "P8", None), issuer(4, None, " X0", "8-K"),
               issuer(5, None, None, None), issuer(6, "A0", "XX", "6-K")]
    issuers[0]["listings"].append(dict(ticker="1.B", exchange="Nasdaq"))
    symbols = ["1", "1.B", "2", "3", "4", "5", "6", "7"]
    master = [("NAS", symbol, "2", "USD", "Y" if symbol == "1.B" else "N") for symbol in symbols]
    rows, _ = classify_market(master, issuers, {})
    tags, counts = summarize_issuer_tags(rows, issuers)
    assert len(tags) == 6
    assert tags[issuers[0]["cik"]]["incorporation"]["country_code"] == "US"
    assert tags[issuers[0]["cik"]]["business_address"]["country_code"] == "CA"
    assert counts["master_dr_rows_by_raw_flag"] == {"N": 7, "Y": 1}
    assert counts["business_address_top10"][0] == dict(country_code="CA", country_name_ko="캐나다", stock_rows=2)
    assert tags[issuers[3]["cik"]]["business_address"]["raw_code"] == " X0"
    assert counts["business_address_unknown_reasons"] == dict(UNLINKED=1, UNMAPPED=1, MISSING=1, SOURCE_UNKNOWN=1)
    assert (counts["comparable_country_rows"], counts["different_country_rows"]) == (4, 2)
    assert (counts["comparable_country_issuers"], counts["different_country_issuers"]) == (3, 1)
    assert counts["reporting_type_issuers"] == {"DOMESTIC_FORM": 2, "FOREIGN_FORM": 2, "UNKNOWN": 2}


def test_top_ten_distinct_countries_and_ties():
    codes = "CA A0 E9 L2 M5 V8 X0 D0 P7 L3 C3 C4".split()
    issuers = [issuer(i, code, code, None) for i, code in enumerate(codes)]
    rows = [dict(issuer_id=i["cik"], master_dr_flag="") for i in issuers]
    _, counts = summarize_issuer_tags(rows, issuers)
    top = counts["business_address_top10"]
    assert len(top) == 10 and [v["country_code"] for v in top] == sorted(v["country_code"] for v in top)
    assert counts["business_address_other_known_rows"] == 2
    assert sum(v["stock_rows"] for v in top) + counts["business_address_other_known_rows"] == len(rows)


@pytest.mark.parametrize("schema,edit,error", [
    (1, {}, "REQUIRE_V2"), (2, {"business_address_code": ""}, "TAG_FIELDS"),
    (2, {"incorporation_code": 10}, "TAG_FIELDS"), (2, {"recent_reporting_form": "4"}, "REPORTING_FORM"),
    (2, {"missing_key": True}, "TAG_FIELDS"), (2, {}, None)])
def test_integrity_checked_delivery(tmp_path, schema, edit, error):
    row = issuer(1, None, " X0", "40-F/A")
    row.update(issuer_name="Synthetic", sic_description=None, source_url="https://www.sec.gov/example",
               source_sha256="a"*64, source_member=None, observed_at="2026-11-28T00:00:00Z")
    if "missing_key" in edit:
        del row["incorporation_code"]
    else:
        row.update(edit)
    body = (json.dumps(row) + "\n").encode()
    (tmp_path/"issuers.ndjson").write_bytes(body)
    manifest = dict(schema_version=f"sec-issuer-sic/{schema}", snapshot_id="test", complete=True,
                    issuers_sha256=sha256(body).hexdigest(), issuer_count=1, listing_count=1,
                    missing_sic_count=0, no_listing_count=0, source_url=row["source_url"],
                    source_sha256="b"*64, collected_at=row["observed_at"])
    data = json.dumps(manifest).encode()
    (tmp_path/"manifest.json").write_bytes(data)
    digest = sha256(data).hexdigest()
    if error:
        with pytest.raises(ValueError, match=error):
            read_snapshot(tmp_path, digest, require_issuer_tags=True)
    else:
        assert read_snapshot(tmp_path, digest, require_issuer_tags=True) == [row]
