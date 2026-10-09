import importlib.util
import sys
import os
import subprocess
import io
import contextlib
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

class AppendOnlyRepositoryStateTests(unittest.TestCase):
    """Exercise real Git states; fixtures contain synthetic public text only."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_root = guard.REPO_ROOT
        guard.REPO_ROOT = self.root
        self.addCleanup(setattr, guard, "REPO_ROOT", self.old_root)
        self.cfg = guard.load_config()
        self.register = self.cfg["append_only_exact_paths"][0]
        self.evidence = self.cfg["append_only_prefixes"][0] + "synthetic.txt"
        self.frozen = self.cfg["immutable_exact_paths"][0]
        self.original = b"Synthetic original decision.\n"
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "synthetic-test@example.invalid")
        self.git("config", "user.name", "SYNTHETIC APPEND GUARD TEST")
        self.write(self.cfg["autonomy_mode_file"], b"READ_ONLY\n")
        self.write(self.register, self.original)
        self.write(self.evidence, b"Synthetic original evidence.\n")
        self.write(self.frozen, b"Synthetic frozen artifact.\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(
            ["git", "--no-replace-objects", *args], cwd=self.root,
            check=True, capture_output=True, text=True,
        ).stdout

    def write(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "Synthetic guard state")

    def check(self, base=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = guard.cmd_diff(self.base if base is None else base)
        return result, json.loads(output.getvalue())

    def assert_pass(self, base=None):
        result, receipt = self.check(base)
        self.assertEqual(result, 0, receipt)
        self.assertEqual(receipt["gate_a_repository_guard"], "PASS")

    def assert_fail(self, base=None):
        result, receipt = self.check(base)
        self.assertEqual(result, 1, receipt)
        self.assertEqual(receipt["gate_a_repository_guard"], "FAIL")

    def test_real_global_config_committed_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic newly authorized decision.\n")
        self.commit()
        self.assert_pass()

    def test_staged_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic appended decision.\n")
        self.git("add", "--", self.register)
        self.assert_pass()

    def test_tracked_worktree_register_append_passes(self):
        self.write(self.register, self.original + b"Synthetic appended decision.\n")
        self.assert_pass()

    def test_utf8_crlf_and_missing_final_newline_append_preserves_bytes(self):
        self.write(self.register, "Synthetic decision 한글\r\nNo newline".encode("utf-8"))
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        with (self.root / self.register).open("ab") as file:
            file.write(b" appended bytes\n")
        self.commit()
        self.assert_pass()

    def test_empty_register_can_append(self):
        self.write(self.register, b"")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, self.original)
        self.commit()
        self.assert_pass()

    def test_committed_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.assert_fail()

    def test_register_truncation_fails(self):
        self.write(self.register, self.original[:-1])
        self.commit()
        self.assert_fail()

    def test_committed_delete_fails(self):
        (self.root / self.register).unlink()
        self.commit()
        self.assert_fail()

    def test_committed_rename_fails(self):
        self.git("mv", self.register, self.register + ".moved")
        self.commit()
        self.assert_fail()

    def test_register_mode_change_fails(self):
        (self.root / self.register).chmod(0o755)
        self.commit()
        self.assert_fail()

    def test_register_symlink_type_change_fails(self):
        (self.root / self.register).unlink()
        (self.root / self.register).symlink_to("missing-target")
        self.commit()
        self.assert_fail()

    def test_binary_register_append_fails(self):
        self.write(self.register, b"Synthetic\0binary")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, b"Synthetic\0binary appended")
        self.commit()
        self.assert_fail()

    def test_non_utf8_register_append_fails(self):
        self.write(self.register, b"Synthetic\xfftext")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(self.register, b"Synthetic\xfftext appended")
        self.commit()
        self.assert_fail()

    def test_existing_evidence_append_fails(self):
        with (self.root / self.evidence).open("ab") as file:
            file.write(b"Append still changes original evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_regular_evidence_passes(self):
        self.write(self.evidence + ".new", b"Synthetic new evidence.\n")
        self.commit()
        self.assert_pass()

    def test_new_binary_evidence_passes(self):
        self.write(self.evidence + ".bin", b"Synthetic\0binary evidence")
        self.commit()
        self.assert_pass()

    def test_new_evidence_rewrite_in_later_commit_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.commit()
        self.write(path, b"Rewritten synthetic evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_evidence_removed_in_later_commit_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.commit()
        (self.root / path).unlink()
        self.commit()
        self.assert_fail()

    def test_rewrite_then_restore_fails(self):
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_delete_then_restore_fails(self):
        (self.root / self.register).unlink()
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_rename_then_restore_fails(self):
        self.git("mv", self.register, self.register + ".moved")
        self.commit()
        self.git("mv", self.register + ".moved", self.register)
        self.commit()
        self.assert_fail()

    def test_append_then_remove_appended_bytes_fails(self):
        self.write(self.register, self.original + b"Synthetic append.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_frozen_rewrite_then_restore_fails(self):
        original = (self.root / self.frozen).read_bytes()
        self.write(self.frozen, b"Rewritten synthetic frozen artifact.\n")
        self.commit()
        self.write(self.frozen, original)
        self.commit()
        self.assert_fail()

    def test_staged_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.git("add", "--", self.register)
        self.assert_fail()

    def test_tracked_worktree_register_rewrite_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.assert_fail()

    def test_staged_rewrite_hidden_by_worktree_restore_fails(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.git("add", "--", self.register)
        self.write(self.register, self.original)
        self.assert_fail()

    def test_staged_delete_hidden_by_untracked_restore_fails(self):
        self.git("rm", "--", self.register)
        self.write(self.register, self.original)
        self.assert_fail()

    def test_tracked_worktree_delete_fails(self):
        (self.root / self.register).unlink()
        self.assert_fail()

    def test_worktree_mode_change_detected_with_filemode_false(self):
        self.git("config", "core.filemode", "false")
        (self.root / self.register).chmod(0o755)
        self.assert_fail()

    def test_worktree_symlink_does_not_follow_untracked_target(self):
        self.write("untracked-target.txt", self.original)
        (self.root / self.register).unlink()
        (self.root / self.register).symlink_to(self.root / "untracked-target.txt")
        self.assert_fail()

    def test_worktree_symlink_parent_does_not_follow_external_target(self):
        with tempfile.TemporaryDirectory() as external:
            parent = (self.root / self.register).parent
            (Path(external) / Path(self.register).name).write_bytes(self.original)
            parent.rename(parent.with_name("untracked-backup"))
            parent.symlink_to(external, target_is_directory=True)
            # Mode validation lives below this same directory; read it before
            # changing the parent by using another valid, tracked mode path.
            self.cfg = dict(self.cfg, autonomy_mode_file="SYNTHETIC_MODE")
            self.write("SYNTHETIC_MODE", b"READ_ONLY\n")
            old_load = guard.load_config
            guard.load_config = lambda: self.cfg
            self.addCleanup(setattr, guard, "load_config", old_load)
            self.assert_fail()

    def test_staged_new_evidence_worktree_rewrite_fails(self):
        path = self.evidence + ".new"
        self.write(path, b"Synthetic new evidence.\n")
        self.git("add", "--", path)
        self.write(path, b"Rewritten synthetic evidence.\n")
        self.assert_fail()

    def test_side_parent_rewrite_restore_is_inspected(self):
        self.git("branch", "side")
        self.write("main.txt", b"Synthetic main change.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, b"Rewritten old decision.\n")
        self.commit()
        self.write(self.register, self.original)
        self.commit()
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "Synthetic merge", "side")
        self.assert_fail()

    def test_merge_result_cannot_remove_side_parent_append(self):
        self.git("branch", "side")
        self.write("main.txt", b"Synthetic main change.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, self.original + b"Synthetic side append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "--no-commit", "side")
        self.write(self.register, self.original)
        self.commit()
        self.assert_fail()

    def test_divergent_reference_uses_resolved_merge_base(self):
        self.git("branch", "reference")
        self.write(self.register, self.original + b"Synthetic HEAD append.\n")
        self.commit()
        self.git("checkout", "-q", "reference")
        self.write(self.register, self.original + b"Different reference append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        self.assert_pass("reference")

    def test_missing_comparison_ref_fails_closed(self):
        with self.assertRaises(guard.GuardError):
            self.check("missing-comparison-reference")

    def test_option_shaped_comparison_ref_fails_closed(self):
        with self.assertRaises(guard.GuardError):
            self.check("--help")

    def test_protected_unmerged_index_fails_closed(self):
        self.git("branch", "side")
        self.write(self.register, self.original + b"Synthetic main append.\n")
        self.commit()
        self.git("checkout", "-q", "side")
        self.write(self.register, self.original + b"Synthetic side append.\n")
        self.commit()
        self.git("checkout", "-q", "main")
        merge = subprocess.run(["git", "merge", "--no-commit", "side"], cwd=self.root, capture_output=True)
        self.assertNotEqual(merge.returncode, 0)
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_evidence_filename_with_tabs_newlines_unicode_is_protected(self):
        path = self.evidence + "\t한글\n:literal"
        self.write(path, b"Synthetic original evidence.\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(path, b"Rewritten evidence.\n")
        self.commit()
        self.assert_fail()

    def test_new_protected_symlink_fails(self):
        path = self.evidence + ".link"
        (self.root / path).symlink_to("missing-target")
        self.commit()
        self.assert_fail()

    def test_untracked_unregistered_private_device_file_is_not_read(self):
        self.write("untracked-device.json", b'{"schema":"device-actual-holdings/1","kind":"ACTUAL","positions":[{"symbol":"SYNTHETIC","quantity":1,"average_cost":1,"currency":"ZZZ"}]}')
        self.assert_pass()

    def test_all_configured_exact_registers_allow_preserved_text_append(self):
        for path in self.cfg["append_only_exact_paths"]:
            self.write(path, self.original)
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        for path in self.cfg["append_only_exact_paths"]:
            self.write(path, self.original + b"Synthetic append.\n")
        self.commit()
        self.assert_pass()

    def test_missing_comparison_blob_fails_closed(self):
        oid = self.git("rev-parse", self.base + ":" + self.register).strip()
        self.write(self.register, self.original + b"Synthetic append.\n")
        self.commit()
        (self.root / ".git/objects" / oid[:2] / oid[2:]).unlink()
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_committed_mode_change_then_restore_fails(self):
        (self.root / self.register).chmod(0o755)
        self.commit()
        (self.root / self.register).chmod(0o644)
        self.commit()
        self.assert_fail()

    def test_staged_mode_change_with_unchanged_worktree_fails(self):
        self.git("update-index", "--chmod=+x", "--", self.register)
        self.assert_fail()

    def test_evidence_prefix_protection_wins_over_exact_log_overlap(self):
        self.cfg = dict(self.cfg, append_only_exact_paths=[*self.cfg["append_only_exact_paths"], self.evidence])
        old_load = guard.load_config
        guard.load_config = lambda: self.cfg
        self.addCleanup(setattr, guard, "load_config", old_load)
        with (self.root / self.evidence).open("ab") as file:
            file.write(b"Synthetic evidence append.\n")
        self.commit()
        self.assert_fail()

    def test_worktree_read_may_update_access_time(self):
        file = self.root / self.register
        os.utime(file, (1, file.stat().st_mtime))
        self.assert_pass()

    def test_native_graft_cannot_hide_rewrite_restore_history(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.commit()
        self.write(self.register, self.original + b"Synthetic restored append.\n")
        self.commit()
        self.assert_fail()
        head = self.git("rev-parse", "HEAD").strip()
        self.write(".git/info/grafts", (head + " " + self.base + "\n").encode("ascii"))
        self.assertEqual(self.git("rev-parse", "--is-shallow-repository").strip(), "false")
        self.assertEqual(len(self.git("rev-list", self.base + "..HEAD").splitlines()), 1)
        with self.assertRaises(guard.GuardError):
            self.check()

    def test_redirected_graft_cannot_hide_rewrite_restore_history(self):
        self.write(self.register, b"Rewritten synthetic decision.\n")
        self.commit()
        self.write(self.register, self.original + b"Synthetic restored append.\n")
        self.commit()
        self.assert_fail()
        head = self.git("rev-parse", "HEAD").strip()
        with tempfile.TemporaryDirectory() as external:
            graft_file = Path(external) / "synthetic-grafts"
            graft_file.write_text(head + " " + self.base + "\n", encoding="ascii")
            child_env = dict(os.environ, GIT_GRAFT_FILE=str(graft_file))
            history = subprocess.run(
                ["git", "--no-replace-objects", "rev-list", self.base + "..HEAD"],
                cwd=self.root, env=child_env, check=True, capture_output=True, text=True,
            )
            self.assertEqual(len(history.stdout.splitlines()), 1)
            child_code = (
                "import importlib.util, pathlib, sys; "
                "s=importlib.util.spec_from_file_location('synthetic_guard',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "m.REPO_ROOT=pathlib.Path(sys.argv[2]); "
                "sys.argv=['guard','diff','--base',sys.argv[3]]; "
                "sys.exit(m.main())"
            )
            checked = subprocess.run(
                [sys.executable, "-c", child_code, str(MODULE_PATH), str(self.root), self.base],
                cwd=self.root, env=child_env, capture_output=True, text=True,
            )
            self.assertEqual(checked.returncode, 2)
            self.assertIn("AUTONOMY_GUARD_FAIL:", checked.stderr)
            self.assertNotIn(str(graft_file), checked.stderr)


if __name__ == "__main__":
    unittest.main()
