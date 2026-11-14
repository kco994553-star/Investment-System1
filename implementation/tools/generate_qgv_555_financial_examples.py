"""Synthetic-only temporary financial views from the common 555 engine."""
import argparse,hashlib
from copy import deepcopy
from pathlib import Path
from investment_system.research.qgv_555 import configuration,fixture,run
from investment_system.research.qgv_555_financial_temporary import financial_catalog
from investment_system.research.dual_qgv import json_bytes


def generate():
    e,r=fixture(10)
    for s in (e,r):
        for i,row in enumerate(s['rows']):
            row.update(accounting_template='BANK',sector_id='FINANCIALS',calculation_accounting_template=None,
                calculation_sector_id='FINANCIALS',calculation_industry_group='synthetic-financial',
                financial_calculation_profile='FINANCIAL',financial_peer_template='BANK',
                financial_temporary_policy='official-financial-role-bridge/1',
                financial_temporary_source_refs=['SYNTHETIC_ONLY'],
                owner_source_context=dict(profile='FINANCIAL',record_hash='a'*64,companyfacts_sha256='b'*64,acquired_at='2026-11-03T12:00:00Z'),
                classification_status='VERIFIED',classification_record_id='synthetic-peer',
                classification_mapping=dict(common_record_id='synthetic-peer',evidence_refs=['SYNTHETIC_ONLY'],
                    common_dictionary_version='common-industry-dictionary/2',common_mapping_version='common-classification-map/2',
                    common_classification_hash='a'*64,valid_from='2026-11-04',valid_to='2026-11-05',knowledge_as_of='2026-11-04T20:00:00Z'))
            for key,spec in financial_catalog().items():
                row['metrics'][key]=(i+1)/10
                proof=dict(status='TEMPORARY_OFFICIAL_FINANCIAL_RAW',variant=spec['variant'],
                    financial_temporary_policy='official-financial-role-bridge/1',source_formula_version='qgv2-calc/2026-10-23.1',
                    source_metric=spec['source_metric'],source_record_hash='a'*64,source_body_sha256='b'*64,
                    raw_reusable=True,source_refs=['SYNTHETIC_ONLY'],available_at=s['input_cutoff'],reviewed_at=s['input_cutoff'],
                    source_available_at='2026-11-03T12:00:00Z',retrieved_at='2026-11-03T12:00:00Z')
                if spec['historical_share_evidence_required']:
                    proof.update(official_share_reuse_version='held-555-official-share-reuse/1',historical_share_basis='OFFICIAL_PATH_REUSED',
                        adoption_basis='EVIDENCE_LINKED',requires_assumption=False,allowed_assumptions=[],evidence_only_eligible=True,
                        strict_verified=False,denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',
                        formula_variant={'eps_cagr_3y':'REPORTED_DILUTED_EPS_CAGR_3Y','dilution_3y':'WEIGHTED_DILUTED_SHARES_CAGR_3Y',
                         'book_value_per_share_cagr_3y':'OFFICIAL_EQUITY_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y'}[spec['source_metric']])
                row['metric_evidence'][key]=proof
        s['rows'][1].update(accounting_template=None,financial_peer_template=None,classification_status='UNKNOWN')
        s['rows'][2].update(accounting_template='INSURANCE',financial_peer_template='INSURANCE')
    # A target clock failure cannot be fixed by the reference group.
    for p in e['rows'][0]['metric_evidence'].values():p['reviewed_at']='2030-01-01T00:00:00Z'
    e['rows'][3]['gate']=None
    views={}
    for model in ('U1-555','S1-555'):
        c=configuration(model,version='0.5.0');out=run(c,e,r,calculated_at='2026-11-04T22:00:00Z')
        rows=[deepcopy(x) for x in out['rows'][:4]]
        views[model]=dict(model_id=out['model_id'],configuration=c,evaluation=out['evaluation'],reference=out['reference'],
            rows=rows,coverage=out['coverage'])
    assert views['U1-555']['rows'][0]['axes']['Q']['score'] is None
    assert views['U1-555']['rows'][1]['axes']['Q']['score'] is not None
    assert views['S1-555']['rows'][1]['status']=='FINANCIAL_PEER_MODEL_UNCONFIRMED'
    assert views['S1-555']['rows'][2]['roles']['q_profitability']['metrics'][0]['reference_n']==1
    return dict(schema_version='qgv-555-financial-temporary-examples/1',data_kind='SYNTHETIC',views=views,
        meanings=['source clock invalid','temporary profile, peer model unknown','small insurance peer group','gate unknown'],
        financial_definition_complete=False,official=False,browser_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);b=json_bytes(generate())
    f=args.output/'examples.json';f.write_bytes(b)
    (args.output/'manifest.json').write_bytes(json_bytes(dict(schema_version='qgv-555-financial-example-manifest/1',
        files=[dict(path=f.name,size=len(b),sha256=hashlib.sha256(b).hexdigest())])))
    assert f.read_bytes()==b


if __name__=='__main__':main()
