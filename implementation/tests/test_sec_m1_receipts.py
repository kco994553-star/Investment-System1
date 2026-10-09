"""Immutable M1 generation storage and CLI: synthetic temporary I/O only."""
import hashlib
import importlib
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from .test_sec_m1_strict import OBSERVED, audit, encoded, fixture_inputs, request, strict


def receipts():
    name = "investment_system.ingestion.sec_m1_receipts"
    assert importlib.util.find_spec(name) is not None, "M1 immutable receipt store is missing"
    return importlib.import_module(name)


def cli():
    path = Path(__file__).resolve().parents[1] / "tools" / "sec_m1_audit.py"
    assert path.exists(), "M1 offline CLI is missing"
    spec = importlib.util.spec_from_file_location("sec_m1_audit_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def persisted(tmp_path):
    m, store = strict(), receipts()
    result = audit(m)
    receipt = store.persist_m1_generation(result, output_root=tmp_path / "runtime", imported_at=result.request.now)
    return m, store, result, receipt


def test_real_raw_store_and_idempotent_retry_preserve_first_receipt(tmp_path):
    m, s, result, first = persisted(tmp_path)
    root = tmp_path / "runtime"
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    retry = m.audit_sec_m1(replace(result.request, now=result.request.now + timedelta(days=1)),
                          result.artifacts[::-1], result.observation_receipts[::-1])
    second = s.persist_m1_generation(retry, output_root=root, imported_at=retry.request.now)
    assert first == second
    assert second["imported_at"] == result.request.now.isoformat()
    assert second["evaluated_at"] == result.request.now.isoformat()
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert s.read_m1_generation(root, first["generation_id"]) == first
    assert s.list_m1_generations(root) == (first["generation_id"],)
    assert len(first["generation_id"]) == 64


def test_new_body_and_cutoff_produce_distinct_generation_preserving_original(tmp_path):
    m, s, result, first = persisted(tmp_path)
    later = audit(m, as_of=OBSERVED + timedelta(days=2), observed=OBSERVED + timedelta(days=1),
                  rows=[{"accn": "0001193125-24-000001", "form": "10-K", "filed": "2024-02-22",
                         "end": "2023-12-31", "val": 99}])
    second = s.persist_m1_generation(later, output_root=tmp_path / "runtime", imported_at=later.request.now)
    assert second["generation_id"] != first["generation_id"]
    assert s.read_m1_generation(tmp_path / "runtime", first["generation_id"]) == first
    assert len(s.list_m1_generations(tmp_path / "runtime")) == 2


@pytest.mark.parametrize("target", ["blob", "manifest", "receipt", "marker"])
def test_corrupt_or_missing_generation_is_fail_closed(tmp_path, target):
    m, s, result, receipt = persisted(tmp_path)
    directory = tmp_path / "runtime" / "generations" / receipt["generation_id"]
    path = {"blob": directory / "raw" / "blobs" / receipt["raw_entries"][0]["artifact_id"],
            "manifest": directory / "raw" / "manifests" / (receipt["raw_entries"][0]["artifact_id"] + ".json"),
            "receipt": directory / "receipt.json", "marker": directory / "COMMITTED.json"}[target]
    if target in {"blob", "receipt"}:
        path.write_bytes(b"CORRUPTED_SECRET_SENTINEL")
    else:
        path.unlink()
    with pytest.raises(m.M1Error) as error:
        s.read_m1_generation(tmp_path / "runtime", receipt["generation_id"])
    assert "SECRET_SENTINEL" not in str(error.value)
    with pytest.raises(m.M1Error):
        s.persist_m1_generation(result, output_root=tmp_path / "runtime", imported_at=result.request.now)


def test_write_failure_before_atomic_directory_promotion_preserves_prior(tmp_path, monkeypatch):
    m, s, result, first = persisted(tmp_path)
    later = audit(m, as_of=OBSERVED + timedelta(hours=1))
    def crash(*args):
        raise OSError("SECRET_SENTINEL crash boundary")
    monkeypatch.setattr(s, "_promote_generation", crash)
    with pytest.raises(m.M1Error, match="^PERSISTENCE_FAILED$"):
        s.persist_m1_generation(later, output_root=tmp_path / "runtime", imported_at=later.request.now)
    assert s.read_m1_generation(tmp_path / "runtime", first["generation_id"]) == first
    assert s.list_m1_generations(tmp_path / "runtime") == (first["generation_id"],)


def test_concurrent_same_generation_returns_one_complete_receipt(tmp_path):
    m, s = strict(), receipts()
    result = audit(m)
    def write(_):
        return s.persist_m1_generation(result, output_root=tmp_path / "runtime", imported_at=result.request.now)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(write, range(4)))
    assert all(v == values[0] for v in values)
    assert s.list_m1_generations(tmp_path / "runtime") == (values[0]["generation_id"],)


@pytest.mark.parametrize("unsafe", ["symlink_root", "symlink_child", "repository", "pages", "escape"])
def test_runtime_paths_reject_unsafe_destinations_before_write(tmp_path, unsafe):
    m, s = strict(), receipts()
    result = audit(m)
    output = tmp_path / "runtime"
    if unsafe == "symlink_root":
        output.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    elif unsafe == "symlink_child":
        output.mkdir()
        (output / "generations").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    elif unsafe == "repository":
        (tmp_path / ".git").write_text("gitdir: somewhere")
    elif unsafe == "pages":
        output = tmp_path / "Pages" / "runtime"
    else:
        output = tmp_path / "safe" / ".." / "runtime"
    with pytest.raises(m.M1Error, match="^UNSAFE_RUNTIME_PATH$"):
        s.persist_m1_generation(result, output_root=output, imported_at=result.request.now)
    assert not (output / "generations").is_dir()


def test_revalidated_audit_cannot_write_forged_results(tmp_path):
    m, s = strict(), receipts()
    result = audit(m)
    forged = replace(result, facts=(replace(result.facts[0], value=999),))
    with pytest.raises(m.M1Error, match="^AUDIT_BINDING_MISMATCH$"):
        s.persist_m1_generation(forged, output_root=tmp_path / "runtime", imported_at=result.request.now)
    assert not (tmp_path / "runtime").exists()


def test_corrupt_receipt_cannot_authorize_modified_bindings(tmp_path):
    m, s, result, receipt = persisted(tmp_path)
    directory = tmp_path / "runtime" / "generations" / receipt["generation_id"]
    changed = dict(receipt, generation_id="0" * 64)
    body = encoded(changed)
    (directory / "receipt.json").write_bytes(body)
    (directory / "COMMITTED.json").write_bytes(encoded({"schema": "SEC_M1_COMMIT/1", "generation_id": receipt["generation_id"],
        "receipt_sha256": hashlib.sha256(body).hexdigest(), "receipt_bytes": len(body)}))
    with pytest.raises(m.M1Error):
        s.read_m1_generation(tmp_path / "runtime", receipt["generation_id"])


def manifest_for(tmp_path, m):
    artifacts, proofs = fixture_inputs(m)
    values = []
    for index, a in enumerate(artifacts):
        path = f"input-{index}.json"
        (tmp_path / path).write_bytes(a.body)
        values.append({"issuer_id": a.issuer_id, "cik": a.cik, "source_kind": a.source_kind,
                       "source_url": a.source_url, "path": path, "sha256": a.expected_sha256, "bytes": a.expected_bytes})
    observations = []
    for index, p in enumerate(proofs):
        path = f"observation-{index}.json"
        (tmp_path / path).write_bytes(p.body)
        observations.append({"path": path, "sha256": p.expected_sha256, "bytes": p.expected_bytes})
    manifest = {"schema": "SEC_M1_OFFLINE_IMPORT/1", "issuer_ids": ["nvda"], "synthetic": True,
                "artifacts": values, "observation_receipts": observations}
    target = tmp_path / "input-manifest.json"
    target.write_bytes(encoded(manifest))
    return target


def test_offline_cli_uses_real_files_and_prints_only_counts_codes_hashes(tmp_path, capsys, monkeypatch):
    m, command = strict(), cli()
    import urllib.request
    from investment_system.providers import sec_submissions, sec_companyfacts
    from investment_system.validation import historical
    def forbidden(*args, **kwargs):
        raise AssertionError("SECRET_SENTINEL forbidden entrypoint")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(sec_submissions, "fetch_submissions", forbidden)
    monkeypatch.setattr(sec_companyfacts, "try_fetch_companyfacts", forbidden)
    monkeypatch.setattr(historical, "run_as_of", forbidden)
    path = manifest_for(tmp_path, m)
    assert command.main(["--input-manifest", str(path), "--as-of", OBSERVED.isoformat(),
                         "--now", (OBSERVED + timedelta(days=3)).isoformat(), "--output", str(tmp_path / "runtime")]) == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["status"] == "PASS" and summary["fact_counts"] == {"ELIGIBLE": 1}
    assert len(summary["generation_id"]) == 64 and summary["synthetic"] is True
    assert all(summary[k] is False for k in ("full_pit_pass", "real_data_verified", "publication_approved"))
    assert not captured.err
    assert "123" not in captured.out.replace(summary["generation_id"], "")
    assert "SECRET_SENTINEL" not in captured.out and "score" not in captured.out and "price" not in captured.out


@pytest.mark.parametrize("failure", ["malformed", "sha", "exception", "unsafe_input", "unknown_option"])
def test_cli_failures_never_echo_payload_exception_or_paths(tmp_path, capsys, monkeypatch, failure):
    m, command = strict(), cli()
    path = manifest_for(tmp_path, m)
    if failure == "malformed":
        path.write_bytes(b'{SECRET_SENTINEL')
    elif failure in {"sha", "unsafe_input"}:
        data = json.loads(path.read_bytes())
        data["artifacts"][0]["sha256" if failure == "sha" else "path"] = "SECRET_SENTINEL"
        if failure == "unsafe_input": data["artifacts"][0]["path"] = "../SECRET_SENTINEL"
        path.write_bytes(encoded(data))
    elif failure == "exception":
        def crash(*args, **kwargs): raise RuntimeError("SECRET_SENTINEL")
        monkeypatch.setattr(command, "persist_m1_generation", crash)
    argv = ["--input-manifest", str(path), "--as-of", OBSERVED.isoformat(), "--now",
            (OBSERVED + timedelta(days=3)).isoformat(), "--output", str(tmp_path / "runtime")]
    if failure == "unknown_option": argv += ["--fetch", "SECRET_SENTINEL"]
    assert command.main(argv) == 2
    captured = capsys.readouterr()
    assert "SECRET_SENTINEL" not in captured.out + captured.err
    assert str(tmp_path) not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "FAIL"


def test_unexpected_file_and_symlink_blob_are_rejected(tmp_path):
    m, s, result, receipt = persisted(tmp_path)
    directory = tmp_path / "runtime" / "generations" / receipt["generation_id"]
    rogue = directory / "unexpected.json"
    rogue.write_bytes(b"{}")
    with pytest.raises(m.M1Error, match="^GENERATION_INTEGRITY_FAILED$"):
        s.read_m1_generation(tmp_path / "runtime", receipt["generation_id"])
    rogue.unlink()
    blob = directory / "raw" / "blobs" / receipt["raw_entries"][0]["artifact_id"]
    saved = tmp_path / "outside.json"
    saved.write_bytes(blob.read_bytes())
    blob.unlink()
    blob.symlink_to(saved)
    with pytest.raises(m.M1Error, match="^UNSAFE_RUNTIME_PATH$"):
        s.read_m1_generation(tmp_path / "runtime", receipt["generation_id"])


def test_missing_blob_is_rejected(tmp_path):
    m, s, result, receipt = persisted(tmp_path)
    blob = tmp_path / "runtime" / "generations" / receipt["generation_id"] / "raw" / "blobs" / receipt["raw_entries"][0]["artifact_id"]
    blob.unlink()
    with pytest.raises(m.M1Error, match="^GENERATION_INTEGRITY_FAILED$"):
        s.read_m1_generation(tmp_path / "runtime", receipt["generation_id"])


def test_changed_observation_proof_produces_distinct_generation(tmp_path):
    m, s, result, first = persisted(tmp_path)
    artifacts, proofs = fixture_inputs(m, observed=OBSERVED - timedelta(minutes=1))
    changed = m.audit_sec_m1(result.request, artifacts, proofs)
    second = s.persist_m1_generation(changed, output_root=tmp_path / "runtime", imported_at=changed.request.now)
    assert first["generation_id"] != second["generation_id"]
    assert s.read_m1_generation(tmp_path / "runtime", first["generation_id"]) == first


def test_staging_raw_manifest_failure_is_uncommitted(tmp_path, monkeypatch):
    m, s, result, first = persisted(tmp_path)
    from investment_system.ingestion.raw_store import RawDatasetStore
    original = RawDatasetStore.put
    def fail_after_put(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise OSError("SECRET_SENTINEL simulated write failure")
    monkeypatch.setattr(RawDatasetStore, "put", fail_after_put)
    changed = audit(m, as_of=OBSERVED + timedelta(hours=1))
    with pytest.raises(m.M1Error, match="^PERSISTENCE_FAILED$"):
        s.persist_m1_generation(changed, output_root=tmp_path / "runtime", imported_at=changed.request.now)
    assert s.list_m1_generations(tmp_path / "runtime") == (first["generation_id"],)


def test_parallel_distinct_generations_are_retained(tmp_path):
    m, s = strict(), receipts()
    values = [audit(m, as_of=OBSERVED + timedelta(hours=index)) for index in range(3)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        written = list(pool.map(lambda a: s.persist_m1_generation(a, output_root=tmp_path / "runtime", imported_at=a.request.now), values))
    assert set(s.list_m1_generations(tmp_path / "runtime")) == {r["generation_id"] for r in written}


def test_embedded_checkout_in_staging_rejected_before_raw_writes(tmp_path):
    m, s = strict(), receipts()
    root = tmp_path / "runtime"
    (root / ".staging").mkdir(parents=True)
    (root / ".staging" / ".git").write_text("gitdir: sentinel")
    result = audit(m)
    with pytest.raises(m.M1Error, match="^UNSAFE_RUNTIME_PATH$"):
        s.persist_m1_generation(result, output_root=root, imported_at=result.request.now)


def test_unsafe_receipt_fields_never_become_filesystem_paths():
    m, s = strict(), receipts()
    with pytest.raises(m.M1Error, match="^GENERATION_INTEGRITY_FAILED$"):
        s._expected_entry("INPUT", "nvda", "0001045810", "SEC_SUBMISSIONS/../../escape",
                          "https://data.sec.gov/submissions/CIK0001045810.json", "0" * 64, 1, None)


def test_tampered_commit_never_attempts_an_outside_raw_file_read(tmp_path, monkeypatch):
    m, s, result, receipt = persisted(tmp_path)
    root = tmp_path / "runtime"
    original = root / "generations" / receipt["generation_id"]
    changed = json.loads(encoded(receipt))
    entry = next(e for e in changed["raw_entries"] if e["role"] == "INPUT")
    spec = next(a for a in changed["semantic_binding"]["artifacts"]
                if (a["issuer_id"], a["source_kind"]) == (entry["issuer_id"], entry["input_kind"]))
    unsafe_kind = "SEC_FAKE/../../../../../../canary"
    spec["source_kind"] = unsafe_kind
    entry.update(input_kind=unsafe_kind, source_kind=unsafe_kind,
                 artifact_id=f"sec_m1_{unsafe_kind.lower()}_{entry['cik']}_{entry['sha256']}")
    changed["generation_id"] = m.sha256(m.canonical_json(changed["semantic_binding"]))
    directory = root / "generations" / changed["generation_id"]
    original.rename(directory)
    for subdirectory in ("blobs", "manifests"):
        (directory / "raw" / subdirectory / "sec_m1_sec_fake").mkdir()
    body = encoded(changed)
    (directory / "receipt.json").write_bytes(body)
    (directory / "COMMITTED.json").write_bytes(encoded({"schema": "SEC_M1_COMMIT/1",
        "generation_id": changed["generation_id"], "receipt_sha256": hashlib.sha256(body).hexdigest(), "receipt_bytes": len(body)}))
    outside_reads = []
    real_read = s._file
    def guarded_read(path, **kwargs):
        if not path.resolve().is_relative_to(directory):
            outside_reads.append(True)
            raise m.M1Error("GENERATION_INTEGRITY_FAILED")
        return real_read(path, **kwargs)
    monkeypatch.setattr(s, "_file", guarded_read)
    with pytest.raises(m.M1Error):
        s.read_m1_generation(root, changed["generation_id"])
    assert not outside_reads, "untrusted receipt must be rejected before constructing outside paths"


@pytest.mark.parametrize("invalid", ["issuer", "source", "sha", "size", "proof_size", "path", "clock"])
def test_cli_preflights_all_metadata_before_any_sibling_body_read(tmp_path, monkeypatch, capsys, invalid):
    m, command = strict(), cli()
    path = manifest_for(tmp_path, m)
    payload = json.loads(path.read_bytes())
    if invalid == "issuer": payload["issuer_ids"] = ["unknown"]
    elif invalid == "source": payload["artifacts"][1]["source_url"] += "?token=SECRET_SENTINEL"
    elif invalid == "sha": payload["artifacts"][1]["sha256"] = "SECRET_SENTINEL"
    elif invalid == "size": payload["artifacts"][1]["bytes"] = -1
    elif invalid == "proof_size": payload["observation_receipts"][1]["bytes"] = -1
    elif invalid == "path": payload["artifacts"][1]["path"] = "../SECRET_SENTINEL"
    path.write_bytes(encoded(payload))
    opened = []
    original = command._read_file
    def record_read(target, **kwargs):
        if Path(target) != path:
            opened.append(True)
        return original(target, **kwargs)
    monkeypatch.setattr(command, "_read_file", record_read)
    assert command.main(["--input-manifest", str(path), "--as-of",
                         "SECRET_SENTINEL" if invalid == "clock" else OBSERVED.isoformat(),
                         "--now", (OBSERVED + timedelta(days=3)).isoformat(), "--output", str(tmp_path / "runtime")]) == 2
    assert not opened, "invalid metadata must fail before any sibling bytes are read"
    assert not (tmp_path / "runtime").exists()
    assert "SECRET_SENTINEL" not in capsys.readouterr().out


def test_staging_symlink_swap_is_rejected_before_raw_store_initialization(tmp_path, monkeypatch):
    m, s = strict(), receipts()
    root = tmp_path / "runtime"
    target = tmp_path / "external-checkout"
    target.mkdir()
    (target / ".git").write_text("gitdir: sentinel")
    original = s.tempfile.mkdtemp
    def swapped_staging(*args, **kwargs):
        staging_parent = root / ".staging"
        staging_parent.rmdir()
        staging_parent.symlink_to(target, target_is_directory=True)
        return original(*args, **kwargs)
    monkeypatch.setattr(s.tempfile, "mkdtemp", swapped_staging)
    initialized = []
    actual_init = s.RawDatasetStore.__init__
    def record_init(self, *args, **kwargs):
        initialized.append(True)
        actual_init(self, *args, **kwargs)
    monkeypatch.setattr(s.RawDatasetStore, "__init__", record_init)
    result = audit(m)
    with pytest.raises(m.M1Error, match="^UNSAFE_RUNTIME_PATH$"):
        s.persist_m1_generation(result, output_root=root, imported_at=result.request.now)
    assert not initialized


def test_runtime_rejects_existing_cockpit_ancestor_regardless_of_directory_name(tmp_path):
    m, s = strict(), receipts()
    cockpit = tmp_path / "arbitrary-cockpit-name"
    cockpit.mkdir()
    (cockpit / "index.html").write_bytes(b"synthetic marker")
    (cockpit / "data.json").write_bytes(b"synthetic marker")
    result = audit(m)
    with pytest.raises(m.M1Error, match="^UNSAFE_RUNTIME_PATH$"):
        s.persist_m1_generation(result, output_root=cockpit / "runtime", imported_at=result.request.now)
    assert not (cockpit / "runtime").exists()


def test_retry_must_finish_directory_sync_after_successful_rename(tmp_path, monkeypatch):
    m, s = strict(), receipts()
    root = tmp_path / "runtime"
    result = audit(m)
    actual_sync = s._sync_directory
    def failed_generation_sync(path):
        if path == root / "generations":
            raise OSError("synthetic directory sync failure")
        actual_sync(path)
    monkeypatch.setattr(s, "_sync_directory", failed_generation_sync)
    with pytest.raises(m.M1Error, match="^PERSISTENCE_FAILED$"):
        s.persist_m1_generation(result, output_root=root, imported_at=result.request.now)
    generation_id, = s.list_m1_generations(root)
    original_receipt = s.read_m1_generation(root, generation_id)
    original_files = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    retry = m.audit_sec_m1(replace(result.request, now=result.request.now + timedelta(days=1)),
                          result.artifacts, result.observation_receipts)
    with pytest.raises(m.M1Error, match="^PERSISTENCE_FAILED$"):
        s.persist_m1_generation(retry, output_root=root, imported_at=retry.request.now)
    monkeypatch.setattr(s, "_sync_directory", actual_sync)
    assert s.persist_m1_generation(retry, output_root=root, imported_at=retry.request.now) == original_receipt
    assert original_files == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
