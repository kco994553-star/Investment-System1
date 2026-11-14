from copy import deepcopy
import pytest
from investment_system.research.qgv_555_share_review import review_share_history


def source(split=1,eps_consistent=True):
    tax={};dates={2022:('old','2023-02-01'),2023:('middle','2024-02-01'),2024:('new','2025-02-01'),2025:('basis','2026-02-01')}
    def put(tag,unit,year,value,filing):
        accn,filed=dates[filing]
        tax.setdefault(tag,{'units':{}})['units'].setdefault(unit,[]).append(dict(val=value,start=f'{year}-01-01',end=f'{year}-12-31',filed=filed,accn=accn,form='10-K'))
    for filing in range(2022,2026):
        for year in range(max(2022,filing-1),filing+1):
            factor=split if filing>=2024 else 1
            put('EarningsPerShareDiluted','USD/shares',year,(year-2020)/factor if eps_consistent or filing<2024 else year-2020,filing)
            put('WeightedAverageNumberOfDilutedSharesOutstanding','shares',year,100*factor,filing)
            put('NetIncomeLoss','USD',year,100*(year-2020),filing)
            put('NetCashProvidedByUsedInOperatingActivities','USD',year,200*(year-2020),filing)
            put('PaymentsToAcquirePropertyPlantAndEquipment','USD',year,20,filing)
    rec=dict(cik='0000000001',acquired_at='2026-02-03T00:00:00Z',fiscal_year_end='2025-12-31',currency='USD',profile='GENERAL')
    return dict(cik=1,facts={'us-gaap':tax}),rec


def test_same_basis_requires_real_cross_filing_overlap():
    p,r=source();out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='VERIFIED'
    assert out['metrics']['eps_cagr_3y']['value']==pytest.approx(0.357209)
    assert out['metrics']['dilution_3y']['value']==0
    assert out['metrics']['fcf_per_share_cagr_3y']['value'] is not None
    p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']=[x for x in p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'] if x['accn']=='basis' or x['accn']=='old']
    assert review_share_history(p,r,'SYNTHETIC')['metrics']['eps_cagr_3y']['basis_status']=='UNKNOWN'


@pytest.mark.parametrize('factor',[2,0.5])
def test_integer_and_inverse_split_normalizes_share_history(factor):
    p,r=source(factor);out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='ADJUSTED'
    # Original EPS2022=2, after-restatement EPS2025=5/factor.
    assert out['metrics']['eps_cagr_3y']['value']==pytest.approx(0.357209)
    assert out['metrics']['dilution_3y']['value']==0
    assert any(e['status']=='ADJUSTED' for e in out['accepted_edges'])


@pytest.mark.parametrize('case',['inverse_mismatch','noninteger','unit','future','annual_ytd','conflict'])
def test_unconfirmed_restatement_or_bad_period_is_not_adopted(case):
    p,r=source(2 if case=='inverse_mismatch' else 1,eps_consistent=case!='inverse_mismatch')
    tax=p['facts']['us-gaap'];rows=tax['EarningsPerShareDiluted']['units']['USD/shares']
    if case=='noninteger':
        for x in tax['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']:
            if x['accn']=='middle':x['val']=101
    elif case=='unit':tax['EarningsPerShareDiluted']['units']['EUR/shares']=tax['EarningsPerShareDiluted']['units'].pop('USD/shares')
    elif case=='future':
        for x in rows:
            if x['accn']=='middle':x['filed']='2027-01-01'
    elif case=='annual_ytd':
        for x in rows:
            if x['accn']=='middle':x['start']=x['end'][:4]+'-07-01';x['form']='10-Q'
    elif case=='conflict':
        x=next(x for x in rows if x['accn']=='basis' and x['end']=='2025-12-31');rows.append(dict(x,val=999))
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['basis_status']=='UNKNOWN'


def test_zero_or_negative_eps_keeps_verified_basis_but_no_cagr():
    p,r=source()
    for x in p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']:
        if x['end']=='2022-12-31':x['val']=0
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['metrics']['eps_cagr_3y']['basis_status']=='VERIFIED'
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['dilution_3y']['value']==0


def test_same_accession_with_different_filed_dates_is_not_distinct_filings():
    p,r=source()
    for tag in ('EarningsPerShareDiluted','WeightedAverageNumberOfDilutedSharesOutstanding'):
        for rs in p['facts']['us-gaap'][tag]['units'].values():
            for x in rs:x['accn']='SAME-ACCESSION'
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='UNKNOWN' and not out['accepted_edges']
    assert any(e['reason']=='SAME_ACCESSION_IS_NOT_DISTINCT_FILINGS' for e in out['rejected_edges'])


from investment_system.research.qgv_555_share_review import review_share_eligibility_v2


def v2_source(split=1):
    payload, record = source(split)
    tax = payload['facts']['us-gaap']
    tax['NetIncomeLossAvailableToCommonStockholdersDiluted'] = deepcopy(tax['NetIncomeLoss'])
    for name, concept in tax.items():
        for unit, rows in concept['units'].items():
            for row in rows:
                row.update(class_id='COMMON-A', accounting_scope='CONSOLIDATED',
                           decimals=2 if unit == 'USD/shares' else 0)
    proof = dict(status='VERIFIED', issuer_id=record['cik'], currency='USD',
        class_id='COMMON-A', accounting_scope='CONSOLIDATED',
        period_start='2022-01-01', period_end='2025-12-31',
        available_at='2026-02-02T00:00:00Z', basis_accession='basis',
        filing_accessions=['old', 'middle', 'new', 'basis'],
        basis_method='EXPLICIT_SAME_BASIS_COMPARATIVES',
        evidence_refs=['SYNTHETIC#common-basis-note'])
    return payload, record, proof


def test_v2_documented_comparative_chain_is_automatic_without_price_identity():
    p, r, proof = v2_source()
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['stage1']['status'] == 'CONSISTENT'
    assert out['stage1']['numeric_consistency_comparisons'] == 3
    for metric in ('eps_cagr_3y', 'fcf_per_share_cagr_3y', 'dilution_3y'):
        claim = out['metrics'][metric]
        assert claim['stage2']['status'] == 'FINAL_ELIGIBLE'
        assert claim['stage2']['all_used_years_linked'] is True
        assert claim['stage2']['documented_common_basis'] is True
        assert claim['stage2']['evidence_refs'] == proof['evidence_refs']
        assert claim['denominator_definition'] == 'WEIGHTED_AVERAGE_DILUTED_SHARES'
    assert out['metrics']['eps_cagr_3y']['value'] == pytest.approx(0.357209)
    assert out['metrics']['dilution_3y']['value'] == 0
    assert out['metrics']['fcf_per_share_cagr_3y']['value'] == pytest.approx((9.8/3.8)**(1/3)-1, rel=1e-5)


def test_v2_repeated_numbers_are_not_full_period_basis_or_no_split_evidence():
    p, r, _ = v2_source()
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC')
    assert out['stage1']['status'] == 'CONSISTENT'
    claim = out['metrics']['eps_cagr_3y']
    assert claim['value'] is None
    assert claim['stage2']['status'] == 'UNCONFIRMED_PERIOD_BASIS'
    assert 'EXPLICIT_FULL_PERIOD_COMMON_BASIS_EVIDENCE_MISSING' in claim['stage2']['issues']
    assert claim['corporate_action']['status'] == 'UNKNOWN'


def test_v2_companyfacts_missing_context_or_decimals_is_not_fabricated():
    p, r, proof = v2_source()
    for concept in p['facts']['us-gaap'].values():
        for rows in concept['units'].values():
            for row in rows:
                for key in ('class_id', 'accounting_scope', 'decimals'):
                    del row[key]
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['stage1']['status'] == 'PARTIAL_CONSISTENCY'
    assert out['stage1']['numeric_consistency_comparisons'] == 3
    claim = out['metrics']['eps_cagr_3y']
    assert {'SHARE_CLASS_CONTEXT_NOT_REPORTED', 'ACCOUNTING_SCOPE_CONTEXT_NOT_REPORTED',
            'SOURCE_ROUNDING_PRECISION_NOT_REPORTED'}.issubset(claim['stage2']['issues'])
    assert claim['basis_status'] == 'UNKNOWN' and claim['value'] is None


@pytest.mark.parametrize('factor', [2, 0.5])
def test_v2_inverse_triplets_are_split_candidates_and_never_auto_adjusted(factor):
    p, r, proof = v2_source(factor)
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['stage1']['status'] == 'SPLIT_CANDIDATE'
    assert out['stage1']['split_candidate_comparisons'] == 1
    for claim in out['metrics'].values():
        assert claim['value'] is None
        assert claim['corporate_action']['status'] == 'CANDIDATE'
        assert claim['corporate_action']['adjustment_applied'] is False
        assert 'FULL_PERIOD_COMPARATIVE_OVERLAP_CHAIN_UNCONFIRMED' in claim['stage2']['issues']


def test_v2_consolidated_profit_is_not_diluted_attributable_numerator():
    p, r, proof = v2_source()
    del p['facts']['us-gaap']['NetIncomeLossAvailableToCommonStockholdersDiluted']
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['stage1']['annual_triplets'] == 0
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert 'DILUTED_ATTRIBUTED_INCOME_ANNUAL_YEAR_MISSING' in out['metrics']['eps_cagr_3y']['stage2']['issues']
    # A cash-flow/share or WAD trend has its own required numerator, not an EPS
    # approval inherited from a missing/valid diluted earnings numerator.
    assert out['metrics']['fcf_per_share_cagr_3y']['value'] is not None
    assert out['metrics']['dilution_3y']['value'] == 0


@pytest.mark.parametrize('changed', ['class', 'scope', 'period', 'future_proof', 'future_filing', 'missing_middle_year'])
def test_v2_period_scope_and_availability_boundaries(changed):
    p, r, proof = v2_source()
    rows = p['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
    if changed == 'class':
        for row in rows:
            if row['end'] == '2022-12-31': row['class_id'] = 'COMMON-B'
    elif changed == 'scope':
        for row in rows:
            if row['end'] == '2022-12-31': row['accounting_scope'] = 'PARENT_ONLY'
    elif changed == 'period':
        proof['period_start'] = '2023-01-01'
    elif changed == 'future_proof':
        proof['available_at'] = '2026-02-04T00:00:00Z'
    elif changed == 'future_filing':
        for concept in p['facts']['us-gaap'].values():
            for rs in concept['units'].values():
                for row in rs:
                    if row['accn'] == 'middle': row['filed'] = '2027-02-01'
    elif changed == 'missing_middle_year':
        rows[:] = [row for row in rows if row['end'] != '2023-12-31']
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['basis_status'] == 'UNKNOWN'


def test_v2_declared_rounding_is_used_but_not_inferred_from_json_digits():
    p, r, proof = v2_source()
    for row in p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']:
        if row['accn'] == 'middle' and row['end'] == '2023-12-31':
            row['val'] = 3.004
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['stage1']['status'] == 'CONSISTENT'
    assert out['metrics']['eps_cagr_3y']['value'] is not None
    for concept in p['facts']['us-gaap'].values():
        for rows in concept['units'].values():
            for row in rows: row.pop('decimals')
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['stage1']['status'] != 'CONSISTENT'


@pytest.mark.parametrize('eps', [0, -2])
def test_v2_formula_domain_failure_keeps_basis_proof_but_no_cagr(eps):
    p, r, proof = v2_source()
    for tag in ('EarningsPerShareDiluted', 'NetIncomeLossAvailableToCommonStockholdersDiluted'):
        unit = 'USD/shares' if tag == 'EarningsPerShareDiluted' else 'USD'
        for row in p['facts']['us-gaap'][tag]['units'][unit]:
            if row['end'] == '2022-12-31': row['val'] = eps if unit == 'USD/shares' else eps*100
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['metrics']['eps_cagr_3y']['stage2']['status'] == 'FINAL_ELIGIBLE'
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['reason'] == 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE'
    assert out['metrics']['dilution_3y']['value'] == 0


def test_v2_latest_comparative_already_adjusted_is_not_adjusted_twice():
    p, r, proof = v2_source(2)
    tax = p['facts']['us-gaap']
    # A later filing reports all four years already on the new basis; the
    # explicit source note documents that retrospective basis, not an inferred
    # correction to values selected from another filing.
    for tag, unit in [('EarningsPerShareDiluted', 'USD/shares'),
                      ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares'),
                      ('NetIncomeLossAvailableToCommonStockholdersDiluted', 'USD'),
                      ('NetCashProvidedByUsedInOperatingActivities', 'USD'),
                      ('PaymentsToAcquirePropertyPlantAndEquipment', 'USD')]:
        rows = tax[tag]['units'][unit]
        for year in (2022, 2023):
            row = deepcopy(next(x for x in rows if x['end'] == f'{year}-12-31'))
            row.update(accn='basis', filed='2026-02-01')
            if tag == 'EarningsPerShareDiluted': row['val'] = (year-2020)/2
            if tag == 'WeightedAverageNumberOfDilutedSharesOutstanding': row['val'] = 200
            rows.append(row)
    proof['basis_method'] = 'EXPLICIT_RETROSPECTIVE_ADJUSTMENT'
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    claim = out['metrics']['eps_cagr_3y']
    assert claim['stage2']['status'] == 'FINAL_ELIGIBLE'
    assert claim['value'] == pytest.approx(0.357209)
    assert claim['corporate_action']['status'] == 'CONFIRMED'
    assert claim['corporate_action']['adjustment_applied'] is False


def test_v2_latest_conflict_does_not_expose_a_quiet_older_value():
    p, r, proof = v2_source()
    rows = p['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
    row = next(x for x in rows if x['accn'] == 'basis' and x['end'] == '2025-12-31')
    rows.append(dict(row, val=999))
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    for claim in out['metrics'].values():
        assert claim['value'] is None
        assert 'LATEST_FILING_CONFLICT' in claim['stage2']['issues']


def test_v2_basic_or_actual_shares_never_replace_the_diluted_denominator():
    p, r, proof = v2_source()
    tax = p['facts']['us-gaap']
    tax['WeightedAverageNumberOfSharesOutstandingBasic'] = tax.pop('WeightedAverageNumberOfDilutedSharesOutstanding')
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert all(claim['value'] is None for claim in out['metrics'].values())
    assert all('DILUTED_SHARES_ANNUAL_YEAR_MISSING' in claim['stage2']['issues'] for claim in out['metrics'].values())


def test_v2_does_not_mutate_pinned_source_or_record():
    p, r, proof = v2_source(); original_p = deepcopy(p); original_r = deepcopy(r)
    review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert p == original_p and r == original_r


@pytest.mark.parametrize('available', ['2026-02-03T20:00:00Z', '2026-02-03', '2026-02-02T23:00:00'])
def test_v2_explicit_basis_availability_does_not_drop_time_precision(available):
    p, r, proof = v2_source(); r['acquired_at'] = '2026-02-03T08:00:00Z'
    proof['available_at'] = available
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert 'EXPLICIT_FULL_PERIOD_COMMON_BASIS_EVIDENCE_MISSING' in out['metrics']['eps_cagr_3y']['stage2']['issues']


@pytest.mark.parametrize('changed', ['class', 'scope', 'precision', 'latest_conflict'])
def test_v2_unselected_common_year_bridge_context_must_be_eligible(changed):
    p, r, proof = v2_source()
    rows = p['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
    row = next(x for x in rows if x['accn'] == 'new' and x['end'] == '2024-12-31')
    if changed == 'class': row['class_id'] = 'COMMON-B'
    elif changed == 'scope': row['accounting_scope'] = 'PARENT_ONLY'
    elif changed == 'precision': del row['decimals']
    elif changed == 'latest_conflict':
        # This non-selected bridge period still has a latest-filing conflict;
        # a quiet older overlap cannot establish the connection.
        later = next(x for x in rows if x['accn'] == 'basis' and x['end'] == '2024-12-31')
        rows.append(dict(later, val=999))
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    claim = out['metrics']['eps_cagr_3y']
    assert claim['value'] is None
    assert 'FULL_PERIOD_COMPARATIVE_OVERLAP_CHAIN_UNCONFIRMED' in claim['stage2']['issues']


def test_v2_new_review_cutoff_keeps_source_acquisition_and_historical_context_separate():
    p, r, proof = v2_source(); original = deepcopy(r)
    proof['available_at'] = '2026-03-01T10:00:00Z'
    held = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert held['metrics']['eps_cagr_3y']['value'] is None
    reconstructed = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof],
        review_cutoff='2026-03-01T11:00:00Z')
    assert reconstructed['metrics']['eps_cagr_3y']['value'] is not None
    assert reconstructed['source_input_cutoff'] == r['acquired_at']
    assert reconstructed['review_input_cutoff'] == '2026-03-01T11:00:00Z'
    assert reconstructed['temporal_scope'] == 'CURRENT_HELD_DOCUMENT_RECONSTRUCTION_NOT_HISTORICAL_SYSTEM_PIT'
    assert r == original


def test_v2_documented_path_is_deterministic_despite_an_undocumented_alternate():
    p, r, proof = v2_source()
    for concept in p['facts']['us-gaap'].values():
        for rows in concept['units'].values():
            copies = [dict(row, accn='undocumented-bridge', filed='2025-01-31')
                      for row in rows if row['accn'] == 'new']
            rows.extend(copies)
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    claim = out['metrics']['eps_cagr_3y']
    assert claim['value'] == pytest.approx(0.357209)
    assert 'undocumented-bridge' not in {x['accession'] for x in claim['stage2']['required_chain_filings']}
    for concept in p['facts']['us-gaap'].values():
        for rows in concept['units'].values(): rows.reverse()
    reordered = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert reordered['metrics']['eps_cagr_3y']['value'] == claim['value']
    assert reordered['metrics']['eps_cagr_3y']['stage2']['required_chain_filings'] == claim['stage2']['required_chain_filings']


def test_v2_only_formula_endpoints_and_necessary_share_bridges_are_required():
    p, r, proof = v2_source()
    # FY2023/FY2024 cash-flow and diluted numerator are not CAGR operands.
    # WAD comparative years remain to prove the documented endpoint basis.
    for tag in ('NetCashProvidedByUsedInOperatingActivities', 'PaymentsToAcquirePropertyPlantAndEquipment',
                'NetIncomeLossAvailableToCommonStockholdersDiluted'):
        rows = p['facts']['us-gaap'][tag]['units']['USD']
        rows[:] = [x for x in rows if x['end'] in ('2022-12-31', '2025-12-31')]
    out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
    assert all(x['value'] is not None for x in out['metrics'].values())
    assert all(len(x['stage2']['annual_periods']) == 2 for x in out['metrics'].values())


@pytest.mark.parametrize('field,value', [('class_id', 'COMMON-B'), ('accounting_scope', 'PARENT_ONLY')])
def test_v2_equal_duplicate_facts_cannot_hide_a_context_conflict(field, value):
    p, r, proof = v2_source()
    rows = p['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']
    row = next(x for x in rows if x['accn'] == 'basis' and x['end'] == '2025-12-31')
    rows.append(dict(row, **{field: value}))
    for _ in range(2):
        out = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof])
        assert all(x['value'] is None for x in out['metrics'].values())
        assert all('LATEST_FILING_CONFLICT' in x['stage2']['issues'] for x in out['metrics'].values())
        rows.reverse()


def test_v2_auxiliary_fact_context_is_bound_to_source_period_unit_and_review_time():
    p, r, proof = v2_source(); contexts = {}
    for concept_name, concept in p['facts']['us-gaap'].items():
        for unit, rows in concept['units'].items():
            for n, row in enumerate(rows):
                pointer = '/facts/us-gaap/' + concept_name + '/units/' + unit.replace('/', '~1') + '/' + str(n)
                contexts[pointer] = dict(status='VERIFIED', issuer_id=r['cik'],
                    period_start=row['start'], period_end=row['end'], unit=unit,
                    available_at='2026-02-02T12:00:00Z', evidence_refs=['SYNTHETIC#xbrl-context'],
                    class_id=row.pop('class_id'), accounting_scope=row.pop('accounting_scope'), decimals=row.pop('decimals'))
    ok = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof], fact_contexts=contexts)
    assert ok['metrics']['eps_cagr_3y']['value'] is not None
    for context in contexts.values(): context['available_at'] = '2026-02-03T20:00:00Z'
    future = review_share_eligibility_v2(p, r, 'SYNTHETIC', period_evidence=[proof], fact_contexts=contexts)
    assert all(x['value'] is None for x in future['metrics'].values())
    assert 'AUXILIARY_CONTEXT_EVIDENCE_INVALID' in future['metrics']['eps_cagr_3y']['stage2']['issues']
