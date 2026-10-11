"""Virtual ledger sheet storage v1 (D-10): pure row format, replay verification and missing-session plan.

Python reference for the pure part of web_assets/virtual-ledger-sheets.js (vectors:
tests/fixtures/virtual_ledger_sheets_v1.json). The device keeps prices in RAM and writes the virtual ledgers only to
the user's own Google Sheet (tabs VirtualA / VirtualB / VirtualMine / VirtualMeta / VirtualFlags) on an explicit
click. This module only defines, for the same synthetic inputs, which rows the device must write and how recorded
rows are checked by deterministic replay. Nothing here fetches, stores or publishes prices, ledgers or holdings.

Rules:
- Ledger rows are append-only. A session counts as recorded when its rows are in the ledger tab; recorded rows must
  equal, cell for cell, the rows the engine reproduces from the same inputs (else LEDGER_REPLAY_MISMATCH, no writes).
- Missing sessions are the replayed sessions after the last recorded one, up to the latest session whose public Q·G
  record exists (inputs final). A day whose inputs are missing is written with the engine's own outcome
  (NOT_AVAILABLE valuation, BLOCK judgements, EXEC_*_MISSING cancellations); nothing is skipped or filled.
- Every ledger has a fixed definition (VirtualMeta LEDGER_START): begin date, target weights and, for the shadow
  ledger, the actual-holdings snapshot it started from (D-17). A changed Set B or a re-sync closes the ledger
  (LEDGER_CLOSE) and starts a new one; recorded rows are never rewritten.
- Numbers are written as text in the ECMAScript Number-to-String form so the device and this reference agree exactly.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import math
import re

from . import virtual_trading as vt
from . import virtual_trading_inputs as vi

SCHEMA = 'virtual-ledger-sheets/1'
TABS = {'SET_A': 'VirtualA', 'SET_B': 'VirtualB', 'SHADOW': 'VirtualMine'}
META = 'VirtualMeta'
FLAGS = 'VirtualFlags'
LEDGER_HEAD = ('ledger_id', 'session_date', 'row_type', 'company', 'level', 'aux_levels', 'reason_codes', 'aux_codes',
               'side', 'amount', 'quantity', 'price_used', 'fx_used', 'cash_after', 'total_value')
META_HEAD = ('recorded_at', 'ledger_id', 'kind', 'event', 'start_date', 'end_date', 'config_version', 'engine_version',
             'last_recorded_session', 'inputs_sha256', 'payload')
FLAGS_HEAD = ('created_at', 'date', 'company', 'kind')
HEADS = {'VirtualA': LEDGER_HEAD, 'VirtualB': LEDGER_HEAD, 'VirtualMine': LEDGER_HEAD, META: META_HEAD, FLAGS: FLAGS_HEAD}
ROW_TYPES = ('INITIAL', 'EXECUTED', 'CANCELLED', 'JUDGEMENT', 'ORDER', 'SUMMARY')
EVENTS = ('LEDGER_START', 'LEDGER_CLOSE', 'RECORD', 'USER_TARGET')
KINDS = ('SET_A', 'SET_B', 'SHADOW')
BASES = ('TARGET_V0', 'SET_B', 'USER_TARGET')
NA = 'NOT_AVAILABLE'
ID = re.compile(r'(?:set_a|set_b-[1-9][0-9]{0,5}|shadow-[1-9][0-9]{0,5})')
WEIGHT_TEXT = re.compile(r'(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?')
SHA = re.compile(r'[0-9a-f]{64}')
SERIAL_EPOCH = date(1899, 12, 30)


class SheetError(ValueError):
    pass


def _fail(code):
    raise SheetError(code)


# ---------- text form ----------

def num_str(x):
    """ECMAScript Number::toString for a finite number (shortest round-trip digits)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        _fail('NUMBER_INVALID')
    if isinstance(x, int):
        if abs(x) < 10 ** 21:
            return str(x)
        x = float(x)
    if not math.isfinite(x):
        _fail('NUMBER_INVALID')
    if x == 0:
        return '0'
    if x < 0:
        return '-' + num_str(-x)
    mantissa, _, exponent = repr(x).partition('e')
    whole, _, frac = mantissa.partition('.')
    text = whole + frac
    stripped = text.lstrip('0')
    digits = stripped.rstrip('0')
    trailing = len(stripped) - len(digits)
    k = len(digits)
    n = k + trailing + (int(exponent) if exponent else 0) - len(frac)
    if k <= n <= 21:
        return digits + '0' * (n - k)
    if 0 < n <= 21:
        return digits[:n] + '.' + digits[n:]
    if -6 < n <= 0:
        return '0.' + '0' * (-n) + digits
    e = n - 1
    return digits[0] + ('.' + digits[1:] if k > 1 else '') + 'e' + ('+' if e >= 0 else '-') + str(abs(e))


def canonical(v):
    """Canonical JSON: sorted keys, no spaces, numbers in num_str form (same text as the device)."""
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return num_str(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return '[' + ','.join(canonical(x) for x in v) + ']'
    if isinstance(v, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + canonical(v[k]) for k in sorted(v)) + '}'
    _fail('VALUE_INVALID')


def _codes(values):
    return ','.join(values or [])


def _n(v):
    return '' if v is None else num_str(v)


# ---------- ledger rows (one engine day → rows) ----------

def day_rows(ledger_id, day, initial=None):
    rows = []
    for cid in sorted((initial or {}).get('positions', {})):
        p = initial['positions'][cid]
        rows.append([ledger_id, day['date'], 'INITIAL', cid, '', '', '', '', '', num_str(p['cost']), num_str(p['quantity']), '', '', '', ''])
    for t in day['executed']:
        rows.append([ledger_id, day['date'], 'EXECUTED', t['company'], '', '', _codes(t['reason_codes']), t.get('user_flag') or '',
                     t['side'], num_str(t['amount']), num_str(t['quantity']), num_str(t['price']), num_str(t['fx']), '', ''])
    for o in day['cancelled']:
        rows.append([ledger_id, day['date'], 'CANCELLED', o['company'], '', '', o['cancel_reason'], _codes(o['reason_codes']),
                     o['side'], num_str(o['amount']), '', '', '', '', ''])
    for cid in sorted(day['judgements']):
        j = day['judgements'][cid]
        rows.append([ledger_id, day['date'], 'JUDGEMENT', cid, j['main'], _codes(j['aux_levels']), _codes(j['reason_codes']),
                     _codes(j['aux']), '', '', '', '', '', '', ''])
    for o in day['orders']:
        rows.append([ledger_id, day['date'], 'ORDER', o['company'], '', '', _codes(o['reason_codes']), '', o['side'],
                     num_str(o['amount']), '', '', '', '', ''])
    total = day['total_value']
    rows.append([ledger_id, day['date'], 'SUMMARY', _codes(day['stale_valuation']), '', '',
                 'VALUATION_NOT_AVAILABLE' if total is None else '', '', '', num_str(day['deposit']), '', '', '',
                 num_str(day['cash']), NA if total is None else num_str(total)])
    return rows


def ledger_rows(ledger_id, result, ledger_input, dates):
    """Rows for the replayed days whose date is in `dates` (INITIAL rows go with the ledger's first day)."""
    wanted, out = set(dates), []
    for i, day in enumerate(result['days']):
        if day['date'] in wanted:
            out.extend(day_rows(ledger_id, day, ledger_input.get('initial') if i == 0 else None))
    return out


# ---------- reading tabs ----------

def parse_tab(values, head):
    """Sheet values (first row = header) → padded string rows. Header differs → SHEET_HEADER_MISMATCH."""
    if not isinstance(values, list):
        _fail('SHEET_ROWS_INVALID')
    if not values:
        return {'header': False, 'rows': []}
    if list(values[0]) != list(head):
        _fail('SHEET_HEADER_MISMATCH')
    rows = []
    for raw in values[1:]:
        if not isinstance(raw, list) or not raw or len(raw) > len(head) or any(not isinstance(c, str) for c in raw):
            _fail('SHEET_ROWS_INVALID')
        rows.append(list(raw) + [''] * (len(head) - len(raw)))
    return {'header': True, 'rows': rows}


def group_ledger_rows(rows):
    """Ledger tab rows → {ledger_id: [rows]} in sheet order; dates must not go back within one ledger."""
    out = {}
    for r in rows:
        if not ID.fullmatch(r[0]) or not vi._day(r[1]) or r[2] not in ROW_TYPES:
            _fail('SHEET_ROWS_INVALID')
        prev = out.get(r[0])
        if prev and prev[-1][1] > r[1]:
            _fail('SHEET_ROWS_INVALID')
        out.setdefault(r[0], []).append(r)
    return out


def recorded_dates(rows):
    out = []
    for r in rows:
        if not out or out[-1] != r[1]:
            out.append(r[1])
    return out


def _weights(w, allowed=None):
    if not isinstance(w, dict) or not w:
        return False
    for k, v in w.items():
        if not (k in vi.TARGETS and (allowed is None or k in allowed) and vi._num(v) and 0 <= v <= 100):
            return False
    total = 0
    for k in sorted(w):
        total += w[k]
    return total <= 100 + 1e-9


def _snapshot_ok(s):
    return (isinstance(s, dict) and isinstance(s.get('effective_at'), str) and isinstance(s.get('positions'), dict)
            and all(k in vi.TARGETS and isinstance(p, dict) for k, p in s['positions'].items()))


def parse_meta(rows):
    """VirtualMeta rows → ledger definitions (in start order), latest user target and latest RECORD per ledger."""
    ledgers, order, records, target = {}, [], {}, None
    for i, r in enumerate(rows):
        ev = dict(zip(META_HEAD, r))
        try:
            payload = json.loads(ev['payload']) if ev['payload'] else {}
        except ValueError:
            return {'state': 'META_INVALID', 'reason_codes': ['META_ROW_INVALID'], 'row': i}
        ok = isinstance(payload, dict)
        event, lid, kind = ev['event'], ev['ledger_id'], ev['kind']
        if ok and event == 'LEDGER_START':
            basis, weights = payload.get('target_basis'), payload.get('target_weights')
            ok = (ID.fullmatch(lid) is not None and lid not in ledgers and kind in KINDS and lid.startswith({'SET_A': 'set_a', 'SET_B': 'set_b-', 'SHADOW': 'shadow-'}[kind])
                  and vi._day(ev['start_date']) and ev['end_date'] == '' and basis in BASES and _weights(weights)
                  and (kind != 'SHADOW' or _snapshot_ok(payload.get('snapshot'))))
            if ok:
                ledgers[lid] = {'id': lid, 'kind': kind, 'begin': ev['start_date'], 'end': None, 'target_basis': basis,
                                'target_weights': weights, 'snapshot': payload.get('snapshot') if kind == 'SHADOW' else None,
                                'config_version': ev['config_version'], 'engine_version': ev['engine_version'],
                                'reason': payload.get('reason') if isinstance(payload.get('reason'), str) else None}
                order.append(lid)
        elif ok and event == 'LEDGER_CLOSE':
            led = ledgers.get(lid)
            ok = (led is not None and led['kind'] == kind and led['end'] is None and vi._day(ev['end_date'])
                  and ev['end_date'] >= led['begin'])
            if ok:
                led['end'] = ev['end_date']
        elif ok and event == 'RECORD':
            ok = lid in ledgers and ledgers[lid]['kind'] == kind and vi._day(ev['last_recorded_session']) and SHA.fullmatch(ev['inputs_sha256']) is not None
            if ok:
                records[lid] = {'session': ev['last_recorded_session'], 'sha256': ev['inputs_sha256']}
        elif ok and event == 'USER_TARGET':
            w = payload.get('target_weights')
            ok = lid == '' and kind == 'TARGET' and (w is None or _weights(w))
            if ok:
                target = w
        else:
            ok = False
        if not ok:
            return {'state': 'META_INVALID', 'reason_codes': ['META_ROW_INVALID'], 'row': i}
    return {'state': 'OK', 'reason_codes': [], 'ledgers': [ledgers[k] for k in order], 'records': records, 'user_target': target}


def active(meta, kind):
    """Latest open ledger of a kind, else None."""
    found = None
    for led in meta['ledgers']:
        if led['kind'] == kind and led['end'] is None:
            found = led
    return found


def set_a_ledger(meta, base_input, config):
    """The Set A ledger: its stored definition, else the implicit one (start date, TARGET v0 from the catalog)."""
    for led in meta['ledgers']:
        if led['id'] == 'set_a':
            return led
    return {'id': 'set_a', 'kind': 'SET_A', 'begin': config['start_date'], 'end': None, 'target_basis': 'TARGET_V0',
            'target_weights': dict(base_input['target_weights']), 'snapshot': None, 'implicit': True,
            'config_version': config.get('config_version'), 'engine_version': config['rules_version'], 'reason': None}


def next_id(meta, kind):
    prefix = {'SET_B': 'set_b-', 'SHADOW': 'shadow-'}[kind]
    return prefix + str(1 + sum(1 for led in meta['ledgers'] if led['kind'] == kind))


# ---------- weights / flags input ----------

def validate_weights(raw, allowed):
    """User weights {cid: text|number} → OK (positive entries), NOT_AVAILABLE (nothing entered) or INVALID."""
    if not isinstance(raw, dict):
        return {'state': 'INVALID', 'reason_codes': ['WEIGHT_INVALID'], 'weights': None}
    out = {}
    for cid in sorted(raw):
        v = raw[cid]
        if v is None or (isinstance(v, str) and v.strip() == ''):
            continue
        if cid not in allowed:
            return {'state': 'INVALID', 'reason_codes': ['COMPANY_NOT_SUPPORTED'], 'weights': None}
        if isinstance(v, str):
            if not WEIGHT_TEXT.fullmatch(v.strip()):
                return {'state': 'INVALID', 'reason_codes': ['WEIGHT_INVALID'], 'weights': None}
            v = float(v.strip())
        elif isinstance(v, bool) or not vi._num(v):
            return {'state': 'INVALID', 'reason_codes': ['WEIGHT_INVALID'], 'weights': None}
        if not 0 <= v <= 100:
            return {'state': 'INVALID', 'reason_codes': ['WEIGHT_INVALID'], 'weights': None}
        if v > 0:
            out[cid] = int(v) if float(v).is_integer() else v
    if not out:
        return {'state': NA, 'reason_codes': ['WEIGHTS_EMPTY'], 'weights': None}
    total = 0
    for k in sorted(out):
        total += out[k]
    if total > 100 + 1e-9:
        return {'state': 'INVALID', 'reason_codes': ['WEIGHT_SUM_OVER_100'], 'weights': None}
    return {'state': 'OK', 'reason_codes': [], 'weights': out}


def _flag_date(v):
    if isinstance(v, str) and vi._day(v.strip()):
        return v.strip()
    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 1 <= v < 2958466 and float(v).is_integer():
        return (SERIAL_EPOCH + timedelta(days=int(v))).isoformat()
    return None


def parse_flags(values):
    """VirtualFlags values (the user may type rows): valid rows → engine flags; others are counted and ignored."""
    if not isinstance(values, list) or not values:
        return {'flags': [], 'ignored': 0}
    if list(values[0]) != list(FLAGS_HEAD):
        _fail('SHEET_HEADER_MISMATCH')
    by_ticker = {t: cid for cid, t in vi.TARGETS.items()}
    flags, ignored = [], 0
    for raw in values[1:]:
        row = list(raw) + [''] * (4 - len(raw)) if isinstance(raw, list) else None
        if row is None or not any(c not in ('', None) for c in row):
            continue
        d = _flag_date(row[1])
        company = row[2].strip() if isinstance(row[2], str) else ''
        cid = company if company in vi.TARGETS else by_ticker.get(company.upper())
        kind = row[3].strip().upper() if isinstance(row[3], str) else ''
        if d is None or cid is None or kind not in vi.FLAG_KINDS:
            ignored += 1
            continue
        flags.append({'date': d, 'company': cid, 'kind': kind})
    return {'flags': flags, 'ignored': ignored}


# ---------- ledger inputs ----------

def recordable_through(base_input):
    """Latest session whose public Q·G record exists (its inputs are final), else None."""
    if not base_input or not base_input['sessions']:
        return None
    last = base_input['sessions'][-1]
    days = [d for d in base_input.get('snapshots', {}) if d <= last]
    return max(days) if days else None


def derive_input(base_input, ledger):
    """Engine input for one ledger from the assembled Set A input: its sessions [begin, end), its fixed target weights
    and, for the shadow ledger, the stored snapshot with KRW cost by the runner's FX rule (rate on or before the
    ledger's first session)."""
    sessions = [d for d in base_input['sessions'] if d >= ledger['begin'] and (ledger['end'] is None or d < ledger['end'])]
    initial = {'cash': 0, 'positions': {}}
    if ledger['kind'] == 'SHADOW':
        positions = ledger['snapshot'].get('positions') if isinstance(ledger.get('snapshot'), dict) else {}
        held = {cid: p for cid, p in sorted((positions or {}).items())
                if cid in base_input['companies'] and isinstance(p, dict) and vi._num(p.get('quantity')) and p['quantity'] > 0}
        if not held:
            return {'state': NA, 'reason_codes': ['NO_ACTUAL'], 'input': None}
        if any(not (vi._num(p.get('average_cost')) and p['average_cost'] >= 0 and p.get('currency') in vi.CURRENCIES) for p in held.values()):
            return {'state': NA, 'reason_codes': ['ACTUAL_INVALID'], 'input': None}
        if sessions:
            for cid, p in held.items():
                rate = 1 if p['currency'] == 'KRW' else vi._rate_on_or_before(base_input['fx'].get(p['currency'], {}), sessions[0])
                if rate is None:
                    return {'state': NA, 'reason_codes': ['INITIAL_COST_FX_MISSING'], 'input': None}
                initial['positions'][cid] = {'quantity': p['quantity'], 'cost': p['quantity'] * p['average_cost'] * rate}
    out = dict(base_input)
    out.update({'id': ledger['id'], 'kind': ledger['kind'], 'sessions': sessions, 'target_weights': dict(ledger['target_weights']),
                'initial': initial})
    return {'state': 'READY', 'reason_codes': [], 'input': out}


def truncate(ledger_input, last):
    """The part of a ledger input that the sessions up to `last` depend on (for the inputs hash)."""
    def cut(series):
        return {k: v for k, v in series.items() if k <= last}
    return {'id': ledger_input['id'], 'kind': ledger_input['kind'], 'sessions': [d for d in ledger_input['sessions'] if d <= last],
            'target_weights': ledger_input['target_weights'], 'initial': ledger_input.get('initial', {'cash': 0, 'positions': {}}),
            'companies': {cid: {'currency': c['currency'], 'sector_benchmark': c.get('sector_benchmark'), 'closes': cut(c['closes'])}
                          for cid, c in ledger_input['companies'].items()},
            'benchmarks': {k: cut(v) for k, v in ledger_input.get('benchmarks', {}).items()},
            'fx': {k: cut(v) for k, v in ledger_input.get('fx', {}).items()},
            'snapshots': cut(ledger_input.get('snapshots', {})), 'v_scores': cut(ledger_input.get('v_scores', {})),
            'flags': [f for f in ledger_input.get('flags', []) if f['date'] <= last], 'events': cut(ledger_input.get('events', {}))}


def inputs_text(ledger_input, last):
    return canonical(truncate(ledger_input, last))


# ---------- replay verification + missing sessions ----------

def ledger_status(ledger, base_input, recorded, config, through):
    """Verify one ledger's recorded rows by replay and list the sessions still to write (pure, deterministic)."""
    out = {'id': ledger['id'], 'kind': ledger['kind'], 'tab': TABS[ledger['kind']], 'begin': ledger['begin'], 'end': ledger['end'],
           'target_basis': ledger['target_basis'], 'state': 'OK', 'reason_codes': [], 'recorded_sessions': 0,
           'recorded_through': None, 'missing': [], 'first_mismatch': None, 'append_rows': [], 'replay_through': None}
    dates = recorded_dates(recorded)
    out['recorded_sessions'] = len(dates)
    out['recorded_through'] = dates[-1] if dates else None
    derived = derive_input(base_input, ledger)
    if derived['state'] != 'READY':
        out.update(state='LEDGER_REPLAY_MISMATCH' if dates else NA, reason_codes=list(derived['reason_codes']))
        if dates:
            out['first_mismatch'] = {'session': dates[0], 'row': 0}
        return out, None
    inp = derived['input']
    result = vt.run_ledger(config, inp)
    replay = [d['date'] for d in result['days']] if result['state'] == 'OK' else []
    out['replay_through'] = replay[-1] if replay else None
    if result['state'] != 'OK':
        if dates:
            out.update(state='LEDGER_REPLAY_MISMATCH', reason_codes=list(result['reason_codes']), first_mismatch={'session': dates[0], 'row': 0})
        else:
            out.update(state=result['state'], reason_codes=list(result['reason_codes']))
        return out, inp
    expected = ledger_rows(ledger['id'], result, inp, dates)
    if replay[:len(dates)] != dates or expected != recorded:
        i = 0
        while i < len(recorded) and i < len(expected) and recorded[i] == expected[i]:
            i += 1
        session = recorded[i][1] if i < len(recorded) else (expected[i][1] if i < len(expected) else dates[-1])
        out.update(state='LEDGER_REPLAY_MISMATCH', reason_codes=['LEDGER_REPLAY_MISMATCH'], first_mismatch={'session': session, 'row': i})
        return out, inp
    missing = [d for d in replay[len(dates):] if through is not None and d <= through]
    out['missing'] = missing
    out['append_rows'] = ledger_rows(ledger['id'], result, inp, missing)
    if not missing and len(replay) > len(dates):
        out['reason_codes'] = ['WAITING_FOR_QG_RECORD']
    return out, inp


# ---------- VirtualMeta rows ----------

def start_row(now, ledger, config, payload):
    return [now, ledger['id'], ledger['kind'], 'LEDGER_START', ledger['begin'], '', config.get('config_version') or '',
            config['rules_version'], '', '', canonical(payload)]


def close_row(now, ledger, end, payload):
    return [now, ledger['id'], ledger['kind'], 'LEDGER_CLOSE', '', end, '', '', '', '', canonical(payload)]


def record_row(now, status, config, sha256, rows):
    return [now, status['id'], status['kind'], 'RECORD', '', '', config.get('config_version') or '', config['rules_version'],
            status['missing'][-1], sha256, canonical({'rows': rows, 'sessions': len(status['missing'])})]


def target_row(now, weights):
    return [now, '', 'TARGET', 'USER_TARGET', '', '', '', '', '', '', canonical({'target_weights': weights})]


def _next_day(d):
    return (date.fromisoformat(d) + timedelta(days=1)).isoformat()


def begin_for(now, config, previous_last=None):
    """First session date of a new ledger defined at instant `now`: its New York date (the runner's shadow rule), not
    before the start date and after the last recorded session of the ledger it replaces."""
    begin = vi.eastern_date(now)
    if config['start_date'] and begin < config['start_date']:
        begin = config['start_date']
    if previous_last and begin <= previous_last:
        begin = _next_day(previous_last)
    return begin


def replace_rows(meta, kind, now, config, payload, recorded_last=None, reason='INITIAL'):
    """Meta rows for a new Set B / shadow ledger: LEDGER_CLOSE of the open one (if any) then LEDGER_START."""
    old = active(meta, kind)
    begin = begin_for(now, config, recorded_last if old else None)
    new = {'id': next_id(meta, kind), 'kind': kind, 'begin': begin}
    rows = []
    if old is not None:
        rows.append(close_row(now, old, begin, {'next': new['id'], 'reason': reason}))
    body = dict(payload)
    body['reason'] = reason
    if old is not None:
        body['previous'] = old['id']
    rows.append(start_row(now, new, config, body))
    return rows


def now_iso(dt=None):
    return (dt or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
