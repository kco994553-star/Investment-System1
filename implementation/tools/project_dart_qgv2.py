#!/usr/bin/env python3
"""Project already-collected DART annual lines with the same v2 Q/G formulae.

No external request, credential lookup or personal input. The original DART daily
step owns collection; this optional projection fails open with fixed tokens.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def project(directory):
    from investment_system.product import dart_public as dart
    from investment_system.product.dart_qgv2 import metric_projection
    path = Path(directory) / dart.FINANCIALS_FILENAME
    if not path.is_file():
        print('DART_QGV2_REFERENCE NOT_AVAILABLE code=DART_NOT_COLLECTED')
        return 0
    try:
        payload = dart.require_financials(dart.parse_json(path.read_bytes()))
        for company in payload['companies'].values():
            company['qgv2'] = metric_projection(company)
        body = dart.encode(dart.FINANCIALS_FILENAME, dart.require_financials(payload))
        temporary = path.with_suffix('.qgv2-tmp')
        temporary.write_bytes(body)
        temporary.replace(path)
    except Exception:
        print('DART_QGV2_REFERENCE NOT_AVAILABLE code=PROJECTION_FAILED')
        return 0
    state = payload['companies']['hanmi']['state']
    print('DART_QGV2_REFERENCE state=' + state + ' comparison=REFERENCE_ONLY')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    raise SystemExit(project(parser.parse_args().out))
