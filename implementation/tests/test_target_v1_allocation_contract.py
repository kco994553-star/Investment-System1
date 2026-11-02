"""AUD-01: existing TARGET v1 validator with source JSON, no frontend edits."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate(general_pct):
    # Inject source config in memory; the generated browser copy belongs to Main.
    script = r'''
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=process.argv[1],pct=Number(process.argv[2]);
const cfg=JSON.parse(fs.readFileSync(path.join(root,'src/investment_system/qgv/playbook_v1.json')));
const web=path.join(root,'src/investment_system/product/web_assets');
const context={PlaybookConfigDefaults:cfg,PlaybookEngine:require(path.join(web,'playbook-engine.js'))};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(web,'playbook-screen.js'),'utf8'),context);
const rows=Array.from({length:15},(_,i)=>({symbol:'TEST'+i,grade:i<5?'CORE':'GENERAL',pct:i<5?8:pct,
  sector:'synthetic-sector-'+i,thesis:'reason one\nreason two',invalidation:'condition one\ncondition two'}));
try {process.stdout.write(JSON.stringify(context.PlaybookScreen.targetValidate({rows,cash_pct:100-40-10*pct})));}
catch(e){process.stdout.write(JSON.stringify({error:e.message}));}
'''
    run = subprocess.run(['node', '-e', script, str(ROOT), str(general_pct)], capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def test_approved_core5x8_general10x6_passes_existing_target_validator():
    result = validate(6)
    assert result.get('error') is None, result
    assert result['ok'] is True and result['violations'] == []


def test_superseded_general_4_or_5_is_not_current_target_v1():
    for pct in (4, 5):
        assert validate(pct) == {'error': 'TARGET_THESIS_OR_GRADE_INVALID'}
