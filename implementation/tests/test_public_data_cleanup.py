"""GSQ-010 finite HEAD cleanup and metadata-only custody contracts."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "implementation/docs/public_price_boundary"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_receipt(name):
    path = DOCS / name
    assert path.is_file(), "required metadata-only cleanup receipt is missing"
    return json.loads(path.read_text())


def test_all_140_authorized_preimages_have_complete_finite_actions():
    receipt = read_receipt("CLEANUP_TRANSITIONS.json")
    rows = receipt["transitions"]
    assert len(rows) == len({row["path"] for row in rows}) == 140
    metadata = [{key: row[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")} for row in rows]
    assert digest(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()) == "8f7ae790408f78f022275394e7f81ca239da500ca14513177b12eb9460aa1b67"
    counts = {"DELETE_FROM_HEAD": 0, "INDEPENDENT_SYNTHETIC_REPLACEMENT": 0}
    for row in rows:
        assert not row["path"].endswith(".md")
        path = ROOT / row["path"]
        counts[row["action"]] += 1
        if row["action"] == "DELETE_FROM_HEAD":
            assert not path.exists() and not path.is_symlink(), "authorized payload remains at HEAD"
            assert row["after"] is None
        else:
            data = path.read_bytes()
            assert digest(data) == row["after"]["sha256"]
            assert len(data) == row["after"]["bytes"]
            assert digest(data) != row["sha256"]
            assert row["lineage"] == "INDEPENDENT_TEST_GENERATION_NO_CAPTURED_INPUTS"
    assert counts == {"DELETE_FROM_HEAD": 138, "INDEPENDENT_SYNTHETIC_REPLACEMENT": 2}


def test_frozen_receipts_preserve_only_metadata_and_iso_dates():
    from datetime import date
    rows = read_receipt("FROZEN_RECEIPTS.json")["receipts"]
    actions = {row["path"]: row for row in read_receipt("CLEANUP_TRANSITIONS.json")["transitions"]}
    assert len(rows) == 3
    for row in rows:
        assert set(row) == {"receipt_id", "original_path", "as_of", "kind", "source_commit", "git_blob_sha1", "sha256", "bytes", "source_evidence_path", "private_archive", "history"}
        assert date.fromisoformat(row["as_of"]).isoformat() == row["as_of"]
        assert not (ROOT / row["original_path"]).exists()
        assert row["private_archive"] == "USER_SEPARATE_ACTION_NOT_PERFORMED"
        assert row["history"] == "RESIDUAL_PUBLIC_COPIES_ACCEPTED_NO_REWRITE"
        assert all(row[key] == actions[row["original_path"]][key] for key in ("bytes", "sha256", "git_blob_sha1"))


def test_five_uncertain_paths_retain_classification_and_bound_inputs():
    receipt = read_receipt("UNCERTAIN_CUSTODY.json")
    assert len(receipt["retained"]) == 5
    original_metadata = [{key: row[key] for key in ("path", "sha256", "bytes", "classification")} for row in receipt["retained"]]
    assert digest(json.dumps(original_metadata, sort_keys=True, separators=(",", ":")).encode()) == '6e13c96d6f3341cd96162af57852627b0d1fefd8d5d50230b09df5571eb68a16'
    for row in receipt["retained"]:
        assert row["classification"] == "UNCERTAIN"
        data = (ROOT / row["path"]).read_bytes()
        assert digest(data) == row["after_sha256"]
        if row["audit_id"] != "H46":
            assert row["sha256"] == row["a_sha256"] == row["after_sha256"]
        else:
            tree = ast.parse(data)
            functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
            for bound in row["unknown_origin_numeric_custody"]:
                node = functions[bound["function"]]
                literals = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]
                assert digest(json.dumps(literals).encode()) == bound["a_and_b_numeric_ast_sha256"]
                close = [ast.dump(value) for d in ast.walk(node) if isinstance(d, ast.Dict)
                         for key, value in zip(d.keys, d.values) if isinstance(key, ast.Constant) and key.value == "close"]
                assert digest(json.dumps(close).encode()) == bound["original_close_ast_sha256"] == bound["a_and_b_close_ast_sha256"]


def test_generated_session_quotes_have_independent_lineage(monkeypatch, tmp_path):
    from tests.synthetic_cleanup_inputs import session_inputs
    lineage = read_receipt("SYNTHETIC_LINEAGE.json")
    live, ids = session_inputs(monkeypatch, tmp_path)
    hashes = {digest(json.dumps(row["price"]).encode()) for row in live["prices"].values()}
    assert hashes.isdisjoint(lineage["removed_capture_price_scalar_sha256"])
    assert all(cid.startswith("cleanup_case_") for cid in ids)
    assert lineage["generation"] == "INDEPENDENT_AUTHORED_ARITHMETIC_NO_CAPTURED_INPUT_READS"
    assert lineage["fundamentals"] == "REUSE_EXISTING_EXPLICIT_SYNTHETIC_CATALOG"


def test_default_public_bundle_never_needs_deleted_frozen_payloads():
    from investment_system.product.web_mvp import repository_bundle
    from investment_system.producers.registry import FrozenUniverseProducer, ProduceRequest
    from datetime import datetime, timezone
    assert repository_bundle()["companies"] == []
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    snapshot = FrozenUniverseProducer().produce(ProduceRequest(now, now))
    assert snapshot["data_state"] == "NOT_AVAILABLE"


@pytest.mark.parametrize("consumer", json.loads((DOCS / "ARCHIVED_CONSUMERS.json").read_text())["consumers"])
def test_retired_archived_consumers_stop_before_any_payload_or_process_access(consumer, monkeypatch, capsys):
    import runpy
    import socket
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("retired consumer attempted an input, subprocess, or network access")

    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(ROOT / consumer["path"]), run_name="__main__")
    assert stopped.value.code == 2
    assert json.loads(capsys.readouterr().out) == {"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}
