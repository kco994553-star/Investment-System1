"""Actual Actions C7 mandatory software acceptance; never reads real Holdout."""
from pathlib import Path
import json
import subprocess
from tools.track_c_c6_acceptance import boundary_audit, blobs, git
from tests.evl_c7_fixture import full_acceptance
from investment_system.evl.walkforward import digest
from investment_system.evl.profile_selection import STAGES
START='88f66c57c810b5dda135b79552b38484d89d61a7'
NEW_FILES=["implementation/src/investment_system/evl/selection.py","implementation/src/investment_system/evl/selection_contracts.py","implementation/src/investment_system/evl/landscape.py","implementation/src/investment_system/evl/profile_selection.py","implementation/tests/evl_c7_fixture.py","implementation/tests/test_evl_c7_selection.py","implementation/tests/test_evl_c7_protocol.py"]
def preservation():
    prior,current=blobs(START),blobs('HEAD')
    frozen=[p for p in prior if p.startswith('implementation/src/')
        or p.startswith('implementation/tests/')]
    changed=[p for p in frozen if prior[p]!=current.get(p)]
    if changed: raise ValueError('C0-C6/upstream source/test preservation failure: '+repr(changed))
    allowed_existing={
        '.github/workflows/track-c-evl-validation.yml',
        'implementation/tools/track_c_c6_acceptance.py',
        'Investment System · Project Index.md',
        'Investment-System1 · Artifact Evidence Register 2026-09-23.md',
        'Investment-System1 · CURRENT_HANDOFF.md',
        'Investment-System1 · Contract Conflict Register 2026-09-23.md',
        'Investment-System1 · HANDOFF_HISTORY.md',
        'Investment-System1 · Master Status Index 2026-09-22.md',
        'implementation/reports/track_c_decision_register_2026-10-01.md'}
    unexpected=[p for p in prior if prior[p]!=current.get(p) and p not in allowed_existing]
    if unexpected: raise ValueError('historical/proposal/protected evidence changed: '+repr(unexpected))
    unexpected_new=[p for p in current if p not in prior and p not in NEW_FILES
        and p!='implementation/tools/track_c_c7_acceptance.py'
        and not p.startswith('implementation/reports/track_c_')]
    if unexpected_new: raise ValueError('new unauthorized files: '+repr(unexpected_new))
    return {'status':'PASS','frozen_source_tests_preserved':len(frozen),
        'existing_source_tests_changed':changed,'unexpected_changes':unexpected,
        'historical_A_B_and_inactive_packages':'PRESERVED_BY_BLOB_IDENTITY',
        'boundary':boundary_audit()}

if __name__=='__main__':
    out=Path('reports/track_c_c7_generated');out.mkdir(parents=True,exist_ok=False)
    audit=preservation()
    result=full_acceptance(out/'integrated')
    # Full registrations, every C5/C6 attempt and all C4/C6/C7 reports persist in artifact.
    stages=json.loads((out/'integrated'/'selection'/'selection-report.json').read_text())['output']['stages']
    mandatory={s:'PASS' if any(row['stage']==s for row in stages) else 'FAIL' for s in STAGES}
    if result['acceptance']['status']!='PASS' or set(mandatory.values())!={'PASS'}:
        raise SystemExit('C7 software acceptance blocked')
    evidence={'scope':'SYNTHETIC_SOFTWARE_VALIDATION',
        'configuration_scope':'SYNTHETIC_SOFTWARE_VALIDATION_ONLY','status':'PASS',
        'tested_head':git('rev-parse','HEAD'),'mandatory':mandatory,'integrated':result,
        'preservation':audit,'PIT_no_lookahead':'PASS_CURRENT_C4_C5_C6_C7_RESOLUTION',
        'lineage_provenance':'PASS_CURRENT_ANCESTOR_AND_ALL_STAGE_HASH_RESOLUTION',
        'holdout_state':'UNCONSUMED_NO_READER','real_pit_research_validation':'NOT_RUN_MISSING_COMPLETE_REAL_FAMILY',
        'Investor_QGV':'FUTURE_TRACK_C_INPUT','packages_A_B_C':'PROPOSED_NOT_APPROVED_NOT_ACTIVE',
        'official':False,'tax_mode':'EXCLUDED',
        'negative_paths':'VERIFIED_BY_TARGETED_C7_AND_PREVIOUS_PHASE_TESTS'}
    (out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('TRACK_C_C7_EVIDENCE='+json.dumps(evidence,sort_keys=True,separators=(',',':')))
