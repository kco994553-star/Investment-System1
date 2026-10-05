#!/usr/bin/env python3
"""Repeat nine independently reviewed offline probes; fabricated claims only.

Selects --repo explicitly and exclusively creates --output outside repositories.
Replays the preserved nine case definitions and historical fixture clock.
No receipt is authenticated,
no gate is closed, and no production or owner data is changed.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
REPO = args.repo.resolve()
OUTPUT = args.output.resolve()
# The runner is diagnostic-only: never create evidence inside either the
# selected input checkout or the checkout containing this runner.
RUNNER_REPO = next((p for p in Path(__file__).resolve().parents if (p / '.git').exists()), None)
if not (REPO / '.git').exists():
    parser.error('--repo must be a Git checkout root')
if OUTPUT.is_relative_to(REPO) or (RUNNER_REPO and OUTPUT.is_relative_to(RUNNER_REPO)):
    parser.error('--output must be outside input and runner repositories')
if OUTPUT.exists():
    parser.error('--output must be a new file; overwrite is forbidden')
PINS = json.loads(Path(__file__).with_name('DIAGNOSTIC_INPUT_PINS.json').read_text())
for name, pin in PINS['selected_inputs'].items():
    candidate = REPO / pin['path']
    if not candidate.resolve().is_relative_to(REPO):
        parser.error('selected diagnostic input escapes --repo')
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != pin['sha256']:
        parser.error('selected diagnostic input hash differs: ' + name)

TOOL_DIR = REPO / 'implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6'
TOOL_PATH = TOOL_DIR / 'receipt_preflight.py'
FIXTURE_PATH = TOOL_DIR / 'test_receipt_preflight.py'
CLOCK = '2026-10-05T03:00:00+00:00'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


tool = load('review_tool', TOOL_PATH)
fixtures = load('review_fixture', FIXTURE_PATH)
pinned_bytes = tool.git_bytes(REPO, tool.SOURCE_COMMIT, tool.REQUEST_PATH)
baseline = tool.strict_json(pinned_bytes)
baseline_equals_fixture = baseline == json.loads(fixtures.BASELINE_PATH.read_text())
def require(condition, message):
    if not condition:
        raise ValueError(message)


require(baseline_equals_fixture, 'pinned request differs from fixture baseline')
require(len(baseline['constituents']) == 19, 'pinned request is not the preserved 19-row fixture')
outcomes = []


def probe(name, edit, expected):
    packet = fixtures.fake_complete_packet(baseline)
    edit(packet)
    before = copy.deepcopy(packet)
    report = tool.inspect_packet(packet, baseline, REPO, CLOCK)
    input_unchanged = packet == before
    gates_remain_open = report['open_count'] == 6 and report['closed_count'] == 0
    production_payload_null = report['production_payload'] is None
    status_matches = report['source_inspection'] == expected
    require(input_unchanged, name + ': probe mutated its input')
    require(status_matches, name + ': unexpected inspection ' + report['source_inspection'])
    require(gates_remain_open and production_payload_null, name + ': diagnostic authority boundary changed')
    outcomes.append({
        'name': name,
        'expected_source_inspection': expected,
        'observed_source_inspection': report['source_inspection'],
        'input_unchanged': input_unchanged,
        'open_count': report['open_count'],
        'closed_count': report['closed_count'],
        'production_readiness': report['production_readiness'],
        'production_payload_is_null': production_payload_null,
        'findings': report['findings'],
        'outcome': 'PASS',
    })


probe('Timezone-equal root start',
      lambda x: x['root_owner_return'].__setitem__('effective_from', '2026-10-05T09:00:00+09:00'),
      'INPUT_COMPLETE_UNAUTHENTICATED')
probe('Earlier covering row start',
      lambda x: x['constituents'][0]['owner_return'].__setitem__('effective_from', '2026-10-04T23:00:00+00:00'),
      'INPUT_COMPLETE_UNAUTHENTICATED')
probe('Later row start misses root beginning',
      lambda x: x['constituents'][0]['owner_return'].__setitem__('effective_from', '2026-10-05T00:01:00+00:00'),
      'INVALID')
probe('Finite row cannot cover indefinite root',
      lambda x: x['constituents'][0]['owner_return'].__setitem__('effective_to', '2026-10-06T00:00:00+00:00'),
      'INVALID')


def finite(packet):
    packet['root_owner_return']['effective_to'] = '2026-10-07T00:00:00+00:00'
    packet['constituents'][0]['owner_return']['effective_to'] = '2026-10-06T00:00:00+00:00'


probe('Finite row misses finite root end', finite, 'INVALID')
probe('Source rows may reorder without identity reassignment',
      lambda x: x['constituents'].reverse(), 'INPUT_COMPLETE_UNAUTHENTICATED')
probe('Nested invalid float in unchanged source shape',
      lambda x: x['constituents'][0]['source_refs'][0].__setitem__('line', float('inf')),
      'INVALID')
probe('Explicit available-at exactly decision',
      lambda x: x['root_owner_return'].__setitem__('available_at', CLOCK),
      'INPUT_COMPLETE_UNAUTHENTICATED')
probe('Expired row end is exclusive',
      lambda x: x['constituents'][0]['owner_return'].__setitem__('effective_to', CLOCK),
      'INVALID')

result = {
    'scope': 'NINE_READ_ONLY_OFFLINE_PREFLIGHT_PROBES_NOT_PRODUCTION_EVIDENCE',
    'synthetic_owner_claims_only': True,
    'observed_at_utc': datetime.now(timezone.utc).isoformat(),
    'decision_time': CLOCK,
    'repository': str(REPO),
    'tool': {'path': str(TOOL_PATH), 'sha256': digest(TOOL_PATH)},
    'fixture_generator': {'path': str(FIXTURE_PATH), 'sha256': digest(FIXTURE_PATH)},
    'fixture_baseline': {'path': str(fixtures.BASELINE_PATH), 'sha256': digest(fixtures.BASELINE_PATH)},
    'pinned_request': {
        'commit': tool.SOURCE_COMMIT,
        'path': tool.REQUEST_PATH,
        'sha256': hashlib.sha256(pinned_bytes).hexdigest(),
        'equals_current_fixture_baseline': baseline_equals_fixture,
        'constituent_count': len(baseline['constituents']),
    },
    'reproducer_sha256': digest(Path(__file__)),
    'input_pin_manifest_sha256': digest(Path(__file__).with_name('DIAGNOSTIC_INPUT_PINS.json')),
    'historical_probe_commit': PINS['historical_probe_commit'],
    'historical_probe_sha256': PINS['historical_probe_sha256'],
    'case_count': len(outcomes),
    'pass_count': sum(x['outcome'] == 'PASS' for x in outcomes),
    'cases': outcomes,
    'review_recommendation': 'NO_CHANGE',
    'all_six_gates_remain_open': all(x['open_count'] == 6 and x['closed_count'] == 0 for x in outcomes),
    'repository_files_modified': False,
}
result_path = OUTPUT
with result_path.open('x', encoding='utf-8') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    handle.write('\n')
print(json.dumps({
    'result_path': str(result_path),
    'case_count': result['case_count'],
    'pass_count': result['pass_count'],
    'tool_sha256': result['tool']['sha256'],
    'fixture_generator_sha256': result['fixture_generator']['sha256'],
    'fixture_baseline_sha256': result['fixture_baseline']['sha256'],
}, indent=2))
