import importlib.util, sys, unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"tools"/"free_cloud_material_queue.py"
s=importlib.util.spec_from_file_location("free_cloud_material_queue",P)
m=importlib.util.module_from_spec(s); sys.modules[s.name]=m
assert s.loader is not None; s.loader.exec_module(m)

class MaterialQueueTests(unittest.TestCase):
    def test_no_change_is_no_action(self):
        r=m.build("a","a",[])
        self.assertFalse(r["material_change"])
        self.assertEqual(r["main_action"],"NO_ACTION")

    def test_qgv_change_routes_qgv(self):
        r=m.build("a","b",["implementation/docs/qgv_common_contract_vnext/x.md"])
        self.assertTrue(r["material_change"])
        self.assertEqual(r["queue"][0]["lane"],"qgv")

    def test_chart_change_routes_chart(self):
        r=m.build("a","b",["implementation/experiments/chart-contract-v0.1/CURRENT_HANDOFF.md"])
        self.assertEqual(r["queue"][0]["lane"],"chart")

    def test_multiple_paths_deduplicate_lane(self):
        r=m.build("a","b",[
            "implementation/docs/qgv/a.md",
            "implementation/docs/qgv/b.md",
        ])
        self.assertEqual(len(r["queue"]),1)

    def test_never_authorizes_product_mutation(self):
        r=m.build("a","b",["implementation/web/app.js"])
        self.assertFalse(r["automatic_product_mutation"])

if __name__=="__main__":
    unittest.main()
