#!/usr/bin/env python3
"""Fail-closed repository guard for Autonomous Execution SSoT v1.1 Gate A.

This guard does not grant autonomy by itself. It enforces:
- immutable Frozen artifacts cannot be modified/deleted/renamed;
- append-only records cannot rewrite or delete existing bytes;
- AUTONOMY_MODE is a single explicit state;
- operating values stay within the adopted CDR-024 configuration.

HG-02 still requires GitHub-side branch/ruleset enforcement.
"""

from __future__ import annotations

import argparse
import stat
import re
import os
import errno
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = IMPLEMENTATION_ROOT / "docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json"


class GuardError(RuntimeError):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    expected = {"cycle_max_tasks": 5, "lease_ttl_seconds": 7200, "repair_round_cap": 3}
    if cfg.get("operating_values") != expected:
        raise GuardError(f"operating values drift: {cfg.get('operating_values')!r}")
    return cfg


def parse_name_status(raw: str) -> list[tuple[str, list[str]]]:
    """Accept Git's unquoted NUL format and the legacy unit-test text format."""
    out: list[tuple[str, list[str]]] = []
    if "\0" in raw:
        fields = raw.split("\0")
        if fields.pop() != "":
            raise GuardError("incomplete protected-content diff metadata")
        index = 0
        while index < len(fields):
            status = fields[index]
            count = 2 if status.startswith(("R", "C")) else 1
            paths = fields[index + 1:index + 1 + count]
            if not re.fullmatch(r"[ACDMRTUXB][0-9]*", status) or len(paths) != count or not all(paths):
                raise GuardError("invalid protected-content diff metadata")
            out.append((status, paths))
            index += count + 1
        return out
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise GuardError("invalid protected-content diff metadata")
        out.append((parts[0], parts[1:]))
    return out


def _touches(path: str, cfg: dict) -> bool:
    return (
        path in cfg["immutable_exact_paths"]
        or path in cfg["append_only_exact_paths"]
        or any(path.startswith(prefix) for prefix in cfg["append_only_prefixes"])
    )


def classify_diff(records: list[tuple[str, list[str]]], cfg: dict, append_verifier=None) -> list[str]:
    """An M may append only to an exact log with independent content proof.

    Without a verifier this remains conservative. Evidence-directory entries
    and immutable paths never use the log append exception.
    """
    violations: list[str] = []
    immutable = set(cfg["immutable_exact_paths"])
    append_files = set(cfg["append_only_exact_paths"])
    prefixes = tuple(cfg["append_only_prefixes"])
    for status, paths in records:
        if not status or not paths:
            raise GuardError("invalid protected-content diff metadata")
        code = status[0]
        old_path, new_path = paths[0], paths[-1]
        if old_path in immutable or new_path in immutable:
            if code != "A":
                violations.append(f"immutable path changed: {status} {paths}")
            continue
        evidence_hit = old_path.startswith(prefixes) or new_path.startswith(prefixes)
        append_hit = old_path in append_files or new_path in append_files or evidence_hit
        if append_hit and code != "A":
            proven_append = (
                code == "M" and old_path == new_path and old_path in append_files
                and not evidence_hit and append_verifier is not None
                and append_verifier(old_path)
            )
            if not proven_append:
                violations.append(f"append-only existing content changed: {status} {paths}")
    return violations


def _guard_git_bytes(args: list[str]) -> bytes:
    proc = subprocess.run(
        ["git", "--no-replace-objects", *args], cwd=REPO_ROOT,
        check=False, capture_output=True,
    )
    if proc.returncode:
        raise GuardError("protected-content verification could not read repository state")
    return proc.stdout


def _reject_grafted_history() -> None:
    """Grafts can conceal committed states despite --no-replace-objects."""
    if "GIT_GRAFT_FILE" in os.environ:
        raise GuardError("protected-content verification does not support grafted history")
    graft_path = _guard_git_bytes([
        "rev-parse", "--path-format=absolute", "--git-path", "info/grafts",
    ]).removesuffix(b"\n")
    if not graft_path:
        raise GuardError("protected-content verification could not locate history metadata")
    try:
        os.lstat(os.fsdecode(graft_path))
    except FileNotFoundError:
        return
    except OSError:
        raise GuardError("protected-content verification could not inspect history metadata") from None
    raise GuardError("protected-content verification does not support grafted history")


def resolve_comparison(base: str) -> tuple[str, str]:
    """Freeze the same unique merge base and HEAD used by the reported diff."""
    _reject_grafted_history()
    def commit(ref):
        oid = _guard_git_bytes(["rev-parse", "--verify", "--end-of-options", ref + "^{commit}"]).strip()
        if not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise GuardError("invalid protected-content comparison commit")
        return oid.decode("ascii")
    base_commit, head = commit(base), commit("HEAD")
    bases = _guard_git_bytes(["merge-base", "--all", base_commit, head]).splitlines()
    if len(bases) != 1 or not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", bases[0]):
        raise GuardError("protected-content verification requires one unambiguous merge base")
    if _guard_git_bytes(["rev-parse", "--is-shallow-repository"]).strip() != b"false":
        raise GuardError("protected-content verification requires complete repository history")
    return bases[0].decode("ascii"), head


def git_name_status(base: str, *, head: str | None = None) -> str:
    if head is None:
        base, head = resolve_comparison(base)
    return _guard_git_bytes([
        "diff", "--name-status", "-z", "--no-renames", "--no-ext-diff",
        "--no-textconv", "--ignore-submodules=none", base, head, "--",
    ]).decode("utf-8", "surrogateescape")


def _safe_git_path(raw_path: bytes) -> str:
    path = raw_path.decode("utf-8", "surrogateescape")
    if not path or path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")):
        raise GuardError("invalid protected-content repository path")
    return path


def _protected_tree(tree: str, cfg: dict) -> dict:
    state = {}
    for entry in _guard_git_bytes(["ls-tree", "-r", "--full-tree", "-z", tree]).split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, oid = metadata.split()
        except ValueError:
            raise GuardError("invalid protected-content tree metadata") from None
        path = _safe_git_path(raw_path)
        if _touches(path, cfg):
            state[path] = (mode.decode("ascii"), kind.decode("ascii"), oid.decode("ascii"))
    return state


def _protected_index(cfg: dict) -> dict:
    state = {}
    for entry in _guard_git_bytes(["ls-files", "--stage", "-z"]).split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, oid, stage = metadata.split()
        except ValueError:
            raise GuardError("invalid protected-content index metadata") from None
        path = _safe_git_path(raw_path)
        if _touches(path, cfg):
            if stage != b"0" or path in state:
                raise GuardError("protected-content verification requires a resolved index")
            state[path] = (mode.decode("ascii"), "commit" if mode == b"160000" else "blob", oid.decode("ascii"))
    return state


def _protected_worktree_entry(path: str):
    """Read a protected tracked file without following any symlink component."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise GuardError("protected-content verification requires no-follow filesystem support")
    directory = file_fd = None
    try:
        directory = os.open(REPO_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parts = path.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            return None
        with os.fdopen(file_fd, "rb") as file:
            file_fd = None
            content = file.read()
            after = os.fstat(file.fileno())
        stable_fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
            raise GuardError("protected-content file changed during verification")
        mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        return mode, "blob", content
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.ELOOP, errno.ENOTDIR}:
            return None
        raise GuardError("protected-content verification could not read a tracked file") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory is not None:
            os.close(directory)


def _regular_entry(entry) -> bool:
    return entry is not None and entry[0] in {"100644", "100755"} and entry[1] == "blob"


def _log_text(content: bytes) -> bool:
    if b"\0" in content:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _protected_transition(before: dict, after: dict, cfg: dict, blob_cache: dict) -> list[str]:
    def content(entry):
        value = entry[2]
        if isinstance(value, bytes):
            return value
        if value not in blob_cache:
            blob_cache[value] = _guard_git_bytes(["cat-file", "blob", value])
        return blob_cache[value]

    def append_proof(path):
        old, new = before[path], after[path]
        if not _regular_entry(old) or not _regular_entry(new) or old[:2] != new[:2]:
            return False
        old_bytes, new_bytes = content(old), content(new)
        return _log_text(old_bytes) and _log_text(new_bytes) and new_bytes.startswith(old_bytes)

    records, invalid = [], []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        if old is None:
            code = "A"
            if not _regular_entry(new) or (
                path in cfg["append_only_exact_paths"] and not _log_text(content(new))
            ):
                invalid.append("protected repository addition requires a regular artifact of the configured type")
        elif new is None:
            code = "D"
        elif old[:2] != new[:2] or not _regular_entry(old) or not _regular_entry(new):
            code = "T"
        elif content(old) == content(new):
            continue
        else:
            code = "M"
        records.append((code, [path]))
    return invalid + classify_diff(records, cfg, append_proof)


def protected_repository_violations(comparison: str, head: str, cfg: dict) -> list[str]:
    """Verify every committed parent edge, final tree, index, and tracked files."""
    trees, blobs = {}, {}
    def tree(oid):
        if oid not in trees:
            trees[oid] = _protected_tree(oid, cfg)
        return trees[oid]
    violations = _protected_transition(tree(comparison), tree(head), cfg, blobs)
    history = _guard_git_bytes([
        "rev-list", "--reverse", "--topo-order", "--parents", f"{comparison}..{head}", "--",
    ])
    for line in history.splitlines():
        commits = line.decode("ascii").split()
        if not commits or not all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid) for oid in commits):
            raise GuardError("invalid protected-content history metadata")
        commit, parents = commits[0], commits[1:]
        for parent in parents:
            violations.extend(_protected_transition(tree(parent), tree(commit), cfg, blobs))
        if not parents:
            violations.extend(_protected_transition({}, tree(commit), cfg, blobs))
    index = _protected_index(cfg)
    violations.extend(_protected_transition(tree(head), index, cfg, blobs))
    worktree = {}
    for path in tree(head).keys() | index.keys():
        entry = _protected_worktree_entry(path)
        if entry is not None:
            worktree[path] = entry
    violations.extend(_protected_transition(index, worktree, cfg, blobs))
    return list(dict.fromkeys(violations))


def validate_mode(cfg: dict) -> str:
    p = REPO_ROOT / cfg["autonomy_mode_file"]
    mode = p.read_text(encoding="utf-8").strip()
    if mode not in cfg["allowed_modes"]:
        raise GuardError(f"invalid AUTONOMY_MODE={mode!r}")
    return mode


def cmd_diff(base: str) -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    comparison, head = resolve_comparison(base)
    records = parse_name_status(git_name_status(comparison, head=head))
    violations = protected_repository_violations(comparison, head, cfg)
    print(json.dumps({
        "mode": mode,
        "records": len(records),
        "violations": violations,
        "gate_a_repository_guard": "PASS" if not violations else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 1 if violations else 0


def cmd_mode() -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    print(mode)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--base", required=True)
    sub.add_parser("mode")
    args = parser.parse_args()
    try:
        if args.cmd == "diff":
            return cmd_diff(args.base)
        return cmd_mode()
    except (GuardError, OSError, json.JSONDecodeError) as exc:
        print(f"AUTONOMY_GUARD_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
