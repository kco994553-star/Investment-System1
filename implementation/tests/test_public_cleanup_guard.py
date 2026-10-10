"""Real Git state tests using an independent synthetic preimage, never legacy values."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

GUARD_PATH = Path(__file__).resolve().parents[1] / "tools/autonomy_gate_a_guard.py"
spec = importlib.util.spec_from_file_location("cleanup_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
READINESS = "implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json"
RECEIPT = "implementation/docs/public_price_boundary/CLEANUP_AUTHORITY.json"


class Repository:
    def __init__(self, root, monkeypatch):
        self.root = root
        self.cfg = {"immutable_exact_paths": [READINESS, "other.json"], "append_only_exact_paths": [], "append_only_prefixes": []}
        self.original = b"Independent synthetic readiness surrogate; no market inputs.\n"
        self.authority = b'{"authority":"independent synthetic guard test only"}\n'
        monkeypatch.setattr(guard, "REPO_ROOT", root)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Synthetic Guard Test")
        self.git("config", "user.email", "guard-test@example.invalid")
        self.write(READINESS, self.original)
        self.write("other.json", b"independent protected evidence\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        blob = self.git("rev-parse", "HEAD:" + READINESS).strip()
        for key, value in {
            "_CLEANUP_READINESS_BLOB_SHA1": blob,
            "_CLEANUP_AUTHORITY_COMMIT": self.base,
            "_CLEANUP_AUTHORITY_PINS": {},
            "_CLEANUP_READINESS_SHA256": hashlib.sha256(self.original).hexdigest(),
            "_CLEANUP_READINESS_BYTES": len(self.original),
            "_CLEANUP_RECEIPT_SHA256": hashlib.sha256(self.authority).hexdigest(),
        }.items():
            monkeypatch.setattr(guard, key, value, raising=False)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def write(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "Synthetic cleanup state")

    def clean(self):
        (self.root / READINESS).unlink()
        self.write(RECEIPT, self.authority)

    def violations(self, base=None):
        return guard.protected_repository_violations(base or self.base, self.git("rev-parse", "HEAD").strip(), self.cfg)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    return Repository(tmp_path, monkeypatch)


@pytest.mark.parametrize("stage", ["commit", "index", "worktree"])
def test_exact_authorized_transition_passes_at_each_state(repo, stage):
    # Receipt must be tracked; readiness may then be removed in any inspected state.
    repo.clean()
    if stage == "commit":
        repo.commit()
    elif stage == "index":
        repo.git("add", "-A")
    else:
        repo.git("add", "--", RECEIPT)
    assert not repo.violations()


@pytest.mark.parametrize("bad", ["missing", "arbitrary", "wrong_metadata", "extra_authority", "duplicate_key", "executable", "symlink"])
def test_unpinned_receipt_never_authorizes_deletion(repo, bad):
    repo.clean()
    p = repo.root / RECEIPT
    if bad == "missing":
        p.unlink()
    elif bad == "executable":
        p.chmod(0o755)
    elif bad == "symlink":
        p.unlink()
        p.symlink_to("../../../../other.json")
    elif bad == "duplicate_key":
        repo.write(RECEIPT, b'{"authority":"invalid","authority":"independent synthetic guard test only"}\n')
    else:
        repo.write(RECEIPT, json.dumps({"claim": bad}).encode())
    repo.commit()
    assert repo.violations()


def test_wrong_readiness_preimage_cannot_use_cleanup_authority(repo):
    repo.write(READINESS, b"a different synthetic preimage\n")
    repo.commit()
    repo.base = repo.git("rev-parse", "HEAD").strip()
    repo.clean()
    repo.commit()
    assert repo.violations()


def test_other_protected_deletion_is_still_rejected(repo):
    repo.clean()
    (repo.root / "other.json").unlink()
    repo.commit()
    assert repo.violations()


@pytest.mark.parametrize("target", [READINESS, RECEIPT])
def test_rewrite_then_restore_cannot_hide_in_parent_history(repo, target):
    if target == RECEIPT:
        repo.clean()
        repo.commit()
    original = (repo.root / target).read_bytes()
    repo.write(target, b"unapproved intervening rewrite\n")
    repo.commit()
    repo.write(target, original)
    repo.commit()
    if target == READINESS:
        repo.clean()
        repo.commit()
    assert repo.violations()


@pytest.mark.parametrize("kind", ["regular", "directory", "symlink", "dangling_symlink", "parent_symlink"])
def test_deleted_readiness_cannot_be_reintroduced_untracked(repo, kind):
    repo.clean()
    repo.commit()
    repo.base = repo.git("rev-parse", "HEAD").strip()
    p = repo.root / READINESS
    if kind == "regular":
        p.write_bytes(repo.original)
    elif kind == "directory":
        p.mkdir()
    elif kind in {"symlink", "dangling_symlink"}:
        p.symlink_to("missing" if kind == "dangling_symlink" else repo.root / "other.json")
    else:
        p.parent.rmdir()
        p.parent.symlink_to(repo.root / "missing-directory", target_is_directory=True)
    assert repo.violations()


def test_readiness_rename_is_not_an_authorized_deletion(repo):
    repo.git("mv", READINESS, "relocated.json")
    repo.write(RECEIPT, repo.authority)
    repo.commit()
    assert repo.violations()


@pytest.mark.parametrize("stage", ["index", "worktree"])
def test_receipt_tampering_after_cleanup_is_rejected(repo, stage):
    repo.clean()
    repo.commit()
    repo.base = repo.git("rev-parse", "HEAD").strip()
    repo.write(RECEIPT, b"changed authority\n")
    if stage == "index":
        repo.git("add", "--", RECEIPT)
    assert repo.violations()


def test_receipt_added_only_at_final_head_cannot_authorize_an_earlier_deletion(repo):
    (repo.root / READINESS).unlink()
    repo.commit()
    repo.write(RECEIPT, repo.authority)
    repo.commit()
    assert repo.violations()


def test_delete_restore_delete_is_not_a_second_authorized_transition(repo):
    repo.clean()
    repo.commit()
    repo.write(READINESS, repo.original)
    repo.commit()
    (repo.root / READINESS).unlink()
    repo.commit()
    assert repo.violations()


@pytest.mark.parametrize("operation", ["delete", "mutate"])
def test_steady_absent_state_requires_receipt_even_when_base_equals_head(repo, operation):
    repo.clean()
    repo.commit()
    if operation == "delete":
        (repo.root / RECEIPT).unlink()
    else:
        repo.write(RECEIPT, b"wrong authority\n")
    repo.commit()
    assert repo.violations(base=repo.git("rev-parse", "HEAD").strip())


def test_staged_receipt_mutation_cannot_hide_behind_restored_worktree(repo):
    repo.clean()
    repo.commit()
    repo.write(RECEIPT, b"wrong staged authority\n")
    repo.git("add", "--", RECEIPT)
    repo.write(RECEIPT, repo.authority)
    assert repo.violations()


def test_missing_historical_authority_cannot_be_replaced_by_receipt_claim(repo, monkeypatch):
    monkeypatch.setattr(guard, "_CLEANUP_AUTHORITY_COMMIT", "f" * 40)
    repo.clean()
    repo.commit()
    assert repo.violations()


def test_side_parent_receipt_rewrite_is_checked_even_after_restore(repo):
    repo.clean()
    repo.commit()
    repo.git("checkout", "-qb", "side")
    repo.write(RECEIPT, b"unauthorized side-parent authority\n")
    repo.commit()
    repo.write(RECEIPT, repo.authority)
    repo.commit()
    repo.git("checkout", "-q", "main")
    repo.write("public.txt", b"independent public metadata\n")
    repo.commit()
    repo.git("merge", "--no-ff", "-qm", "Synthetic merge", "side")
    assert repo.violations()


def test_production_pins_are_bound_to_canonical_metadata_only_receipt():
    # Independent assertions prevent weakening the production pins to fit fixtures.
    import importlib.util
    fresh_spec = importlib.util.spec_from_file_location("production_cleanup_guard", GUARD_PATH)
    production = importlib.util.module_from_spec(fresh_spec)
    fresh_spec.loader.exec_module(production)
    assert production._CLEANUP_AUTHORITY_COMMIT == "ee039041ae7f5cb94e6a127930c7e43effb811ec"
    assert production._CLEANUP_READINESS_BLOB_SHA1 == "d369dd3af1b7f10ccf5233cf9e04694bc7fad165"
    assert production._CLEANUP_READINESS_SHA256 == "5789dc3d3b10dd29d466931bf9c6f459d2569d15071f80dfd50236d0b0cef006"
    assert production._CLEANUP_READINESS_BYTES == 8781
    data = (GUARD_PATH.parents[2] / RECEIPT).read_bytes()
    assert hashlib.sha256(data).hexdigest() == production._CLEANUP_RECEIPT_SHA256
    receipt = json.loads(data)
    assert receipt["authority_source_commit"] == production._CLEANUP_AUTHORITY_COMMIT
    assert {item["path"]: item["git_blob_sha1"] for item in receipt["authority_sources"]} == production._CLEANUP_AUTHORITY_PINS
