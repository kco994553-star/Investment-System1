"""Verify the transferable SA01/SA02 patch in a disposable source copy.

Reuses the prior RED evidence and negative tests; no original RED replay.
Only reviewed pinned modules execute, with package initializers bypassed.
No owner worktree, database, provider, credential or deployment is touched.
"""
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PIN = "78a51462f89eac8e34647cddc4e53ed97e831178"
SOURCE = "implementation/src/investment_system/platform/contracts.py"
BASE_HASH = "b13686d8ce134ccb61ef78c51d178597404e7a3401e7b22240dcc47c01d0aa7b"
PRIOR = HERE.parent / "storage_auth_2026-10-05"


def main():
    spec = importlib.util.spec_from_file_location("prior_platform_probes", PRIOR / "owner_probes.py")
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    original = prior.git("show", f"{PIN}:{SOURCE}")
    assert hashlib.sha256(original).hexdigest() == BASE_HASH
    patch = HERE / "SA01_SA02_candidate.patch"
    with tempfile.TemporaryDirectory(prefix="platform-candidate-") as directory:
        target = Path(directory) / SOURCE
        target.parent.mkdir(parents=True)
        target.write_bytes(original)
        for args in (("--check",), ()):
            subprocess.run(["git", "apply", *args, str(patch)], cwd=directory,
                           check=True, capture_output=True, text=True)
        patched = target.read_bytes()

    for package in ("investment_system", "investment_system.personal", "investment_system.platform", "tests"):
        module = types.ModuleType(package)
        module.__path__ = []
        sys.modules[package] = module
    manifest = []
    for name, path in prior.SOURCE_MODULES:
        if path == SOURCE:
            module = types.ModuleType(name)
            module.__file__ = f"candidate:{PIN}:{SOURCE}"
            module.__package__ = name.rpartition(".")[0]
            sys.modules[name] = module
            exec(compile(patched, module.__file__, "exec"), module.__dict__)
        else:
            module = prior.load(name, path, manifest)
        parent, _, attr = name.rpartition(".")
        setattr(sys.modules[parent], attr, module)
    c = sys.modules["investment_system.platform.contracts"]
    shim = prior.load("owner_mini_pytest", "implementation/tools/mini_pytest.py", manifest)
    shim._install_shim()
    tests = prior.load("tests.test_product_platform_contracts", "implementation/tests/test_product_platform_contracts.py", manifest)

    checks = []
    for name, test in inspect.getmembers(tests, inspect.isfunction):
        if name.startswith("test_") and test.__module__ == tests.__name__:
            prior.record_check(checks, "affected_owner_" + name, test)
    assert len(checks) == 9
    prior.record_check(checks, "SA01_actual_patched_digest_identity",
                       lambda: prior.test_direct_digest_case_equivalence(c, lambda ref: ref))
    prior.record_check(checks, "SA02_actual_patched_inherited_write_and_masked_read_denial",
                       lambda: prior.test_inherited_callable_trade_denied(
                           c, lambda interface: prior.original_interface_validator(c, interface)))

    def frozen_ref():
        ref = c.SourceRecordRef("t1", "conn", "r1", "v1", "A" * 64)
        assert ref.payload_sha256 == "a" * 64
        assert hash(ref) == hash(prior.source(c).ref)
        return prior.rejects(FrozenInstanceError, lambda: setattr(ref, "payload_sha256", "b" * 64))

    prior.record_check(checks, "SA01_canonical_ref_hash_and_frozen_after_construction", frozen_ref)
    counts = prior.counts(checks)
    result = {
        "schema": "platform-transferable-candidate-verification-v1",
        "owner_pin": PIN, "source_path": SOURCE,
        "base_sha256": BASE_HASH, "candidate_sha256": hashlib.sha256(patched).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version.split()[0], "patch_application": "PASS disposable copy; git apply --check then git apply",
        "checks": checks, "counts": counts, "dependency_manifest": manifest,
        "original_RED": "REUSED prior source-pinned receipt; NOT_RERUN",
        "prior_receipt_sha256": hashlib.sha256((PRIOR / "owner_probes.json").read_bytes()).hexdigest(),
        "owner_source_mutated": False, "owner_adopted": False,
        "repository_regression_rerun": False, "production_verified": False,
        "scope": "candidate source bytes only; mini_pytest shim, not pytest; no real auth/provider/DB/network",
    }
    output = json.dumps(result, indent=2, default=str, sort_keys=True) + "\n"
    (HERE / "candidate_verification.json").write_text(output)
    print(output, end="")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
