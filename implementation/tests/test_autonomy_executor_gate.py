import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "autonomy_executor_gate.py"
spec = importlib.util.spec_from_file_location("autonomy_executor_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gate)


class HG03ExecutorGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "implementation/docs/coordination/governance").mkdir(parents=True)
        self.old_repo_root = gate.REPO_ROOT
        self.old_config = gate.CONFIG
        self.old_mode = gate.MODE_FILE
        self.old_state = gate.STATE_FILE
        gate.REPO_ROOT = root
        gate.CONFIG = root / "implementation/docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json"
        gate.MODE_FILE = root / "implementation/docs/coordination/governance/AUTONOMY_MODE"
        gate.STATE_FILE = root / "implementation/docs/coordination/governance/AUTONOMY_RUNTIME_STATE.json"
        gate.CONFIG.write_text(json.dumps({
            "operating_values": {
                "cycle_max_tasks": 5,
                "lease_ttl_seconds": 7200,
                "repair_round_cap": 3
            }
        }), encoding="utf-8")
        gate.MODE_FILE.write_text("RUN\n", encoding="utf-8")

    def tearDown(self):
        gate.REPO_ROOT = self.old_repo_root
        gate.CONFIG = self.old_config
        gate.MODE_FILE = self.old_mode
        gate.STATE_FILE = self.old_state
        self.tmp.cleanup()

    def test_read_only_blocks_cycle_start(self):
        gate.MODE_FILE.write_text("READ_ONLY\n", encoding="utf-8")
        with self.assertRaises(gate.GateError):
            gate.start_cycle("w", "b", "c", 100)

    def test_pause_blocks_cycle_start(self):
        gate.MODE_FILE.write_text("PAUSE\n", encoding="utf-8")
        with self.assertRaises(gate.GateError):
            gate.start_cycle("w", "b", "c", 100)

    def test_start_cycle_sets_two_hour_lease(self):
        s = gate.start_cycle("w", "b", "c", 100)
        self.assertEqual(s.lease_expires_at_epoch, 7300)
        self.assertEqual(s.tasks_used, 0)

    def test_task_cap_five_then_denies_sixth(self):
        gate.start_cycle("w", "b", "c", 100)
        for i in range(5):
            gate.before_task("w", "c", 101 + i)
        with self.assertRaises(gate.GateError):
            gate.before_task("w", "c", 110)

    def test_repair_cap_three_then_requires_replan(self):
        gate.start_cycle("w", "b", "c", 100)
        for i in range(3):
            gate.before_repair("w", "c", "F1", 101 + i)
        with self.assertRaises(gate.GateError):
            gate.before_repair("w", "c", "F1", 110)

    def test_publish_rechecks_mode(self):
        gate.start_cycle("w", "b", "c", 100)
        gate.MODE_FILE.write_text("PAUSE\n", encoding="utf-8")
        with self.assertRaises(gate.GateError):
            gate.before_publish("w", "c", 101)

    def test_expired_lease_never_auto_reclaimed(self):
        gate.start_cycle("w", "b", "c", 100)
        with self.assertRaises(gate.GateError):
            gate.start_cycle("w2", "b2", "c2", 7401)

    def test_wrong_holder_cannot_mutate_or_publish(self):
        gate.start_cycle("w", "b", "c", 100)
        with self.assertRaises(gate.GateError):
            gate.before_task("other", "c", 101)
        with self.assertRaises(gate.GateError):
            gate.before_publish("other", "c", 101)

    def test_end_cycle_releases_local_runtime_state(self):
        gate.start_cycle("w", "b", "c", 100)
        s = gate.end_cycle("w", "c", 101)
        self.assertEqual(s.status, "IDLE")
        self.assertIsNone(s.lease_expires_at_epoch)


if __name__ == "__main__":
    unittest.main()
