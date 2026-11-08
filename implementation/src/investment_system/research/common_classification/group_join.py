"""Create a dated group roster from trusted classification/projection artifacts.

No input prices, selected QGV rows or successful measurements determine members.
Existing /1 files are unchanged; this opt-in sidecar binds their identities.
"""
from copy import deepcopy

from ..sector_qgv import digest
from ..kis_price_bridge import _day
from .technical_macro import _rows, _sector


def _applies(row, day):
    a = row.get('applicability', {})
    if a.get('kind') == 'EVALUATION_ONLY':
        return a.get('evaluation_date') == day and a.get('valid_from') is None and a.get('valid_to') is None
    if a.get('kind') == 'INTERVAL' and a.get('valid_from'):
        return _day(a['valid_from']) <= day and (a.get('valid_to') is None or day < _day(a['valid_to']))
    return False


def build_group_manifest(view, technical, group_id):
    """Inputs must be authenticated/manifest-verified before this pure adapter.

    An opaque matching hash is not authentication. A truncated projection cannot
    reduce the original view's denominator or fabricate a complete group.
    """
    companies = _rows(view)
    if any(not isinstance(view.get(k), str) or not view[k] for k in ('universe_id', 'universe_version')):
        raise ValueError('GROUP_UNIVERSE_CONTEXT_REQUIRED')
    if technical.get('schema_version') != 'common-classification-technical/1':
        raise ValueError('GROUP_PROJECTION_SCHEMA_MISMATCH')
    for key in ('valuation_date', 'classification_hash', 'data_kind'):
        if technical.get(key) != view[key]:
            raise ValueError('GROUP_PROJECTION_CONTEXT_MISMATCH:' + key)
    projected = technical.get('rows', [])
    if (len(projected) != len(companies) or len({r['company_id'] for r in projected}) != len(companies)
            or {r['company_id'] for r in projected} != set(companies)):
        raise ValueError('GROUP_PROJECTION_MEMBERS_MISMATCH')
    by_code = {r['company_id']: r for r in projected}
    for code, row in companies.items():
        p = by_code[code]
        if (p.get('issuer_id') != row.get('issuer_id') or p.get('classification_record_id') != row.get('record_id')
                or p.get('sector_id') != _sector(row)):
            raise ValueError('GROUP_PROJECTION_RECORD_MISMATCH')
    found = [g for g in technical.get('groups', []) if g['board'].get('group_id') == group_id]
    if len(found) != 1:
        raise ValueError('GROUP_PROJECTION_GROUP_MISMATCH')
    group = found[0]; board = group['board']; basis = technical['price_basis']
    if (group_id != 'COMMON:' + group['sector_id'] + ':' + basis or board['signal_day'] != view['valuation_date']
            or board['membership_status'] != group['membership_status']):
        raise ValueError('GROUP_PROJECTION_CONTEXT_MISMATCH:board')
    if board['membership_source'] != ('common-classification:' + view['classification_hash']
                                      if group['membership_status'] == 'CONFIRMED' else None):
        raise ValueError('GROUP_PROJECTION_CONTEXT_MISMATCH:classification_hash')
    relevant = [r for r in view['rows'] if _sector(r) == group['sector_id']]
    if group['counts']['company_members'] != len(relevant):
        raise ValueError('GROUP_PROJECTION_MEMBERS_MISMATCH')
    reasons = list(group.get('membership_reasons', []))
    if any(_sector(row) is None for row in companies.values()):
        reasons.append('CLASSIFICATION_POPULATION_INCOMPLETE')
    members = []
    for row in relevant:
        p = by_code[row['company_id']]; ids = p.get('security_ids', [])
        if p.get('status') != 'CONFIRMED' or len(ids) != 1:
            reasons.append('GROUP_MEMBER_SECURITY_UNCONFIRMED')
        if not _applies(row, view['valuation_date']):
            reasons.append('CLASSIFICATION_APPLICABILITY_UNCONFIRMED')
        if not row.get('record_id') or not row.get('issuer_id'):
            reasons.append('GROUP_MEMBER_EVIDENCE_UNCONFIRMED')
        members.append(dict(company_id=row['company_id'], issuer_id=row.get('issuer_id'),
            classification_record_id=row.get('record_id'), security_id=ids[0] if len(ids) == 1 else None,
            evidence_refs=deepcopy(row.get('source_refs') or row['sector'].get('evidence_refs', []))))
    if group['membership_status'] != 'CONFIRMED' and not reasons:
        reasons.append('GROUP_MEMBERSHIP_UNCONFIRMED')
    context = dict(signal_day=view['valuation_date'], group_id=group_id,
        classification_hash=view['classification_hash'], population_hash=board['population_hash'],
        universe_id=view['universe_id'], universe_version=view['universe_version'],
        universe_members_hash=digest(sorted(view['members'])), dictionary_version=view['dictionary_version'],
        mapping_version=view['mapping_version'], knowledge_as_of=view['knowledge_as_of'], price_basis=basis)
    return dict(schema_version='technical-filter-membership/1', data_kind=view['data_kind'], context=context,
        membership_status='UNKNOWN' if reasons else 'CONFIRMED', reasons=sorted(set(reasons)), members=members)
