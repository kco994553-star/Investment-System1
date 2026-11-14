"""Synthetic hand expectations for official-route reuse, not market coverage."""
from copy import deepcopy
import pytest
from investment_system.research.qgv_555_official_share import review_official_share_history
from investment_system.qgv import v2_factors as vf


def source(split=1):
    tax={}
    dates={2022:('old','2023-02-01'),2023:('middle','2024-02-01'),
           2024:('new','2025-02-01'),2025:('basis','2026-02-01')}
    def put(tag,unit,year,value,filing):
        accn,filed=dates[filing]
        tax.setdefault(tag,{'units':{}})['units'].setdefault(unit,[]).append(dict(
            val=value,start=f'{year}-01-01',end=f'{year}-12-31',filed=filed,accn=accn,form='10-K'))
    for filing in range(2022,2026):
        for year in range(max(2022,filing-1),filing+1):
            factor=split if filing>=2024 else 1
            put('EarningsPerShareDiluted','USD/shares',year,(year-2020)/factor,filing)
            put('WeightedAverageNumberOfDilutedSharesOutstanding','shares',year,100*factor,filing)
            put('NetIncomeLoss','USD',year,100*(year-2020),filing)
            put('NetCashProvidedByUsedInOperatingActivities','USD',year,200*(year-2020),filing)
            put('PaymentsToAcquirePropertyPlantAndEquipment','USD',year,20,filing)
    record=dict(cik='0000000001',acquired_at='2026-02-03T00:00:00Z',fiscal_year_end='2025-12-31',
        currency='USD',profile='GENERAL',calc_version='qgv2-calc/2026-10-23.1')
    return dict(cik=1,facts={'us-gaap':tax}),record


def reviewed(p,r):return review_official_share_history(p,r,'SYNTHETIC_ONLY')


def values(p,tag,unit):return p['facts']['us-gaap'][tag]['units'][unit]


def test_exact_common_period_path_reuses_only_raw_math_without_strict_claim():
    p,r=source();prior=deepcopy(p);out=reviewed(p,r)
    eps=out['metrics']['eps_cagr_3y'];cash=out['metrics']['fcf_per_share_cagr_3y']
    assert eps['value']==pytest.approx(.357209)
    assert cash['value']==pytest.approx(round(((980/380)**(1/3)-1),6),abs=1e-6)
    assert out['metrics']['dilution_3y']['value']==0
    for m in out['metrics'].values():
        assert m['adoption_basis']=='EVIDENCE_LINKED' and m['evidence_only_eligible']
        assert not m['requires_assumption'] and not m['strict_verified']
        assert m['additional_verification_required'] and not m['valuation_price_identity_verified']
    assert p==prior and 'rank' not in out and 'score' not in out


def test_disconnected_no_split_factor_one_is_inherited_assumption():
    p,r=source()
    for node in p['facts']['us-gaap'].values():
        for rows in node['units'].values():
            rows[:]=[x for x in rows if int(x['end'][:4])==int(x['filed'][:4])-1]
    out=reviewed(p,r)
    for m in out['metrics'].values():
        assert m['value'] is not None and m['requires_assumption'] and not m['evidence_only_eligible']
        assert m['adoption_basis']=='OFFICIAL_ASSUMPTION_INHERITED'
        assert 'OFFICIAL_NO_OVERLAP_NO_REPORTED_SPLIT_FACTOR_ONE' in m['allowed_assumptions']


@pytest.mark.parametrize('factor',[2,.5])
def test_reported_split_fact_uses_official_adjustment_without_double_adjustment(factor):
    p,r=source(factor)
    p['facts']['us-gaap'][vf.SPLIT_RATIO_CONCEPTS[0]]={'units':{'pure':[
        dict(val=factor,filed='2025-02-01',end='2024-06-01',accn='new',form='10-K')]}}
    out=reviewed(p,r)
    for m in out['metrics'].values():
        assert m['adoption_basis']=='FILING_SPLIT_ADJUSTED' and m['evidence_only_eligible']
    assert out['metrics']['eps_cagr_3y']['value']==pytest.approx(.357209)
    assert out['metrics']['dilution_3y']['value']==0


def test_integer_ratio_without_reported_split_is_not_auto_corrected():
    p,r=source(2);out=reviewed(p,r)
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['adoption_basis']=='EXPLICIT_CONFLICT_EXCLUDED'


def test_official_ordinary_revision_tolerance_is_disclosed_as_assumption():
    p,r=source(1.02);out=reviewed(p,r)
    for m in out['metrics'].values():
        assert m['value'] is not None and not m['evidence_only_eligible']
        assert m['requires_assumption']
        assert 'OFFICIAL_ORDINARY_REVISION_TOLERANCE' in m['allowed_assumptions']


def test_different_filing_values_are_not_all_called_explicit_restatement_conflict():
    p,r=source()
    for row in values(p,'EarningsPerShareDiluted','USD/shares'):
        if row['end']=='2022-12-31' and row['accn']=='middle':row['val']=2.1
    eps=reviewed(p,r)['metrics']['eps_cagr_3y']
    assert eps['value'] is not None and eps['adoption_basis']=='EVIDENCE_LINKED'


@pytest.mark.parametrize('tag,unit,metric',[
    ('EarningsPerShareDiluted','USD/shares','eps_cagr_3y'),
    ('WeightedAverageNumberOfDilutedSharesOutstanding','shares','dilution_3y'),
    ('NetCashProvidedByUsedInOperatingActivities','USD','fcf_per_share_cagr_3y'),
])
def test_same_filing_conflicting_fact_is_not_hidden_by_an_older_value(tag,unit,metric):
    p,r=source();rows=values(p,tag,unit)
    row=next(x for x in rows if x['accn']=='basis' and x['end']=='2025-12-31')
    rows.append(dict(row,val=999))
    m=reviewed(p,r)['metrics'][metric]
    assert m['value'] is None and m['adoption_basis']=='EXPLICIT_CONFLICT_EXCLUDED'


@pytest.mark.parametrize('number',[0,-1])
def test_eps_domain_failure_does_not_withdraw_other_metric_eligibility(number):
    p,r=source()
    for x in values(p,'EarningsPerShareDiluted','USD/shares'):
        if x['end']=='2022-12-31':x['val']=number
    out=reviewed(p,r)
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['reason']=='FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE'
    assert out['metrics']['dilution_3y']['value']==0
    assert out['metrics']['fcf_per_share_cagr_3y']['reusable']


def test_eps_source_does_not_automatically_validate_or_block_fcf_and_dilution():
    p,r=source();del p['facts']['us-gaap']['EarningsPerShareDiluted']
    out=reviewed(p,r)
    assert not out['metrics']['eps_cagr_3y']['reusable']
    assert out['metrics']['fcf_per_share_cagr_3y']['reusable']
    assert out['metrics']['dilution_3y']['reusable']


def test_missing_cash_flow_only_blocks_its_own_metric():
    p,r=source();del p['facts']['us-gaap']['NetCashProvidedByUsedInOperatingActivities']
    out=reviewed(p,r)
    assert not out['metrics']['fcf_per_share_cagr_3y']['reusable']
    assert out['metrics']['eps_cagr_3y']['reusable'] and out['metrics']['dilution_3y']['reusable']


def test_no_cover_reference_is_not_a_history_ratio_block_or_price_validation():
    p,r=source();out=reviewed(p,r)
    m=out['metrics']['dilution_3y']
    assert {x['status'] for x in m['cover_scale_diagnostics']}=={'NO_REFERENCE'}
    assert m['reusable'] and m['evidence_only_eligible']
    assert not m['valuation_price_identity_verified']


def test_scale_mismatch_needs_review_for_wad_metrics_without_changing_reported_eps():
    p,r=source()
    p['facts']['dei']={'EntityCommonStockSharesOutstanding':{'units':{'shares':[
        dict(val=100000000,end='2025-12-31',filed='2026-02-01',accn='basis',form='10-K')]}}}
    out=reviewed(p,r)
    for metric in ('fcf_per_share_cagr_3y','dilution_3y'):
        assert out['metrics'][metric]['value'] is None
        assert out['metrics'][metric]['adoption_basis']=='ADDITIONAL_VERIFICATION_REQUIRED'
        assert 'SHARES_SCALE_UNCONFIRMED' in out['metrics'][metric]['reason']
    assert out['metrics']['eps_cagr_3y']['reusable']


def test_official_share_jump_rejection_is_not_reaccepted_by_reported_eps():
    p,r=source()
    for row in values(p,'WeightedAverageNumberOfDilutedSharesOutstanding','shares'):
        if row['end']=='2022-12-31':row['val']=1000
    out=reviewed(p,r)
    assert not out['metrics']['eps_cagr_3y']['reusable']
    assert out['metrics']['eps_cagr_3y']['adoption_basis']=='EXPLICIT_CONFLICT_EXCLUDED'


def test_future_fact_and_payload_order_do_not_change_current_result():
    p,r=source();base=reviewed(p,r);q=deepcopy(p)
    rows=values(q,'EarningsPerShareDiluted','USD/shares')
    rows.append(dict(rows[-1],filed='2027-01-01',val=999,accn='future'))
    for node in q['facts']['us-gaap'].values():
        for xs in node['units'].values():xs.reverse()
    assert reviewed(q,r)==base


def test_explicit_software_component_conflict_withholds_fcf_reuse():
    p,r=source()
    for year,filing,filed in [(2022,'middle','2024-02-01'),(2025,'basis','2026-02-01')]:
        node=p['facts']['us-gaap'].setdefault('PaymentsForSoftware',{'units':{'USD':[]}})
        row=dict(val=10,start=f'{year}-01-01',end=f'{year}-12-31',accn=filing,filed=filed,form='10-K')
        node['units']['USD'].append(row)
        if year==2025:node['units']['USD'].append(dict(row,val=20))
    m=reviewed(p,r)['metrics']['fcf_per_share_cagr_3y']
    assert not m['reusable'] and m['adoption_basis']=='EXPLICIT_CONFLICT_EXCLUDED'


@pytest.mark.parametrize('change',['issuer','currency','clock'])
def test_source_identity_currency_and_acquired_clock_are_not_invented(change):
    p,r=source()
    if change=='issuer':r['cik']='0000000002'
    elif change=='currency':r['currency']='EUR'
    else:r['acquired_at']='2026-02-03T00:00:00'
    with pytest.raises(ValueError):reviewed(p,r)


@pytest.mark.parametrize('accession',[None,''])
def test_missing_document_id_is_not_an_evidence_link(accession):
    p,r=source()
    for node in p['facts']['us-gaap'].values():
        for xs in node['units'].values():
            for x in xs:
                if accession is None:x.pop('accn')
                else:x['accn']=accession
    out=reviewed(p,r)
    for m in out['metrics'].values():
        assert m['value'] is None and m['adoption_basis']=='ADDITIONAL_VERIFICATION_REQUIRED'
        assert m['unrounded_value'] is not None and not m['evidence_only_eligible']
        assert 'FILING_ACCESSION_UNAVAILABLE' in m['blocking_reasons']


def test_financial_profile_is_not_a_general_fcf_growth_raw_definition():
    p,r=source();r['profile']='FINANCIAL'
    out=reviewed(p,r)
    assert out['metrics']['eps_cagr_3y']['reusable']
    assert out['metrics']['dilution_3y']['reusable']
    assert out['metrics']['fcf_per_share_cagr_3y']['value'] is None
    assert out['metrics']['fcf_per_share_cagr_3y']['unrounded_value'] is None
    assert out['metrics']['fcf_per_share_cagr_3y']['reason']=='OFFICIAL_FINANCIAL_PROFILE_FCF_GROWTH_NOT_APPLICABLE'


def test_missing_intermediate_document_id_cannot_make_an_evidence_chain():
    p,r=source()
    for node in p['facts']['us-gaap'].values():
        for xs in node['units'].values():
            for x in xs:
                if x['accn']=='new':x.pop('accn')
    out=reviewed(p,r)
    assert out['metrics']['eps_cagr_3y']['adoption_basis']=='ADDITIONAL_VERIFICATION_REQUIRED'


def test_published_scores_and_fk_are_not_raw_growth_or_eligibility_inputs():
    p,r=source();base=reviewed(p,r)
    r.update(metrics={'eps_cagr_3y':999},axes={'G':{'score':99}},
        factors={'g_per_share_growth':99},rank=1,
        v_inputs_v2={'ebit_per_share_history':[{'fiscal_year_end':'2022-12-31','share_basis_factor':1.0}]})
    assert reviewed(p,r)==base
    split_payload,record=source(2)
    record['v_inputs_v2']=r['v_inputs_v2']
    assert reviewed(split_payload,record)['metrics']['eps_cagr_3y']['adoption_basis']=='EXPLICIT_CONFLICT_EXCLUDED'
