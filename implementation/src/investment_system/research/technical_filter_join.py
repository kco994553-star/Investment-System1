"""Dated fixed-security join for an already validated Main technical board.

This pure adapter consumes evidence; it does not discover identities, create IDs,
calculate indicators, rank rows, or publish data. Main owns the screen consumer.
"""
from copy import deepcopy
import hashlib
import json
import re

from .exp_deciles.technical_leaderboard import filter_board
from .exp_deciles.technical_measures import METRIC_IDS
from .kis_price_bridge import _day
from .private_technical_board import SECURITY_IDENTIFIER_TYPES

GROUP_CONTEXT_FIELDS = ('signal_day', 'group_id', 'classification_hash', 'population_hash',
    'universe_id', 'universe_version', 'universe_members_hash', 'dictionary_version',
    'mapping_version', 'knowledge_as_of', 'price_basis')


def _text(value, error):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(error)
    return value


def _board_securities(board):
    """Check join identities across metrics, without duplicating the Main reader."""
    if board.get('schema') != 'technical-leaderboard/1':
        raise ValueError('TECHNICAL_BOARD_SCHEMA_MISMATCH')
    _day(board.get('signal_day'))
    if board.get('membership_status') != 'CONFIRMED':
        raise ValueError('GROUP_MEMBERSHIP_UNCONFIRMED')
    if set(board.get('metrics', {})) != set(METRIC_IDS):
        raise ValueError('TECHNICAL_METRICS_MISMATCH')
    securities = None
    for metric in METRIC_IDS:
        seen = {}
        for row in board['metrics'][metric]['rows']:
            sid = _text(row.get('security_id'), 'PERMANENT_SECURITY_ID_REQUIRED')
            series = _text(row.get('series_id'), 'REQUEST_SERIES_ID_REQUIRED')
            if sid in seen:
                raise ValueError('DUPLICATE_TECHNICAL_KEY')
            seen[sid] = (series, row.get('symbol'))
        if securities is not None and seen != securities:
            raise ValueError('TECHNICAL_IDENTITY_MISMATCH')
        securities = seen
    return securities


def _group_rows(board, rows, manifest, context, data_kind):
    """Check a trusted producer roster against independently pinned request context.

    Neither input rows nor measurement availability can establish membership.
    Hash equality binds supplied records; it does not authenticate an arbitrary
    object. The caller must load the manifest from its verified source bundle.
    """
    if not isinstance(manifest, dict) or not isinstance(context, dict):
        raise ValueError('GROUP_MEMBERSHIP_REQUIRED')
    if manifest.get('schema_version') != 'technical-filter-membership/1':
        raise ValueError('GROUP_MEMBERSHIP_SCHEMA_MISMATCH')
    if manifest.get('data_kind') != data_kind:
        raise ValueError('GROUP_DATA_KIND_MISMATCH')
    if manifest.get('membership_status') != 'CONFIRMED':
        raise ValueError('GROUP_MEMBERSHIP_UNCONFIRMED')
    bound = manifest.get('context')
    if not isinstance(bound, dict):
        raise ValueError('GROUP_CONTEXT_REQUIRED')
    for key in GROUP_CONTEXT_FIELDS:
        _text(bound.get(key), 'GROUP_CONTEXT_REQUIRED')
        if context.get(key) != bound[key]:
            raise ValueError('GROUP_CONTEXT_MISMATCH:' + key)
    for key in ('classification_hash', 'population_hash', 'universe_members_hash'):
        if re.fullmatch('[0-9a-f]{64}', bound[key]) is None:
            raise ValueError('GROUP_CONTEXT_HASH_INVALID')
    for key in ('signal_day', 'group_id', 'population_hash'):
        if board.get(key) != bound[key]:
            raise ValueError('GROUP_CONTEXT_MISMATCH:' + key)
    _day(bound['signal_day'])
    if board.get('membership_source') != 'common-classification:' + bound['classification_hash']:
        raise ValueError('GROUP_CONTEXT_MISMATCH:classification_hash')
    if bound['price_basis'] not in ('RAW', 'SPLIT_ADJUSTED') or not bound['group_id'].endswith(':' + bound['price_basis']):
        raise ValueError('GROUP_CONTEXT_MISMATCH:price_basis')
    members = manifest.get('members')
    if not isinstance(members, list):
        raise ValueError('GROUP_MEMBERSHIP_REQUIRED')
    by_code, security_ids = {}, set()
    for member in members:
        if not isinstance(member, dict):
            raise ValueError('GROUP_MEMBER_INVALID')
        code = _text(member.get('company_id'), 'GROUP_MEMBER_INVALID')
        sid = _text(member.get('security_id'), 'GROUP_MEMBER_INVALID')
        if code in by_code or sid in security_ids:
            raise ValueError('DUPLICATE_GROUP_MEMBER')
        _text(member.get('classification_record_id'), 'GROUP_MEMBER_INVALID')
        _text(member.get('issuer_id'), 'GROUP_MEMBER_INVALID')
        by_code[code] = member
        security_ids.add(sid)
    population = dict(group_id=bound['group_id'], signal_day=bound['signal_day'], members=sorted(security_ids))
    if (hashlib.sha256(json.dumps(population, sort_keys=True).encode()).hexdigest() != bound['population_hash']
            or set(_board_securities(board)) != security_ids):
        raise ValueError('BOARD_MEMBERSHIP_MISMATCH')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('COMPANY_CODE_REQUIRED')
        code = _text(row.get('code'), 'COMPANY_CODE_REQUIRED')
        if code in seen:
            raise ValueError('DUPLICATE_GROUP_ROW')
        seen.add(code)
        if code not in by_code:
            raise ValueError('ROW_OUTSIDE_GROUP')
        member = by_code[code]
        if row.get('signal_day') != bound['signal_day']:
            raise ValueError('SIGNAL_DAY_MISMATCH')
        for key, expected in (('classification_hash', bound['classification_hash']),
                              ('classification_record_id', member['classification_record_id'])):
            if key in row and row[key] != expected:
                raise ValueError('ROW_CLASSIFICATION_MISMATCH')
        if row.get('security_id') != member['security_id']:
            raise ValueError('SECURITY_CLASSIFICATION_MISMATCH')
        if row.get('issuer_id') is not None and row['issuer_id'] != member['issuer_id']:
            raise ValueError('ISSUER_CLASSIFICATION_MISMATCH')
    if seen != set(by_code):
        raise ValueError('GROUP_MEMBER_MISSING')
    return by_code


def join_group_rows(board, *, qgv_rows, security_links, conditions, data_kind,
                    group_manifest=None, group_context=None, connect_issuers=False):
    """Strict /2 envelope, preserving original rows and explicit connection audit.

    Issuer connection is opt-in evidence enrichment, before the unchanged identity
    checks. Null is never silently replaced by the legacy id/ticker. A missing
    roster cannot receive VERIFIED; legacy join_filtered_rows remains identity-only.
    """
    if data_kind not in ('SYNTHETIC', 'RETAINED_INPUT'):
        raise ValueError('JOIN_DATA_KIND_REQUIRED')
    if type(connect_issuers) is not bool:
        raise ValueError('ISSUER_CONNECTION_OPTION_INVALID')
    rows = list(qgv_rows)
    members = _group_rows(board, rows, group_manifest, group_context, data_kind)
    connected, audit = deepcopy(rows), []
    if connect_issuers:
        for row in connected:
            if row.get('issuer_id') is not None:
                continue
            member = members[row['code']]
            refs = member.get('evidence_refs')
            if not isinstance(refs, list) or not refs or any(not isinstance(v, str) or not v.strip() for v in refs):
                raise ValueError('ISSUER_CONNECTION_EVIDENCE_REQUIRED')
            audit.append(dict(company_id=row['code'], previous_field_present='issuer_id' in row,
                previous_issuer_id=row.get('issuer_id'), issuer_id=member['issuer_id'],
                classification_record_id=member['classification_record_id'],
                classification_hash=group_context['classification_hash'], signal_day=group_context['signal_day'],
                knowledge_as_of=group_context['knowledge_as_of'], evidence_refs=deepcopy(refs),
                basis='VERIFIED_CLASSIFICATION_RECORD'))
            row['issuer_id'] = member['issuer_id']
    selected = join_filtered_rows(board, qgv_rows=connected, security_links=security_links,
        conditions=conditions, data_kind=data_kind, group_manifest=group_manifest, group_context=group_context)
    return dict(schema_version='technical-filter-join/2', data_kind=data_kind,
        membership_validation='VERIFIED' if members else 'VERIFIED_EMPTY', context=deepcopy(group_context),
        original_group_count=len(members), selected_count=len(selected), issuer_connections=audit, rows=selected)


def join_filtered_rows(board, *, qgv_rows, security_links, conditions, data_kind,
                       group_manifest=None, group_context=None):
    """Return selected QGV rows, unchanged and in their original input order.

    Precondition: ``board`` passed the existing ``techScreen.validate`` reader
    (or was produced by the shared board builder). This adds join validation,
    not a replacement board/numeric validator. Keys are (signal_day, security_id).
    QGV rows keep Main's id/ticker/code/score/rank fields and explicitly supply
    signal_day and security_id. Never derive those two from id, code or ticker.

    Links reuse private_technical_board's fixed-ID link fields, with issuer_id,
    symbol, share_class and identity status/reference. Dates are inclusive. Only
    a unique CONFIRMED link active at S can relate an existing ID to that series,
    issuer and ticker. Different securities never join via a common issuer.
    A bad row rejects the entire requested batch, including rows a filter would
    exclude. Caller must report the refusal, not silently apply another join.
    With group_manifest + group_context it also validates the complete group.
    Without both it is legacy identity validation only (completeness NOT_CHECKED).
    """
    if data_kind not in ('SYNTHETIC', 'RETAINED_INPUT'):
        raise ValueError('JOIN_DATA_KIND_REQUIRED')
    securities = _board_securities(board)
    signal = board['signal_day']
    rows = list(qgv_rows)
    if group_manifest is not None or group_context is not None:
        _group_rows(board, rows, group_manifest, group_context, data_kind)
    links_by_id = {}
    active_series = set()
    active_ids = set()
    for link in security_links:
        sid = _text(link.get('security_id'), 'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')
        kind = link.get('identifier_type')
        if not isinstance(kind, str) or kind not in SECURITY_IDENTIFIER_TYPES:
            raise ValueError('FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')
        for field in ('reference', 'identity_reference', 'series_id', 'issuer_id', 'symbol', 'share_class'):
            _text(link.get(field), 'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')
        if link.get('identity_status') != 'CONFIRMED':
            raise ValueError('FIXED_SECURITY_LINK_UNCONFIRMED')
        if sid in (link['issuer_id'], link['symbol']):
            raise ValueError('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID')
        synthetic = kind == 'SYNTHETIC_FIXED_SECURITY_ID' or sid.startswith('SYNTHETIC:')
        if synthetic and data_kind != 'SYNTHETIC':
            raise ValueError('SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT')
        if _day(link.get('valid_from')) > _day(link.get('valid_to')):
            raise ValueError('INVALID_SECURITY_LINK_RANGE')
        links_by_id.setdefault(sid, []).append(link)
        if link['valid_from'] <= signal <= link['valid_to']:
            if link['series_id'] in active_series or sid in active_ids:
                raise ValueError('DUPLICATE_SECURITY_LINK')
            active_series.add(link['series_id'])
            active_ids.add(sid)

    seen = set()
    for row in rows:
        if _day(row.get('signal_day')) != signal:
            raise ValueError('SIGNAL_DAY_MISMATCH')
        sid = _text(row.get('security_id'), 'PERMANENT_SECURITY_ID_REQUIRED')
        if sid in (row.get('id'), row.get('issuer_id'), row.get('ticker'), row.get('code')):
            raise ValueError('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID')
        key = (signal, sid)
        if key in seen:
            raise ValueError('DUPLICATE_QGV_KEY')
        seen.add(key)
        if sid not in securities:
            raise ValueError('SECURITY_ID_NOT_IN_BOARD')
        candidates = links_by_id.get(sid, [])
        if not candidates:
            raise ValueError('FIXED_SECURITY_LINK_MISSING')
        active = [link for link in candidates if link['valid_from'] <= signal <= link['valid_to']]
        if not active:
            raise ValueError('SECURITY_LINK_OUTSIDE_SIGNAL_DAY')
        link = active[0]
        series, symbol = securities[sid]
        if link['series_id'] != series:
            raise ValueError('SERIES_LINK_MISMATCH')
        # New common records retain the original company code as id and carry
        # issuer_id separately. Absence (not an explicit null) preserves /1.
        issuer = row['issuer_id'] if 'issuer_id' in row else row.get('id')
        if issuer != link['issuer_id']:
            raise ValueError('ISSUER_LINK_MISMATCH')
        if row.get('ticker') != link['symbol'] or symbol not in (None, link['symbol']):
            raise ValueError('SYMBOL_LINK_MISMATCH')

    # This selects IDs from existing predicates. It never recalculates scores,
    # ranks, median, N or deciles. Validation above also applies to excluded rows.
    selected = set(filter_board(board, conditions))
    return [deepcopy(row) for row in rows if row['security_id'] in selected]
