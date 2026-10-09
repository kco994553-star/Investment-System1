"""Run the dependency-free mocked Worker suite in the existing native CI flow."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PrivateHistoryWorkerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed for Worker mock tests")
    def test_owner_history_worker_mock_suite(self):
        result = subprocess.run(
            [shutil.which("node"), "--test", "worker/tests/worker.test.mjs",
             "tools/private_history_node_test.js", "tools/private_history_contract_test.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, "Mocked Worker suite failed:\n" + result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"(?:#|ℹ) fail 0\b")
        self.assertNotRegex(result.stdout, r"(?:#|ℹ) pass 0\b")


if __name__ == "__main__":
    unittest.main()
