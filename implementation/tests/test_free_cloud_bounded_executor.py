import importlib.util, sys, tempfile, unittest, json
from pathlib import Path

MODULE_PATH=Path(__file__).resolve().parents[1]/"tools"/"free_cloud_bounded_executor.py"
spec=importlib.util.spec_from_file_location("free_cloud_bounded_executor",MODULE_PATH)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod
assert spec.loader is not None; spec.loader.exec_module(mod)

class BoundedExecutorTests(unittest.TestCase):
    def test_plan_is_path_bounded(self):
        p=mod.build_plan()
        self.assertEqual(p["allowed_branch"],"automation/free-cloud-state-v1")
        self.assertEqual(p["allowed_paths"],[
            "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"
        ])
        self.assertIn("canonical",p["forbidden"])
        self.assertIn("paid API",p["forbidden"])

    def test_current_repo_is_fail_closed(self):
        p=mod.build_plan()
        self.assertFalse(p["allow_mutation"])
        self.assertIn(p["reason"],{"AUTONOMY_MODE_READ_ONLY","AUTONOMY_MODE_PAUSE","GATE_A_CLOSED","ACTIVE_RUNTIME_STATE"})

if __name__=="__main__":
    unittest.main()
