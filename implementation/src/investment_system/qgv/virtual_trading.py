"""Virtual trading rules v1 (PROVISIONAL): deterministic daily replay of one virtual ledger.

Python reference for web_assets/virtual-trading.js (vectors: tests/fixtures/virtual_trading_reference_v1.json).
Everything here is RAM-only research: prices, ledgers and P&L are inputs/outputs of a pure function and are never
fetched, persisted or published. A virtual buy/sell is a rule record, not an order or a recommendation.

Float operations are written in the same order as the JS port so both produce identical doubles.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name('virtual_trading_v1_provisional.json')
LEDGER_KINDS = ('SET_A', 'SET_B', 'SHADOW')
COVERAGES = ('READY', 'PARTIAL', 'BLOCKED')
FLAG_KINDS = ('HOLD', 'EXCLUDE', 'CONFIRMED_TEMPORARY', 'CONFIRMED_STRUCTURAL', 'CLEAR')
EVENT_KINDS = ('EARNINGS_WINDOW', 'TYPE_CHANGED')
# Judgement levels, highest priority first (REPORT_TEMPLATE_V1 §7.1, D-19).
LEVELS = ('BLOCK', 'RISK_RECHECK', 'REDUCE_REVIEW', 'INCREASE_REVIEW', 'ADDITIONAL_REVIEW', 'HOLDING_CONTEXT', 'OBSERVE')
SYMBOLS = {'BLOCK': '■', 'RISK_RECHECK': '▼', 'REDUCE_REVIEW': '▼', 'INCREASE_REVIEW': '▲',
           'ADDITIONAL_REVIEW': '●', 'HOLDING_CONTEXT': '●', 'OBSERVE': '●'}
SP500 = 'SP500'


class VirtualTradingInputError(ValueError):
    pass


def load_config(path=CONFIG_PATH):
    return validate_config(json.loads(Path(path).read_text(encoding='utf-8')))


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def _pos(v):
    return _num(v) and v > 0


def _day(v):
    if not (isinstance(v, str) and len(v) == 10 and v[4] == '-' and v[7] == '-' and (v[:4] + v[5:7] + v[8:]).isdigit()):
        return False
    m, d = int(v[5:7]), int(v[8:])
    return 1 <= m <= 12 and 1 <= d <= 31


def _need(ok, code='INPUT_INVALID'):
    if not ok:
        raise VirtualTradingInputError(code)


def validate_config(c):
    _need(isinstance(c, dict) and c.get('schema_version') == 1 and c.get('rules_version') == 'virtual_trading_rules/v1', 'CONFIG_INVALID')
    _need(c.get('start_date') is None or _day(c['start_date']), 'CONFIG_INVALID')
    for k in ('daily_deposit', 'buy_limit', 'sell_limit', 'min_trade', 'band_pp', 'qg_decline_threshold'):
        _need(_num(c.get(k)) and c[k] >= 0, 'CONFIG_INVALID')
    _need(_num(c.get('cost_bps')) and 0 <= c['cost_bps'] < 10000, 'CONFIG_INVALID')
    _need(c.get('execution') == 'NEXT_SESSION_CLOSE' and c.get('fractional_quantity') is True, 'CONFIG_INVALID')
    a, s = c.get('abnormal_drop'), c.get('v_slope')
    _need(isinstance(a, dict) and type(a.get('window_sessions')) is int and a['window_sessions'] > 0
          and type(a.get('lookback_sessions')) is int and a['lookback_sessions'] > 1 and _pos(a.get('k')), 'CONFIG_INVALID')
    _need(isinstance(s, dict) and type(s.get('lookback_sessions')) is int and s['lookback_sessions'] > 0 and _pos(s.get('threshold')), 'CONFIG_INVALID')
    _need(isinstance(c.get('hit_windows'), list) and all(type(w) is int and w > 0 for w in c['hit_windows'])
          and type(c.get('hit_min_samples')) is int and c['hit_min_samples'] > 0, 'CONFIG_INVALID')
    _need(c.get('sector_basis') in ('SP500_SUBSTITUTE_D22_PENDING', 'SECTOR_ETF_CONFIRMED'), 'CONFIG_INVALID')
    return c


def _series(v):
    _need(isinstance(v, dict) and all(_day(k) and _pos(x) for k, x in v.items()))
    return v


def _validate_ledger(L):
    _need(isinstance(L, dict) and L.get('kind') in LEDGER_KINDS and isinstance(L.get('id'), str) and L['id'])
    sessions = L.get('sessions')
    _need(isinstance(sessions, list) and all(_day(d) for d in sessions) and all(sessions[i] < sessions[i + 1] for i in range(len(sessions) - 1)))
    tw = L.get('target_weights')
    if tw is not None:
        _need(isinstance(tw, dict) and all(isinstance(k, str) and _num(v) and 0 <= v <= 100 for k, v in tw.items()))
        total = 0
        for k in sorted(tw):
            total += tw[k]
        _need(total <= 100 + 1e-9)
    comps = L.get('companies')
    _need(isinstance(comps, dict))
    for cid, c in comps.items():
        _need(isinstance(c, dict) and isinstance(c.get('currency'), str) and len(c['currency']) == 3)
        _series(c.get('closes'))
        _need(c.get('sector_benchmark') is None or isinstance(c['sector_benchmark'], str))
    bm = L.get('benchmarks', {})
    _need(isinstance(bm, dict))
    for v in bm.values():
        _series(v)
    fx = L.get('fx', {})
    _need(isinstance(fx, dict))
    for v in fx.values():
        _series(v)
    init = L.get('initial', {'cash': 0, 'positions': {}})
    _need(isinstance(init, dict) and _num(init.get('cash')) and init['cash'] >= 0 and isinstance(init.get('positions'), dict))
    for cid, p in init['positions'].items():
        _need(cid in comps and isinstance(p, dict) and _pos(p.get('quantity')) and _num(p.get('cost')) and p['cost'] >= 0)
    snaps = L.get('snapshots', {})
    _need(isinstance(snaps, dict))
    for d, rows in snaps.items():
        _need(_day(d) and isinstance(rows, dict))
        for r in rows.values():
            _need(isinstance(r, dict) and r.get('coverage') in COVERAGES and (r.get('q') is None or _num(r['q'])) and (r.get('g') is None or _num(r['g'])))
    vs = L.get('v_scores', {})
    _need(isinstance(vs, dict) and all(_day(d) and isinstance(r, dict) and all(v is None or _num(v) for v in r.values()) for d, r in vs.items()))
    flags = L.get('flags', [])
    _need(isinstance(flags, list) and all(isinstance(f, dict) and _day(f.get('date')) and f.get('kind') in FLAG_KINDS and isinstance(f.get('company'), str) for f in flags))
    ev = L.get('events', {})
    _need(isinstance(ev, dict) and all(_day(d) and isinstance(r, dict) and all(isinstance(x, list) and all(e in EVENT_KINDS for e in x) for x in r.values()) for d, r in ev.items()))
    return L


def _fx(L, ccy, day):
    if ccy == 'KRW':
        return 1
    s = L.get('fx', {}).get(ccy)
    return s.get(day) if s else None


def _last_on_or_before(series, day):
    best = None
    for k in series:
        if k <= day and (best is None or k > best):
            best = k
    return best


def _active_flag(flags, cid, day):
    """Latest flag for this company dated on or before `day`; ties resolve to the later list entry."""
    found = None
    for f in flags:
        if f['company'] == cid and f['date'] <= day and (found is None or f['date'] >= found['date']):
            found = f
    return None if found is None or found['kind'] == 'CLEAR' else found['kind']


def _qg(row):
    if row is None or row.get('q') is None or row.get('g') is None:
        return None
    return (row['q'] + row['g']) / 2


def _prev_snapshot(snaps, cid, day):
    best = None
    for d, rows in snaps.items():
        if d < day and cid in rows and (best is None or d > best):
            best = d
    return snaps[best][cid] if best is not None else None


def abnormal_drop(closes, bench, day, cfg):
    """D-5: 20-session excess return vs the sector basis below mean − k·σ of the company's own past-year distribution."""
    a = cfg['abnormal_drop']
    w, n_look, k = a['window_sessions'], a['lookback_sessions'], a['k']
    if bench is None:
        return {'state': 'NOT_AVAILABLE', 'reason': 'SECTOR_BASIS_NOT_AVAILABLE'}
    dates = sorted(d for d in closes if d <= day and d in bench)
    if not dates or dates[-1] != day:
        return {'state': 'NOT_AVAILABLE', 'reason': 'PRICE_NOT_ALIGNED'}
    need = n_look + w + 1
    if len(dates) < need:
        return {'state': 'NOT_AVAILABLE', 'reason': 'HISTORY_INSUFFICIENT'}
    dates = dates[-need:]
    ex = []
    for j in range(w, len(dates)):
        rs = closes[dates[j]] / closes[dates[j - w]] - 1
        rb = bench[dates[j]] / bench[dates[j - w]] - 1
        ex.append(rs - rb)
    current = ex[-1]
    sample = ex[:-1]
    mean = 0
    for x in sample:
        mean += x
    mean = mean / len(sample)
    var = 0
    for x in sample:
        var += (x - mean) * (x - mean)
    sd = math.sqrt(var / (len(sample) - 1))
    if not sd > 0:
        return {'state': 'NOT_AVAILABLE', 'reason': 'DISTRIBUTION_DEGENERATE'}
    z = (current - mean) / sd
    return {'state': 'ABNORMAL' if z < -k else 'NORMAL', 'reason': None, 'z': z}


def _sector_series(L, cid, cfg):
    bm = L.get('benchmarks', {})
    key = L['companies'][cid].get('sector_benchmark') if cfg['sector_basis'] == 'SECTOR_ETF_CONFIRMED' else None
    if key and key in bm:
        return bm[key], key
    return bm.get(SP500), SP500


def _judge(L, cfg, cid, day, idx, state, total):
    """One company's judgement on decision day `day` (sessions index `idx`). Returns (judgement, desire)."""
    comp = L['companies'].get(cid)
    pos = state['positions'].get(cid)
    held = pos is not None
    target = (L['target_weights'] or {}).get(cid, 0)
    snaps, flags = L.get('snapshots', {}), L.get('flags', [])
    reasons, aux, levels = [], [], set()
    price = comp['closes'].get(day) if comp else None
    fx = _fx(L, comp['currency'], day) if comp else None
    snap = snaps.get(day, {}).get(cid)
    flag = _active_flag(flags, cid, day)
    if comp is None or price is None:
        reasons.append('DATA_PRICE_MISSING')
    elif fx is None:
        reasons.append('DATA_FX_MISSING')
    if snap is None:
        reasons.append('DATA_SNAPSHOT_MISSING')
    elif snap['coverage'] == 'BLOCKED':
        reasons.append('COVERAGE_BLOCKED')
    if flag == 'EXCLUDE':
        reasons.append('USER_EXCLUDE')
    actual = 0
    if held and price is not None and fx is not None and total > 0:
        actual = pos['quantity'] * price * fx / total * 100
    if reasons:
        return _finish(['BLOCK'], reasons, aux, held, target, actual), None
    qg_now = _qg(snap)
    prev = _prev_snapshot(snaps, cid, day)
    qg_prev = _qg(prev)
    no_trade = False
    sell_all = False
    if qg_now is not None and qg_prev is not None and qg_prev - qg_now >= cfg['qg_decline_threshold']:
        levels.add('RISK_RECHECK'); reasons.append('QG_DECLINE')
        sell_all = held
    if prev is not None and prev['coverage'] == 'READY' and snap['coverage'] == 'PARTIAL':
        levels.add('RISK_RECHECK'); reasons.append('COVERAGE_WORSENED'); no_trade = True
    if flag == 'HOLD':
        levels.add('RISK_RECHECK'); reasons.append('USER_HOLD'); no_trade = True
    bench, basis = _sector_series(L, cid, cfg)
    drop = abnormal_drop(comp['closes'], bench, day, cfg)
    if basis == SP500 and cfg['sector_basis'] != 'SECTOR_ETF_CONFIRMED':
        aux.append('SECTOR_SP500_SUBSTITUTE')
    v_usable = drop['state'] != 'NOT_AVAILABLE'
    if not v_usable:
        reasons.append('RECHECK_BASIS_NOT_AVAILABLE')
    if drop['state'] == 'ABNORMAL':
        if flag == 'CONFIRMED_TEMPORARY':
            reasons.append('USER_CONFIRMED_TEMPORARY')
        else:
            levels.add('RISK_RECHECK'); reasons.append('RECHECK_ABNORMAL_DROP'); no_trade = True
            if flag == 'CONFIRMED_STRUCTURAL':
                reasons.append('USER_CONFIRMED_STRUCTURAL')
    # D-21 V slope: Q·G maintained (no decline beyond threshold over the lookback) and V moved by ≥ threshold.
    v_up = v_down = False
    lb = cfg['v_slope']['lookback_sessions']
    if v_usable and idx - lb >= 0:
        past = L['sessions'][idx - lb]
        v_now = L.get('v_scores', {}).get(day, {}).get(cid)
        v_past = L.get('v_scores', {}).get(past, {}).get(cid)
        qg_past = _qg(snaps.get(past, {}).get(cid))
        if v_now is not None and v_past is not None and qg_now is not None and qg_past is not None \
                and qg_now - qg_past > -cfg['qg_decline_threshold']:
            if v_now - v_past >= cfg['v_slope']['threshold']:
                v_up = True
            elif v_past - v_now >= cfg['v_slope']['threshold']:
                v_down = True
    band = cfg['band_pp']
    upper = target + band if v_up else target
    lower = target - band if v_down else target
    desire = None
    if 'RISK_RECHECK' in levels:
        if v_up:
            aux.append('INCREASE_CANDIDATE')
        if held and actual > target + band:
            aux.append('OVERWEIGHT')
        if sell_all and not no_trade:
            desire = ('SELL', actual, ['QG_DECLINE'])
    elif held and actual > target + band:
        levels.add('REDUCE_REVIEW'); reasons.append('OVERWEIGHT_GAP')
        if v_down:
            reasons.append('V_DETERIORATED')
        desire = ('SELL', actual - lower, ['OVERWEIGHT_GAP', 'V_DETERIORATED'] if v_down else ['OVERWEIGHT_GAP'])
    elif held and v_down and actual > lower:
        levels.add('REDUCE_REVIEW'); reasons.append('V_DETERIORATED')
        desire = ('SELL', actual - lower, ['V_DETERIORATED'])
    elif actual < target - band:
        levels.add('INCREASE_REVIEW'); reasons.append('UNDERWEIGHT_GAP')
        if v_up:
            reasons.append('V_IMPROVED')
        desire = ('BUY', upper - actual, ['UNDERWEIGHT_GAP', 'V_IMPROVED'] if v_up else ['UNDERWEIGHT_GAP'])
    elif v_up and actual < upper and target > 0:
        levels.add('INCREASE_REVIEW'); reasons.append('V_IMPROVED')
        desire = ('BUY', upper - actual, ['V_IMPROVED'])
    elif held:
        reasons.append('BAND_INSIDE')
    if snap['coverage'] == 'PARTIAL':
        levels.add('ADDITIONAL_REVIEW'); aux.append('COVERAGE_PARTIAL')
    for e in L.get('events', {}).get(day, {}).get(cid, []):
        levels.add('ADDITIONAL_REVIEW'); aux.append(e)
    if desire is not None and desire[1] <= 0:
        desire = None
    return _finish(sorted(levels, key=LEVELS.index), reasons, aux, held, target, actual), desire


def _finish(levels, reasons, aux, held, target, actual):
    if not levels:
        levels = ['HOLDING_CONTEXT' if held else 'OBSERVE']
    main = levels[0]
    chips = [lv for lv in levels[1:]]
    return {'main': main, 'symbol': SYMBOLS[main], 'aux_levels': chips, 'aux': aux, 'reason_codes': reasons,
            'held': held, 'target_weight': target, 'actual_weight': actual}


def _allocate(cands, limit, cfg):
    """Pro-rata share of `limit` by desired amount; floor to whole won; drop below the minimum trade."""
    total = 0
    for c in cands:
        total += c['desired']
    out = []
    for c in cands:
        amt = c['desired'] if total <= limit else limit * c['desired'] / total
        amt = math.floor(amt)
        codes = list(c['reason_codes'])
        if amt < math.floor(c['desired']):
            codes.append('LIMIT_EXHAUSTED')
        if amt < cfg['min_trade'] or amt <= 0:
            continue
        out.append({'company': c['company'], 'side': c['side'], 'amount': amt, 'reason_codes': codes})
    return out


def _value(L, state, day):
    """Positions value in base currency; carries the last close/FX on or before `day` (holidays) and lists those as stale."""
    total, stale = 0, []
    for cid in sorted(state['positions']):
        p = state['positions'][cid]
        comp = L['companies'][cid]
        d = _last_on_or_before(comp['closes'], day)
        rate, fd = 1, day
        if comp['currency'] != 'KRW':
            fs = L.get('fx', {}).get(comp['currency'], {})
            fd = _last_on_or_before(fs, day)
            rate = fs[fd] if fd is not None else None
        if d is None or rate is None:
            return None, [cid]
        if d != day or fd != day:
            stale.append(cid)
        total += p['quantity'] * comp['closes'][d] * rate
    return total, stale


def run_ledger(config, ledger):
    """Replay one ledger from config.start_date. Pure and deterministic; prices stay in the arguments."""
    cfg = validate_config(config)
    base = {'ledger_id': ledger.get('id') if isinstance(ledger, dict) else None, 'config_version': cfg.get('config_version'),
            'rules_version': cfg['rules_version'], 'status': cfg.get('status'), 'role': 'RAM_ONLY_DEVICE'}
    if cfg['start_date'] is None:
        return {**base, 'state': 'NOT_STARTED', 'reason_codes': ['START_DATE_NOT_SET'], 'days': [], 'trades': [], 'summary': None}
    try:
        L = _validate_ledger(ledger)
    except VirtualTradingInputError as e:
        return {**base, 'state': 'NOT_AVAILABLE', 'reason_codes': [str(e)], 'days': [], 'trades': [], 'summary': None}
    if L.get('target_weights') is None:
        return {**base, 'state': 'NOT_AVAILABLE', 'reason_codes': ['TARGET_NOT_AVAILABLE'], 'days': [], 'trades': [], 'summary': None}
    start = cfg['start_date']
    first = next((i for i, d in enumerate(L['sessions']) if d >= start), None)
    if first is None:
        return {**base, 'state': 'NOT_STARTED', 'reason_codes': ['NO_SESSION_ON_OR_AFTER_START'], 'days': [], 'trades': [], 'summary': None}
    init = L.get('initial', {'cash': 0, 'positions': {}})
    state = {'cash': init['cash'], 'positions': {k: {'quantity': v['quantity'], 'cost': v['cost']} for k, v in sorted(init['positions'].items())}}
    initial_value, _ = _value(L, state, L['sessions'][first])
    if initial_value is None:
        return {**base, 'state': 'NOT_AVAILABLE', 'reason_codes': ['INITIAL_VALUE_NOT_AVAILABLE'], 'days': [], 'trades': [], 'summary': None}
    initial_value += state['cash']
    fee_rate = cfg['cost_bps'] / 10000
    pending, days, trades = [], [], []
    deposits, realized, prev_total, growth = 0, 0, None, 1
    universe = sorted(set(L['target_weights']) | set(state['positions']))
    for idx in range(first, len(L['sessions'])):
        day = L['sessions'][idx]
        executed, cancelled = [], []
        for o in sorted(pending, key=lambda o: (0 if o['side'] == 'SELL' else 1, o['company'])):
            comp = L['companies'].get(o['company'])
            price = comp['closes'].get(day) if comp else None
            rate = _fx(L, comp['currency'], day) if comp else None
            if price is None or rate is None:
                cancelled.append({**o, 'cancel_reason': 'EXEC_PRICE_MISSING' if price is None else 'EXEC_FX_MISSING'})
                continue
            unit = price * rate
            if o['side'] == 'SELL':
                p = state['positions'].get(o['company'])
                if p is None:
                    cancelled.append({**o, 'cancel_reason': 'NO_POSITION'})
                    continue
                qty = o['amount'] / unit
                if qty >= p['quantity']:
                    qty = p['quantity']
                gross = qty * unit
                fee = gross * fee_rate
                avg = p['cost'] / p['quantity']
                cost_out = avg * qty
                pnl = gross - fee - cost_out
                realized += pnl
                state['cash'] += gross - fee
                if qty == p['quantity']:
                    del state['positions'][o['company']]
                else:
                    p['quantity'] -= qty
                    p['cost'] -= cost_out
                rec = {'date': day, 'decided_on': o['decided_on'], 'company': o['company'], 'side': 'SELL', 'amount': gross,
                       'quantity': qty, 'price': price, 'fx': rate, 'fee': fee, 'realized_pnl': pnl, 'reason_codes': o['reason_codes'],
                       'user_flag': o['user_flag']}
            else:
                amount = o['amount'] if o['amount'] <= state['cash'] else state['cash']
                if amount < cfg['min_trade'] or amount <= 0:
                    cancelled.append({**o, 'cancel_reason': 'CASH_INSUFFICIENT'})
                    continue
                fee = amount * fee_rate
                qty = (amount - fee) / unit
                p = state['positions'].setdefault(o['company'], {'quantity': 0, 'cost': 0})
                p['quantity'] += qty
                p['cost'] += amount
                state['cash'] -= amount
                rec = {'date': day, 'decided_on': o['decided_on'], 'company': o['company'], 'side': 'BUY', 'amount': amount,
                       'quantity': qty, 'price': price, 'fx': rate, 'fee': fee, 'realized_pnl': None, 'reason_codes': o['reason_codes'],
                       'user_flag': o['user_flag']}
            executed.append(rec)
            trades.append(rec)
        state['cash'] += cfg['daily_deposit']
        deposits += cfg['daily_deposit']
        pos_value, stale = _value(L, state, day)
        if pos_value is None:
            total = None
        else:
            total = pos_value + state['cash']
        if total is not None and prev_total is not None and prev_total > 0:
            growth = growth * ((total - cfg['daily_deposit']) / prev_total)
        judgements, sells, buys = {}, [], []
        if total is not None:
            for cid in universe:
                j, desire = _judge(L, cfg, cid, day, idx, state, total)
                judgements[cid] = j
                if desire is None:
                    continue
                side, pct, codes = desire
                desired = pct / 100 * total
                if side == 'SELL':
                    p = state['positions'][cid]
                    held_value = p['quantity'] * L['companies'][cid]['closes'][day] * _fx(L, L['companies'][cid]['currency'], day)
                    if desired > held_value:
                        desired = held_value
                flag = _active_flag(L.get('flags', []), cid, day)
                (sells if side == 'SELL' else buys).append({'company': cid, 'side': side, 'desired': desired, 'reason_codes': codes, 'user_flag': flag})
        orders = _allocate(sells, cfg['sell_limit'], cfg) + _allocate(buys, min(cfg['buy_limit'], state['cash']), cfg)
        flags_by = {c['company']: c['user_flag'] for c in sells + buys}
        pending = [{**o, 'decided_on': day, 'user_flag': flags_by[o['company']]} for o in orders]
        days.append({'date': day, 'executed': executed, 'cancelled': cancelled, 'deposit': cfg['daily_deposit'], 'cash': state['cash'],
                     'positions_value': pos_value, 'total_value': total, 'stale_valuation': stale,
                     'judgements': judgements, 'orders': [{k: o[k] for k in ('company', 'side', 'amount', 'reason_codes')} for o in pending]})
        if total is not None:
            prev_total = total
    last = days[-1]
    unrealized = None
    if last['positions_value'] is not None:
        cost = 0
        for cid in sorted(state['positions']):
            cost += state['positions'][cid]['cost']
        unrealized = last['positions_value'] - cost
    invested = initial_value + deposits
    summary = {'start_date': L['sessions'][first], 'end_date': last['date'], 'initial_value': initial_value, 'deposits': deposits,
               'total_value': last['total_value'], 'cash': state['cash'],
               'simple_return': None if last['total_value'] is None or invested <= 0 else last['total_value'] / invested - 1,
               'twr': growth - 1, 'realized_pnl': realized, 'unrealized_pnl': unrealized,
               'buy_count': sum(1 for t in trades if t['side'] == 'BUY'), 'sell_count': sum(1 for t in trades if t['side'] == 'SELL'),
               'user_flagged_count': sum(1 for t in trades if t['user_flag'] is not None),
               'pending_orders': days[-1]['orders']}
    return {**base, 'state': 'OK', 'reason_codes': [], 'days': days, 'trades': trades, 'summary': summary}


def evaluate_hits(config, ledger, trades):
    """D+N hit check per window vs the S&P 500: buy hits when the stock beats it, sell hits when the stock trails it."""
    cfg = validate_config(config)
    sessions = ledger['sessions']
    pos = {d: i for i, d in enumerate(sessions)}
    bench = ledger.get('benchmarks', {}).get(SP500)
    out = []
    for w in cfg['hit_windows']:
        samples = hits = pending = missing = 0
        for t in trades:
            i = pos.get(t['date'])
            if i is None or i + w >= len(sessions):
                pending += 1
                continue
            end = sessions[i + w]
            closes = ledger['companies'][t['company']]['closes']
            if bench is None or t['date'] not in closes or end not in closes or t['date'] not in bench or end not in bench:
                missing += 1
                continue
            rs = closes[end] / closes[t['date']] - 1
            rb = bench[end] / bench[t['date']] - 1
            samples += 1
            if (t['side'] == 'BUY' and rs > rb) or (t['side'] == 'SELL' and rs < rb):
                hits += 1
        enough = samples >= cfg['hit_min_samples']
        out.append({'window': w, 'samples': samples, 'hits': hits, 'pending': pending, 'missing': missing,
                     'state': 'OK' if enough else 'INSUFFICIENT_SAMPLE', 'hit_rate': hits / samples if enough else None})
    return out
