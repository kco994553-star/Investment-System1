"""Provider-neutral RIG news ingestion. No network and no provider secrets."""

import base64
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_system.contracts.universe import DataEvent
from investment_system.rig.gate import LineageIndex
from investment_system.rig.ingest.contract import (
    ENTITY_METADATA_AUDITED_SHA,
    PRODUCER_INFRA_AUDITED_SHA,
    canonical_bytes,
)
from investment_system.rig.ingest.dedup import assign_semantic_group
from investment_system.rig.ingest.entities import AliasIndex, index_from_registry
from investment_system.rig.ingest.errors import IngestError
from investment_system.rig.ingest.normalize import to_public_dict
from investment_system.rig.ingest.pipeline import ingest
from investment_system.rig.ingest.producer import build_news_snapshot, unavailable_news_snapshot
from investment_system.rig.ingest.rig_input import promote_news_event, to_rig_input
from investment_system.rig.model import ClaimPolarity, EconomicEventKind, NewsEvent

UTC = timezone.utc
NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
REPO = Path(__file__).resolve().parents[2]
RIG = REPO / "implementation" / "src" / "investment_system" / "rig"
FROZEN_RIG = {
    "__init__.py": "edb4a0078fbca7e43382f5c615413b0ba8ac1dc485d6135f7a46ee567e84b44f",
    "adapter.py": "68abf8504f8ece07e0b13496cdb6b931169b24a77bce89c1a721fde75e38816e",
    "discovery/__init__.py": "34c264c8d4f9c2af12bb127de88e4836d0db1c2037f95368d0346a4736357836",
    "discovery/discovery.py": "0face140c5fbdaf54487dca874786d7d219343de3cde5207c96aa97168628136",
    "discovery/impact.py": "a1ab617cf4f2958d94a9ef7396f2c38b2113a05e05d0427ace41a27a89455265",
    "discovery/present.py": "4688b79129cd640250337b1e12c51d819e089702b064daf02e608a631a000199",
    "gate.py": "bffd0201b85b0b20edd5b06dd41a0faa49e24200eaf42bf254d16f18e3903666",
    "intel/__init__.py": "5bcfa837406a101b52cebeaec8ca760af924ac8c94bae7a4a519479afc624f9b",
    "intel/intel.py": "26e6742def877b7517c2a6268c625d02d8dfab8e0f2532d5f618ac4a1062b633",
    "intel/present.py": "c2c8deec0ec6f87f57118a7c0bc771e36b015130ca178c7674742ab87cad9be2",
    "ledger.py": "3b318bd8ff899c0c2054caecbab1c6186ef88299461441a618732a432a6c1791",
    "model.py": "4c863a3f466257d289fad2598cb42bd32120cb1cab628455fbe1b96667b6e850",
    "myview/__init__.py": "b9e77dc54e41fcddf76a6f2f14e32913150b105d0d20a96e1188138edc49f93d",
    "myview/prefs.py": "d222a5f8c7621de5ee59e6f7dc53b81fce080f774b5fa7039a032550eb9d3128",
    "myview/present.py": "4ff0cd7efe7e3d28c54a6fdca04329f96b41553615b61763f1f33d29983004f9",
    "myview/scope.py": "fbb8d1f7bc10d3cf81bef2e4bed8865a8eb54ae051376b31174cf22214333991",
    "network/__init__.py": "fee3aaf7787e4a1ff369a2a347ffde0eb7e6fd045714e643e5e22b6b2c317db2",
    "network/labels.py": "4824b439bd72e0f9e62000d0a6fdf4284fa8df720482389aab50607f2c9a6b75",
    "network/render.py": "4866ceb1042c40372ede796480fff9f378bf2f1034e81eb0c9d20678d5ea146c",
    "network/views.py": "54678dcda5a0dd9c4bbe3ee253a7a49f899c0a971a61b39f5503f5fadceda7ff",
}


def rec(**overrides):
    item = {
        "source": "fixture.wire",
        "source_item_id": "item-1",
        "canonical_url": "https://Example.com/a/b?b=2&a=1#frag",
        "title": "Apple ships a chip",
        "body": "Full original body.",
        "published_at": datetime(2026, 9, 30, 15, tzinfo=UTC),
        "available_at": datetime(2026, 9, 30, 15, 5, tzinfo=UTC),
        "fetched_at": datetime(2026, 9, 30, 16, tzinfo=UTC),
        "source_language": "en-US",
        "raw_bytes": b'{"wire":"original-body-v1"}',
        "mentions": ["AAPL"],
    }
    item.update(overrides)
    return item


def apple_index():
    index = AliasIndex()
    index.add("aapl", tickers=("AAPL",), names=("Apple Inc.", "애플"))
    return index


def test_published_available_fetched_order():
    result = ingest([rec(available_at=datetime(2026, 9, 30, 14, tzinfo=UTC))], now=NOW, aliases=apple_index())
    assert result.rejected[0].code == "TIME_ORDER"
    assert result.accepted == ()
    late_fetch = ingest(
        [rec(fetched_at=datetime(2026, 9, 30, 15, tzinfo=UTC))], now=NOW, aliases=apple_index(),
    )
    assert late_fetch.rejected[0].code == "TIME_ORDER"


def test_future_news_is_rejected():
    future = NOW + timedelta(minutes=1)
    for field in ("published_at", "available_at", "fetched_at"):
        kwargs = {field: future}
        if field == "published_at":
            kwargs["available_at"] = future
            kwargs["fetched_at"] = future
        elif field == "available_at":
            kwargs["fetched_at"] = future
        result = ingest([rec(**kwargs)], now=NOW, aliases=apple_index())
        assert result.rejected[0].code == "FUTURE"


def test_provenance_and_raw_hash_are_separated_from_normalized_text():
    raw = b'{"wire":"original-body-v1"}'
    result = ingest([rec()], now=NOW, aliases=apple_index())
    item = result.accepted[0]
    assert item.raw_hash == hashlib.sha256(raw).hexdigest()
    assert result.raw_by_hash[item.raw_hash] == raw
    public = to_public_dict(item)
    assert public["provenance"]["source"] == "fixture.wire"
    assert public["provenance"]["fetcher"] == "RIG_NEWS_INGEST/1+supplied"
    assert public["provenance"]["canonical_url"] == "https://example.com/a/b?a=1&b=2"
    assert public["canonical_url"] == "https://example.com/a/b?a=1&b=2"
    encoded = canonical_bytes(public).decode("utf-8")
    assert "Full original body." not in encoded
    assert item.body_sha256 == hashlib.sha256("Full original body.".encode()).hexdigest()
    assert "sentiment" not in public and "impact_score" not in public and "consensus" not in public


def test_exact_duplicate_and_source_asserted_repeat_are_distinct():
    first = rec()
    again = rec(fetched_at=datetime(2026, 9, 30, 18, tzinfo=UTC), source_asserted_group_id="story-9")
    other = rec(
        source_item_id="item-2",
        title="Apple ships a chip today",
        body="A different article about the same story.",
        raw_bytes=b'{"wire":"original-body-v2"}',
        canonical_url="https://example.com/other",
        source_asserted_group_id="story-9",
        mentions=["AAPL"],
    )
    first_grouped = rec(source_asserted_group_id="story-9")
    result = ingest([first_grouped, again, other], now=NOW, aliases=apple_index())
    assert len(result.accepted) == 2
    assert len(result.exact_duplicates) == 1
    assert result.exact_duplicates[0].coverage == "EXACT_DUPLICATE"
    assert result.exact_duplicates[0].duplicate_group_id == result.accepted[0].duplicate_group_id
    assert result.exact_duplicates[0].duplicate_group_id != result.accepted[1].duplicate_group_id
    assert {item.coverage for item in result.accepted} == {"SOURCE_ASSERTED_REPEAT"}
    assert {item.source_asserted_group_id for item in result.accepted} == {"story-9"}
    with pytest.raises(IngestError) as raised:
        assign_semantic_group(result.accepted)
    assert raised.value.code == "POLICY_BLOCKED"


def test_same_source_item_with_a_different_payload_conflicts():
    result = ingest(
        [rec(), rec(raw_bytes=b'{"wire":"changed"}', body="Changed body.")],
        now=NOW,
        aliases=apple_index(),
    )
    assert len(result.accepted) == 1
    assert result.rejected[-1].code == "CONFLICT"


def test_similar_titles_are_not_grouped_without_a_threshold():
    result = ingest(
        [
            rec(source_item_id="a", raw_bytes=b"a", title="Apple wins a contract"),
            rec(source_item_id="b", raw_bytes=b"b", title="Apple wins a contract!", canonical_url="https://example.com/b"),
        ],
        now=NOW,
        aliases=apple_index(),
    )
    assert len(result.accepted) == 2
    assert result.accepted[0].duplicate_group_id != result.accepted[1].duplicate_group_id
    assert all(item.semantic_grouping == "POLICY_BLOCKED" for item in result.accepted)


def test_entity_resolution_unknown_and_ambiguous():
    index = apple_index()
    index.add("msft", tickers=("MSFT",), names=("Microsoft Corporation",))
    index.add("csco", names=("시스코",))
    index.add("syy", names=("시스코",))
    result = ingest(
        [rec(mentions=["AAPL", "Apple Inc.", "애플", "Not A Real Company", "시스코"])],
        now=NOW,
        aliases=index,
    )
    item = result.accepted[0]
    by_mention = {hit.mention: hit for hit in item.entity_hits}
    assert by_mention["AAPL"].status == "RESOLVED" and by_mention["AAPL"].company_id == "aapl"
    assert by_mention["Apple Inc."].company_id == "aapl" and by_mention["Apple Inc."].matched_field == "name"
    assert by_mention["애플"].company_id == "aapl"
    assert by_mention["Not A Real Company"].status == "UNKNOWN" and by_mention["Not A Real Company"].company_id is None
    assert by_mention["시스코"].status == "AMBIGUOUS" and by_mention["시스코"].company_id is None
    assert item.canonical_entity_ids == ("aapl",)


def test_pr7_registry_is_read_only_and_not_copied():
    assert not (REPO / "implementation" / "reports" / "entity_metadata").exists()
    raw = subprocess.check_output(
        ["git", "show", f"{ENTITY_METADATA_AUDITED_SHA}:implementation/reports/entity_metadata/top500_entity_metadata_2024-12-31.json"],
        cwd=REPO,
    )
    index = index_from_registry(json.loads(raw))
    assert index.universe_id == "uni_0d1a30b1ee47"
    for mention in ("META", "Facebook Inc", "FB", "페이스북"):
        hit = index.resolve(mention)
        assert hit.status == "RESOLVED" and hit.company_id == "meta", mention
    assert index.resolve("Not A Real Company XYZ").status == "UNKNOWN"


def test_source_language_is_preserved_and_display_locale_is_ignored():
    korean = rec(source_language="ko-KR", title="애플 공급계약", body="원문", raw_bytes=b'{"lang":"ko"}')
    left = ingest([korean], now=NOW, aliases=apple_index(), display_locale="ko-KR")
    right = ingest([korean], now=NOW, aliases=apple_index(), display_locale="en-US")
    assert left.display_locale_applied is False and right.display_locale_applied is False
    assert to_public_dict(left.accepted[0]) == to_public_dict(right.accepted[0])
    assert left.accepted[0].source_language == "ko-KR"
    refused = ingest([{**korean, "display_locale": "ko-KR"}], now=NOW)
    assert refused.rejected[0].code == "DISPLAY_LOCALE_IS_NOT_SOURCE_LANGUAGE"


def test_normalization_is_deterministic():
    kwargs = {"now": NOW, "aliases": apple_index(), "display_locale": "ko-KR"}
    assert canonical_bytes(to_public_dict(ingest([rec()], **kwargs).accepted[0])) == canonical_bytes(
        to_public_dict(ingest([rec()], **kwargs).accepted[0])
    )


def test_malformed_items_are_rejected():
    naive = rec(published_at=datetime(2026, 9, 30, 15))
    cases = [
        naive,
        rec(title="   "),
        rec(raw_bytes="not-bytes"),
        rec(canonical_url="notaurl"),
        rec(source_language=""),
        {**rec(), "sentiment": 0.2},
    ]
    for record in cases:
        result = ingest([record], now=NOW)
        assert result.accepted == ()
        assert result.rejected[0].code in {"MALFORMED", "DISPLAY_LOCALE_IS_NOT_SOURCE_LANGUAGE"}


def test_rig_input_boundary_does_not_invent_a_news_event():
    item = ingest([rec()], now=NOW, aliases=apple_index()).accepted[0]
    boundary = to_rig_input(item)
    assert boundary.company_ids == ("aapl",)
    assert boundary.issuer_ids == ()
    lineage = LineageIndex()
    lineage.add_source(boundary.source)
    lineage.add_evidence(boundary.evidence)
    assert boundary.evidence.available_at >= boundary.source.published_at
    with pytest.raises(IngestError) as raised:
        promote_news_event(item, kind=None, statement=None, polarity=None)
    assert raised.value.code == "EXPLICIT_ONLY"
    mapped = to_rig_input(item, issuer_ids=("issuer_apple",))
    boundary, claim, event = promote_news_event(
        item,
        kind=EconomicEventKind.CONTRACT,
        statement="Apple announced a supply contract.",
        polarity=ClaimPolarity.AFFIRMS,
        issuer_ids=mapped.issuer_ids,
    )
    assert isinstance(event, NewsEvent) and not issubclass(NewsEvent, DataEvent)
    assert event.occurred_on is None
    lineage.add_source(boundary.source)
    lineage.add_evidence(boundary.evidence)
    lineage.add_claim(claim)
    lineage.add_event(event)
    traced = lineage.trace((event.event_id,), NOW)
    assert traced.events[0].event_id == event.event_id
    assert traced.sources[0].raw_artifact_id == f"newsraw:{item.raw_hash}"


def _producer_validate(snapshot: dict, blobs: dict[str, bytes]) -> None:
    worktree = Path("/tmp/rig-news-producer-ro")
    if not worktree.exists():
        subprocess.check_call(
            ["git", "worktree", "add", "--detach", str(worktree), PRODUCER_INFRA_AUDITED_SHA],
            cwd=REPO,
        )
    script = """
import base64, json, sys
sys.path.insert(0, "implementation/src")
from investment_system.producers.contract import validate_snapshot, verify_inputs
payload = json.load(sys.stdin)
snapshot = validate_snapshot(payload["snapshot"])
blobs = {key: base64.b64decode(value) for key, value in payload["blobs"].items()}
if snapshot["data_state"] != "NOT_AVAILABLE":
    def resolve(artifact_id):
        if not artifact_id.startswith("newsraw:"):
            return None
        return blobs.get(artifact_id.split(":", 1)[1])
    verify_inputs(snapshot, resolve)
print(snapshot["section"])
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({
            "snapshot": snapshot,
            "blobs": {key: base64.b64encode(value).decode("ascii") for key, value in blobs.items()},
        }),
        text=True,
        cwd=worktree,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "news"


def test_producer_infrastructure_compatibility_and_absence():
    absent = unavailable_news_snapshot(generated_at=NOW, requested_as_of=NOW)
    assert absent["data_state"] == "NOT_AVAILABLE"
    assert absent["reason_code"] == "NEWS_NO_SOURCE"
    assert absent["data"] is None
    _producer_validate(absent, {})
    result = ingest(
        [rec(), rec(fetched_at=datetime(2026, 9, 30, 18, tzinfo=UTC))],
        now=NOW,
        aliases=apple_index(),
        display_locale="ko-KR",
    )
    snapshot = build_news_snapshot(
        result,
        now=NOW,
        requested_as_of=NOW,
        data_state="FROZEN_SNAPSHOT",
        issuer_by_company={"aapl": "issuer_apple"},
    )
    assert snapshot["synthetic"] is False
    assert len(snapshot["data"]) == 1
    card = snapshot["data"][0]
    assert card["status"] == "NEW"
    assert card["issuer_ids"] == ["issuer_apple"]
    assert card["source_language"] == "en-US"
    assert "headline_localized" not in card
    assert "consensus" not in card and "sentiment" not in card
    _producer_validate(snapshot, result.raw_by_hash)
    with pytest.raises(IngestError) as raised:
        build_news_snapshot(result, now=NOW, requested_as_of=NOW, data_state="LIVE")
    assert raised.value.code == "EXPIRES_AT_REQUIRED"


def test_frozen_rig_modules_are_unchanged():
    for relative, digest in FROZEN_RIG.items():
        assert hashlib.sha256((RIG / relative).read_bytes()).hexdigest() == digest
    assert not issubclass(NewsEvent, DataEvent)
