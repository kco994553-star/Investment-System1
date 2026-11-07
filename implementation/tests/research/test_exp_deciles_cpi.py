"""2025-dollar cap thresholds: synthetic releases, never real CPI observations."""
import copy
from decimal import Decimal as D
from fractions import Fraction
import pytest
from investment_system.research.exp_deciles import runner, settings, synthetic as syn, universe


def cpi_input():
    def evidence():
        return dict(source='https://example.invalid/synthetic-cpi', source_sha256='a'*64,
                    data_version='synthetic-v1', evidence_status='SYNTHETIC')
    return dict(schema='exp-deciles-cpi-input/1', series_id='CUUR0000SA0', index_base='1982-84=100',
                base=dict(year=2025, aggregation='ANNUAL_AVERAGE', value='300',
                          vintage_at='2026-01-15T08:30:00-05:00', **evidence()),
                calendar=dict(coverage_start='2018-01-01', coverage_end='2019-12-31', **evidence(), releases=[
                    dict(month='2017-12', released_at='2018-01-12T08:30:00-05:00'),
                    dict(month='2018-01', released_at='2018-02-14T08:30:00-05:00'),
                    dict(month='2019-01', released_at='2019-02-13T08:30:00-05:00')]),
                observations=[dict(month='2017-12', value='210', vintage_at='2018-01-12T08:30:00-05:00', **evidence()),
                    dict(month='2018-01', value='240', vintage_at='2018-02-14T08:30:00-05:00', **evidence()),
                    dict(month='2018-01', value='270', vintage_at='2018-03-01T08:30:00-05:00', **evidence()),
                    dict(month='2019-01', value='300', vintage_at='2019-02-13T08:30:00-05:00', **evidence())],
                signal_cutoffs={'2018-02-16':'2018-02-16T16:00:00-05:00',
                                '2019-02-15':'2019-02-15T16:00:00-05:00'})


def resolve(data=None, day='2018-02-16'):
    # Import inside the test: missing implementation is an assertion failure, not test collection failure.
    from investment_system.research.exp_deciles import cap_thresholds
    return cap_thresholds.resolve(cpi_input() if data is None else data, day)


def test_latest_released_month_uses_then_known_vintage_and_future_base_is_only_numeraire():
    r=resolve()
    assert r['status']=='SYNTHETIC' and r['observation_month']=='2018-01'
    assert r['monthly_cpi']==D('240') and r['base_cpi']==D('300')
    assert r['thresholds']==dict(c2_min_usd=D('160000000'),u_a_entry_usd=D('200000000'),
                                u_a_stay_usd=D('160000000'),u_b_min_usd=D('8000000000'))
    assert r['vintage_at']=='2018-02-14T08:30:00-05:00'
    assert r['released_at']=='2018-02-14T08:30:00-05:00'
    assert r['monthly_source']['data_version']=='synthetic-v1'


@pytest.mark.parametrize('change,reason',[
    ('latest_missing','CPI_VINTAGE_UNAVAILABLE'),('late_revision_only','CPI_VINTAGE_UNAVAILABLE'),
    ('unverified','CPI_EVIDENCE_UNVERIFIED'),('calendar','CPI_CALENDAR_COVERAGE_MISSING'),
    ('base','CPI_BASE_UNAVAILABLE'),('cutoff','CPI_SIGNAL_TIME_MISSING')])
def test_missing_evidence_never_falls_back_to_older_month_or_nominal(change,reason):
    data=cpi_input()
    if change=='latest_missing':data['observations']=[x for x in data['observations'] if x['month']!='2018-01']
    if change=='late_revision_only':data['observations']=[x for x in data['observations'] if x['vintage_at']!='2018-02-14T08:30:00-05:00']
    if change=='unverified':data['observations'][1]['evidence_status']='UNVERIFIED'
    if change=='calendar':data['calendar']['coverage_end']='2018-02-15'
    if change=='base':data['base']=None
    if change=='cutoff':data['signal_cutoffs']={}
    r=resolve(data)
    assert r['status']=='BLOCKED' and reason in r['reasons'] and r['thresholds'] is None


def test_release_after_signal_on_same_date_not_yet_usable():
    data=cpi_input();data['calendar']['releases'][1]['released_at']='2018-02-16T16:01:00-05:00'
    data['observations'][1]['vintage_at']='2018-02-16T16:01:00-05:00'
    r=resolve(data)
    assert r['observation_month']=='2017-12' and r['thresholds']['u_a_entry_usd']==D('175000000')


@pytest.mark.parametrize('key,value',[('series_id','CUSR0000SA0'),('index_base','other')])
def test_wrong_series_or_index_unit_refused(key,value):
    data=cpi_input();data[key]=value
    with pytest.raises(ValueError,match='CPI_SERIES_INVALID'): resolve(data)


def test_direct_api_does_not_ignore_cpi_under_legacy_default():
    with pytest.raises(ValueError,match='CPI_RESOURCE_WITH_NOMINAL_POLICY'):
        universe.build_universes([],signal_day='2018-02-16',cpi=cpi_input())


def rec(i, cap):
    return dict(security_id=f'TEST{i}',cik=str(i),listed=True,security_type='COMMON',
                shares_outstanding='1000000',shares_filed='2018-01-02',shares_period_end='2017-12-31',
                share_price_basis='CONFIRMED',price=str(D(cap)/D('1000000')),price_label='SYNTHETIC')


def test_real_threshold_boundary_first_build_stay_leave_reentry_and_c2_independence():
    records=[rec(1,'200000000'),rec(2,'160000000'),rec(3,'159999999.99'),rec(4,'8000000000')]
    kw=dict(signal_day='2018-02-16',market_cap_version='cpi-2025-v1',cpi=cpi_input())
    first=universe.build_universes(records,**kw)
    assert first['U_A']['member_securities']==('TEST1','TEST4')
    assert first['C2']['member_securities']==('TEST1','TEST2','TEST4')
    assert first['U_B']['member_securities']==('TEST4',)
    later=universe.build_universes(records,previous_u_a=['2','3'],**kw)
    assert later['U_A']['member_securities']==('TEST1','TEST2','TEST4')
    assert later['issuers']['0000000003']['U_A']['status']=='EXCLUDED'
    # A former member now absent from the immediate previous membership must re-enter at 200m.
    reentry=universe.build_universes([rec(2,'190000000')],previous_u_a=[],**kw)
    assert reentry['U_A']['member_securities']==() and reentry['C2']['member_securities']==('TEST2',)
    # Unknown prior membership in the band is still UNKNOWN for U-A, but doesn't contaminate C2.
    uncertain=universe.build_universes([rec(2,'190000000')],previous_u_a=[],previous_u_a_unknown=['2'],**kw)
    assert uncertain['U_A']['unknown']==('0000000002',) and uncertain['C2']['member_securities']==('TEST2',)


def test_new_selection_scores_c2_without_changing_qgv_missing_rules_or_legacy_settings():
    args=dict(year=2018,companyfacts=syn.companyfacts_by_cik(),filing_rows=syn.filing_rows(),quotes=syn.quotes(2018))
    old=runner.selection_stage(syn.records(2018),**args)
    new=runner.selection_stage(syn.records(2018),market_cap_version='cpi-2025-v1',cpi=cpi_input(),**args)
    assert old['settings_sha256']!=new['settings_sha256']
    assert old['counts']['U_A']['eligible']==30 and new['counts']['U_A']['eligible']==31
    assert new['scores']['scoring_population']=='C2_AT_S_CPI2025'
    assert new['operational_d11']==old['operational_d11']=='NOT_APPLIED_OWNER_DECISION_PENDING'
    assert new['signal']==old['signal']
    assert new['universe']['C2']['members']==new['universe']['U_A']['members']
    assert new['market_cap_context']['status']=='SYNTHETIC'
    assert settings.settings_dict()==settings.settings_dict('nominal-v1')

# Existing CLI fixture controls only code-state provenance, not calculations or policy.
from test_exp_deciles_cli import cli, write_bundle, WHEN
import json, hashlib


def write_cpi_bundle(path):
    manifest=write_bundle(path)
    body=(json.dumps(cpi_input(),sort_keys=True)+'\n').encode()
    (path/'cpi.json').write_bytes(body)
    md=json.loads(manifest.read_text())
    md['resources'].append(dict(name='cpi',path='cpi.json',sha256=hashlib.sha256(body).hexdigest(),
                               source='SYNTHETIC',period='2018-2019 + fixed2025 base',rights_note='invented test data'))
    manifest.write_text(json.dumps(md))
    return manifest


def test_cli_new_default_requires_cpi_and_never_silently_uses_nominal(cli,tmp_path,capsys):
    manifest=write_bundle(tmp_path/'input')
    code=cli.main(['select','--manifest',str(manifest),'--year','2018','--out',str(tmp_path/'out')])
    assert code==2 and 'CPI_INPUT_MISSING' in capsys.readouterr().err
    assert not (tmp_path/'out'/'selection_inputs.json').exists()


def test_cpi_cli_manifest_settings_replay_and_hysteresis_chain(cli,tmp_path,capsys):
    manifest=write_cpi_bundle(tmp_path/'input')
    results=[]
    for folder in ['first','replay']:
        assert cli.main(['select','--manifest',str(manifest),'--year','2018','--out',str(tmp_path/folder),
                         '--generated-at',WHEN])==0
        results.append((tmp_path/folder/'selection_inputs.json').read_bytes())
    assert results[0]==results[1]
    one=json.loads(results[0]);meta=json.loads((tmp_path/'first'/'manifest.json').read_text())
    assert meta['settings']['schema']=='exp-deciles-settings/2'
    assert meta['settings']['scoring']['population']=='C2_AT_S_CPI2025'
    assert '--market-cap-version' in meta['reproduction']['argv']
    assert one['market_cap_context']['monthly_cpi']=='240'
    assert cli.main(['select','--manifest',str(manifest),'--year','2019',
                     '--previous-u-a',str(tmp_path/'first'/'selection_inputs.json'),
                     '--out',str(tmp_path/'second'),'--generated-at',WHEN])==0
    assert cli.main(['verify','--run',str(tmp_path/'second')])==0
    two=json.loads((tmp_path/'second'/'selection_inputs.json').read_text())
    assert two['previous_u_a']==one['universe']['U_A']['members']
    assert two['universe']['thresholds']['u_a_stay_usd']=='200000000'
    assert one['settings_sha256']==two['settings_sha256']
    assert two['market_cap_context']['base_cpi']==one['market_cap_context']['base_cpi']
    printed=capsys.readouterr().out
    assert 'XQ' not in printed and '240.0' not in printed


def test_annual_base_cannot_be_a_forecast_published_before_2025_finished():
    data=cpi_input();data['base']['vintage_at']='2025-06-01T08:30:00-04:00'
    with pytest.raises(ValueError,match='CPI_BASE_BEFORE_YEAR_END'):resolve(data)


def test_c2_prices_and_facts_include_non_member_and_never_select_it_into_u_a():
    records=syn.records(2018);quotes=syn.quotes(2018)
    next(r for r in records if r['security_id']=='XQ033')['price']=D('1.8') # 180m: C2>=160m, first UA<200m
    quotes['XQ033']['price']=D('1.8')
    out=runner.selection_stage(records,year=2018,companyfacts=syn.companyfacts_by_cik(),
            filing_rows=syn.filing_rows(),quotes=quotes,market_cap_version='cpi-2025-v1',cpi=cpi_input())
    assert out['counts']['C2']['eligible']==31 and out['counts']['U_A']['eligible']==30
    assert 'XQ033' in out['scores']['securities']
    assert out['scores']['securities']['XQ033']['quote_status']=='SUPPLIED'
    for strategy in out['selections'].values():
        assert 'XQ033' not in strategy['U_A']['order']


def test_duplicate_vintage_is_refused_even_if_values_match():
    data=cpi_input();data['observations'].append(copy.deepcopy(data['observations'][1]))
    with pytest.raises(ValueError,match='CPI_VINTAGE_DUPLICATE'):resolve(data)


def test_mixed_nominal_and_real_selection_cannot_form_one_ledger():
    args=dict(companyfacts=syn.companyfacts_by_cik(),filing_rows=syn.filing_rows())
    one=runner.selection_stage(syn.records(2018),year=2018,quotes=syn.quotes(2018),**args)
    state=runner.u_a_state(one)
    two=runner.selection_stage(syn.records(2019),year=2019,quotes=syn.quotes(2019),
            previous_u_a=state['members'],previous_u_a_unknown=state['unknown'],previous_u_a_securities=state['securities'],
            market_cap_version='cpi-2025-v1',cpi=cpi_input(),**args)
    with pytest.raises(ValueError,match='SELECTION_MARKET_CAP_POLICY_MISMATCH'):
        runner.ledger_stage([one,two],prices=[],events=[])


def test_cpi_cli_reaches_existing_ledger_with_nominal_nav_and_blocks_mixed_policy(cli,tmp_path,capsys):
    manifest=write_cpi_bundle(tmp_path/'input')
    select=tmp_path/'select'
    assert cli.main(['select','--manifest',str(manifest),'--year','2018','--out',str(select),
                     '--generated-at',WHEN])==0
    argv=['ledger','--manifest',str(manifest),'--selection',str(select/'selection_inputs.json'),
          '--end','2018-02-21','--generated-at',WHEN]
    assert cli.main(argv+['--out',str(tmp_path/'ledger')])==0
    out=json.loads((tmp_path/'ledger'/'ledger_outputs.json').read_text())
    assert out['market_cap_version']=='cpi-2025-v1' and out['currency']=='USD'
    assert out['run']['settings']['market_cap_policy']['return_inflation_adjustment'] is False
    assert out['run']['settings']['account']['cost_bps_per_side']=='10'
    for p in out['portfolios'].values():
        for scenarios in p['runs'].values():
            for run in scenarios.values():
                for row in run['daily']:
                    # Exact nominal account normalization; no CPI price/return multiplier.
                    assert Fraction(row['nav_index'])==Fraction(row['nav'])/10000
    assert cli.main(['verify','--run',str(tmp_path/'ledger')])==0
    assert cli.main(argv+['--out',str(tmp_path/'wrong'),'--market-cap-version','nominal-v1'])==2
    assert 'CPI_RESOURCE_WITH_NOMINAL_POLICY' in capsys.readouterr().err
