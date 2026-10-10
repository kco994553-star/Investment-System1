import json
from pathlib import Path
import subprocess
from investment_system.qgv.theme_exposure import summarize_theme_exposure

def test_public_theme_metadata_matches_pending_engine_without_scores():
    base=Path(__file__).parents[1]/'src/investment_system'
    c=json.loads((base/'qgv/theme_config_v1.json').read_text());expected=summarize_theme_exposure(config=c,etf_evidence={})
    p=subprocess.run(['node','-e','process.stdout.write(JSON.stringify(require(process.argv[1])))',str(base/'product/web_assets/theme-reference.js')],capture_output=True,text=True,check=True)
    v=json.loads(p.stdout)
    assert v['state']==expected['state']=='NOT_AVAILABLE'
    assert v['reason_codes']==expected['reason_codes']
    assert [(t['id'],t['name'],t['etfs']) for t in v['themes']]==[(t['id'],t['name'],[e['ticker'] for e in t['etfs']]) for t in c['themes']]
    assert 'membership' not in json.dumps(v) and v['maximum_display']==2
