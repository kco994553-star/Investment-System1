"""Source-bound, additive FINANCIAL raw bridge for the temporary 555 research.

No network access, official score copying, general-metric rewriting or peer
inference. Historical BVPS receives its own official share/equity review.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from ..qgv import v2_factors as vf
from .sector_qgv import digest, timestamp
from .qgv_555_official_share import (
    VERSION as SHARE_VERSION, FORMULAS, DENOMINATOR, BASES, _TracedCompany,
    _route, _selected_source, _context_qualifications, _finite,
)
from .qgv_555_share_review import _collect, _filing
from .qgv_555_financial_temporary import (
    CALC_VERSION, HISTORICAL_SHARE_METRICS, STATUS, financial_catalog,
    validate_official_financial_record,
)

POLICY = 'official-financial-role-bridge/1'
BOOK_FORMULA = 'OFFICIAL_EQUITY_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y'
SHARE_FORMULAS = dict(FORMULAS, book_value_per_share_cagr_3y=BOOK_FORMULA)
PEER_TEMPLATES = frozenset(('BANK', 'INSURANCE', 'BROKER', 'ASSET_MANAGER', 'MORTGAGE_REIT'))


def _equity_endpoint(payload, facts, company, k, cutoff):
    """Trace the unchanged official instant picker and retain latest conflicts."""
    target = company.end(k)
    value = company.i('equity', k)
    selected = None
    conflicts = []
    for n, (table, sources) in enumerate(zip(facts.items['equity'], facts.sources['equity'])):
        concept = facts.concepts['equity'][n]
        rows = payload['facts'][facts.taxonomy].get(concept, {}).get('units', {}).get(facts._unit('equity'), [])
        by_end = {}
        for index, row in enumerate(rows):
            end, filed = vf._day(row.get('end')), vf._day(row.get('filed'))
            if (end is None or filed is None or filed > cutoff or row.get('form') not in vf.INSTANT_FORMS
                    or not _finite(row.get('val')) or abs((end-target).days) > vf.YEAR_TOLERANCE_DAYS):
                continue
            by_end.setdefault(end, []).append((filed, row['val'], index))
        for end, candidates in by_end.items():
            latest = max(r[0] for r in candidates)
            if len({r[1] for r in candidates if r[0] == latest}) > 1:
                conflicts.append('LATEST_FILING_CONFLICT:equity:' + concept)
        hits = [(abs((end-target).days), end, v, (start, end))
            for (start, end), v in table.items() if abs((end-target).days) <= vf.YEAR_TOLERANCE_DAYS]
        if selected is None and hits:
            _, end, picked, key = sorted(hits)[0]
            filing = sources.get(key)
            selected = dict(item='equity', year_offset=k, value=picked, period_end=str(end),
                concept=concept, filing=_filing(filing) if filing else None,
                attribution='OFFICIAL_EQUITY_NOT_CONFIRMED_COMMON')
    if selected is not None and selected['value'] != value:
        raise ValueError('FINANCIAL_BOOK_EQUITY_PICKER_MISMATCH')
    return selected, conflicts


def review_official_book_value_history(payload, record, source_ref):
    """Independently review BVPS endpoints using official arithmetic and routes."""
    validate_official_financial_record(record)
    if str(payload.get('cik')).zfill(10) != record.get('cik'):
        raise ValueError('FINANCIAL_BOOK_SOURCE_ISSUER')
    clock = datetime.fromisoformat(record['acquired_at'].replace('Z', '+00:00'))
    if clock.tzinfo is None:
        raise ValueError('FINANCIAL_BOOK_SOURCE_CLOCK')
    cutoff = clock.astimezone(timezone.utc).date()
    taxonomy, currency = vf._taxonomy_and_currency(payload, cutoff)
    fy = vf._day(record.get('fiscal_year_end'))
    if not taxonomy or not currency or not fy:
        raise ValueError('FINANCIAL_BOOK_PERIOD_CONTEXT')
    if record.get('currency') != currency:
        raise ValueError('FINANCIAL_BOOK_SOURCE_CURRENCY')
    facts = vf._Facts(payload, taxonomy, currency, cutoff)
    company = _TracedCompany(facts, fy, sic=record.get('sic'), profile='FINANCIAL')
    computed = vf._metrics_financial(company)['book_value_per_share_cagr_3y']
    selected, locations, invalid, conflicts = _collect(payload, facts, 'diluted_shares', cutoff)
    periods, routes, scales, problems, missing = [], [], [], [], []
    for k in (0, 3):
        equity, equity_conflicts = _equity_endpoint(payload, facts, company, k, cutoff)
        problems.extend(equity_conflicts)
        if equity is None:
            missing.append('EQUITY_ENDPOINT_MISSING')
        else:
            periods.append(equity)
            if equity['value'] <= 0:
                missing.append('EQUITY_ENDPOINT_NOT_POSITIVE')
        info, hit, filing = _selected_source(facts, company, 'diluted_shares', k)
        periods.append(info)
        if hit is None:
            missing.append('DILUTED_SHARES_ANNUAL_ENDPOINT_MISSING')
            continue
        if (hit[1], hit[2]) in conflicts or (filing, (hit[1], hit[2])) in invalid:
            problems.append('LATEST_FILING_CONFLICT:diluted_shares')
        routes.append(dict(item='diluted_shares', year_offset=k, **_route(company, filing)))
        check = vf._shares_scale(hit[0], facts.cover_count(filing))
        scales.append(dict(year_offset=k, **check))
        if hit[0] <= 0:
            problems.append('DILUTED_SHARE_COUNT_NOT_POSITIVE')
        if check['status'] == vf.SHARES_SCALE_UNCONFIRMED:
            missing.append(vf.SHARES_SCALE_UNCONFIRMED)
        if company.shares(k) is None and routes[-1]['factor'] is not None:
            problems.append('OFFICIAL_SHARE_JUMP_LIMIT_REJECTED')
        if equity is not None and equity['period_end'] != str(hit[2]):
            missing.append('EQUITY_SHARES_ENDPOINT_PERIOD_MISMATCH')
        # Explicitly exercise the official per-share denominator, separately
        # from EPS and dilution claims from the old review.
        if equity is not None and company.per_share(company.i('equity', k), k) is None:
            missing.append('BOOK_VALUE_PER_SHARE_ENDPOINT_UNAVAILABLE')
    if any(abs((period[1]-company.end(k)).days) <= vf.YEAR_TOLERANCE_DAYS
            for period in conflicts for k in (0, 3)):
        problems.append('LATEST_FILING_CONFLICT:diluted_shares')
    route_bases = {r['adoption_basis'] for r in routes}
    assumptions = sorted({a for r in routes for a in r['allowed_assumptions']})
    if problems or 'EXPLICIT_CONFLICT_EXCLUDED' in route_bases:
        basis = 'EXPLICIT_CONFLICT_EXCLUDED'
    elif missing or len(routes) != 2 or 'ADDITIONAL_VERIFICATION_REQUIRED' in route_bases:
        basis = 'ADDITIONAL_VERIFICATION_REQUIRED'
    elif assumptions:
        basis = 'OFFICIAL_ASSUMPTION_INHERITED'
    elif 'FILING_SPLIT_ADJUSTED' in route_bases:
        basis = 'FILING_SPLIT_ADJUSTED'
    else:
        basis = 'EVIDENCE_LINKED'
    accepted = basis in BASES[:3] and _finite(computed)
    value = vf._round(computed) if accepted else None
    if accepted and value != record.get('metrics', {}).get('book_value_per_share_cagr_3y'):
        raise ValueError('FINANCIAL_BOOK_SOURCE_VALUE_MISMATCH')
    return dict(value=value, unrounded_value=computed if _finite(computed) else None,
        adoption_basis=basis, reason=None if accepted else
            sorted(set(problems + missing))[0] if problems or missing else 'FORMULA_DOMAIN_OR_BASIS_UNAVAILABLE',
        allowed_assumptions=assumptions, requires_assumption=bool(assumptions),
        evidence_only_eligible=accepted and not assumptions and basis in BASES[:2],
        reusable=accepted, strict_verified=False, additional_verification_required=True,
        additional_verification=_context_qualifications(payload) + ['OFFICIAL_EQUITY_NOT_CONFIRMED_COMMON'],
        blocking_reasons=sorted(set(problems + missing)), formula_variant=BOOK_FORMULA,
        denominator_definition=DENOMINATOR, accounting_scope=['FINANCIAL'],
        formula_source='EXISTING_OFFICIAL_V2_FISCAL_KERNEL', periods=periods,
        endpoint_factors=routes, cover_scale_diagnostics=scales, source_refs=[source_ref],
        common_attribution_confirmed=False, valuation_price_identity_verified=False,
        actual_share_issuance_interpretation=False)


def _anchor_key(context):
    return digest(context['source_record'])


def _claim_valid(claim, metric, raw):
    if not isinstance(claim, dict):
        return False
    assumptions = claim.get('allowed_assumptions')
    basis = claim.get('adoption_basis')
    requires = claim.get('requires_assumption')
    evidence = claim.get('evidence_only_eligible')
    if (type(claim.get('reusable')) is not bool or type(requires) is not bool or type(evidence) is not bool or not isinstance(assumptions, list)
            or not all(isinstance(a, str) and a for a in assumptions) or bool(assumptions) != requires
            or evidence and (requires or basis not in BASES[:2])
            or basis == 'OFFICIAL_ASSUMPTION_INHERITED' and not requires):
        raise ValueError('FINANCIAL_SHARE_ASSUMPTION_METADATA')
    if (claim.get('formula_variant') != SHARE_FORMULAS[metric] or
            claim.get('denominator_definition') != DENOMINATOR or claim.get('strict_verified') is not False):
        raise ValueError('FINANCIAL_SHARE_FORMULA_METADATA')
    reusable = claim.get('reusable') is True and basis in BASES[:3] and _finite(claim.get('value'))
    if reusable and claim['value'] != raw:
        raise ValueError('FINANCIAL_SHARE_SOURCE_VALUE_MISMATCH')
    return reusable


def apply_temporary_financial_inputs(snapshot, source_review_file, source_review_sha256,
                                     reviewed_at, input_cutoff, *, book_value_reviews=None):
    """Add namespaced raw evidence while preserving the complete 0.4 input."""
    blob = Path(source_review_file).read_bytes()
    if not re.fullmatch('[0-9a-f]{64}', source_review_sha256) or hashlib.sha256(blob).hexdigest() != source_review_sha256:
        raise ValueError('FINANCIAL_REVIEW_FILE_HASH')
    review = json.loads(blob)
    if not timestamp(snapshot['input_cutoff']) <= timestamp(reviewed_at) <= timestamp(input_cutoff):
        raise ValueError('FINANCIAL_REVIEW_TIME')
    if timestamp(review['reviewed_at']) > timestamp(reviewed_at):
        raise ValueError('FINANCIAL_SOURCE_REVIEW_TIME')
    contexts = {}
    for key, context in review['source_contexts'].items():
        record = context['source_record']
        if record.get('profile') != 'FINANCIAL':
            continue
        validate_official_financial_record(record)
        anchor = _anchor_key(context)
        if anchor in contexts:
            raise ValueError('FINANCIAL_AMBIGUOUS_SOURCE_CONTEXT')
        contexts[anchor] = key, context
    cats = financial_catalog()
    out = deepcopy(snapshot)
    out['input_cutoff'] = input_cutoff
    audit = []
    for row in out['rows']:
        owner = row.get('owner_source_context') or {}
        if owner.get('profile') != 'FINANCIAL':
            continue
        anchor = owner.get('record_hash')
        entry = contexts.get(anchor)
        if entry is None:
            raise ValueError('FINANCIAL_SOURCE_CONTEXT_MISSING')
        key, context = entry
        record = context['source_record']
        validate_official_financial_record(record)
        if digest(record) != owner.get('record_hash'):
            raise ValueError('FINANCIAL_SOURCE_RECORD_HASH')
        body_hash = record.get('source_sha256', {}).get('companyfacts')
        if (not isinstance(body_hash, str) or not re.fullmatch('[0-9a-f]{64}', body_hash)
                or owner.get('companyfacts_sha256') != body_hash or context.get('source_sha256') != body_hash):
            raise ValueError('FINANCIAL_SOURCE_BODY_HASH')
        for field in ('currency', 'fiscal_year_end', 'acquired_at', 'calc_version', 'sic', 'industry_group'):
            if owner.get(field) != record.get(field):
                raise ValueError('FINANCIAL_SOURCE_CONTEXT_FIELD:' + field)
        if (context.get('issuer_id') != record['cik'] or row.get('issuer_id') != record['cik'] or context.get('currency') != record.get('currency')
                or context.get('fiscal_year_end') != record.get('fiscal_year_end')
                or context.get('acquired_at') != record.get('acquired_at')
                or context.get('official_calc_version') != CALC_VERSION):
            raise ValueError('FINANCIAL_REVIEW_CONTEXT_FIELD')
        if timestamp(record['acquired_at']) > timestamp(snapshot['input_cutoff']):
            raise ValueError('FINANCIAL_SOURCE_NOT_AVAILABLE')
        if timestamp(record['acquired_at']) > timestamp(review['reviewed_at']):
            raise ValueError('FINANCIAL_SOURCE_REVIEW_BEFORE_ACQUISITION')
        source_anchor = f"sha256:{owner['source_sha256']}#{owner['source_pointer']}"
        if (source_anchor not in (row.get('financial_reference') or {}).get('source_refs', []) or
                not any(re.search(r'(?:sha256:|sha256=)' + body_hash + r'(?:$|[#/])', r)
                    for r in context.get('source_refs', []) if isinstance(r, str))):
            raise ValueError('FINANCIAL_SOURCE_POINTER')
        pointer = '/source_contexts/' + key.replace('~', '~0').replace('/', '~1')
        accepted = []
        for metric_key, spec in cats.items():
            metric = spec['source_metric']
            raw = record.get('metrics', {}).get(metric)
            claim = None
            if metric in HISTORICAL_SHARE_METRICS:
                if metric == 'book_value_per_share_cagr_3y':
                    wrapper = (book_value_reviews or {}).get(key)
                    if wrapper is not None:
                        if wrapper.get('source_record_hash') != digest(record) or wrapper.get('source_body_sha256') != body_hash:
                            raise ValueError('FINANCIAL_BOOK_REVIEW_BINDING')
                        claim = wrapper.get('claim')
                else:
                    claim = context.get('metrics', {}).get(metric)
                reusable = _claim_valid(claim, metric, raw)
                value = claim['value'] if reusable else None
            else:
                reusable = _finite(raw)
                value = raw if reusable else None
            proof = dict(status='TEMPORARY_OFFICIAL_FINANCIAL_RAW', variant=spec['variant'],
                financial_temporary_policy=POLICY, source_formula_version=CALC_VERSION,
                source_metric=metric, source_record_hash=digest(record), source_body_sha256=body_hash,
                source_context_key=key, raw_reusable=reusable, diagnostic_raw=raw,
                source_refs=[source_anchor + '/metrics/' + metric,
                    f'sha256:{source_review_sha256}#{pointer}'],
                available_at=reviewed_at, source_available_at=record['acquired_at'],
                retrieved_at=record['acquired_at'], reviewed_at=reviewed_at,
                source_review_created_at=review['reviewed_at'], review_file_received_at=None,
                period_end=record.get('fiscal_year_end'), currency=record.get('currency'),
                financial_calculation_profile='FINANCIAL', common_attribution_confirmed=False)
            if metric in HISTORICAL_SHARE_METRICS:
                for field in ('value', 'unrounded_value', 'adoption_basis', 'reason', 'basis_reason',
                        'formula_status', 'allowed_assumptions', 'requires_assumption', 'evidence_only_eligible',
                        'reusable', 'strict_verified', 'additional_verification_required', 'additional_verification',
                        'blocking_reasons', 'formula_source', 'periods', 'endpoint_factors', 'cover_scale_diagnostics',
                        'cover_scale_applies_to', 'actual_share_issuance_interpretation', 'valuation_price_identity_verified'):
                    if field in (claim or {}):
                        proof[field] = deepcopy(claim[field])
                proof.update(official_share_reuse_version=SHARE_VERSION,
                    historical_share_basis='OFFICIAL_PATH_REUSED' if reusable else 'UNCONFIRMED',
                    raw_reusable=reusable, diagnostic_raw=raw,
                    formula_variant=SHARE_FORMULAS[metric], denominator_definition=DENOMINATOR)
                if metric == 'book_value_per_share_cagr_3y' and wrapper is not None:
                    proof.update(metric_specific_review_hash=digest(wrapper),
                        metric_specific_review_type='INDEPENDENT_OFFICIAL_BOOK_VALUE_SHARE_EQUITY_REVIEW')
                if claim is None:
                    proof.update(adoption_basis='ADDITIONAL_VERIFICATION_REQUIRED',
                        reason='METRIC_SPECIFIC_BOOK_VALUE_REVIEW_MISSING', strict_verified=False,
                        allowed_assumptions=[], requires_assumption=False, evidence_only_eligible=False)
            # Idempotency never overwrites a conflicting prior financial bridge.
            if metric_key in row.get('metrics', {}) and row['metrics'][metric_key] != value:
                raise ValueError('FINANCIAL_EXISTING_RAW_CONFLICT')
            row.setdefault('metrics', {})[metric_key] = value
            row.setdefault('metric_evidence', {})[metric_key] = proof
            if reusable:
                accepted.append(metric_key)
        row.update(financial_calculation_profile='FINANCIAL',
            financial_peer_template=row.get('accounting_template') if row.get('accounting_template') in PEER_TEMPLATES else None,
            financial_temporary_policy=POLICY,
            financial_temporary_status=STATUS,
            financial_temporary_source_refs=[source_anchor, f'sha256:{source_review_sha256}#{pointer}'])
        audit.append(dict(company_id=row['company_id'], issuer_id=row.get('issuer_id'),
            source_context_key=key, source_record_hash=digest(record), source_body_sha256=body_hash,
            financial_calculation_profile='FINANCIAL', financial_peer_template=row['financial_peer_template'],
            accepted_metrics=accepted, missing_metrics=sorted(set(cats)-set(accepted)),
            temporary_status=STATUS, official_scores_copied=False))
    out['financial_temporary_inputs'] = dict(policy=POLICY, source_review_sha256=source_review_sha256,
        reviewed_at=reviewed_at, input_cutoff=input_cutoff, original_input_hash=digest(snapshot),
        original_input_cutoff=snapshot['input_cutoff'], historical_system_pit_complete=False)
    return out, dict(policy=POLICY, financial_rows=len(audit), rows=audit,
        official_scores_copied=False, general_metrics_modified=False)
