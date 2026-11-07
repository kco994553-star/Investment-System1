"""Published handoff cases: consumers can run the same expected outcomes."""
import json
from pathlib import Path
import pytest

from investment_system.research.common_classification.records import resolve
from investment_system.research.common_classification.technical_macro import technical_groups
from investment_system.research.exp_deciles.technical_leaderboard import filter_board

FIXTURE=json.loads((Path(__file__).parents[2]/'docs/research/common_classification/fixtures.json').read_text())


@pytest.mark.parametrize('name',FIXTURE['record_cases'])
def test_shared_record_case(name):
    case=FIXTURE['record_cases'][name]; want=case['expected']
    if want.get('error'):
        with pytest.raises(ValueError,match=want['error']):
            resolve(case['store'],valuation_date=case['valuation_date'],knowledge_as_of=case['knowledge_as_of'])
        return
    result=resolve(case['store'],valuation_date=case['valuation_date'],knowledge_as_of=case['knowledge_as_of'])
    assert len(result['rows'])==want['member_count']
    row=result['rows'][0]
    assert row['sector']['status']==want['sector_status']
    assert row['industry']['status']==want['industry_status']
    if want['reason']: assert want['reason'] in row['sector']['reasons']
    if 'sector_id' in want: assert row['sector']['id']==want['sector_id']


@pytest.mark.parametrize('name',FIXTURE['technical_cases'])
def test_shared_technical_case(name):
    c=FIXTURE['technical_cases'][name];w=c['expected']
    args={k:v for k,v in c.items() if k!='expected'}
    if w['error']:
        with pytest.raises(ValueError,match=w['error']): technical_groups(**args)
        return
    result=technical_groups(**args)
    group=next(g for g in result['groups'] if g['sector_id']=='INFORMATION_TECHNOLOGY')
    assert group['membership_status']==w['membership_status']
    metric=group['board']['metrics']['momentum_3m']
    assert metric['n_valid']==w['n_valid'] and metric['k']==w['k']
    if w['filtered_ranks']:
        selected=filter_board(group['board'],[{'metric':'volatility_6m','condition':'exclude_D10'}])
        assert [r['rank'] for r in metric['rows'] if r['security_id'] in selected]==w['filtered_ranks']
