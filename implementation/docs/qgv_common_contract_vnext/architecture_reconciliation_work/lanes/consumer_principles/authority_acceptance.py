"""Bounded inactive approval-to-contract verifier. Never evaluates a factor/result.

Expected clause obligations are taken from the immutable approved package.
Negative cases test authority expansion at this audit artifact boundary only.
They do not constitute production enforcement, factor binding or numeric policy.
"""
import copy
import hashlib
import json
from pathlib import Path

EXPECTED = {
    'B2':['dated_subject_context','predeclared_predicate_input_scope','separate_na_proof_and_denominator_permission'],
    'B3':['exact_method_input_source_pit_refs','preserved_original_reason_and_affected_scope','no_unresolved_or_rejected_to_affirmative_promotion'],
    'B5':['independent_producer_owned_assessments','exact_result_context_binding','numeric_existence_is_not_validity_confidence_or_completeness'],
    'B6':['same_exact_producer_refs','separate_consumer_purpose_cohort_admission','diagnostic_structure_does_not_grant_eligibility'],
}
EXCLUSIONS = {'numeric_policy','individual_factor_binding','runtime_activation','score_history_migration','canonical_merge'}

class ScopeError(ValueError): pass
def require(ok, code):
    if not ok: raise ScopeError(code)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def validate(approval_bytes, package_bytes, mapping):
    approval=json.loads(approval_bytes)
    require(approval['status']=='APPROVED_SEMANTIC_CONTRACT_PRINCIPLES_ONLY','APPROVAL_SCOPE')
    require(approval['decision_package']['head']=='16f58f20a29516e45e202aee7d3b27b8a1378d5c','PACKAGE_HEAD')
    require(blob(package_bytes)==approval['decision_package']['git_blob_sha']=='ab1ec644610ab3536f21fa8093bc4cc338c4431a','PACKAGE_IDENTITY')
    pref=approval['decision_package']['ref']
    require(digest(package_bytes)==pref['sha256'],'PACKAGE_BYTES')
    require(set(mapping['approval_ref'])=={'id','version','sha256','locator'},'REFERENCE_SHAPE')
    require(mapping['approval_ref']['sha256']==digest(approval_bytes),'EXACT_APPROVAL_REFERENCE')
    require(mapping['approval_ref']['id']==approval['approval_id'] and mapping['approval_ref']['version']=='1.0','APPROVAL_IDENTITY')
    require(mapping['approval_ref']['locator'].endswith('/lanes/consumer_principles/approval.json'),'APPROVAL_LOCATOR')
    require(mapping['package_ref']==pref,'SAME_APPROVED_PACKAGE_REFERENCE')
    require(set(approval['clauses'])==set(mapping['approved_clauses'])==set(EXPECTED),'CLAUSE_INVENTORY')
    require(set(approval['excluded'])==EXCLUSIONS,'USER_EXCLUSIONS')
    for key, expected in EXPECTED.items():
        source=approval['clauses'][key]; compiled=mapping['approved_clauses'][key]
        require(source['status']=='APPROVED_SEMANTIC_CONTRACT_PRINCIPLES_ONLY','CLAUSE_APPROVAL_SCOPE')
        require(source['obligations']==compiled['required_declarations']==expected,'PRINCIPLE_OBLIGATION_DRIFT')
        require(compiled['principle']==source['principle'] and compiled['excluded']==source['excluded'],'CLAUSE_CONTENT_DRIFT')
        require(compiled['concrete_authority_status']=='NOT_APPROVED','CONCRETE_AUTHORITY_PROMOTION')
        binding=mapping['per_clause_binding'][key]
        require(binding=={'scope':'CONTRACT_PRINCIPLES_ONLY','concrete_policy_ref':None,'factor_bindings':[], 'assessment_status':'UNASSESSED','consumer_admission':'NOT_EVALUATED'},'INDIVIDUAL_BINDING_OR_ASSESSMENT_PROMOTION')
    for record in (approval,mapping):
        require(record['numeric_policy'] is None,'NUMERIC_POLICY_FORBIDDEN')
        require(record['factor_bindings']==[],'INDIVIDUAL_FACTOR_BINDING_FORBIDDEN')
        for flag in ('runtime_enabled','activation_authorized','score_history_migration_authorized','canonical_merge_authorized'):
            require(record[flag] is False,'PROTECTED_AUTHORITY_EXPANSION')
        require(record['V2']=={'metadata_alignment':'ALREADY_D1_D2','assessment_reference_scope_principles':'APPROVED_WITH_B5_B6','actual_assessment_methodology':'NOT_APPROVED'},'V2_SCOPE_COLLAPSE')
    require(mapping['semantic_validity']=='NOT_EVALUATED' and mapping['consumer_admission']=='NOT_EVALUATED','RESULT_PROMOTION')
    require(mapping['consumer_eligibility']=={'ranking':False,'portfolio':False,'publication':False},'ELIGIBILITY_PROMOTION')
    return {'contract_binding':'PASS','semantic_validity':'NOT_EVALUATED','consumer_admission':'NOT_EVALUATED','runtime_enabled':False}

def run(root):
    approval=(root/'approval.json').read_bytes()
    # Local frozen intake or original sibling package in the published repo.
    candidates=[root.parent/'DECISION_PACKAGE.input.md',root.parent/'semantic/root/DECISION_PACKAGE.md']
    package=next(p for p in candidates if p.is_file()).read_bytes()
    mapping=json.loads((root/'OBLIGATION_MAP.json').read_text())
    cases=[]
    def case(name, fn, expected=None):
        try:
            value=fn(); actual='PASS'; observation=value
        except ScopeError as e:
            actual=str(e); observation=None
        cases.append({'case':name,'expected':expected or 'PASS','actual':actual,'pass':actual==(expected or 'PASS'),'observation':observation})
    case('approved_package_to_obligations',lambda:validate(approval,package,mapping))
    def mutation(name, fn, code):
        clone=copy.deepcopy(mapping); fn(clone)
        case(name,lambda:validate(approval,package,clone),code)
    case('different_package_bytes',lambda:validate(approval,package+b'\n',mapping),'PACKAGE_IDENTITY')
    edited=json.loads(approval); edited['recorded_at_kst']='ALTERED'
    case('coherently_parsed_but_unpinned_approval',lambda:validate(json.dumps(edited).encode(),package,mapping),'EXACT_APPROVAL_REFERENCE')
    mutation('stale_approval_id',lambda x:x['approval_ref'].update(id='OTHER'),'APPROVAL_IDENTITY')
    mutation('wrong_approval_locator',lambda x:x['approval_ref'].update(locator='fixture://other'),'APPROVAL_LOCATOR')
    mutation('different_package_reference',lambda x:x['package_ref'].update(version='OTHER'),'SAME_APPROVED_PACKAGE_REFERENCE')
    mutation('drop_B2_clause',lambda x:x['approved_clauses'].pop('B2'),'CLAUSE_INVENTORY')
    mutation('B2_na_proof_merged_with_denominator',lambda x:x['approved_clauses']['B2']['required_declarations'].pop(),'PRINCIPLE_OBLIGATION_DRIFT')
    mutation('B3_rejected_promoted_to_affirmative',lambda x:x['approved_clauses']['B3']['required_declarations'].pop(),'PRINCIPLE_OBLIGATION_DRIFT')
    mutation('B5_numeric_existence_implies_validity',lambda x:x['approved_clauses']['B5']['required_declarations'].pop(),'PRINCIPLE_OBLIGATION_DRIFT')
    mutation('B6_diagnostic_implies_consumer_right',lambda x:x['approved_clauses']['B6']['required_declarations'].pop(),'PRINCIPLE_OBLIGATION_DRIFT')
    mutation('B5_concrete_method_approved',lambda x:x['approved_clauses']['B5'].update(concrete_authority_status='APPROVED'),'CONCRETE_AUTHORITY_PROMOTION')
    mutation('individual_factor_binding',lambda x:x.update(factor_bindings=['UNAUTHORIZED']),'INDIVIDUAL_FACTOR_BINDING_FORBIDDEN')
    mutation('concrete_B2_policy_binding',lambda x:x['per_clause_binding']['B2'].update(concrete_policy_ref='UNAUTHORIZED'),'INDIVIDUAL_BINDING_OR_ASSESSMENT_PROMOTION')
    mutation('UNASSESSED_promoted_VALID',lambda x:x['per_clause_binding']['B3'].update(assessment_status='VALID'),'INDIVIDUAL_BINDING_OR_ASSESSMENT_PROMOTION')
    mutation('numeric_default_adoption',lambda x:x.update(numeric_policy={'cutoff':'UNAUTHORIZED'}),'NUMERIC_POLICY_FORBIDDEN')
    for flag in ('runtime_enabled','activation_authorized','score_history_migration_authorized','canonical_merge_authorized'):
        mutation(flag,lambda x,f=flag:x.update({f:True}),'PROTECTED_AUTHORITY_EXPANSION')
    mutation('V2_methodology_inferred_approved',lambda x:x['V2'].update(actual_assessment_methodology='APPROVED'),'V2_SCOPE_COLLAPSE')
    mutation('consumer_validity_inferred_from_contract',lambda x:x.update(semantic_validity='VALID'),'RESULT_PROMOTION')
    for purpose in ('ranking','portfolio','publication'):
        mutation('eligibility_'+purpose,lambda x,p=purpose:x['consumer_eligibility'].update({p:True}),'ELIGIBILITY_PROMOTION')
    out={'scope':'INACTIVE_APPROVAL_TO_OBLIGATION_ONLY','verification_lane':'STANDARD_WITH_INDEPENDENT_PRINCIPLE_REVIEW','checks':len(cases),'passed':sum(x['pass'] for x in cases),'cases':cases,'approval_sha256':digest(approval),'mapping_sha256':digest((root/'OBLIGATION_MAP.json').read_bytes()),'validator_sha256':digest(Path(__file__).read_bytes()),'old_tests_rerun':0,'production_enforcement':'NOT_IMPLEMENTED','real_PIT_OOS':'NOT_RUN','semantic_validity':'NOT_EVALUATED','consumer_admission':'NOT_EVALUATED','runtime_enabled':False}
    (root/'AUTHORITY_ACCEPTANCE_RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    require(out['passed']==out['checks'],'FAILED_ACCEPTANCE')
    print(json.dumps({'checks':out['checks'],'passed':out['passed'],'production_enforcement':out['production_enforcement']}))

if __name__=='__main__': run(Path(__file__).resolve().parent)
