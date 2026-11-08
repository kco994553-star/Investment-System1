"""Describe existing research selection; never rank, select or change weights."""
from collections import defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path


def _hash(value):
    try:
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    except (ValueError,TypeError):
        return None  # Do not change the legacy path or invent a replay identity.


def describe_selection(*, quality, members, ranked, selected, policy, as_of, universe, portfolio, rule_id, qgv_version=None):
    setting=asdict(policy) if policy is not None else None
    identities={m.company_id:m.cik for m in universe.members}
    original=list(members); ranks={r['company_id']:r['rank'] for r in ranked}
    issuer_groups=defaultdict(list); rows=[]
    for cid in original:
        q=quality.get(cid,{})
        reasons=[axis+'_MISSING' for axis in ('Q','G') if q.get(axis) is None]
        if not reasons and cid not in selected:reasons=['OUTSIDE_SELECTION_LIMIT']
        issuer=identities.get(cid)
        if issuer is not None:issuer_groups[issuer].append(cid)
        rows.append({'company_id':cid,'issuer_id':issuer,'eligible':q.get('Q') is not None and q.get('G') is not None,
                     'selected':cid in selected,'original_rank':ranks.get(cid),'exclusion_reasons':reasons})
    weights=None if portfolio is None else {h.company_id:h.target_weight for h in portfolio.holdings}
    cash=None if portfolio is None else portfolio.cash_weight
    duplicate={k:sorted(v) for k,v in issuer_groups.items() if len(v)>1}
    population={'members':original,'denominator':len(original),'unit':'DECLARED_COMPANY_ID',
        'universe_id':universe.universe_id,'universe_kind':universe.universe_kind.value,
        'membership_basis':universe.membership_basis,'source':universe.source,'source_vintage':universe.source_vintage,
        'as_of':universe.as_of.isoformat(),'available_at':universe.available_at.isoformat(),
        'parent_universe_members':list(universe.ids()),'is_subset_of_parent':set(original)!=set(universe.ids())}
    source_hashes={}
    base=Path(__file__).resolve().parents[1]
    for name in ('validation/vertical_slice.py','contracts/portfolio_input.py','research/selection_details.py'):
        try:source_hashes[name]=hashlib.sha256((base/name).read_bytes()).hexdigest()
        except OSError:source_hashes[name]=None
    input_hash=_hash({'quality':quality,'quality_input_order':list(quality),'population':population,'issuer_ids':identities})
    setting_hash=_hash({'rule_id':rule_id,'selection_policy':setting})
    result_hash=_hash({'input_hash':input_hash,'setting_hash':setting_hash,'source_hashes':source_hashes,'selected':selected,'weights':weights,'cash_weight':cash}) if input_hash and all(source_hashes.values()) else None
    return {'schema_version':'research-selection-details/1','as_of':as_of.isoformat(),'original_population':population,
        'rule_id':rule_id,'selection_policy':setting,'rows':rows,
        'tie_rule':'Q_DESC_G_DESC_V_DESC_MISSING_LAST_COMPANY_ID_ASC' if policy else 'LEGACY_STABLE_INPUT_ORDER',
        'percent_rule':'FLOOR_ELIGIBLE_N_TIMES_DECIMAL_STR_PERCENT_DIV_100',
        'portfolio':{'state':'NOT_FORMED' if portfolio is None else 'FORMED','weights':weights,'cash_weight':cash,
            'weight_sum':None if portfolio is None else portfolio.weight_sum(),'extra_cap':None,'extra_cap_state':'NOT_DEFINED_FOR_GENERAL_SELECTION'},
        'issuers':{'mapping_basis':'DECLARED_UNIVERSE_MEMBER_CIK_NOT_SECURITY_EVIDENCE','unknown_company_ids':[c for c in original if identities.get(c) is None],
            'duplicate_groups':duplicate,'handling':'NO_CONSOLIDATION_OR_ISSUER_CAP_IN_EXISTING_RULE','security_identity_verified':False},
        'reproduction':{'scope':'SELECTION_AND_WEIGHTS_FROM_RETAINED_AXES_NOT_QGV_OR_PERFORMANCE_REPLAY',
            'setting_hash':setting_hash,'input_hash':input_hash,'result_hash':result_hash,'engine_source_sha256':source_hashes,
            'status':'REPLAY_IDENTIFIED' if result_hash else 'IDENTITY_UNAVAILABLE',
            'requires_original_input':True,'latest_input_is_new_calculation':True,
            'qgv_version':qgv_version,'qgv_version_reason':None if qgv_version else 'NOT_SUPPLIED_BY_SOURCE_RESULT'},
        'performance_verified':False}
