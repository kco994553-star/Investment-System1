from dataclasses import replace
from datetime import timedelta
from statistics import NormalDist, mean, stdev, variance
import copy
import math
import pytest

from investment_system.evl.statistical_kernels import (
    MissingStatisticalEvidence, aligned_family, period_sharpe, probabilistic_sharpe,
    expected_maximum_sharpe, deflated_sharpe_family, cscv_pbo,
    circular_block_indices, empirical_quantile, joint_circular_bootstrap,
    family_reality_check, excess_family_from_periods)
from investment_system.evl.metrics import ReturnPeriod, summarize
from investment_system.evl.pit import PITObservation
from tests.test_evl_c2 import dt, contract, sample

A=(.01,-.02,.03,-.01,.02,-.03,.04,.005)
B=(.015,-.025,.02,-.005,.03,-.02,.025,.01)


def matrix():
    return {'a':A,'b':B}


def dsr(columns=None,count=16):
    columns=matrix() if columns is None else columns
    spread=variance(period_sharpe(v) for v in columns.values())
    return deflated_sharpe_family(tuple(columns),columns,all_charged_attempts=count,
        candidate_count_provenance='registered-full-family-hash',
        attempt_count_provenance='append-only-ledger-hash',
        registered_sharpe_variance=spread)


def test_period_sharpe_matches_unchanged_c3_and_annualization_units():
    sr=period_sharpe(A)
    assert sr==pytest.approx(mean(A)/stdev(A))
    assert summarize(A,periods_per_year=12)['sharpe']==pytest.approx(sr*math.sqrt(12))


def test_psr_known_symmetric_moment_correction_and_reference_probability():
    values=(-.02,0.,.02)
    r=probabilistic_sharpe(values,reference_sharpe=0.)
    assert r['sharpe_period']==0.
    assert r['skew']==0.
    assert r['kurtosis_nonexcess']==pytest.approx(1.5)
    assert r['moment_correction']==1.
    assert r['probability']==.5
    r=probabilistic_sharpe(values,reference_sharpe=.5)
    assert r['probability']==pytest.approx(NormalDist().cdf(-.5*math.sqrt(2)))


def test_psr_reference_shift_and_positive_scale_metamorphic():
    base=probabilistic_sharpe(A,reference_sharpe=0.)
    scaled=probabilistic_sharpe(tuple(x*10 for x in A),reference_sharpe=0.)
    assert scaled['probability']==pytest.approx(base['probability'])
    assert probabilistic_sharpe(A,reference_sharpe=1.)['probability']<base['probability']
    at_sr=probabilistic_sharpe(A,reference_sharpe=period_sharpe(A))
    assert at_sr['probability']==.5


@pytest.mark.parametrize('values',[(),(.1,),(.1,.2),(.1,.1,.1),(0.,float('nan'),1.),(0.,float('inf'),1.),(False,.1,.2)])
def test_psr_missing_or_invalid_support_never_becomes_fake_probability(values):
    with pytest.raises(ValueError):
        probabilistic_sharpe(values,reference_sharpe=0.)


def test_dsr_both_views_count_provenance_and_conservative_count_sensitivity():
    r=dsr()
    views=r['views']
    assert views['DISTINCT_FULL_CANDIDATES']['trial_count']==2
    assert views['ALL_CHARGED_ATTEMPTS']['trial_count']==16
    assert views['DISTINCT_FULL_CANDIDATES']['count_provenance']=='registered-full-family-hash'
    assert views['ALL_CHARGED_ATTEMPTS']['count_provenance']=='append-only-ledger-hash'
    assert not r['independent_trial_count_estimated']
    assert views['ALL_CHARGED_ATTEMPTS']['reference_sharpe_period']>views['DISTINCT_FULL_CANDIDATES']['reference_sharpe_period']
    for k in matrix():
        assert views['ALL_CHARGED_ATTEMPTS']['candidates'][k]['probability']<views['DISTINCT_FULL_CANDIDATES']['candidates'][k]['probability']


def test_dsr_expected_maximum_published_formula_and_single_trial():
    value=expected_maximum_sharpe(trial_count=10,sharpe_variance=.04)
    gamma=.5772156649015329
    expected=.2*((1-gamma)*NormalDist().inv_cdf(.9)+gamma*NormalDist().inv_cdf(1-1/(10*math.e)))
    assert value==pytest.approx(expected)
    assert expected_maximum_sharpe(trial_count=1,sharpe_variance=.04)==0.
    assert expected_maximum_sharpe(trial_count=10,sharpe_variance=0.)==0.


@pytest.mark.parametrize('change',['subset','unaligned','count','provenance','variance','one_candidate'])
def test_complete_dsr_family_and_registered_variance_fail_closed(change):
    columns=matrix()
    roster=('a','b')
    count=16; cref='family'; aref='ledger'
    spread=variance(period_sharpe(v) for v in columns.values())
    if change=='subset': columns={'a':A}
    if change=='unaligned': columns['b']=B[:-1]
    if change=='count': count=1
    if change=='provenance': aref=''
    if change=='variance': spread+=.1
    if change=='one_candidate': columns={'a':A};roster=('a',)
    with pytest.raises(ValueError):
        deflated_sharpe_family(roster,columns,all_charged_attempts=count,
            candidate_count_provenance=cref,attempt_count_provenance=aref,
            registered_sharpe_variance=spread)


def test_full_cscv_all_combinations_and_tied_selection_mass():
    columns={'a':A,'b':A,'c':A}
    result=cscv_pbo(tuple(columns),columns,block_count=4)
    assert result['partition_count']==math.comb(4,2)==6
    assert len(result['partitions'])==6
    choices=[c for p in result['partitions'] for c in p['tied_winners']]
    assert len(choices)==18
    assert sum(c['weight'] for c in choices)==pytest.approx(1.)
    assert all(c['oos_average_rank']==2 and c['at_median'] for c in choices)
    assert result['pbo']==0. and result['median_equality_mass']==pytest.approx(1.)


def test_cscv_scores_recomputed_from_complete_explicit_complements():
    result=cscv_pbo(('a','b'),matrix(),block_count=4)
    for row in result['partitions']:
        train=tuple(i for block in row['train_blocks'] for i in range(block*2,block*2+2))
        test=tuple(i for block in row['test_blocks'] for i in range(block*2,block*2+2))
        assert set(train).isdisjoint(test) and sorted((*train,*test))==list(range(8))
        for k,values in matrix().items():
            assert row['in_sample_scores'][k]==pytest.approx(period_sharpe(tuple(values[i] for i in train)))
            assert row['out_of_sample_scores'][k]==pytest.approx(period_sharpe(tuple(values[i] for i in test)))
    assert 0<=result['pbo']<=1


@pytest.mark.parametrize('kind',['odd','partial_blocks','zero_variance','shrunk_family'])
def test_cscv_no_dropped_rows_or_invalid_scores(kind):
    columns=matrix(); blocks=4
    if kind=='odd': blocks=3
    if kind=='partial_blocks': columns={k:v[:-1] for k,v in columns.items()}
    if kind=='zero_variance': columns['a']=(.1,)*8
    if kind=='shrunk_family': columns={'a':A}
    with pytest.raises(ValueError):
        cscv_pbo(('a','b'),columns,block_count=blocks)


def test_circular_blocks_wrap_and_share_exact_time_indices():
    indices=circular_block_indices(n=8,block_length=3,replicates=16,seed=7)
    assert indices==circular_block_indices(n=8,block_length=3,replicates=16,seed=7)
    assert any(7 in ix for ix in indices)
    for ix in indices:
        assert len(ix)==8 and all(0<=i<8 for i in ix)
        for start in (0,3,6):
            block=ix[start:start+3]
            assert all(b==(a+1)%8 for a,b in zip(block,block[1:]))


def test_joint_bootstrap_preserves_affine_cross_candidate_and_benchmark_relation():
    columns={'a':A,'b':tuple(2*x+.01 for x in A)}
    benchmark={'eq':tuple(x-.005 for x in A)}
    before=copy.deepcopy((columns,benchmark))
    r=joint_circular_bootstrap(('a','b'),columns,benchmark,block_length=2,replicates=32,seed=7,
        quantiles=(0.,.5,1.),quantile_convention='EMPIRICAL_INVERSE_CDF')
    assert (columns,benchmark)==before
    assert r['mean_replicates']['b']==pytest.approx(tuple(2*x+.01 for x in r['mean_replicates']['a']))
    assert r['mean_replicates']['eq']==pytest.approx(tuple(x-.005 for x in r['mean_replicates']['a']))
    for ix,value in zip(r['sample_indices'],r['mean_replicates']['a']):
        assert value==pytest.approx(mean(A[i] for i in ix))
    assert r==joint_circular_bootstrap(('b','a'),dict(reversed(list(columns.items()))),benchmark,
        block_length=2,replicates=32,seed=7,quantiles=(0.,.5,1.),quantile_convention='EMPIRICAL_INVERSE_CDF')


def test_empirical_quantiles_are_explicit_actual_observations_not_interpolated():
    assert empirical_quantile((3.,1.,2.,4.),.5,convention='EMPIRICAL_INVERSE_CDF')==2.
    assert empirical_quantile((3.,1.),0.,convention='EMPIRICAL_INVERSE_CDF')==1.
    assert empirical_quantile((3.,1.),1.,convention='EMPIRICAL_INVERSE_CDF')==3.
    with pytest.raises(ValueError):
        empirical_quantile((1.,2.),.5,convention='unspecified')


@pytest.mark.parametrize('args',[
    {'n':0,'block_length':1,'replicates':2,'seed':7},
    {'n':8,'block_length':9,'replicates':2,'seed':7},
    {'n':8,'block_length':2,'replicates':0,'seed':7},
    {'n':8,'block_length':True,'replicates':2,'seed':7},
    {'n':8,'block_length':2,'replicates':2,'seed':None}])
def test_invalid_resampling_dimensions_blocked(args):
    with pytest.raises(ValueError): circular_block_indices(**args)


def test_reality_check_identical_benchmark_and_manual_centered_family_draws():
    r=family_reality_check(('a','b'),{'a':A,'b':A},A,block_length=2,replicates=16,seed=7)
    assert r['observed_max_mean_statistic']==0.
    assert r['centered_bootstrap_statistics']==(0.,)*16
    assert r['tail_fraction']==1.
    columns=matrix();benchmark=(.001,)*8
    r=family_reality_check(('a','b'),columns,benchmark,block_length=2,replicates=16,seed=7)
    indices=circular_block_indices(n=8,block_length=2,replicates=16,seed=7)
    diffs={k:tuple(x-.001 for x in v) for k,v in columns.items()}
    expected=tuple(math.sqrt(8)*max(mean(d[i]-mean(d) for i in ix) for d in diffs.values()) for ix in indices)
    assert r['centered_bootstrap_statistics']==pytest.approx(expected)
    assert r['tail_fraction']==sum(x>=r['observed_max_mean_statistic'] for x in expected)/16
    assert r['decision']=='NOT_ASSESSED_PENDING_C8'


def test_family_reality_check_never_accepts_selected_subset_or_missing_benchmark():
    with pytest.raises(MissingStatisticalEvidence):
        family_reality_check(('a','b'),{'a':A},A,block_length=2,replicates=16,seed=7)
    with pytest.raises(MissingStatisticalEvidence):
        family_reality_check(('a','b'),matrix(),A[:-1],block_length=2,replicates=16,seed=7)


def qualified_periods():
    start=dt(2014,6)
    periods=[]; samples=[]
    for i,value in enumerate(A):
        s=start+timedelta(days=i);e=s+timedelta(days=1)
        samples.append(sample('s'+str(i),s,e))
        periods.append(ReturnPeriod(s,e,value,.001,.002,0.,0.,0.,'USD',
            PITObservation('rf'+str(i),s,'fixture','v1'),
            PITObservation('out'+str(i),e,'fixture','v1'),
            PITObservation('cpi'+str(i),e,'fixture','v1')))
    return tuple(samples),tuple(periods)


def test_c2_c3_adapter_uses_approved_net_arithmetic_risk_free_excess():
    samples,periods=qualified_periods()
    r=excess_family_from_periods(('a','b'),{'a':periods,'b':periods},samples,
        split=contract(),partition='train',stress=False,evaluation_time=dt(2020))
    assert r['series']['a']==pytest.approx(tuple(x-.003 for x in A))
    assert r['period_hashes']['a']==r['period_hashes']['b']
    assert r['definition']=='NET_PRE_TAX_MINUS_RISK_FREE_ARITHMETIC_PERIOD_RETURN'


@pytest.mark.parametrize('kind',['holdout','future_feature','future_rf','unpublished_outcome','period_mismatch','mixed_currency','wrong_partition','partial_family'])
def test_adapter_pit_lineage_and_holdout_isolation(kind):
    samples,periods=qualified_periods()
    columns={'a':periods,'b':periods}; partition='train'
    if kind=='holdout': samples=(sample('holdout',dt(2017)),*samples[1:])
    if kind=='future_feature':
        samples=(replace(samples[0],observations=(PITObservation('future',samples[0].label_end,'fixture','v1'),)),*samples[1:])
    if kind=='future_rf':
        columns['a']=(replace(periods[0],risk_free_stamp=replace(periods[0].risk_free_stamp,available_at=periods[0].end)),*periods[1:])
    if kind=='unpublished_outcome':
        columns['a']=(replace(periods[0],outcome_stamp=replace(periods[0].outcome_stamp,available_at=dt(2021))),*periods[1:])
    if kind=='period_mismatch': columns['a']=(replace(periods[0],end=periods[0].end+timedelta(hours=1)),*periods[1:])
    if kind=='mixed_currency': columns['a']=(replace(periods[0],currency='KRW'),*periods[1:])
    if kind=='wrong_partition': partition='oos'
    if kind=='partial_family': columns={'a':periods}
    with pytest.raises(ValueError):
        excess_family_from_periods(('a','b'),columns,samples,split=contract(),partition=partition,
            stress=False,evaluation_time=dt(2020))
