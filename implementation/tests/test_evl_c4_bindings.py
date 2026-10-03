from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from investment_system.contracts.lineage import StampedValue
from investment_system.contracts.models import DataStamp, PortfolioSnapshot, Holding
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.evl.bindings import evaluate_bound, validate_parameters

D = datetime(2020,1,10,tzinfo=timezone.utc)


def point(value, i=0):
    instant = D-timedelta(days=3-i)
    stamp=DataStamp('s'+str(i),'provider','PRICE','raw-'+str(i),instant,instant,
                    D+timedelta(days=100),synthetic=True)
    return StampedValue(value,instant,stamp,'v1')


def portfolio():
    return PortfolioSnapshot('pf','v1',D,'USD',(Holding('a','A',.5,actual_weight=.45),
        Holding('b','B',.5,actual_weight=.55)),0.,1.,'p','FIXTURE',True)


def inputs():
    return {'a':(point(-.005),point(-.005,1),point(.006,2)),
            'b':(point(.001),point(.001,1),point(.001,2))}


def indicators():
    return {'growth':point(.02),'inflation':point(.02,1)}


def run(parameters):
    return evaluate_bound(D,portfolio(),inputs(),indicators(),parameters,synthetic=True)


def test_technical_stamped_preserves_original_decision_and_derives_availability():
    rows=inputs()['a']
    old=TechnicalEngine().evaluate('a',D,[r.value for r in rows])
    new=TechnicalEngine().evaluate_stamped('a',D,rows,synthetic=True)
    assert (old.regime,old.execution_zone,old.scenarios)==(new.regime,new.execution_zone,new.scenarios)
    assert new.available_at==rows[-1].stamp.available_at < D
    assert new.input_hash and new.data_stamp_refs==('s0','s1','s2')
    assert new.source_vintages==(('s0','v1'),('s1','v1'),('s2','v1'))
    assert old.available_at is None


def test_macro_stamped_preserves_confirmed_rules_without_defaulting_missing_inputs():
    old=MacroEngine().evaluate(D,{'growth':.02,'inflation':.02})
    new=MacroEngine().evaluate_stamped(D,indicators(),synthetic=True)
    assert (new.state,new.regime,new.macro_version)==(old.state,old.regime,old.macro_version)
    with pytest.raises(ValueError,match='requires'):
        MacroEngine().evaluate_stamped(D,{'growth':point(.02)},synthetic=True)


@pytest.mark.parametrize('change', ['future','missing_vintage','estimated','naive','synthetic'])
def test_lineage_cannot_be_fabricated_from_as_of(change):
    p=point(.01)
    synthetic=True
    if change=='future': p=replace(p,stamp=replace(p.stamp,available_at=D+timedelta(days=1)))
    if change=='missing_vintage': p=replace(p,vintage='')
    if change=='estimated': p=replace(p,stamp=replace(p.stamp,estimated=True))
    if change=='naive': p=replace(p,measured_at=p.measured_at.replace(tzinfo=None))
    if change=='synthetic': synthetic=False
    with pytest.raises(ValueError):
        TechnicalEngine().evaluate_stamped('a',D,(p,),synthetic=synthetic)


def test_cash_buffer_changes_exposure_and_does_not_mutate_input():
    p=portfolio()
    before=p.to_dict()
    zero=run({'cash_buffer':0.})
    cash=run({'cash_buffer':.2})
    assert sum(zero['integration'].target_weights.values())==pytest.approx(1.)
    assert sum(cash['integration'].target_weights.values())==pytest.approx(.8)
    assert cash['cash_weight']==pytest.approx(.2)
    assert p.to_dict()==before


def test_lookback_changes_actual_technical_zone_and_integrated_targets():
    full=run({'technical_lookback':3})
    short=run({'technical_lookback':1})
    assert full['technical']['a'].execution_zone != short['technical']['a'].execution_zone
    assert full['integration'].target_weights != short['integration'].target_weights
    assert short['technical']['a'].data_stamp_refs==('s2',)


def test_deadband_changes_intents_but_not_target_weight_performance():
    small=run({'execution_deadband_pp':1.})
    large=run({'execution_deadband_pp':10.})
    assert small['integration'].order_intents and not large['integration'].order_intents
    assert small['integration'].target_weights==large['integration'].target_weights
    with pytest.raises(ValueError,match='order-only'):
        validate_parameters({'execution_deadband_pp':1.},performance_search=True)


@pytest.mark.parametrize('name',['risk_multiplier','signal_threshold','macro_warning_sensitivity','q_weights'])
def test_undefined_and_frozen_settings_do_not_silently_pass(name):
    with pytest.raises(ValueError,match='unbound or frozen'):
        run({name:1.})


def test_insufficient_lookback_or_missing_technical_membership_fails_closed():
    with pytest.raises(ValueError,match='insufficient'):
        run({'technical_lookback':4})
    with pytest.raises(ValueError,match='membership'):
        evaluate_bound(D,portfolio(),{'a':inputs()['a']},indicators(),{},synthetic=True)


def test_legacy_snapshot_serialization_keeps_qualification_unknown():
    old=TechnicalEngine().evaluate('a',D,[.01])
    assert old.to_dict()['available_at'] is None
    assert old.to_dict()['input_hash'] is None
