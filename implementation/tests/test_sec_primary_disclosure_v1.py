"""SEC 8-K primary disclosure. Synthetic Atom only. No network and no exhibit text."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from investment_system.rig.ingest.contract import LANGUAGE_NOT_PROVIDED
from investment_system.rig.ingest.errors import IngestError
from investment_system.rig.ingest.pipeline import ingest
from investment_system.rig.ingest.rig_input import to_rig_input
from investment_system.rig.ingest.sec_primary_disclosure_v1 import (
    ExplicitIdentityMap,
    build_primary_disclosure_snapshot,
    fetch_sec_atom,
    general_news_snapshot,
    identity_from_registry,
    publish_web_disclosure,
    sec_user_agent,
)
from investment_system.rig.model import SourceKind

UTC = timezone.utc
NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
FETCHED = datetime(2026, 9, 30, 20, tzinfo=UTC)
GENERATED = datetime(2026, 10, 1, 12, tzinfo=UTC)
GENERATED_LATER = datetime(2026, 10, 1, 13, tzinfo=UTC)


def entry(**kw) -> str:
    accession = kw.get("accession", "0000000001-26-000001")
    cik = kw.get("cik", "0000000001")
    form = kw.get("form", "8-K")
    title = kw.get("title", f"{form} - Example Issuer Inc. ({cik}) (Filer)")
    updated = kw.get("updated", "2026-09-30T15:05:00-04:00")
    filed = kw.get("filed", "2026-09-30")
    items = kw.get("items", (("2.02", "Results of Operations and Financial Condition"),))
    extra = kw.get("extra", "EXHIBIT BODY MUST NOT LEAK")
    lang = kw.get("lang")
    lang_attr = f' xml:lang="{lang}"' if lang else ""
    url_cik = kw.get("url_cik", str(int(cik)))
    href = kw.get(
        "href",
        f"https://www.sec.gov/Archives/edgar/data/{url_cik}/{accession.replace('-', '')}/{accession}-index.htm",
    )
    filed_line = "" if filed is None else f" <b>Filed:</b> {filed} "
    item_lines = "\n".join(f"<br/>Item {code}: {label}" for code, label in items)
    summary = kw.get("summary")
    if summary is None:
        summary = (
            f"\n{filed_line}<b>AccNo:</b> {accession} <b>Size:</b> 1 KB\n"
            f"{item_lines}\n{extra}\n"
        )
    return (
        f"<entry{lang_attr}>\n"
        f"<title>{title}</title>\n"
        f'<link rel="alternate" type="text/html" href="{href}"/>\n'
        f'<summary type="html">{summary}</summary>\n'
        f"<updated>{updated}</updated>\n"
        f'<category scheme="https://www.sec.gov/" label="form type" term="{form}"/>\n'
        f"<id>urn:tag:sec.gov,2008:accession-number={accession}</id>\n"
        f"</entry>"
    )


def feed(*entries: str) -> bytes:
    body = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "<title>synthetic</title>\n"
        "<updated>2026-09-30T12:00:00-04:00</updated>\n"
        f"{body}\n"
        "</feed>"
    ).encode("utf-8")


def build(payload: bytes, identity: ExplicitIdentityMap | None = None, **kw):
    return build_primary_disclosure_snapshot(
        payload,
        now=kw.pop("now", NOW),
        fetched_at=kw.pop("fetched_at", FETCHED),
        generated_at=kw.pop("generated_at", GENERATED),
        identity=identity,
        synthetic=kw.pop("synthetic", True),
        **kw,
    )


def test_valid_8k_preserves_sec_fields_and_drops_the_summary():
    payload = feed(entry())
    batch = build(payload)
    item = batch.snapshot["items"][0]
    assert item["source_layer"] == "PRIMARY_DISCLOSURE"
    assert item["form_type"] == "8-K"
    assert item["title"] == "8-K - Example Issuer Inc. (0000000001) (Filer)"
    assert item["item_labels"] == [{"code": "2.02", "label": "Results of Operations and Financial Condition"}]
    assert item["accession"] == "0000000001-26-000001"
    assert item["sec_timestamp"] == {
        "role": "FEED_DISSEMINATION",
        "element": "updated",
        "value": "2026-09-30T15:05:00-04:00",
    }
    assert item["filed_on"] == "2026-09-30"
    assert item["filed_on_status"] == "DATE_ONLY"
    assert item["acceptance_at"] is None
    assert item["acceptance_status"] == "NOT_PROVIDED"
    assert item["canonical_url"] == (
        "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/0000000001-26-000001-index.htm"
    )
    assert item["source_language"] == LANGUAGE_NOT_PROVIDED
    assert item["display_locale_applied"] is False
    encoded = json.dumps(batch.snapshot)
    assert "EXHIBIT BODY" not in encoded
    assert "<b>" not in encoded and "AccNo" not in encoded
    assert "published_at" not in encoded
    assert "T00:00:00" not in encoded
    assert "sentiment" not in item and "impact_score" not in item and "consensus" not in item
    assert "body" not in item and "summary" not in item
    assert batch.snapshot["data_state"] != "LIVE"
    assert batch.snapshot["web_publication"]["reason_code"] == "P01_FRESHNESS_REQUIRED"
    assert batch.snapshot["rig"]["news_event_created"] is False
    assert batch.snapshot["rig"]["source_kind"] == "PRIMARY_DISCLOSURE"
    assert batch.snapshot["flags"]["RIG_REAL_PRODUCER_READY"] == "NO"
    assert batch.snapshot["flags"]["GENERAL_NEWS_PROVIDER_READY"] == "NO"
    assert batch.snapshot["flags"]["CONSENSUS_PRODUCER_READY"] == "NO"


def test_timezone_aware_updated_is_not_rewritten_and_date_only_is_not_a_clock():
    kept = build(feed(entry())).snapshot["items"][0]
    assert kept["sec_timestamp"]["value"].endswith("-04:00")
    assert kept["filed_on"] == "2026-09-30"
    clocked = build(feed(entry(filed="2026-09-30T00:00:00+00:00")))
    assert clocked.snapshot["items"][0]["filed_on"] is None
    assert "2026-09-30T00:00:00+00:00" not in json.dumps(clocked.snapshot)
    dated = build(feed(entry(updated="2026-09-30")))
    assert dated.snapshot["items"] == []
    assert dated.snapshot["rejected"][0]["code"] == "DATE_ONLY_NOT_A_CLOCK"
    assert "T00:00:00" not in json.dumps(dated.snapshot)


def test_sec_escaped_summary_markup_is_metadata_not_a_copied_snippet():
    # Real Atom stores the summary tags as text entities. Build that shape in code
    # so the fixture cannot be rewritten into live XML elements.
    lt, gt = "&" + "lt;", "&" + "gt;"
    summary = (
        f"\n {lt}b{gt}Filed:{lt}/b{gt} 2026-09-30 {lt}b{gt}AccNo:{lt}/b{gt} 0000000001-26-000001\n"
        f"{lt}br{gt}Item 7.01: Regulation FD Disclosure\n"
        "EXHIBIT BODY MUST NOT LEAK\n"
    )
    item = build(feed(entry(summary=summary, items=()))).snapshot["items"][0]
    assert item["filed_on"] == "2026-09-30"
    assert item["item_labels"] == [{"code": "7.01", "label": "Regulation FD Disclosure"}]
    encoded = json.dumps(item)
    assert "EXHIBIT BODY" not in encoded and "<b>" not in encoded and "AccNo" not in encoded


def test_duplicate_accession_is_exact_and_distinct_accessions_are_not_grouped():
    payload = feed(entry(), entry())
    batch = build(payload)
    assert batch.snapshot["exact_duplicate_count"] == 1
    assert len(batch.snapshot["items"]) == 1
    assert batch.snapshot["items"][0]["coverage"] == "STANDALONE"
    raw = next(iter(batch.raw_by_hash.values()))
    assert hashlib.sha256(raw).hexdigest() == batch.snapshot["items"][0]["raw_hash"]
    other = entry(accession="0000000001-26-000002", title="8-K - Example Issuer Inc. (0000000001) (Filer)")
    # Title matches the first filing. That is not a group.
    pair = build(feed(entry(), other))
    assert pair.snapshot["exact_duplicate_count"] == 0
    assert [row["coverage"] for row in pair.snapshot["items"]] == ["STANDALONE", "STANDALONE"]
    assert pair.snapshot["items"][0]["duplicate_group_id"] != pair.snapshot["items"][1]["duplicate_group_id"]
    assert all(row["source_asserted_group_id"] is None for row in pair.snapshot["items"])
    changed = entry(title="8-K - Example Issuer Inc. (0000000001) (Filer) revised")
    conflict = build(feed(entry(), changed))
    assert [row["code"] for row in conflict.snapshot["rejected"]] == ["CONFLICT"]
    assert len(conflict.snapshot["items"]) == 1
    assert conflict.snapshot["items"][0]["coverage"] != "SOURCE_ASSERTED_REPEAT"


def test_language_is_not_invented_and_is_independent_of_display_locale():
    hangul = entry(title="8-K - 예시 주식회사 (0000000001) (Filer)")
    item = build(feed(hangul)).snapshot["items"][0]
    assert item["source_language"] == LANGUAGE_NOT_PROVIDED
    assert item["display_locale_applied"] is False
    stated = build(feed(entry(lang="en"))).snapshot["items"][0]
    assert stated["source_language"] == "en"
    assert stated["source_language"] != "en-US"


def test_company_cik_map_unknown_ambiguous_and_missing_issuer():
    payload = feed(entry())
    unknown = build(payload, ExplicitIdentityMap())
    row = unknown.snapshot["items"][0]
    assert row["cik"] == "0000000001"
    assert row["identity_status"] == "UNKNOWN"
    assert row["company_id"] is None
    assert row["issuer_id"] is None
    assert row["company_filter"] == "NOT_AVAILABLE"
    mapped = ExplicitIdentityMap()
    mapped.add("1", "example")
    missing_issuer = build(payload, mapped).snapshot["items"][0]
    assert missing_issuer["company_id"] == "example"
    assert missing_issuer["issuer_id"] is None
    assert missing_issuer["company_filter"] == "NOT_AVAILABLE"
    mapped.add("0000000001", "example", "iss_example")
    resolved = build(payload, mapped).snapshot["items"][0]
    assert resolved["identity_status"] == "RESOLVED"
    assert resolved["issuer_id"] == "iss_example"
    assert resolved["company_filter"] == "RESOLVED"
    ambiguous = ExplicitIdentityMap()
    ambiguous.add("0000000001", "left")
    ambiguous.add("0000000001", "right")
    refused = build(payload, ambiguous)
    assert refused.snapshot["items"] == []
    assert refused.snapshot["rejected"][0]["code"] == "AMBIGUOUS"
    mismatch = build(feed(entry(url_cik="99")))
    assert mismatch.snapshot["items"] == []
    assert mismatch.snapshot["rejected"][0]["code"] == "CIK_MISMATCH"


def test_registry_cik_is_not_a_name_search_key():
    document = {
        "kind": "ENTITY_SEARCH_METADATA_REGISTRY",
        "schema_version": 1,
        "records": {
            "other": {
                "company_id": "other",
                "cik": "0000000099",
                "ticker": "EX",
                "official_name": {"value": "Example Issuer Inc."},
                "aliases": {"value": "예시 주식회사"},
            }
        },
    }
    mapping = identity_from_registry(document)
    payload = feed(entry(title="8-K - Example Issuer Inc. (0000000001) (Filer)"))
    row = build(payload, mapping).snapshot["items"][0]
    assert row["company_id"] is None
    assert row["identity_status"] == "UNKNOWN"
    hit = build(feed(entry(cik="0000000099")), mapping).snapshot["items"][0]
    assert hit["company_id"] == "other"
    assert hit["issuer_id"] is None
    assert hit["company_filter"] == "NOT_AVAILABLE"


def test_future_timestamp_is_rejected():
    payload = feed(entry(updated="2026-10-02T00:00:00+00:00"))
    batch = build(payload, fetched_at=datetime(2026, 10, 2, 1, tzinfo=UTC))
    assert batch.snapshot["items"] == []
    assert batch.snapshot["rejected"][0]["code"] == "FUTURE"


def test_amendment_is_in_scope_and_other_forms_are_not():
    amended = build(feed(entry(form="8-K/A"))).snapshot["items"][0]
    assert amended["form_type"] == "8-K/A"
    other = build(feed(entry(form="10-K", title="10-K - Example Issuer Inc. (0000000001) (Filer)")))
    assert other.snapshot["items"] == []
    assert other.snapshot["rejected"][0]["code"] == "OUT_OF_SCOPE"


def test_normalization_is_deterministic_and_hashes_raw_bytes():
    payload = feed(entry())
    left = build(payload)
    right = build(payload, generated_at=GENERATED_LATER)
    assert left.snapshot["semantic_hash"] == right.snapshot["semantic_hash"]
    changed = feed(entry(title="8-K - Other Name (0000000001) (Filer)"))
    assert build(changed).snapshot["semantic_hash"] != left.snapshot["semantic_hash"]
    assert left.snapshot["provenance"]["feed_sha256"] == hashlib.sha256(payload).hexdigest()


def test_general_news_stays_unavailable_and_web_live_is_blocked():
    news = general_news_snapshot(generated_at=NOW, requested_as_of=NOW)
    assert news["section"] == "news"
    assert news["data_state"] == "NOT_AVAILABLE"
    assert news["reason_code"] == "NEWS_NO_SOURCE"
    assert news["data"] is None
    snapshot = build(feed(entry())).snapshot
    assert snapshot["contract"] == "PRIMARY_DISCLOSURE_SNAPSHOT"
    assert snapshot["contract"] != "PRODUCER_SNAPSHOT"
    with pytest.raises(IngestError) as raised:
        publish_web_disclosure(snapshot, data_state="LIVE")
    assert raised.value.code == "WEB_PUBLICATION_BLOCKED"


def test_user_agent_is_configuration_not_a_hardcoded_contact(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("INVESTMENT_SYSTEM_SEC_UA", raising=False)
    with pytest.raises(IngestError) as raised:
        sec_user_agent()
    assert raised.value.code == "SEC_USER_AGENT_REQUIRED"
    with pytest.raises(IngestError) as fetch_raised:
        fetch_sec_atom("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom")
    assert fetch_raised.value.code == "SEC_USER_AGENT_REQUIRED"
    monkeypatch.setenv("SEC_USER_AGENT", "Configured Contact example@invalid")
    assert sec_user_agent() == "Configured Contact example@invalid"
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "src/investment_system/rig/ingest/sec_primary_disclosure_v1.py"
    ).read_text()
    assert "example.invalid" not in source
    assert "webmaster@" not in source
    assert "AliasIndex" not in source
    assert "promote_news_event" not in source
    assert "entity_metadata" not in source


def _news(**overrides):
    item = {
        "source": "fixture.wire",
        "source_item_id": "item-1",
        "canonical_url": "https://example.com/a",
        "title": "A filing headline",
        "body": "",
        "published_at": datetime(2026, 9, 30, 15, tzinfo=UTC),
        "available_at": datetime(2026, 9, 30, 15, tzinfo=UTC),
        "fetched_at": FETCHED,
        "source_language": "en-US",
        "raw_bytes": b"raw-body",
    }
    item.update(overrides)
    return item


def test_language_not_provided_is_a_general_contract_not_an_sec_exception():
    omitted = ingest([_news(source_language=LANGUAGE_NOT_PROVIDED)], now=NOW)
    assert omitted.accepted[0].source_language == LANGUAGE_NOT_PROVIDED
    left = ingest([_news(source_language=LANGUAGE_NOT_PROVIDED)], now=NOW, display_locale="ko-KR")
    right = ingest([_news(source_language=LANGUAGE_NOT_PROVIDED)], now=NOW, display_locale="en-US")
    assert left.accepted[0].source_language == right.accepted[0].source_language == LANGUAGE_NOT_PROVIDED
    assert left.display_locale_applied is False
    english = ingest([_news(source_language="en-US")], now=NOW).accepted[0]
    assert english.source_language == "en-US"
    assert english.content_sha256 != omitted.accepted[0].content_sha256
    for record in (_news(source_language=""), {key: value for key, value in _news().items() if key != "source_language"}):
        result = ingest([record], now=NOW)
        assert result.accepted == ()
        assert result.rejected[0].code == "MALFORMED"
    refused = ingest([{**_news(), "display_locale": "ko-KR"}], now=NOW)
    assert refused.rejected[0].code == "DISPLAY_LOCALE_IS_NOT_SOURCE_LANGUAGE"
    boundary = to_rig_input(english)
    assert boundary.source.kind is SourceKind.NEWS
    disclosure = to_rig_input(omitted.accepted[0], kind=SourceKind.PRIMARY_DISCLOSURE)
    assert disclosure.source.kind is SourceKind.PRIMARY_DISCLOSURE
