"""Approved C7 invariants and adversarial algorithm cases, fixture-only numbers."""
from itertools import permutations
from fractions import Fraction
import pytest
from investment_system.evl.selection import (number, frontier, plateau, complexity,
    low_drift, medoids, adjacency)
SCOPE='SYNTHETIC_SOFTWARE_VALIDATION_ONLY'

def bridge():
    params={'P':{'x':0},'B':{'x':1},'Q':{'x':2}}
    vals={'P':[3,1],'B':[1,1],'Q':[1,3]}
    return params,vals

def test_dominated_bridge_preserved_but_never_selectable():
    p,v=bridge(); f=frontier(v,['max','max'])
    assert f==['P','Q']
    g=plateau(p,{'x':[0,1,2]},v,[2,2],f)
    assert g['vertex_universe']==['B','P','Q']
    assert g['survivors']==['P','Q']
    assert g['components'][0]['non_pareto_members']==['B']
    assert len(g['edges'])==2

def test_pareto_only_graph_would_destroy_approved_plateau():
    p,v=bridge()
    g=plateau({k:p[k] for k in ('P','Q')},{'x':[0,1,2]},v,[2,2],['P','Q'])
    assert not g['survivors']
    assert all(not c['stable'] for c in g['components'])

def test_chain_diameter_is_diagnostic_not_edge_tolerance_gate():
    p={str(i):{'x':i} for i in range(4)}
    g=plateau(p,{'x':[0,1,2,3]},{str(i):[i] for i in range(4)},[1],list(p))
    assert len(g['components'])==1
    assert g['components'][0]['metric_diameters']==['3']
    assert len(g['survivors'])==4

def test_all_components_preserved_without_largest_ranking():
    p={str(i):{'x':i} for i in (0,1,2,4,5)}
    g=plateau(p,{'x':list(range(6))},{i:[0] for i in p},[0],list(p))
    assert sorted(len(c['members']) for c in g['components'])==[2,3]
    assert g['survivors']==sorted(p)

@pytest.mark.parametrize('order',list(permutations(('P','B','Q'))))
def test_order_does_not_change_pareto_graph_or_medoid(order):
    p,v=bridge(); p={k:p[k] for k in order};v={k:v[k] for k in order}
    g=plateau(p,{'x':[0,1,2]},v,[2,2],frontier(v,['max','max']))
    m=medoids(['P','Q'],g,p,{'x':[0,1,2]})
    assert m[0]['representatives']==['P','Q']
    assert m[0]['costs']=={'P':'5/4','Q':'5/4'}

def test_multi_cohort_tradeoff_cannot_be_averaged_away():
    v={'A':[10,1,0],'B':[1,10,0],'C':[0,0,0]}
    assert frontier(v,['max','max','min'])==['A','B']

def test_exact_tiny_difference_not_epsilon_tie():
    assert frontier({'A':['1.0000000000000000001'],'B':['1']},['max'])==['A']

def test_ties_are_not_dominance():
    assert frontier({'A':[1,2],'B':[1,2]},['min','max'])==['A','B']

def test_drift_signed_direction_has_no_superiority():
    assert low_drift({'P':[-1],'Q':[0]})['survivors']==['Q']

def test_drift_tradeoffs_remain_vectors():
    d=low_drift({'A':[-1,0,3],'B':[0,-2,1],'C':[3,3,4]})
    assert d['survivors']==['A','B']
    assert d['absolute_normalized_vectors']['A']==['1','0','3']

def test_drift_equal_magnitude_tie():
    assert low_drift({'A':[-1,2],'B':[1,-2]})['survivors']==['A','B']

def test_complexity_is_existing_c5_baseline_departure_count():
    c=complexity({'A':{'x':1,'y':0},'B':{'x':0,'y':1},
                  'C':{'x':1,'y':1}}, {'x':0,'y':0})
    assert c['counts']=={'A':1,'B':1,'C':2}
    assert c['survivors']==['A','B']

def test_center_uses_full_registered_range_not_component_range():
    p={'A':{'x':0,'y':0},'B':{'x':1,'y':0},'C':{'x':2,'y':0}}
    g=plateau(p,{'x':[0,1,2,10],'y':[0]},{i:[0] for i in p},[0],list(p))
    m=medoids(['A','B','C'],g,p,{'x':[0,1,2,10],'y':[0]})[0]
    assert m['representatives']==['B']
    assert m['costs']['B']=='1/50'
    assert m['domain_ranges']['y']=='0'

def test_medoid_restricted_not_dominated_component_center():
    p,v=bridge();g=plateau(p,{'x':[0,1,2]},v,[2,2],['P','Q'])
    m=medoids(['P','Q'],g,p,{'x':[0,1,2]})[0]
    assert m['representatives']==['P','Q']
    assert 'B' not in m['costs']

@pytest.mark.parametrize('bad',[True,float('inf'),float('-inf'),float('nan'),None,{},'NaN'])
def test_invalid_numeric_fails_closed(bad):
    with pytest.raises(ValueError): number(bad)

@pytest.mark.parametrize('left,right,expected',[
    ({'x':0,'y':0},{'x':1,'y':0},True),
    ({'x':0,'y':0},{'x':2,'y':0},False),
    ({'x':0,'y':0},{'x':1,'y':1},False),
    ({'x':0,'y':0},{'x':0,'y':0},False)])
def test_registered_grid_adjacency(left,right,expected):
    assert adjacency(left,right,{'x':[0,1,2],'y':[0,1]}) is expected

@pytest.mark.parametrize('directions',[[],['sum'],['max','min']])
def test_invalid_objective_registration(directions):
    with pytest.raises(ValueError): frontier({'A':[1]},directions)

def test_drift_dimensions_cannot_be_dropped():
    with pytest.raises(ValueError): low_drift({'A':[1,2],'B':[1]})

def test_no_implicit_plateau_tolerance():
    with pytest.raises(ValueError): plateau({'A':{'x':0}},{'x':[0]},{'A':[0]},[],['A'])

from investment_system.evl.landscape import metric_value
from investment_system.evl.selection_contracts import metric_registration
from investment_system.evl.statistical_kernels import MissingStatisticalEvidence

@pytest.mark.parametrize('report',[{}, {'views':{}},
    {'views':{'NET_OF_TRADING_COST_PRE_TAX':{'cagr':None}}}])
def test_legitimate_missing_undefined_support_is_not_run(report):
    with pytest.raises(MissingStatisticalEvidence):
        metric_value(report,metric_registration('cagr','NET_OF_TRADING_COST_PRE_TAX','cagr','max'))

@pytest.mark.parametrize('bad',[float('inf'),float('nan'),True,'invented'])
def test_nonfinite_invalid_required_metric_is_fail(bad):
    with pytest.raises(ValueError):
        metric_value({'views':{'NET_OF_TRADING_COST_PRE_TAX':{'cagr':bad}}},
            metric_registration('cagr','NET_OF_TRADING_COST_PRE_TAX','cagr','max'))

@pytest.mark.parametrize('metric,units',[('downside_capture','DIMENSIONLESS'),
    ('tail_mean_return','DECIMAL_RETURN'),('turnover_sum','TURNOVER'),
    ('mean_period_turnover','TURNOVER_PER_PERIOD'),
    ('net_minus_benchmark_total_return','DECIMAL_RETURN')])
def test_existing_c3_top_level_metrics_are_registered_without_new_derivation(metric,units):
    m=metric_registration(metric,None,metric,'min')
    assert m['path']==[metric] and m['units']==units
    assert metric_value({metric:.1},m)==.1

@pytest.mark.parametrize('view',['benchmark','risk_free'])
def test_existing_c3_control_metric_paths(view):
    m=metric_registration('control_cagr',view,'cagr','max')
    assert metric_value({view:{'cagr':.02}},m)==.02
