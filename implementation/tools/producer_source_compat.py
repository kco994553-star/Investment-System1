"""Exact source acceptance for approved CDR-004 integration; no scoring code executes."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

MODELS = "investment_system/contracts/models.py"
CANONICAL_SOURCE_COMMIT = "b8e39a2196a6d7794a04a0cd5393c68329e126ca"
CANONICAL_SOURCE_PREFIX = "implementation/src/"
# Original bytes retained; CDR-004 adopts exactly Track C 2137883, not arbitrary schema changes.
MODELS_PRE_ADOPTION_SHA256 = "5313bbd41224da718580ba529f622d091787d33d62d70c6d5a6bc3073d6ac506"
MODELS_C28_ADOPTED_SHA256 = "fa386626f19fcdd0dfc97fd7d9b56ba1c56493ae9e1cfaecac42a5214297ed92"
MODELS_PRE_ADOPTION_AST_SHA256 = "c56ebb2c050053107ae21c434e90710be1ee5a8c57413c5b57ac8b378a01568e"
LINEAGE_DECLARATIONS = {
    "available_at": "available_at: Optional[datetime] = None",
    "data_stamp_refs": "data_stamp_refs: tuple[str, ...] = ()",
    "source_vintages": "source_vintages: tuple[tuple[str, str], ...] = ()",
    "input_hash": "input_hash: Optional[str] = None",
}


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _ast_shape(node):
    # Empty Python 3.12 type_params has the same meaning as its absence in Python 3.11.
    if isinstance(node, ast.AST):
        return {"kind": type(node).__name__, "fields": {name: _ast_shape(value)
                for name, value in ast.iter_fields(node) if not (name == "type_params" and not value)}}
    if isinstance(node, list):
        return [_ast_shape(value) for value in node]
    if node is Ellipsis:
        return {"constant": "ELLIPSIS"}
    return node


def models_state(body: bytes) -> dict:
    """Accept exact old/adopted bytes and independently preserve the complete prior AST."""
    digest = sha256(body)
    state = {MODELS_PRE_ADOPTION_SHA256: "PRE_ADOPTION", MODELS_C28_ADOPTED_SHA256: "C28_ADOPTED"}.get(digest)
    try:
        tree = ast.parse(body)
        fields = {}
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name in {"TechnicalSnapshot", "MacroSnapshot"}):
            additions = [node for node in cls.body if isinstance(node, ast.AnnAssign)
                         and isinstance(node.target, ast.Name) and node.target.id in LINEAGE_DECLARATIONS]
            fields[cls.name] = [node.target.id for node in additions]
            if state == "C28_ADOPTED":
                if fields[cls.name] != list(LINEAGE_DECLARATIONS):
                    return {"status": "FAIL", "sha256": digest, "reason": "partial or reordered lineage fields"}
                for node in additions:
                    expected = ast.parse(LINEAGE_DECLARATIONS[node.target.id]).body[0]
                    if ast.dump(node, include_attributes=False) != ast.dump(expected, include_attributes=False):
                        return {"status": "FAIL", "sha256": digest, "reason": "unapproved annotation or default"}
                cls.body = [node for node in cls.body if node not in additions]
            elif additions:
                return {"status": "FAIL", "sha256": digest, "reason": "unapproved lineage state"}
        preserved = sha256(json.dumps(_ast_shape(tree), sort_keys=True, separators=(",", ":")).encode()) == MODELS_PRE_ADOPTION_AST_SHA256
        ok = state is not None and preserved and set(fields) == {"TechnicalSnapshot", "MacroSnapshot"}
        return {"status": "PASS" if ok else "FAIL", "state": state, "sha256": digest,
                "pre_existing_AST_preserved": preserved, "lineage_fields": fields,
                "authority": "CDR-004; Track C 21378835883c5a9740143899c70d75d6405aa55a"}
    except (SyntaxError, ValueError, UnicodeDecodeError, TypeError) as error:
        return {"status": "FAIL", "sha256": digest, "reason": str(error)}


def compare_shared_sources(own_src: Path, infra_src: Path, shared: tuple[str, ...]) -> dict:
    same_tree = own_src.resolve() == infra_src.resolve()
    files = {}
    for rel in shared:
        paths = [own_src / rel, infra_src / rel]
        bodies = [p.read_bytes() if p.is_file() else None for p in paths]
        detail = {"own": sha256(bodies[0]) if bodies[0] is not None else None,
                  "infra": sha256(bodies[1]) if bodies[1] is not None else None}
        if rel == MODELS and all(body is not None for body in bodies):
            states = [models_state(body) for body in bodies]
            ok = all(state["status"] == "PASS" for state in states)
            detail.update({"mode": "EXACT_CDR004_SCHEMA_ACCEPTANCE", "states": states})
        elif same_tree and rel != MODELS:
            # Pair equality is vacuous when both paths resolve to one source
            # tree. Compare with the fixed canonical Git object instead; never
            # use HEAD, a moving ref, caller source bytes or an absent fallback.
            baseline, error = _canonical_source(rel)
            ok = baseline is not None and all(body is not None and body == baseline for body in bodies)
            detail.update({"mode": "EXACT_CANONICAL_SOURCE_PROTECTION",
                           "baseline_commit": CANONICAL_SOURCE_COMMIT,
                           "baseline_path": CANONICAL_SOURCE_PREFIX + rel,
                           "baseline_sha256": sha256(baseline) if baseline is not None else None,
                           "baseline_available": baseline is not None})
            if error is not None:
                detail["baseline_error"] = error
        else:
            ok = all(body is not None for body in bodies) and bodies[0] == bodies[1]
            detail["mode"] = "BYTE_IDENTICAL"
        detail["status"] = "PASS" if ok else "FAIL"
        files[rel] = detail
    return {"status": "PASS" if all(v["status"] == "PASS" for v in files.values()) else "FAIL", "files": files}


def _canonical_source(rel: str) -> tuple[bytes | None, str | None]:
    """Local immutable baseline lookup from this helper's repository, fail closed."""
    try:
        proc = subprocess.run(["git", "--no-replace-objects", "-C", str(Path(__file__).resolve().parents[1]), "show",
                               CANONICAL_SOURCE_COMMIT + ":" + CANONICAL_SOURCE_PREFIX + rel],
                              capture_output=True)
    except OSError as error:
        return None, "canonical Git baseline unavailable: " + type(error).__name__
    if proc.returncode != 0:
        return None, "canonical Git object or source path unavailable"
    return proc.stdout, None


def boundary_pin(path: Path) -> dict:
    """Read the immutable historical pin without importing either source tree."""
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INFRA_PIN" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"INFRA_PIN missing: {path}")


def dependency_reference(infra_src: Path, own_src: Path, historical_pin: dict) -> dict:
    infra_src, own_src = infra_src.resolve(), own_src.resolve()
    def git(*args):
        proc = subprocess.run(["git", "-C", str(infra_src), *args], text=True, capture_output=True)
        return proc.stdout.strip() if proc.returncode == 0 else None
    manifest = {p.relative_to(infra_src).as_posix(): sha256(p.read_bytes())
                for p in sorted(infra_src.rglob("*.py")) if "__pycache__" not in p.parts}
    head = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", str(infra_src))
    if infra_src == own_src:
        mode = "INTEGRATED_SAME_TREE"
    elif head == historical_pin["commit"] and dirty == "":
        mode = "PINNED_CHECKOUT"
    elif head is not None:
        mode = "EXTERNAL_CHECKOUT"
    else:
        mode = "UNVERSIONED_SOURCE"
    return {"mode": mode, "path": str(infra_src), "commit": head, "git_tree": git("rev-parse", "HEAD^{tree}"),
            "source_dirty": None if dirty is None else bool(dirty), "source_manifest": manifest,
            "source_manifest_sha256": sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "historical_pin_is_actual": mode == "PINNED_CHECKOUT"}
