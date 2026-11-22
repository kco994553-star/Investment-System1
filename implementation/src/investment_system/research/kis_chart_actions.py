"""Offline, retrospective chart review of SEC/issuer evidence against MODP0 bars."""
from datetime import date
from decimal import Decimal, localcontext
from functools import lru_cache
import json
import re
from pathlib import Path

from ._private_artifacts import digest
from .exp_deciles import schedule
from .kis_price_bridge import EXCHANGES, price_rows, validate_contract


@lru_cache(maxsize=1)
def reviewed_actions():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))


def merge_reviewed_actions(extra):
    """Merge date-keyed evidence without overriding the built-in register."""
    if not isinstance(extra, dict) or extra.get('schema') != 'reviewed-chart-actions/1' or not isinstance(extra.get('listings'), dict):
        raise ValueError('REVIEWED_ACTIONS_SCHEMA')
    merged = reviewed_actions().copy()
    for code, additions in extra['listings'].items():
        if not isinstance(code, str) or not isinstance(additions, list) or not additions:
            raise ValueError('REVIEWED_ACTIONS_LISTING')
        venue, sep, symbol = code.partition(':')
        if not sep or venue not in {*EXCHANGES.values(), 'ETF'} or not re.fullmatch(r'[A-Z0-9][A-Z0-9./-]*', symbol):
            raise ValueError('REVIEWED_ACTIONS_LISTING')
        entries = merged.get(code, [])[:]
        dates = {entry['date'] for entry in entries}
        for entry in additions:
            if not isinstance(entry, dict) or entry.get('kind') not in ('SPLIT', 'DOCUMENTED_MARKET_MOVE'):
                raise ValueError('REVIEWED_ACTION_KIND')
            when = entry.get('date')
            if not isinstance(when, str) or date.fromisoformat(when).isoformat() != when or when in dates:
                raise ValueError('REVIEWED_ACTION_DATE')
            if (not re.fullmatch(r'[0-9]{10}', str(entry.get('cik', ''))) or
                    not isinstance(entry.get('url'), str) or not entry['url'].startswith('https://') or
                    not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', ''))) or not entry.get('locator')):
                raise ValueError('REVIEWED_ACTION_EVIDENCE')
            expected_exchange = EXCHANGES.get(entry.get('provider_excd'))
            if not expected_exchange or (venue != 'ETF' and venue != expected_exchange):
                raise ValueError('REVIEWED_ACTION_VENUE')
            if entry['kind'] == 'SPLIT':
                if any(type(entry.get(k)) is not int or entry[k] <= 0 for k in ('new_shares','old_shares')) or entry['new_shares'] == entry['old_shares']:
                    raise ValueError('REVIEWED_ACTION_RATIO')
            elif not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('raw_step_sha256', ''))):
                raise ValueError('REVIEWED_MARKET_STEP_PIN')
            dates.add(when)
            entries.append(entry)
        merged[code] = sorted(entries, key=lambda e: e['date'])
    return merged


def chart_basis(contract, code, day, *, entries=None):
    validate_contract(contract)
    query = contract['source_query']
    if query['MODP'] != '0' or query['GUBN'] != '0' or query['SYMB'] != contract['symbol']:
        raise ValueError('RAW_DAILY_SOURCE_REQUIRED')
    if EXCHANGES.get(query['EXCD']) != contract['exchange']:
        raise ValueError('SERIES_EXCHANGE_CONFLICT')
    listed = reviewed_actions().get(code, []) if entries is None else entries
    actions = {r['date']: r for r in listed}
    if len(actions) != len(listed):
        raise ValueError('DUPLICATE_REVIEWED_ACTION')
    declared = {r['date']: r for r in contract['splits']}
    events = declared.copy() if contract['basis'] == 'SPLIT_ADJUSTED' else {}
    marks = []
    reviewed_steps = []
    raw = contract['raw_bars']
    for a, b in zip(raw, raw[1:]):
        when = b['date']
        if when > day:
            break
        old, new = a['close'], b['close']
        move = Decimal(new) / Decimal(old) if old and new else None
        jump = move is not None and abs(move - 1) >= Decimal('.30')
        action = actions.get(when)
        if action:
            venue_matches = action.get('provider_excd', query['EXCD']) == query['EXCD']
            listing_matches = code == contract['exchange'] + ':' + contract['symbol']
            if code == 'ETF:' + contract['symbol']:
                listing_matches = action.get('provider_excd') == query['EXCD']
            if (contract['currency'] != 'USD' or not venue_matches or not listing_matches or
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
                reviewed_steps.append(dict(start=a['date'], end=when, reference=action['url']))
                continue
        if action and when in events:
            raise ValueError('SPLIT_REVIEW_CONFLICT')
        if action and action['kind'] == 'SPINOFF_PARENT_UNCHANGED':
            state = 'NON_SPLIT_DISTRIBUTION'
        elif (action and action['kind'] == 'DOCUMENTED_MARKET_MOVE' and jump and
              schedule.previous_session(date.fromisoformat(when)).isoformat() == a['date'] and
              action['raw_step_sha256'] == digest([a['date'], a['close'], when, b['open'], b['close']])):
            state = 'DOCUMENTED_MARKET_MOVE'
        else:
            state = 'EVIDENCE_OR_RAW_STEP_UNCONFIRMED'
        marks.append(dict(date=when, state=state, previous_day=a['date'],
                          close_ratio=str(move) if move is not None else None, evidence=action))
    if not events:
        return contract, marks
    chart = dict(contract, basis='SPLIT_ADJUSTED', splits=sorted(events.values(), key=lambda s: s['date']))
    chart['reviewed_split_steps'] = reviewed_steps
    chart['bars'] = price_rows(chart, chart['price_basis_date'])
    return chart, marks
