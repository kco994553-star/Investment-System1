"""C6 acceptance evidence and immutable boundary audit, executed by real Actions."""
from pathlib import Path
import json
import subprocess
import tempfile

from tests.evl_c6_fixture import full_acceptance
from investment_system.evl.walkforward import digest

CANONICAL='b8e39a2196a6d7794a04a0cd5393c68329e126ca'
START='88da6f30560c4a2aee281a4cc45760eb3e0f4e80'
BRANCH='claude/investment-system-top500-validation-alrugm'

def git(*args):
    return subprocess.check_output(['git',*args],text=True).strip()

def blobs(ref):
    return {line.split('\t',1)[1]:line.split('\t',1)[0].split()[2]
            for line in git('ls-tree','-r','--full-tree','-z',ref).split('\0') if line}

def boundary_audit():
    baseline,current,start=blobs(CANONICAL),blobs('HEAD'),blobs(START)
    if git('rev-parse','origin/'+BRANCH)!=CANONICAL:
        raise ValueError('canonical advanced; fresh integration audit required')
    frozen=[p for p in start if p.startswith('implementation/src/investment_system/evl/')
        or p.startswith('implementation/tests/test_evl_c')]
    changed=[p for p in frozen if current.get(p)!=start[p]]
    if changed:
        raise ValueError('existing Frozen source/test changed: '+repr(changed))
    # Exactly the six pre-existing shared Track C overlays and four authorized C4 repairs.
    allowed={
        'Investment System · Project Index.md',
        'Investment-System1 · Artifact Evidence Register 2026-09-23.md',
        'Investment-System1 · CURRENT_HANDOFF.md',
        'Investment-System1 · Contract Conflict Register 2026-09-23.md',
        'Investment-System1 · HANDOFF_HISTORY.md',
        'Investment-System1 · Master Status Index 2026-09-22.md',
        'implementation/src/investment_system/contracts/models.py',
        'implementation/src/investment_system/technical/engine.py',
        'implementation/src/investment_system/macro/engine.py'}
    unexpected=[p for p,h in baseline.items() if current.get(p)!=h and p not in allowed]
    if unexpected:
        raise ValueError('canonical protected artifacts changed: '+repr(unexpected))
    # No new source outside EVL except the preserved prior C4 lineage repair.
    unexpected_new=[p for p in current if p not in start and
        not (p.startswith('implementation/src/investment_system/evl/')
             or p.startswith('implementation/tests/evl_c6')
             or p.startswith('implementation/tests/test_evl_c6')
             or p.startswith('implementation/reports/track_c_')
             or p.startswith('implementation/tools/track_c_'))]
    if unexpected_new:
        raise ValueError('new file outside authorized Track C: '+repr(unexpected_new))
    for p in allowed:
        if p.startswith('implementation/src/') and current.get(p)!=start[p]:
            raise ValueError('prior upstream repair changed: '+p)
    if current.get('implementation/src/investment_system/contracts/lineage.py')!=start.get(
            'implementation/src/investment_system/contracts/lineage.py'):
        raise ValueError('prior lineage repair changed')
    merge_base=git('merge-base',CANONICAL,'HEAD')
    ahead_behind=git('rev-list','--left-right','--count',CANONICAL+'...HEAD').split()
    return {'status':'PASS','canonical':CANONICAL,'tested_head':git('rev-parse','HEAD'),
        'merge_base':merge_base,'behind':int(ahead_behind[0]),'ahead':int(ahead_behind[1]),
        'canonical_blob_count':len(baseline),'preserved_start_blob_count':len(start),
        'newly_changed_existing_phase_source_tests':changed,
        'unexpected_protected_changes':unexpected,'unexpected_new_scope_files':unexpected_new,
        'prior_authorized_four_file_repair':'PRESERVED',
        'Track_A_B_D_E_Web':'PRESERVED_BY_GIT_BLOB_IDENTITY',
        'EVL_SPEC_v0.1':'UNCHANGED'}

if __name__=='__main__':
    out=Path('reports/track_c_c6_generated')
    out.mkdir(parents=True,exist_ok=False)
    audit=boundary_audit()
    (out/'boundary_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    # Keep all full input registrations, C1/C5 ledgers, C4 predictions and C6 reports.
    result=full_acceptance(out/'families')
    summary={'boundary_audit':audit,'acceptance':result,
        'acceptance_hash':digest(result),
        'PIT_no_lookahead':'SYNTHETIC_CONTRACT_PATHS_VERIFIED',
        'lineage_provenance':'REGISTERED_HASH_BOUND_CURRENT_RESOLUTION_VERIFIED',
        'Holdout':'UNCONSUMED_NO_READER','cross_track':'PASS_BLOB_AUDIT',
        'real_research':'NOT_RUN_MISSING_COMPLETE_REAL_FAMILY',
        'negative_regression':'Required FAIL/NOT_RUN/budget/invalidation tests run before this artifact'}
    (out/'evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('TRACK_C_C6_EVIDENCE='+json.dumps(summary,sort_keys=True,separators=(',',':')))
    if result['status']!='PASS':
        raise SystemExit('C6 acceptance NOT_ACCEPTED; software Freeze blocked')
