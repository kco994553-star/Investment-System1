"""Test-only synthetic handoff builder. Uses the real producer, no network/data fetch."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
from investment_system.research import dual_qgv as dual
from investment_system.research.qgv_333 import candidate_configs,configuration_contract
from investment_system.research.dual_qgv_distribution import distribution_artifacts,STORED


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    # One shared synthetic factory; pytest is a test-only builder dependency.
    factory=runpy.run_path(str(Path(__file__).resolve().parents[1]/'tests/research/test_qgv_333.py'))
    cases={};expected={};configs=candidate_configs()
    for name,n,template in [('normal',20,'GENERAL'),('small-reference',19,'GENERAL'),('financial-scope',20,'BANK'),('reit-pending',20,'EQUITY_REIT')]:
        e,r=factory['snapshots'](n,template)
        boards={k:dual.run_board(c,e,r,request_id='SYN333:'+name+':'+k) for k,c in configs.items()}
        cases[name]={k:{'model_id':b['model_id'],'configuration_hash':dual.digest(b['configuration']),
            'evaluation_population':b['evaluation_population'],'reference_population':b['reference_population'],
            'coverage':b['coverage'],'rows':b['rows'],'result_hash':b['result_hash']} for k,b in boards.items()}
        expected[name]={k:{'Q':b['coverage']['stages']['Q']['code_rows'],'G':b['coverage']['stages']['G']['code_rows'],
            'V':b['coverage']['stages']['V']['code_rows'],'total':b['coverage']['stages']['total']['code_rows']} for k,b in boards.items()}
    e,r=factory['snapshots']();e=r
    boards={k:dual.run_board(c,e,r,request_id='SYN333:bins:'+k) for k,c in configs.items()}
    # Reuse full-bin producer; every displayed valid row is assigned exactly once.
    artifacts=distribution_artifacts(boards,scope='operating504',data_kind='SYNTHETIC',display_policy=STORED)
    files={'qgv-333-contract.json':configuration_contract(),'synthetic-cases.json':dict(data_kind='SYNTHETIC',cases=cases),
        'expected.json':dict(data_kind='SYNTHETIC',cases=expected,all_bins={g['group_id']:g['bins'] for g in artifacts['distribution-index.json']['groups']})}
    files.update({'bins/'+k:v for k,v in artifacts.items()})
    from investment_system.research.dual_qgv_distribution_index import bin_index_artifacts
    raw={k:dual.json_bytes(v) for k,v in artifacts.items()}
    routes=bin_index_artifacts(raw,expected_manifest_sha256=hashlib.sha256(raw['distribution-manifest.json']).hexdigest())
    files.update({'bin-routing/'+k:v for k,v in routes.items()})
    entries=[]
    for name,value in files.items():
        data=dual.json_bytes(value);assert len(data)<2_000_000
        dest=a.output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        entries.append(dict(path=name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    (a.output/'manifest.json').write_bytes(dual.json_bytes(dict(schema_version='qgv-333-examples/1',data_kind='SYNTHETIC',files=entries)))
    print(json.dumps({'files':len(entries),'maximum_bytes':max(x['size'] for x in entries)}))

if __name__=='__main__':main()
