"""Read-only JSON/AST authority cross-check. Does not execute any numeric kernel."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

REPOSITORY = Path('/workspace/Investment-System1')
HEAD = '675d0d298fbaab5b8473ed048a561ef84e2f3e78'
OWNER = 'b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565'
INPUT = Path('/workspace/takeover-evidence/pr31-handoff/arithmetic-repro')
OUTPUT = Path('/workspace/takeover-evidence/pr31-handoff/method-authority-review')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def encoded(value):
    if type(value) is float:
        return {'decimal': repr(value), 'hex': value.hex()}
    if isinstance(value, dict):
        return {key: encoded(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encoded(item) for item in value]
    return value


def literal(node):
    """Only the existing diagnostic fixture's literal syntax; never eval code."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [literal(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -literal(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return literal(node.left) * literal(node.right)
    raise ValueError(type(node).__name__)


def git_bytes(path, ref=HEAD):
    return subprocess.check_output(['git', '-C', str(REPOSITORY), 'show', ref + ':' + path])


def binding(path, raw):
    return {'sha256': digest(raw), 'git_blob': hashlib.sha1(
        b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


manifest = json.loads((INPUT / 'ARTIFACT_MANIFEST.json').read_text())
archive_checks = []
for entry in manifest['files']:
    raw = (INPUT / entry['path']).read_bytes()
    assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
    archive_checks.append(entry)

driver_path = INPUT / 'replay_arithmetic_candidates.py'
driver_raw = driver_path.read_bytes()
driver = ast.parse(driver_raw)
assert any(isinstance(n, ast.FunctionDef) and n.name == 'original_functions' for n in driver.body)
sim_path = 'implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py'
sim_tree = ast.parse(git_bytes(sim_path))
run = next(n for n in sim_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
out_pos = next(i for i, n in enumerate(run.body) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'out' for t in n.targets))
prefix = run.body[:out_pos + 1]
prefix_hash = digest('\n'.join(ast.dump(n, include_attributes=False) for n in prefix).encode())
assert len(prefix) == 18
assert prefix_hash == '8ac9671c8fc36037a1a5824cddffc734c9c5466d36f3db152b66cf152b2b88df'
diagnostic_path = 'implementation/tools/gsup_mb_reduction_diagnostic.py'
diagnostic = ast.parse(git_bytes(diagnostic_path))
fixture_node = next(n for n in diagnostic.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in n.targets))
fixtures = literal(fixture_node.value)
assert len(fixtures) == 9
fixture_by_id = {f['id']: encoded(f) for f in fixtures}

processes = []
all_runtime_summaries = {}
all_source_bindings = {}
trace_statuses = Counter()
trace_checks = count_checks = source_checks = literal_p_checks = 0
shared_case_indices = {}
for label in ('cpython311_numpy235', 'cpython312_numpy235', 'cpython313_numpy224'):
    paths = [INPUT / (label + '_process' + str(i) + '.json') for i in (1, 2)]
    assert paths[0].read_bytes() == paths[1].read_bytes(), label
    for path in paths:
        raw = path.read_bytes()
        data = json.loads(raw)
        assert data['driver_sha256'] == digest(driver_raw)
        assert data['status'] == 'EVIDENCE_ONLY_NO_REDUCTION_SELECTED'
        assert data['frozen_index_grid_checks'] == sum((1, 2, 3, 4, 5, 8, 9, 12)) * 4 == 176
        assert data['frozen_index_grid_sha256'] == '679f4fc26848fda68b65890e8dc4bf94b99ca01f8ff8be9b3f7a4b0eb7a7e34b'
        core = {key: data[key] for key in ('scope', 'status', 'cases', 'frozen_index_grid_checks', 'frozen_index_grid_sha256')}
        assert digest(canonical(encoded(core))) == data['canonical_numeric_output_sha256']
        for source_path, expected in data['pinned_sources'].items():
            actual = binding(source_path, git_bytes(source_path))
            assert actual == expected, source_path
            all_source_bindings[source_path] = actual
            source_checks += 1
        case_summaries = {}
        for case in data['cases']:
            case_id = case['fixture']['id']
            assert case['fixture'] == fixture_by_id[case_id]
            assert digest(canonical(case['indices'])) == case['indices_sha256']
            if case_id in shared_case_indices:
                assert case['indices'] == shared_case_indices[case_id]
            shared_case_indices[case_id] = case['indices']
            summaries = {}
            for reference in case['references']:
                trace = reference['trace']
                assert digest(canonical({k: v for k, v in trace.items() if k != 'reduction'})) == reference['numeric_payload_sha256']
                assert trace['selected_authoritative_reduction'] is False and trace['official'] is False
                summary = reference['summary']
                assert summary['status'] == trace['status']
                trace_statuses[trace['status']] += 1
                trace_checks += 1
                if trace['status'] != 'NOT_RUN':
                    assert trace['indices'] == case['indices']
                    draws = trace['replicates']
                    assert len(draws) == case['fixture']['replicates']
                    assert summary['r'] == trace['exceedances'] == sum(d['exceeds'] for d in draws)
                    assert summary['degenerate'] == trace['degenerate_replicates'] == sum(d['degenerate'] for d in draws)
                    assert summary['tie'] == trace['ties'] == sum(d['tie'] for d in draws)
                    assert all(not d['exceeds'] and not d['tie'] for d in draws if d['degenerate'])
                    assert all(d['exceeds'] for d in draws if d['tie'])
                    assert summary['p_hex'] == trace['p_value']['hex']
                    assert float.fromhex(summary['p_hex']) == (summary['r'] + 1) / (len(draws) + 1)
                    count_checks += 1
                summaries[reference['candidate']] = summary
            literal_check = case['pinned_original_mb_s_plus1_check']
            if literal_check['status'] == 'EXACT_P_HEX_MATCH':
                assert literal_check['p_hex'] == summaries['NUMPY_CUMULATIVE_2_3_5']['p_hex']
                literal_p_checks += 1
            case_summaries[case_id] = {'candidates': summaries, 'literal_original': literal_check}
        processes.append({'path': path.name, 'sha256': digest(raw), 'bytes': len(raw),
                          'runtime': {k: data['runtime'][k] for k in ('python_version', 'numpy', 'machine', 'compiler', 'platform', 'executable_sha256', 'numpy_multiarray_sha256')},
                          'canonical_numeric_output_sha256': data['canonical_numeric_output_sha256']})
        all_runtime_summaries.setdefault(label, case_summaries)

historical_path = 'implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.json'
old = json.loads(git_bytes(historical_path))
owner_old = git_bytes(historical_path, OWNER)
assert owner_old == git_bytes(historical_path)
ce4 = old['CE4_decision_flip_L_not_dividing_n']
assert ce4['MB'] == {'p': 0.1, 'r': 1, 'degenerate': 1}
assert ce4['kernel'] == {'p': 0.15, 'r': 2, 'degenerate': 1}
for label, cases in all_runtime_summaries.items():
    for candidate, result in cases['CE4_DEGENERACY']['candidates'].items():
        if result['status'] != 'NOT_RUN':
            assert result['p'] == ce4['MB']['p'] and result['r'] == ce4['MB']['r']
    assert cases['CE4_DEGENERACY']['literal_original']['status'] in ('EXACT_P_HEX_MATCH', 'NOT_RUN')

output = {
    'record': 'PR31_INDEPENDENT_READ_ONLY_ARITHMETIC_RECEIPT_CROSSCHECK',
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'source_HEAD': HEAD, 'owner_HEAD': OWNER, 'status': 'PASS_EVIDENCE_ONLY_NO_REDUCTION_SELECTED',
    'reviewer_scope': 'Read-only Git blobs, source AST, receipt hashes, JSON counts and exact commitments; no numerical-kernel or index-stream reexecution',
    'arithmetic_worker_execution_observed': {'fresh_processes': 6, 'fresh_process_pairs_byte_identical': '3/3', 'existing_fixtures_per_process': 9, 'reported_frozen_index_combinations_per_process': 176},
    'independently_verified': {'archive_files': len(archive_checks), 'exact_source_binding_checks': source_checks, 'distinct_pinned_sources': len(all_source_bindings),
                              'numeric_trace_commitments': trace_checks, 'computed_trace_counts_and_plus_one': count_checks, 'original_literal_p_hex_matches': literal_p_checks,
                              'status_counts': dict(trace_statuses), 'shared_fixture_definitions': 9, 'shared_frozen_case_index_streams': 9},
    'driver_sha256': digest(driver_raw), 'driver_AST_inspected': True,
    'original_run_prefix': {'statements_through_out': len(prefix), 'AST_sha256': prefix_hash,
                            'unchanged_S_plus1_expressions': True, 'unrelated_removed_section': 'M-C/BM_t',
                            'explicit_transport_substitution': 'Original rng.integers supplied normative Frozen C6 Python random.Random starts; not original NumPy RNG stream'},
    'source_bindings': all_source_bindings, 'process_receipts': processes,
    'runtime_case_summaries': all_runtime_summaries,
    'CE4_label_reconciliation': {'status': 'NO_SOURCE_OR_RESULT_CONTRADICTION', 'historical_blob': binding(historical_path, owner_old),
                               'immutable_MB': ce4['MB'], 'immutable_v1_kernel': ce4['kernel'],
                               'finding': 'An internal review request reversed the labels; both immutable JSON and MD say M-B .10 versus v1 .15. All available current M-B transports reproduce .10 on this fixture.'},
    'historical_environment_limits': {'simulation_numpy_version': 'UNRECORDED', 'simulation_full_runtime': 'UNVERIFIED',
                                      'Python_3_11_15_in_historical_reproducibility': 'C6 index/kernel subsection only; does not independently pin NumPy M-B simulation',
                                      'exact_historical_MB_aggregate_replay_claim': 'NOT_SUPPORTED_BY_ANY_CANDIDATE'},
    'numpy_2_3_5_on_Python_3_13_with_installed_2_2_4': 'NOT_RUN_NO_FALLBACK_OR_REPIN',
    'decision': {'selected_reduction': None, 'authoritative_v2': 'NOT_IMPLEMENTED', 'status': 'USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION'},
    'reviewer_actions': {'numerical_driver': 'NOT_RUN', 'numeric_kernel': 'NOT_RUN', 'repository_tests': 'NOT_RUN', 'GitHub_Actions': 'NOT_RUN',
                         'repo_or_remote_changes': 0, 'CAL_VERIFY_accesses': 0, 'Holdout_consumptions': 0, 'numeric_defaults_selected': 0,
                         'Freeze_grants': 0, 'publication_grants': 0, 'canonical_merges': 0}
}
target = OUTPUT / 'ARITHMETIC_REPRO_CROSSCHECK.json'
with target.open('x') as handle:
    json.dump(output, handle, indent=2, sort_keys=True, allow_nan=False)
    handle.write('\n')
print(json.dumps({'receipt': str(target), 'sha256': digest(target.read_bytes()), 'checks': output['independently_verified']}))
