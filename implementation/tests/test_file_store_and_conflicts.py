from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.enums import QualityState, TrackScope
from investment_system.qgv.identifiers import IdentifierRegistry
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.records import ScopedTrackStore

AS_OF = datetime(2026, 9, 23, tzinfo=timezone.utc)
# Resolved relative to the package so the suite is portable across AI sandboxes.
REG = Path(__file__).resolve().parents[2] / "Investment-System1 · Contract Conflict Register 2026-09-23.md"


def test_file_store_survives_reload(tmp_path):
    path = tmp_path / "track_store.json"
    store = ScopedTrackStore(FileTrackRecordStore(path))
    rec = store.record(TrackScope.QGV, "nvda", AS_OF, ("s1",), {"prediction": {"x": 1}, "decision": {}})
    rid = rec.track_record_id
    again = FileTrackRecordStore(path)
    loaded = again.get(rid)
    assert loaded.subject_id == "nvda"
    assert loaded.payload["prediction"]["x"] == 1
    try:
        again.overwrite(rid)
        assert False
    except Exception:
        pass


def test_tel_identity_isolated_not_us_connectivity():
    reg = IdentifierRegistry()
    assert reg.get("tokyo_electron").company_id == "tokyo_electron"
    assert reg.resolve_ticker("TEL") == QualityState.IDENTIFIER_AMBIGUOUS


def test_conflict_register_uses_new_status_model():
    text = REG.read_text(encoding="utf-8")
    assert "C-01" in text and "RESOLVED" in text
    assert "C-03" in text and "DECISION REQUIRED" in text
    assert "C-16" in text and "HISTORICAL-BLOCKED" in text
    assert "C-08" in text and "OPEN-ISOLATED" in text
