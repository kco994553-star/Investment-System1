"""Macro real producer: PIT boundary, unchanged v0.1.1 engine, fail-closed Web export."""

import dataclasses
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from investment_system.contracts.models import MacroSnapshot, TechnicalSnapshot
from investment_system.macro.engine import MacroEngine
from investment_system.macro.real_producer import (
    PUBLICATION,
    FutureReleaseError,
    MacroInputError,
    MacroProvenanceError,
    PolicyBlocked,
    RevisedHistoryError,
    SyntheticLiveError,
    VintageSeries,
    company_industry_exposure,
    produce,
)
from investment_system.producers.adapters import macro_section
from investment_system.producers.assembler import assemble_bundle, bundle_sha256
from investment_system.producers.contract import validate_snapshot
from investment_system.producers.errors import IncompatibleShapeError
from investment_system.producers.registry import ProduceRequest, default_registry
from investment_system.producers.serialization import canonical_sha256
from investment_system.technical.engine import TechnicalEngine
from investment_system.versions import MACRO_CANDIDATE, MACRO_CONFIRMED

ROOT = Path(__file__).resolve().parents[1]
DECISION = datetime(2024, 12, 31, tzinfo=timezone.utc)
GENERATED = datetime(2024, 12, 31, 12, tzinfo=timezone.utc)
LATER = datetime(2025, 3, 15, tzinfo=timezone.utc)
LATER_GENERATED = datetime(2025, 3, 15, 12, tzinfo=timezone.utc)

# ---- Pin history (history-preserving; each state is exact, nothing is "either value accepted") ----
# Pre-adoption pins, recorded 2026-10-01 with PR #12 (code commit 38e3dff): canonical
# b8e39a2196a6d7794a04a0cd5393c68329e126ca bytes of macro/engine.py and technical/engine.py.
MACRO_ENGINE_SHA256_PRE_ADOPTION = "c593a2ef3b1be06960dde46ccc34db9f1858d1357336614ccf15bbb57ccec80b"
TECHNICAL_ENGINE_SHA256_PRE_ADOPTION = "f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf"
# Adopted pins: C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03.
# 2137883 appends four optional lineage fields to MacroSnapshot/TechnicalSnapshot and adds
# evaluate_stamped() to both engines; the legacy evaluate() bodies are byte-identical, so the
# research MacroSnapshot of this producer keeps every existing field value and gains only
# available_at=None, data_stamp_refs=(), source_vintages=(), input_hash=None.
# Independent before/after comparison (PASS, recorded before this edit):
# docs/macro_real_producer/evidence/c28_adoption_invariance_2026-10-03.json
# Macro owner adoption record: docs/macro_real_producer/LINEAGE_SCHEMA_OWNER_ADOPTION_2026-10-03.md
MACRO_ENGINE_SHA256_C28_ADOPTED = "a0a7c983bebd098aeb8bed81095d849c5bec2dbfd18233408b6ba8929573ee10"
TECHNICAL_ENGINE_SHA256_C28_ADOPTED = "86607bf7004804b923f50cda1db7dbffaf4dd782002a7e0f56ca3c95be625c2c"
LINEAGE_FIELDS = frozenset({"available_at", "data_stamp_refs", "source_vintages", "input_hash"})


def _c28_adoption_state() -> bool | None:
    """Detect the adopted state from the adopted feature itself, never from bytes.

    True: Track C 2137883 present on both engines and both snapshots. False: pre-adoption tree.
    None: partially adopted tree; it selects a digest no file has, so the byte check fails.
    """
    signals = (
        hasattr(MacroEngine, "evaluate_stamped"),
        hasattr(TechnicalEngine, "evaluate_stamped"),
        LINEAGE_FIELDS <= {f.name for f in dataclasses.fields(MacroSnapshot)},
        LINEAGE_FIELDS <= {f.name for f in dataclasses.fields(TechnicalSnapshot)},
    )
    if all(signals):
        return True
    if not any(signals):
        return False
    return None


C28_ADOPTED = _c28_adoption_state()
_INCONSISTENT = "C28_ADOPTION_STATE_INCONSISTENT"
_ENGINE_HASHES = {
    "src/investment_system/macro/engine.py": {
        True: MACRO_ENGINE_SHA256_C28_ADOPTED, False: MACRO_ENGINE_SHA256_PRE_ADOPTION
    }.get(C28_ADOPTED, _INCONSISTENT),
    "src/investment_system/qgv/analysis.py": "bfd4e1310dde9f908f60a8a2030cb9928f4267f73180c3eb5b12bc7947e3de88",
    "src/investment_system/technical/engine.py": {
        True: TECHNICAL_ENGINE_SHA256_C28_ADOPTED, False: TECHNICAL_ENGINE_SHA256_PRE_ADOPTION
    }.get(C28_ADOPTED, _INCONSISTENT),
    "src/investment_system/qgv/portfolio.py": "ecb44165cb163d2e975e94c39c343a18ed3e2d43538431394065b4523246da49",
    "src/investment_system/qgv/leaderboard.py": "f3246131c2219a6f3ea869aa7c88d6cefb30e735992dbcb3b5fc095ff3565248",
}


def _obs(day: str, value: str, realtime: str) -> dict:
    return {"date": day, "value": value, "realtime_end": realtime}


def _vintage(series_id: str, available_at: datetime, observations: list, **kwargs) -> VintageSeries:
    payload = {"observations": observations}
    return VintageSeries(
        series_id=series_id,
        available_at=available_at,
        payload=payload,
        artifact_id=kwargs.get("artifact_id", f"raw:{series_id}:{available_at.date().isoformat()}"),
        sha256=canonical_sha256(payload),
        source=kwargs.get("source", "fred/series/observations realtime_end=as_of"),
        synthetic=kwargs.get("synthetic", False),
        vintage_kind=kwargs.get("vintage_kind", "ALFRED_AS_OF"),
        vintage_at=kwargs.get("vintage_at"),
        release_at=kwargs.get("release_at"),
        ingested_at=kwargs.get("ingested_at"),
    )


def _history(value_2024: str) -> list:
    return [
        _obs("2023-12-01", "100", "2023-12-15"),
        _obs("2024-12-01", value_2024, "2024-12-20"),
        _obs("2026-01-01", "999", "2026-01-15"),
    ]


def _vintages(cpi_2024: str = "102", *, revised: bool = False) -> list[VintageSeries]:
    rows = [
        _vintage("INDPRO", datetime(2024, 12, 20, tzinfo=timezone.utc), _history("104")),
        _vintage("CPIAUCSL", datetime(2024, 12, 20, tzinfo=timezone.utc), _history(cpi_2024)),
    ]
    if revised:
        rows.append(
            _vintage(
                "CPIAUCSL",
                datetime(2025, 3, 1, tzinfo=timezone.utc),
                [
                    _obs("2023-12-01", "100", "2025-03-01"),
                    _obs("2024-12-01", "110", "2025-03-01"),
                ],
                artifact_id="raw:CPIAUCSL:2025-03-01",
            )
        )
    return rows


def test_valid_pit_input_uses_confirmed_engine_and_blocks_web():
    result = produce(DECISION, _vintages(), generated_at=GENERATED)
    direct = MacroEngine().evaluate(DECISION, {"growth": 0.04, "inflation": 0.02}, synthetic=False)
    assert result.snapshot.regime == direct.regime == "EXPANSION"
    assert result.snapshot.state == direct.state
    assert result.snapshot.macro_version == MACRO_CONFIRMED
    assert result.snapshot.mutated_qgv is False
    assert result.snapshot.synthetic is False
    assert result.snapshot.environment["candidate_not_applied"] == MACRO_CANDIDATE
    assert result.snapshot.environment["indicators"]["growth"] == pytest.approx(0.04)
    assert result.snapshot.environment["indicators"]["inflation"] == pytest.approx(0.02)
    assert result.snapshot.environment["vintage"] == "ALFRED_AS_OF"
    assert result.snapshot.environment["fallback_reason"] is None
    assert result.snapshot.environment["real_data_verified"] is False
    assert result.snapshot.environment["pit"]["series"][0]["available_at"]
    assert result.publication == PUBLICATION
    assert result.producer_snapshot["data_state"] == "NOT_AVAILABLE"
    assert result.producer_snapshot["data"] is None
    assert result.producer_snapshot["reason_code"] == "POLICY_BLOCKED"
    validate_snapshot(result.producer_snapshot)


def test_future_release_is_not_used_and_missing_required_vintage_fails():
    early = produce(DECISION, _vintages(), generated_at=GENERATED)
    assert early.snapshot.regime == "EXPANSION"
    only_future = [
        _vintage("INDPRO", datetime(2026, 1, 15, tzinfo=timezone.utc), _history("104")),
        _vintage("CPIAUCSL", datetime(2024, 12, 20, tzinfo=timezone.utc), _history("102")),
    ]
    with pytest.raises(FutureReleaseError):
        produce(DECISION, only_future, generated_at=GENERATED)


def test_revised_vintage_does_not_rewrite_the_earlier_decision():
    both = _vintages(revised=True)
    early = produce(DECISION, both, generated_at=GENERATED)
    late = produce(LATER, both, generated_at=LATER_GENERATED)
    assert early.snapshot.regime == "EXPANSION"
    assert early.snapshot.state.value == "NORMAL"
    assert late.snapshot.regime == "INFLATION_SHOCK"
    assert late.snapshot.state.value == "EMERGENCY"
    replay = produce(DECISION, both, generated_at=GENERATED)
    assert replay.snapshot.regime == early.snapshot.regime
    assert replay.snapshot.environment["indicators"]["inflation"] == pytest.approx(0.02)
    assert late.snapshot.environment["indicators"]["inflation"] == pytest.approx(0.10)
    early_cpi = [row for row in early.provenance if row["series_id"] == "CPIAUCSL"]
    late_cpi = [row for row in late.provenance if row["series_id"] == "CPIAUCSL"]
    assert early_cpi[0]["available_at"].startswith("2024-12-20")
    assert late_cpi[0]["available_at"].startswith("2025-03-01")


def test_missing_provenance_is_rejected():
    bad_hash = _vintage("INDPRO", datetime(2024, 12, 20, tzinfo=timezone.utc), _history("104"))
    bad_hash = VintageSeries(
        series_id=bad_hash.series_id,
        available_at=bad_hash.available_at,
        payload=bad_hash.payload,
        artifact_id=bad_hash.artifact_id,
        sha256="0" * 64,
        source=bad_hash.source,
    )
    with pytest.raises(MacroProvenanceError):
        produce(DECISION, [bad_hash, _vintages()[1]], generated_at=GENERATED)
    no_source = _vintage("CPIAUCSL", datetime(2024, 12, 20, tzinfo=timezone.utc), _history("102"), source="  ")
    with pytest.raises(MacroProvenanceError):
        produce(DECISION, [_vintages()[0], no_source], generated_at=GENERATED)


def test_snapshot_is_deterministic():
    first = produce(DECISION, _vintages(), generated_at=GENERATED)
    second = produce(DECISION, _vintages(), generated_at=GENERATED)
    assert first.snapshot.macro_snapshot_id == second.snapshot.macro_snapshot_id
    assert first.snapshot.to_dict() == second.snapshot.to_dict()
    assert first.producer_snapshot == second.producer_snapshot
    assert first.snapshot.macro_snapshot_id.startswith("mac_")
    assert "v0.1.4" not in first.snapshot.macro_version


def test_methodology_matches_engine_and_candidate_stays_unpromoted():
    result = produce(DECISION, _vintages(), generated_at=GENERATED)
    indicators = result.snapshot.environment["indicators"]
    direct = MacroEngine().evaluate(DECISION, indicators, synthetic=False)
    assert result.snapshot.regime == direct.regime
    assert result.snapshot.state == direct.state
    assert result.snapshot.macro_version == direct.macro_version == MACRO_CONFIRMED
    assert direct.environment["candidate_not_applied"] == MACRO_CANDIDATE
    assert result.snapshot.environment["candidate_not_applied"] == MACRO_CANDIDATE
    neutral = MacroEngine().evaluate(DECISION, {"growth": 0.01, "inflation": 0.02})
    shock = MacroEngine().evaluate(DECISION, {"growth": -0.02, "inflation": 0.09})
    stag = MacroEngine().evaluate(DECISION, {"growth": -0.01, "inflation": 0.06})
    assert neutral.regime == "NEUTRAL" and neutral.state.value == "NORMAL"
    assert shock.regime == "INFLATION_SHOCK" and shock.state.value == "EMERGENCY"
    assert stag.regime == "STAGFLATION_RISK" and stag.state.value == "WARNING"


def test_synthetic_and_revised_history_cannot_become_live():
    synthetic = _vintage(
        "INDPRO",
        datetime(2024, 12, 20, tzinfo=timezone.utc),
        _history("104"),
        synthetic=True,
    )
    with pytest.raises(SyntheticLiveError):
        produce(DECISION, [synthetic, _vintages()[1]], generated_at=GENERATED)
    revised = _vintage(
        "INDPRO",
        datetime(2024, 12, 20, tzinfo=timezone.utc),
        _history("104"),
        vintage_kind="CURRENT_REVISED_NOT_ALFRED",
    )
    with pytest.raises(RevisedHistoryError):
        produce(DECISION, [revised, _vintages()[1]], generated_at=GENERATED)


def test_incomplete_input_does_not_fall_through_to_neutral_zero():
    with pytest.raises(MacroInputError):
        produce(DECISION, [_vintages()[1]], generated_at=GENERATED)


def test_exposure_boundary_is_policy_blocked():
    with pytest.raises(PolicyBlocked):
        company_industry_exposure("nvda")


def test_producer_infrastructure_and_web_accept_fail_closed_macro():
    result = produce(DECISION, _vintages(), generated_at=GENERATED)
    snaps = default_registry().run(ProduceRequest(GENERATED, GENERATED))
    assert snaps["macro"]["reason_code"] == "MACRO_SHAPE_INCOMPATIBLE"
    assert snaps["qgv"]["reason_code"] == "QGV_RESEARCH_ONLY_NO_EXPORT"
    snaps["macro"] = result.producer_snapshot
    bundle = assemble_bundle(default_registry().producers["universe"].companies(), snaps, GENERATED)
    again = assemble_bundle(default_registry().producers["universe"].companies(), snaps, GENERATED)
    assert bundle_sha256(bundle) == bundle_sha256(again)
    assert bundle["macro"]["state"] == "NOT_AVAILABLE"
    assert bundle["macro"]["data"] is None
    assert bundle["macro"]["producer"]["reason_code"] == "POLICY_BLOCKED"
    assert bundle["macro"]["producer"]["methodology"]["status"] == "PROVISIONAL"
    assert bundle["qgv"]["state"] == "NOT_AVAILABLE"
    assert bundle["qgv"]["producer"]["reason_code"] == "QGV_RESEARCH_ONLY_NO_EXPORT"
    assert bundle["technical"]["producer"]["reason_code"] == "TECHNICAL_NO_REAL_MODEL"
    assert bundle["portfolio"]["producer"]["reason_code"] == "PORTFOLIO_NO_ACTUAL_HOLDINGS"
    assert bundle["leaderboard"]["producer"]["reason_code"] == "LEADERBOARD_NO_UPSTREAM_QGV"
    with pytest.raises(IncompatibleShapeError):
        macro_section(result.snapshot)


def test_existing_engine_qgv_technical_portfolio_leaderboard_bytes_unchanged():
    for rel, digest in _ENGINE_HASHES.items():
        assert sha256((ROOT / rel).read_bytes()).hexdigest() == digest
