"""Connect a pinned official-kernel raw review to a new 555 research input.

The caller verifies the review's original file bytes. This bridge checks the
retained source-record identity and clocks, never treats reuse as strict proof,
and changes no classification, price, gate, non-share metric or population.
"""
from copy import deepcopy
import math
import re
from .sector_qgv import digest, timestamp
from .qgv_555 import catalog, SHARE_METRICS, SHARE_DENOMINATOR, official_reuse_assumptions_valid
from .qgv_555_official_share import VERSION,FORMULAS

ALLOWED={'EVIDENCE_LINKED','FILING_SPLIT_ADJUSTED','OFFICIAL_ASSUMPTION_INHERITED'}
REJECTED={'ADDITIONAL_VERIFICATION_REQUIRED','EXPLICIT_CONFLICT_EXCLUDED'}


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def apply_official_share_reuse(snapshot, review_file, *, review_sha256, reviewed_at, input_cutoff):
    if not re.fullmatch('[0-9a-f]{64}',review_sha256):raise ValueError('OFFICIAL_REUSE_FILE_HASH')
    if review_file.get('adapter_version')!=VERSION:raise ValueError('OFFICIAL_REUSE_VERSION')
    review_time=timestamp(reviewed_at)
    if not timestamp(snapshot['input_cutoff'])<=review_time<=timestamp(input_cutoff):
        raise ValueError('OFFICIAL_REUSE_INPUT_CLOCK')
    if timestamp(review_file['reviewed_at'])>review_time:raise ValueError('OFFICIAL_REUSE_REVIEW_CLOCK')
    sources={}
    for key,review in review_file['source_contexts'].items():
        record=review['source_record'];record_hash=digest(record)
        if record_hash in sources:raise ValueError('OFFICIAL_REUSE_DUPLICATE_SOURCE')
        if (review.get('adapter_version')!=VERSION or review.get('issuer_id')!=record.get('cik') or
            record.get('calc_version')!='qgv2-calc/2026-10-23.1' or
            record.get('source_sha256',{}).get('companyfacts')!=review.get('source_sha256')):
            raise ValueError('OFFICIAL_REUSE_SOURCE_IDENTITY')
        acquired=timestamp(record['acquired_at'])
        if (timestamp(review['source_input_cutoff'])!=acquired or
            not acquired<=timestamp(review['review_input_cutoff'])<=review_time):
            raise ValueError('OFFICIAL_REUSE_SOURCE_CLOCK')
        sources[record_hash]=(key,review)
    input_hash=digest(snapshot)
    out=deepcopy(snapshot);out['input_cutoff']=input_cutoff;cats=catalog();audit=[]
    for row in out['rows']:
        context=row.get('owner_source_context') or {};found=sources.get(context.get('record_hash'))
        review=found[1] if found else {};record=review.get('source_record') or {}
        if found and (row.get('issuer_id')!=record['cik'] or
            context.get('companyfacts_sha256')!=review['source_sha256'] or
            timestamp(context['acquired_at'])!=timestamp(record['acquired_at']) or
            context.get('fiscal_year_end')!=record.get('fiscal_year_end')):
            raise ValueError('OFFICIAL_REUSE_ROW_IDENTITY')
        for metric in sorted(SHARE_METRICS):
            claim=review.get('metrics',{}).get(metric) or {}
            basis=claim.get('adoption_basis','ADDITIONAL_VERIFICATION_REQUIRED')
            if basis not in ALLOWED|REJECTED:raise ValueError('OFFICIAL_REUSE_ADOPTION_BASIS')
            value=claim.get('value');prior=row.get('metric_evidence',{}).get(metric)
            prior_value=row.get('metrics',{}).get(metric)
            requires=claim.get('requires_assumption',False)
            evidence_only=claim.get('evidence_only_eligible',False)
            assumptions=claim.get('allowed_assumptions',[])
            if not official_reuse_assumptions_valid(dict(adoption_basis=basis,
                requires_assumption=requires,evidence_only_eligible=evidence_only,allowed_assumptions=assumptions)):
                raise ValueError('OFFICIAL_REUSE_ASSUMPTION_IDENTITY')
            if basis in ALLOWED and (claim.get('strict_verified') is not False or
                claim.get('denominator_definition')!=SHARE_DENOMINATOR or not claim.get('formula_source') or
                claim.get('formula_variant')!=FORMULAS[metric]):
                raise ValueError('OFFICIAL_REUSE_METRIC_DEFINITION')
            applicable=row.get('calculation_accounting_template')=='GENERAL'
            adopted=bool(found and basis in ALLOWED and finite(value) and applicable)
            refs=[f'sha256:{review_sha256}#/source_contexts/{found[0].replace("~","~0").replace("/","~1")}/metrics/{metric}'] if found else []
            proof=dict(status='RESEARCH_USABLE' if adopted else 'QUARANTINED',variant=cats[metric]['variant'],
                historical_share_basis='OFFICIAL_PATH_REUSED' if adopted else 'UNKNOWN',
                official_share_reuse_version=VERSION,adoption_basis=basis,
                strict_verified=False,requires_assumption=requires,evidence_only_eligible=evidence_only,
                allowed_assumptions=deepcopy(assumptions),denominator_definition=claim.get('denominator_definition'),
                additional_verification_required=claim.get('additional_verification_required',True),
                additional_verification=deepcopy(claim.get('additional_verification',[])),
                reason=claim.get('reason') if found else 'REVIEW_SOURCE_CONTEXT_NOT_LINKED',
                periods=deepcopy(claim.get('periods',[])),formula_source=claim.get('formula_source'),
                formula_variant=claim.get('formula_variant'),
                source_formula_version=record.get('calc_version'),available_at=reviewed_at,reviewed_at=reviewed_at,
                retrieved_at=record.get('acquired_at'),source_refs=refs,
                source_record_hash=context.get('record_hash'),source_companyfacts_sha256=review.get('source_sha256'),
                prior_metric_evidence_hash=digest(prior),
                original_input_hash=input_hash,verifies_valuation_security=False)
            row.setdefault('metric_evidence',{})[metric]=proof
            if adopted:row.setdefault('metrics',{})[metric]=value
            audit.append(dict(company_id=row['company_id'],issuer_id=row.get('issuer_id'),metric=metric,
                adoption_basis=basis,adopted=adopted,evidence_only_adoptable=adopted and evidence_only and not requires,
                requires_assumption=requires,allowed_assumptions=deepcopy(assumptions),strict_verified=False,
                prior_raw=prior_value,reviewed_value=value,raw_changed=adopted and prior_value!=value,
                newly_connected_numeric=adopted and not finite(prior_value),
                reason=('FINANCIAL_REFERENCE_ONLY' if found and not applicable else proof['reason']),source_refs=refs))
    meta=dict(version=VERSION,review_sha256=review_sha256,reviewed_at=reviewed_at,
        original_input_hash=input_hash,historical_system_pit_complete=False,
        official_scores_reused=False,independent_share_scope_filters=['ALL_OFFICIAL_REUSE','EVIDENCE_ONLY'])
    out['official_share_reuse']=meta
    out['source_anchors']=[*deepcopy(snapshot.get('source_anchors',[])),deepcopy(meta)]
    return out,audit
