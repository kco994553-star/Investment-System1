#!/usr/bin/env python3
"""Compare a local archived publication with optional dated identities/PIT scores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.research.operational_coverage import coverage_from_archive
from investment_system.research.fv3_archive_compare import compare_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--identity-links', type=Path)
    ap.add_argument('--reconstructed', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    out = a.output.resolve()
    if any((p / '.git').exists() for p in out.parents):
        ap.error('output must be outside Git working trees')
    body = a.archive.read_bytes()
    coverage = coverage_from_archive(body)
    archive = json.loads(body)
    inputs = {'archive': coverage['source_sha256']}
    def optional(path, schema, key):
        if path is None:
            return None
        b = path.read_bytes()
        obj = json.loads(b)
        if obj.get('schema_version') != schema or not isinstance(obj.get(key), list):
            raise ValueError('INPUT_SCHEMA_MISMATCH')
        inputs[schema] = hashlib.sha256(b).hexdigest()
        return obj[key]
    links = optional(a.identity_links, 'dated-security-links/1', 'links') or []
    reconstructed = optional(a.reconstructed, 'fv3-pit-qgv/1', 'rows')
    result = compare_rows(archive['rows'], reconstructed, links,
                          as_of=archive['times']['price_basis_date'], calc_version=archive['calc_version'])
    result.update(input_hashes=inputs, archive_publication_id=archive['publication_id'], archive_times=archive['times'],
                  archive_signal_date_pit_eligible=coverage['signal_date_pit_eligible'],
                  source_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps({'schema_version': result['schema_version'], 'counts': result['counts']}))


if __name__ == '__main__':
    main()
