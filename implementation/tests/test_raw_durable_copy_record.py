"""The committed 2026-10-11 storage record must keep the raw dataset DURABLE_COPY_PRESENT (private release, verified)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from investment_system.producers.raw_persistence import retention_audit

ROOT = Path(__file__).resolve().parents[1]


def test_private_release_copy_is_durable_and_bound_to_the_frozen_set():
    loc = json.loads((ROOT / 'reports/raw_persistence/storage_locations_2026-10-11.json').read_text())
    release = [l for l in loc['locations'] if l['kind'] == 'GITHUB_RELEASE']
    assert len(release) == 1 and release[0]['expires_at'] is None and release[0]['verified'] and release[0]['complete_blobs']
    assert release[0]['archive_sha256'] == '712e43bcc1fcd137e5e99ccdda2440850eda56015e02037293d8eac8db399f94'
    assert 'verify_blobs PASS 6808/6808' in release[0]['verification']
    # Still durable after the Actions artifact expires (2026-12-26).
    for now in (datetime(2026, 10, 11, tzinfo=timezone.utc), datetime(2027, 1, 1, tzinfo=timezone.utc)):
        assert retention_audit(loc['locations'], now)['overall'] == 'DURABLE_COPY_PRESENT'
    manifest = json.loads((ROOT / 'reports/raw_persistence/raw_dataset_manifest_2026-10-11.json').read_text())
    assert manifest['retention']['overall'] == 'DURABLE_COPY_PRESENT' and manifest['n_artifacts'] == 6808
    assert manifest['integrity_binding']['consistent_with_committed_manifests'] is True
