import hashlib, importlib.util, json, shutil, subprocess, tempfile
from pathlib import Path

repo = Path('/workspace/Investment-System1')
worktree = Path('/workspace/shared-source-hardening')
evidence = Path('/workspace/takeover-evidence/shared-source-hardening-review')
helper = worktree / 'implementation/tools/producer_source_compat.py'
spec = importlib.util.spec_from_file_location('independently_reviewed_compat', helper)
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
inventory = json.loads((evidence / 'source_inventory.json').read_text())
shared = tuple(r['path'] for r in inventory['files'])
nonmodels = tuple(r['path'] for r in inventory['files'] if not r['models_exception'])
baseline = inventory['canonical_baseline']

def git(*args, cwd=repo):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(cwd),*args], stderr=subprocess.PIPE)

def original(rel):
    return git('show', baseline + ':implementation/src/' + rel)

def populate(root, adopted=True):
    for rel in shared:
        body = (worktree / 'implementation/src' / rel).read_bytes() if adopted and rel == compat.MODELS else original(rel)
        path=root/rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

cases=[]
def record(name, result, expected, **extra):
    actual=result['status']
    assert actual == expected, (name,actual,expected)
    cases.append({'case':name, 'expected':expected, 'actual':actual, 'accepted':True, **extra})

with tempfile.TemporaryDirectory(prefix='probe-', dir=evidence) as task_tmp:
    task = Path(task_tmp)
    source=task/'source'
    populate(source)
    record('adopted models with ten original protected sources',compat.compare_shared_sources(source,source,shared),'PASS')
    canonical=task/'canonical'
    populate(canonical,adopted=False)
    record('all canonical source controls',compat.compare_shared_sources(canonical,canonical,shared),'PASS')
    for rel in nonmodels:
        path=source/rel
        clean=path.read_bytes()
        path.write_bytes(clean+b'\n# independent unrelated mutation\n')
        result=compat.compare_shared_sources(source,source,shared)
        assert result['files'][rel]['own'] == result['files'][rel]['infra']
        assert result['files'][rel]['baseline_sha256'] == next(r['canonical_sha256'] for r in inventory['files'] if r['path']==rel)
        assert result['files'][rel]['status']=='FAIL'
        assert all(detail['status']=='PASS' for name,detail in result['files'].items() if name != rel)
        record('dirty same-tree '+rel,result,'FAIL',failed_path=rel)
        path.write_bytes(clean)
    rel=nonmodels[0]
    path=source/rel
    clean=path.read_bytes()
    path.unlink()
    record('missing current same-tree file',compat.compare_shared_sources(source,source,shared),'FAIL',failed_path=rel)
    path.write_bytes(clean)
    alias=task/'alias'
    alias.symlink_to(source,target_is_directory=True)
    path.write_bytes(clean+b'\n# same resolved path via alias\n')
    record('same-resolved symlink alias mutation',compat.compare_shared_sources(source,alias,shared),'FAIL')
    path.write_bytes(clean)
    recorded_commit=compat.CANONICAL_SOURCE_COMMIT
    compat.CANONICAL_SOURCE_COMMIT='0'*40
    result=compat.compare_shared_sources(source,source,shared)
    assert all(result['files'][rel]['baseline_available'] is False for rel in nonmodels)
    assert result['files'][compat.MODELS]['status']=='PASS'
    record('missing Git object no fallback',result,'FAIL')
    compat.CANONICAL_SOURCE_COMMIT=recorded_commit
    recorded_prefix=compat.CANONICAL_SOURCE_PREFIX
    compat.CANONICAL_SOURCE_PREFIX='no-such-path/'
    record('missing baseline source path no fallback',compat.compare_shared_sources(source,source,shared),'FAIL')
    compat.CANONICAL_SOURCE_PREFIX=recorded_prefix
    recorded_run=compat.subprocess.run
    def absent_git(*args,**kwargs):
        raise FileNotFoundError('independent simulated unavailable Git')
    compat.subprocess.run=absent_git
    record('Git unavailable is structured failure',compat.compare_shared_sources(source,source,shared),'FAIL')
    compat.subprocess.run=recorded_run
    external=task/'external'
    populate(external,adopted=False)
    result=compat.compare_shared_sources(source,external,shared)
    assert all(result['files'][rel]['mode']=='BYTE_IDENTICAL' for rel in nonmodels)
    record('external exact mixed old/adopted models',result,'PASS')
    extfile=external/nonmodels[0]
    extfile.write_bytes(extfile.read_bytes()+b'\n# external mismatch\n')
    record('external unequal bytes remain rejected',compat.compare_shared_sources(source,external,shared),'FAIL')
    # The helper-owned repository must override a caller's unrelated Git repository.
    caller=task/'caller'; caller_src=caller/'implementation/src'; populate(caller_src)
    git('init','-q',cwd=caller)
    git('config','user.name','Independent review fixture',cwd=caller)
    git('config','user.email','review-fixture@example.invalid',cwd=caller)
    (caller_src/nonmodels[0]).write_bytes(original(nonmodels[0])+b'\n# unrelated caller baseline\n')
    git('add','.',cwd=caller); git('commit','-qm','Disposable caller fixture',cwd=caller)
    record('caller Git HEAD cannot substitute helper baseline',compat.compare_shared_sources(caller_src,caller_src,shared),'FAIL')
    # Only this disposable fixture gets replacement refs; the original repository is unchanged.
    replacement=task/'replacement-fixture'; replacement.mkdir()
    git('init','-q',cwd=replacement)
    git('config','user.name','Independent review fixture',cwd=replacement)
    git('config','user.email','review-fixture@example.invalid',cwd=replacement)
    replace_src=replacement/'implementation/src'; populate(replace_src)
    git('add','.',cwd=replacement); git('commit','-qm','Original fixture object',cwd=replacement)
    fixture_original=git('rev-parse','HEAD',cwd=replacement).decode().strip()
    file=replace_src/nonmodels[0]; file.write_bytes(file.read_bytes()+b'\n# replacement fixture content\n')
    git('add','.',cwd=replacement); git('commit','-qm','Replacement fixture object',cwd=replacement)
    fixture_modified=git('rev-parse','HEAD',cwd=replacement).decode().strip()
    git('replace',fixture_original,fixture_modified,cwd=replacement)
    normal=subprocess.check_output(['git','-C',str(replacement),'show',fixture_original+':implementation/src/'+nonmodels[0]])
    assert normal==file.read_bytes(), 'ordinary Git lookup must demonstrate replacement override'
    recorded_file=compat.__file__
    compat.__file__=str(replacement/'implementation/tools/producer_source_compat.py')
    compat.CANONICAL_SOURCE_COMMIT=fixture_original
    result=compat.compare_shared_sources(replace_src,replace_src,(nonmodels[0],))
    assert result['files'][nonmodels[0]]['baseline_sha256']==hashlib.sha256(original(nonmodels[0])).hexdigest()
    record('local replacement ref ignored for exact baseline',result,'FAIL',disposable_fixture_only=True)
    compat.__file__=recorded_file; compat.CANONICAL_SOURCE_COMMIT=recorded_commit

report={'reviewed_helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'source_base':inventory['source_head'],'canonical_baseline':baseline,'cases':cases,'case_count':len(cases),'all_expected_results_matched':all(c['accepted'] for c in cases),'protected_source_written':False,'original_repository_ref_mutations':False,'external_actions':'NOT_RUN'}
p=evidence/'independent_results.json';p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cases':len(cases),'all_expected_results_matched':True,'helper_sha256':report['reviewed_helper_sha256'],'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
