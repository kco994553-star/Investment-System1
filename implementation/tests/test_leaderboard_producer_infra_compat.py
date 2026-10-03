"""Producer Infrastructure v1 is read-only and unmerged. Without LEADERBOARD_PRODUCER_INFRA_SRC this only
checks that the dependency is absent on this branch.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from importlib.util import find_spec

from investment_system.leaderboard_producer import infra_boundary

ROOT = Path(__file__).resolve().parents[1]


def test_leaderboard_export_is_compatible_with_pinned_producer_infrastructure(tmp_path):
    src = os.environ.get("LEADERBOARD_PRODUCER_INFRA_SRC")
    if not src:
        infra = infra_boundary.load_infra()
        if infra is None:  # original isolated branch; full comparison runs in integrated trees
            assert infra is None
            assert find_spec("investment_system.producers") is None, "integrated dependency could not be loaded"
            return
        assert not infra_boundary.missing_api(infra), "integrated dependency API is incomplete"
        src = str(ROOT / "src")
    exports = os.environ.get("LEADERBOARD_EXPORTS", str(ROOT / "reports" / "leaderboard_producer" / "full"))
    report = tmp_path / "compat.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "leaderboard_producer_infra_compat.py"),
         "--infra-src", src, "--root", str(ROOT), "--exports", str(Path(exports).relative_to(ROOT)),
         "--dates", "2024-12-31", "--report", str(report), "--now", "2026-10-01T00:00:00+00:00"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    out = json.loads(report.read_text())
    assert out["status"] == "PASS"
    assert out["checks"]["2024-12-31:research_candidate_rejected"]["error"]["type"] == "ResearchStatusError"
    assert out["checks"]["2024-12-31:published_not_available"]["reason_code"] == "LEADERBOARD_RESEARCH_ONLY_NO_EXPORT"
    assert out["checks"]["2024-12-31:bundle_assembles_and_web_validates"]["leaderboard_state"] == "NOT_AVAILABLE"
