"""Technical real-input producer. Offline. Does not claim a Top-500 validation."""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.technical.codec import semantic_hash
from investment_system.technical.engine import TechnicalEngine
from investment_system.technical.errors import (
    CompanyIdentityError,
    FutureInputError,
    MissingLookbackError,
    MissingProvenanceError,
    SyntheticLiveError,
)
from investment_system.technical.exporter import export_producer_snapshot
from investment_system.technical.persistence import read_batch, write_batch
from investment_system.technical.pit_market import InputProvenance
from investment_system.technical.producer import produce_batch, produce_company, produce_demo
from investment_system.versions import MACRO_CONFIRMED, QGV_ANALYSIS_CONTRACT, TECHNICAL_STRUCTURAL

START = 1_700_000_000
DECISION = datetime.fromtimestamp(START + 9 * 86400 + 3600, tz=timezone.utc)
GENERATED = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
ENGINE_FINGERPRINT = "28e910f3005c74888aa33e9b6f45b8d94fc70d4f023e1bc49a6af4100ea9ede6"
SOURCE_SHA256 = {
    "src/investment_system/technical/engine.py": "f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf",
    "src/investment_system/macro/engine.py": "c593a2ef3b1be06960dde46ccc34db9f1858d1357336614ccf15bbb57ccec80b",
    "src/investment_system/qgv/scoring.py": "1aa4802a65175210be802c7d1d08e17e8af5cfa40a9b6faaa014447354d9e629",
    "src/investment_system/qgv/leaderboard.py": "f3246131c2219a6f3ea869aa7c88d6cefb30e735992dbcb3b5fc095ff3565248",
    "src/investment_system/qgv/portfolio.py": "ecb44165cb163d2e975e94c39c343a18ed3e2d43538431394065b4523246da49",
    "src/investment_system/integration/engine.py": "53aff49209d284e54620697b704a6c71250665984c676dd294d52f1206f1664d",
}


def _rows(n=12, volume_at=None):
    rows = []
    for i in range(n):
        volume = None if volume_at is not None and i in volume_at else 1_000_000 + i
        rows.append((START + i * 86400, 100.0 + i, volume, 90.0 + i))
    return rows


def _body(symbol, rows):
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": symbol, "currency": "USD"},
                    "timestamp": [r[0] for r in rows],
                    "indicators": {
                        "quote": [{"close": [r[1] for r in rows], "volume": [r[2] for r in rows]}],
                        "adjclose": [{"adjclose": [r[3] for r in rows]}],
                    },
                }
            ]
        }
    }
    return json.dumps(payload).encode("utf-8")


def _prov(body, symbol, evidence="STRUCTURAL_FIXTURE", synthetic=True):
    return InputProvenance(
        artifact_id=f"yahoo_chart:{symbol}:test",
        sha256=hashlib.sha256(body).hexdigest(),
        nbytes=len(body),
        source_provider="yahoo-chart",
        source_reference=symbol,
        evidence_class=evidence,
        synthetic=synthetic,
    )


def _produce(symbol="AAPL", company_id="aapl", rows=None, decision=DECISION, generated=GENERATED, **kw):
    rows = _rows() if rows is None else rows
    body = _body(symbol, rows)
    evidence = kw.pop("evidence", "STRUCTURAL_FIXTURE")
    synthetic = kw.pop("synthetic", evidence != "LIVE_FETCH")
    return produce_company(
        company_id=company_id,
        ticker=symbol,
        decision_time=decision,
        lookback_bars=kw.pop("lookback_bars", 5),
        lookback_id=kw.pop("lookback_id", "caller-window-5"),
        body=body,
        provenance=_prov(body, symbol, evidence, synthetic),
        generated_at=generated,
        **kw,
    )


def test_real_pit_input_pass():
    record = _produce()
    assert record["validation"]["status"] == "PASS"
    assert record["research_state"] == "POLICY_BLOCKED"
    assert record["technical_outputs"]["status"] == "NOT_AVAILABLE"
    assert record["technical_outputs"]["regime"] is None
    assert record["technical_outputs"]["model_applied"] is False
    assert record["path"] == "FIXTURE"
    assert record["synthetic"] is True
    assert record["universe_claim"] is False
    last = datetime.fromisoformat(record["lookback"]["last_observed_at"])
    assert last <= DECISION
    assert record["lookback"]["future_excluded"] == 2
    assert datetime.fromisoformat(record["available_at"]) <= DECISION
    assert "PRICE_SERIES" in {b["id"] for b in record["policy_blockers"]}


def test_future_input_fail():
    with pytest.raises(FutureInputError, match="FUTURE_INPUT"):
        _produce(on_future="reject")


def test_missing_provenance_fail():
    body = _body("AAPL", _rows())
    bad = InputProvenance(
        artifact_id="yahoo_chart:AAPL:test",
        sha256="0" * 64,
        nbytes=len(body),
        source_provider="yahoo-chart",
        source_reference="AAPL",
        evidence_class="STRUCTURAL_FIXTURE",
        synthetic=True,
    )
    with pytest.raises(MissingProvenanceError, match="MISSING_PROVENANCE"):
        produce_company(
            company_id="aapl",
            ticker="AAPL",
            decision_time=DECISION,
            lookback_bars=5,
            lookback_id="caller-window-5",
            body=body,
            provenance=bad,
            generated_at=GENERATED,
        )


def test_missing_lookback_fail():
    with pytest.raises(MissingLookbackError, match="MISSING_LOOKBACK"):
        _produce(lookback_bars=50)
    with pytest.raises(MissingLookbackError, match="MISSING_LOOKBACK"):
        _produce(lookback_id="")


def test_missing_volume_is_not_filled():
    record = _produce(rows=_rows(volume_at={7}))
    assert record["lookback"]["incomplete_eligible"] == 1
    first = datetime.fromisoformat(record["lookback"]["first_observed_at"])
    last = datetime.fromisoformat(record["lookback"]["last_observed_at"])
    hole = datetime.fromtimestamp(START + 7 * 86400, tz=timezone.utc)
    assert first <= hole <= last
    assert hole.isoformat() not in (
        record["lookback"]["first_observed_at"],
        record["lookback"]["last_observed_at"],
    )
    # The hashed window must not contain a fabricated volume for the hole.
    assert record["lookback"]["series_sha256"] != _produce()["lookback"]["series_sha256"]


def test_synthetic_cannot_be_live():
    body = _body("AAPL", _rows())
    with pytest.raises(SyntheticLiveError, match="SYNTHETIC_LIVE"):
        _prov(body, "AAPL", evidence="LIVE_FETCH", synthetic=True).validate(body)
    with pytest.raises(SyntheticLiveError, match="SYNTHETIC_LIVE"):
        export_producer_snapshot(
            requested_as_of=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            generated_at=GENERATED,
            data_state="LIVE",
        )


def test_same_semantic_input_same_hash():
    a = _produce()
    b = _produce(generated=GENERATED + timedelta(hours=3))
    assert a["semantic_hash"] == b["semantic_hash"]
    assert a["record_id"] == b["record_id"]
    assert a["generated_at"] != b["generated_at"]
    assert semantic_hash(a) == a["semantic_hash"]


def test_different_as_of_different_snapshot():
    later = DECISION + timedelta(days=3)
    a = _produce()
    b = _produce(decision=later)
    assert a["semantic_hash"] != b["semantic_hash"]
    assert a["as_of"] != b["as_of"]
    assert b["lookback"]["future_excluded"] < a["lookback"]["future_excluded"]


def test_company_identity_preserved():
    record = _produce()
    assert record["company_id"] == "aapl"
    assert record["ticker"] == "AAPL"
    body = _body("MSFT", _rows())
    with pytest.raises(CompanyIdentityError, match="COMPANY_IDENTITY"):
        produce_company(
            company_id="aapl",
            ticker="AAPL",
            decision_time=DECISION,
            lookback_bars=5,
            lookback_id="caller-window-5",
            body=body,
            provenance=_prov(body, "AAPL"),
            generated_at=GENERATED,
        )


def test_demo_preserves_engine_outputs_exactly():
    as_of = datetime(2026, 9, 14, tzinfo=timezone.utc)
    returns = [0.01, -0.02, 0.03, 0.005, 0.01, -0.001]
    direct = TechnicalEngine().evaluate("aapl", as_of, returns, synthetic=True)
    demo = produce_demo(
        company_id="aapl", ticker="AAPL", as_of=as_of, returns=returns, generated_at=GENERATED
    )
    out = demo["technical_outputs"]
    assert out["regime"] == direct.regime.value
    assert out["execution_zone"] == direct.execution_zone.value
    assert out["invalidation"] == direct.invalidation
    assert out["scenarios"] == [dict(s) for s in direct.scenarios]
    assert out["drawdown_recheck"] == direct.drawdown_recheck
    assert out["mutated_qgv"] is False
    assert out["technical_version"] == direct.technical_version == TECHNICAL_STRUCTURAL
    assert demo["synthetic"] is True
    assert demo["path"] == "DEMO"
    assert demo["engine_snapshot_id"] == direct.technical_snapshot_id or demo["engine_snapshot_id"].startswith("ta_")
    assert out["model_applied"] is False


def test_exporter_does_not_recalculate(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("exporter or real path recalculated TechnicalEngine")

    monkeypatch.setattr(TechnicalEngine, "evaluate", boom)
    record = _produce()
    assert record["technical_outputs"]["status"] == "NOT_AVAILABLE"
    snap = export_producer_snapshot(
        requested_as_of=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        generated_at=GENERATED,
    )
    assert snap["data"] is None
    assert snap["section"] == "technical"
    assert "regime" not in json.dumps(snap["data"])


def test_exporter_matches_producer_infrastructure_not_available():
    snap = export_producer_snapshot(
        requested_as_of=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        generated_at=datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc),
    )
    golden = json.loads(
        (ROOT / "docs/technical_real_producer/evidence/producer_not_available_golden.json").read_text(encoding="utf-8")
    )
    assert snap == golden


def test_partial_batch_is_explicit():
    good = _body("AAPL", _rows())
    short = _body("MSFT", _rows(n=2))
    items = [
        dict(
            company_id="aapl",
            ticker="AAPL",
            decision_time=DECISION,
            lookback_bars=5,
            lookback_id="caller-window-5",
            body=good,
            provenance=_prov(good, "AAPL"),
            generated_at=GENERATED,
        ),
        dict(
            company_id="msft",
            ticker="MSFT",
            decision_time=DECISION,
            lookback_bars=5,
            lookback_id="caller-window-5",
            body=short,
            provenance=_prov(short, "MSFT"),
            generated_at=GENERATED,
        ),
    ]
    batch = produce_batch(items)
    assert batch["partial"] is True
    assert batch["complete"] is False
    assert batch["coverage"] == "PARTIAL"
    assert batch["input_pass"] == 1
    assert batch["input_fail"] == 1
    assert batch["universe_claim"] is False
    assert batch["universe_size_claim"] is None
    assert batch["records"][0]["company_id"] == "aapl"
    assert "MISSING_LOOKBACK" in batch["failures"][0]["error"]


def test_offline_replay_and_raw_store(tmp_path):
    body = _body("NVDA", _rows())
    store = RawDatasetStore(tmp_path / "raw")
    store.put(f"yahoo_chart:NVDA:test", body, "fixture://nvda", "YAHOO_CHART", "application/json", "test")
    manifest = store.get_manifest("yahoo_chart:NVDA:test")
    assert manifest["sha256"] == hashlib.sha256(body).hexdigest()
    record = produce_company(
        company_id="nvda",
        ticker="NVDA",
        decision_time=DECISION,
        lookback_bars=5,
        lookback_id="caller-window-5",
        body=store.get_bytes("yahoo_chart:NVDA:test"),
        provenance=InputProvenance(
            artifact_id="yahoo_chart:NVDA:test",
            sha256=manifest["sha256"],
            nbytes=manifest["bytes"],
            source_provider="yahoo-chart",
            source_reference="NVDA",
            evidence_class="STRUCTURAL_FIXTURE",
            synthetic=True,
        ),
        generated_at=GENERATED,
    )
    assert record["available_at"] != manifest["fetched_at"]
    batch = produce_batch([])
    batch["records"] = [record]
    batch["input_pass"] = 1
    batch["requested"] = 1
    batch["input_fail"] = 0
    batch["partial"] = False
    batch["complete"] = True
    batch["coverage"] = "COMPLETE"
    batch["failures"] = []
    write_batch(batch, tmp_path / "out")
    restored = read_batch(tmp_path / "out")
    assert restored["records"][0]["semantic_hash"] == record["semantic_hash"]
    assert restored["records"][0]["company_id"] == "nvda"


def test_technical_package_does_not_import_network():
    package = ROOT / "src/investment_system/technical"
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "urllib" not in text
        assert "urlopen" not in text
        assert "socket" not in text


def test_engine_fingerprint_and_cross_track_sources_unchanged():
    assert TECHNICAL_STRUCTURAL == "v0.6-STRUCTURAL-FREEZE"
    assert MACRO_CONFIRMED == "v0.1.1"
    assert QGV_ANALYSIS_CONTRACT == "v1.7.6"
    for rel, digest in SOURCE_SHA256.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest

    def norm(obj):
        if dataclasses.is_dataclass(obj):
            obj = dataclasses.asdict(obj)
        if isinstance(obj, dict):
            return {k: norm(v) for k, v in sorted(obj.items()) if k != "technical_snapshot_id"}
        if isinstance(obj, (list, tuple)):
            return [norm(v) for v in obj]
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    rows = [
        [0.01, -0.02, 0.03, 0.005, 0.01, -0.001],
        [0.0],
        [],
        [0.05] * 6,
        [-0.01, -0.02, -0.01, -0.03, -0.02],
        [0.002] * 8,
    ]
    out = [TechnicalEngine().evaluate("c", now, r, synthetic=True) for r in rows]
    blob = json.dumps([norm(x) for x in out], sort_keys=True).encode()
    assert hashlib.sha256(blob).hexdigest() == ENGINE_FINGERPRINT
