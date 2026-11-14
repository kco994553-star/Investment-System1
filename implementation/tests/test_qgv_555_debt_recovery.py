"""Synthetic FY debt connection, independent expected ratio and narrow repair."""
from copy import deepcopy
import hashlib
import json
import pytest
from investment_system.research.qgv_555 import catalog
from investment_system.research.qgv_555_held import held_fy_debt_metric, connect_fy_debt_review


def source():
    tax = {}
    for tag, value in [('Assets', 200), ('CashAndCashEquivalentsAtCarryingValue', 10),
                       ('DebtLongtermAndShorttermCombinedAmount', 70)]:
        tax[tag] = {'units': {'USD': [dict(val=value, end='2025-12-31', filed='2026-02-01', accn='SYN', form='10-K')]}}
    for tag, value in [('OperatingIncomeLoss', 20), ('DepreciationDepletionAndAmortization', 10), ('NetIncomeLoss', 12)]:
        tax[tag] = {'units': {'USD': [dict(val=value, start='2025-01-01', end='2025-12-31', filed='2026-02-01', accn='SYN', form='10-K')]}}
    p = dict(cik=1, facts={'us-gaap': tax})
    r = dict(cik='0000000001', acquired_at='2026-02-02T12:00:00Z', fiscal_year_end='2025-12-31',
             currency='USD', profile='GENERAL', state='LIVE')
    return p,r


def test_exact_fy_debt_uses_existing_kernel_not_quarterly_total():
    p,r=source()
    assert held_fy_debt_metric(p,r,'synthetic')['value'] == 2  # (70-10)/(20+10)
    p['facts']['us-gaap']['DebtLongtermAndShorttermCombinedAmount']['units']['USD'][0]['end']='2025-09-30'
    assert held_fy_debt_metric(p,r,'synthetic')['value'] is None


@pytest.mark.parametrize('case',['missing','liabilities','unit','future','conflict','no_da','financial'])
def test_missing_or_invalid_input_is_not_zero_or_a_substitute(case):
    p,r=source();tax=p['facts']['us-gaap'];node=tax['DebtLongtermAndShorttermCombinedAmount'];x=node['units']['USD'][0]
    if case=='missing':del tax['DebtLongtermAndShorttermCombinedAmount']
    elif case=='liabilities':tax['Liabilities']=tax.pop('DebtLongtermAndShorttermCombinedAmount')
    elif case=='unit':node['units']['EUR']=node['units'].pop('USD')
    elif case=='future':x['filed']='2027-01-01'
    elif case=='conflict':node['units']['USD'].append(dict(x,val=71))
    elif case=='no_da':del tax['DepreciationDepletionAndAmortization']
    else:r['profile']='FINANCIAL'
    assert held_fy_debt_metric(p,r,'synthetic')['value'] is None


def entry_and_snapshot():
    p,r=source();raw=json.dumps(p).encode();sha=hashlib.sha256(raw).hexdigest()
    r['source_sha256']={'companyfacts':sha};m='net_debt_to_ebitda'
    row=dict(company_id='SYN:1',issuer_id=r['cik'],accounting_template='GENERAL',metrics={m:None},
        metric_evidence={m:dict(status='VERIFIED',variant=catalog()[m]['variant'],source_refs=['original'],
                               period_end=r['fiscal_year_end'],available_at=r['acquired_at'])})
    snap=dict(input_cutoff='2026-02-03T00:00:00Z',rows=[row],members=['SYN:1'],source_anchors=['original'])
    return dict(record=r,source_bytes=raw,sha256=sha,reference='synthetic#sha256='+sha),snap


def connect(s,es):
    return connect_fy_debt_review(s,es,reviewed_at='2026-02-04T00:00:00Z',input_cutoff='2026-02-04T00:00:00Z')


def test_repair_preserves_source_cutoff_and_original_and_only_repairs_matching_rows():
    e,s=entry_and_snapshot();old=deepcopy(s);m='net_debt_to_ebitda'
    wrong=deepcopy(s['rows'][0]);wrong.update(company_id='SYN:2',accounting_template=None)
    s['rows'].append(wrong);s['members'].append('SYN:2')
    o,a=connect(s,[e])
    assert o['rows'][0]['metrics'][m]==2 and o['rows'][1]['metrics'][m] is None
    assert s['rows'][0]==old['rows'][0] and o['members']==s['members']
    proof=o['rows'][0]['metric_evidence'][m]
    assert proof['retrieved_at']==e['record']['acquired_at'] and proof['available_at']==o['input_cutoff']
    assert not o['review_context']['historical_system_pit_complete']
    s['rows'][0]['metric_evidence'][m]['period_end']='2024-12-31'
    assert connect(s,[e])[0]['rows'][0]['metrics'][m] is None


def test_omitted_null_metric_requires_matching_retained_fiscal_context():
    e,s=entry_and_snapshot();m='net_debt_to_ebitda';row=s['rows'][0]
    p=row['metric_evidence'].pop(m);row['metrics'].pop(m)
    e['record']['calc_version']='qgv2-calc/2026-10-23.1'
    p['source_formula_version']=e['record']['calc_version']
    row['metric_evidence']['roic']=p
    assert connect(s,[e])[0]['rows'][0]['metrics'][m]==2
    p['available_at']='2026-02-02T13:00:00Z'
    assert m not in connect(s,[e])[0]['rows'][0]['metrics']


def test_multiple_acquisitions_bind_only_the_pinned_retained_context():
    e,s=entry_and_snapshot();older=deepcopy(e)
    older['record']['acquired_at']='2026-02-02T01:00:00Z'
    payload=json.loads(older['source_bytes'])
    payload['facts']['us-gaap']['DebtLongtermAndShorttermCombinedAmount']['units']['USD'][0]['val']=100
    older['source_bytes']=json.dumps(payload).encode()
    older['sha256']=hashlib.sha256(older['source_bytes']).hexdigest()
    older['record']['source_sha256']['companyfacts']=older['sha256']
    older['reference']='synthetic#sha256='+older['sha256']
    for entries in ([older,e],[e,older]):
        out,audit=connect(s,entries)
        assert out['rows'][0]['metrics']['net_debt_to_ebitda']==2
        skipped=next(a for a in audit if a['retrieved_at']==older['record']['acquired_at'])
        assert not skipped['linked_rows']
        assert skipped['row_decisions'][0]['cause']=='RETAINED_FISCAL_CONTEXT_MISMATCH'


@pytest.mark.parametrize('case',['hash','issuer','duplicate','future_review'])
def test_repair_rejects_incoherent_evidence(case):
    e,s=entry_and_snapshot();es=[e]
    if case=='hash':e['sha256']='0'*64
    elif case=='issuer':e['record']['cik']='0000000002'
    elif case=='duplicate':es.append(deepcopy(e))
    else:s['input_cutoff']='2027-01-01T00:00:00Z'
    with pytest.raises(ValueError):connect(s,es)
