#!/usr/bin/env python3
"""Main screen inputs for the /2 boundary policy pair (owner 2026-11-08) made ONLY by Codex's own functions on Codex's own cases.

Codex #520 41f2a25b owns every decision: tests/fixtures/common_classification/boundary-policy-v2.json (SHA-256 pinned below) holds
six synthetic cases (REIT, managed care, broadcast, newspaper, real estate that is not a REIT, mixed cable). For each case this tool
runs, exactly as Codex's test_public_boundary_fixture_expected_components_and_unchanged_gate and
test_policy_view_remains_usable_by_common_technical_and_macro_producers do:
  extend_held_classification(snapshot, evidence, rule_version) → from_sector_snapshot(..., dictionary_version /2)
  → resolve(store, valuation_date=snapshot valuation date, knowledge_as_of=AT) → macro_projection(view, [])
and keeps the view, the macro projection and Codex's own expected sector / accounting. dictionary('common-industry-dictionary/2') is
kept once. Cases stay in Codex's order (a list). Main writes no view, no state and no expected value.
SYNTHETIC only. Run from the repository root:
  python implementation/tools/common_classification_policy_main_fixture.py [--check]
writes (or with --check compares byte-for-byte) implementation/tests/fixtures/common_classification_main/policy_v2_fixture.json."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from investment_system.research.sector_qgv_classification import extend_held_classification  # noqa: E402
from investment_system.research.common_classification.catalog import dictionary  # noqa: E402
from investment_system.research.common_classification.records import from_sector_snapshot, resolve  # noqa: E402
from investment_system.research.common_classification.technical_macro import macro_projection  # noqa: E402

CASES = ROOT / 'tests/fixtures/common_classification/boundary-policy-v2.json'
CASES_SHA256 = 'e82a248886f9b6bb89f681e3beed69931b9faf737aa4bc73853a7346abd689d9'
OUT = ROOT / 'tests/fixtures/common_classification_main/policy_v2_fixture.json'
DICT = 'common-industry-dictionary/2'
AT = '2026-11-08T09:00:00Z'      # Codex's own knowledge time in test_classification_boundary_policy.py


def text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + '\n'


def build():
    raw = CASES.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CASES_SHA256:
        raise SystemExit('CODEX_CASES_CHANGED ' + digest)
    pack = json.loads(raw)
    cases = []
    for case in pack['cases']:
        out, _ = extend_held_classification(case['snapshot'], case['evidence'], rule_version=pack['rule_version'])
        store = from_sector_snapshot(out, case['evidence'], source_sha256=digest, recorded_at=AT, data_kind='SYNTHETIC',
                                     dictionary_version=DICT)
        view = resolve(store, valuation_date=case['snapshot']['valuation_date'], knowledge_as_of=AT)
        cases.append({'case_id': case['case_id'], 'view': view, 'macro': macro_projection(view, []), 'expected': case['expected']})
    return {'schema_version': 'common-classification-policy-main-fixture/1', 'data_kind': 'SYNTHETIC',
            'codex_cases_sha256': digest, 'rule_version': pack['rule_version'], 'knowledge_as_of': AT,
            'dictionary': dictionary(DICT), 'cases': cases}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    body = text(build())
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding='utf-8') != body:
            print('POLICY_MAIN_FIXTURE_STALE')
            return 1
        print('OK ' + hashlib.sha256(body.encode('utf-8')).hexdigest())
        return 0
    OUT.write_text(body, encoding='utf-8')
    print('WROTE ' + hashlib.sha256(body.encode('utf-8')).hexdigest())
    return 0


if __name__ == '__main__':
    sys.exit(main())
