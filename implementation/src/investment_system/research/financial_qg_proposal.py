"""Isolated financial Q/G definition study, not an official/555 default.

Only orchestration: reuse calc23.1 issuer pools, average-rank percentiles and
the common 50%-available-role axis kernel. No raw financial/price engine,
classification mutation, gate substitution, official result or global ranking.
"""
from copy import deepcopy
import math

from ..qgv.qgv_v2 import axis_score, WEIGHTS
from ..qgv.v2_scoring import SUBMETRICS, MIN_PEERS, _Pool, percentile
from ._private_artifacts import digest

VERSION = 'financial-qg-subtype-study/0.1.0'
SOURCE_BASIS = 'REPORTED_FINANCIAL_EQUITY_AND_INCOME_PROXY_NOT_COMMON_EQUITY_CERTIFIED'


PEER_POLICIES = ('MATCH_ACCOUNTING_SUBTYPE', 'BROAD_THREE_TYPES_DIAGNOSTIC')


def peer_group(row, peer_policy='MATCH_ACCOUNTING_SUBTYPE'):
    if peer_policy not in PEER_POLICIES:
        raise ValueError('UNKNOWN_PEER_POLICY')
    if row.get('financial_calculation_profile') != 'FINANCIAL':
        raise ValueError('NOT_FINANCIAL_INPUT')
    template = row.get('financial_peer_template')
    if template in ('BANK', 'INSURANCE'):
        return template, 'HELD_ACCOUNTING_TEMPLATE'
    if template in ('BROKER', 'ASSET_MANAGER'):
        return ('OTHER_FINANCIAL' if peer_policy == 'BROAD_THREE_TYPES_DIAGNOSTIC' else template), 'HELD_ACCOUNTING_TEMPLATE'
    sic = str((row.get('owner_source_context') or {}).get('sic') or '')
    if len(sic) != 4 or not sic.isdigit() or not 6000 <= int(sic) <= 6499:
        raise ValueError('FINANCIAL_SUBTYPE_UNCONFIRMED')
    # Nondepository credit 61xx is not automatically a deposit-taking bank.
    group = 'BANK' if sic.startswith('60') else 'INSURANCE' if sic.startswith('63') else 'OTHER_FINANCIAL'
    if group == 'OTHER_FINANCIAL' and peer_policy == 'MATCH_ACCOUNTING_SUBTYPE':
        group = {'6282': 'ASSET_MANAGER', '6211': 'BROKER', '6411': 'INSURANCE_AGENCY'}.get(sic, 'UNCONFIRMED_FINANCIAL')
    return group, 'PROVISIONAL_OFFICIAL_SIC_NOT_CONFIRMED_BUSINESS_MODEL'


def recipes(group):
    if group not in ('BANK', 'INSURANCE', 'OTHER_FINANCIAL', 'BROKER', 'ASSET_MANAGER',
                     'INSURANCE_AGENCY', 'UNCONFIRMED_FINANCIAL'):
        raise ValueError('UNKNOWN_FINANCIAL_PEER_GROUP')
    out = deepcopy(SUBMETRICS['FINANCIAL'])
    if group != 'BANK':
        out['q_profitability'] = tuple((m, d) for m, d in out['q_profitability']
                                      if m != 'net_interest_income_to_assets')
    return out


def _metrics(row):
    # Retain actual negative/zero observations; never convert absence to zero.
    out={}
    for key,value in row['metrics'].items():
        if not key.startswith('financial::') or type(value) not in (int,float) or not math.isfinite(value):
            continue
        basis=row.get('metric_evidence',{}).get(key,{}).get('adoption_basis')
        if basis in ('EXPLICIT_CONFLICT_EXCLUDED','ADDITIONAL_VERIFICATION_REQUIRED','UNREVIEWED'):
            raise ValueError('REJECTED_RAW_METRIC_SUPPLIED')
        out[key.removeprefix('financial::')]=value
    return out


def score_financial(evaluation, reference, *, peer_policy='MATCH_ACCOUNTING_SUBTYPE'):
    """One score per evaluation code row; reference points deduplicate issuers.

    The caller pins the two snapshots independently. Every reference is already
    eligible for the same source-period/adoption policy; this study does not
    upgrade inherited share assumptions to verified evidence.
    """
    if len({r['company_id'] for r in evaluation}) != len(evaluation):
        raise ValueError('EVALUATION_DUPLICATE_CODE')
    points = {}
    for row in reference:
        group, _ = peer_group(row, peer_policy)
        issuer = row.get('issuer_id')
        if not isinstance(issuer, str) or not issuer:
            raise ValueError('ISSUER_ID_REQUIRED')
        value = (group, _metrics(row))
        if issuer in points and points[issuer] != value:
            raise ValueError('ISSUER_REFERENCE_CONFLICT')
        points[issuer] = value
    groups={peer_group(row,peer_policy)[0] for row in evaluation}
    pools = {group: _Pool({issuer: metrics for issuer, (g, metrics) in points.items()
                          if g == group and g != 'UNCONFIRMED_FINANCIAL'}) for group in groups}
    out = {}
    for row in evaluation:
        group, classification_basis = peer_group(row, peer_policy)
        issuer = row.get('issuer_id')
        if not isinstance(issuer, str) or not issuer:
            raise ValueError('ISSUER_ID_REQUIRED')
        metrics, roles = _metrics(row), {}
        for role, specs in recipes(group).items():
            items, scores = [], []
            for metric, direction in specs:
                value, score, n = metrics.get(metric), None, 0
                if value is not None and group != 'UNCONFIRMED_FINANCIAL':
                    less, equal, n = pools[group].rank(metric, direction, value, issuer)
                    if n >= MIN_PEERS:
                        score = percentile(less, equal, n)
                        scores.append(score)
                items.append(dict(metric=metric, raw=value, score=score, reference_valid_n=n,
                    reason='ACCOUNTING_SUBTYPE_UNCONFIRMED' if group == 'UNCONFIRMED_FINANCIAL' else
                           'RAW_NOT_ADOPTED' if value is None else 'PEER_SAMPLE_SMALL' if score is None else None))
            roles[role] = dict(score=sum(scores)/len(scores) if scores else None,
                nominal_weight=WEIGHTS[role[0].upper()][role], metrics=items,
                reason='DEFINITION_NOT_COMPLETED' if not specs else 'NO_SCORED_METRIC' if not scores else None)
        values = {k: v['score'] for k, v in roles.items()}
        axes = {a: axis_score(values, a) for a in ('Q', 'G')}
        for role, item in roles.items():
            used = sum(r['nominal_weight'] for k, r in roles.items()
                       if k[0] == role[0] and r['score'] is not None)
            item['effective_axis_weight'] = item['nominal_weight']/used if item['score'] is not None and used else 0
        out[row['company_id']] = dict(issuer_id=issuer, group=group, classification_basis=classification_basis,
            model_version=VERSION, peer_policy=peer_policy, source_basis=SOURCE_BASIS, roles=roles, axes=axes,
            source_metric_evidence_hash=digest({k: v for k, v in row.get('metric_evidence', {}).items()
                                               if k.startswith('financial::')}),
            share_adoption_basis={k: v.get('adoption_basis') for k, v in row.get('metric_evidence', {}).items()
                                  if k in ('financial::eps_cagr_3y','financial::dilution_3y',
                                           'financial::book_value_per_share_cagr_3y')},
            quality_definition_complete=False, global_rank=None, official=False)
    return out
