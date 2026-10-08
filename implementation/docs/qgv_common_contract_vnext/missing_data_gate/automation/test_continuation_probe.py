"""Meaningful control-boundary tests; no production evaluator or policy oracle."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from continuation_probe import (canonical_hash, file_hash, output_digest,
                                select, task_fingerprint, two_hop_receipt_readiness)


class ContinuationProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        for name, content in {"source.py": "legacy calculation\n", "approval.json":
                              '{"scope":"M1-M5 principles only"}',
                              "method.json": '{"method":"legacy"}',
                              "acceptance.md": "Exact legacy source comparison acceptance v1\n"}.items():
            (self.repo / name).write_text(content)
        self.task = {
            "id": "HOP1", "version": "1", "classification": "D1",
            "authority_scope": "EXPLICIT_AUTHORIZED_AUDIT_DESIGN_ONLY",
            "work_spec": "Generate legacy replay manifest from existing factor audit",
            "semantic_inputs": [{"path": "source.py", "sha256": file_hash(self.repo / "source.py")}],
            "method_policy_refs": [{"id": "legacy", "path": "method.json",
                                    "sha256": file_hash(self.repo / "method.json")}],
            "approval_dependencies": [{"id": "M1-M5", "scope": "PRINCIPLES_ONLY",
                                       "path": "approval.json", "sha256": file_hash(self.repo / "approval.json")}],
            "dependencies": [], "output_contract": {"paths": ["manifest.json"]},
            "acceptance_ref": {"id": "legacy-code-comparison", "version": "1",
                               "path": "acceptance.md", "sha256": file_hash(self.repo / "acceptance.md")},
        }
        self.state = {"repository": "kco994553-star/Investment-System1", "lease": None,
                      "continuation_plan": {"tasks": [self.task], "two_hop_task_ids": ["HOP1", "HOP2"]}}

    def fp(self, task=None):
        return task_fingerprint(self.state["repository"], task or self.task)

    def receipt(self, task=None, disposition="COMPLETED"):
        task = task or self.task
        outputs = []
        for relative in task["output_contract"]["paths"]:
            (self.repo / relative).write_text(json.dumps({"legacy_unchanged": True, "task": task["id"]}))
            outputs.append({"path": relative, "sha256": file_hash(self.repo / relative)})
        return {"task_id": task["id"], "task_fingerprint": self.fp(task), "disposition": disposition,
                "task_version": task["version"], "input_digest": canonical_hash(
                    task["semantic_inputs"] + task["method_policy_refs"] + task["approval_dependencies"] +
                    [task["acceptance_ref"]]),
                "acceptance": {"status": "ACCEPTED", "validator_ref": task["acceptance_ref"]},
                "outputs": outputs}

    def status(self, receipts=None, events=None):
        return select(self.repo, self.state, receipts or [], events or [])

    def test_unfinished_task_runs_without_event(self):
        result = self.status()
        self.assertEqual(result["status"], "EXECUTABLE_STATE_WORK")
        self.assertEqual(result["event_input_status"], "NO_NEW_MATERIAL_EVENT")

    def test_self_only_event_does_not_suppress_unfinished_task(self):
        result = self.status(events=[{"material": True, "self_control_only": True}])
        self.assertIsNotNone(result["next_task"])

    def test_accepted_completed_outputs_are_not_reexecuted(self):
        self.state["continuation_plan"]["finite_task_ids"] = ["HOP1"]
        result = self.status([self.receipt()])
        self.assertEqual(result["status"], "TERMINAL_D1_D2_COMPLETE_AWAITING_D3")
        self.assertIsNone(result["next_task"])

    def test_unbound_hop2_template_prevents_premature_terminal(self):
        result = self.status([self.receipt()])
        self.assertEqual(result["status"], "WAITING_NEXT_TASK_BINDING")
        self.assertEqual(result["unbound_finite_task_ids"], ["HOP2"])

    def test_wait_and_intake_receipts_do_not_complete_task(self):
        for disposition in ("PENDING_D3", "WAITING_FOR_APPROVAL", "WAITING_EXTERNAL", "NO_ACTION", "INTAKE_ONLY"):
            with self.subTest(disposition=disposition):
                self.assertIsNotNone(self.status([self.receipt(disposition=disposition)])["next_task"])

    def test_rejected_or_unverified_output_receipt_needs_recovery(self):
        receipt = self.receipt()
        receipt["acceptance"]["status"] = "PROPOSED"
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "RECEIPT_VALIDATION_REQUIRED")

    def test_completed_state_boolean_cannot_replace_receipt(self):
        self.task["state"] = "COMPLETED"
        self.assertIsNotNone(self.status()["next_task"])

    def test_output_content_drift_is_not_completed(self):
        receipt = self.receipt()
        (self.repo / "manifest.json").write_text("different\n")
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "RECEIPT_VALIDATION_REQUIRED")

    def test_completed_receipt_cannot_hide_current_source_drift(self):
        receipt = self.receipt()
        (self.repo / "source.py").write_text("changed method\n")
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "WAITING_EXACT_INPUTS")

    def test_completed_receipt_cannot_hide_revoked_task_authority(self):
        receipt = self.receipt()
        self.task["authority_scope"] = "REVOKED"
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "AUTHORITY_SCOPE_UNRESOLVED")

    def test_unpinned_acceptance_validator_blocks_task(self):
        self.task["acceptance_ref"].pop("sha256")
        self.assertIsNone(self.status()["next_task"])

    def test_completed_receipt_cannot_hide_changed_acceptance_validator(self):
        receipt = self.receipt()
        (self.repo / "acceptance.md").write_text("looser acceptance v2\n")
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "WAITING_EXACT_INPUTS")

    def test_d3_path_blocked_while_independent_task_runs(self):
        d3 = copy.deepcopy(self.task)
        d3.update(id="PRODUCTION_ROLE", classification="D3")
        self.state["continuation_plan"]["tasks"].insert(0, d3)
        result = self.status()
        self.assertEqual(result["tasks"][0]["status"], "PENDING_D3")
        self.assertEqual(result["next_task"]["task_id"], "HOP1")

    def test_stale_looking_lease_is_never_stolen(self):
        self.state["lease"] = {"token": "other", "expiry": "1999-01-01", "status": "RUNNING"}
        result = self.status()
        self.assertIsNone(result["next_task"])
        self.assertEqual(result["tasks"][0]["status"], "BLOCKED_ACTIVE_LEASE_NO_TAKEOVER")
        self.assertEqual(self.state["lease"]["token"], "other")

    def test_own_lease_preview_is_read_only(self):
        self.state["lease"] = {"token": "mine"}
        result = select(self.repo, self.state, [], own_lease_token="mine")
        self.assertIsNotNone(result["next_task"])
        self.assertFalse(result["mutation_performed"])

    def test_missing_source_and_changed_source_hold_task(self):
        (self.repo / "source.py").unlink()
        self.assertIsNone(self.status()["next_task"])
        (self.repo / "source.py").write_text("new method\n")
        self.assertIn("INPUT_HASH_CHANGED:source.py", self.status()["tasks"][0]["reasons"])

    def test_missing_approval_scope_is_not_accepted(self):
        self.task["approval_dependencies"][0].pop("scope")
        self.assertIsNone(self.status()["next_task"])

    def test_control_noise_not_semantic_input(self):
        path = self.repo / "automation/STATE.json"
        path.parent.mkdir()
        path.write_text("{}")
        self.task["semantic_inputs"] = [{"path": "automation/STATE.json", "sha256": file_hash(path)}]
        self.assertIsNone(self.status()["next_task"])

    def test_owner_head_lease_time_and_status_noise_do_not_change_fingerprint(self):
        before = self.fp()
        self.task.update(owner_head="arbitrary", updated_at="now", status="RUNNING", lease="noise")
        self.assertEqual(before, self.fp())

    def test_method_policy_source_and_approval_scope_change_fingerprint(self):
        before = self.fp()
        self.task["method_policy_refs"][0]["id"] = "new-method"
        self.assertNotEqual(before, self.fp())
        before = self.fp()
        self.task["approval_dependencies"][0]["scope"] = "different"
        self.assertNotEqual(before, self.fp())

    def test_same_failed_fingerprint_requires_replan(self):
        receipt = self.receipt(disposition="FAILED")
        self.assertEqual(self.status([receipt])["tasks"][0]["status"], "FAILED_REPLAN_REQUIRED")

    def test_dependency_unmet_blocks_only_dependent_path(self):
        hop2 = copy.deepcopy(self.task)
        hop2.update(id="HOP2", dependencies=[{"task_id": "HOP1", "task_fingerprint": self.fp(),
                                            "output_digest": "unbound"}])
        self.state["continuation_plan"]["tasks"].append(hop2)
        result = self.status()
        self.assertEqual(result["tasks"][1]["status"], "WAITING_DEPENDENCY")
        self.assertEqual(result["next_task"]["task_id"], "HOP1")

    def bound_hop2(self, hop1_receipt):
        task = copy.deepcopy(self.task)
        task.update(id="HOP2", work_spec="Independent exact replay manifest closure",
                    output_contract={"paths": ["closure.json"]},
                    dependencies=[{"task_id": "HOP1", "task_fingerprint": self.fp(),
                                   "output_digest": output_digest(hop1_receipt)}])
        task["semantic_inputs"].append(hop1_receipt["outputs"][0])
        self.state["continuation_plan"]["tasks"].append(task)
        return task

    def test_local_two_step_progression_not_real_autonomous_verification(self):
        hop1 = self.receipt()
        task2 = self.bound_hop2(hop1)
        result = self.status([hop1])
        self.assertEqual(result["next_task"]["task_id"], "HOP2")
        hop2 = self.receipt(task2)
        terminal = self.status([hop1, hop2])
        self.assertEqual(terminal["status"], "TERMINAL_D1_D2_COMPLETE_AWAITING_D3")
        check = two_hop_receipt_readiness(self.repo, self.state, [hop1, hop2])
        self.assertEqual(check["status"], "REAL_EXECUTION_EVIDENCE_REQUIRED")
        self.assertFalse(check["verified"])

    def test_two_writes_one_scheduler_run_are_not_two_hops(self):
        hop1 = self.receipt()
        task2 = self.bound_hop2(hop1)
        hop2 = self.receipt(task2)
        for receipt in (hop1, hop2):
            receipt["execution"] = {"kind": "PLATFORM_SCHEDULED", "automation_id": "watch",
                                    "platform_execution_id": "same", "platform_readback_ref": "ref",
                                    "fresh_read_ref": "ref", "lease_evidence_ref": "ref"}
        check = two_hop_receipt_readiness(self.repo, self.state, [hop1, hop2])
        self.assertEqual(check["status"], "DISTINCT_SCHEDULER_EXECUTIONS_REQUIRED")

    def test_structural_run_claims_still_require_platform_authentication(self):
        hop1 = self.receipt()
        task2 = self.bound_hop2(hop1)
        hop2 = self.receipt(task2)
        for index, receipt in enumerate((hop1, hop2)):
            receipt["execution"] = {"kind": "PLATFORM_SCHEDULED", "automation_id": "watch",
                                    "platform_execution_id": f"run-{index}", "platform_readback_ref": "ref",
                                    "fresh_read_ref": "ref", "lease_evidence_ref": "ref"}
        check = two_hop_receipt_readiness(self.repo, self.state, [hop1, hop2])
        self.assertEqual(check["status"], "TWO_HOP_RECEIPTS_READY_FOR_PLATFORM_VERIFICATION")
        self.assertFalse(check["verified"])

    def test_dependency_cycle_rejected(self):
        hop2 = copy.deepcopy(self.task)
        hop2.update(id="HOP2", dependencies=[{"task_id": "HOP1"}])
        self.task["dependencies"] = [{"task_id": "HOP2"}]
        self.state["continuation_plan"]["tasks"].append(hop2)
        self.assertTrue(all(t["status"] == "DEPENDENCY_CYCLE" for t in self.status()["tasks"]))

    def test_failed_replan_changes_explicit_version_not_owner_head(self):
        failed = self.receipt(disposition="FAILED")
        (self.repo / "method.json").write_text('{"method":"legacy","locator_verified":true}')
        self.task["method_policy_refs"][0]["sha256"] = file_hash(self.repo / "method.json")
        self.task.update(version="2", replan={"parent_failed_fingerprint": failed["task_fingerprint"],
                                              "action": "Repair source locator then recheck exact file hashes",
                                              "evidence_hashes": [canonical_hash("locator evidence")]})
        self.assertIsNotNone(self.status([failed])["next_task"])

    def test_version_only_after_failure_does_not_retry(self):
        failed = self.receipt(disposition="FAILED")
        self.task["version"] = "2"
        self.assertEqual(self.status([failed])["tasks"][0]["status"], "EXPLICIT_ACTIONABLE_REPLAN_REQUIRED")

    def test_replan_with_unchanged_inputs_does_not_retry(self):
        failed = self.receipt(disposition="FAILED")
        self.task.update(version="2", replan={"parent_failed_fingerprint": failed["task_fingerprint"],
                                             "action": "Try again", "evidence_hashes": [canonical_hash("claim")]})
        self.assertEqual(self.status([failed])["tasks"][0]["status"], "REPLAN_NEW_VERSION_AND_CHANGED_INPUTS_REQUIRED")

    def test_missing_authority_is_not_inferred_from_weight_or_receipt(self):
        self.task["authority_scope"] = "UNRESOLVED"
        self.assertIsNone(self.status()["next_task"])

    def test_external_wait_is_not_task_completion(self):
        self.task["state"] = "WAITING_EXTERNAL"
        self.assertEqual(self.status()["tasks"][0]["status"], "WAITING_EXTERNAL")

    def test_selector_does_not_modify_repo_or_state(self):
        before_state = copy.deepcopy(self.state)
        before_files = {p.name: file_hash(p) for p in self.repo.iterdir() if p.is_file()}
        self.status(events=[{"material": True}])
        self.assertEqual(self.state, before_state)
        self.assertEqual(before_files, {p.name: file_hash(p) for p in self.repo.iterdir() if p.is_file()})


if __name__ == "__main__":
    unittest.main()
