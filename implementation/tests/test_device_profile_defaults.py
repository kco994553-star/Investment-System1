"""The UI parameter skeleton copies official leaves, never adds parent weights."""
import json
from pathlib import Path
import subprocess
from investment_system.qgv.strategy_preview import official_v1_weight_copy
from investment_system.personal.weights import SIBLING_SUM_TOLERANCE

def test_profile_ui_defaults_equal_engine_authoritative_copy():
    path=Path(__file__).parents[1]/'src/investment_system/product/web_assets/profile-defaults.js'
    p=subprocess.run(['node','-e','process.stdout.write(JSON.stringify(require(process.argv[1])))',str(path)],text=True,capture_output=True,check=True)
    v=json.loads(p.stdout)
    assert v['weights']==official_v1_weight_copy()
    assert v['sum_tolerance']==SIBLING_SUM_TOLERANCE*100
    assert v['role']=='PREVIEW'
