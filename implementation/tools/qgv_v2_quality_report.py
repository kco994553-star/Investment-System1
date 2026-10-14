#!/usr/bin/env python3
"""Report only validated published, price-free SEC QGV v2 inputs. Never acquires prices or fills unavailable rows."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.qgv.v2_quality_report import report
from investment_system.universe.sec_qgv2 import parse_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = report(parse_json(args.input.read_bytes()))
    except Exception:
        print('QGV2_QUALITY_REPORT INPUT_NOT_AVAILABLE_OR_INVALID')
        return 1
    args.out.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    print('QGV2_QUALITY_REPORT GENERATED codes=' + str(result['registered_codes']) + ' q=' + str(result['axes']['Q']['distribution']['count']) + ' g=' + str(result['axes']['G']['distribution']['count']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
