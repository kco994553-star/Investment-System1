import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "autonomy_gate_a_guard.py"
spec = importlib.util.spec_from_file_location("autonomy_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guard)


class AutonomyGateAGuardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "immutable_exact_paths": ["frozen.json"],
            "append_only_exact_paths": ["DECISIONS.md"],
            "append_only_prefixes": ["evidence/"],
        }

    def test_parse_name_status(self):
        self.assertEqual(
            guard.parse_name_status("M\tfrozen.json\nA\tevidence/new.json\n"),
            [("M", ["frozen.json"]), ("A", ["evidence/new.json"])],
        )

    def test_immutable_modify_fails(self):
        v = guard.classify_diff([("M", ["frozen.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_immutable_delete_fails(self):
        v = guard.classify_diff([("D", ["frozen.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_append_only_add_is_allowed(self):
        self.assertEqual(
            guard.classify_diff([("A", ["evidence/new.json"])], self.cfg), []
        )

    def test_append_only_modify_fails(self):
        v = guard.classify_diff([("M", ["evidence/existing.json"])], self.cfg)
        self.assertEqual(len(v), 1)

    def test_append_only_rename_fails(self):
        v = guard.classify_diff(
            [("R100", ["evidence/a.json", "evidence/b.json"])], self.cfg
        )
        self.assertEqual(len(v), 1)

    def test_unprotected_change_allowed(self):
        self.assertEqual(
            guard.classify_diff([("M", ["implementation/src/x.py"])], self.cfg), []
        )

    def test_config_operating_values_are_pinned(self):
        cfg = guard.load_config()
        self.assertEqual(cfg["operating_values"]["cycle_max_tasks"], 5)
        self.assertEqual(cfg["operating_values"]["lease_ttl_seconds"], 7200)
        self.assertEqual(cfg["operating_values"]["repair_round_cap"], 3)

    def test_invalid_mode_fails_closed(self):
        cfg = guard.load_config()
        mode_path = guard.ROOT / cfg["autonomy_mode_file"].removeprefix("implementation/")
        original = mode_path
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            p = fake_root / cfg["autonomy_mode_file"]
            p.parent.mkdir(parents=True)
            p.write_text("INVALID\n", encoding="utf-8")
            old_root = guard.REPO_ROOT
            try:
                guard.REPO_ROOT = fake_root
                with self.assertRaises(guard.GuardError):
                    guard.validate_mode(cfg)
            finally:
                guard.REPO_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
