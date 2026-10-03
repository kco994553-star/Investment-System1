"""Restore check for the raw store archive (read-only; uploads, deletes or commits nothing).

Verifies, against the committed data/raw/manifests (the repository's provenance of record):
  1. archive sha256 == expected (e.g. raw_integrity_audit archive_sha256)
  2. every committed manifest has a blob in the restored store with identical sha256/size
  3. the restored store's own manifests equal the committed manifests
  4. manifest_set_sha256 reproduces
  5. offline replay smoke via existing ingestion.replay on restored data

Usage (after extracting the artifact zip into DIR):
  python tools/raw_artifact_restore_check.py --archive a.zip --expected-sha <hex> --restored DIR --out result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.producers.raw_persistence import artifact_records, manifest_set_sha256, verify_blobs  # noqa: E402


def file_sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', required=True)
    ap.add_argument('--expected-sha', required=True)
    ap.add_argument('--restored', required=True, help='directory the artifact zip was extracted into')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    restored = Path(a.restored)
    store = next((p.parent for p in restored.rglob('STORE_INDEX.json') if (p.parent / 'blobs').is_dir()), None)
    committed = artifact_records(ROOT / 'data/raw')
    res = {'archive_bytes': Path(a.archive).stat().st_size, 'archive_sha256': file_sha(Path(a.archive)),
           'expected_sha256': a.expected_sha, 'restored_store_root': str(store)}
    res['archive_sha_match'] = res['archive_sha256'] == a.expected_sha
    if store is None:
        res['passed'] = False
        res['error'] = 'no RawDatasetStore (STORE_INDEX.json + blobs/) found in restored tree'
    else:
        restored_records = artifact_records(store)
        res['n_committed_manifests'] = len(committed)
        res['n_restored_manifests'] = len(restored_records)
        res['restored_manifests_equal_committed'] = (
            sorted((r['artifact_id'], r['sha256'], r['size']) for r in restored_records)
            == sorted((r['artifact_id'], r['sha256'], r['size']) for r in committed))
        res['n_blob_files'] = sum(1 for p in (store / 'blobs').iterdir() if p.is_file() and p.name != '.gitkeep')
        res['n_history_dirs'] = sum(1 for _ in (store / 'history').iterdir()) if (store / 'history').is_dir() else 0
        res['blob_verification'] = verify_blobs(store, committed)
        res['manifest_set_sha256'] = manifest_set_sha256(committed)
        res['restored_manifest_set_sha256'] = manifest_set_sha256(restored_records)
        smoke = {}
        try:
            from investment_system.ingestion.raw_store import RawDatasetStore
            from investment_system.ingestion.replay import load_price_bars
            st = RawDatasetStore(store)
            charts = sorted(i for i in st.list_ids() if i.startswith('yahoo_chart:') and i.endswith(':5y'))[:3]
            smoke['price_bars'] = {c: len(load_price_bars(st, c.split(':')[1], '5y')) for c in charts}
            facts = sorted(i for i in st.list_ids() if i.startswith('companyfacts:'))[:3]
            smoke['companyfacts_json_parse'] = {f: len(json.loads(st.get_bytes(f)).get('facts', {})) for f in facts}
            smoke['passed'] = all(v > 0 for v in smoke['price_bars'].values()) and all(v > 0 for v in smoke['companyfacts_json_parse'].values())
        except Exception as e:  # report, never hide
            smoke = {'passed': False, 'error': f'{type(e).__name__}: {e}'}
        res['offline_replay_smoke'] = smoke
        ge = next((p for p in restored.rglob('gate_evidence') if p.is_dir()), None)
        if ge is not None:
            same = diff = only = 0
            for f in ge.rglob('*'):
                if f.is_file():
                    g = ROOT / 'reports/gate_evidence' / f.relative_to(ge)
                    if not g.exists():
                        only += 1
                    elif file_sha(f) == file_sha(g):
                        same += 1
                    else:
                        diff += 1
            res['gate_evidence_vs_repo_info'] = {'identical': same, 'different': diff, 'only_in_artifact': only,
                                                 'note': 'information only; repo evidence was finalized after run 36305927245'}
        res['passed'] = bool(res['archive_sha_match'] and res['restored_manifests_equal_committed']
                             and res['blob_verification']['status'] == 'PASS' and smoke.get('passed'))
    res['elapsed_s'] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if res['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
