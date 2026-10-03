"""Producer Infrastructure v1 compatibility of a QGV export, using the Infrastructure's own code.

Producer Infrastructure v1 is a read-only, unmerged dependency. CI checks it out at the pinned commit and sets
QGV_PRODUCER_INFRA_SRC=<checkout>/implementation/src. Without that variable this test only checks that the
dependency is absent on this branch. That is a precondition, not compatibility evidence.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from importlib.util import find_spec

from investment_system.qgv_producer import infra_boundary
from investment_system.qgv_producer.exporter import export_batch

from tests.test_qgv_producer import T0, batch, make_store

ROOT = Path(__file__).resolve().parents[1]


def test_qgv_export_is_compatible_with_pinned_producer_infrastructure(tmp_path):
    src = os.environ.get("QGV_PRODUCER_INFRA_SRC")
    if not src:
        infra = infra_boundary.load_infra()
        if infra is None:  # original isolated branch; see docs/qgv_producer/STATUS.md
            assert infra is None
            assert find_spec("investment_system.producers") is None, "integrated dependency could not be loaded"
            return
        assert not infra_boundary.missing_api(infra), "integrated dependency API is incomplete"
        src = str(ROOT / "src")
    store, index = make_store(tmp_path)
    b = batch(store, index)
    export_batch(b.records, b.manifest, tmp_path / "exports")
    report = tmp_path / "compat.json"
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "qgv_producer_infra_compat.py"), "--infra-src", src,
                           "--root", str(tmp_path), "--exports", "exports", "--dates", T0.date().isoformat(),
                           "--report", str(report), "--now", "2026-10-01T00:00:00+00:00"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    out = json.loads(report.read_text())
    assert out["status"] == "PASS"
    d = T0.date().isoformat()
    assert out["checks"][f"{d}:research_candidate_rejected"]["error"]["type"] == "ResearchStatusError"
    assert out["checks"][f"{d}:published_not_available"]["reason_code"] == "QGV_RESEARCH_ONLY_NO_EXPORT"
    assert out["checks"][f"{d}:bundle_assembles_and_web_validates"]["qgv_state"] == "NOT_AVAILABLE"
