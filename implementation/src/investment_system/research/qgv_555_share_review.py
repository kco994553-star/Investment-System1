"""Owner-approved cross-filing share-basis review; no price/identity fabrication.

Only same annual period, same taxonomy/currency and paired diluted EPS/shares
can connect two filing bases. Missing overlap is not equality. Exact rational
arithmetic implements the approved integer/inverse-integer rule without a new
numerical tolerance. Metric arithmetic remains in the existing fiscal kernel.
"""
from collections import defaultdict, deque
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from itertools import combinations
from ..qgv import v2_factors as vf

VERSION = 'held-555-cross-filing-share-review/1'
METRICS = ('eps_cagr_3y', 'fcf_per_share_cagr_3y', 'dilution_3y')


def _fraction(value):
    if type(value) not in (int, float, Decimal):return None
    try:
        d=Decimal(str(value))
        return Fraction(d) if d.is_finite() else None
    except (InvalidOperation, ValueError):return None


def _filing(node):
    return dict(accession=node[0],filed=str(node[1]),filed_precision='DATE')


def _collect(payload, facts, item, cutoff):
    tax=payload['facts'][facts.taxonomy];unit=facts._unit(item)
    selected={};invalid=set();locations={};available=defaultdict(list)
    # Preserve the existing concept precedence within a filing/period. Conflicts
    # in its primary concept are retained as invalid, not hidden by a fallback.
    for concept in facts.concepts[item]:
        bykey=defaultdict(list)
        for n,r in enumerate(tax.get(concept,{}).get('units',{}).get(unit,[])):
            start,end,filed=(vf._day(r.get(k)) for k in ('start','end','filed'))
            val=_fraction(r.get('val'))
            if (None in (start,end,filed) or filed>cutoff or r.get('form') not in vf.ANNUAL_FORMS
                or not vf.ANNUAL_DAYS[0]<=(end-start).days<=vf.ANNUAL_DAYS[1]
                or val is None or not isinstance(r.get('accn'),str)):
                continue
            if item=='diluted_shares' and val<=0:continue
            key=((r['accn'],filed),(start,end))
            pointer='/facts/'+facts.taxonomy+'/'+concept+'/units/'+unit.replace('~','~0').replace('/','~1')+'/'+str(n)
            bykey[key].append((val,pointer))
        for key,rs in bykey.items():
            if key in selected or key in invalid:continue
            if len({v for v,p in rs})!=1:invalid.add(key);continue
            selected[key]=rs[0][0];locations[key]=[p for v,p in rs]
    # The same filed date with conflicting accessions/values cannot expose a
    # quiet older value through the existing per-period picker.
    byperiod=defaultdict(list)
    for (node,period),value in selected.items():byperiod[period].append((node,value))
    latest_conflicts=set()
    for period,rs in byperiod.items():
        latest=max(n[1] for n,v in rs)
        values={v for n,v in rs if n[1]==latest}
        if len(values)>1:latest_conflicts.add(period)
    for key in invalid:
        node,period=key
        if not byperiod.get(period) or node[1]>=max(n[1] for n,v in byperiod[period]):latest_conflicts.add(period)
    return selected,locations,invalid,latest_conflicts


def _paired_graph(eps,shares,eloc,sloc):
    perperiod=defaultdict(dict)
    for key,value in shares.items():
        if key in eps:perperiod[key[1]][key[0]]=(eps[key],value)
    comparisons=defaultdict(list);same_accession=[]
    for period,nodes in perperiod.items():
        for a,b in combinations(sorted(nodes,key=str),2):
            if a[0]==b[0]:
                same_accession.append(dict(from_filing=_filing(a),to_filing=_filing(b),
                    comparisons=[],status='UNKNOWN',reason='SAME_ACCESSION_IS_NOT_DISTINCT_FILINGS'))
                continue
            ea,sa=nodes[a];eb,sb=nodes[b];ratio=sb/sa
            clean=(ratio==1 or ratio.denominator==1 or ratio.numerator==1)
            coherent=ea==eb*ratio
            reason='MATCHED' if clean and coherent else 'NON_INTEGER_OR_INVERSE_RATIO' if not clean else 'EPS_SHARE_INVERSE_MISMATCH'
            comparisons[(a,b)].append(dict(period_start=str(period[0]),period_end=str(period[1]),
                factor_numerator=ratio.numerator,factor_denominator=ratio.denominator,reason=reason,
                source_pointers=eloc[(a,period)]+sloc[(a,period)]+eloc[(b,period)]+sloc[(b,period)]))
    graph=defaultdict(dict);accepted=[];rejected=same_accession
    for (a,b),rows in comparisons.items():
        ratios={Fraction(r['factor_numerator'],r['factor_denominator']) for r in rows}
        okay=all(r['reason']=='MATCHED' for r in rows) and len(ratios)==1
        item=dict(from_filing=_filing(a),to_filing=_filing(b),comparisons=rows)
        if okay:
            factor=next(iter(ratios));graph[a][b]=factor;graph[b][a]=1/factor
            item.update(factor_numerator=factor.numerator,factor_denominator=factor.denominator,
                        status='VERIFIED' if factor==1 else 'ADJUSTED')
            accepted.append(item)
        else:
            item.update(status='UNKNOWN',reason='INCONSISTENT_PERIOD_RATIOS' if len(ratios)>1 else rows[0]['reason'])
            rejected.append(item)
    return graph,accepted,rejected


def _factors_to_basis(graph,basis):
    if basis not in graph:return {},False
    factors={basis:Fraction(1)};q=deque([basis]);consistent=True
    while q:
        b=q.popleft()
        for a,edge_b_to_a in graph[b].items():
            value=factors[b]/edge_b_to_a
            if a in factors:
                if factors[a]!=value:consistent=False
            else:factors[a]=value;q.append(a)
    return factors,consistent


class _ReviewedCompany(vf._Company):
    def __init__(self,*args,reviewed_factors,**kwargs):
        super().__init__(*args,**kwargs);self.reviewed_factors=reviewed_factors
    def share_factor(self,filing,target=None):
        basis=self._basis() if target is None else target
        if basis!=self._basis():return None
        factor=self.reviewed_factors.get(filing)
        return None if factor is None else float(factor)


def review_share_history(payload,record,source_ref):
    if str(payload.get('cik')).zfill(10)!=record.get('cik'):raise ValueError('SHARE_SOURCE_ISSUER')
    out=dict(adapter_version=VERSION,issuer_id=record['cik'],source_refs=[source_ref],
        acquired_at=record['acquired_at'],fiscal_year_end=record.get('fiscal_year_end'),
        verification_rule='PAIRED_ANNUAL_EPS_AND_DILUTED_SHARES_EXACT_INTEGER_OR_INVERSE',
        historical_security_scope='ISSUER_REPORTED_DILUTED_COMMON_BASIS_NOT_VALUATION_PRICE_IDENTITY',
        metrics={m:dict(value=None,basis_status='UNKNOWN',reason='PERIOD_CONTEXT_UNAVAILABLE') for m in METRICS},
        status='UNKNOWN',accepted_edges=[],rejected_edges=[])
    cutoff=date.fromisoformat(record['acquired_at'][:10]);tax,cur=vf._taxonomy_and_currency(payload,cutoff)
    fy=vf._day(record.get('fiscal_year_end'))
    if not tax or not cur or not fy:return out
    if record.get('currency') and cur!=record['currency']:raise ValueError('SHARE_SOURCE_CURRENCY')
    facts=vf._Facts(payload,tax,cur,cutoff)
    eps,eloc,einvalid,econflicts=_collect(payload,facts,'eps_diluted',cutoff)
    shares,sloc,sinvalid,sconflicts=_collect(payload,facts,'diluted_shares',cutoff)
    graph,accepted,rejected=_paired_graph(eps,shares,eloc,sloc)
    base=vf._Company(facts,fy,sic=record.get('sic'),profile=record.get('profile','GENERAL'))
    basis=base._basis();factors,consistent=_factors_to_basis(graph,basis)
    out.update(basis_filing=_filing(basis) if basis else None,accepted_edges=accepted,rejected_edges=rejected,
        accounting_taxonomy=tax,currency=cur,graph_nodes=len(graph),graph_consistent=consistent,
        conflicted_periods=dict(eps=[list(map(str,x)) for x in sorted(econflicts)],shares=[list(map(str,x)) for x in sorted(sconflicts)]))
    company=_ReviewedCompany(facts,fy,sic=record.get('sic'),profile=record.get('profile','GENERAL'),reviewed_factors=factors)
    # Only the existing formulas generate metric values. A proved basis is
    # separate from positive-endpoint CAGR and cash-flow availability.
    computed=vf._metrics_general(company);vf._growth_common(company,computed)
    requests={'eps_cagr_3y':('eps_diluted',),'dilution_3y':('diluted_shares',),
              'fcf_per_share_cagr_3y':('diluted_shares',)}
    for metric,items in requests.items():
        needed=[];periods=[];conflict=False;missing=False
        for item in items:
            for k in (0,3):
                hit=facts.annual(item,company.end(k));filing=facts.annual_filing(item,company.end(k))
                if hit is None or filing is None:missing=True;continue
                periods.append(dict(item=item,period_start=str(hit[1]),period_end=str(hit[2]),filing=_filing(filing)))
                needed.append(filing)
                if (hit[1],hit[2]) in (econflicts if item=='eps_diluted' else sconflicts):conflict=True
        reason=('LATEST_FILING_CONFLICT' if conflict else 'ANNUAL_ENDPOINT_MISSING' if missing else
                'INCONSISTENT_SHARE_GRAPH' if not consistent else 'NO_PAIRED_CROSS_FILING_PATH' if not needed or any(n not in factors for n in needed) else None)
        if reason:
            out['metrics'][metric]=dict(value=None,basis_status='UNKNOWN',reason=reason,periods=periods);continue
        adjusted=any(factors[n]!=1 for n in needed)
        raw=computed[metric];value=vf._round(raw)
        out['metrics'][metric]=dict(value=value,unrounded_value=raw,
            basis_status='ADJUSTED' if adjusted else 'VERIFIED',reason=None if value is not None else 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE',
            periods=periods,endpoint_factors=[dict(filing=_filing(n),numerator=factors[n].numerator,denominator=factors[n].denominator) for n in needed],
            formula_source='EXISTING_V2_FISCAL_KERNEL',raw_precision='EXISTING_SIX_SIGNIFICANT_DIGITS')
    statuses={r['basis_status'] for r in out['metrics'].values()}
    out['status']='ADJUSTED' if 'ADJUSTED' in statuses else 'VERIFIED' if 'VERIFIED' in statuses else 'UNKNOWN'
    return out
