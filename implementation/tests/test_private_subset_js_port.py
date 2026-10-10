"""Compare the RAM JS port against Codex2's merged Python using synthetic inputs."""
import dataclasses
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

import pytest
from tests import test_m3_private_universe as reference


def encode(value):
    if isinstance(value, (datetime,date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode()
    raise TypeError('UNSUPPORTED_SYNTHETIC_REFERENCE')


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_python_and_js_m3_quality_and_failure_contracts_match():
    a=reference.api()
    cases=[]
    expected=[]
    for google,price,mode in [(90,10,'normal'),(110,10,'normal'),(91,10,'normal'),(109,10,'normal'),(None,10,'normal'),('#N/A',10,'normal'),(100,None,'normal'),(100,False,'normal'),(90,10,'different'),(90,10,'unknown'),(90,10,'bad_hash'),(90,10,'future'),(90,10,'mixed'),(90,10,'bad_identity'),(90,10,'invalid_currency')]:
        s=reference.seed(a)
        unit=reference.basis(a,s)
        receipt=reference.sec(a,s)
        if mode=='different':unit=dataclasses.replace(unit,share_class_basis='DIFFERENT')
        if mode=='unknown':unit=dataclasses.replace(unit,basis_status='UNKNOWN')
        if mode=='bad_hash':receipt=dataclasses.replace(receipt,facts_sha256='0'*64)
        if mode=='future':receipt=dataclasses.replace(receipt,acquired_at=reference.AT.replace(day=11))
        if mode=='mixed':receipt=dataclasses.replace(receipt,synthetic=False)
        if mode=='bad_identity':receipt=dataclasses.replace(receipt,cik='0000000002')
        if mode=='invalid_currency':unit=dataclasses.replace(unit,currency='JPY')
        values=[['NYSE:A',google,price]]
        p=reference.parse(a,values)
        shares=a.prepare_sec_shares(s,receipt,unit,reference.AT)
        value=a.prepare_universe_price(p.rows[0],unit,as_of=reference.AT)
        check=a.compare_universe_market_cap(p.rows[0],shares,value,a.QualityConfig(.1,True))
        expected.append(dict(state=check.state,quality=check.quality,reason_codes=list(check.reason_codes),recomputed_cap=check.recomputed_cap,relative_difference=check.relative_difference))
        cases.append(dict(values=values,receipt=dataclasses.asdict(p.receipt),identities={'NYSE:A':dataclasses.asdict(s)},seed=dataclasses.asdict(s),sec=dataclasses.asdict(receipt),basis=dataclasses.asdict(unit),as_of=reference.AT))
    script=Path(__file__).resolve().parents[1]/'tools/private_subset_port_compare.js'
    run=subprocess.run(['node',str(script)],input=json.dumps(cases,default=encode),capture_output=True,text=True,check=False)
    assert run.returncode==0, 'JS_PORT_EXECUTION_FAILED'
    actual=json.loads(run.stdout)
    assert len(actual)==len(expected)
    for observed,wanted in zip(actual,expected):
        for key in ('state','quality','reason_codes'):
            assert observed[key]==wanted[key], 'JS_PORT_CONTRACT_MISMATCH'
        for key in ('recomputed_cap','relative_difference'):
            if wanted[key] is None:
                assert observed[key] is None,'JS_PORT_NULL_MISMATCH'
            else:
                assert math.isclose(observed[key],wanted[key],rel_tol=1e-12,abs_tol=1e-12),'JS_PORT_NUMBER_MISMATCH'
