"""Read-only exact-SHA handoff checks; writes only this review directory."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
REPO = Path('/workspace/Investment-System1')
OUT = Path('/workspace/takeover-evidence/pr31-handoff/handoff-gap-review')
SOURCE = '675d0d298fbaab5b8473ed048a561ef84e2f3e78'
OWNER = 'b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565'
BASE = '86ad3628dd5c62c6d873e42511e577f24f4fb588'
GLOBAL = '994eb114ef14838d09d6233cfd2367d4d19738e2'
APPROVAL = 'implementation/reports/track_c_c8_gsup_v2_source_identity_approval_2026-10-03.json'
REGISTER = 'implementation/reports/track_c_decision_register_2026-10-01.md'


def git(*args):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(REPO),*args])


def show(ref,path):
    return git('show',ref+':'+path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tree(ref):
    result = {}
    for entry in git('ls-tree','-rz',ref).split(b'\0'):
        if entry:
            header,path = entry.split(b'\t',1)
            mode,kind,oid = header.decode().split()
            result[path.decode()] = oid
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate-root',default='/workspace/gsup-v2-integration');ap.add_argument('--output',default='BOUNDED_CHECKS_SOURCE675.json')
    args=ap.parse_args();candidate=Path(args.candidate_root)
    before=tree(SOURCE);owner=tree(OWNER);base=tree(BASE)
    existing=[p for p in base if p.startswith('implementation/src/') or p.startswith('implementation/tests/')]
    assert all(before.get(p)==base[p] for p in existing)
    existing_owner_evl=[p for p in owner if p.startswith('implementation/src/investment_system/evl/')]
    assert all(before.get(p)==owner[p] for p in existing_owner_evl)
    approval_blob=git('rev-parse',SOURCE+':'+APPROVAL).decode().strip();assert approval_blob=='a5279d516c028f0a8cb9166ee2d54366da00877b'
    approval=json.loads(show(SOURCE,APPROVAL));assert approval['method']['numeric_configuration']=='NOT_APPROVED'
    assert approval['source_identity']['status']=='APPROVED_SYNTHETIC_SOFTWARE_VALIDATION_ONLY'
    assert show(SOURCE,REGISTER).startswith(show(OWNER,REGISTER))
    wrapper=ast.parse(show(SOURCE,'implementation/src/investment_system/evl/superiority_source_identity.py'))
    cls=next(n for n in wrapper.body if isinstance(n,ast.ClassDef) and n.name=='IdentityBoundGsupRegistry')
    numeric_methods=['_validate_spec','_feasibility','_evaluate','_result']
    for method in numeric_methods:
        n=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==method)
        assert len(n.body)==1 and isinstance(n.body[0],ast.Return)
        call=n.body[0].value;assert isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.value.id=='legacy'
    assert 'implementation/src/investment_system/evl/gsup_mb_v2.py' not in before
    hashes={p:{'git_blob':before[p],'sha256':sha(show(SOURCE,p))} for p in [APPROVAL,REGISTER,
            'implementation/src/investment_system/evl/gsup_source_identity.py',
            'implementation/src/investment_system/evl/superiority_source_identity.py',
            'implementation/src/investment_system/evl/superiority.py',
            'implementation/tests/test_evl_gsup_source_identity.py',
            'implementation/tests/test_evl_gsup_v2_identity_adversarial.py',
            'implementation/tests/test_evl_gsup_identity_kernel_invariance.py',
            'implementation/tests/test_evl_gsup_mb_reduction_diagnostic.py',
            'implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.json',
            'implementation/reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_REVIEW_2026-10-03.md',
            'implementation/reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_TRACES_2026-10-03.json']}
    junit=Path('/workspace/takeover-evidence/gsup-v2/actions-review/37106686279/artifact11268415800/combined-junit.xml')
    xml=ET.parse(junit).getroot();suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
    counts={k:int(suite.attrib[k]) for k in ['tests','failures','errors','skipped']};assert counts=={'tests':1277,'failures':0,'errors':0,'skipped':0}
    groups={}
    for case in suite.findall('testcase'):
        name=case.attrib.get('classname','')
        if any(name.endswith(n) for n in ['test_evl_gsup_source_identity','test_evl_gsup_v2_identity_adversarial','test_evl_gsup_identity_kernel_invariance','test_evl_gsup_mb_reduction_diagnostic']):
            assert not list(case.findall('failure')) and not list(case.findall('error')) and not list(case.findall('skipped'))
            groups[name]=groups.get(name,0)+1
    expected={'tests.test_evl_gsup_source_identity':33,'tests.test_evl_gsup_v2_identity_adversarial':48,
              'tests.test_evl_gsup_identity_kernel_invariance':11,'tests.test_evl_gsup_mb_reduction_diagnostic':20};assert groups==expected
    changed_existing=[]
    for p in before:
        if p.startswith(('implementation/src/','implementation/tests/','.github/workflows/')) or p.endswith('.json') and p.startswith('implementation/reports/'):
            if not (candidate/p).is_file() or (candidate/p).read_bytes()!=show(SOURCE,p):changed_existing.append(p)
    assert not changed_existing
    baseline_reports={p:sha(show(SOURCE,p)) for p in before if p.startswith('implementation/reports/') and p.endswith('.json')}
    candidate_reports={str(p.relative_to(candidate)):sha(p.read_bytes()) for p in sorted((candidate/'implementation/reports').rglob('*.json'))}
    assert candidate_reports==baseline_reports
    sys.path.insert(0,str(candidate/'implementation/src'))
    from investment_system.evl.superiority import studentized_cbb
    fixture=json.loads(show(SOURCE,'implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.json'))['CE4_decision_flip_L_not_dividing_n']
    legacy=studentized_cbb(fixture['data'],block_length=fixture['L'],replicates=fixture['B'],seed=fixture['seed'])
    actual={'p':legacy['p_value'],'r':legacy['exceedances'],'degenerate':legacy['degenerate_replicates']};assert actual==fixture['kernel']
    result={'review_source':SOURCE,'base':BASE,'owner':OWNER,'Global_routing':GLOBAL,'source_manifest':hashes,
            'integration_existing_source_test_blobs_unchanged':len(existing),'owner_existing_evl_source_blobs_unchanged':len(existing_owner_evl),
            'approval_blob_exact':approval_blob,'approved_scope':'SYNTHETIC_SOURCE_IDENTITY_ONLY; M choice approved, reduction/kernel activation deferred',
            'wrapper_numeric_methods':'Exact thin legacy delegation, no new kernel or default','authoritative_M_v2_module_present':False,
            'existing_source_test_workflow_reportJSON_candidate_differences':changed_existing,
            'report_JSON_inventory':{'entries':len(baseline_reports),'before_equals_candidate':True,'sha256':sha(json.dumps(baseline_reports,sort_keys=True,separators=(',',':')).encode()),'new_report_JSON_entries':[]},
            'candidate_root':str(candidate),'candidate_local_git_HEAD':subprocess.check_output(['git','-C',str(candidate),'rev-parse','HEAD'],text=True).strip(),
            'native_CI_artifact_reparsed_not_rerun':{'junit_sha256':sha(junit.read_bytes()),'exact_source':SOURCE,'counts':counts,'groups':groups},
            'bounded_actual_legacy_counterexample_execution':{'fixture':'CE4','actual':actual,'historical_MB_record':fixture['MB'],'meaning':'Reproduces preserved v1 p.15; historical M p.10 is evidence, not active new v2 or selected arithmetic'},
            'tests_actually_executed':'One fixed synthetic legacy kernel function; bounded source/AST/blob/prefix/CI-artifact/inventory checks, no full suite',
            'Actions_actually_executed':'NOT_RUN_BY_THIS_REVIEWER','real_CAL_VERIFY':'NOT_ACCESSED','Holdout':'UNCONSUMED','canonical_merge':'NOT_RUN'}
    (OUT/args.output).write_text(json.dumps(result,indent=2)+'\n');print('Bounded checks PASS; source/reportinventory/approval preserved; native675 JUnit reparsed; legacyCE4 p.15 reproduced')


if __name__=='__main__':main()
