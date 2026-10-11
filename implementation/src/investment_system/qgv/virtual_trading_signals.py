"""Virtual trading signals v1: D-5 basis labels, device V history inputs and the rehearsal window (pure functions).

Python reference for web_assets/virtual-trading-signals.js (vectors: tests/fixtures/virtual_trading_signals_v1.json).
Nothing here fetches, stores or publishes prices, FX rates, ledgers or V scores; closes are arguments only.

- basis_rows: per company, the D-5 abnormal-drop basis exactly as the engine computes it on the ledger's last session
  (virtual_trading.abnormal_drop on virtual_trading._sector_series): which benchmark was used (the D-22 sector ETF, or
  S&P 500 when the ETF series is absent: the engine's fallback), whether the basis is NOT_AVAILABLE and why
  (HISTORY_INSUFFICIENT: fewer than lookback + window + 1 = 273 aligned closes, PRICE_NOT_ALIGNED,
  SECTOR_BASIS_NOT_AVAILABLE, DISTRIBUTION_DEGENERATE), the aligned close count, and whether the D-21 V slope can be
  evaluated (engine rule: basis usable, a session 20 ledger sessions back exists, V stored on both dates).
- v_progress: how far device V recording is from the 20-session V slope lookback.
- v_axis / v_scores_for / capture_plan: the device V score recorded per completed session. V = the PREVIEW V axis of
  the official v1 V weight copy (strategy_preview, missing factors not renormalized) over the device V factors
  (device_valuation.device_value_view) computed from that session's close. Rounded to 2 decimals.
- rehearsal_start / rehearsal_config: rehearsal (not recorded) runs the engine from the first of the last N completed
  SPY sessions (runner date rules), cash 0 + daily deposits, in RAM only.
"""
from __future__ import annotations

import math

from ..contracts.enums import QualityState
from ..contracts.models import FactorObservation
from . import virtual_trading as vt
from . import virtual_trading_inputs as vi
from .device_valuation import device_value_view
from .strategy_preview import recalculate_strategy_preview

SCHEMA = 'virtual-trading-signals/1'
REHEARSAL_WINDOW = 5
SP500 = 'SP500'
LEDGER_KINDS = ('SET_A', 'SET_B', 'SHADOW')


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def round2(v):
    """Half-up to 2 decimals, same float steps as the JS port (x - floor(x) is exact for doubles)."""
    y = v * 100
    n = math.floor(y)
    return (n + (1 if y - n >= 0.5 else 0)) / 100


def rehearsal_start(histories, window=REHEARSAL_WINDOW):
    """First of the last `window` completed SPY sessions (same close rules as the runner), or None without SPY."""
    if not (type(window) is int and window >= 1):
        return None
    closes, code = vi.series_from_history((histories or {}).get(vi.SP500_SYMBOL), vi.SP500_SYMBOL, 'USD')
    if code is not None:
        return None
    sessions = sorted(closes)
    return sessions[max(0, len(sessions) - window)]


def rehearsal_config(histories, config, window=REHEARSAL_WINDOW):
    """Engine config for a rehearsal: only start_date moves; every rule value stays as configured."""
    start = rehearsal_start(histories, window)
    out = dict(config)
    if start is not None:
        out['start_date'] = start
    return out


def rehearsal_snapshot(qg_rows):
    """Today's public Q·G screen rows {cid: {q, g, partial}} → engine snapshot rows (rehearsal only)."""
    out = {}
    for cid in sorted(qg_rows if isinstance(qg_rows, dict) else {}):
        r = qg_rows[cid]
        if cid not in vi.TARGETS or not isinstance(r, dict):
            continue
        q, g = r.get('q'), r.get('g')
        q, g = (q if _num(q) else None), (g if _num(g) else None)
        out[cid] = {'q': q, 'g': g, 'coverage': 'BLOCKED' if q is None or g is None else 'PARTIAL' if r.get('partial') is True else 'READY'}
    return out


def apply_rehearsal_snapshots(assembled, qg_rows):
    """Rehearsal: window sessions without a RECORDED forward-ledger snapshot use today's public Q·G screen snapshot.
    Returns (assembled with filled snapshots, sorted filled session dates)."""
    rows = rehearsal_snapshot(qg_rows)
    if not isinstance(assembled, dict) or not rows:
        return assembled, []
    out = dict(assembled, ledgers=dict(assembled.get('ledgers') or {}))
    filled = set()
    for kind, entry in out['ledgers'].items():
        if not (isinstance(entry, dict) and entry.get('state') == 'READY'):
            continue
        snaps = dict(entry['input'].get('snapshots') or {})
        for d in entry['input']['sessions']:
            if d not in snaps:
                snaps[d] = rows
                filled.add(d)
        out['ledgers'][kind] = dict(entry, input=dict(entry['input'], snapshots=dict(sorted(snaps.items()))))
    return out, sorted(filled)


def basis_rows(ledger_input, config):
    """D-5 basis per company on the ledger's last session (labels only: no price, no z value)."""
    L = ledger_input
    if not isinstance(L, dict) or not L.get('sessions'):
        return {}
    sessions = L['sessions']
    day, idx = sessions[-1], len(sessions) - 1
    a, lb = config['abnormal_drop'], config['v_slope']['lookback_sessions']
    needed = a['lookback_sessions'] + a['window_sessions'] + 1
    v_scores = L.get('v_scores') or {}
    past = sessions[idx - lb] if idx - lb >= 0 else None
    out = {}
    for cid in sorted(L['companies']):
        comp = L['companies'][cid]
        requested = comp.get('sector_benchmark') if config['sector_basis'] == 'SECTOR_ETF_CONFIRMED' else None
        requested = requested or SP500
        bench, used = vt._sector_series(L, cid, config)
        drop = vt.abnormal_drop(comp['closes'], bench, day, config)
        aligned = 0 if bench is None else sum(1 for d in comp['closes'] if d <= day and d in bench)
        v_now = (v_scores.get(day) or {}).get(cid)
        v_past = (v_scores.get(past) or {}).get(cid) if past is not None else None
        if drop['state'] == 'NOT_AVAILABLE':
            v_state = 'BASIS_NOT_AVAILABLE'
        elif v_now is not None and v_past is not None:
            v_state = 'READY'
        else:
            v_state = 'V_HISTORY_SHORT'
        out[cid] = {'requested': requested, 'benchmark': used, 'fallback': requested != SP500 and used == SP500,
                    'state': drop['state'], 'reason': drop['reason'], 'aligned': aligned, 'needed': needed, 'v_slope': v_state}
    return out


def v_progress(sessions, v_scores, lookback):
    """Sessions elapsed since the first stored V date (SPY sessions when known, else stored dates), against lookback."""
    dates = sorted(d for d, row in (v_scores or {}).items() if vi._day(d) and isinstance(row, dict) and row)
    if not dates:
        return {'state': 'NOT_RECORDED', 'first': None, 'last': None, 'recorded': 0, 'elapsed': 0, 'needed': lookback}
    first = dates[0]
    elapsed = sum(1 for s in sessions if s > first) if sessions else len(dates) - 1
    return {'state': 'READY' if elapsed >= lookback else 'COLLECTING', 'first': first, 'last': dates[-1],
            'recorded': len(dates), 'elapsed': elapsed, 'needed': lookback}


def v_axis(view):
    """PREVIEW V axis (official v1 V weight copy, no renormalization) over the available device V factors."""
    factors = view.get('v_factors') if isinstance(view, dict) else None
    if not isinstance(factors, dict):
        return None
    observations = {k: FactorObservation(k, None, f['score'], QualityState.OK, None) for k, f in factors.items()
                    if isinstance(f, dict) and f.get('state') != 'NOT_AVAILABLE' and _num(f.get('score'))}
    if not observations:
        return None
    score = recalculate_strategy_preview(observations).axes['V'].score
    return score if _num(score) else None


def _valuation_row(valuation, cid):
    try:
        rows = valuation['data']['companies']
    except (TypeError, KeyError):
        return None
    return rows.get(cid) if isinstance(rows, dict) else None


def capture_plan(assembled):
    """Latest completed SPY session and the companies (closes, currency) of every READY ledger, or None."""
    if not isinstance(assembled, dict) or assembled.get('state') != 'READY':
        return None
    day, companies = None, {}
    for kind in LEDGER_KINDS:
        entry = (assembled.get('ledgers') or {}).get(kind)
        if not (isinstance(entry, dict) and entry.get('state') == 'READY'):
            continue
        spy = entry['input']['benchmarks'].get(SP500) or {}
        if spy:
            last = max(spy)
            day = last if day is None or last > day else day
        for cid, comp in entry['input']['companies'].items():
            companies.setdefault(cid, comp)
    if day is None:
        return None
    return {'date': day, 'companies': {cid: companies[cid] for cid in sorted(companies)}}


def v_scores_for(plan, valuation, parameters):
    """V per company on plan['date'] from that session's close (absent close or V → absent, never 0)."""
    out, raw = {}, {}
    if not plan:
        return out, raw
    day = plan['date']
    for cid, comp in plan['companies'].items():
        close = comp['closes'].get(day)
        row = _valuation_row(valuation, cid)
        if close is None or row is None:
            continue
        view = device_value_view(row=row, quote={'price': close, 'currency': comp['currency']}, parameters=parameters)
        v = v_axis(view)
        if v is not None and 0 <= v <= 100:
            raw[cid] = v
            out[cid] = round2(v)
    return out, raw


def with_v_scores(assembled, store):
    """The assembled result with every READY ledger's v_scores re-read from the (updated) device store."""
    if not isinstance(assembled, dict):
        return assembled
    scores = vi.v_scores_from_store(store)
    out = dict(assembled, ledgers=dict(assembled.get('ledgers') or {}))
    for kind, entry in out['ledgers'].items():
        if isinstance(entry, dict) and entry.get('state') == 'READY':
            out['ledgers'][kind] = dict(entry, input=dict(entry['input'], v_scores=scores))
    return out


def report_signals(assembled, kind, config, store):
    """S17 signals for one ledger tab: D-5 basis rows on the last session and V recording progress."""
    lb = config['v_slope']['lookback_sessions']
    entry = ((assembled or {}).get('ledgers') or {}).get(kind) if isinstance(assembled, dict) else None
    if isinstance(entry, dict) and entry.get('state') == 'READY':
        L = entry['input']
        sessions = sorted(L['benchmarks'].get(SP500) or {})
        return {'schema': SCHEMA, 'date': L['sessions'][-1] if L['sessions'] else None,
                'basis': basis_rows(L, config), 'v_progress': v_progress(sessions, L.get('v_scores'), lb)}
    return {'schema': SCHEMA, 'date': None, 'basis': {}, 'v_progress': v_progress([], vi.v_scores_from_store(store), lb)}
