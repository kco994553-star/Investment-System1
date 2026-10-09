"""Read-only checkpoint verification; no source acquisition or production tests."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASELINE = '581c61c4af859f6cbdc3418209bba9be7bbc76a3'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def verify():
    tracked = git('ls-tree', '-rz', BASELINE).split(b'\0')
    matched = 0
    for record in tracked:
        if not record:
            continue
        meta, filename = record.split(b'\t', 1)
        mode, kind, expected = meta.decode().split()
        assert kind == 'blob', (kind, filename)
        path = ROOT / filename.decode()
        data = path.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == expected, ('baseline-byte-drift', filename.decode())
        matched += 1
    inv = json.loads((ROOT / 'implementation/experiments/chart-contract-v0.1/chart_inventory.json').read_text())
    assert inv['counts'] == {'user_core': 81, 'repository_additional': 24, 'candidate_extensions': 8, 'total_rows': 113}
    a = json.loads((HERE / 'lane-a/TARGET_ROOT_AND_MEMBERSHIP_EVIDENCE.json').read_text())
    assert a['validation']['total_exact_fraction'] == '1'
    assert a['validation']['theme_counts'] == {'반도체 장비': 5, 'AI·반도체': 5, 'Big Tech': 3, '기타산업': 6}
    assert a['production_current_target_root_status'] == 'NOT_AVAILABLE_NOT_ADMITTED'
    assert a['actual']['status'] == 'NOT_AVAILABLE' and a['actual']['fallback_to_target'] is False
    g = json.loads((HERE / 'governance/IMPLEMENTATION_PATH_MATRIX.json').read_text())
    assert g['combined_root_count']['total'] == 6
    assert g['combined_root_count']['new_chart_d3'] == 0
    assert all(not p['executed'] for p in g['candidates'])
    for path in HERE.rglob('*.json'):
        json.loads(path.read_text())
    for path in HERE.rglob('*.json.gz'):
        json.loads(gzip.decompress(path.read_bytes()))
    missing = []
    for path in HERE.rglob('*.md'):
        content = path.read_text()
        for link in re.findall(r'\]\(([^)]+)\)', content):
            if not link.startswith(('http:', 'https:', '#', '/')):
                target = link.split('#', 1)[0]
                if target and not (path.parent / target).exists():
                    missing.append((str(path.relative_to(HERE)), target))
    assert not missing, ('unresolved-local-links', missing)
    paths = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    manifest_path = HERE / 'ADDITIVE_ARTIFACT_MANIFEST.json'
    verified_artifacts = 0
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for rel, expected in manifest.get('files', {}).items():
            data = (HERE / rel).read_bytes()
            assert len(data) == expected['bytes']
            assert hashlib.sha256(data).hexdigest() == expected['sha256'], ('artifact-drift', rel)
            verified_artifacts += 1
    return {'status': 'PASS_CHECKPOINT_ONLY', 'baseline': BASELINE, 'existing_baseline_files_byte_equal': matched,
            'existing_paths_changed': 0, 'inventory_scope_preserved': inv['counts'],
            'current_target_production_root': a['production_current_target_root_status'],
            'target_pre_code_closure_gates': 6, 'new_chart_d3': 0,
            'new_checkpoint_files_observed': len(paths), 'new_manifested_artifact_hashes_verified': verified_artifacts,
            'local_links_resolve': True,
            'json_and_gzip_parse': True, 'production_code_writes': 0,
            'production_tests': 'NOT_RUN', 'chart_merge_result_fpia': 'NOT_RUN',
            'canonical_merge': 'NOT_DONE', 'network_requests_by_verifier': 0}


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
