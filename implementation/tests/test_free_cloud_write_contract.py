import importlib.util,sys,unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"tools"/"free_cloud_write_contract.py"
s=importlib.util.spec_from_file_location("free_cloud_write_contract",P)
m=importlib.util.module_from_spec(s); sys.modules[s.name]=m
assert s.loader is not None; s.loader.exec_module(m)

class WriteContractTests(unittest.TestCase):
    def test_only_exact_branch_and_path_allowed(self):
        r=m.validate("automation/free-cloud-state-v1",[
            "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"
        ])
        self.assertTrue(r["allowed"])

    def test_global_branch_denied(self):
        r=m.validate("integration/global-handoff-v1",[
            "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"
        ])
        self.assertFalse(r["allowed"])
        self.assertIn("protected_branch",r["reasons"])

    def test_canonical_branch_denied(self):
        r=m.validate("claude/investment-system-top500-validation-alrugm",[
            "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"
        ])
        self.assertFalse(r["allowed"])

    def test_other_path_denied(self):
        r=m.validate("automation/free-cloud-state-v1",[
            "implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md"
        ])
        self.assertFalse(r["allowed"])

    def test_governance_path_denied(self):
        r=m.validate("automation/free-cloud-state-v1",[
            "implementation/docs/coordination/governance/AUTONOMY_MODE"
        ])
        self.assertFalse(r["allowed"])

if __name__=="__main__":
    unittest.main()
