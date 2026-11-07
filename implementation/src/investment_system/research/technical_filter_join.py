"""Dated fixed-security join for an already validated Main technical board.

This pure adapter consumes evidence; it does not discover identities, create IDs,
calculate indicators, rank rows, or publish data. Main owns the screen consumer.
"""
from copy import deepcopy

from .exp_deciles.technical_leaderboard import filter_board
from .exp_deciles.technical_measures import METRIC_IDS
from .kis_price_bridge import _day
from .private_technical_board import SECURITY_IDENTIFIER_TYPES


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


def join_filtered_rows(board, *, qgv_rows, security_links, conditions, data_kind):
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
    """
    if data_kind not in ('SYNTHETIC', 'RETAINED_INPUT'):
        raise ValueError('JOIN_DATA_KIND_REQUIRED')
    securities = _board_securities(board)
    signal = board['signal_day']
    rows = list(qgv_rows)
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
