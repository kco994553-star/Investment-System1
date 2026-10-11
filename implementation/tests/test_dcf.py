import copy
import importlib
import json
from pathlib import Path
from decimal import Decimal,getcontext
import pytest

def api():return importlib.import_module('investment_system.qgv.dcf')
def params():
    x=json.loads((Path(__file__).parents[1]/'src/investment_system/qgv/dcf_config_v1.json').read_text())
    x.update(confirmed=True,discount_rate=.10,terminal_growth=.02,cashflow_basis='FCFE_PER_SHARE',discount_rate_basis='COST_OF_EQUITY',currency='USD',per_share_basis_confirmed=True)
    x['solver'].update(growth_lower=-.5,growth_upper=1.)
    return x

def forward(cashflow=1.,growth=.05,config=None):return api().two_stage_dcf(cashflow_per_share=cashflow,growth_rate=growth,parameters=config or params(),cashflow_currency='USD')
def reverse(price,config=None):return api().reverse_dcf(cashflow_per_share=1.,price=price,parameters=config or params(),cashflow_currency='USD',price_currency='USD')

def test_unapproved_defaults_remain_not_available():
    x=json.loads((Path(__file__).parents[1]/'src/investment_system/qgv/dcf_config_v1.json').read_text())
    r=forward(config=x)
    assert r.state=='NOT_AVAILABLE' and r.reason_codes==('PARAMETER_APPROVAL_PENDING',) and r.value_per_share is None

def test_constant_perpetuity_reference():
    x=params();x['terminal_growth']=0
    r=forward(growth=0,config=x)
    assert r.value_per_share==pytest.approx(10.) and r.state=='PROVISIONAL'

def test_two_stage_matches_independent_decimal_reference():
    getcontext().prec=45;d=Decimal
    f=d('1');growth=d('.05');r=d('.10');g=d('.02')
    expected=sum(f*(1+growth)**t/(1+r)**t for t in range(1,6))+f*(1+growth)**5*(1+g)/(r-g)/(1+r)**5
    out=forward()
    assert out.value_per_share==pytest.approx(float(expected),rel=1e-13)
    assert len(out.discounted_cashflows)==5

@pytest.mark.parametrize('growth',[-.30,0,.05,.20,.90])
def test_reverse_reconstructs_implied_growth_without_echoing_price(growth):
    value=forward(growth=growth).value_per_share
    r=reverse(value)
    assert r.implied_growth==pytest.approx(growth,abs=1e-9) and r.state=='PROVISIONAL'
    assert 'price' not in r.__dict__ and str(value) not in repr(r)

def test_endpoint_roots_and_unbracketed_price():
    x=params()
    for endpoint in (-.5,1):
        r=reverse(forward(growth=endpoint).value_per_share)
        assert r.implied_growth==endpoint
    r=reverse(forward(growth=2).value_per_share)
    assert r.reason_codes==('ROOT_NOT_BRACKETED',) and r.implied_growth is None

@pytest.mark.parametrize('updates,reason',[
 ({'discount_rate':None},'PARAMETER_INVALID'),
 ({'terminal_growth':.10},'GORDON_RATE_ORDER'),
 ({'discount_rate':True},'PARAMETER_INVALID'),
 ({'discount_rate':float('nan')},'PARAMETER_INVALID'),
 ({'cashflow_basis':'FCFF'},'CASHFLOW_BASIS_UNCONFIRMED'),
 ({'discount_rate_basis':'WACC'},'CASHFLOW_BASIS_UNCONFIRMED'),
 ({'per_share_basis_confirmed':False},'SHARE_BASIS_UNCONFIRMED'),
 ({'explicit_years':5.0},'PARAMETER_INVALID'),
 ({'currency':None},'CURRENCY_BASIS_UNCONFIRMED'),
])
def test_parameter_errors_never_compute(updates,reason):
    x=params();x.update(updates)
    r=forward(config=x)
    assert r.state=='NOT_AVAILABLE' and r.reason_codes==(reason,) and r.value_per_share is None

@pytest.mark.parametrize('cashflow,growth',[(None,.1),(True,.1),(float('nan'),.1),(1,-1),(1,float('inf')),(10**999,.1)])
def test_invalid_inputs_fixed_codes_no_zero_substitute(cashflow,growth):
    assert forward(cashflow,growth).state=='NOT_AVAILABLE'

def test_zero_cashflow_is_real_zero_and_reverse_nonidentifiable():
    assert forward(0).value_per_share==0
    r=api().reverse_dcf(cashflow_per_share=0,price=10,parameters=params(),cashflow_currency='USD',price_currency='USD')
    assert r.reason_codes==('NON_POSITIVE_CASHFLOW',)

def test_currency_mismatch_no_conversion_and_mutation_free():
    x=params();before=copy.deepcopy(x)
    r=api().reverse_dcf(cashflow_per_share=1,price=10,parameters=x,cashflow_currency='USD',price_currency='JPY')
    assert r.reason_codes==('CURRENCY_BASIS_UNCONFIRMED',) and x==before

@pytest.mark.parametrize('solver',[
 {'growth_lower':None}, {'growth_upper':-.5},{'growth_lower':-1},
 {'maximum_iterations':True},{'relative_price_tolerance':0}, {'maximum_iterations':0}])
def test_invalid_solver_returns_fixed_reason(solver):
    x=params();x['solver'].update(solver)
    assert reverse(20,config=x).reason_codes==('SOLVER_INVALID',)

def test_nonconvergence_and_numeric_overflow_are_not_results():
    x=params();x['solver']['maximum_iterations']=1
    assert reverse(forward(growth=.13).value_per_share,config=x).reason_codes==('ROOT_NOT_CONVERGED',)
    assert forward(1e308,1e308).reason_codes==('NUMERIC_OVERFLOW',)

def test_custom_period_is_parameterized_and_not_implicit_model_adoption():
    x=params();x['explicit_years']=3
    r=forward(config=x)
    assert len(r.discounted_cashflows)==3 and r.model_status=='NOT_APPLIED' and r.role=='RAM_ONLY_RESEARCH'


def test_reverse_missing_price_currency_does_not_infer_matching_currency():
    r=api().reverse_dcf(cashflow_per_share=1,price=10,parameters=params(),cashflow_currency='USD',price_currency=None)
    assert r.state=='NOT_AVAILABLE' and r.reason_codes==('CURRENCY_BASIS_UNCONFIRMED',)
