#!/usr/bin/env python3
"""Explicit private-input QGV research entrypoint; safe summaries only."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from investment_system.research.qgv_backtest.config import audit_inputs,validate_spec

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True,choices=('audit','synthetic','smoke','primary','sensitivity','report'))
    p.add_argument('--spec',default=str(ROOT/'docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json'))
    p.add_argument('--period-id',default='TARGET_QGV_V2',choices=('TARGET_QGV_V2','SECONDARY_DIAGNOSTIC_NOT_TARGET','DATA_LIMITED_DIAGNOSTIC_NOT_TARGET'))
    p.add_argument('--input-manifest');p.add_argument('--output')
    p.add_argument('--extension-spec',help='Separate versioned decile/factor contract; frozen thirty-strategy spec remains intact')
    p.add_argument('--experiment-id',action='append',help='Explicit repeatable experiment allowlist; no implicit fallback')
    p.add_argument('--formation-month',action='append',choices=['all']+[str(m) for m in range(1,13)],
                   help='Annual contract robustness only; each offset reselects once every twelve months')
    args=p.parse_args(argv)
    try:
        spec=json.loads(Path(args.spec).read_text());validate_spec(spec)
        extension=json.loads(Path(args.extension_spec).read_text()) if args.extension_spec else None
        formation_months=sorted({m for value in args.formation_month or [] for m in (range(1,13) if value=='all' else [int(value)])}) or None
        if formation_months is not None and extension is None:
            raise ValueError('FORMATION_REQUIRES_ANNUAL_CONTRACT')
        if extension is not None:
            from investment_system.research.qgv_backtest.extensions import validate_extension
            validate_extension(extension)
        if args.stage=='synthetic':
            files=sorted(str(f) for f in (ROOT/'tests/research').glob('test_qgv_backtest_*.py') if f.name!='test_qgv_backtest_cli.py')
            env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT))
            result=subprocess.run([sys.executable,'-m','pytest','-q',*files],cwd=ROOT,env=env,capture_output=True,text=True)
            match=re.findall(r'\d+ passed',result.stdout)
            out=dict(status='SYNTHETIC_PASS' if result.returncode==0 else 'SYNTHETIC_FAIL',test_summary=match[-1] if match else 'SEE_LOCAL_TEST_RUN',real_data_executed=False)
            code=0 if result.returncode==0 else 1
        else:
            manifest=json.loads(Path(args.input_manifest).read_text()) if args.input_manifest else None
            if args.stage=='audit' and extension is None and args.experiment_id is None:out=audit_inputs(spec,manifest,args.period_id)
            else:
                from investment_system.research.qgv_backtest.runner import run_stage
                out=run_stage(spec,args.stage,args.period_id,manifest,args.output,extension=extension,experiment_ids=args.experiment_id,formation_months=formation_months)
            code=0 if out['status'] in ('INPUT_INTEGRITY_PASS','SEMANTIC_INPUT_CONTRACT_PASS','SMOKE_PASS','PRIMARY_DONE','SENSITIVITY_DONE','REVIEWED','REPORT_READY','REPORT_DONE') else 2
        print(json.dumps(out,ensure_ascii=False,allow_nan=False))
        return code
    except (ValueError,KeyError,OSError,TypeError) as exc:
        # Do not print exception messages: they may embed private values/paths.
        print(json.dumps({'status':'ERROR','error_type':type(exc).__name__,'real_data_executed':False}))
        return 1
if __name__=='__main__':raise SystemExit(main())
