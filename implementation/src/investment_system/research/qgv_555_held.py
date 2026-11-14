"""Project retained formula-versioned raw records into 555; no recomputation/fetch."""
from copy import deepcopy
from .qgv_555 import catalog, SHARE_METRICS
from .sector_qgv import timestamp, digest
from .dual_qgv import _classification_valid


def held_fy_debt_metric(payload, record, reference):
    """Connect an explicit FY debt total to the existing FY metric kernel.

    Quarterly repaired sector debt is not substituted for annual 555 debt.
    This returns raw evidence only, with no security/price or accounting approval.
    """
    from datetime import date
    from ..qgv import v2_factors as vf
    from .sector_qgv_held import _connect_explicit_debt
    if str(payload.get('cik')).zfill(10) != record.get('cik'):
        raise ValueError('DEBT_SOURCE_ISSUER_MISMATCH')
    out = dict(metric='net_debt_to_ebitda', value=None, unrounded_value=None, components={}, reasons={},
               source_reference=reference, adapter_version='held-555-fy-debt/2')
    if record.get('profile') != 'GENERAL':
        out['reasons']['accounting'] = 'ACCOUNTING_NOT_APPLICABLE'
        return out
    cutoff = date.fromisoformat(record['acquired_at'][:10])
    taxonomy, currency = vf._taxonomy_and_currency(payload, cutoff)
    if not taxonomy or not record.get('fiscal_year_end'):
        out['reasons']['context'] = 'PERIOD_OR_CURRENCY_UNCONFIRMED'
        return out
    if record.get('currency') and currency != record['currency']:
        raise ValueError('DEBT_SOURCE_CURRENCY_MISMATCH')
    facts = vf._Facts(payload, taxonomy, currency, cutoff)
    company = vf._Company(facts, date.fromisoformat(record['fiscal_year_end']),
                          sic=record.get('sic'), profile=record['profile'])
    end = company.end(0)
    if company.debt(0) is not None:
        out['reasons']['debt'] = 'EXISTING_DEBT_INPUT_PRESERVED'
        return out
    assets = facts.instant('total_assets', end, 0)
    if assets is None:
        out['reasons']['assets'] = 'EXACT_FY_BALANCE_ANCHOR_MISSING'
        return out
    fields = dict(assets_end=dict(value=assets, period_end=str(end), currency=currency))
    _connect_explicit_debt(payload, fields, out['reasons'], cutoff)
    out['components'] = fields
    if 'debt' not in fields:
        return out
    # Inject only the validated component. All arithmetic remains in the old
    # calculator; its unrelated computed outputs are deliberately not adopted.
    company._cache[('debt', 0)] = fields['debt']['value']
    for name, item in [('ebit', 'ebit'), ('da', 'depreciation_amortization')]:
        hit = company.annual_hit(item, end)
        fields[name] = None if hit is None else dict(value=hit[0], period_start=str(hit[1]),
                                                    period_end=str(hit[2]), currency=currency)
    fields['cash'] = dict(value=company.i('cash_and_equivalents', 0),
                          target_end=str(end), currency=currency,
                          period_policy='EXISTING_FY_INSTANT_TOLERANCE')
    out['unrounded_value'] = vf._metrics_general(company)['net_debt_to_ebitda']
    # compute_reported_periods publishes/ranks these legacy raw metrics at six
    # significant digits. Keep precise audit arithmetic separate from that input.
    out['value'] = vf._round(out['unrounded_value'])
    out['raw_precision_policy'] = 'EXISTING_PUBLISHED_SIX_SIGNIFICANT_DIGITS'
    if out['value'] is None:
        out['reasons']['metric'] = 'OTHER_REQUIRED_COMPONENT_MISSING_OR_DENOMINATOR_INVALID'
    return out


def connect_fy_debt_review(snapshot, entries, *, reviewed_at, input_cutoff):
    """Apply a pinned, narrow repair without rewriting an old input version."""
    import hashlib
    import json
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('DEBT_REVIEW_TIME')
    out = deepcopy(snapshot); audits = []; seen = set()
    out['input_cutoff'] = input_cutoff
    for entry in entries:
        record = entry['record']; key = (record['cik'], record['acquired_at'], record['fiscal_year_end'])
        if key in seen:raise ValueError('DUPLICATE_DEBT_REVIEW')
        seen.add(key)
        raw = entry['source_bytes']; sha = hashlib.sha256(raw).hexdigest()
        if sha != entry['sha256'] or record.get('source_sha256', {}).get('companyfacts') != sha:
            raise ValueError('DEBT_SOURCE_HASH')
        if '#sha256='+sha not in entry['reference'] or timestamp(record['acquired_at']) > timestamp(reviewed_at):
            raise ValueError('DEBT_SOURCE_CONTEXT')
        audit = held_fy_debt_metric(json.loads(raw), record, entry['reference'])
        audit.update(issuer_id=record['cik'], source_sha256=sha, linked_rows=[], row_decisions=[],
                     retrieved_at=record['acquired_at'], reviewed_at=reviewed_at)
        metric = audit['metric']
        for row in out['rows']:
            if row.get('issuer_id') != record['cik']:continue
            proof = row.get('metric_evidence', {}).get(metric) or {}
            # Published raw records omit null metric keys. In that case bind the
            # fiscal context through retained legacy evidence, not an unrelated
            # TTM observation or the issuer ID alone.
            if not proof:
                contexts = [p for name,p in row.get('metric_evidence', {}).items()
                    if not name.startswith('sector::') and p.get('status') == 'VERIFIED'
                    and p.get('source_formula_version') == record.get('calc_version')
                    and p.get('period_end') == record['fiscal_year_end']
                    and p.get('available_at') == record['acquired_at'] and p.get('source_refs')]
                if contexts:
                    proof = dict(contexts[0], variant=catalog()[metric]['variant'])
            if (row.get('accounting_template') != 'GENERAL' or
                proof.get('period_end') != record['fiscal_year_end'] or
                proof.get('available_at') != record['acquired_at']):
                audit['row_decisions'].append(dict(company_id=row['company_id'],
                    cause='ACCOUNTING_UNCONFIRMED_OR_NOT_APPLICABLE' if row.get('accounting_template') != 'GENERAL'
                    else 'RETAINED_FISCAL_CONTEXT_MISMATCH'))
                continue
            if row['metrics'].get(metric) is not None or audit['value'] is None:
                audit['row_decisions'].append(dict(company_id=row['company_id'],
                    cause='EXISTING_METRIC_PRESERVED' if row['metrics'].get(metric) is not None else 'RAW_NOT_COMPUTABLE',
                    component_reasons=deepcopy(audit['reasons'])))
                continue
            row['metrics'][metric] = audit['value']
            row['metric_evidence'][metric] = dict(proof, available_at=reviewed_at,
                retrieved_at=record['acquired_at'], reviewed_at=reviewed_at,
                source_refs=[entry['reference']], original_input_context_evidence=deepcopy(proof),
                component_evidence=deepcopy(audit['components']),
                adapter_version=audit['adapter_version'])
            row.setdefault('diagnostics', {})[metric] = 'HELD_EXPLICIT_FY_DEBT_CONNECTED'
            audit['linked_rows'].append(row['company_id'])
            audit['row_decisions'].append(dict(company_id=row['company_id'],cause='INPUT_CONNECTED'))
        audits.append(audit)
    out['review_context'] = dict(original_input_hash=digest(snapshot),
        original_input_cutoff=snapshot['input_cutoff'], reviewed_at=reviewed_at,
        result_kind='RETROSPECTIVE_REVIEW', historical_system_pit_complete=False,
        evidence_hash=digest(audits))
    out['source_anchors'] = [*deepcopy(snapshot.get('source_anchors', [])),
                            dict(repair='held-555-fy-debt/2', evidence_hash=digest(audits))]
    return out, audits


def held_input(snapshot, sources, *, source_anchors):
    """sources: independently pinned {sha256, records}; latest acquired issuer point.

    This reads raw metrics, never infers availability from stored Q/G totals.
    All legacy FY and sector TTM definitions retain distinct variant IDs.
    """
    selected={};cats=catalog();cutoff=timestamp(snapshot['as_of'])
    for source in sources:
        for record_key,r in source['records'].items():
            issuer=r.get('cik')
            if not issuer or not r.get('acquired_at') or timestamp(r['acquired_at'])>cutoff:continue
            if r.get('calc_version')!='qgv2-calc/2026-10-23.1':continue
            if r.get('state') not in ('LIVE','STALE'):continue
            if issuer not in selected or timestamp(r['acquired_at'])>timestamp(selected[issuer][0]['acquired_at']):
                # Source files use different containers and row keys. Issuer IDs
                # identify entities; they are not automatically JSON member keys.
                tokens=(source.get('records_key','records'),str(record_key))
                pointer='/'+'/'.join(x.replace('~','~0').replace('/','~1') for x in tokens)
                selected[issuer]=(r,source['sha256'],pointer)
    rows=[]
    for item in snapshot['rows']:
        r=deepcopy(item);template=r.get('accounting_template')
        classified=_classification_valid(r,snapshot)
        # Sector-only confirmation must not silently supply accounting GENERAL.
        template=template if classified else None
        metrics={};proof={};diagnostics={};source=selected.get(r.get('issuer_id'))
        if source:
            src,sha,pointer=source
            if template=='GENERAL' and src.get('profile')=='GENERAL':
                for m,v in src.get('metrics',{}).items():
                    if m not in cats:continue
                    metrics[m]=v
                    proof[m]=dict(status='VERIFIED',variant=cats[m]['variant'],available_at=src['acquired_at'],
                        source_refs=[f'sha256:{sha}#{pointer}/metrics/{m}'],
                        source_formula_version=src['calc_version'],period_end=src.get('fiscal_year_end'),
                        currency=src.get('currency'),historical_share_basis='UNKNOWN' if m in SHARE_METRICS else None)
            else:diagnostics['legacy_metrics']='ACCOUNTING_PROFILE_NOT_INTERCHANGEABLE'
        else:diagnostics['legacy_metrics']='RETAINED_RAW_RECORD_NOT_LINKED'
        for v,obs in r.get('observations',{}).items():
            name='sector::'+v
            if name not in cats:continue
            if obs.get('status') not in ('VALID','VALID_NEGATIVE','VALID_ZERO'):continue
            # These observations already passed the common raw validator. Keep its
            # recipe, periods and evidence; never reinterpret them as legacy FY.
            metrics[name]=obs['value']
            proof[name]=dict(status='VERIFIED',variant=cats[name]['variant'],available_at=obs['source_available_at'],
                source_refs=obs['provenance'],period=obs.get('fiscal_period'),currency=obs.get('currency'),
                original_observation=deepcopy(obs))
        g=r.get('gate') or {}
        gate=dict(percentile=g.get('q_industry_percentile'),evaluation_day=g.get('as_of'),
            calc_version=g.get('calc_version'),source_refs=g.get('provenance'),original=deepcopy(g))
        rows.append(dict(company_id=r['company_id'],issuer_id=r.get('issuer_id'),security_id=r.get('security_id'),
            sector_id=r.get('sector_id') if classified else None,accounting_template=template,
            industry_group=source[0].get('industry_group') if source else None,
            classification_record_id=r.get('classification_record_id'),classification_mapping=r.get('mapping'),
            classification_status='VERIFIED' if classified else 'UNKNOWN',
            metrics=metrics,metric_evidence=proof,gate=gate,diagnostics=diagnostics))
    return dict(schema_version='qgv-555-input/1',population_id=snapshot['universe_id'],population_version=snapshot['universe_version'],
        members=deepcopy(snapshot['members']),rows=rows,evaluation_day=snapshot['valuation_date'],
        input_cutoff=snapshot['as_of'],classification_version=snapshot['mapping_version'],
        classification_context=deepcopy(snapshot.get('classification_context')),
        source_anchors=deepcopy(source_anchors),source_snapshot_hash=digest(snapshot),
        construction_rule='HELD_FORMULA_VERSIONED_RAW_PROJECTION/2',historical_pit=False,
        share_metrics_policy='NO_ADOPTION_WITHOUT_HISTORICAL_BASIS_PROOF')
