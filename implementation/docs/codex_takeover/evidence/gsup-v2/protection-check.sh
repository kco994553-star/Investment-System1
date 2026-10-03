python - <<'PY'
import subprocess
owner = 'b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565'
def paths(ref):
    return set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref], text=True).splitlines())
def protected(path):
    return (path.startswith('implementation/src/investment_system/evl/')
            or path in {'implementation/tests/evl_c8_fixture.py', 'implementation/tests/evl_c8_gsup_oracle.py'}
            or (path.startswith('implementation/tests/test_evl_') and path.endswith('.py')))
existing = {path for path in paths(owner) if protected(path)}
subprocess.run(['git', 'diff', '--exit-code', owner, 'HEAD', '--', *sorted(existing)], check=True)
allowed_additions = {
    'implementation/src/investment_system/evl/gsup_source_identity.py',
    'implementation/src/investment_system/evl/superiority_source_identity.py',
    'implementation/tests/test_evl_gsup_source_identity.py',
    'implementation/tests/test_evl_gsup_v2_identity_adversarial.py',
    'implementation/tests/test_evl_gsup_identity_kernel_invariance.py',
    'implementation/tests/test_evl_gsup_mb_reduction_diagnostic.py',
}
additions = {path for path in paths('HEAD') - paths(owner) if protected(path)}
unexpected = additions - allowed_additions
if unexpected:
    raise SystemExit('Unapproved Track C additions: ' + ', '.join(sorted(unexpected)))
print(f'Preserved {len(existing)} exact owner files; approved additive files {len(additions)}')
PY
git diff --exit-code b8e39a2196a6d7794a04a0cd5393c68329e126ca -- implementation/reports/gate_evidence implementation/data
git diff --exit-code b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565 -- implementation/src/investment_system/technical/engine.py implementation/src/investment_system/macro/engine.py implementation/src/investment_system/contracts/models.py implementation/src/investment_system/contracts/lineage.py
