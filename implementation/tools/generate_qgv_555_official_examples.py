"""Public synthetic 0.4 evidence/assumption examples from the common producer."""
import argparse,hashlib
from pathlib import Path
from investment_system.research.qgv_555 import configuration,fixture,run,SHARE_METRICS
from investment_system.research.qgv_555_official_share import FORMULAS
from investment_system.research.dual_qgv import json_bytes


def generate():
    e,r=fixture(12)
    for s in (e,r):
        for row in s['rows']:
            for m in SHARE_METRICS:row['metric_evidence'][m].update(
                status='RESEARCH_USABLE',historical_share_basis='OFFICIAL_PATH_REUSED',
                official_share_reuse_version='held-555-official-share-reuse/1',
                adoption_basis='EVIDENCE_LINKED',requires_assumption=False,
                allowed_assumptions=[],evidence_only_eligible=True,strict_verified=False,
                formula_variant=FORMULAS[m],additional_verification_required=True,
                additional_verification=['SYNTHETIC_COMMON_PERIOD_BASIS_NOT_STRICT_OR_PRICE_IDENTITY'])
    cases=[('EVIDENCE_LINKED',[]),('FILING_SPLIT_ADJUSTED',[]),
        ('OFFICIAL_ASSUMPTION_INHERITED',['OFFICIAL_NO_OVERLAP_NO_REPORTED_SPLIT_FACTOR_ONE']),
        ('ADDITIONAL_VERIFICATION_REQUIRED',[]),('EXPLICIT_CONFLICT_EXCLUDED',[]),
        ('OFFICIAL_ASSUMPTION_INHERITED',['OFFICIAL_ORDINARY_REVISION_TOLERANCE']),
        ('EVIDENCE_LINKED',[])]
    for s in (e,r):
        for row,(basis,assumptions) in zip(s['rows'],cases):
            for m in SHARE_METRICS:
                p=row['metric_evidence'][m]
                p.update(adoption_basis=basis,requires_assumption=bool(assumptions),
                    allowed_assumptions=assumptions,
                    evidence_only_eligible=basis in ('EVIDENCE_LINKED','FILING_SPLIT_ADJUSTED'))
                if row['company_id']=='SYN:006':p['additional_verification']=['NO_REFERENCE_IS_NOT_A_PRICE_VERIFICATION']
    views={}
    for scope in ('ALL_OFFICIAL_REUSE','EVIDENCE_ONLY'):
        c=configuration('U1-555',version='0.4.0');c['share_evidence_scope']=scope
        out=run(c,e,r,calculated_at='2026-11-04T22:00:00Z')
        rows=[]
        for row in out['rows'][:len(cases)]:
            metrics=[m for role in row['roles'].values() for m in role['metrics'] if m['metric'] in SHARE_METRICS]
            rows.append(dict(company_id=row['company_id'],issuer_id=row['issuer_id'],metrics=metrics,
                expected_adopted=all(m['score'] is not None for m in metrics)))
        views[scope]=dict(model_id=out['model_id'],configuration=out['configuration'],rows=rows,
            evaluation=out['evaluation'],reference=out['reference'])
    assert [x['expected_adopted'] for x in views['ALL_OFFICIAL_REUSE']['rows']]==[True,True,True,False,False,True,True]
    assert [x['expected_adopted'] for x in views['EVIDENCE_ONLY']['rows']]==[True,True,False,False,False,False,True]
    return dict(schema_version='qgv-555-official-share-examples/1',data_kind='SYNTHETIC',views=views,
        official=False,strict_verified=False,browser_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    data=json_bytes(generate());path=args.output/'examples.json';path.write_bytes(data)
    manifest=dict(schema_version='qgv-555-official-example-manifest/1',data_kind='SYNTHETIC',
        files=[dict(path=path.name,size=len(data),sha256=hashlib.sha256(data).hexdigest())])
    (args.output/'manifest.json').write_bytes(json_bytes(manifest));assert path.read_bytes()==data


if __name__=='__main__':main()
