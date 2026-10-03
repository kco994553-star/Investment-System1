import ast, hashlib, json, os, subprocess, sys
from pathlib import Path

repo=Path('/workspace/Investment-System1')
out=Path('/workspace/takeover-evidence/adoption')
track='origin/ccr-22e3ff16-p7n5k5'
pairs=[('pr11-technical-producer','technical_real_producer','feature/technical-real-producer-v1','test_technical_real_producer.py'),
('pr12-macro-producer','macro_real_producer','feature/macro-real-producer-v1','test_macro_real_producer.py'),
('pr14-leaderboard','leaderboard_real_producer','feature/leaderboard-real-producer-v1','test_leaderboard_real_producer.py'),
('pr15-technical-model','technical_real_model','feature/technical-real-model-v1','test_technical_real_model_v1.py'),
('pr17-p01','research_publication','feature/p01-research-publication-v1','test_p01_research_publication.py'),
('pr18-us-equity-session','us_equity_session','feature/us-equity-session-v1','test_us_equity_session_v1.py')]
def run(args,cwd=repo,env=None):
    p=subprocess.run(args,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {'command':args,'exit_code':p.returncode,'output':p.stdout}
def git(*args):
    r=run(['git',*args]);
    if r['exit_code']: raise RuntimeError(r)
    return r['output'].strip()
def compare(a,b,path='',diffs=None):
    if diffs is None: diffs=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for key in sorted(set(a)|set(b)):
            loc=f'{path}/{key}'
            if key not in a: diffs.append({'kind':'added','path':loc,'after':b[key]})
            elif key not in b: diffs.append({'kind':'removed','path':loc,'before':a[key]})
            else: compare(a[key],b[key],loc,diffs)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)): compare(x,y,f'{path}/{i}',diffs)
    elif type(a) is not type(b) or a != b: diffs.append({'kind':'changed','path':path,'before':a,'after':b})
    return diffs
records=[]
for short,scope,base,test in pairs:
    ref='origin/integration/a1-adoption/'+short
    work=Path('/workspace/adoption-audit-'+short.split('-')[0])
    if not work.exists():
        r=run(['git','worktree','add','--detach',str(work),ref]);
        if r['exit_code']: raise RuntimeError(r)
    record={'proposal':ref,'scope':scope,'HEAD':git('rev-parse',ref),'owner_base':base,'base_SHA':git('rev-parse','origin/'+base),
            'merge_base':git('merge-base',ref,'origin/'+base),'track_C_SHA':git('rev-parse',track),
            'changed_files':git('diff','--name-status','origin/'+base+'...'+ref).splitlines(),
            'maturity_before_after':'UNCHANGED (independent integration audit only)',
            'Actions_actually_executed':'NOT_RUN','BRANCH_STATE':'REMOTE_DRAFT_PROPOSAL_READ_ONLY',
            'INTEGRATION_STATE':'LOCAL_TRIAL_NOT_CANONICAL','CANONICAL_STATE':'NOT_MERGED'}
    own_source=git('diff','--name-only','origin/'+base+'...'+ref,'--','implementation/src')
    record['own_source_changes']=own_source.splitlines()
    impl=work/'implementation'; env={**os.environ,'PYTHONPATH':str(impl/'src')}
    for state in ['before','after']:
        if state=='after':
            merge=run(['git','-c','user.name=Codex Audit','-c','user.email=codex-audit@example.invalid','merge','--no-commit','--no-ff',track],work)
            (out/(short+'-merge.log')).write_text(merge['output'])
            record['merge_exit_code']=merge['exit_code']
            if merge['exit_code']: raise RuntimeError(merge)
            record['after_tree']=run(['git','write-tree'],work)['output'].strip()
        probe=run([sys.executable,str(out/'probe.py'),str(impl)],impl,env)
        (out/(short+'-'+state+'-probe.json')).write_text(probe['output'])
        record[state+'_probe_exit_code']=probe['exit_code']
        testresult=run([sys.executable,'-m','pytest','-q','tests/'+test],impl,env)
        filename=short+'-'+state+'-pytest.log'
        (out/filename).write_text(testresult['output'])
        record[state+'_tests']={'exit_code':testresult['exit_code'],'summary':testresult['output'].splitlines()[-1] if testresult['output'] else '', 'log':filename,
                               'sha256':hashlib.sha256(testresult['output'].encode()).hexdigest()}
        print(short,state,record[state+'_tests']['summary'],flush=True)
    before=json.loads((out/(short+'-before-probe.json')).read_text()); after=json.loads((out/(short+'-after-probe.json')).read_text())
    diffs=compare(before,after)
    fields={'available_at','data_stamp_refs','source_vintages','input_hash'}
    unexpected=[d for d in diffs if not (d['kind']=='added' and d['path'].split('/')[-1] in fields and d['after'] in [None,[]]) and not d['path'].startswith('/fingerprints/')]
    fingerprint_changes=[d for d in diffs if d['path'].startswith('/fingerprints/')]
    unexpected += [d for d in fingerprint_changes if d['path'].split('/')[-1] not in {'technical','macro'}]
    record['field_level_comparison']={'changes':len(diffs),'lineage_additions':len(diffs)-len(fingerprint_changes),
                                      'fingerprint_changes':fingerprint_changes,'unexpected':unexpected,
                                      'verdict':'PASS' if not unexpected else 'FAIL'}
    record['probe_artifact_sha256']={s:hashlib.sha256((out/(short+'-'+s+'-probe.json')).read_bytes()).hexdigest() for s in ['before','after']}
    source=[]
    for rel in ['contracts/models.py','technical/engine.py','macro/engine.py','contracts/lineage.py']:
        full='implementation/src/investment_system/'+rel
        before_bytes=subprocess.run(['git','show',ref+':'+full],cwd=repo,stdout=subprocess.PIPE).stdout
        after_bytes=(work/full).read_bytes()
        item={'path':full,'before_sha256':hashlib.sha256(before_bytes).hexdigest() if before_bytes else 'ABSENT','after_sha256':hashlib.sha256(after_bytes).hexdigest()}
        if rel.endswith('engine.py'):
            def method(payload):
                tree=ast.parse(payload)
                return next(ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='evaluate')
            item['legacy_evaluate_AST_identical']=method(before_bytes)==method(after_bytes)
        source.append(item)
    record['protected_source_impact']=source
    record['USER_DECISION_REQUIRED']='NO for existing approved adoption audit; canonical merge remains separate approval'
    records.append(record)
    (out/'results.json').write_text(json.dumps(records,indent=2))
print('completed',len(records),'proposals',flush=True)
