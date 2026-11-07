#!/usr/bin/env python3
"""Measure a local official archive; writes privately outside Git, never fetches."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.research.operational_coverage import coverage_from_archive


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    if any((p / '.git').exists() for p in (output.parent, *output.parents)):
        ap.error('output must be outside Git working trees')
    report = coverage_from_archive(args.archive.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(report, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'schema_version': report['schema_version'], 'rows': report['denominator']['count'],
                      'source_sha256': report['source_sha256']}))


if __name__ == '__main__':
    main()
