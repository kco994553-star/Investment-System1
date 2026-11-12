#!/usr/bin/env python3
"""Create public routing examples from retained synthetic distributions/hand cases."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from investment_system.research.dual_qgv import json_bytes
from investment_system.research.sector_qgv import digest
from investment_system.research.dual_qgv_distribution import STORED, distribution_artifacts
from investment_system.research.dual_qgv_distribution_index import bin_index_artifacts, validate_distribution

# Independently specified expectations for Main's requested small-N boundaries.
BOUNDARIES={9:[None]*9,10:[10,9,8,7,6,5,4,3,2,1],
            11:[10,9,9,8,7,6,5,4,3,2,1],17:[10,9,9,8,8,7,7,6,6,5,5,4,4,3,3,2,1]}


def main():
    root=Path(__file__).resolve().parents[1]/'docs/research/sector_qgv'
    src=root/'dual-distribution-synthetic';dest=root/'dual-bin-synthetic'
    dest.mkdir(exist_ok=True);cases=[]
    originals=json.loads((src/'cases.json').read_bytes())['cases']
    sources=[dict(source='../dual-distribution-synthetic/'+c['output'],output=c['output']) for c in originals if c['display_policy']==STORED]
    # These are explicit fictional saved scores/ranks, not a financial calculation.
    original_board=json.loads((src/originals[0]['source']).read_bytes())['U1']
    for n,ds in BOUNDARIES.items():
        b=deepcopy(original_board);b['rows']=b['rows'][:n]
        for i,r in enumerate(b['rows']):
            r['factors']['debt_assets'].update(rank=i+1,rank_n=n,decile=ds[i],decile_status='VALID' if n>=10 else 'SAMPLE_LT_10')
        b['evaluation_population'].update(code_rows=n,issuers=n,members_hash=digest([r['company_id'] for r in b['rows']]))
        b['bindings']['evaluation']=deepcopy(b['evaluation_population'])
        b['result_hash']=digest({k:v for k,v in b.items() if k not in ('request_id','result_hash')})
        directory=dest/f'boundary-{n}'/'source';directory.mkdir(parents=True,exist_ok=True)
        out=distribution_artifacts({'U1':b},scope='operating504',data_kind='SYNTHETIC',display_policy=STORED)
        for name,value in out.items():(directory/name).write_bytes(json_bytes(value))
        (dest/f'boundary-{n}'/'saved-board.json').write_bytes(json_bytes({'U1':b}))
        sources.append(dict(source=f'boundary-{n}/source',output=f'boundary-{n}/routing'))
    for c in sources:
        directory=dest/c['source'];files={p.name:p.read_bytes() for p in directory.iterdir()}
        pin=hashlib.sha256(files['distribution-manifest.json']).hexdigest()
        artifacts=bin_index_artifacts(files,expected_manifest_sha256=pin)
        target=dest/c['output'];target.mkdir(parents=True,exist_ok=True)
        for name,value in artifacts.items():(target/name).write_bytes(json_bytes(value))
        idx,rows,_,_=validate_distribution(files,pin)
        expected=[dict(group_id=g['group_id'],bins=[dict(decile=d,members=[r['company_id'] for r in sorted(rows[g['group_id']],key=lambda r:r['rank'] or 0) if r['decile']==d],ranks=[r['rank'] for r in sorted(rows[g['group_id']],key=lambda r:r['rank'] or 0) if r['decile']==d]) for d in range(10,0,-1)],unavailable_count=g['unavailable_count']) for g in idx['groups']]
        cases.append(dict(source=c['source'],source_manifest_sha256=pin,
            output=c['output'],manifest_sha256=hashlib.sha256(json_bytes(artifacts['bin-manifest.json'])).hexdigest(),expected_groups=expected))
    (dest/'cases.json').write_bytes(json_bytes(dict(schema_version='qgv-dual-bin-examples/1',data_kind='SYNTHETIC',cases=cases)))


if __name__=='__main__':main()
