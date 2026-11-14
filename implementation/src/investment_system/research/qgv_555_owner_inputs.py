"""Owner-approved temporary 555 inputs; original classification remains evidence.

No classification is invented, no financial formula is recomputed, and no
FINANCIAL score is inserted into a 555 role. Temporary permissions belong only
to the new research configuration, not the original official/common records.
"""
from copy import deepcopy
import math
import re
from .qgv_555 import catalog, SHARE_METRICS
from .sector_qgv import digest, timestamp

POLICY = 'owner-555-temporary-official-inputs/2026-11-14.1'
CALC = 'qgv2-calc/2026-10-23.1'


def _selected_sources(sources, cutoff):
    selected = {}
    for source in sources:
        for key, record in source['records'].items():
            issuer, acquired = record.get('cik'), record.get('acquired_at')
            if (not issuer or not acquired or timestamp(acquired) > cutoff or
                record.get('calc_version') != CALC or record.get('state') not in ('LIVE', 'STALE')):
                continue
            tokens = (source.get('records_key', 'records'), str(key))
            pointer = '/' + '/'.join(t.replace('~', '~0').replace('/', '~1') for t in tokens)
            candidate = (record, source['sha256'], pointer)
            if issuer not in selected or timestamp(acquired) > timestamp(selected[issuer][0]['acquired_at']):
                selected[issuer] = candidate
    return selected


def temporary_official_inputs(snapshot, sources, *, original_snapshot,
                              original_snapshot_sha256, reviewed_at, input_cutoff):
    """Restore held raw metrics only where the owner permits temporary GENERAL.

    Official SIC/profile is a temporary accounting/industry classification, not
    an invented common 10-sector mapping. A sector previously confirmed in the
    original common classification can be restored independently of accounting.
    """
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('OWNER_INPUT_REVIEW_TIME')
    original = {r['company_id']: r for r in original_snapshot['rows']}
    if (set(original) != set(snapshot['members']) or len(original) != len(original_snapshot['rows']) or
        original_snapshot['valuation_date'] != snapshot['evaluation_day']):
        raise ValueError('OWNER_INPUT_ORIGINAL_POPULATION')
    if not re.fullmatch('[0-9a-f]{64}', original_snapshot_sha256):
        raise ValueError('OWNER_INPUT_ORIGINAL_HASH')
    selected = _selected_sources(sources, timestamp(snapshot['input_cutoff']))
    out = deepcopy(snapshot); out['input_cutoff'] = input_cutoff
    cats = catalog(); audit = []
    for row in out['rows']:
        old = original[row['company_id']]
        if row.get('issuer_id') != old.get('issuer_id'):
            raise ValueError('OWNER_INPUT_ORIGINAL_ISSUER')
        template = row.get('accounting_template')
        calc_template = template
        calc_sector = row.get('sector_id')
        entry = selected.get(row.get('issuer_id'))
        item = dict(company_id=row['company_id'], issuer_id=row.get('issuer_id'),
                    original_accounting_template=template, restored_metrics=[], restored_sector=False)
        temporary = dict(status='NOT_REQUIRED', label=None, reason=None, policy=POLICY,
                         original_classification_record_id=row.get('classification_record_id'))
        if entry:
            src, sha, pointer = entry
            refs = [f'sha256:{sha}#{pointer}']
            row['owner_source_context'] = dict(source_sha256=sha, source_pointer=pointer,
                record_hash=digest(src), profile=src.get('profile'), sic=src.get('sic'),
                industry_group=src.get('industry_group'), fiscal_year_end=src.get('fiscal_year_end'),
                acquired_at=src['acquired_at'], currency=src.get('currency'), calc_version=src['calc_version'],
                companyfacts_sha256=src.get('source_sha256', {}).get('companyfacts'))
            row['calculation_industry_group'] = src.get('industry_group')
            if src.get('profile') == 'FINANCIAL':
                calc_template = None
                temporary.update(status='REFERENCE_ONLY', label='금융 공식 FINANCIAL 참고',
                    reason='FINANCIAL_NOT_A_555_RECIPE', source_refs=refs)
                row['financial_reference'] = dict(model_id=CALC, profile='FINANCIAL',
                    axes=deepcopy(src.get('axes')), factors=deepcopy(src.get('factors')),
                    acquired_at=src['acquired_at'], fiscal_year_end=src.get('fiscal_year_end'),
                    source_refs=refs, counts_as_555=False, replaces_555=False)
            elif src.get('profile') == 'GENERAL' and template in (None, 'EQUITY_REIT', 'GENERAL'):
                calc_template = 'GENERAL'
                if template is None:
                    temporary.update(status='TEMPORARY_OFFICIAL_PROFILE', label='공식 프로필·SIC 임시 분류',
                        reason='COMMON_ACCOUNTING_OR_CLASSIFICATION_UNCONFIRMED', source_refs=refs)
                elif template == 'EQUITY_REIT':
                    temporary.update(status='TEMPORARY_REIT_GENERAL', label='REIT 임시(일반기업 식)',
                        reason='FFO_AFFO_RECIPE_PENDING', source_refs=refs)
                if template != 'GENERAL':
                    for metric, value in src.get('metrics', {}).items():
                        if metric not in cats or metric in row['metrics']:
                            continue
                        row['metrics'][metric] = value
                        row['metric_evidence'][metric] = dict(status='VERIFIED', variant=cats[metric]['variant'],
                            available_at=src['acquired_at'], reviewed_at=reviewed_at,
                            source_refs=[f'sha256:{sha}#{pointer}/metrics/{metric}'],
                            source_formula_version=CALC, period_end=src.get('fiscal_year_end'),
                            currency=src.get('currency'),
                            historical_share_basis='UNKNOWN' if metric in SHARE_METRICS else None)
                        item['restored_metrics'].append(metric)
            else:
                calc_template = None
                temporary.update(status='UNCONFIRMED', label='공식 프로필 연결 미확인',
                    reason='PROFILE_OR_COMMON_ACCOUNTING_CONFLICT', source_refs=refs)
        else:
            temporary.update(status='UNCONFIRMED', label='공식 프로필 자료 미연결',
                reason='HELD_FORMULA_VERSIONED_RECORD_NOT_LINKED')
            if template is None:calc_template = None
            row['calculation_industry_group'] = row.get('industry_group')
        # The common adapter writes component_mappings only for CONFIRMED
        # components. Accounting UNKNOWN must not erase a confirmed sector.
        sector_mapping = old.get('component_mappings', {}).get('sector')
        if (calc_sector is None and old.get('sector_id') and sector_mapping and
            sector_mapping.get('evidence_refs')):
            calc_sector = old['sector_id']; item['restored_sector'] = True
            row['calculation_sector_evidence'] = dict(
                source_ref=f'sha256:{original_snapshot_sha256}#/rows/{list(original).index(row["company_id"])}/sector_id',
                mapping=deepcopy(sector_mapping), status='CONFIRMED_COMPONENT_REUSED')
        row['calculation_accounting_template'] = calc_template
        row['calculation_sector_id'] = calc_sector
        row['calculation_classification_status'] = (temporary['status'] if temporary['status'] != 'NOT_REQUIRED'
                                                   else row.get('classification_status'))
        row['temporary_classification'] = temporary
        row['owner_input_policy'] = POLICY
        item.update(calculation_accounting_template=calc_template, calculation_sector_id=calc_sector,
                    temporary_status=temporary['status'], official_profile=entry[0].get('profile') if entry else None)
        audit.append(item)
    out['owner_policy'] = dict(version=POLICY, original_input_hash=digest(snapshot),
        original_input_cutoff=snapshot['input_cutoff'], reviewed_at=reviewed_at,
        historical_system_pit_complete=False, original_common_snapshot_sha256=original_snapshot_sha256)
    out['source_anchors'] = [*deepcopy(snapshot.get('source_anchors', [])),
        dict(policy=POLICY, original_input_hash=digest(snapshot),
             original_common_snapshot_sha256=original_snapshot_sha256,
             financial_source_hashes=[s['sha256'] for s in sources])]
    return out, audit


def apply_reviewed_share_metrics(snapshot, review_file, *, review_sha256,
                                 reviewed_at, input_cutoff):
    """Adopt only the individually reviewed metric of the same retained record.

    `review_file` is the share reviewer's pinned offline output. No single
    successful metric grants permission to another, to a price join, or to an
    unreviewed acquisition of the same issuer.
    """
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('OWNER_SHARE_REVIEW_TIME')
    if not re.fullmatch('[0-9a-f]{64}', review_sha256):
        raise ValueError('OWNER_SHARE_REVIEW_HASH')
    candidates = {}
    for key, review in review_file['source_contexts'].items():
        record = review['source_record']; raw_sha = review['source_sha256']
        if (record.get('source_sha256', {}).get('companyfacts') != raw_sha or
            timestamp(record['acquired_at']) > timestamp(reviewed_at)):
            raise ValueError('OWNER_SHARE_SOURCE_CONTEXT')
        record_hash = digest(record)
        if record_hash in candidates:raise ValueError('OWNER_SHARE_DUPLICATE_CONTEXT')
        candidates[record_hash] = (key, review)
    out = deepcopy(snapshot); out['input_cutoff'] = input_cutoff; audit = []
    cats = catalog()
    for row in out['rows']:
        context = row.get('owner_source_context') or {}
        found = candidates.get(context.get('record_hash'))
        if not found:
            if row.get('calculation_accounting_template') == 'GENERAL':
                audit.extend(dict(company_id=row['company_id'], issuer_id=row['issuer_id'], metric=m,
                    basis_status='UNKNOWN', adopted=False, reason='REVIEW_SOURCE_CONTEXT_NOT_LINKED')
                    for m in sorted(SHARE_METRICS))
            continue
        key, review = found; record = review['source_record']
        if (record['cik'] != row.get('issuer_id') or
            record['acquired_at'] != context.get('acquired_at') or
            record.get('fiscal_year_end') != context.get('fiscal_year_end') or
            review['source_sha256'] != context.get('companyfacts_sha256')):
            raise ValueError('OWNER_SHARE_ROW_CONTEXT')
        token = key.replace('~','~0').replace('/','~1')
        if row.get('calculation_accounting_template') != 'GENERAL':
            continue  # FINANCIAL remains reference only, even with share proof.
        for metric in sorted(SHARE_METRICS):
            claim = review.get('metrics', {}).get(metric) or {}
            status, value = claim.get('basis_status'), claim.get('value')
            item = dict(company_id=row['company_id'], issuer_id=row['issuer_id'], metric=metric,
                        basis_status=status or 'UNKNOWN', adopted=False, reason=claim.get('reason'))
            if status in ('VERIFIED','ADJUSTED') and type(value) in (int,float) and math.isfinite(value):
                prior = deepcopy(row.get('metric_evidence', {}).get(metric))
                row['metrics'][metric] = value
                row['metric_evidence'][metric] = dict(status='VERIFIED',variant=cats[metric]['variant'],
                    historical_share_basis='VERIFIED', historical_share_review_status=status,
                    available_at=reviewed_at, reviewed_at=reviewed_at,
                    retrieved_at=record['acquired_at'], source_formula_version=record['calc_version'],
                    period_end=record.get('fiscal_year_end'), currency=record.get('currency'),
                    source_refs=[f'sha256:{review_sha256}#/source_contexts/{token}/metrics/{metric}'],
                    companyfacts_sha256=review['source_sha256'],
                    reviewed_source_record_hash=context['record_hash'], original_metric_evidence=prior)
                item['adopted'] = True
            audit.append(item)
    out['owner_share_review'] = dict(review_sha256=review_sha256, reviewed_at=reviewed_at,
        original_input_hash=digest(snapshot), original_input_cutoff=snapshot['input_cutoff'],
        historical_system_pit_complete=False, per_metric_adoption=True)
    out['source_anchors'] = [*deepcopy(snapshot.get('source_anchors', [])),
        dict(policy='owner-555-historical-share-review/2026-11-14.1', review_sha256=review_sha256)]
    return out, audit


def apply_reviewed_roa_fallback(snapshot, review_file, *, review_sha256,
                                reviewed_at, input_cutoff):
    """Connect an existing GENERAL ROA-improvement observation when both paths
    lacked input. It never replaces a valid primary or an existing ROA value.
    """
    from .qgv_555 import _usable, calculation_row, configuration
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('OWNER_ROA_REVIEW_TIME')
    if not re.fullmatch('[0-9a-f]{64}', review_sha256):raise ValueError('OWNER_ROA_REVIEW_HASH')
    metric='sector::roa_improvement_3y';out=deepcopy(snapshot);out['input_cutoff']=input_cutoff;audit=[]
    for row in out['rows']:
        if row.get('calculation_accounting_template')!='GENERAL':continue
        view=calculation_row(configuration('U1-555',version='0.2.0'),row)
        if _usable(view,'incremental_roic_3y',snapshot)[0] is not None:continue
        old=row.get('metrics',{}).get(metric)
        if type(old) in (int,float) and math.isfinite(old):continue
        context=row.get('owner_source_context') or {};key=context.get('record_hash')
        review=review_file['cache'].get(key)
        item=dict(company_id=row['company_id'],issuer_id=row['issuer_id'],adopted=False)
        if not review:
            item['reason']='REVIEW_SOURCE_CONTEXT_NOT_LINKED';audit.append(item);continue
        record=review['record'];obs=review['observation'];value=obs.get('value')
        if (digest(record)!=key or record['cik']!=row['issuer_id'] or
            review['source_sha256']!=context.get('companyfacts_sha256') or
            record['acquired_at']!=context.get('acquired_at') or
            record.get('fiscal_year_end')!=context.get('fiscal_year_end')):
            raise ValueError('OWNER_ROA_SOURCE_CONTEXT')
        item['observation_status']=obs.get('status')
        if (obs.get('status') in ('VALID','VALID_NEGATIVE','VALID_ZERO') and
            type(value) in (int,float) and math.isfinite(value)):
            if (obs.get('issuer_id')!=row['issuer_id'] or obs.get('currency')!=record.get('currency') or
                obs.get('variant_id')!='roa_improvement_3y' or obs.get('unit')!='decimal' or
                not obs.get('provenance') or timestamp(obs['source_available_at'])>timestamp(reviewed_at)):
                raise ValueError('OWNER_ROA_OBSERVATION_CONTEXT')
            row['metrics'][metric]=value
            row['metric_evidence'][metric]=dict(status='VERIFIED',variant=catalog()[metric]['variant'],
                available_at=reviewed_at,reviewed_at=reviewed_at,retrieved_at=record['acquired_at'],
                source_refs=[f'sha256:{review_sha256}#/cache/{key}/observation',*obs['provenance']],
                period=deepcopy(obs.get('fiscal_period')),currency=obs['currency'],
                original_observation=deepcopy(obs),reviewed_source_record_hash=key,
                source_formula_version='sector_qgv.calculate_factor/1')
            item['adopted']=True
        else:item['reason']='HELD_COMPONENTS_NOT_VALID_FOR_EXISTING_ROA_VARIANT'
        audit.append(item)
    out['owner_roa_review']=dict(review_sha256=review_sha256,reviewed_at=reviewed_at,
        original_input_hash=digest(snapshot),original_input_cutoff=snapshot['input_cutoff'],
        historical_system_pit_complete=False,existing_kernel_only=True)
    out['source_anchors']=[*deepcopy(snapshot.get('source_anchors',[])),
        dict(policy='owner-555-existing-roa-fallback-inputs/2026-11-14.1',review_sha256=review_sha256)]
    return out,audit


TWO_STAGE_SHARE_REVIEW = 'held-555-share-eligibility/2'
TWO_STAGE_SHARE_FORMULAS = {
    'eps_cagr_3y': 'REPORTED_DILUTED_EPS_CAGR_3Y',
    'fcf_per_share_cagr_3y': 'FCF_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y',
    'dilution_3y': 'WEIGHTED_DILUTED_SHARES_CAGR_3Y',
}


def apply_two_stage_share_review(snapshot, review_file, *, review_sha256,
                                 reviewed_at, input_cutoff):
    """Quarantine earlier share proofs, then adopt only full-period eligibility.

    The caller hash-checks the serialized review before supplying this object.
    Cross-filing consistency and integer-ratio candidates are diagnostic stages,
    not permission to use a metric. Existing numerical observations remain in
    the copied input for audit, but their proof is explicitly unadopted until a
    source-bound, individually eligible metric replaces it. No financial recipe,
    price join, share-count definition or adjustment is inferred here.
    """
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('TWO_STAGE_SHARE_REVIEW_TIME')
    if not re.fullmatch('[0-9a-f]{64}', review_sha256):
        raise ValueError('TWO_STAGE_SHARE_REVIEW_HASH')
    candidates = {}
    for key, review in review_file.get('source_contexts', {}).items():
        record = review['source_record']; raw_sha = review['source_sha256']
        if (review.get('adapter_version') != TWO_STAGE_SHARE_REVIEW or
            record.get('calc_version') != CALC or
            record.get('source_sha256', {}).get('companyfacts') != raw_sha or
            not re.fullmatch('[0-9a-f]{64}', raw_sha) or
            timestamp(record['acquired_at']) > timestamp(reviewed_at)):
            raise ValueError('TWO_STAGE_SHARE_SOURCE_CONTEXT')
        source_cutoff=review.get('source_input_cutoff')
        review_cutoff=review.get('review_input_cutoff')
        if (not isinstance(source_cutoff,str) or not isinstance(review_cutoff,str) or
            timestamp(source_cutoff)!=timestamp(record['acquired_at']) or
            not timestamp(source_cutoff)<=timestamp(review_cutoff)<=timestamp(reviewed_at)):
            raise ValueError('TWO_STAGE_SHARE_REVIEW_CLOCK')
        key_hash = digest(record)
        if key_hash in candidates:raise ValueError('TWO_STAGE_SHARE_DUPLICATE_CONTEXT')
        candidates[key_hash] = (key, review)
    out = deepcopy(snapshot); out['input_cutoff'] = input_cutoff
    cats = catalog(); audit = []
    finite = lambda value: type(value) in (int, float) and math.isfinite(value)
    for row in out['rows']:
        context = row.get('owner_source_context') or {}
        found = candidates.get(context.get('record_hash'))
        if found:
            key, review = found; record = review['source_record']
            if (record['cik'] != row.get('issuer_id') or
                record['acquired_at'] != context.get('acquired_at') or
                record.get('fiscal_year_end') != context.get('fiscal_year_end') or
                review['source_sha256'] != context.get('companyfacts_sha256')):
                raise ValueError('TWO_STAGE_SHARE_ROW_CONTEXT')
            token = key.replace('~', '~0').replace('/', '~1')
        else:
            key = token = None; review = {}; record = {}
        for metric in sorted(SHARE_METRICS):
            prior = deepcopy(row.get('metric_evidence', {}).get(metric))
            retained_value = row.get('metrics', {}).get(metric)
            claim = review.get('metrics', {}).get(metric) or {}
            stage1 = deepcopy(claim.get('stage1') or dict(status='UNKNOWN'))
            stage2 = deepcopy(claim.get('stage2') or dict(status='UNCONFIRMED_PERIOD_BASIS'))
            action = deepcopy(claim.get('corporate_action') or dict(status='UNKNOWN', adjustment_applied=False))
            raw = claim.get('raw_value')
            # A retained value is not discarded or silently replaced with zero.
            # It remains a quarantined diagnostic, independent of source review.
            raw_connected = finite(raw) or finite(retained_value)
            summary = dict(stage1_status=stage1.get('status'),stage2_status=stage2.get('status'),
                corporate_action_status=action.get('status'),
                adjustment_applied=action.get('adjustment_applied') is True,
                raw_connected=raw_connected,raw_source_context_linked=found is not None,
                retained_numeric=finite(retained_value),reviewed_raw_numeric=finite(raw),
                full_period_evidence_ref_count=len(stage2.get('evidence_refs') or []),
                final_eligibility='QUARANTINED')
            refs = [f'sha256:{review_sha256}#/source_contexts/{token}/metrics/{metric}'] if found else []
            proof = dict(status='QUARANTINED',variant=cats[metric]['variant'],
                historical_share_basis='UNKNOWN',share_eligibility_stage='UNCONFIRMED_PERIOD_BASIS',
                two_stage_review_version=TWO_STAGE_SHARE_REVIEW,
                available_at=reviewed_at,reviewed_at=reviewed_at,
                retrieved_at=record.get('acquired_at', (prior or {}).get('retrieved_at')),
                source_refs=refs,validation_stages=summary,
                denominator_definition=claim.get('denominator_definition'),
                formula_variant=claim.get('formula_variant'),
                original_metric_evidence=prior,
                quarantine_reason='PRIOR_CONSISTENCY_OR_RATIO_IS_NOT_FULL_PERIOD_ELIGIBILITY')
            row.setdefault('metric_evidence', {})[metric] = proof
            item = dict(company_id=row['company_id'],issuer_id=row.get('issuer_id'),metric=metric,
                raw_connected=raw_connected,retained_numeric=finite(retained_value),
                reviewed_raw_numeric=finite(raw),source_context_linked=found is not None,
                retained_raw_value=retained_value if finite(retained_value) else None,
                reviewed_raw_value=raw if finite(raw) else None,
                stage1=stage1,stage2=stage2,corporate_action=action,
                denominator_definition=claim.get('denominator_definition'),
                formula_variant=claim.get('formula_variant'),
                calculation_applicable=row.get('calculation_accounting_template')=='GENERAL',
                prior_adopted=(prior or {}).get('historical_share_basis')=='VERIFIED',
                adopted=False,reason=claim.get('reason') or stage2.get('status'))
            if stage2.get('status') == 'FINAL_ELIGIBLE':
                if (stage2.get('all_used_years_linked') is not True or
                    stage2.get('documented_common_basis') is not True or
                    not isinstance(stage2.get('evidence_refs'), list) or
                    not stage2['evidence_refs'] or
                    not all(isinstance(x, str) and x for x in stage2['evidence_refs']) or
                    claim.get('basis_status') != 'VERIFIED'):
                    raise ValueError('TWO_STAGE_FINAL_EVIDENCE_INCOMPLETE')
                if (claim.get('denominator_definition') != 'WEIGHTED_AVERAGE_DILUTED_SHARES' or
                    claim.get('formula_variant') != TWO_STAGE_SHARE_FORMULAS[metric]):
                    raise ValueError('TWO_STAGE_METRIC_DEFINITION_MISMATCH')
                if action.get('adjustment_applied') is True and (
                    action.get('status') != 'CONFIRMED' or not action.get('evidence_refs')):
                    raise ValueError('TWO_STAGE_UNCONFIRMED_ADJUSTMENT')
                value = claim.get('value')
                if not finite(value):
                    item['reason'] = 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE'
                elif row.get('calculation_accounting_template') != 'GENERAL':
                    item['reason'] = 'FINANCIAL_REFERENCE_ONLY'
                else:
                    row.setdefault('metrics', {})[metric] = value
                    proof.update(status='VERIFIED',historical_share_basis='VERIFIED',
                        share_eligibility_stage='FINAL_ELIGIBLE',
                        source_formula_version=record['calc_version'],
                        period_end=record.get('fiscal_year_end'),currency=record.get('currency'),
                        companyfacts_sha256=review['source_sha256'],
                        reviewed_source_record_hash=context['record_hash'])
                    summary['final_eligibility']='FINAL_ELIGIBLE'
                    item.update(adopted=True,reason=None)
            elif not found:
                item['reason'] = 'REVIEW_SOURCE_CONTEXT_NOT_LINKED'
            audit.append(item)
    out['owner_two_stage_share_review'] = dict(adapter_version=TWO_STAGE_SHARE_REVIEW,
        review_sha256=review_sha256,reviewed_at=reviewed_at,
        original_input_hash=digest(snapshot),original_input_cutoff=snapshot['input_cutoff'],
        historical_system_pit_complete=False,per_metric_adoption=True,
        prior_proofs_quarantined=True,
        numeric_consistency_does_not_prove_absence_of_corporate_actions=True)
    out['source_anchors'] = [*deepcopy(snapshot.get('source_anchors', [])),
        dict(policy=TWO_STAGE_SHARE_REVIEW,review_sha256=review_sha256,
             original_input_hash=digest(snapshot))]
    return out, audit
