"""Independent scoped review from exact remote snapshot and read-only Git objects."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path('/workspace/Investment-System1')
OUT = Path('/workspace/takeover-evidence/c28-evidence-32-33')
SNAPSHOT = Path('/workspace/takeover-evidence/gsup-v2/REMOTE_FINAL_OBSERVATION.json')
GLOBAL = '6dedaaf36a417e9301ba22ea9595bff5f37acb38'
OWNER = 'b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565'
ADOPTED = ['contracts/lineage.py', 'contracts/models.py', 'technical/engine.py', 'macro/engine.py']
SEARCH = ['82165414','7bbfad69','d1b9cd91','112b245b','53d930a7','a1714480',
          'producer_engine_fingerprint','numeric_fingerprint','engine_numerical_fingerprint']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def text(*args):
    return git(*args).decode().strip()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relation(base, head):
    behind, ahead = map(int, text('rev-list','--left-right','--count',base+'...'+head).split())
    return {'base':base, 'head':head, 'merge_base':text('merge-base',base,head), 'ahead':ahead, 'behind':behind}


def main():
    snapshot = json.loads(SNAPSHOT.read_text())
    replay = json.loads((OUT/'independent-offline-fingerprint-replay.json').read_text())
    pulls = {p['number']:p for p in snapshot['pulls']}
    register = git('show', GLOBAL+':implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md').decode()
    cdr004 = register.split('## CDR-004 ·',1)[1].split('## CDR-005 ·',1)[0]
    words = [line[2:] for line in cdr004.splitlines() if line.startswith('> ')]
    results = {'workflow_id':'C28_EVIDENCE_ADOPTION_32_33_READONLY_2026_10_03',
               'baseline_remote_observed_at':snapshot['observed_at'],
               'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'remote_snapshot_sha256':sha(SNAPSHOT.read_bytes()),
               'workflow_baseline':{'canonical':'b8e39a2196a6d7794a04a0cd5393c68329e126ca',
                                    'global':GLOBAL, 'integration':'86ad3628dd5c62c6d873e42511e577f24f4fb588',
                                    'open_draft_prs':snapshot['open_pr_count'], 'branches':snapshot['remote_branch_count']},
               'separation':'These two external upstream Draft PRs add evidence only. They are neither Codex PR increments nor part of native G-SUP675 validation or its fixed prior baseline.',
               'reviewer_actions':'READ_ONLY_GIT_OBJECTS_AND_REMOTE_API; isolated tree exports and evidence writes only; no commits, refs, dispatch, source edits, full-suite runs, CAL_VERIFY or Holdout',
               'criteria':{}, 'proposals':{}}
    for number, domain, note, expected_lines in [(32,'producer_infrastructure','STATUS.md',18), (33,'entity_metadata','HANDOFF.md',17)]:
        pr = pulls[number]; base = pr['base']['sha']; head = pr['head']['sha']
        assert pr['state']=='open' and pr['draft'] is True
        record_path=f'implementation/docs/{domain}/evidence/c28_adoption_post_adoption_2026-10-03.json'
        note_path=f'implementation/docs/{domain}/{note}'
        historical_path=f'implementation/docs/{domain}/evidence/validation.json'
        rawrecord=git('show', head+':'+record_path); record=json.loads(rawrecord)
        assert rawrecord==(OUT/f'pr{number}-adoption-record.json').read_bytes()
        assert record['authority']['cdr_004_full_user_wording_from_register']==words
        assert GLOBAL in record['authority']['register_location']
        rel=relation(base,head); assert rel['merge_base']==base and rel['ahead']==1 and rel['behind']==0
        assert text('show','-s','--format=%P',head)==base
        diff=text('diff','--name-status',base,head).splitlines()
        assert set(diff)=={'M\t'+note_path,'A\t'+record_path}
        oldnote=git('show',base+':'+note_path);newnote=git('show',head+':'+note_path)
        assert newnote.startswith(oldnote)
        assert len(newnote.splitlines())-len(oldnote.splitlines())==expected_lines
        assert git('show',base+':'+historical_path)==git('show',head+':'+historical_path)
        code_diff=text('diff','--name-only',base,head,'--','implementation/src','implementation/tests','implementation/tools','.github')
        assert not code_diff
        search=subprocess.run(['git','grep','-n','-E','|'.join(SEARCH),base,'--','implementation/tests'],cwd=REPO,capture_output=True)
        assert search.returncode==1 and not search.stdout
        before_tree=text('rev-parse',base+'^{tree}'); assert before_tree==record['trees']['before']['tree']
        merged=subprocess.run(['git','merge-tree','--write-tree','--messages',base,OWNER],cwd=REPO,capture_output=True,text=True)
        assert merged.returncode==0
        after_tree=merged.stdout.splitlines()[0]
        assert after_tree==record['trees']['after']['throwaway_merge_tree']
        blob_identity={p:{'after_blob':text('rev-parse',after_tree+':implementation/src/investment_system/'+p),
                          'owner_blob':text('rev-parse',OWNER+':implementation/src/investment_system/'+p)} for p in ADOPTED}
        assert all(v['after_blob']==v['owner_blob'] for v in blob_identity.values())
        generator_path=record['generator']['path']
        assert git('show',base+':'+generator_path)==git('show',head+':'+generator_path)==git('show',after_tree+':'+generator_path)
        assert replay[str(number)]['before']['tool_sha256']==record['generator']['sha256_before']
        assert replay[str(number)]['after']['tool_sha256']==record['generator']['sha256_after']
        if number==32:
            before=json.loads((OUT/'pr32-before-stdout-1.json').read_text()); after=json.loads((OUT/'pr32-after-stdout-1.json').read_text())
            f=record['engine_numerical_fingerprint']
            assert before==f['before_reproduced']==f['pre_adoption_committed_in_validation_json']
            assert after==f['after_post_adoption']
            fingerprints={'before':before,'after':after,'92_lineage_additions_only':True,
                          'stripped_exactly_restores_before':replay['32']['stripped_equals_before'],
                          'known_technical_macro_pair_match':after['technical']=='66cb23830d65d1867df895a52d6cf3adef52c84a8ee2645d2c06617711a5e655' and after['macro']=='7e427949a4c15ebaf78304cfec2d7a952f8bfec2a694371801ad90d09fe0c501'}
            a=json.loads((OUT/'pr32-actions-observed.json').read_text()); assert a['total_count']==0 and a['workflow_runs']==[]
            actions={'actual_independent_observation':'BRANCH_ALL_EVENT_MODES_QUERY_TOTAL0', 'Actions_executed_by_reviewer':'NOT_RUN',
                     'evidence':'pr32-actions-observed.json','qualification':'No proposal Actions observed; original owner TrackC Actions is separate exact-owner scope, not this proposal.'}
        else:
            f=record['numeric_fingerprint']; b=replay['33']['before']['stdout_sha256']; a=replay['33']['after']['stdout_sha256']
            assert b==f['before_reproduced_sha256_stdout'] and a==f['after_sha256_stdout']
            output_before=json.loads((OUT/'pr33-before-stdout-1.json').read_text());output_after=json.loads((OUT/'pr33-after-stdout-1.json').read_text())
            after_minus_fields=json.loads(json.dumps(output_after))
            for snap in after_minus_fields['technical'].values():
                for k in ('available_at','data_stamp_refs','source_vintages','input_hash'):del snap[k]
            for k in ('available_at','data_stamp_refs','source_vintages','input_hash'):del after_minus_fields['macro'][k]
            after_minus_reports=json.loads(json.dumps(output_after))
            for k in set(output_after['reports_sha256'])-set(output_before['reports_sha256']):del after_minus_reports['reports_sha256'][k]
            def h(v):return sha((json.dumps(v,sort_keys=True,ensure_ascii=False,default=str)+'\n').encode())
            assert h(after_minus_fields)==f['decomposition_of_after']['after_minus_four_keys_only']
            assert h(after_minus_reports)==f['decomposition_of_after']['after_minus_27_track_c_report_entries_only']
            fingerprints={'before_stdout_sha256':b,'after_stdout_sha256':a,'lineage_additions':44,'report_inventory_additions':27,
                          'existing_140_report_digests_unchanged':True,'all_existing_investment_fields_unchanged':True,
                          'minus_four_keys_only_sha256':h(after_minus_fields),'minus_report_additions_only_sha256':h(after_minus_reports),
                          'minus_both_exact_reconstructed_stdout_sha256':replay['33']['exact_reconstructed_stdout_sha256'],
                          'qualification':'The27 report inventory additions are separately disclosed tree additions, not C28 schema or changed existing numerical outputs.'}
            a=json.loads((OUT/'pr33-actions-exact-pr-observed.json').read_text());assert a['workflow_runs']==[]
            actions={'actual_independent_observation':'EXACT_COMMIT_PULL_REQUEST_RUNS_EMPTY_FIRST_PAGE_CONNECTOR',
                     'Actions_executed_by_reviewer':'NOT_RUN','evidence':'pr33-actions-exact-pr-observed.json',
                     'full_branch_query_status':'AUTHENTICATION_FAILED_HTTP401; raw response retained in pr33-actions-observed.json',
                     'other_event_modes':'Initially NOT_OBSERVED_INDEPENDENTLY; see separately attributed root receipt below',
                     'qualification':'Owner declares Actions NOT_RUN. Connector observes no exact-commit PR-triggered runs; this does not prove absence of every push/dispatch mode. No failure relabeled as success.'}
        root_actions=OUT/f'PR{number}_ALL_BRANCH_ACTIONS_ROOT.json'
        root_observation=json.loads(root_actions.read_text())
        assert root_observation['total_count']==0 and root_observation['workflow_runs']==[]
        actions['root_observed_all_branch_event_modes']={'source':'Root executed gh API with additional network permission; this reviewer inspected exact raw receipt, did not reexecute it',
                                                        'file':root_actions.name,'sha256':sha(root_actions.read_bytes()),'total_count':0,'workflow_runs':[]}
        actions['current_classification']='NO_ACTIONS_OBSERVED_ALL_BRANCH_MODES_ROOT_RECEIPT; reviewer performed no dispatch'
        criteria={'1_exact_additive_paths_history_and_CDR004':'PASS','2_independent_fingerprint_and_existing_value_invariance':'PASS',
                  '3_validation_evidence_actual_observation_and_NOT_RUN_qualification':'PASS_WITH_DECLARED_VS_EXECUTED_SOURCE_ATTRIBUTION'}
        results['proposals'][str(number)]={'head_branch':pr['head']['ref'],'head':head,'owner_base_branch':pr['base']['ref'],
                    'relation':rel,'changed_paths':diff,'append_only_lines':expected_lines,'historical_validation_sha256':sha(git('show',base+':'+historical_path)),
                    'record_sha256':sha(rawrecord),'source_tests_tools_workflows_changed':[], 'existing_test_pin_search':'NO_MATCH_NO_REPIN',
                    'authority_register':GLOBAL,'CDR004_full_quote_exact':True,'reconstructed_after_tree':after_tree,
                    'declared_local_after_commit':record['trees']['after']['throwaway_merge_commit'],
                    'same_commit_claim':'NOT_MADE; independent reconstruction proves exact TREE identity, not identity of an unreferenced local commit',
                    'adopted_source_blobs_equal_exact_owner':blob_identity,'fingerprints':fingerprints,'criteria':criteria,
                    'declared_owner_tests_not_reexecuted':record['tests'],'owner_record_qualification':'JSON proposal validation described a pre-final-doc draft; exact proposal full-suite counts are declared in PR body. This reviewer did not rerun either full suite or shim and does not label declarations as own execution.',
                    'actual_reviewer_execution':{'fingerprint_generators':'EXECUTED_TWICE_EACH_BEFORE_AFTER_NATIVE_PYTHON3.11.16','normalized_field_replay':'EXECUTED','full_pytest':'NOT_RUN_DOCS_ONLY','mini_pytest':'NOT_RUN','Web_E2E':'NOT_RUN','dispatch':'NOT_RUN'},
                    'Actions':actions,'BRANCH_STATE':'REMOTE_DRAFT_EVIDENCE_ONLY_PROPOSAL','INTEGRATION_STATE':'NOT_MERGED_TO_OWNER_TRACKC_NOT_MERGED_IN_PROPOSAL',
                    'CANONICAL_STATE':'NOT_MERGED_UNCHANGED_b8','maturity_change':'NONE_DOCUMENTATION_AND_EVIDENCE_ONLY','blockers':['Owner adoption merge pending; no canonical merge authorized'],
                    'USER_DECISION_REQUIRED':'NONE_FOR_READ_ONLY_REVIEW','next_autonomous_action':'Primary Integration Writer may consume this exact independent review; retain owner proposal semantics and do not treat it as merged source adoption'}
        results['criteria'][str(number)]=criteria
    results['scoped_acceptance']='3/3 for each evidence-only proposal; no claim of merged adoption or full-suite independent rerun. Actual no-Actions observation includes root-attributed all-branch receipts for both proposals, not a successful workflow run.'
    results['artifacts']={p.name:sha(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()
                          and p.name not in {'FINAL_REVIEW.json','review-stdout.log','review-stderr.log'}}
    (OUT/'FINAL_REVIEW.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Scoped acceptance:',results['scoped_acceptance']);print('FINAL_REVIEW sha256:',sha((OUT/'FINAL_REVIEW.json').read_bytes()))


if __name__=='__main__':main()
