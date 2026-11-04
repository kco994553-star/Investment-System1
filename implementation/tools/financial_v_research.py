#!/usr/bin/env python3
"""Evaluate locally prepared financial V research inputs; no network/publication."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.research.financial_v import evaluate, VERSION, CONFIG_SHA256


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    output = args.output.resolve()
    if any((p / '.git').exists() for p in (output.parent, *output.parents)):
        ap.error('output must be outside Git working trees')
    rows = [evaluate(row) for row in json.loads(args.input.read_bytes())['rows']]
    report = {'schema_version': VERSION, 'config_sha256': CONFIG_SHA256, 'rows': rows}
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({'schema_version': VERSION, 'rows': len(rows)}))


if __name__ == '__main__':
    main()
