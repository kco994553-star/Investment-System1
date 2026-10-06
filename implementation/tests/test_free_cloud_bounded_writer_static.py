import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WF=ROOT/".github/workflows/free-cloud-bounded-writer.yml"

class BoundedWriterStaticTests(unittest.TestCase):
    def test_writer_permission_and_scope_are_explicit(self):
        text=WF.read_text(encoding="utf-8")
        self.assertIn("contents: write",text)
        self.assertIn("automation/free-cloud-state-v1",text)
        self.assertIn("implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json",text)

    def test_no_external_ai_secret_reference(self):
        text=WF.read_text(encoding="utf-8")
        self.assertNotIn("OPENAI_API_KEY",text)
        self.assertNotIn("ANTHROPIC_API_KEY",text)
        self.assertNotIn("GOOGLE_API_KEY",text)

    def test_force_push_not_present(self):
        text=WF.read_text(encoding="utf-8")
        self.assertNotIn("--force",text)
        self.assertNotIn("force-with-lease",text)

    def test_production_read_only_is_required(self):
        text=WF.read_text(encoding="utf-8")
        self.assertIn('= "READ_ONLY"',text)

if __name__=="__main__":
    unittest.main()
