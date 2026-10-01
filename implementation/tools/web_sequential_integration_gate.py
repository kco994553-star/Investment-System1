"""Reproduce canonical -> PR5 -> PR6 using temporary real git normal merges."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

PINS = {"canonical":"b8e39a2196a6d7794a04a0cd5393c68329e126ca","pr5":"a4e49c83f5783c19617fb609b8f95b179cb13e84","pr6":"eda65bf5d9203aee05f4d28992d1ccfcd815ebd4","trackCAtStart":"88da6f30560c4a2aee281a4cc45760eb3e0f4e80"}
ALLOWED = set([".github/workflows/web-mvp-validation.yml","implementation/docs/web_mvp/CONTRACT.md","implementation/docs/web_mvp/README.md","implementation/docs/web_mvp/STATUS.md","implementation/docs/web_mvp/evidence/browser.json","implementation/src/investment_system/product/web_assets/app.js","implementation/src/investment_system/product/web_assets/index.html","implementation/src/investment_system/product/web_assets/network-bridge.js","implementation/src/investment_system/product/web_assets/network-style.css","implementation/src/investment_system/product/web_assets/research-bridge.js","implementation/src/investment_system/product/web_assets/research-style.css","implementation/src/investment_system/product/web_assets/style.css","implementation/src/investment_system/product/web_mvp.py","implementation/tests/test_web_mvp.py","implementation/tools/build_web_mvp_demo.py","implementation/tools/web_mvp_browser_test.js","implementation/docs/global_language_search/CONTRACT.md","implementation/docs/global_language_search/STATUS.md","implementation/docs/global_language_search/evidence/validation.json","implementation/src/investment_system/product/entity_catalog.py","implementation/src/investment_system/product/web_assets/entity-search.js","implementation/src/investment_system/product/web_assets/locale.js","implementation/tests/test_global_language_search.py","implementation/tools/global_language_search_browser_test.js","implementation/tools/global_language_search_test.js"])
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'integration-evidence'
OUT.mkdir(exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix='web-sequential-', dir=os.environ['RUNNER_TEMP']))
REPLAY = WORK / 'worktree'
KST = timezone(timedelta(hours=9))
ENV = dict(os.environ, NODE_PATH=str(ROOT / 'node_modules'))
report = {'started_kst': datetime.now(KST).isoformat(), 'pins': PINS, 'stages': {},
          'scope': 'WEB_INTEGRATION_ONLY; public synthetic fixtures; no real producer/deployment readiness'}
def run(args, cwd=ROOT, filename=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env or ENV, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if filename:
        Path(filename).write_text(result.stdout, encoding='utf-8')
    print(result.stdout, flush=True)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {args}')
    return result.stdout.strip()
def git(*args, cwd=ROOT):
    return run(['git', *args], cwd)
def save():
    (OUT / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('INTEGRATION_SUMMARY_JSON=' + json.dumps(report, ensure_ascii=False), flush=True)
def junit(path):
    suites = ET.parse(path).getroot().iter('testsuite')
    counts = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, 0))
    assert counts['tests'] > 0 and counts['failures'] == counts['errors'] == counts['skipped'] == 0, counts
    return counts
def preserve(stage):
    changed = git('diff', '--name-only', PINS['canonical'], 'HEAD', cwd=REPLAY).splitlines()
    modified_original = git('diff', '--name-only', '--diff-filter=MDT', PINS['canonical'], 'HEAD', cwd=REPLAY).splitlines()
    assert not modified_original, modified_original
    assert set(changed) <= ALLOWED, changed
    assert not git('status', '--porcelain', '--untracked-files=no', cwd=REPLAY), 'tracked source mutated during tests'
    gate = REPLAY / 'implementation/reports/gate_evidence'
    manifest = json.loads((gate / 'track_a_freeze_readiness_2026-09-27.json').read_text())
    for name, expected in manifest['evidence_sha256'].items():
        assert hashlib.sha256((gate / name).read_bytes()).hexdigest() == expected, name
    stage.update(changed_files=changed, modified_canonical_files=[],
                 frozen_manifest_hashes_verified=len(manifest['evidence_sha256']),
                 original_canonical_blob_count=len(git('ls-tree', '-r', '--name-only', PINS['canonical']).splitlines()))
NUMERIC_PROBE = """
import json, sys
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.portfolio import PortfolioEngine
from tests.helpers import AS_OF, complete_obs
outputs = {
 'qgv': AnalysisEngine().analyze('nvda', AS_OF, complete_obs(), synthetic=True).to_dict(),
 'technical': TechnicalEngine().evaluate('nvda', AS_OF, [0.01,0.02,-0.01]).to_dict(),
 'macro': MacroEngine().evaluate(AS_OF, {'growth':0.04,'inflation':0.02}).to_dict(),
 'portfolio': PortfolioEngine().official_v11(AS_OF).to_dict()
}
# Each engine independently creates a fresh UUID. Compare all other output fields exactly.
id_fields = {'qgv':'qgv_snapshot_id', 'technical':'technical_snapshot_id',
             'macro':'macro_snapshot_id', 'portfolio':'portfolio_snapshot_id'}
for section, key in id_fields.items():
    del outputs[section][key]
open(sys.argv[1], 'w').write(json.dumps(outputs, sort_keys=True))
"""
def stage(name, head, language):
    dest = OUT / name
    dest.mkdir(exist_ok=True)
    info = report['stages'][name] = {'status': 'RUNNING'}
    try:
        before = git('rev-parse', 'HEAD', cwd=REPLAY)
        result = run(['git','-c','user.name=Integration Audit',
                      '-c','user.email=integration-audit@example.invalid',
                      'merge','--no-ff','--no-edit','-m','Temporary Web integration normal merge',head],
                     REPLAY, dest / 'merge.txt')
        info.update(merge_sha=git('rev-parse','HEAD',cwd=REPLAY),
                    tree=git('rev-parse','HEAD^{tree}',cwd=REPLAY),
                    parents=git('show','-s','--format=%P','HEAD',cwd=REPLAY).split(),
                    merge_conflicts=[], merge_output=result)
        assert info['parents'] == [before, head], info['parents']
        assert info['tree'] == git('rev-parse',head+'^{tree}'), 'unexpected normal merge tree'
        preserve(info)
        impl = REPLAY / 'implementation'
        targets = ['tests/test_web_mvp.py']
        if language:
            targets.append('tests/test_global_language_search.py')
        run([sys.executable,'-m','pytest','-q',*targets,'--junitxml='+str(dest/'targeted.xml')],
            impl,dest/'targeted.txt')
        info['targeted'] = junit(dest/'targeted.xml')
        run([sys.executable,'-m','pytest','-q','--junitxml='+str(dest/'full.xml')],
            impl,dest/'full.txt')
        info['full_regression'] = junit(dest/'full.xml')
        buildroot = WORK / ('build-'+name)
        buildroot.mkdir(exist_ok=True)
        buildenv = dict(ENV,PYTHONPATH=str(impl/'src'))
        run([sys.executable,'-m','investment_system.product.web_mvp','--out',str(buildroot/'web-mvp')],
            REPLAY,dest/'build-default.txt',buildenv)
        run([sys.executable,'implementation/tools/build_web_mvp_demo.py','--out',str(buildroot/'web-mvp-demo')],
            REPLAY,dest/'build-demo.txt')
        run([sys.executable,'-c',NUMERIC_PROBE,str(dest/'engine-outputs.json')],
            impl,dest/'engine-probe.txt',dict(buildenv,PYTHONPATH=str(impl/'src')+os.pathsep+str(impl)))
        for mode in ('web-mvp','web-mvp-demo'):
            shutil.copyfile(buildroot/mode/'data.json',dest/(mode+'-data.json'))
        if language:
            output=run(['node','implementation/tools/global_language_search_test.js',str(buildroot/'web-mvp-demo')],
                       REPLAY,dest/'search-locale.txt')
            node_result=json.loads(output.splitlines()[-1])
            assert node_result['passed'] and node_result['checks']==26, node_result
            info['search_locale'] = node_result
        with (dest/'http-server.txt').open('w') as logfile:
            server=subprocess.Popen([sys.executable,'-m','http.server','8765','--bind','127.0.0.1',
                                     '--directory',str(buildroot)],stdout=logfile,stderr=subprocess.STDOUT)
            try:
                import urllib.request
                for attempt in range(100):
                    try:
                        urllib.request.urlopen('http://127.0.0.1:8765/web-mvp/data.json',timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('HTTP server not ready')
                run(['node','implementation/tools/web_mvp_browser_test.js'],REPLAY,dest/'web-e2e.txt')
                if language:
                    run(['node','implementation/tools/global_language_search_browser_test.js'],REPLAY,dest/'language-search-e2e.txt')
            finally:
                server.terminate()
                server.wait(timeout=10)
                generated=impl/'reports/web_mvp'
                if generated.exists():
                    shutil.copytree(generated,dest/'browser',dirs_exist_ok=True)
        web=json.loads((dest/'browser/browser.json').read_text())
        assert web['passed'] and len(web['checks'])==10 and web['errors']==[], web
        info['web_e2e']={'checks':len(web['checks']),'passed':web['passed'],'errors':web['errors']}
        info['responsive_widths']=[360,390,1280]
        if language:
            extra=json.loads((dest/'browser/global-language-search-browser.json').read_text())
            assert extra['passed'] and len(extra['checks'])==8 and extra['errors']==[], extra
            info['global_e2e']={'checks':len(extra['checks']),'passed':extra['passed'],'errors':extra['errors']}
            baseline=json.loads((OUT/'pr5/engine-outputs.json').read_text())
            current=json.loads((dest/'engine-outputs.json').read_text())
            assert baseline==current, 'engine numerical/semantic outputs changed'
            for mode in ('web-mvp','web-mvp-demo'):
                original=json.loads((OUT/'pr5'/(mode+'-data.json')).read_text())
                added=json.loads((dest/(mode+'-data.json')).read_text())
                for key in ('universe','qgv','technical','macro','portfolio','leaderboard','news','relationships','changes'):
                    assert original[key]==added[key], (mode,key)
            info['numerical_invariance']='PASS: all four engine outputs equal except fresh snapshot UUIDs; all nine default/demo producer envelopes exactly equal'
            info['leaderboard_locale_invariance']='PASS: existing browser test preserves nontrivial supplied rank/order under locale changes'
        preserve(info)
        info['status']='PASS'
    except Exception as error:
        info['status']='FAIL'
        info['error']=str(error)
        info['unmerged_paths']=git('diff','--name-only','--diff-filter=U',cwd=REPLAY).splitlines()
        (dest/'exception.txt').write_text(traceback.format_exc())
        raise
    finally:
        save()
try:
    run(['git','fetch','origin','--prune'],ROOT,OUT/'git-fetch.txt')
    refs=git('ls-remote','origin',
             'refs/heads/claude/investment-system-top500-validation-alrugm',
             'refs/heads/feature/web-mvp-v1','refs/heads/feature/global-language-search-v1',
             'refs/heads/feature/track-c-evl')
    report['remote_refs_before']=refs
    refmap={line.split()[1]:line.split()[0] for line in refs.splitlines()}
    for key, branch in [('canonical','claude/investment-system-top500-validation-alrugm'),
                        ('pr5','feature/web-mvp-v1'),('pr6','feature/global-language-search-v1')]:
        assert refmap['refs/heads/'+branch]==PINS[key], 'source HEAD advanced; repin before replay'
    git('merge-base','--is-ancestor',PINS['canonical'],PINS['pr5'])
    git('merge-base','--is-ancestor',PINS['pr5'],PINS['pr6'])
    git('worktree','add','--detach',str(REPLAY),PINS['canonical'])
    stage('pr5',PINS['pr5'],False)
    stage('combined',PINS['pr6'],True)
    report['readiness']={'pr5':'INTEGRATION_READY','pr6':'INTEGRATION_READY_AFTER_PR5',
                         'combined':'PR5_PLUS_PR6_INTEGRATION_READY'}
except Exception:
    report['readiness']={'combined':'NOT_READY'}
    report['exception']=traceback.format_exc()
    raise
finally:
    report['ended_kst']=datetime.now(KST).isoformat()
    save()
