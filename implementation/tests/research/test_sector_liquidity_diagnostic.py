from datetime import date
from decimal import Decimal
import pytest
from investment_system.research.exp_deciles import liquidity
from investment_system.research.exp_deciles import sector_comparison


def row(day, vwap='10.25', volume='100', close='10', symbol='TEST'):
    return dict(date=day, source_timestamp=day+'T05:00:00Z', returned_symbol=symbol, price_basis='RAW',
                vwap=vwap, volume=volume, close=close, source_sha256='a'*64)


def test_missing_day_not_zero_and_no_vwap_fallback():
    out=liquidity.summarize([row('2018-02-15'),row('2018-02-16',vwap=None)],
                            signal_day='2018-02-16',symbol='TEST')
    assert out['vwap_volume']['valid_days']==1
    assert out['vwap_volume']['mean_observed']=='1025.00'
    assert out['vwap_volume']['mean_complete'] is None
    assert out['close_volume_proxy']['valid_days']==2
    assert len(out['missing_dates'])==out['expected_sessions']-2
    assert out['market_percentile'] is None


def test_boundaries_duplicates_conflict_and_identity():
    rows=[row('2017-08-16'),row('2018-02-16'),row('2018-02-20')]
    out=liquidity.summarize(rows+[rows[1]],signal_day='2018-02-16',symbol='TEST')
    assert out['observed_sessions']==1 and out['duplicates_removed']==1
    assert out['identity_status']=='UNVERIFIED'
    with pytest.raises(ValueError,match='CONFLICTING_DAY'):
        liquidity.summarize([row('2018-02-16'),row('2018-02-16',volume='101')],signal_day='2018-02-16',symbol='TEST')
    with pytest.raises(ValueError,match='SYMBOL_MISMATCH'):
        liquidity.summarize([row('2018-02-16',symbol='OTHER')],signal_day='2018-02-16',symbol='TEST')


def test_explicit_zero_volume_and_invalid_values():
    out=liquidity.summarize([row('2018-02-15',volume='0'),row('2018-02-16',volume='NaN')],signal_day='2018-02-16',symbol='TEST')
    assert out['vwap_volume']['mean_observed']=='0.00'
    assert out['vwap_volume']['valid_days']==1
    assert out['vwap_volume']['invalid_dates']==['2018-02-16']


def test_rank_change_is_separate_from_coverage():
    a={f'S{i:02}':float(i) for i in range(20)};b=dict(a);b['S19']=None;b['S00']=18.5
    got=sector_comparison.compare_scores(a,b,members=list(a),sectors={})
    assert got['eligible_a']==20 and got['eligible_b']==19
    assert got['coverage_lost']==['S19'] and got['common_eligible']==19
    assert got['common_rank_changes']['S00']==dict(before=19,after=1,delta=18)
    assert got['own_population']['top']['exited']==['S18','S19']  # k changes from 2 to 1


def test_small_n_has_no_fake_rank_comparison():
    got=sector_comparison.compare_scores({'X':None},{'X':None},members=['X'],sectors={})
    assert got['common_rank_changes'] is None
    assert got['reason']=='ELIGIBLE_BELOW_MIN_N'


def test_baseline_uses_existing_engine_and_blocks_unevidenced_candidates():
    import json
    from pathlib import Path
    from investment_system.research.exp_deciles import scoring
    config=json.loads(Path(sector_comparison.__file__).with_name('sector_liquidity_v1.json').read_text())
    result=sector_comparison.baseline_diagnostic({}, {}, population=['UNKNOWN'],groups={'U_A':[]},config=config)
    assert result['baseline']==scoring.score_population({}, {}, population=['UNKNOWN'],include_engine=True)
    assert result['comparisons']['U_A']['eligible_a']==0
    assert result['variants']['B']=='BASELINE_FALLBACK_NO_EVIDENCED_CANDIDATE'
    config['active_sector_candidates']=[{'sector':'invented'}]
    with pytest.raises(ValueError,match='SECTOR_CANDIDATE'):
        sector_comparison.baseline_diagnostic({}, {},population=[],groups={},config=config)
