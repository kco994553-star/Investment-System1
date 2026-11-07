import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/qgv_backtest_research.py'
SPEC=ROOT/'docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json'

def test_help_is_real_cli():
    r=subprocess.run([sys.executable,str(SCRIPT),'--help'],capture_output=True,text=True)
    assert r.returncode==0
    assert '--period-id' in r.stdout

def test_audit_without_private_data_fails_closed():
    r=subprocess.run([sys.executable,str(SCRIPT),'--stage','audit','--spec',str(SPEC)],capture_output=True,text=True)
    assert r.returncode==2
    report=json.loads(r.stdout)
    assert report['status']=='BLOCKED_ON_DATA'
    assert len(report['strategies'])==30
    assert all(row['metrics'] is None for row in report['strategies'])
