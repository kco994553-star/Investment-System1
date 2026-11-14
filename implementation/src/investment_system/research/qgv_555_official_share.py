"""Price-free research reuse of official historical per-share arithmetic.

This module calls the official fiscal kernel.  It annotates its share-basis
routes and permitted assumptions; it does not copy scores, infer a security ID,
or equate an official route with the stricter full-period evidence contract.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
import math
from types import SimpleNamespace

from ..qgv import v2_factors as vf
from .qgv_555_share_review import _collect, _filing

VERSION = 'held-555-official-share-reuse/1'
METRICS = ('eps_cagr_3y', 'fcf_per_share_cagr_3y', 'dilution_3y')
FORMULAS = {
    'eps_cagr_3y': 'REPORTED_DILUTED_EPS_CAGR_3Y',
    'fcf_per_share_cagr_3y': 'FCF_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y',
    'dilution_3y': 'WEIGHTED_DILUTED_SHARES_CAGR_3Y',
}
DENOMINATOR = 'WEIGHTED_AVERAGE_DILUTED_SHARES'
BASES = ('EVIDENCE_LINKED', 'FILING_SPLIT_ADJUSTED',
         'OFFICIAL_ASSUMPTION_INHERITED', 'ADDITIONAL_VERIFICATION_REQUIRED',
         'EXPLICIT_CONFLICT_EXCLUDED')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class _TracedCompany(vf._Company):
    """Observe calls to the unchanged official methods, never replace their math."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edge_calls = []
        self.factor_calls = {}

    def _edge(self, a, b):
        value = super()._edge(a, b)
        va = self.f.share_filings.get(a, {})
        vb = self.f.share_filings.get(b, {})
        common = sorted(va.keys() & vb.keys(), key=str)
        self.edge_calls.append(dict(from_node=a, to_node=b, factor=value,
            common_periods=[dict(concept_index=p[0], period_start=str(p[1]), period_end=str(p[2]),
                from_shares=va[p], to_shares=vb[p], exactly_equal=va[p] == vb[p]) for p in common]))
        return value

    def share_factor(self, filing, target=None):
        target = self._basis() if target is None else target
        key = (filing, target)
        start = len(self.edge_calls)
        factor = super().share_factor(filing, target)
        if key not in self.factor_calls:
            self.factor_calls[key] = dict(factor=factor, calls=self.edge_calls[start:])
        return factor


def _route(c, filing, target=None):
    target = c._basis() if target is None else target
    factor = c.share_factor(filing, target)
    base = dict(from_filing=_filing(filing) if filing else None,
                to_filing=_filing(target) if target else None,
                factor=factor, allowed_assumptions=[], path=[])
    if filing is None or target is None:
        return dict(base, adoption_basis='ADDITIONAL_VERIFICATION_REQUIRED',
                    reason='FILING_BASIS_UNAVAILABLE')
    if not all(isinstance(n[0],str) and n[0] for n in (filing,target)):
        return dict(base, adoption_basis='ADDITIONAL_VERIFICATION_REQUIRED',
                    reason='FILING_ACCESSION_UNAVAILABLE')
    if filing == target:
        return dict(base, adoption_basis='EVIDENCE_LINKED', reason='SAME_FILING_COMPARATIVE_BASIS')
    calls = c.factor_calls[(filing, target)]['calls']
    adjacency = defaultdict(list)
    for call in calls:
        if call['factor'] is not None and call['factor'] != 'X':
            adjacency[call['from_node']].append(call)
    queue = deque([(filing, [])]); seen = {filing}; path = None
    while queue:
        node, trace = queue.popleft()
        if node == target:
            path = trace; break
        for edge in adjacency[node]:
            if edge['to_node'] not in seen:
                seen.add(edge['to_node']); queue.append((edge['to_node'], trace + [edge]))
    if path is not None and factor is not None:
        public_path = [dict(from_filing=_filing(x['from_node']),to_filing=_filing(x['to_node']),
                            factor=x['factor'],common_periods=x['common_periods']) for x in path]
        if any(not isinstance(x[side][0],str) or not x[side][0]
               for x in path for side in ('from_node','to_node')):
            return dict(base,adoption_basis='ADDITIONAL_VERIFICATION_REQUIRED',
                        reason='FILING_ACCESSION_UNAVAILABLE',path=public_path)
        revised = any(x['factor'] == 1.0 and any(not p['exactly_equal'] for p in x['common_periods']) for x in path)
        split = any(x['factor'] != 1.0 for x in path)
        assumptions = ['OFFICIAL_ORDINARY_REVISION_TOLERANCE'] if revised else []
        return dict(base, adoption_basis='FILING_SPLIT_ADJUSTED' if split else
                    'OFFICIAL_ASSUMPTION_INHERITED' if revised else 'EVIDENCE_LINKED',
                    reason='REPORTED_SPLIT_FACT_MATCHED' if split else
                    'COMMON_PERIOD_ORDINARY_REVISION_WITHIN_OFFICIAL_TOLERANCE' if revised else
                    'COMMON_PERIOD_EXACT_SHARE_BASIS_LINK', path=public_path,
                    allowed_assumptions=assumptions)
    if factor is None:
        raw_reachable = target in c._linked(filing, c._period_index())
        return dict(base, adoption_basis='EXPLICIT_CONFLICT_EXCLUDED',
                    reason='OFFICIAL_UNCONFIRMED_RESTATEMENT_REJECTED' if raw_reachable else
                    'REPORTED_SPLIT_WITHOUT_CONNECTED_BASIS')
    return dict(base, adoption_basis='OFFICIAL_ASSUMPTION_INHERITED',
                reason='NO_OVERLAP_NO_INTERVENING_REPORTED_SPLIT',
                allowed_assumptions=['OFFICIAL_NO_OVERLAP_NO_REPORTED_SPLIT_FACTOR_ONE'])


def _selected_source(facts, c, item, k):
    hit = c.annual_hit(item, c.end(k))
    filing = facts.annual_filing(item, c.end(k))
    info = dict(item=item, year_offset=k, value=hit[0] if hit else None,
        period_start=str(hit[1]) if hit else None, period_end=str(hit[2]) if hit else None,
        filing=_filing(filing) if filing else None)
    if item == 'capital_expenditure':
        base = c._capex_base(c.end(k))
        lines = ([base] if base else []) + c._capex_with_software(c.end(k))[1]
        components = []
        for (line_hit, table, concept) in lines:
            for group, tables in facts.items.items():
                for n, candidate in enumerate(tables):
                    if table is candidate:
                        line_filing = facts.sources[group][n].get(line_hit[1:])
                        components.append(dict(item=group,concept=concept,value=line_hit[0],
                            period_start=str(line_hit[1]),period_end=str(line_hit[2]),
                            filing=_filing(line_filing) if line_filing else None))
        info['components'] = components
    return info, hit, filing


def _component_conflicts(payload, facts, info, cutoff, c):
    issues=[]
    lines=list(info.get('components', []))
    if info['item']=='capital_expenditure':
        base=c._capex_base(c.end(info['year_offset']))
        if base and base[2] not in vf.CAPEX_INCLUDES_SOFTWARE:
            # A dropped, explicitly conflicting software fact is not the same
            # as no software disclosure. The official assembler stays intact;
            # this research reuse withholds that ambiguous FCF numerator.
            for group in ('capital_expenditure_software_total','capital_expenditure_software_parts'):
                lines.extend(dict(item=group,concept=n) for n in facts.concepts.get(group,()))
    for line in lines:
        item=line['item'];concept=line['concept']
        # Reuse the existing diagnostic collector, constrained to the actual
        # selected component rather than another optional CAPEX definition.
        view=SimpleNamespace(taxonomy=facts.taxonomy,concepts={item:(concept,)},_unit=facts._unit)
        selected,loc,invalid,conflicts=_collect(payload,view,item,cutoff)
        if any(abs((p[1]-c.end(info['year_offset'])).days)<=vf.YEAR_TOLERANCE_DAYS for p in conflicts):
            issues.append('LATEST_FILING_CONFLICT:'+concept)
    return issues


def _context_qualifications(payload):
    # Companyfacts omits original contextRef and decimals in common responses.
    # Absence is a transport limitation, not proof of the wrong share class.
    return ['ORIGINAL_CONTEXT_AND_PRECISION_NOT_INDEPENDENTLY_RECONCILED',
            'SHARE_CLASS_ATTRIBUTION_NOT_A_VALUATION_SECURITY_ID',
            'CURRENT_HELD_RECONSTRUCTION_NOT_HISTORICAL_SYSTEM_PIT']


def review_official_share_history(payload, record, source_ref):
    """Reuse three raw metrics, labeling the official share-basis acceptance.

    Evidence-only eligibility means the official route used documented common
    periods or reported split facts without its revision/no-overlap assumptions.
    It deliberately does *not* mean strict v0.3, price identity, or split-free.
    Missing/ambiguous same-filing cover shares remain NO_REFERENCE diagnostics.
    """
    if str(payload.get('cik')).zfill(10) != record.get('cik'):
        raise ValueError('OFFICIAL_SHARE_SOURCE_ISSUER')
    clock = datetime.fromisoformat(record['acquired_at'].replace('Z', '+00:00'))
    if clock.tzinfo is None:
        raise ValueError('OFFICIAL_SHARE_SOURCE_CLOCK')
    cutoff = clock.astimezone(timezone.utc).date()
    tax, cur = vf._taxonomy_and_currency(payload, cutoff)
    fy = vf._day(record.get('fiscal_year_end'))
    out = dict(adapter_version=VERSION, issuer_id=record['cik'],source_refs=[source_ref],
        acquired_at=record['acquired_at'],source_input_cutoff=record['acquired_at'],
        fiscal_year_end=record.get('fiscal_year_end'), metrics={},
        official_calc_version=record.get('calc_version'), strict_verified=False,
        temporal_scope='CURRENT_HELD_DOCUMENT_RECONSTRUCTION_NOT_HISTORICAL_SYSTEM_PIT',
        historical_scope='OFFICIAL_REPORTED_DILUTED_SHARE_BASIS_NOT_PRICE_SECURITY_IDENTITY')
    if not tax or not cur or not fy:
        for metric in METRICS:
            out['metrics'][metric] = dict(value=None, unrounded_value=None,
                adoption_basis='ADDITIONAL_VERIFICATION_REQUIRED', reason='PERIOD_CONTEXT_UNAVAILABLE',
                allowed_assumptions=[],requires_assumption=False,evidence_only_eligible=False,
                reusable=False,strict_verified=False,formula_variant=FORMULAS[metric],
                denominator_definition=DENOMINATOR,periods=[],endpoint_factors=[])
        return out
    if record.get('currency') and record['currency'] != cur:
        raise ValueError('OFFICIAL_SHARE_SOURCE_CURRENCY')
    facts = vf._Facts(payload,tax,cur,cutoff)
    c = _TracedCompany(facts,fy,sic=record.get('sic'),profile=record.get('profile','GENERAL'))
    # All metric arithmetic is the official implementation. No stored score,
    # factor percentile or decile is read from the record.
    if c.profile not in ('GENERAL','FINANCIAL'):
        raise ValueError('OFFICIAL_SHARE_SOURCE_PROFILE')
    computed = vf._metrics_financial(c) if c.profile=='FINANCIAL' else vf._metrics_general(c)
    vf._growth_common(c,computed)
    requests = {'eps_cagr_3y':('eps_diluted',),
                'fcf_per_share_cagr_3y':('operating_cash_flow','capital_expenditure','diluted_shares'),
                'dilution_3y':('diluted_shares',)}
    audits = {item:_collect(payload,facts,item,cutoff) for item in set(sum(requests.values(),()))}
    for metric, items in requests.items():
        periods=[]; routes=[]; problems=[]; missing=[]; scale=[]
        for k in (0,3):
            year_hits=[]
            for item in items:
                info, hit, filing = _selected_source(facts,c,item,k); periods.append(info)
                if hit is None:
                    missing.append(item.upper()+'_ANNUAL_ENDPOINT_MISSING'); continue
                year_hits.append(hit)
                selected,locations,invalid,conflicts = audits[item]
                if (hit[1],hit[2]) in conflicts or (filing,(hit[1],hit[2])) in invalid:
                    problems.append('LATEST_FILING_CONFLICT:'+item)
                problems.extend(_component_conflicts(payload,facts,info,cutoff,c))
                if item in ('eps_diluted','diluted_shares'):
                    routes.append(dict(item=item,year_offset=k,**_route(c,filing)))
                if item=='eps_diluted' and k>0 and c._raw_shares(k) is not None and c.shares(k) is None:
                    problems.append('OFFICIAL_DILUTED_SHARE_BASIS_OR_JUMP_REJECTED')
                if item == 'diluted_shares':
                    reference = facts.cover_count(filing)
                    check = vf._shares_scale(hit[0],reference)
                    scale.append(dict(year_offset=k,**check))
                    if hit[0] <= 0:
                        problems.append('DILUTED_SHARE_COUNT_NOT_POSITIVE')
                    elif check['status'] == vf.SHARES_SCALE_UNCONFIRMED:
                        missing.append(vf.SHARES_SCALE_UNCONFIRMED)
                    if c.shares(k) is None and routes[-1]['factor'] is not None:
                        problems.append('OFFICIAL_SHARE_JUMP_LIMIT_REJECTED')
            if metric == 'fcf_per_share_cagr_3y' and len(year_hits)==len(items):
                if len({(h[1],h[2]) for h in year_hits}) != 1:
                    missing.append('FCF_NUMERATOR_DENOMINATOR_PERIOD_MISMATCH')
        # The official picker can return an older annual span after dropping a
        # latest conflicting span. Do not hide that explicit conflict by reuse.
        for item in items:
            for period in audits[item][3]:
                if any(abs((period[1]-c.end(k)).days)<=vf.YEAR_TOLERANCE_DAYS for k in (0,3)):
                    problems.append('LATEST_FILING_CONFLICT:'+item)
        route_bases={x['adoption_basis'] for x in routes}
        assumptions=sorted({a for x in routes for a in x['allowed_assumptions']})
        if metric=='fcf_per_share_cagr_3y' and c.profile!='GENERAL':
            missing.append('OFFICIAL_FINANCIAL_PROFILE_FCF_GROWTH_NOT_APPLICABLE')
        if problems or 'EXPLICIT_CONFLICT_EXCLUDED' in route_bases:
            basis='EXPLICIT_CONFLICT_EXCLUDED'
            reason=sorted(set(problems))[0] if problems else next(x['reason'] for x in routes if x['adoption_basis']==basis)
        elif missing or not routes or 'ADDITIONAL_VERIFICATION_REQUIRED' in route_bases:
            basis='ADDITIONAL_VERIFICATION_REQUIRED'
            reason=sorted(set(missing))[0] if missing else 'FILING_BASIS_UNAVAILABLE'
        elif assumptions:
            basis='OFFICIAL_ASSUMPTION_INHERITED';reason='OFFICIAL_SHARE_ASSUMPTIONS_DISCLOSED'
        elif 'FILING_SPLIT_ADJUSTED' in route_bases:
            basis='FILING_SPLIT_ADJUSTED';reason='REPORTED_SPLIT_FACT_AND_BASIS_PATH'
        else:
            basis='EVIDENCE_LINKED';reason='OFFICIAL_COMMON_PERIOD_OR_SAME_FILING_BASIS'
        raw = computed.get(metric)
        accepted = basis in BASES[:3] and _finite(raw)
        value = vf._round(raw) if accepted else None
        evidence_only = accepted and not assumptions and basis in BASES[:2]
        out['metrics'][metric] = dict(value=value,unrounded_value=raw if _finite(raw) else None,
            adoption_basis=basis,reason=(reason if basis not in BASES[:3] else
                'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE' if not accepted else None),
            basis_reason=reason,formula_status='NUMERIC' if _finite(raw) else 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE',
            allowed_assumptions=assumptions,requires_assumption=bool(assumptions),
            evidence_only_eligible=evidence_only,reusable=accepted,strict_verified=False,
            additional_verification_required=True,additional_verification=_context_qualifications(payload),
            blocking_reasons=sorted(set(problems+missing+[x['reason'] for x in routes if x['adoption_basis'] in BASES[3:]])),
            formula_variant=FORMULAS[metric],denominator_definition=DENOMINATOR,
            accounting_scope=['GENERAL'] if metric=='fcf_per_share_cagr_3y' else ['GENERAL','FINANCIAL'],
            formula_source='EXISTING_OFFICIAL_V2_FISCAL_KERNEL',periods=periods,endpoint_factors=routes,
            cover_scale_diagnostics=scale,cover_scale_applies_to='DIAGNOSTIC_HISTORY_REUSE_NO_REFERENCE_NOT_A_BLOCK',
            actual_share_issuance_interpretation=False,valuation_price_identity_verified=False)
    out['status'] = 'RAW_REUSABLE' if any(x['reusable'] for x in out['metrics'].values()) else 'NOT_REUSABLE'
    out['basis_filing'] = _filing(c._basis()) if c._basis() else None
    out['accounting_taxonomy']=tax;out['currency']=cur
    return out
