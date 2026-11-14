"""Offline evidence adapter over the existing market-cap selector; never publishes."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from collections import Counter

from ..universe.sources import mcap_top_n_snapshot
from .sector_qgv import digest, timestamp


def _positive(value):
    if isinstance(value, bool):
        raise ValueError('INVALID_NUMBER')
    try:
        x = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('INVALID_NUMBER') from None
    if not x.is_finite() or x <= 0:
        raise ValueError('INVALID_NUMBER')
    return x


def _class_cap(c, day, cutoff, policy):
    if c.get('identity_status') != 'VERIFIED' or not c.get('security_id') or not c.get('identity_evidence'):
        raise ValueError('SECURITY_IDENTITY_UNVERIFIED')
    if c.get('security_kind') not in policy['included_kinds']:
        raise ValueError('SECURITY_KIND_UNRESOLVED')
    if c.get('exchange') not in policy['markets']:
        raise ValueError('LISTING_MARKET_UNVERIFIED')
    if not c.get('valid_from') or date.fromisoformat(c['valid_from']) > day or (
            c.get('valid_to') and day >= date.fromisoformat(c['valid_to'])):
        raise ValueError('SECURITY_INTERVAL')
    if not c.get('available_at') or timestamp(c['available_at']) > cutoff:
        raise ValueError('INPUT_UNAVAILABLE_AT_CUTOFF')
    if any(c.get(k) != day.isoformat() for k in ('observed_on', 'price_day', 'shares_day')):
        raise ValueError('VALUATION_DATE_MISMATCH')
    if c.get('price_security_id') != c['security_id'] or c.get('price_basis') != 'RAW_CLOSE':
        raise ValueError('PRICE_CLASS_OR_BASIS_MISMATCH')
    if c.get('corporate_action_status') != 'VERIFIED' or not c.get('corporate_action_evidence'):
        raise ValueError('ACTION_CONTINUITY_UNVERIFIED')
    if not c.get('evidence') or not c.get('economic_class_id'):
        raise ValueError('CLASS_EVIDENCE_MISSING')
    if c.get('security_kind') == 'ADR':
        if c.get('shares_basis') != 'ACTUAL_UNDERLYING_CLASS_OUTSTANDING' or not c.get('adr_evidence'):
            raise ValueError('ADR_BASIS_UNVERIFIED')
        divisor = _positive(c.get('underlying_per_receipt'))
    else:
        if c.get('shares_basis') != 'ACTUAL_CLASS_OUTSTANDING':
            raise ValueError('ACTUAL_CLASS_SHARES_REQUIRED')
        divisor = Decimal(1)
    if not c.get('currency'):
        raise ValueError('CURRENCY_MISSING')
    fx = _positive(c.get('fx_to_usd'))
    if c['currency'] == 'USD':
        if fx != 1:
            raise ValueError('USD_FX_MISMATCH')
    elif c.get('fx_day') != day.isoformat() or not c.get('fx_evidence'):
        raise ValueError('FX_EVIDENCE_MISSING')
    return _positive(c.get('price')) * _positive(c.get('shares')) * fx / divisor


def select_top500(job, *, previous=None):
    if job.get('schema_version') != 'top500-input/1':
        raise ValueError('INPUT_SCHEMA')
    day = date.fromisoformat(job['evaluation_day'])
    cutoff = timestamp(job['input_cutoff'])
    if timestamp(job['apply_at']) < cutoff:
        raise ValueError('APPLICATION_BEFORE_AVAILABILITY')
    policy = job['policy']
    if policy.get('version') != 'top500-research/0.1.0' or policy.get('status') != 'RESEARCH_PROPOSAL':
        raise ValueError('POLICY_VERSION')
    rows = job['issuers']; ids = [r['issuer_id'] for r in rows]
    duplicates = {k for k,v in Counter(ids).items() if v > 1}
    coverage = job['coverage']; expected = coverage.get('expected_issuers') or []
    reasons = []
    if (coverage.get('status') != 'COMPLETE' or not coverage.get('evidence') or not expected
            or len(expected) != len(set(expected)) or set(ids) != set(expected)):
        reasons.append('CANDIDATE_COVERAGE_UNPROVEN')
    if duplicates:
        reasons.append('DUPLICATE_ISSUER')
    prepared, caps, unresolved, excluded = [], {}, [], []
    seen_securities = Counter(c.get('security_id') for r in rows for c in r.get('classes', []))
    for r in sorted(rows, key=lambda x:x['issuer_id']):
        cid = r['issuer_id']
        if cid in duplicates:
            continue
        if r.get('eligibility') == 'EXCLUDED' and r.get('exclusion_evidence'):
            excluded.append(dict(issuer_id=cid, reason=r.get('exclusion_reason'), evidence=r['exclusion_evidence']))
            continue
        try:
            if r.get('eligibility') != 'ELIGIBLE':
                raise ValueError('ELIGIBILITY_UNRESOLVED')
            cs = r.get('classes') or []
            if not r.get('classes_complete') or not cs:
                raise ValueError('CLASS_COVERAGE_UNPROVEN')
            class_ids = [c.get('economic_class_id') for c in cs]
            if len(class_ids) != len(set(class_ids)):
                raise ValueError('DUPLICATE_ECONOMIC_CLASS_OR_ADR_UNDERLYING')
            if any(seen_securities[c.get('security_id')] != 1 for c in cs):
                raise ValueError('DUPLICATE_SECURITY')
            representative = r.get('representative_security_id')
            if representative not in {c.get('security_id') for c in cs} or not r.get('representative_evidence'):
                raise ValueError('REPRESENTATIVE_UNVERIFIED')
            cap = sum((_class_cap(c,day,cutoff,policy) for c in cs), Decimal(0))
            caps[cid] = dict(issuer_id=cid, representative_security_id=representative,
                market_cap_usd=format(cap,'f'), economic_classes=class_ids,
                selection_evidence=deepcopy(cs), representative_evidence=r['representative_evidence'])
            # The existing sorter receives one issuer point. shares=1 is an explicit
            # adapter representation of already validated class-cap aggregation, NOT
            # a fabricated source share observation.
            prepared.append(dict(company_id=cid,ticker=r['ticker'],price=cap,shares=Decimal(1),
                                 shares_available_at=cutoff,price_observed_at=cutoff))
        except (ValueError, TypeError, KeyError) as exc:
            unresolved.append(dict(issuer_id=cid,reason=str(exc)))
    snap, report = mcap_top_n_snapshot(prepared, cutoff, n=500,
                                     source='VALIDATED_CLASS_MARKET_CAP_AGGREGATE/1')
    members = [caps[m.company_id] for m in snap.members]
    ranked = sorted(caps.values(), key=lambda x:(-Decimal(x['market_cap_usd']),x['issuer_id']))
    if unresolved: reasons.append('MISSING_MARKET_CAP_COULD_CROSS_BOUNDARY')
    if len(members) != 500: reasons.append('FEWER_THAN_500_ELIGIBLE_ISSUERS')
    good = not reasons
    prior_ids = {x['issuer_id'] for x in (previous or {}).get('members',[])}
    current_ids = {x['issuer_id'] for x in members}
    out = dict(schema_version='top500-selection/1', population_id=job['population_id'],
        population_version=job['population_version'],policy=deepcopy(policy),
        evaluation_day=day.isoformat(), input_cutoff=job['input_cutoff'],apply_at=job['apply_at'],
        input_hash=digest(job),candidate_members_hash=digest(sorted(expected)),
        status='VALIDATED_RESEARCH_CANDIDATE' if good else 'UNCONFIRMED_CANDIDATE',
        official=False, target_count=475, denominator=500 if good else None,
        availability_context='RETROSPECTIVE' if cutoff.date()>day else 'SAME_DAY_INPUT_CUTOFF',
        historical_pit=False,
        members=members, members_hash=digest(members), ranked=ranked,
        unresolved=unresolved,excluded=excluded,reasons=reasons,boundary_uncertain=not good,
        selected_count=len(members), candidate_count=len(ids), unique_candidate_issuers=len(set(ids)),
        retained_confirmed=deepcopy(previous), replace_official=False,
        membership_changes=dict(entered=sorted(current_ids-prior_ids),exited=sorted(prior_ids-current_ids),
            reason='PROVISIONAL_MARKET_CAP_ORDER' if not good else 'VALIDATED_RESEARCH_MARKET_CAP_ORDER'),
        whole_market_denominator=None)
    out['result_hash']=digest(out)
    return out
