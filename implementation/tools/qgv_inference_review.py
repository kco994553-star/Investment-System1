#!/usr/bin/env python3
"""Public V price-inference review (lane B-2, 2026-10-23). SYNTHETIC ONLY.

An independent attacker model against the public central V (qgv-official.json fields of
docs/qgv_scoring_standard/CENTRAL_V_PUBLICATION_DESIGN_20261018.md §4) plus the public SEC V inputs
(sec-qgv2.json v_inputs_v2) plus public market knowledge (other names' prices, past month-end closes).

The engine (investment_system.qgv.qgv_v2.score_universe) is imported and run unchanged on a synthetic universe
(NYSE:SYNnnn codes, generated fundamentals and prices). Nothing here reads a real price, a provider, a key or a
network resource, and nothing is written except the optional --json summary path given on the command line.

Attack model (exact, not sampled): every public V value is a mid-rank percentile, so for one target name all
public fields are step functions of that name's own price P, with the steps at "break prices" where the target's
yield / expectation gap / own-history yield crosses another known value. The tool lists every break price inside
a [P/20, 20P] window, evaluates the public view on each segment and keeps the segments that reproduce what was
published. The hull of those segments is the attacker's price interval. An attacker who knows only part of the
other prices gets percentile ranges instead of points (interval arithmetic).

Usage: qgv_inference_review.py [--n 500] [--seed 20261023] [--rounds 5] [--days 20] [--daily-sample 80] [--sample 0] [--json PATH]
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from investment_system.qgv import qgv_v2 as engine  # noqa: E402  (read-only use; never patched)
from investment_system.qgv.dcf import reverse_dcf, two_stage_dcf  # noqa: E402
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters  # noqa: E402
from investment_system.qgv.type_config import load_official_type_config  # noqa: E402

SEED = 20261023
WINDOW = 20.0                      # search window [P/20, 20P]; a hull touching it counts as unbounded on that side
EPS = 1e-9
V_IDS = tuple(engine.WEIGHTS['V'])
CROSS = ('v_earnings_yield', 'v_fcf_yield', 'v_vs_industry', 'v_expectation_check')
PRICE_DEPENDENT = frozenset({'EV_NON_POSITIVE', 'ROOT_NOT_BRACKETED', 'ROOT_NOT_CONVERGED', 'NUMERIC_OVERFLOW'})
GROUPED = 'PRICE_DEPENDENT_NOT_COMPUTABLE'
Q_IDS = tuple(engine.WEIGHTS['Q'])
G_IDS = tuple(engine.WEIGHTS['G'])


# ----------------------------------------------------------------------------------------------------------------
# Synthetic universe
# ----------------------------------------------------------------------------------------------------------------

def _month_end(y, m):
    return '%04d-%02d-%02d' % (y, m, calendar.monthrange(y, m)[1])


def _months(start=(2019, 1), end=(2026, 9)):
    y, m = start
    out = []
    while (y, m) <= end:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def synthetic_universe(seed=SEED, n=500):
    """(companies, quotes, sec_view). companies/quotes are engine inputs; sec_view is what the public sec-qgv2 file
    would show for the per-share history: as-filed values plus the per-item share_basis_factor F_k (owner A-plan)."""
    rng = random.Random(seed)
    groups = ['syn_group_%02d' % k for k in range(1, 13)]
    gweights = [rng.uniform(0.5, 2.0) for _ in groups]
    months = _months()
    companies, quotes, sec_view = {}, {}, {}
    for idx in range(1, n + 1):
        code = 'NYSE:SYN%03d' % idx
        u = rng.random()
        profile = 'FINANCIAL' if u < 0.07 else 'GENERAL'
        group = 'syn_group_fin' if profile == 'FINANCIAL' else 'syn_group_small' if u < 0.08 else rng.choices(groups, gweights)[0]
        shares = round(math.exp(rng.gauss(math.log(300.0), 0.9)), 3)
        price = round(math.exp(rng.gauss(math.log(80.0), 0.7)), 2)
        mcap = price * shares
        cash = mcap * rng.uniform(0.01, 0.2)
        net = mcap * rng.gauss(0.12, 0.25)
        if net < -0.8 * mcap:
            net = -0.8 * mcap
        debt = cash + net
        if debt < 0:
            debt = mcap * rng.uniform(0.0, 0.03)
            cash = debt - net
        kind = rng.random()
        if kind < 0.015:                                  # net cash above market cap -> EV <= 0
            cash = mcap + debt + mcap * rng.uniform(0.05, 0.6)
        ev_pos = mcap + debt - cash if mcap + debt - cash > 0 else mcap
        ebit = ev_pos / math.exp(rng.gauss(math.log(18.0), 0.45))
        if rng.random() < 0.06:
            ebit = -mcap * rng.uniform(0.005, 0.05)
        fcf = ebit * rng.gauss(0.8, 0.3)
        f = rng.random()
        if f < 0.06:
            fcf = -mcap * rng.uniform(0.005, 0.04)
        elif f < 0.075:                                    # tiny FCF: price above the +100% growth DCF
            fcf = mcap * rng.uniform(1e-4, 3e-3)
        elif f < 0.08:                                     # huge FCF: price below the -50% growth DCF
            fcf = mcap * rng.uniform(1.0, 1.5)
        realized = None if rng.random() < 0.03 else round(max(-0.3, min(0.5, rng.gauss(0.07, 0.08))), 6)
        fm = 12 if rng.random() < 0.75 else rng.randint(1, 11)
        # Month-end closes (split-adjusted, latest share basis), backwards from today's price.
        closes = {}
        c = price / math.exp(rng.gauss(0.0, 0.06))
        for (y, m) in reversed(months):
            closes['%04d-%02d' % (y, m)] = round(c, 4)
            c = c / math.exp(rng.gauss(0.007, 0.08))
        # EBIT/share history on the latest basis (engine input) and the as-filed view (+ F_k) for the public file.
        e = ebit / shares
        hist_latest = []
        for k in range(5):
            year = 2025 - k
            hist_latest.append({'period_end': _month_end(year, fm), 'value': round(e, 6)})
            e = e / max(0.5, rng.gauss(1.08, 0.15))
        hist_latest.reverse()
        h = rng.random()
        if h < 0.10:
            closes = {}
        elif h < 0.15:
            hist_latest = hist_latest[-2:]
        split = None
        if rng.random() < 0.08:
            ratio = rng.choice((2, 3, 4))
            sy, sm = rng.choice([ym for ym in months if (2021, 6) <= ym <= (2026, 6)])
            split = {'ratio': ratio, 'month': '%04d-%02d' % (sy, sm)}
        filed = []
        for item in hist_latest:
            pre = split is not None and item['period_end'][:7] < split['month']
            factor = 1.0 / split['ratio'] if pre else 1.0
            filed.append({'period_end': item['period_end'], 'value_as_filed': round(item['value'] / factor, 6),
                          'share_basis_factor': factor})
        rnd = lambda x: round(x, 3)
        companies[code] = {
            'cik': 'SYN%07d' % idx, 'industry_group': group, 'profile': profile, 'memberships': None,
            'factors': {k: round(rng.uniform(1, 99), 4) for k in Q_IDS + G_IDS},
            'qg_axes': {'Q': {'score': round(rng.uniform(2, 98), 4)}, 'G': {'score': round(rng.uniform(2, 98), 4)}},
            'v_inputs': {'currency': 'USD', 'ebit': rnd(ebit), 'fcf': rnd(fcf), 'total_debt': rnd(debt), 'cash': rnd(cash),
                         'diluted_shares': shares, 'ebit_per_share_history': [dict(x) for x in hist_latest],
                         'revenue_cagr_3y': realized},
        }
        quotes[code] = {'price': price, 'currency': 'USD', 'month_closes': closes}
        sec_view[code] = {'history_as_filed': filed, 'split': split}
    return companies, quotes, sec_view


def daily_quotes(quotes, days, seed=SEED):
    """Day 0 = quotes; days 1.. move prices (market 1.0% + idiosyncratic 1.5% daily); month-end closes unchanged."""
    rng = random.Random(seed + 7)
    out = [quotes]
    cur = {k: v['price'] for k, v in quotes.items()}
    for _ in range(days - 1):
        mkt = rng.gauss(0.0, 0.010)
        nxt = {}
        for k in sorted(cur):
            cur[k] = round(cur[k] * math.exp(mkt + rng.gauss(0.0, 0.015)), 4)
            nxt[k] = dict(quotes[k], price=cur[k])
        out.append(nxt)
    return out


def run_engine(companies, quotes):
    cfg = load_official_type_config().to_dict()
    params = load_default_dcf_parameters()
    return engine.score_universe(companies, quotes, type_config=cfg, parameters=params), params


# ----------------------------------------------------------------------------------------------------------------
# Publication policies (what a public file shows) and transforms
# ----------------------------------------------------------------------------------------------------------------

def tf_apply(t, x):
    if x is None or t is None or t[0] == 'hidden':
        return None
    if t[0] == 'full':
        return x
    if t[0] == 'round':
        return round(x, t[1])
    if t[0] == 'bucket':
        top = int(round(100.0 / t[1])) - 1
        return min(int(x // t[1]), top)
    raise ValueError(t)


def tf_match(t, pub, lo, hi):
    """Is there an x in [lo, hi] with T(x) == pub? (T monotone non-decreasing.) None-ness must agree."""
    if t is None or t[0] == 'hidden':
        return True
    if pub is None or lo is None:
        return pub is None and lo is None
    if t[0] == 'full':
        return lo - EPS <= pub <= hi + EPS
    return tf_apply(t, lo) <= pub <= tf_apply(t, hi)


FULL, R1, R0 = ('full',), ('round', 1), ('round', 0)
DEC, QUINT, TERC = ('bucket', 10.0), ('bucket', 20.0), ('bucket', 100.0 / 3.0)


def policy(name, factors, axis, total, rank, reasons='grouped', own=None, states=True):
    """factors: transform of the 4 cross-section V factors; own: transform of v_vs_own_history (default = factors);
    axis/total: transforms (None = not published); rank: None | 'exact' (official rank from the exact total) |
    'published' (rank of the published total); reasons: 'raw' | 'grouped' (D-CV2) | 'state_only';
    states: per-factor availability visible (axes.V.weight_available / factors_available reveal it even when the
    factor rows are hidden), False only when nothing about V is published."""
    return {'name': name, 'factors': factors, 'own': factors if own is None else own, 'axis': axis, 'total': total,
            'rank': rank, 'reasons': reasons, 'states': states}


POLICIES = [
    policy('A_design_full', FULL, FULL, FULL, 'exact'),
    policy('A_raw_reasons', FULL, FULL, FULL, 'exact', reasons='raw'),
    policy('B_round1', R1, R1, R1, 'exact'),
    policy('C_round0', R0, R0, R0, 'exact'),
    policy('D_axis_only_full', None, FULL, FULL, 'exact'),
    policy('E_axis_int_rank_exact', None, R0, R0, 'exact'),
    policy('F_axis_int_rank_pub', None, R0, R0, 'published'),
    policy('G_decile', DEC, DEC, R0, 'published'),
    policy('H_quintile', QUINT, QUINT, R0, 'published'),
    policy('I_axis_quintile_total_int', None, QUINT, R0, 'published'),
    policy('J_axis_quintile_total_quintile', None, QUINT, QUINT, 'published'),
    policy('K_axis_quintile_only', None, QUINT, None, None),
    policy('L_axis_tercile_only', None, TERC, None, None),
    policy('M_v_withheld', None, None, None, None, states=False),
    # Cross-section factor scores at full precision, but no own-history factor and no V axis / total / rank:
    # is V4 the only absolute anchor of the zero-knowledge bootstrap?
    policy('N_cross_only_no_v4', FULL, None, None, None, own=('hidden',)),
]


def map_reason(code, mode):
    if code is None:
        return None
    if mode == 'raw':
        return code
    if mode == 'grouped':
        return GROUPED if code in PRICE_DEPENDENT else code
    return 'NA'


# ----------------------------------------------------------------------------------------------------------------
# Review context (engine run at the true synthetic prices) and per-target attacker model
# ----------------------------------------------------------------------------------------------------------------

def _finite(x):
    return engine.finite(x)


class Review:
    def __init__(self, companies, quotes, sec_view=None, results=None, params=None):
        self.companies, self.quotes, self.sec_view = companies, quotes, sec_view or {}
        if results is None:
            results, params = run_engine(companies, quotes)
        self.results, self.params = results, params
        sol = params['solver']
        self.g_lo, self.g_hi = sol['growth_lower'], sol['growth_upper']
        self.h_lo = self._dcf(1.0, self.g_lo)
        self.h_hi = self._dcf(1.0, self.g_hi)
        ids = sorted(companies)
        self.ids = ids
        pooled = [i for i in ids if companies[i].get('in_cross_section', True) is not False]
        det = {i: results[i]['detail'] for i in ids}
        self.values = {
            'v_earnings_yield': {i: det[i]['ebit_yield'] for i in pooled if det[i]['ebit_yield'] is not None},
            'v_fcf_yield': {i: det[i]['fcf_yield'] for i in pooled if det[i]['fcf_yield'] is not None},
            'v_expectation_check': {i: -det[i]['expectation_gap'] for i in pooled if det[i]['expectation_gap'] is not None},
        }
        self.values['v_vs_industry'] = self.values['v_earnings_yield']
        self.group = {i: companies[i].get('industry_group') for i in ids}
        self.ranked = {i: results[i]['total'] for i in ids
                       if results[i]['total'] is not None and results[i]['axes']['V']['score'] is not None}
        self.targets = [i for i in ids if companies[i]['profile'] == 'GENERAL' and _finite((quotes.get(i) or {}).get('price'))]

    def _dcf(self, cf, g):
        return two_stage_dcf(cashflow_per_share=cf, growth_rate=g, parameters=self.params, cashflow_currency='USD').value_per_share

    # -- published view ------------------------------------------------------------------------------------------
    def official_rank(self, i, pol):
        if i not in self.ranked:
            return None
        t = pol['total'] if pol['rank'] == 'published' else FULL
        mine = tf_apply(t, self.ranked[i])
        return 1 + sum(1 for j, x in self.ranked.items() if j != i and tf_apply(t, x) > mine)

    def published(self, i, pol):
        r = self.results[i]
        sig = tuple(map_reason(r['factors'][f]['reason'] if r['factors'][f]['score'] is None else None, pol['reasons'])
                    for f in V_IDS)
        fac = {f: tf_apply(pol['own'] if f == 'v_vs_own_history' else pol['factors'], r['factors'][f]['score']) for f in V_IDS}
        return {'sig': sig, 'factors': fac, 'axis': tf_apply(pol['axis'], r['axes']['V']['score']),
                'total': tf_apply(pol['total'], r['total']),
                'rank': self.official_rank(i, pol) if pol['rank'] else None}

    # -- attacker model ------------------------------------------------------------------------------------------
    def past_yields(self, i, with_factor=True, noise=0.0, side=0):
        """Attacker's own-history points from the public as-filed history (+F_k) and public month-end closes.
        noise > 0: the attacker's month-end close is within +-noise of the publisher's; side -1/+1 = low/high end."""
        closes = self.quotes[i].get('month_closes') or {}
        hist = self.sec_view.get(i, {}).get('history_as_filed')
        if hist is None:   # no as-filed view: the engine input itself (latest basis)
            hist = [{'period_end': h['period_end'], 'value_as_filed': h['value'], 'share_basis_factor': 1.0}
                    for h in self.companies[i]['v_inputs']['ebit_per_share_history']]
        out = []
        for h in hist:
            c = engine.month_close(closes, h['period_end'])
            if c is not None:
                y = h['value_as_filed'] * (h['share_basis_factor'] if with_factor else 1.0)
                a, b = y / (c * (1 + noise)), y / (c * (1 - noise))
                out.append(y / c if side == 0 else min(a, b) if side < 0 else max(a, b))
        return out

    def value_intervals(self, iv):
        """Per cross factor {j: (lo, hi)} value interval of every pooled other j, from the attacker's price interval
        iv[j] = (lo, hi) (absolute; lo == hi when the price is known; absent = unknown -> (-inf, inf))."""
        out = {}
        for f in ('v_earnings_yield', 'v_fcf_yield', 'v_expectation_check'):
            d = {}
            for j, x in self.values[f].items():
                if j not in iv:
                    d[j] = (-math.inf, math.inf)
                    continue
                lo, hi = iv[j]
                if lo == hi:
                    d[j] = (x, x)
                    continue
                d[j] = self._value_range(j, f, lo, hi)
            out[f] = d
        out['v_vs_industry'] = out['v_earnings_yield']
        return out

    def _value_range(self, j, f, lo, hi):
        v = self.companies[j]['v_inputs']
        s = v['diluted_shares']
        if f == 'v_expectation_check':
            cf = v['fcf'] / s
            def val(p):
                if p <= cf * self.h_lo:
                    return v['revenue_cagr_3y'] - self.g_lo
                if p >= cf * self.h_hi:
                    return v['revenue_cagr_3y'] - self.g_hi
                rev = reverse_dcf(cashflow_per_share=cf, price=p, parameters=self.params, cashflow_currency='USD', price_currency='USD')
                return v['revenue_cagr_3y'] - rev.implied_growth
            a = val(max(lo, 1e-12)) if lo > 0 else v['revenue_cagr_3y'] - self.g_lo
            b = val(hi) if hi < math.inf else v['revenue_cagr_3y'] - self.g_hi
            return (min(a, b), max(a, b))
        X = v['ebit'] if f == 'v_earnings_yield' else v['fcf']
        N = v['total_debt'] - v['cash']
        pe0 = max(0.0, -N / s)
        def val(p):
            if p is None or p <= pe0:
                return math.copysign(math.inf, X) if N <= 0 else X / N
            if p == math.inf:
                return 0.0
            return X / (p * s + N)
        a, b = val(lo if lo > pe0 else None), val(hi)
        return (min(a, b), max(a, b))

    def model(self, i, ovals, with_factor=True, close_noise=0.0):
        """Segments [(a, b, sig_raw, ranges)] over [P/W, P*W] for target i. ovals = value_intervals(iv) of the
        attacker's knowledge of the other names (the target's own entry is ignored)."""
        v = self.companies[i]['v_inputs']
        P = self.quotes[i]['price']
        s, E, F, D, C = v['diluted_shares'], v['ebit'], v['fcf'], v['total_debt'], v['cash']
        realized = v.get('revenue_cagr_3y')
        debt_ok = _finite(D) and _finite(C) and D >= 0 and C >= 0
        N = (D - C) if debt_ok else 0.0
        pe0 = max(0.0, -N / s)
        cf = F / s if _finite(F) else None
        lo_w, hi_w = P / WINDOW, P * WINDOW
        res = self.results[i]
        pts = set()
        fac = {}

        def events(values, vl, vr, inv):
            base, bps = 0, []
            dec = vl > vr
            for o in values:
                if dec:
                    if o >= vl:
                        continue
                    if o <= vr:
                        base += 1
                        continue
                else:
                    if o <= vl:
                        base += 1
                        continue
                    if o >= vr:
                        continue
                b = inv(o)
                bps.append(b)
                if lo_w < b < hi_w:
                    pts.add(b)
            bps.sort()
            return {'dec': dec, 'base': base, 'bps': bps}

        def yield_side(X):
            if not _finite(X) or X == 0:
                return None
            # v(P) = X / (P*s + N) on EV > 0: value at the domain start (P -> max(0, -N/s)) and at P -> inf.
            vl = X / N if N > 0 else math.copysign(math.inf, X)
            return vl, 0.0, (lambda o: (X / o - N) / s)

        for f in CROSS:
            others = ovals[f]
            pool = [j for j in others if j != i]
            if f == 'v_vs_industry':
                g = self.group[i]
                members = [j for j in pool if g is not None and self.group[j] == g]
                if g is not None and len(members) + 1 >= engine.MIN_PEERS:
                    pool = members
            his = [others[j][1] for j in pool]
            los = [others[j][0] for j in pool]
            side = None
            if f in ('v_earnings_yield', 'v_vs_industry', 'v_fcf_yield') and debt_ok:
                side = yield_side(F if f == 'v_fcf_yield' else E)
            elif f == 'v_expectation_check' and cf is not None and cf > 0 and _finite(realized):
                side = (realized - self.g_lo, realized - self.g_hi, lambda o: self._dcf(cf, realized - o))
            if side is None:
                fac[f] = None
                continue
            sure = events(his, *side)
            maybe = sure if his == los else events(los, *side)
            fac[f] = {'sure': sure, 'maybe': maybe, 'n': len(pool)}
        # own history
        has_own = res['factors']['v_vs_own_history']['score'] is not None
        own = None
        if has_own and _finite(E) and E != 0:
            side = (math.copysign(math.inf, E), 0.0, lambda o: E / (s * o))
            if close_noise:
                sure = events(self.past_yields(i, with_factor, close_noise, +1), *side)
                maybe = events(self.past_yields(i, with_factor, close_noise, -1), *side)
            else:
                sure = maybe = events(self.past_yields(i, with_factor), *side)
            own = {'sure': sure, 'maybe': maybe, 'n': len(self.past_yields(i, with_factor))}
        # availability break prices
        for b in (pe0, (cf * self.h_lo) if cf and cf > 0 else None, (cf * self.h_hi) if cf and cf > 0 else None):
            if b is not None and lo_w < b < hi_w:
                pts.add(b)
        edges = [lo_w] + sorted(pts) + [hi_w]
        static = {f: res['factors'][f]['reason'] for f in V_IDS}

        def raw_sig(p):
            ev_ok = debt_ok and p * s + N > 0
            out = []
            for f in V_IDS:
                if f == 'v_vs_own_history':
                    out.append(None if own is not None or res['factors'][f]['score'] is not None else static[f])
                    continue
                if f == 'v_expectation_check':
                    if cf is None:
                        out.append('FCF_NOT_AVAILABLE')
                    elif cf <= 0:
                        out.append('NON_POSITIVE_CASHFLOW')
                    elif not (cf * self.h_lo < p < cf * self.h_hi):
                        out.append('ROOT_NOT_BRACKETED')
                    elif not _finite(realized):
                        out.append('REALIZED_GROWTH_NOT_AVAILABLE')
                    else:
                        out.append(None)
                    continue
                if not debt_ok:
                    out.append('DEBT_CASH_NOT_AVAILABLE')
                elif not ev_ok:
                    out.append('EV_NON_POSITIVE')
                elif f == 'v_fcf_yield' and not _finite(F):
                    out.append('FCF_NOT_AVAILABLE')
                elif f != 'v_fcf_yield' and not _finite(E):
                    out.append('EBIT_NOT_AVAILABLE')
                else:
                    out.append(None)
            return tuple(out)

        def less(spec, p):
            if spec['dec']:
                return spec['base'] + len(spec['bps']) - bisect.bisect_right(spec['bps'], p)
            return spec['base'] + bisect.bisect_left(spec['bps'], p)

        segs = []
        for a, b in zip(edges, edges[1:]):
            if b <= a:
                continue
            p = math.sqrt(a * b)
            sig = raw_sig(p)
            ranges = {}
            for f, code in zip(V_IDS, sig):
                if code is not None:
                    ranges[f] = None
                    continue
                spec = own if f == 'v_vs_own_history' else fac[f]
                if spec is None:
                    if f == 'v_vs_own_history' and res['factors'][f]['score'] is not None:
                        x = res['factors'][f]['score']          # E == 0 corner: constant
                        ranges[f] = (x, x)
                    else:
                        ranges[f] = None
                    continue
                ranges[f] = (100.0 * less(spec['sure'], p) / spec['n'], 100.0 * less(spec['maybe'], p) / spec['n'])
            segs.append((a, b, sig, ranges))
        return segs

    def knowledge(self, codes, noise=0.0):
        """Attacker price knowledge {j: (lo, hi)} for the given codes: exact current prices, or +-noise when the
        attacker only knows a nearby price (official consolidated close vs the IEX last sale the publisher uses)."""
        return {j: (self.quotes[j]['price'] * (1 - noise), self.quotes[j]['price'] * (1 + noise)) for j in codes
                if _finite((self.quotes.get(j) or {}).get('price'))}

    def rank_context(self, i, iv, pol):
        others = [(j, x) for j, x in self.ranked.items() if j != i]
        if pol['rank'] == 'exact':
            if pol['total'] == FULL:          # every other exact total is itself public
                return sorted(x for _, x in others), 0
            kv = sorted(x for j, x in others if j in iv and iv[j][0] == iv[j][1])
            return kv, len(others) - len(kv)
        if pol['rank'] == 'published':        # other rows' published totals are public to everyone
            return sorted(tf_apply(pol['total'], x) for _, x in others), 0
        return None

    def feasible(self, i, segs, pol, pub, rank_ctx):
        r = self.results[i]
        w = r['weights']
        trap = r['value_trap_gate']
        qa, ga = r['axes']['Q']['score'], r['axes']['G']['score']
        out = []
        for a, b, sig, ranges in segs:
            if pol['states'] and tuple(map_reason(c, pol['reasons']) for c in sig) != pub['sig']:
                continue
            ok = True
            for f in V_IDS:
                t = pol['own'] if f == 'v_vs_own_history' else pol['factors']
                rg = ranges[f]
                if t is not None and not tf_match(t, pub['factors'][f], rg[0] if rg else None, rg[1] if rg else None):
                    ok = False
                    break
            if not ok:
                continue
            used = 0.0
            lo = hi = 0.0
            for f, wt in engine.WEIGHTS['V'].items():
                if ranges[f] is not None:
                    used += wt
                    lo += wt * ranges[f][0]
                    hi += wt * ranges[f][1]
            if used == 0 or used / 100.0 < engine.MIN_AXIS_WEIGHT:
                vlo = vhi = None
            else:
                vlo, vhi = lo / used, hi / used
            if not tf_match(pol['axis'], pub['axis'], vlo, vhi):
                continue
            # total (engine composite rule; weights, gate, Q and G are price-free and public)
            data = 0.0
            for p, x in (('Q', qa), ('G', ga), ('V', vlo)):
                if x is not None:
                    data += w[p]
            inc = [(w['Q'], qa, qa)] if qa is not None else []
            if ga is not None:
                inc.append((w['G'], ga, ga))
            if vlo is not None and not trap:
                inc.append((w['V'], vlo, vhi))
            if data / 100.0 < engine.MIN_AXIS_WEIGHT or not inc:
                tlo = thi = None
            else:
                sw = sum(x[0] for x in inc)
                tlo = sum(x[0] * x[1] for x in inc) / sw
                thi = sum(x[0] * x[2] for x in inc) / sw
            if not tf_match(pol['total'], pub['total'], tlo, thi):
                continue
            if pol['rank']:
                if tlo is None or vlo is None:
                    if pub['rank'] is not None:
                        continue
                else:
                    if pub['rank'] is None:
                        continue
                    kv, u = rank_ctx
                    if pol['rank'] == 'exact':
                        r_lo = 1 + len(kv) - bisect.bisect_right(kv, thi)
                        r_hi = 1 + len(kv) - bisect.bisect_right(kv, tlo) + u
                    else:
                        r_lo = 1 + len(kv) - bisect.bisect_right(kv, tf_apply(pol['total'], thi))
                        r_hi = 1 + len(kv) - bisect.bisect_right(kv, tf_apply(pol['total'], tlo))
                    if not r_lo <= pub['rank'] <= r_hi:
                        continue
            out.append((a, b))
        return out

    def interval(self, i, iv, pol, segs=None, ovals=None, with_factor=True, close_noise=0.0):
        """Attacker's price interval for target i given knowledge iv of the other names. lo/hi are relative to the
        true price (0 / inf = unbounded inside the window); abs_lo/abs_hi absolute (for propagation)."""
        if segs is None:
            segs = self.model(i, ovals if ovals is not None else self.value_intervals(iv), with_factor, close_noise)
        pub = self.published(i, pol)
        feas = self.feasible(i, segs, pol, pub, self.rank_context(i, iv, pol))
        P = self.quotes[i]['price']
        if not feas:
            return {'lo': None, 'hi': None, 'w': None, 'contains_truth': False, 'abs_lo': 0.0, 'abs_hi': math.inf}
        lo, hi = feas[0][0], feas[-1][1]
        lo_r = 0.0 if lo <= P / WINDOW * (1 + 1e-12) else lo / P
        hi_r = math.inf if hi >= P * WINDOW * (1 - 1e-12) else hi / P
        truth = any(a <= P <= b for a, b in feas)
        w = math.inf if lo_r == 0.0 or hi_r == math.inf else math.sqrt(hi_r / lo_r) - 1.0
        return {'lo': lo_r, 'hi': hi_r, 'w': w, 'contains_truth': truth, 'abs_lo': lo_r * P, 'abs_hi': hi_r * P}


def known_codes(review, fraction, seed):
    """Global set of names whose current price a partial attacker knows (deterministic)."""
    if fraction >= 1.0:
        return frozenset(review.ids)
    rng = random.Random('%s|%s' % (seed, fraction))
    return frozenset(j for j in review.ids if rng.random() < fraction)


# ----------------------------------------------------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------------------------------------------------

ATTACKERS = (('strong', 1.0, 0.0), ('strong_noise0.5', 1.0, 0.005), ('partial50', 0.5, 0.0), ('partial20', 0.2, 0.0),
             ('zero', 0.0, 0.0))
PROPAGATE = ('A_design_full', 'H_quintile', 'J_axis_quintile_total_quintile', 'K_axis_quintile_only',
             'L_axis_tercile_only', 'N_cross_only_no_v4')


def summarize(ws):
    finite = sorted(x for x in ws if x is not None and x != math.inf)
    n = len(ws)
    if n == 0:
        return {'n': 0}
    q = lambda p: (sorted(ws)[min(n - 1, int(p * n))])
    frac = lambda t: sum(1 for x in ws if x is not None and x < t) / n
    return {'n': n, 'bounded_both': len(finite) / n, 'p05': q(0.05), 'p10': q(0.10), 'median': q(0.5),
            'below_2pct': frac(0.02), 'below_5pct': frac(0.05), 'below_10pct': frac(0.10), 'below_15pct': frac(0.15),
            'below_20pct': frac(0.20)}


def _strong(review, targets, policies, noise=0.0):
    """Every other current price known (exactly, or within +-noise; month-end closes within the same noise)."""
    iv = review.knowledge(review.ids, noise)
    ovals = review.value_intervals(iv)
    per = {p['name']: [] for p in policies}
    misses = 0
    for i in targets:
        segs = review.model(i, ovals, close_noise=noise)
        for pol in policies:
            r = review.interval(i, iv, pol, segs)
            misses += 0 if r['contains_truth'] else 1
            per[pol['name']].append(r['w'])
    return per, misses


def propagate(review, pol, fraction, rounds, seed=SEED, targets=None, noise=0.0):
    """Partial attacker with a global known set K (fraction of the names). Round 0 uses K only; each later round
    feeds the intervals inferred for the unknown names back in as interval knowledge (bootstrap). Returns per round
    the widths of the unknown V-scored names, and the truth-miss count."""
    known = known_codes(review, fraction, seed)
    iv = review.knowledge(known, noise)
    unknown = [i for i in review.targets if i not in known]
    report = [i for i in unknown if review.results[i]['axes']['V']['score'] is not None and (targets is None or i in targets)]
    widths, misses = [], 0
    for rnd in range(rounds + 1):
        ovals = review.value_intervals(iv)
        new = {}
        ws = []
        for i in unknown:
            r = review.interval(i, iv, pol, ovals=ovals, close_noise=noise)
            misses += 0 if r['contains_truth'] else 1
            prev = iv.get(i, (0.0, math.inf))
            new[i] = (max(prev[0], r['abs_lo']), min(prev[1], r['abs_hi']))
        for i in report:
            lo, hi = new[i]
            P = review.quotes[i]['price']
            ws.append(math.inf if lo <= P / WINDOW * (1 + 1e-12) or hi >= P * WINDOW * (1 - 1e-12) else math.sqrt(hi / lo) - 1.0)
        widths.append(ws)
        for i, x in new.items():
            if x[0] > 0.0 or x[1] < math.inf:
                iv[i] = (x[0] if x[0] > 0 else 0.0, x[1])
    return widths, misses


def scenario_policy_matrix(review, targets, attackers=ATTACKERS, policies=POLICIES, seed=SEED, rounds=2,
                           propagate_names=PROPAGATE):
    """Scenarios 1, 5 (hidden-factor policies) and 6 (precision): interval width per policy x attacker.
    Partial and zero attackers: round 0 (independent) and, for the policies in propagate_names, after `rounds`
    bootstrap rounds (key '<attacker>+boot')."""
    out, misses = {}, 0
    for aname, frac, noise in attackers:
        if frac >= 1.0:
            per, m = _strong(review, targets, policies, noise)
            misses += m
            out[aname] = {k: summarize(v) for k, v in per.items()}
            continue
        out[aname], boot = {}, {}
        for pol in policies:
            r = rounds if pol['name'] in propagate_names else 0
            ws, m = propagate(review, pol, frac, r, seed, set(targets), noise)
            misses += m
            out[aname][pol['name']] = summarize(ws[0])
            if r:
                boot[pol['name']] = summarize(ws[-1])
        if boot:
            out[aname + '+boot'] = boot
    return out, misses


def scenario_reasons(review, seed=SEED):
    """Scenario 2: names whose V factors are NA for a price-dependent reason. Strong and zero-knowledge attackers;
    raw vs grouped (D-CV2) vs state-only reasons, with scores (policy A) and with nothing but the reason pattern."""
    rows = []
    strong_iv = review.knowledge(review.ids)
    strong_ov = review.value_intervals(strong_iv)
    zero_ov = review.value_intervals({})
    for i in review.targets:
        r = review.results[i]
        codes = {f: r['factors'][f]['reason'] for f in V_IDS if r['factors'][f]['score'] is None}
        dep = sorted({c for c in codes.values() if c in PRICE_DEPENDENT})
        if not dep:
            continue
        row = {'code': i, 'reasons': dep}
        for aname, iv, ov in (('strong', strong_iv, strong_ov), ('zero', {}, zero_ov)):
            segs = review.model(i, ov)
            for mode in ('raw', 'grouped', 'state_only'):
                row['%s_%s' % (aname, mode)] = review.interval(i, iv, policy('x', FULL, FULL, FULL, 'exact', reasons=mode), segs)
                row['%s_%s_pattern_only' % (aname, mode)] = review.interval(i, iv, policy('x', None, None, None, None, reasons=mode), segs)
        rows.append(row)
    return rows


def scenario_own_history(review, seed=SEED):
    """Scenario 4: zero-knowledge attacker (no current price of anyone) with only v_vs_own_history published (plus
    the public month-end closes and the public history), with and without the per-item share_basis_factor F_k."""
    pol = policy('own_only', None, None, None, None, own=FULL)
    rows = {'with_factor': [], 'without_factor': [], 'split_with_factor': [], 'split_without_factor': []}
    contain = {'with_factor': [0, 0], 'without_factor': [0, 0]}
    zero_ov = review.value_intervals({})
    for i in review.targets:
        if review.results[i]['factors']['v_vs_own_history']['score'] is None:
            continue
        split = any(h['share_basis_factor'] != 1.0 for h in (review.sec_view.get(i) or {}).get('history_as_filed', []))
        for mode, wf in (('with_factor', True), ('without_factor', False)):
            r = review.interval(i, {}, pol, review.model(i, zero_ov, with_factor=wf))
            rows[mode].append(r['w'])
            if split:
                rows['split_' + mode].append(r['w'])
                contain[mode][0] += 1
                contain[mode][1] += 1 if r['contains_truth'] else 0
    return {k: summarize(v) for k, v in rows.items()}, contain


def scenario_backout(review):
    """Scenario 5: (a) one hidden V factor from the V axis; (b) the V axis from total + Q + G + weights."""
    err_a, err_b, n_a, n_b = 0.0, 0.0, 0, 0
    for i in review.targets:
        r = review.results[i]
        sc = {f: r['factors'][f]['score'] for f in V_IDS}
        ax = r['axes']['V']['score']
        if ax is not None and all(x is not None for x in sc.values()):
            for hide in V_IDS:
                acc = sum(engine.WEIGHTS['V'][f] * sc[f] for f in V_IDS if f != hide)
                back = (ax * 100.0 - acc) / engine.WEIGHTS['V'][hide]
                err_a = max(err_a, abs(back - sc[hide]))
                n_a += 1
        if ax is not None and r['total'] is not None and not r['value_trap_gate'] and r['axes']['Q']['score'] is not None \
                and r['axes']['G']['score'] is not None:
            w = r['weights']
            back = (r['total'] * (w['Q'] + w['G'] + w['V']) - w['Q'] * r['axes']['Q']['score'] - w['G'] * r['axes']['G']['score']) / w['V']
            err_b = max(err_b, abs(back - ax))
            n_b += 1
    return {'hidden_factor_cases': n_a, 'hidden_factor_max_abs_error': err_a,
            'axis_from_total_cases': n_b, 'axis_from_total_max_abs_error': err_b}


def decode_axis(review, i, tol=1e-9):
    """Scenario 5c: zero-knowledge decoding of a full-precision V axis (all factor scores hidden) into the exact
    factor ranks by meet-in-the-middle. Population sizes are known from public coverage/state counts.
    Returns (candidate tuples, own-history ranks among candidates, true tuple found)."""
    r = review.results[i]
    sc = {f: r['factors'][f]['score'] for f in V_IDS}
    if r['axes']['V']['score'] is None or any(x is None for x in sc.values()):
        return None
    segs_n = {}
    for f in CROSS:
        pool = [j for j in review.values[f] if j != i]
        if f == 'v_vs_industry' and r['factors'][f]['basis'] == 'INDUSTRY':
            pool = [j for j in pool if review.group[j] == review.group[i]]
        segs_n[f] = len(pool)
    m = len(review.past_yields(i))
    W = engine.WEIGHTS['V']
    n1, n2, n3, n5 = (segs_n[f] for f in CROSS)
    a_side = sorted((W['v_earnings_yield'] * l1 / n1 + W['v_fcf_yield'] * l2 / n2, l1, l2)
                    for l1 in range(n1 + 1) for l2 in range(n2 + 1))
    keys = [x[0] for x in a_side]
    target = r['axes']['V']['score']
    found = []
    for l3 in range(n3 + 1):
        for j in range(m + 1):
            for l5 in range(n5 + 1):
                rest = W['v_vs_industry'] * l3 / n3 + W['v_vs_own_history'] * j / m + W['v_expectation_check'] * l5 / n5
                need = target - rest
                k = bisect.bisect_left(keys, need - tol)
                while k < len(keys) and keys[k] <= need + tol:
                    found.append((a_side[k][1], a_side[k][2], l3, j, l5))
                    k += 1
    truth = tuple(int(round(sc[f] * n / 100.0)) for f, n in
                  (('v_earnings_yield', n1), ('v_fcf_yield', n2), ('v_vs_industry', n3), ('v_vs_own_history', m), ('v_expectation_check', n5)))
    return {'candidates': len(found), 'own_ranks': sorted({c[3] for c in found}), 'true_found': truth in found}


def scenario_decode(review, sample=12, seed=SEED):
    rng = random.Random(seed + 5)
    pool = [i for i in review.targets if review.results[i]['factors']['v_vs_own_history']['score'] is not None
            and review.results[i]['axes']['V']['score'] is not None
            and all(review.results[i]['factors'][f]['score'] is not None for f in V_IDS)]
    rows = []
    for i in rng.sample(pool, min(sample, len(pool))):
        d = decode_axis(review, i)
        if d:
            rows.append(dict(d, code=i))
    return rows


def scenario_daily(companies, quotes, sec_view, days=20, sample=None, seed=SEED, policies=None):
    """Scenario 3: daily snapshots with unchanged SEC inputs.
    (a) zero-knowledge direction: does a change in the published EBIT-yield percentile give the sign of the name's
        return relative to the cross-section median? (per policy transform of factor scores)
    (b) strong attacker who also knows each day's return of the target (upper-bound "dithering" model): intersect the
        daily intervals; width after 1, 5 and `days` days."""
    policies = policies or [p for p in POLICIES if p['name'] in ('A_design_full', 'C_round0', 'H_quintile',
                                                                 'I_axis_quintile_total_int', 'K_axis_quintile_only')]
    qs = daily_quotes(quotes, days, seed)
    reviews = []
    for q in qs:
        res, params = run_engine(companies, q)
        reviews.append(Review(companies, q, sec_view, res, params))
    base = reviews[0]
    targets = base.targets if sample is None else random.Random(seed + 3).sample(base.targets, min(sample, len(base.targets)))
    # (a) direction
    direction = {}
    for name, t in (('full', FULL), ('round0', R0), ('decile', DEC), ('quintile', QUINT)):
        right = changed = total = 0
        for d in range(1, len(reviews)):
            r0, r1 = reviews[d - 1], reviews[d]
            rets = {i: math.log(r1.quotes[i]['price'] / r0.quotes[i]['price']) for i in r0.targets}
            med = statistics.median(rets.values())
            for i in r0.targets:
                a = tf_apply(t, r0.results[i]['factors']['v_earnings_yield']['score'])
                b = tf_apply(t, r1.results[i]['factors']['v_earnings_yield']['score'])
                if a is None or b is None:
                    continue
                total += 1
                if a != b:
                    changed += 1
                    rel = rets[i] - med
                    if (b < a) == (rel > 0):
                        right += 1
        direction[name] = {'pairs': total, 'changed': changed / total if total else None,
                           'sign_correct_when_changed': right / changed if changed else None}
    # (b) intersection over days (relative coordinates log(P/P_true_d) are shift-invariant under known returns)
    ivs = [rv.knowledge(rv.ids) for rv in reviews]
    ovs = [rv.value_intervals(iv) for rv, iv in zip(reviews, ivs)]
    inter = {}
    for pol in policies:
        acc = {i: [0.0, math.inf] for i in targets}
        marks = {}
        for d, rv in enumerate(reviews):
            for i in targets:
                if i not in rv.targets:
                    continue
                r = rv.interval(i, ivs[d], pol, ovals=ovs[d])
                if r['lo'] is None:
                    continue
                acc[i][0] = max(acc[i][0], r['lo'])
                acc[i][1] = min(acc[i][1], r['hi'])
            if d + 1 in (1, 5, days):
                ws = []
                for i in targets:
                    lo, hi = acc[i]
                    ws.append(math.inf if lo == 0.0 or hi == math.inf else math.sqrt(hi / lo) - 1.0)
                marks[d + 1] = summarize(ws)
        inter[pol['name']] = marks
    return {'direction': direction, 'intersection': inter}


def dividend_factor_leak(dividend, factor):
    """If a per-item factor were a dividend (total-return) adjustment a = 1 - D/P_prev instead of a share-count ratio,
    the previous close is recovered exactly: P_prev = D / (1 - a). F_k must be a pure SEC share-count ratio."""
    return dividend / (1.0 - factor)


# ----------------------------------------------------------------------------------------------------------------
# Pass criteria
# ----------------------------------------------------------------------------------------------------------------

CRITERIA = {
    # Level S: every other price on the basis date is known (exact, or within +-0.5%: official close vs IEX last sale).
    'strong': {'min_w': 0.10, 'min_share': 0.95},
    'strong_noise0.5': {'min_w': 0.10, 'min_share': 0.95},
    # Level P: half of the other prices known, then bootstrap rounds; and the zero-knowledge bootstrap (public files +
    # public past month-end closes only). +-15% ~ a 90% band of one month of price moves: the public file must not
    # say more about today's price than last month's close already does.
    'partial50': {'min_w': 0.15, 'min_share': 0.95},
    'partial50+boot': {'min_w': 0.15, 'min_share': 0.95},
    'zero+boot': {'min_w': 0.15, 'min_share': 0.95},
}


def passes(summary, level):
    c = CRITERIA[level]
    key = {0.10: 'below_10pct', 0.15: 'below_15pct', 0.20: 'below_20pct'}[c['min_w']]
    return summary.get('n', 0) > 0 and 1.0 - summary[key] >= c['min_share']


def _fmt(x):
    if x is None:
        return '-'
    if x == math.inf:
        return 'inf'
    return '%.1f%%' % (100 * x)


def markdown_matrix(matrix):
    lines = ['| policy | attacker | median ±w | p05 ±w | p10 ±w | <±5% | <±10% | bounded both | pass |', '|---|---|---|---|---|---|---|---|---|']
    for aname in matrix:
        for pname, s in matrix[aname].items():
            ok = passes(s, aname) if aname in CRITERIA else None
            lines.append('| %s | %s | %s | %s | %s | %.0f%% | %.0f%% | %.0f%% | %s |' % (
                pname, aname, _fmt(s['median']), _fmt(s['p05']), _fmt(s['p10']), 100 * s['below_5pct'],
                100 * s['below_10pct'], 100 * s['bounded_both'], '-' if ok is None else ('PASS' if ok else 'FAIL')))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--n', type=int, default=500)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--days', type=int, default=20)
    ap.add_argument('--sample', type=int, default=0, help='targets per attacker for the matrix (0 = all)')
    ap.add_argument('--daily-sample', type=int, default=80)
    ap.add_argument('--rounds', type=int, default=5, help='bootstrap rounds for partial / zero-knowledge attackers')
    ap.add_argument('--json', type=str, default=None)
    a = ap.parse_args(argv)
    t0 = time.time()
    companies, quotes, sec_view = synthetic_universe(a.seed, a.n)
    rv = Review(companies, quotes, sec_view)
    targets = rv.targets if not a.sample else random.Random(a.seed + 1).sample(rv.targets, min(a.sample, len(rv.targets)))
    v_targets = [i for i in targets if rv.results[i]['axes']['V']['score'] is not None]
    out = {'synthetic': True, 'n': a.n, 'seed': a.seed, 'targets': len(targets), 'v_scored_targets': len(v_targets)}
    matrix, misses = scenario_policy_matrix(rv, v_targets, seed=a.seed, rounds=a.rounds)
    out['matrix'] = matrix
    out['truth_misses'] = misses
    out['reasons'] = scenario_reasons(rv, a.seed)
    out['own_history'], out['own_history_split_containment'] = scenario_own_history(rv, a.seed)
    out['backout'] = scenario_backout(rv)
    out['decode'] = scenario_decode(rv, seed=a.seed)
    out['daily'] = scenario_daily(companies, quotes, sec_view, a.days, a.daily_sample, a.seed) if a.days > 1 else None
    out['seconds'] = round(time.time() - t0, 1)
    print(markdown_matrix(matrix))
    print('truth misses:', misses, ' seconds:', out['seconds'])
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, default=lambda x: None if x == math.inf else str(x)), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
