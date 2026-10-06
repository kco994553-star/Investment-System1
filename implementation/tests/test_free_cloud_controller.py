import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "free_cloud_controller.py"
spec = importlib.util.spec_from_file_location("free_cloud_controller", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


class FreeCloudControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        gov = root / "implementation/docs/coordination/governance"
        gov.mkdir(parents=True)
        self.old = (mod.ROOT, mod.GOV, mod.MODE, mod.GAPS, mod.STATE)
        mod.ROOT = root
        mod.GOV = gov
        mod.MODE = gov / "AUTONOMY_MODE"
        mod.GAPS = gov / "AUTONOMY_HARD_GUARD_GAPS_v1.1.md"
        mod.STATE = gov / "AUTONOMY_RUNTIME_STATE.json"
        mod.STATE.write_text(json.dumps({"status":"IDLE"}), encoding="utf-8")

    def tearDown(self):
        mod.ROOT, mod.GOV, mod.MODE, mod.GAPS, mod.STATE = self.old
        self.tmp.cleanup()

    def _set(self, mode, gate):
        mod.MODE.write_text(mode + "\n", encoding="utf-8")
        marker = "Gate A: **OPEN / UNATTENDED AUTONOMY ENABLED**" if gate else "Gate A: **CLOSED / UNATTENDED AUTONOMY DISABLED**"
        mod.GAPS.write_text(marker + "\n", encoding="utf-8")

    def test_read_only_is_fail_closed(self):
        self._set("READ_ONLY", True)
        self.assertFalse(mod.decision()["allow_mutation"])

    def test_run_with_closed_gate_is_fail_closed(self):
        self._set("RUN", False)
        self.assertEqual(mod.decision()["reason"], "GATE_A_CLOSED")

    def test_active_runtime_blocks_duplicate_executor(self):
        self._set("RUN", True)
        mod.STATE.write_text(json.dumps({"status":"RUNNING"}), encoding="utf-8")
        self.assertEqual(mod.decision()["reason"], "ACTIVE_RUNTIME_STATE")

    def test_run_open_idle_is_eligible(self):
        self._set("RUN", True)
        d = mod.decision()
        self.assertTrue(d["allow_mutation"])
        self.assertEqual(d["execution_class"], "DETERMINISTIC_D1_D2_D3A_ONLY")

    def test_invalid_mode_fails_closed(self):
        self._set("BROKEN", True)
        self.assertFalse(mod.decision()["allow_mutation"])
        self.assertEqual(mod.decision()["mode"], "INVALID")


if __name__ == "__main__":
    unittest.main()
