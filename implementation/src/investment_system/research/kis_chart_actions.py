"""Offline, retrospective chart review of SEC/issuer evidence against MODP0 bars."""
from datetime import date
from decimal import Decimal, localcontext
from functools import lru_cache
import json
from pathlib import Path

from .exp_deciles import schedule
from .kis_price_bridge import EXCHANGES, price_rows, validate_contract


@lru_cache(maxsize=1)
def reviewed_actions():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))


def chart_basis(contract, code, day):
    validate_contract(contract)
    query = contract['source_query']
    if query['MODP'] != '0' or query['GUBN'] != '0' or query['SYMB'] != contract['symbol']:
        raise ValueError('RAW_DAILY_SOURCE_REQUIRED')
    if EXCHANGES.get(query['EXCD']) != contract['exchange']:
        raise ValueError('SERIES_EXCHANGE_CONFLICT')
    listed = reviewed_actions().get(code, [])
    actions = {r['date']: r for r in listed}
    if len(actions) != len(listed):
        raise ValueError('DUPLICATE_REVIEWED_ACTION')
    declared = {r['date']: r for r in contract['splits']}
    events = declared.copy() if contract['basis'] == 'SPLIT_ADJUSTED' else {}
    marks = []
    raw = contract['raw_bars']
    for a, b in zip(raw, raw[1:]):
        when = b['date']
        if when > day:
            break
        old, new = a['close'], b['close']
        move = Decimal(new) / Decimal(old) if old and new else None
        jump = move is not None and abs(move - 1) >= Decimal('.30')
        action = actions.get(when)
        if action and (contract['currency'] != 'USD' or
                       code != contract['exchange'] + ':' + contract['symbol'] or
                       contract.get('issuer_id') not in (None, action['cik'])):
            action = None
        if not action and (not jump or when in events):
            continue
        if action and action['kind'] == 'SPLIT':
            n, d = action['new_shares'], action['old_shares']
            with localcontext() as ctx:
                ctx.prec = 50
                ratio = Decimal(n) / Decimal(d)
            continuous = schedule.previous_session(date.fromisoformat(when)).isoformat() == a['date']
            if continuous and old and b['open'] and abs(Decimal(b['open']) / Decimal(old) * ratio - 1) <= Decimal('.08'):
                if when in declared and Decimal(declared[when]['ratio']) != ratio:
                    raise ValueError('SPLIT_RATIO_CONFLICT')
                events[when] = dict(date=when, ratio=str(ratio), status='CONFIRMED',
                                    new_shares=n, old_shares=d, evidence=action)
                continue
        if action and when in events:
            raise ValueError('SPLIT_REVIEW_CONFLICT')
        if action and action['kind'] == 'SPINOFF_PARENT_UNCHANGED':
            state = 'NON_SPLIT_DISTRIBUTION'
        else:
            state = 'EVIDENCE_OR_RAW_STEP_UNCONFIRMED'
        marks.append(dict(date=when, state=state, previous_day=a['date'],
                          close_ratio=str(move) if move is not None else None, evidence=action))
    if not events:
        return contract, marks
    chart = dict(contract, basis='SPLIT_ADJUSTED', splits=sorted(events.values(), key=lambda s: s['date']))
    chart['bars'] = price_rows(chart, chart['price_basis_date'])
    return chart, marks
