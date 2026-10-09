"""Raw artifact persistence manifest + retention audit (read-only; moves/deletes/uploads nothing).

Usage:
  python tools/raw_persistence_audit.py --now 2026-10-01T00:00:00+00:00 \
      --locations reports/raw_persistence/storage_locations_2026-10-01.json \
      --out reports/raw_persistence/raw_dataset_manifest_2026-10-01.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.producers.assembler import _atomic_write  # noqa: E402
from investment_system.producers.raw_persistence import dataset_manifest  # noqa: E402
from investment_system.producers.serialization import canonical_bytes  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--store', default=str(ROOT / 'data/raw'))
    p.add_argument('--locations', required=True)
    p.add_argument('--integrity', default=str(ROOT / 'reports/gate_evidence/raw_integrity_audit_2026-09-27.json'))
    p.add_argument('--now', required=True, help='explicit tz-aware evaluation clock (deterministic output)')
    p.add_argument('--out', required=True)
    a = p.parse_args(argv)
    loc = json.loads(Path(a.locations).read_text())
    audit = json.loads(Path(a.integrity).read_text())
    binding = {k: audit[k] for k in ('kind', 'upstream_run_id', 'archive_sha256', 'n_artifacts', 'bytes', 'passed')}
    m = dataset_manifest(a.store, loc['dataset_id'], loc['locations'], datetime.fromisoformat(a.now), binding)
    m['integrity_binding']['consistent_with_committed_manifests'] = (
        m['n_artifacts'] == audit['n_artifacts'] and m['total_bytes'] == audit['bytes'] and audit['passed'] is True
        and any(l.get('archive_sha256') == audit['archive_sha256'] and l.get('complete_blobs') for l in loc['locations']))
    if not m['integrity_binding']['consistent_with_committed_manifests']:
        print(json.dumps(m['integrity_binding'], indent=1))
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(out, json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False).encode() + b'\n')
    print(json.dumps({'out': str(out), 'n': m['n_artifacts'], 'bytes': m['total_bytes'],
                      'manifest_set_sha256': m['manifest_set_sha256'], 'retention': m['retention']['overall'],
                      'loss_deadline_if_no_action': m['retention']['loss_deadline_if_no_action']}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
