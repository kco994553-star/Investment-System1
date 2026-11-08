#!/usr/bin/env python3
"""Main screen inputs for 공통 분류 (DC-48, owner 2026-11-07) made ONLY by Codex's own functions on Codex's own cases.

Codex common-classification/1 (#516 9343b5e6; docs/research/common_classification/, manifest SHA-256 pinned below) owns every
classification decision. This tool never writes a view, a technical or a macro projection by hand and never chooses a state:
  record_cases     every fixtures.json record case through records.resolve (error cases keep Codex's error code), with
                   technical_macro.macro_projection on each resolved view.
  technical_cases  every fixtures.json technical case through technical_macro.technical_groups (error cases keep the code);
                   macro_projection on the normal case's view, so its technical and macro rows share one record.
  variants         Codex cases run with other arguments only: the normal store resolved on another valuation date
                   (EVALUATION_ONLY on a different day).
  bundle           the CLI's synthetic offline run (tools/common_classification.py run(), synthetic=True) on Codex's own CLI
                   test job (tests/research/test_common_classification_cli.job): classification-view.json,
                   qgv-classification-links.json, technical.json and macro.json of ONE run, so the same company/date carries
                   the same classification_record_id and classification_hash in detail, QGV, technical and macro.
  universe         the same Codex runs with only the company ids of their INPUTS renamed to Universe504 codes of the browser
                   tests' page (UNIVERSE_CODES; Codex then computes every record, hash and projection itself), so a screen row
                   (code = company_id) can meet them: record_cases (each case on its own), technical_normal (the normal technical
                   case: view, technical, macro) and bundle (the CLI run).
  owner_cases      which entry above shows each owner case (normal, multi-business, partial unclassified, period change,
                   share class / ADR, other evaluation date, version mismatch, empty / small group, plus conflict, outside
                   interval, REIT / telecom unresolved).
SYNTHETIC only. Run from the repository root:
  python implementation/tools/common_classification_main_fixture.py [--check]
writes (or with --check compares byte-for-byte) implementation/tests/fixtures/common_classification_main/main_fixture.json."""
import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests/research')]
from investment_system.research.common_classification.catalog import dictionary  # noqa: E402
from investment_system.research.common_classification.records import resolve  # noqa: E402
from investment_system.research.common_classification.technical_macro import technical_groups, macro_projection  # noqa: E402

HANDOFF = ROOT / 'docs/research/common_classification'
OUT = ROOT / 'tests/fixtures/common_classification_main/main_fixture.json'
PINS = {'CONTRACT.md': '00bccc2c38ae03e037ff820d6010a251b87f35983dadf1986217d0a1989258ea',
        'fixtures.json': '526cbf85defddbc4b255ea8dc5194ccab034c5eb9b317ef94142b5338c26ebcf',
        'dictionary.json': '9ae49c5f849535d325aaa64689da9fa61147347a9c8f8dafcf4055c0ef6d5776'}
# Universe504 codes of the browser tests' QGV page (tools/qgv_v2_fixture.js strictPayload, in its order).
UNIVERSE_CODES = ['NYSE:MMM', 'NYSE:AOS', 'NYSE:ABT', 'NYSE:ABBV', 'NYSE:ACN', 'NASDAQ:ADBE', 'NASDAQ:AMD', 'NYSE:AES', 'NYSE:AFL', 'NYSE:A',
                  'NYSE:APD', 'NASDAQ:ABNB', 'NASDAQ:AKAM', 'NYSE:ALB', 'NYSE:ARE', 'NASDAQ:ALGN', 'NYSE:ALLE', 'NASDAQ:LNT', 'NYSE:ALL', 'NASDAQ:GOOGL']
OWNER_CASES = {
    'normal': ['record_cases.normal', 'technical_cases.normal'],
    'multi_business': ['record_cases.multiple_business_tags'],
    'partial_unclassified_sector_only': ['record_cases.sector_only', 'record_cases.book_telecommunications'],
    'unclassified': ['record_cases.unclassified', 'record_cases.future_source'],
    'period_change': ['record_cases.change_before_known', 'record_cases.change_after_known'],
    'share_class_adr': ['technical_cases.different_share_class', 'technical_cases.different_adr_ratio'],
    'other_evaluation_date': ['variants.normal_other_date', 'technical_cases.different_date'],
    'version_mismatch': ['record_cases.version_mismatch', 'technical_cases.version_mismatch'],
    'empty_or_small_group': ['technical_cases.empty_group', 'technical_cases.nine_valid', 'technical_cases.missing_security'],
    'conflict': ['record_cases.conflicting_primary_sector'],
    'outside_interval': ['record_cases.outside_interval'],
    'reit_telecom_unresolved': ['record_cases.reit_exception', 'record_cases.modern_communication_exception'],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value):
    """The one canonical JSON form (sorted keys, UTF-8, no NaN) the committed file and the check use."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + '\n'


def error_code(exc):
    return str(exc).split(':')[0] if str(exc) else type(exc).__name__


def resolved(store, valuation_date, knowledge_as_of):
    try:
        view = resolve(store, valuation_date=valuation_date, knowledge_as_of=knowledge_as_of)
    except ValueError as exc:
        return {'valuation_date': valuation_date, 'knowledge_as_of': knowledge_as_of, 'error': error_code(exc), 'view': None, 'macro': None}
    return {'valuation_date': valuation_date, 'knowledge_as_of': knowledge_as_of, 'error': None, 'view': view, 'macro': macro_projection(view)}


def renamed(value, names):
    """An input with only exact company-id strings renamed (keys, record ids and every other value unchanged)."""
    if isinstance(value, dict):
        return {k: renamed(v, names) for k, v in value.items()}
    if isinstance(value, list):
        return [renamed(v, names) for v in value]
    return names.get(value, value) if isinstance(value, str) else value


def cli_bundle(names=None):
    spec = importlib.util.spec_from_file_location('common_classification_cli', ROOT / 'tools/common_classification.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    import test_common_classification_cli as codex_cli_test  # Codex's own synthetic CLI job (consumed, not edited)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if names:  # Codex's job() with its snapshot and store company ids renamed before anything is computed
            snapshot, store, view = codex_cli_test.inputs()  # view: only its knowledge_as_of is read by job()
            original = codex_cli_test.inputs
            codex_cli_test.inputs = lambda: (renamed(snapshot, names), renamed(store, names), view)
            try:
                job = codex_cli_test.job(tmp)
            finally:
                codex_cli_test.inputs = original
        else:
            job = codex_cli_test.job(tmp)
        cli.run(job, tmp / 'out', synthetic=True)
        read = lambda name: json.loads((tmp / 'out' / name).read_text())
        return {'view': read('classification-view.json'), 'qgv_links': read('qgv-classification-links.json'),
                'technical': read('technical.json'), 'macro': read('macro.json')}


def build():
    for name, want in PINS.items():
        if sha(HANDOFF / name) != want:
            raise SystemExit('CODEX_HANDOFF_PIN_MISMATCH ' + name)
    fixtures = json.loads((HANDOFF / 'fixtures.json').read_text())
    record_cases = {name: resolved(c['store'], c['valuation_date'], c['knowledge_as_of']) for name, c in fixtures['record_cases'].items()}
    technical_cases = {}
    for name, c in fixtures['technical_cases'].items():
        args = {k: v for k, v in c.items() if k != 'expected'}
        try:
            technical, error = technical_groups(**args), None
        except ValueError as exc:
            technical, error = None, error_code(exc)
        technical_cases[name] = {'error': error, 'technical': technical, 'view': c['view'], 'security_links': c['security_links'],
                                 'macro': macro_projection(c['view']) if name == 'normal' else None}
    normal = fixtures['record_cases']['normal']
    variants = {'normal_other_date': resolved(normal['store'], '2026-11-05', '2026-11-05T23:00:00Z')}
    one = lambda ids: dict(zip(ids, UNIVERSE_CODES))
    universe = {'codes': UNIVERSE_CODES,
                'record_cases': {name: resolved(renamed(c['store'], one(c['store']['members'])), c['valuation_date'], c['knowledge_as_of'])
                                 for name, c in fixtures['record_cases'].items()},
                'bundle': cli_bundle(one(['company-%03d' % i for i in range(20)]))}
    tc = renamed({k: v for k, v in fixtures['technical_cases']['normal'].items() if k != 'expected'}, one(fixtures['technical_cases']['normal']['view']['members']))
    universe['technical_normal'] = {'view': tc['view'], 'security_links': tc['security_links'], 'technical': technical_groups(**tc), 'macro': macro_projection(tc['view'])}
    return {'schema_version': 'main-common-classification-fixture/1', 'data_kind': 'SYNTHETIC',
            'made_by': 'implementation/tools/common_classification_main_fixture.py (Codex functions only)',
            'codex_handoff': {'path': 'implementation/docs/research/common_classification', 'sha256': PINS},
            'dictionary': dictionary(), 'record_cases': record_cases, 'technical_cases': technical_cases,
            'variants': variants, 'bundle': cli_bundle(), 'universe': universe, 'owner_cases': OWNER_CASES}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    body = text(build())
    if args.check:
        if not OUT.exists() or OUT.read_text() != body:
            print('MAIN_FIXTURE_DIFFERS_FROM_CODEX_OUTPUT', file=sys.stderr); return 1
        print('OK ' + hashlib.sha256(body.encode()).hexdigest()); return 0
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(body)
    print('WROTE ' + hashlib.sha256(body.encode()).hexdigest() + ' ' + str(len(body.encode())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
