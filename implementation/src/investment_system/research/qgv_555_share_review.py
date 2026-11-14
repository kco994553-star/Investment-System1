"""Owner-approved cross-filing share-basis review; no price/identity fabrication.

Only same annual period, same taxonomy/currency and paired diluted EPS/shares
can connect two filing bases. Missing overlap is not equality. Exact rational
arithmetic implements the approved integer/inverse-integer rule without a new
numerical tolerance. Metric arithmetic remains in the existing fiscal kernel.
"""
from collections import defaultdict, deque
from datetime import date, datetime
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


# The original review and VERSION above are frozen for 0.2 reproduction. The
# two-stage review deliberately does not reuse its inferred integer-ratio edges.
TWO_STAGE_VERSION = 'held-555-share-eligibility/2'
TWO_STAGE_FORMULAS = {
    'eps_cagr_3y': 'REPORTED_DILUTED_EPS_CAGR_3Y',
    'fcf_per_share_cagr_3y': 'FCF_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y',
    'dilution_3y': 'WEIGHTED_DILUTED_SHARES_CAGR_3Y',
}
# This is an attributed, dilution-adjusted numerator, not consolidated profit
# or the basic-EPS numerator. Other taxonomy variants need their own definition.
_DILUTED_INCOME = ('NetIncomeLossAvailableToCommonStockholdersDiluted',)


def _v2_precision(row):
    """Source-declared XBRL rounding interval; JSON digits are not precision."""
    value = _fraction(row.get('val'))
    d = row.get('decimals')
    if d == 'INF':
        return Fraction(0)
    if type(d) is int or isinstance(d, str) and d.lstrip('-').isdigit():
        d = int(d)
        if -30 <= d <= 30:
            return Fraction(10) ** (-d) / 2
    # XBRL precision is significant digits, unlike decimals. Zero has no
    # order of magnitude, so a finite precision alone cannot bound it.
    p = row.get('precision')
    if type(p) is int or isinstance(p, str) and p.isdigit():
        p = int(p)
        if value and 1 <= p <= 30:
            exponent = Decimal(str(row['val'])).copy_abs().adjusted() - p + 1
            return Fraction(10) ** exponent / 2
    return None


def _v2_collect(payload, taxonomy, concepts, unit, cutoff, fact_contexts, evidence_cutoff):
    values = {}; invalid = set()
    tax = payload['facts'][taxonomy]
    for concept in concepts:
        grouped = defaultdict(list)
        for n, source in enumerate(tax.get(concept, {}).get('units', {}).get(unit, [])):
            if not isinstance(source, dict):
                continue
            start, end, filed = (vf._day(source.get(k)) for k in ('start', 'end', 'filed'))
            value = _fraction(source.get('val'))
            if (None in (start, end, filed) or filed > cutoff
                    or source.get('form') not in vf.ANNUAL_FORMS
                    or not vf.ANNUAL_DAYS[0] <= (end-start).days <= vf.ANNUAL_DAYS[1]
                    or value is None or not isinstance(source.get('accn'), str)):
                continue
            pointer = '/facts/' + taxonomy + '/' + concept + '/units/' + unit.replace('~', '~0').replace('/', '~1') + '/' + str(n)
            # Optional machine-readable context extraction is separate from the
            # pinned payload. Absence never becomes a fabricated common class.
            context = dict(source)
            extra = fact_contexts.get(pointer, {})
            if extra:
                context_ok = (extra.get('status') == 'VERIFIED' and extra.get('evidence_refs')
                    and extra.get('issuer_id') == str(payload.get('cik')).zfill(10)
                    and extra.get('period_start') == str(start) and extra.get('period_end') == str(end)
                    and extra.get('unit') == unit
                    and _v2_available_by(extra.get('available_at'), evidence_cutoff))
                if context_ok:
                    context.update({k: extra[k] for k in ('class_id', 'accounting_scope', 'decimals', 'precision', 'evidence_refs') if k in extra})
                else:
                    context['_review_context_invalid'] = True
            grouped[((source['accn'], filed), (start, end))].append(dict(
                value=value, pointer=pointer, source=source, context=context,
                unit=unit, tolerance=_v2_precision(context)))
        for key, rows in grouped.items():
            if key in values or key in invalid:
                continue
            signatures = {(r['context'].get('class_id'), r['context'].get('accounting_scope')) for r in rows}
            if len({r['value'] for r in rows}) != 1 or len(signatures) != 1:
                invalid.add(key)
            else:
                selected = dict(rows[0])
                # Equal values do not erase an ambiguous class/scope. For truly
                # duplicate contexts retain the least precise declared bound;
                # if any row lacks precision, it remains unknown.
                selected['tolerance'] = (None if any(r['tolerance'] is None for r in rows)
                                         else max(r['tolerance'] for r in rows))
                if any(r['context'].get('_review_context_invalid') for r in rows):
                    selected['context'] = dict(selected['context'], _review_context_invalid=True)
                values[key] = selected
    return values, invalid


def _v2_latest_conflicts(values, invalid):
    byperiod = defaultdict(list)
    for (node, period), row in values.items():
        byperiod[period].append((node, row['value']))
    conflicts = set()
    for period, rows in byperiod.items():
        latest = max(node[1] for node, value in rows)
        if len({value for node, value in rows if node[1] == latest}) > 1:
            conflicts.add(period)
    for node, period in invalid:
        if not byperiod.get(period) or node[1] >= max(n[1] for n, value in byperiod[period]):
            conflicts.add(period)
    return conflicts


def _v2_same(a, b):
    if a['value'] == b['value']:
        return True
    ta, tb = a['tolerance'], b['tolerance']
    return ta is not None and tb is not None and abs(a['value']-b['value']) <= ta+tb


def _v2_context_issues(rows):
    issues = []
    if any(r['context'].get('_review_context_invalid') for r in rows):
        issues.append('AUXILIARY_CONTEXT_EVIDENCE_INVALID')
    classes = {r['context'].get('class_id') for r in rows}
    scopes = {r['context'].get('accounting_scope') for r in rows}
    if None in classes or '' in classes:
        issues.append('SHARE_CLASS_CONTEXT_NOT_REPORTED')
    elif len(classes) != 1:
        issues.append('SHARE_CLASS_CONTEXT_MISMATCH')
    if None in scopes or '' in scopes:
        issues.append('ACCOUNTING_SCOPE_CONTEXT_NOT_REPORTED')
    elif len(scopes) != 1:
        issues.append('ACCOUNTING_SCOPE_CONTEXT_MISMATCH')
    if any(r['tolerance'] is None for r in rows):
        issues.append('SOURCE_ROUNDING_PRECISION_NOT_REPORTED')
    return issues


def _v2_triplet_coherent(eps, shares, income):
    # Interval arithmetic uses only declared rounding. Exact arithmetic can
    # confirm a numerical identity when source precision is unavailable.
    e, s, n = eps['value'], shares['value'], income['value']
    if e*s == n:
        return True
    te, ts, tn = eps['tolerance'], shares['tolerance'], income['tolerance']
    if None in (te, ts, tn):
        return False
    products = [(e+de)*(s+ds) for de in (-te, te) for ds in (-ts, ts)]
    return min(products) <= n+tn and max(products) >= n-tn


def _v2_stage1(eps, shares, income):
    triplets = {key: (eps[key], shares[key], income[key])
                for key in eps.keys() & shares.keys() & income.keys()
                if shares[key]['value'] > 0}
    perperiod = defaultdict(dict)
    for (filing, period), triplet in triplets.items():
        perperiod[period][filing] = triplet
    comparisons = []
    for period, filings in sorted(perperiod.items()):
        for a, b in combinations(sorted(filings, key=str), 2):
            if a[0] == b[0]:
                continue
            ea, sa, na = filings[a]; eb, sb, nb = filings[b]
            same_profit = _v2_same(na, nb)
            same_all = same_profit and _v2_same(ea, eb) and _v2_same(sa, sb)
            ratio = sb['value']/sa['value']
            clean = ratio != 1 and (ratio.denominator == 1 or ratio.numerator == 1)
            inverse = ea['value'] == eb['value']*ratio
            status = ('CONSISTENT' if same_all else 'SPLIT_CANDIDATE'
                      if same_profit and clean and inverse else 'UNCONFIRMED_CHANGE')
            rs = list(filings[a]) + list(filings[b])
            issues = _v2_context_issues(rs)
            coherent = _v2_triplet_coherent(*filings[a]) and _v2_triplet_coherent(*filings[b])
            if not coherent:
                issues.append('ATTRIBUTED_EPS_TRIPLET_COHERENCE_UNCONFIRMED')
            comparisons.append(dict(period_start=str(period[0]), period_end=str(period[1]),
                from_filing=_filing(a), to_filing=_filing(b), numerical_status=status,
                status='CONSISTENT' if status == 'CONSISTENT' and not issues else
                       'PARTIAL_CONSISTENCY' if status == 'CONSISTENT' else status,
                issues=issues, source_pointers=[r['pointer'] for r in rs],
                share_ratio=dict(numerator=ratio.numerator, denominator=ratio.denominator),
                adjustment_applied=False))
    statuses = {x['status'] for x in comparisons}
    status = ('SPLIT_CANDIDATE' if 'SPLIT_CANDIDATE' in statuses else
              'UNCONFIRMED_CHANGE' if 'UNCONFIRMED_CHANGE' in statuses else
              'CONSISTENT' if statuses == {'CONSISTENT'} else
              'PARTIAL_CONSISTENCY' if comparisons else 'UNKNOWN')
    return dict(status=status, annual_triplets=len(triplets), comparisons=comparisons,
        numeric_consistency_comparisons=sum(x['numerical_status'] == 'CONSISTENT' for x in comparisons),
        confirmed_consistency_comparisons=sum(x['status'] == 'CONSISTENT' for x in comparisons),
        split_candidate_comparisons=sum(x['status'] == 'SPLIT_CANDIDATE' for x in comparisons),
        unconfirmed_change_comparisons=sum(x['status'] == 'UNCONFIRMED_CHANGE' for x in comparisons))


def _v2_available_by(value, acquired_at):
    """Do not discard timestamp precision or invent a date-only time."""
    if not isinstance(value, str):
        return False
    try:
        acquired = datetime.fromisoformat(acquired_at.replace('Z', '+00:00'))
        if len(value) == 10:
            # A date-only statement on the cutoff day cannot prove that it
            # preceded an intraday cutoff. Its original DATE precision remains.
            return date.fromisoformat(value) < acquired.date()
        available = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return acquired.tzinfo is not None and available.tzinfo is not None and available <= acquired
    except (ValueError, TypeError):
        return False


def _v2_basis_proof(evidence, record, evidence_cutoff, basis, periods, filings, contexts):
    """Require explicit period-basis evidence, not repeated numerical values."""
    for item in evidence:
        if not isinstance(item, dict):
            continue
        start = vf._day(item.get('period_start')); end = vf._day(item.get('period_end'))
        if (item.get('status') != 'VERIFIED' or item.get('issuer_id') != record['cik']
                or item.get('currency') != record.get('currency')
                or item.get('basis_method') not in (
                    'EXPLICIT_SAME_BASIS_COMPARATIVES', 'EXPLICIT_RETROSPECTIVE_ADJUSTMENT')
                or not item.get('evidence_refs') or start is None or end is None
                or not _v2_available_by(item.get('available_at'), evidence_cutoff)
                or not periods or start > min(p[0] for p in periods) or end < max(p[1] for p in periods)
                or item.get('basis_accession') != (basis[0] if basis else None)
                or not {f[0] for f in filings}.issubset(set(item.get('filing_accessions', [])))):
            continue
        if any(r['context'].get('class_id') != item.get('class_id')
               or r['context'].get('accounting_scope') != item.get('accounting_scope') for r in contexts):
            continue
        return item
    return None


def review_share_eligibility_v2(payload, record, source_ref, *, fact_contexts=None, period_evidence=None, review_cutoff=None):
    """Review annual historical share metrics in two independent stages.

    `fact_contexts` is a pointer-keyed, evidence-backed extraction of class,
    scope and source precision, never an entity/ticker-to-security shortcut.
    `period_evidence` contains an explicit comparative/common-basis statement
    covering the calculation period and named filings. Companyfacts alone
    normally lacks these contexts; exact duplicate numbers remain a diagnostic.
    No price identity, current representative security or future event is used.
    """
    if str(payload.get('cik')).zfill(10) != record.get('cik'):
        raise ValueError('SHARE_SOURCE_ISSUER')
    fact_contexts = fact_contexts or {}; period_evidence = period_evidence or []
    evidence_cutoff = review_cutoff or record['acquired_at']
    # Parse/validate the explicit input cutoff without changing source acquisition.
    try:
        evidence_clock = datetime.fromisoformat(evidence_cutoff.replace('Z', '+00:00'))
        source_clock = datetime.fromisoformat(record['acquired_at'].replace('Z', '+00:00'))
        if evidence_clock.tzinfo is None or source_clock.tzinfo is None or evidence_clock < source_clock:
            raise ValueError('SHARE_REVIEW_CUTOFF')
    except (ValueError, TypeError, AttributeError):
        raise ValueError('SHARE_REVIEW_CUTOFF') from None
    cutoff = date.fromisoformat(record['acquired_at'][:10])
    tax, cur = vf._taxonomy_and_currency(payload, cutoff); fy = vf._day(record.get('fiscal_year_end'))
    out = dict(adapter_version=TWO_STAGE_VERSION, review_version=TWO_STAGE_VERSION,
        issuer_id=record['cik'], acquired_at=record['acquired_at'], fiscal_year_end=record.get('fiscal_year_end'),
        source_refs=[source_ref], metrics={}, status='UNKNOWN',
        source_input_cutoff=record['acquired_at'], review_input_cutoff=evidence_cutoff,
        temporal_scope='CURRENT_HELD_DOCUMENT_RECONSTRUCTION_NOT_HISTORICAL_SYSTEM_PIT',
        historical_security_scope='ISSUER_REPORTED_DILUTED_COMMON_BASIS_NOT_VALUATION_PRICE_IDENTITY',
        precision_policy='EXPLICIT_XBRL_DECIMALS_OR_PRECISION_HALF_UNIT_INTERVAL_ELSE_EXACT_NUMERICAL_DIAGNOSTIC_ONLY')
    if not tax or not cur or not fy:
        stage1 = dict(status='UNKNOWN', annual_triplets=0, comparisons=[],
                      numeric_consistency_comparisons=0, confirmed_consistency_comparisons=0,
                      split_candidate_comparisons=0, unconfirmed_change_comparisons=0)
        for metric in METRICS:
            out['metrics'][metric] = dict(value=None, raw_value=None, basis_status='UNKNOWN',
                reason='PERIOD_CONTEXT_UNAVAILABLE', stage1=stage1,
                stage2=dict(status='UNCONFIRMED_PERIOD_BASIS', all_used_years_linked=False,
                    documented_common_basis=False, evidence_refs=[], issues=['PERIOD_CONTEXT_UNAVAILABLE']),
                corporate_action=dict(status='UNKNOWN', adjustment_applied=False, evidence_refs=[]),
                denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES', formula_variant=TWO_STAGE_FORMULAS[metric])
        out['stage1'] = stage1
        return out
    if record.get('currency') and cur != record['currency']:
        raise ValueError('SHARE_SOURCE_CURRENCY')
    facts = vf._Facts(payload, tax, cur, cutoff)
    collections = {}; invalid = {}
    for item in ('eps_diluted', 'diluted_shares', 'operating_cash_flow', 'capital_expenditure'):
        collections[item], invalid[item] = _v2_collect(payload, tax, facts.concepts[item], facts._unit(item), cutoff, fact_contexts, evidence_cutoff)
    income, income_invalid = _v2_collect(payload, tax, _DILUTED_INCOME if tax == 'us-gaap' else (), cur, cutoff, fact_contexts, evidence_cutoff)
    collections['diluted_attributed_income'] = income; invalid['diluted_attributed_income'] = income_invalid
    conflicts = {item: _v2_latest_conflicts(rows, invalid[item]) for item, rows in collections.items()}
    stage1 = _v2_stage1(collections['eps_diluted'], collections['diluted_shares'], income)
    out.update(stage1=stage1, accounting_taxonomy=tax, currency=cur,
        conflicted_periods={item: [list(map(str, period)) for period in sorted(periods)] for item, periods in conflicts.items()})
    base = vf._Company(facts, fy, sic=record.get('sic'), profile=record.get('profile', 'GENERAL'))
    basis = base._basis(); out['basis_filing'] = _filing(basis) if basis else None
    # All arithmetic, CAGR domains and published rounding remain in the existing
    # kernel. Identity factors are supplied only after a documented basis proof.
    requests = {'eps_cagr_3y': ('eps_diluted', 'diluted_shares', 'diluted_attributed_income'),
                'fcf_per_share_cagr_3y': ('diluted_shares', 'operating_cash_flow', 'capital_expenditure'),
                'dilution_3y': ('diluted_shares',)}
    for metric, items in requests.items():
        needed = []; periods = []; nodes = set(); issues = []; byyear = []
        for k in (0, 3):
            if any(abs((period[1]-base.end(k)).days) <= vf.YEAR_TOLERANCE_DAYS
                   for item in items for period in conflicts[item]):
                issues.append('LATEST_FILING_CONFLICT')
            share_hit = facts.annual('diluted_shares', base.end(k))
            share_filing = facts.annual_filing('diluted_shares', base.end(k))
            if share_hit is None or share_filing is None:
                issues.append('DILUTED_SHARES_ANNUAL_YEAR_MISSING'); continue
            period = (share_hit[1], share_hit[2]); year_rows = []
            for item in items:
                if item == 'diluted_attributed_income':
                    key = (share_filing, period)
                else:
                    hit = facts.annual(item, base.end(k)); filing = facts.annual_filing(item, base.end(k))
                    if hit is None or filing is None:
                        issues.append(item.upper() + '_ANNUAL_YEAR_MISSING'); continue
                    key = (filing, (hit[1], hit[2]))
                if key in invalid[item] or key[1] in conflicts[item]:
                    issues.append('LATEST_FILING_CONFLICT'); continue
                row = collections[item].get(key)
                if row is None:
                    issues.append(item.upper() + '_ANNUAL_YEAR_MISSING'); continue
                if key[1] != period:
                    issues.append('ANNUAL_PERIOD_MISMATCH')
                if key[0] != share_filing:
                    issues.append('NUMERATOR_DENOMINATOR_FILING_MISMATCH')
                if item == 'diluted_shares' and row['value'] <= 0:
                    issues.append('DILUTED_SHARES_NOT_POSITIVE')
                needed.append(row); year_rows.append(row); nodes.add(key[0]); periods.append(key[1])
            byyear.append(dict(period_start=str(period[0]), period_end=str(period[1]),
                filing=_filing(share_filing), source_pointers=[r['pointer'] for r in year_rows]))
            if metric == 'eps_cagr_3y' and len(year_rows) == 3 and not _v2_triplet_coherent(*year_rows):
                issues.append('ATTRIBUTED_EPS_TRIPLET_COHERENCE_UNCONFIRMED')
        issues += _v2_context_issues(needed) if needed else ['ANNUAL_INPUTS_MISSING']
        # A same-filing comparative/overlap chain is still required. A named
        # basis statement cannot silently bridge years with no common facts.
        pernode = defaultdict(set)
        for (node, period), row in collections['diluted_shares'].items():
            if row['value'] > 0:
                pernode[node].add(period)
        graph = defaultdict(set)
        for a, b in combinations(pernode, 2):
            if a[0] == b[0]:
                continue
            overlap = pernode[a] & pernode[b]
            if overlap:
                # Without numeric equality a cross-filing split candidate is
                # not adjusted; a later already-adjusted comparative series is
                # usable when it alone covers all calculation years.
                edges = [row for p in overlap for row in (collections['diluted_shares'][(a, p)], collections['diluted_shares'][(b, p)])]
                edge_scope = _v2_context_issues(edges + needed)
                if (not edge_scope and not overlap.intersection(conflicts['diluted_shares'])
                        and all(_v2_same(collections['diluted_shares'][(a, p)], collections['diluted_shares'][(b, p)]) for p in overlap)):
                    graph[a].add(b); graph[b].add(a)
        proof = _v2_basis_proof(period_evidence, record, evidence_cutoff, basis, periods, nodes, needed)
        # Search within the explicitly documented filings when a proof exists;
        # an undocumented alternate path must not hide a valid documented path.
        allowed = set(proof['filing_accessions']) if proof else None
        reachable = {basis} if basis else set(); frontier = list(reachable); parents = {basis: None} if basis else {}
        while frontier:
            a = frontier.pop()
            for b in sorted(graph[a] - reachable, key=str):
                if allowed is not None and b[0] not in allowed:
                    continue
                reachable.add(b); frontier.append(b); parents[b] = a
        linked = len(byyear) == 2 and nodes.issubset(reachable)
        if not linked:
            issues.append('FULL_PERIOD_COMPARATIVE_OVERLAP_CHAIN_UNCONFIRMED')
        chain_nodes = set()
        for node in nodes & reachable:
            while node is not None and node not in chain_nodes:
                chain_nodes.add(node); node = parents[node]
        if proof is None:
            issues.append('EXPLICIT_FULL_PERIOD_COMMON_BASIS_EVIDENCE_MISSING')
        issues = sorted(set(issues))
        eligible = not issues and linked and proof is not None
        value = None; raw = None
        if eligible:
            company = _ReviewedCompany(facts, fy, sic=record.get('sic'), profile=record.get('profile', 'GENERAL'),
                reviewed_factors={node: Fraction(1) for node in reachable})
            computed = vf._metrics_general(company); vf._growth_common(company, computed)
            raw = computed[metric]; value = vf._round(raw)
        retained = record.get('metrics', {}).get(metric)
        if raw is None and _fraction(retained) is not None:
            raw = retained
        candidate = stage1['split_candidate_comparisons'] > 0
        action = dict(status='CANDIDATE' if candidate else 'UNKNOWN', adjustment_applied=False, evidence_refs=[])
        if eligible:
            # Explicit source restatement is consumed as already adjusted: do
            # not apply an inferred or second corporate-action factor.
            action = dict(status='CONFIRMED' if proof['basis_method'] == 'EXPLICIT_RETROSPECTIVE_ADJUSTMENT' else 'UNKNOWN',
                          adjustment_applied=False, evidence_refs=list(proof['evidence_refs']))
        out['metrics'][metric] = dict(value=value, raw_value=raw,
            raw_value_source='EXISTING_FISCAL_KERNEL' if eligible else 'RETAINED_SOURCE_RECORD_DIAGNOSTIC',
            basis_status='VERIFIED' if eligible else 'UNKNOWN',
            reason=None if eligible and value is not None else 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE' if eligible else issues[0],
            stage1={k: v for k, v in stage1.items() if k != 'comparisons'}, stage2=dict(status='FINAL_ELIGIBLE' if eligible else 'UNCONFIRMED_PERIOD_BASIS',
                all_used_years_linked=linked, documented_common_basis=proof is not None,
                evidence_refs=list(proof['evidence_refs']) if proof else [], issues=issues,
                annual_periods=byyear, required_chain_filings=[_filing(x) for x in sorted(chain_nodes, key=str)], overlap_chain=[dict(filing=_filing(node), overlapping_filings=[_filing(x) for x in sorted(graph[node], key=str)]) for node in sorted(reachable, key=str)]),
            corporate_action=action, denominator_definition='WEIGHTED_AVERAGE_DILUTED_SHARES',
            formula_variant=TWO_STAGE_FORMULAS[metric], formula_source='EXISTING_V2_FISCAL_KERNEL')
    out['status'] = 'FINAL_ELIGIBLE' if any(m['basis_status'] == 'VERIFIED' for m in out['metrics'].values()) else 'UNKNOWN'
    return out
