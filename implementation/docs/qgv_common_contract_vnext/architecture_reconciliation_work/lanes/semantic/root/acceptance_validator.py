"""Bounded inactive artifact/authority closure, not production admission.

The manifest supplies immutable exact-byte contracts. Domain/numeric correctness,
real PIT, scheduler evidence and production enforcement are not evaluated here.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new-base', required=True, type=Path)
    parser.add_argument('--prior-base', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    assert manifest['kind'] == 'INACTIVE_G_C_EXACT_ARTIFACT_ACCEPTANCE_V1'
    assert manifest['production_enabled'] is False
    seen = set()
    checked = []
    for role, base in [('outputs', args.new_base), ('reused_inputs', args.prior_base)]:
        for entry in manifest[role]:
            relative = Path(entry['relative_path'])
            assert not relative.is_absolute() and '..' not in relative.parts
            key = (role, str(relative))
            assert key not in seen
            seen.add(key)
            assert sha(base / relative) == entry['sha256'], key
            checked.append(key)
    approval = json.loads((args.new_base / 'root/approval.json').read_text())
    matrix = json.loads((args.new_base / 'g/G_CANDIDATE_MATRIX.json').read_text())
    g_verification = json.loads((args.new_base / 'g/G_CANDIDATE_VERIFICATION.json').read_text())
    c_verification = json.loads((args.new_base / 'consumer/CONTRACT_ACCEPTANCE_RESULTS.json').read_text())
    assert approval['G1']['economic_target'] == 'LONG_HORIZON_REALIZED_GROWTH'
    assert approval['G2']['principle'] == 'NO_AUTOMATIC_CROSS_METRIC_SUBSTITUTION_WITHOUT_SEMANTIC_AUTHORITY'
    assert sha(args.new_base / 'root/approval.json') == matrix['approval_ref']['sha256']
    assert matrix['approval_ref']['authenticated_remote_commit'] == manifest['approval_commit']
    assert approval['method_selection'] == 'NOT_APPROVED'
    assert approval['migration'] == 'NOT_APPROVED'
    assert approval['runtime_enabled'] is False
    assert approval['production_migration_authorized'] is False
    assert approval['V1'] == approval['V2'] == 'PENDING'
    assert matrix['B1'] == 'MORE_EVIDENCE_REQUIRED'
    assert matrix['new_requiredness_assignments'] == 0
    assert matrix['candidate_count'] == len(matrix['candidates']) == 8
    for candidate in matrix['candidates']:
        assert candidate['method_id'] is candidate['method_version'] is None
        assert candidate['runtime_enabled'] is False
        assert candidate['approved_production_formula'] is None
        assert candidate['numeric_policy'] is None
        assert set(candidate['outputs'].values()) == {'UNCOMPUTED'}
    assert g_verification['count'] == g_verification['passed']
    assert all(case['pass'] for case in g_verification['checks'])
    assert g_verification['script_sha256'] == sha(args.new_base / 'g/g_candidate_comparison.py')
    for name, expected in g_verification['outputs'].items():
        assert sha(args.new_base / 'g' / name) == expected
    assert c_verification['checks_failed'] == 0
    assert c_verification['checks_passed'] == len(c_verification['cases'])
    assert all(case['pass'] for case in c_verification['cases'])
    assert c_verification['script_sha256'] == sha(args.new_base / 'consumer/contract_acceptance_probe.py')
    assert c_verification['production_semantics_changed'] is False
    assert c_verification['consumer_policy_activated'] is False
    assert c_verification['scoring_executed'] is False
    assert c_verification['scheduler_hops_counted'] == 0
    assert c_verification['b1_roles_assigned'] == 0
    output = {
        'status': 'PASS_INACTIVE_ARTIFACT_AUTHORITY_CLOSURE_ONLY',
        'manifest_sha256': sha(args.manifest),
        'validator_sha256': sha(Path(__file__)),
        'outputs_verified': len(manifest['outputs']),
        'reused_inputs_verified': len(manifest['reused_inputs']),
        'G_new_checks': g_verification['count'],
        'C_new_checks': c_verification['checks_passed'],
        'approval_commit': manifest['approval_commit'],
        'scheduler_hops_added': 0,
        'runtime_enabled': False,
        'real_PIT_OOS': 'NOT_RUN',
        'production_enforcement': 'NOT_IMPLEMENTED',
    }
    print(json.dumps(output, sort_keys=True))


if __name__ == '__main__':
    main()
