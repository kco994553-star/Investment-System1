"""Offline FY safety evidence and balance-equation diagnostics, not model policy."""
from datetime import date
from math import isclose

from ..qgv import v2_factors as vf
from .financial_v import _balance_observations
from .sector_qgv_held import _connect_explicit_debt


def _instant(payload, tags, currency, cutoff, end):
    """Exact fiscal instant with an unambiguous latest filing/unit frontier."""
    accepted, rejected, present = _balance_observations(payload, tags, currency, cutoff)
    frontier = []
    for tag in tags:
        for unit, rows in payload.get('facts', {}).get('us-gaap', {}).get(tag, {}).get('units', {}).items():
            for row in rows:
                filed = vf._day(row.get('filed'))
                if row.get('end') == str(end) and filed and filed <= cutoff:
                    frontier.append((filed, row.get('accn'), unit, row.get('start')))
    latest = max((x[0] for x in frontier), default=None)
    keys = [k for k in accepted if k[0] == end and k[1] == latest]
    selected = accepted[keys[0]] if len(keys) == 1 else None
    current = [r for r in frontier if r[0] == latest]
    coherent = selected is not None and current and all(r[1] == keys[0][2] and r[2] == currency and r[3] is None for r in current)
    return (dict(value=selected['value'], period_end=str(end), filed=str(latest), accession=keys[0][2],
                 currency=currency, json_pointers=selected['json_pointers']) if coherent else None,
            dict(present=present, rejected=rejected, status='VALID' if coherent else 'UNCONFIRMED'))


def inspect_safety(payload, record, source_ref):
    """One held source: no-debt/interest0 proof and Assets−Equity candidates.

    Counterfactual flags do not grant a highest score, a new factor definition,
    or FINANCIAL applicability. Parent-only equity is never called total equity.
    """
    if str(payload.get('cik')).zfill(10) != record.get('cik'):
        raise ValueError('SAFETY_SOURCE_ISSUER')
    cutoff = date.fromisoformat(record['acquired_at'][:10])
    taxonomy, currency = vf._taxonomy_and_currency(payload, cutoff)
    out = dict(issuer_id=record['cik'], source_reference=source_ref,
               acquired_at=record['acquired_at'], fiscal_year_end=record.get('fiscal_year_end'),
               profile=record.get('profile'), taxonomy=taxonomy, currency=currency,
               components={}, reasons={}, evidence_only=True, safety_review_version='owner-safety-review/1')
    if not taxonomy or not record.get('fiscal_year_end'):
        out['reasons']['context'] = 'FISCAL_TAXONOMY_OR_CURRENCY_UNKNOWN'
        return out
    end = date.fromisoformat(record['fiscal_year_end'])
    facts = vf._Facts(payload, taxonomy, currency, cutoff)
    c = vf._Company(facts, end, sic=record.get('sic'), profile=record.get('profile'))
    f = out['components']
    # The original FY instant interpretation is preserved for diagnostic presence.
    f['assets_legacy'] = c.i('total_assets', 0)
    f['equity_legacy'] = c.i('equity', 0)
    f['assets_exact_fy'] = facts.instant('total_assets', end, 0)
    f['equity_exact_fy'] = facts.instant('equity', end, 0)
    out['derived_liabilities_arithmetic_candidate'] = None
    if f['assets_exact_fy'] is not None and f['equity_exact_fy'] is not None:
        out['derived_liabilities_arithmetic_candidate'] = f['assets_exact_fy'] - f['equity_exact_fy']
    common_ends = facts.instant_ends('total_assets') & facts.instant_ends('equity')
    out['derived_any_period_arithmetic_present'] = any(
        facts.instant('total_assets', e, 0) is not None and facts.instant('equity', e, 0) is not None
        for e in common_ends)
    out['derived_liabilities_verified'] = None
    out['derived_liabilities_scope'] = 'UNCONFIRMED'
    out['derived_liabilities_definition'] = 'ASSETS_MINUS_CONSOLIDATED_EQUITY_NOT_A_DIRECT_LIABILITIES_TAG'
    if taxonomy == 'us-gaap':
        for name, tags in [('assets', ('Assets',)),
                           ('parent_equity', ('StockholdersEquity',)),
                           ('total_equity', ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',)),
                           ('nci', ('MinorityInterest',)),
                           ('liabilities', ('Liabilities',))]:
            f[name], out['reasons'][name] = _instant(payload, tags, currency, cutoff, end)
        assets, total, parent, nci = (f.get(k) for k in ('assets', 'total_equity', 'parent_equity', 'nci'))
        # Parent equity is allowed only when exact same-filing NCI0 is explicit.
        if total is None and parent and nci and nci['value'] == 0 and parent['accession'] == nci['accession'] and parent['filed'] == nci['filed']:
            total = parent
            out['derived_liabilities_scope'] = 'PARENT_WITH_EXPLICIT_SAME_FILING_ZERO_NCI'
        elif total is not None:
            out['derived_liabilities_scope'] = 'CONSOLIDATED_TOTAL_EQUITY'
        if assets and total:
            if assets['accession'] == total['accession'] and assets['filed'] == total['filed']:
                derived = assets['value'] - total['value']
                if assets['value'] >= 0 and derived >= 0:
                    out['derived_liabilities_verified'] = derived
                else:out['reasons']['derived_liabilities'] = 'NEGATIVE_BALANCE_RESULT'
            else:out['reasons']['derived_liabilities'] = 'ASSET_EQUITY_FILING_MISMATCH'
        direct = f.get('liabilities')
        out['derived_matches_direct'] = None if direct is None or out['derived_liabilities_verified'] is None else isclose(direct['value'], out['derived_liabilities_verified'], rel_tol=1e-10, abs_tol=0)
        if out['derived_matches_direct'] is False:
            out['reasons']['derived_liabilities'] = 'DIRECT_BALANCE_EQUATION_MISMATCH'
            out['derived_liabilities_verified'] = None
    else:
        out['reasons']['derived_liabilities'] = 'IFRS_TOTAL_EQUITY_EXACT_SCOPE_NOT_CONNECTED'
    debt = c.debt_at(end, 0)
    debt_basis = 'REPORTED_DEBT_COMPONENTS' if debt is not None else None
    exact_assets = facts.instant('total_assets', end, 0)
    fields = dict(assets_end=dict(value=exact_assets,period_end=str(end),currency=currency)) if exact_assets is not None else {}
    why = {}
    _connect_explicit_debt(payload, fields, why, cutoff)
    if debt is None:
        if fields.get('debt') is not None:
            debt = fields['debt']['value'];debt_basis = 'EXPLICIT_COMBINED_DEBT_TOTAL'
        else:
            debt = c.debt_rule(end)
            if debt is not None:debt_basis = 'EXISTING_APPROVED_NODEBT_RULE'
    f['debt'], f['debt_basis'], f['explicit_debt_evidence'] = debt, debt_basis, fields.get('debt')
    f['ebit'], f['da'], f['interest'] = c.a('ebit',0),c.a('depreciation_amortization',0),c.a('interest_expense',0)
    f['cash'] = facts.instant('cash_and_equivalents', end, 0)
    f['ebitda'] = None if f['ebit'] is None or f['da'] is None else f['ebit'] + f['da']
    interest_hits = c._component_named('interest_expense_evidence', end)
    interest_values = [hit[0] for hit,_,_ in interest_hits]
    debt_evidence = [v for item in vf.DEBT_ITEMS + ('debt_evidence','finance_lease_total','finance_lease_noncurrent','finance_lease_current') for v in c._any_instant(item,end,0)]
    explicit_total = fields.get('debt')
    out['no_debt_verified'] = (debt == 0 and not any(v != 0 for v in debt_evidence) and
        (c.debt_rule(end) == 0 or explicit_total is not None and explicit_total['value'] == 0))
    out['no_debt_verification_basis'] = ('EXPLICIT_COMBINED_DEBT_ZERO' if out['no_debt_verified'] and explicit_total is not None
        else 'EXISTING_APPROVED_NODEBT_RULE' if out['no_debt_verified'] else 'UNCONFIRMED')
    out['explicit_interest_zero'] = f['interest'] == 0 and bool(interest_values) and not any(v != 0 for v in interest_values)
    out['netcash_verified'] = debt is not None and f['cash'] is not None and debt < f['cash']
    if debt == 0 and not out['no_debt_verified']:out['reasons']['no_debt'] = 'CONFLICTING_OTHER_BORROWING_EVIDENCE'
    if f['interest'] == 0 and not out['explicit_interest_zero']:out['reasons']['interest_zero'] = 'OTHER_INTEREST_EVIDENCE_OR_NO_EXPLICIT_ANNUAL_ZERO'
    # Existing arithmetic is used solely to diagnose the missing safety submetrics.
    if debt is not None:c._cache[('debt',0)] = debt
    m = vf._metrics_general(c)
    out['raw_metrics'] = {k:vf._round(m[k]) for k in ('net_debt_to_ebitda','interest_coverage')}
    out['raw_safety_unavailable'] = all(v is None for v in out['raw_metrics'].values())
    out['highest_counterfactual_qualifier'] = out['no_debt_verified'] or out['explicit_interest_zero']
    out['highest_counterfactual_role_recovery'] = out['raw_safety_unavailable'] and out['highest_counterfactual_qualifier']
    out['highest_counterfactual_adopted'] = False
    return out


def highest_safety_counterfactual(board, evaluation, reference, reviews):
    """Re-evaluate safety role/Q only, never overwrite the saved model result.

    The categorical maximum is not a fabricated zero-valued ratio. It needs a
    verified debt0/interest0 review, both original raw ratios unavailable, and
    at least one original metric peer scope with eight eligible points including
    this categorical candidate. Existing axis_score retains its 50% policy.
    """
    from copy import deepcopy
    from collections import defaultdict
    from .qgv_555 import calculation_row, _usable, catalog, identity, validate_binding
    from .sector_qgv import digest
    from .sector_qgv_registry import SECTORS
    from ..qgv.qgv_v2 import axis_score
    from ..qgv.v2_scoring import _Pool
    validate_binding(board, expected_evaluation=identity(evaluation), expected_reference=identity(reference))
    c = board['configuration'];metrics = ('net_debt_to_ebitda','interest_coverage')
    points = {};ref_rows = {}
    for original in sorted(reference['rows'],key=lambda x:x['company_id']):
        row = calculation_row(c,original)
        if row.get('accounting_template')!='GENERAL' or not row.get('issuer_id'):continue
        values = {m:_usable(row,m,reference)[0] for m in metrics}
        issuer = row['issuer_id']
        if issuer in points:
            if points[issuer]!=values:raise ValueError('SAFETY_REFERENCE_ISSUER_CONFLICT')
            continue
        points[issuer]=values;ref_rows[issuer]=row
    pools = {('all',):_Pool(points)}
    for keyfun in (lambda r:('industry',r.get('industry_group')),
                   lambda r:('sector',r.get('sector_id'),r.get('accounting_template'))):
        grouped=defaultdict(dict)
        for issuer,row in ref_rows.items():grouped[keyfun(row)][issuer]=points[issuer]
        pools.update({k:_Pool(v) for k,v in grouped.items()})
    saved = {r['company_id']:r for r in board['rows']};decisions=[];after={}
    for original in evaluation['rows']:
        row=calculation_row(c,original);old=saved[row['company_id']]
        after[row['company_id']]=dict(issuer_id=row['issuer_id'],
            role_score=old['roles']['q_financial_safety']['score'],Q=deepcopy(old['axes']['Q']))
        if (row.get('accounting_template')!='GENERAL' or
            c['candidate']=='S1-555' and row.get('sector_id') not in SECTORS):continue
        review=reviews.get(row['issuer_id'])
        if not review or review.get('profile')!='GENERAL' or not review.get('highest_counterfactual_qualifier'):continue
        raw={m:_usable(row,m,evaluation)[0] for m in metrics}
        if any(v is not None for v in raw.values()) or not review.get('raw_safety_unavailable'):continue
        context=original.get('owner_source_context') or {}
        matches=(context.get('companyfacts_sha256')==review.get('source_sha256') and
            context.get('acquired_at')==review.get('acquired_at') and
            context.get('fiscal_year_end')==review.get('fiscal_year_end'))
        item=dict(company_id=row['company_id'],issuer_id=row['issuer_id'],
            reason='SOURCE_CONTEXT_MISMATCH',sample_checks=[],sample_ready=False,
            no_debt_verified=review.get('no_debt_verified'),interest_zero=review.get('explicit_interest_zero'),
            ebitda=review.get('components',{}).get('ebitda'),role_before=old['roles']['q_financial_safety']['score'],
            role_after=old['roles']['q_financial_safety']['score'],Q_before=old['axes']['Q']['score'],Q_after=old['axes']['Q']['score'])
        if matches:
            for metric in metrics:
                keys=[('sector',row.get('sector_id'),'GENERAL')] if c['candidate']=='S1-555' else [('industry',row.get('industry_group')),('all',)]
                for key in keys:
                    pool=pools.get(key,_Pool({}))
                    # The candidate is a categorical own point, not a ratio0.
                    # Preserve the existing own-issuer replacement convention.
                    n=len(pool.values(metric,catalog()[metric]['direction']))
                    if pool.points.get(row['issuer_id'],{}).get(metric) is not None:n-=1
                    n+=1
                    item['sample_checks'].append(dict(metric=metric,scope='|'.join(str(k) for k in key),reference_n=n))
                    if n>=c['minimum']:
                        item['sample_ready']=True
                        break
            item['reason']='CATEGORICAL_MAX_RESEARCH_ONLY' if item['sample_ready'] else 'PEER_SAMPLE_SMALL'
            if item['sample_ready']:
                specs=deepcopy(c['roles'])
                if c['candidate']=='S1-555':specs.update(c.get('scoped_role_overrides',{}).get(str(row.get('sector_id'))+'|GENERAL',{}))
                scores={r:data['score'] for r,data in old['roles'].items()}
                scores['q_financial_safety']=100.0
                q=axis_score(scores,'Q',{role:s['weight'] for role,s in specs.items() if s['axis']=='Q'})
                item.update(role_after=100.0,Q_after=q['score'])
                after[row['company_id']].update(role_score=100.0,Q=q)
        decisions.append(item)
    def issuers(predicate):return {r['issuer_id'] for r in board['rows'] if predicate(r)}
    old_role=issuers(lambda r:r['roles']['q_financial_safety']['score'] is not None)
    old_q=issuers(lambda r:r['axes']['Q']['score'] is not None)
    new_role={r['issuer_id'] for r in after.values() if r['role_score'] is not None}
    new_q={r['issuer_id'] for r in after.values() if r['Q']['score'] is not None}
    changed={d['issuer_id'] for d in decisions if d['Q_before'] is not None and d['Q_after'] is not None and d['Q_before']!=d['Q_after']}
    return dict(kind='OFFLINE_SAFETY_HIGHEST_COUNTERFACTUAL',model_id=board['model_id'],
        model_result_hash=board['result_hash'],evaluation=deepcopy(board['evaluation']),reference=deepcopy(board['reference']),
        reviews_hash=digest(reviews),denominator=board['coverage']['denominator'],
        raw_candidates=len({d['issuer_id'] for d in decisions}),sample_ready=len({d['issuer_id'] for d in decisions if d['sample_ready']}),
        role_before=len(old_role),role_after=len(new_role),role_new=len(new_role-old_role),role_lost=len(old_role-new_role),
        Q_before=len(old_q),Q_after=len(new_q),Q_new=len(new_q-old_q),Q_lost=len(old_q-new_q),Q_common_changed=len(changed),
        rows=decisions,baseline_modified=False,axis_policy='EXISTING_AVAILABLE_ROLE_WEIGHT_50_PERCENT',
        ratio_zero_inserted=False,default_policy_applied=False,total_recomputed=False,rank_recomputed=False)
