"""Project retained formula-versioned raw records into 555; no recomputation/fetch."""
from copy import deepcopy
from .qgv_555 import catalog, SHARE_METRICS
from .sector_qgv import timestamp, digest
from .dual_qgv import _classification_valid


def held_input(snapshot, sources, *, source_anchors):
    """sources: independently pinned {sha256, records}; latest acquired issuer point.

    This reads raw metrics, never infers availability from stored Q/G totals.
    All legacy FY and sector TTM definitions retain distinct variant IDs.
    """
    selected={};cats=catalog();cutoff=timestamp(snapshot['as_of'])
    for source in sources:
        for r in source['records'].values():
            issuer=r.get('cik')
            if not issuer or not r.get('acquired_at') or timestamp(r['acquired_at'])>cutoff:continue
            if r.get('calc_version')!='qgv2-calc/2026-10-23.1':continue
            if r.get('state') not in ('LIVE','STALE'):continue
            if issuer not in selected or timestamp(r['acquired_at'])>timestamp(selected[issuer][0]['acquired_at']):
                selected[issuer]=(r,source['sha256'])
    rows=[]
    for item in snapshot['rows']:
        r=deepcopy(item);template=r.get('accounting_template')
        classified=_classification_valid(r,snapshot)
        # Sector-only confirmation must not silently supply accounting GENERAL.
        template=template if classified else None
        metrics={};proof={};diagnostics={};source=selected.get(r.get('issuer_id'))
        if source:
            src,sha=source
            if template=='GENERAL' and src.get('profile')=='GENERAL':
                for m,v in src.get('metrics',{}).items():
                    if m not in cats:continue
                    metrics[m]=v
                    proof[m]=dict(status='VERIFIED',variant=cats[m]['variant'],available_at=src['acquired_at'],
                        source_refs=[f'sha256:{sha}#/records/{r["issuer_id"]}/metrics/{m}'],
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
        source_anchors=deepcopy(source_anchors),source_snapshot_hash=digest(snapshot),
        construction_rule='HELD_FORMULA_VERSIONED_RAW_PROJECTION/1',historical_pit=False,
        share_metrics_policy='NO_ADOPTION_WITHOUT_HISTORICAL_BASIS_PROOF')
