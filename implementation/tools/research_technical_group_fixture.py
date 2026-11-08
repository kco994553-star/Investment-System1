#!/usr/bin/env python3
"""Offline public SYNTHETIC fixture; no prices, collection or runtime dependencies."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/research')]
from technical_membership_cases import make_fixture

OUT = ROOT / 'docs/research/common_classification/group-join-fixtures.json'


def encoded():
    return (json.dumps(make_fixture(), sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encoded()
    if args.check:
        if OUT.read_bytes() != data:
            raise SystemExit('SYNTHETIC_GROUP_FIXTURE_MISMATCH')
        print('SYNTHETIC group fixture matches')
    else:
        OUT.write_bytes(data)
        print(OUT.name)
