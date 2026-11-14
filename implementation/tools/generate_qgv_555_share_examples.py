"""Generate only synthetic stage examples through the existing 555 producer."""
import argparse
import hashlib
from pathlib import Path
from investment_system.research.qgv_555 import configuration, fixture, run, SHARE_METRICS
from investment_system.research.dual_qgv import json_bytes


def generate():
    evaluation,reference=fixture(10)
    cases=[('FINAL_ELIGIBLE','WEIGHTED_AVERAGE_DILUTED_SHARES'),
           ('CROSS_FILING_CONSISTENT','WEIGHTED_AVERAGE_DILUTED_SHARES'),
           ('SPLIT_CANDIDATE','WEIGHTED_AVERAGE_DILUTED_SHARES'),
           ('UNCONFIRMED_PERIOD_BASIS','WEIGHTED_AVERAGE_DILUTED_SHARES'),
           ('FINAL_ELIGIBLE','ACTUAL_ENDING_SHARES')]
    for row,(status,denominator) in zip(evaluation['rows'],cases):
        for metric in SHARE_METRICS:
            proof=row['metric_evidence'][metric]
            proof.update(share_eligibility_stage=status,denominator_definition=denominator,
                validation_stages=dict(stage1_status='CONSISTENT' if status=='CROSS_FILING_CONSISTENT' else status,
                    stage2_status='FINAL_ELIGIBLE' if status=='FINAL_ELIGIBLE' else 'UNCONFIRMED_PERIOD_BASIS',
                    corporate_action_status='SPLIT_CANDIDATE' if status=='SPLIT_CANDIDATE' else 'UNKNOWN',
                    adjustment_applied=False))
    result=run(configuration('U1-555',version='0.3.0'),evaluation,reference,
        calculated_at='2026-11-04T22:00:00Z')
    rows=[]
    for row in result['rows'][:len(cases)]:
        metrics=[m for role in row['roles'].values() for m in role['metrics'] if m['metric'] in SHARE_METRICS]
        rows.append(dict(company_id=row['company_id'],issuer_id=row['issuer_id'],metrics=metrics,
            expected_adopted=all(m['score'] is not None for m in metrics),
            meaning='SYNTHETIC_ONLY_NOT_AN_ACTUAL_ISSUER_OR_PRICE'))
    return dict(schema_version='qgv-555-share-stage-examples/1',data_kind='SYNTHETIC',
        model_id=result['model_id'],configuration=result['configuration'],
        evaluation=result['evaluation'],reference=result['reference'],rows=rows,
        official=False,browser_verified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    data=json_bytes(generate());path=args.output/'stage-examples.json';path.write_bytes(data)
    manifest=dict(schema_version='qgv-555-share-example-manifest/1',data_kind='SYNTHETIC',
        files=[dict(path=path.name,size=len(data),sha256=hashlib.sha256(data).hexdigest())])
    (args.output/'manifest.json').write_bytes(json_bytes(manifest))
    assert path.read_bytes()==data


if __name__=='__main__':main()
