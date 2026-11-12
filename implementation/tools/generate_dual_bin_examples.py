#!/usr/bin/env python3
"""Create public routing examples from existing synthetic saved distributions."""
import hashlib
import json
from pathlib import Path
from investment_system.research.dual_qgv import json_bytes
from investment_system.research.dual_qgv_distribution import STORED
from investment_system.research.dual_qgv_distribution_index import bin_index_artifacts, validate_distribution


def main():
    root=Path(__file__).resolve().parents[1]/'docs/research/sector_qgv'
    src=root/'dual-distribution-synthetic';dest=root/'dual-bin-synthetic'
    dest.mkdir(exist_ok=True);cases=[]
    for c in json.loads((src/'cases.json').read_bytes())['cases']:
        if c['display_policy']!=STORED:continue
        directory=src/c['output'];files={p.name:p.read_bytes() for p in directory.iterdir()}
        pin=hashlib.sha256(files['distribution-manifest.json']).hexdigest()
        artifacts=bin_index_artifacts(files,expected_manifest_sha256=pin)
        target=dest/c['output'];target.mkdir(parents=True,exist_ok=True)
        for name,value in artifacts.items():(target/name).write_bytes(json_bytes(value))
        idx,rows,_,_=validate_distribution(files,pin)
        expected=[dict(group_id=g['group_id'],bins=[dict(decile=d,members=[r['company_id'] for r in sorted(rows[g['group_id']],key=lambda r:r['rank'] or 0) if r['decile']==d],ranks=[r['rank'] for r in sorted(rows[g['group_id']],key=lambda r:r['rank'] or 0) if r['decile']==d]) for d in range(10,0,-1)],unavailable_count=g['unavailable_count']) for g in idx['groups']]
        cases.append(dict(source='../dual-distribution-synthetic/'+c['output'],source_manifest_sha256=pin,
            output=c['output'],manifest_sha256=hashlib.sha256(json_bytes(artifacts['bin-manifest.json'])).hexdigest(),expected_groups=expected))
    (dest/'cases.json').write_bytes(json_bytes(dict(schema_version='qgv-dual-bin-examples/1',data_kind='SYNTHETIC',cases=cases)))


if __name__=='__main__':main()
