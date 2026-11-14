#!/usr/bin/env python3
"""Project pinned retained inputs; independent source pins must come from handoff."""
import argparse,hashlib,json
from pathlib import Path
from investment_system.research.qgv_555_held import held_input
from investment_system.research.qgv_555 import configuration,identity
from investment_system.research.dual_qgv import json_bytes


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('PRESERVE_EXISTING_INPUT_VERSION')
    plan=json.loads(a.plan.read_bytes())
    def read(d):
        b=Path(d['path']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=d['sha256']:raise ValueError('RETAINED_SOURCE_HASH')
        return json.loads(b)
    sources=[dict(sha256=d['sha256'],records=read(d)[d['records_key']]) for d in plan['financial_sources']]
    outputs={k:held_input(read(d),sources,source_anchors=[d,*plan['financial_sources']]) for k,d in plan['snapshots'].items()}
    a.output.mkdir(parents=True)
    desc={}
    for k,v in outputs.items():
        raw=json_bytes(v);path=a.output/(k+'.json');path.write_bytes(raw)
        desc[k]=dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw))
    anchors=dict(schema_version='qgv-555-input-source-anchors/1',source_plan=plan,source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),
        construction_rule='HELD_FORMULA_VERSIONED_RAW_PROJECTION/1',files=desc,identities={k:identity(v) for k,v in outputs.items()},
        runtime_metadata_is_projection_proof=False)
    (a.output/'input-source-anchors.json').write_bytes(json_bytes(anchors))
    for scope,ev,ref in plan['pairs']:
        job=dict(data_kind='PRIVATE',evaluation=desc[ev],reference=desc[ref],configurations={k:configuration(k) for k in ('U1-555','S1-555')})
        (a.output/(scope+'-job.json')).write_bytes(json_bytes(job))


if __name__=='__main__':main()
