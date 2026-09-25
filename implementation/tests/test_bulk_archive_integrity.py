"""import_bulk_real_data.py fail-closed integrity gate. Offline, synthetic archives only."""
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

from investment_system.ingestion.raw_store import RawDatasetStore

ROOT = Path(__file__).resolve().parents[1]


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "import_bulk_real_data.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sec_zip(path, n=3):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, n + 1):
            zf.writestr(f"CIK{str(i).zfill(10)}.json", json.dumps({"cik": i, "facts": {"x": list(range(2000))}}))
    return path


def _run_main(mod, monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["import_bulk_real_data.py", *argv])
    return mod.main()


def test_valid_archive_verifies_and_imports_with_provenance(tmp_path, monkeypatch):
    mod = _mod("ibrd_ok")
    z = _sec_zip(tmp_path / "companyfacts.zip")
    v = mod.verify_archive(z, mod.CIK_RE)
    assert v["passed"] is True and v["n_members"] == 3 and v["n_matching_members"] == 3 and len(v["sha256"]) == 64
    rc = _run_main(mod, monkeypatch, ["--store", str(tmp_path / "raw"), "--sec-companyfacts", str(z),
                                      "--report-out", str(tmp_path / "rep.json")])
    rep = json.loads((tmp_path / "rep.json").read_text())
    store = RawDatasetStore(tmp_path / "raw")
    assert rc == 0 and rep["results"][0]["imported"] == 3
    assert f"archive_sha256={v['sha256']}" in store.get_manifest("companyfacts:0000000001")["notes"]
    assert json.loads((tmp_path / "raw" / "STORE_INDEX.json").read_text())["n_artifacts"] == 3


def test_truncated_archive_like_gpt_r5_is_rejected_and_store_untouched(tmp_path, monkeypatch):
    mod = _mod("ibrd_trunc")
    full = _sec_zip(tmp_path / "full.zip", n=5).read_bytes()
    z = tmp_path / "companyfacts.zip"
    z.write_bytes(full[: int(len(full) * 0.8)])  # no EOCD / central directory, last member cut
    v = mod.verify_archive(z, mod.CIK_RE)
    assert v["passed"] is False and "ZIP_UNREADABLE_NO_CENTRAL_DIRECTORY_OR_TRUNCATED" in v["reasons"]
    assert v["first_signature"] == "504b0304"
    rc = _run_main(mod, monkeypatch, ["--store", str(tmp_path / "raw"), "--sec-companyfacts", str(z)])
    assert rc == 2
    assert not (tmp_path / "raw").exists() or RawDatasetStore(tmp_path / "raw").list_ids() == []


def test_crc_corrupt_member_is_rejected(tmp_path):
    mod = _mod("ibrd_crc")
    z = tmp_path / "c.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("CIK0000000001.json", b'{"a": "' + b"A" * 500 + b'"}')
    b = bytearray(z.read_bytes())
    i = b.find(b"AAAA")
    b[i] = ord("B")  # flip payload byte, CRC now wrong
    z.write_bytes(bytes(b))
    v = mod.verify_archive(z, mod.CIK_RE)
    assert v["passed"] is False and "MEMBER_CRC_FAILED" in v["reasons"]


def test_sha256_mismatch_and_verify_only_never_write(tmp_path, monkeypatch):
    mod = _mod("ibrd_sha")
    z = _sec_zip(tmp_path / "companyfacts.zip")
    assert "SHA256_MISMATCH" in mod.verify_archive(z, mod.CIK_RE, "0" * 64)["reasons"]
    rc = _run_main(mod, monkeypatch, ["--store", str(tmp_path / "raw"), "--sec-companyfacts", str(z), "--verify-only"])
    assert rc == 0 and not (tmp_path / "raw").exists()
