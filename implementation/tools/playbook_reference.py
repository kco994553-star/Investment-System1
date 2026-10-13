#!/usr/bin/env python3
"""Synthetic Python reference vectors for the signal playbook engine (PlaybookEngine.evaluate/transition/criteria/
classifyTypesV0/sectorFor).

Usage: playbook_reference.py --write   (regenerates tests/fixtures/playbook_reference_v1.json)
Every fact below is invented for tests (scores, weights, ranks); never a real holding or price.
Coverage (PLAYBOOK_V1.md §11-7): each code's entry condition, the co-occurrence pairs R2+R3, U1+E1, T2+E3,
R1+확신 유지, every §4 transition row, per-type thresholds, multi-type conflicts and the five §6-4 special rules.
"""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.qgv import playbook as P  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/playbook_reference_v1.json'

BASE = {
    'symbol': 'SYN1', 'held': True, 'watched': False,
    'memberships': {'growth': 0.0, 'value': 0.0, 'dividend': 0.0, 'quality': 0.0, 'cyclical': 0.0, 'defensive': 0.0, 'leader': 0.0},
    'sector': 'software_internet',
    'data': {'price_missing': False, 'fx_missing': False, 'snapshot_missing': False},
    'coverage': 'READY', 'coverage_prev': 'READY', 'user_excluded': False, 'user_hold': False,
    'conviction': None, 'conviction_total_pct': None,
    'q_now': 70, 'q_prev': 70, 'g_now': 60, 'g_prev': 60, 'v_now': 50, 'v_prev20': 50, 'dividend_cut': False,
    'excess_20': -0.01, 'excess_mean_252': 0.0, 'excess_sd_252': 0.02,
    'actual_pct': 5.0, 'target_pct': 5.0,
    'earnings_days_until': 40, 'earnings_pending_reflection': False, 'type_changed': False, 'leaderboard_signal': None,
    'followup_due': False, 'quarterly_check_due': False, 'leaderboard_rank': 120,
    'operating_margin_5y_position': 0.5, 'q_decline_streak_quarters': 0, 'sector_marketcap_rank': 1,
    'theme_weight_pct': 20.0, 'safety_margin_pct': 30.0,
    'basis': 'v1', 'macro_state': 'NORMAL', 'own_value_worsened': None, 'v_industry_pct': 80, 'expectation_check_passed': True,
    'value_trap_gate': False, 'market_explained_ratio_60': 0.5, 'q_industry_pct': 60, 'net_debt_to_ebitda': 0.5, 'interest_coverage': 20,
    'qg_source_missing': False, 'post_earnings_check_due': False, 'thirteenf_full_exit_managers': 0, 'structural_news': False,
}


def sit(**over):
    s = copy.deepcopy(BASE)
    for k, v in over.items():
        if k == 'memberships':
            s['memberships'].update(v)
        else:
            s[k] = v
    return s


def cases():
    c = []

    def ev(case_id, mode='ALL', **over):
        c.append({'id': case_id, 'synthetic': True, 'operation': 'evaluate', 'input': {'situation': sit(**over), 'mode': mode}})

    def tr(case_id, frm, choice, ctx=None):
        c.append({'id': case_id, 'synthetic': True, 'operation': 'transition', 'input': {'from': frm, 'choice': choice, 'ctx': ctx or {}}})

    def cr(case_id, code, facts, ctx=None):
        c.append({'id': case_id, 'synthetic': True, 'operation': 'criteria', 'input': {'code': code, 'facts': facts, 'ctx': ctx or {}}})

    conv = {'active': True, 'invalidated': False, 'months_held': 3, 'risk_review_count': 0}
    # --- entry conditions, one per code ---
    ev('quiet-held-no-code')
    ev('X1-price-and-fx-missing', data={'price_missing': True, 'fx_missing': True, 'snapshot_missing': False})
    ev('X1-snapshot-missing', data={'price_missing': False, 'fx_missing': False, 'snapshot_missing': True})
    ev('X2-coverage-blocked', coverage='BLOCKED')
    ev('X3-user-excluded', user_excluded=True)
    ev('R1-conviction-invalidated', conviction=dict(conv, invalidated=True), conviction_total_pct=10)
    ev('R2-qg-average-drop-at-threshold', q_now=65, g_now=55)
    ev('R2-qg-drop-just-below', q_now=66, g_now=55)
    ev('R2-unknown-q-prev', q_prev=None)
    ev('R3-abnormal-drop', excess_20=-0.05)
    ev('R3-boundary-not-below', excess_20=-0.04)
    ev('R3-unknown-sector-etf', excess_20=None, excess_mean_252=None, excess_sd_252=None)
    ev('R4-ready-to-partial', coverage='PARTIAL', coverage_prev='READY')
    ev('R5-user-hold', user_hold=True)
    ev('T1-v-down-10-default', v_now=40)
    ev('T1-v-down-9-no-code', v_now=41)
    ev('T2-overweight-v-stable', actual_pct=6.5)
    ev('T2-overweight-at-band-no-code', actual_pct=6.0)
    ev('T2-overweight-v-unknown', actual_pct=6.5, v_now=None)
    ev('T3-conviction-cap', conviction=conv, conviction_total_pct=31)
    ev('T3-conviction-at-cap-no-code', conviction=conv, conviction_total_pct=30)
    ev('U1-v-up-10-default', v_now=60)
    ev('U2-underweight', actual_pct=3.5)
    ev('U2-target-without-actual', actual_pct=None)
    ev('E1-seven-days-before', earnings_days_until=7)
    ev('E1-eight-days-no-code', earnings_days_until=8)
    ev('E1-pending-reflection', earnings_days_until=None, earnings_pending_reflection=True)
    ev('E2-type-changed', type_changed=True)
    ev('E3-coverage-partial-steady', coverage='PARTIAL', coverage_prev='PARTIAL')
    ev('E4-near-trigger', leaderboard_signal='NEAR_TRIGGER')
    ev('E4-reassess', leaderboard_signal='REASSESS')
    ev('E4-other-signal-no-code', leaderboard_signal='TRIGGERED')
    ev('E5-followup-due', followup_due=True)
    ev('H1-quarterly-no-signal', quarterly_check_due=True)
    ev('H1-suppressed-by-signal', quarterly_check_due=True, followup_due=True)
    ev('H2-twelve-months', conviction=dict(conv, months_held=12), conviction_total_pct=10)
    ev('H2-two-risk-reviews', conviction=dict(conv, risk_review_count=2), conviction_total_pct=10)
    ev('W1-watch-not-held', held=False, watched=True, actual_pct=None, target_pct=None)
    ev('W2-entry-candidate', held=False, watched=False, actual_pct=None, target_pct=None, leaderboard_rank=50, v_now=60)
    ev('W2-rank-51-no-code', held=False, watched=False, actual_pct=None, target_pct=None, leaderboard_rank=51, v_now=60)
    ev('W1-and-W2-watch-candidate', held=False, watched=True, actual_pct=None, target_pct=None, leaderboard_rank=10, v_now=60)
    ev('W2-margin-unknown-entry-disabled', held=False, actual_pct=None, target_pct=None, leaderboard_rank=10, v_now=60, safety_margin_pct=None)
    # --- co-occurrence (§2) ---
    ev('R2+R3-primary-R2', q_now=60, excess_20=-0.08)
    ev('U1+E1-trades-on-hold', v_now=60, earnings_days_until=3)
    ev('T2+E3-expansion-off', actual_pct=6.5, coverage='PARTIAL', coverage_prev='PARTIAL')
    ev('R1+conviction-keep-removed', conviction=dict(conv, invalidated=True), conviction_total_pct=10, q_now=60)
    ev('R2-conviction-keep-offered', conviction=conv, conviction_total_pct=10, q_now=60)
    ev('R3-conviction-keep-offered', conviction=conv, conviction_total_pct=10, excess_20=-0.08)
    ev('T1-conviction-keep-offered', conviction=conv, conviction_total_pct=10, v_now=40)
    ev('U2+R3-down-disables-up', actual_pct=3.5, excess_20=-0.08)
    ev('X1+R1-E1-not-holding-block', data={'price_missing': True, 'fx_missing': False, 'snapshot_missing': False}, earnings_days_until=1)
    ev('R1+E1-exception', conviction=dict(conv, invalidated=True), conviction_total_pct=10, earnings_days_until=1)
    ev('U1-margin-below-type', v_now=60, safety_margin_pct=14.9)
    ev('U1-margin-unknown', v_now=60, safety_margin_pct=None)
    # --- per-type thresholds (§6-1) ---
    ev('growth-G-alone-7', memberships={'growth': 1.0}, g_now=53)
    ev('growth-v-up-14-no-U1', memberships={'growth': 1.0}, v_now=64)
    ev('growth-v-up-15-U1', memberships={'growth': 1.0}, v_now=65, safety_margin_pct=10)
    ev('value-Q-alone-4', memberships={'value': 1.0}, q_now=66)
    ev('dividend-cut-immediate', memberships={'dividend': 1.0}, dividend_cut=True)
    ev('dividend-cut-unknown', memberships={'dividend': 1.0}, dividend_cut=None)
    ev('quality-Q-alone-3', memberships={'quality': 1.0}, q_now=67)
    ev('quality-qg-5-not-R2', memberships={'quality': 1.0}, q_now=68, g_now=52)
    ev('cyclical-qg-8', memberships={'cyclical': 1.0}, q_now=62, g_now=52)
    ev('cyclical-qg-7-not-R2', memberships={'cyclical': 1.0}, q_now=63, g_now=53)
    ev('defensive-qg-4', memberships={'defensive': 1.0}, q_now=66, g_now=56)
    ev('membership-below-floor-default', memberships={'growth': 0.29}, g_now=53)
    ev('memberships-all-unknown', memberships={'growth': None, 'value': None, 'dividend': None, 'quality': None, 'cyclical': None, 'defensive': None, 'leader': None})
    # --- multiple types (§6-3) ---
    ev('multi-tie-cyclical-wins', memberships={'growth': 1.0, 'cyclical': 1.0}, v_now=40)
    ev('multi-higher-membership-wins', memberships={'growth': 1.0, 'cyclical': 0.6}, v_now=40)
    ev('multi-strictest-expansion', memberships={'growth': 1.0, 'value': 0.5}, v_now=62, safety_margin_pct=20)
    ev('multi-r2-any-type', memberships={'growth': 0.8, 'quality': 0.5}, q_now=67)
    # --- special rules (§6-4) ---
    ev('special-cyclical-peak', memberships={'cyclical': 1.0}, actual_pct=3.5, operating_margin_5y_position=0.8)
    ev('special-cyclical-peak-unknown', memberships={'cyclical': 1.0}, actual_pct=3.5, operating_margin_5y_position=None)
    ev('special-value-trap', memberships={'value': 1.0}, v_now=60, q_decline_streak_quarters=3)
    ev('special-leader-rank-question', memberships={'leader': 1.0}, q_now=60, sector_marketcap_rank=4)
    ev('special-dividend-cut-R2', memberships={'dividend': 0.6, 'growth': 0.9}, dividend_cut=True)
    ev('special-theme-concentration', held=False, actual_pct=None, target_pct=None, leaderboard_rank=5, v_now=60, theme_weight_pct=40.1)
    ev('financial-sector-W2-off', held=False, actual_pct=None, target_pct=None, leaderboard_rank=5, v_now=60, sector='financials')
    # --- §0-1 core v0 scope (default mode) ---
    ev('core-T1-candidate-only', 'CORE_V0', v_now=40)
    u3 = dict(macro_state='WARNING', market_explained_ratio_60=0.7, q_industry_pct=50, net_debt_to_ebitda=1.4, interest_coverage=8.1, v_now=60)
    ev('core-U1-candidate-U3-active', 'CORE_V0', **u3)
    ev('core-T2-off-before-target-v1', 'CORE_V0', actual_pct=6.5)
    ev('core-T2-on-with-target-v1', 'CORE_V0', actual_pct=6.5, target_version='v1')
    ev('core-U2-on-with-target-v1', 'CORE_V0', actual_pct=3.5, target_version='v1')
    ev('core-R1-any-holding', 'CORE_V0', invalidation_triggered=True)
    ev('core-R2-no-conviction-keep', 'CORE_V0', conviction={'active': True, 'invalidated': False, 'months_held': 13, 'risk_review_count': 0},
       conviction_total_pct=40, q_now=60)
    ev('core-H1-with-candidate-only', 'CORE_V0', quarterly_check_due=True, v_now=40)
    ev('core-E4-candidate', 'CORE_V0', leaderboard_signal='REASSESS', structural_news=True)
    ev('core-W2-candidate-not-held', 'CORE_V0', held=False, actual_pct=None, target_pct=None, leaderboard_rank=5, v_now=60)
    # --- §16 portfolio limits ---
    for case_id, rows, cash in [
            ('limits-ok-ten-at-10', [{'symbol': 'S%d' % i, 'pct': 10, 'sector': sec} for i, sec in enumerate(
                ['semiconductors', 'semi_equipment', 'software_internet', 'software_internet', 'defense', 'medical_devices', 'power_equipment',
                 'industrial_automation', 'ecommerce_consumer', 'energy'])], 0),
            ('limits-semis-combined-over-40', [{'symbol': 'S%d' % i, 'pct': 9, 'sector': sec} for i, sec in enumerate(
                ['semiconductors', 'semiconductors', 'semi_equipment', 'semi_equipment', 'semi_equipment', 'software_internet', 'defense',
                 'medical_devices', 'energy', 'utilities'])], 10),
            ('limits-single-over-10-and-few', [{'symbol': 'A', 'pct': 10.5, 'sector': 'energy'}, {'symbol': 'B', 'pct': 4.5, 'sector': 'utilities'}], 85),
            ('limits-unknown-sector', [{'symbol': 'S%d' % i, 'pct': 10, 'sector': None if i == 0 else 'energy%d' % i} for i in range(10)], 0),
            ('limits-sum-not-100', [{'symbol': 'S%d' % i, 'pct': 9, 'sector': 'x%d' % i} for i in range(10)], 5)]:
        c.append({'id': case_id, 'synthetic': True, 'operation': 'portfolio_limits', 'input': {'rows': rows, 'cash_pct': cash}})
    # --- §13-4 Band ---
    ev('band-target-9-inside-1.8', target_pct=9.0, actual_pct=10.7)
    ev('band-target-9-T2-outside-1.8', target_pct=9.0, actual_pct=10.9)
    ev('band-target-9-U2-outside-1.8', target_pct=9.0, actual_pct=7.1)
    ev('band-target-4.5-floor-1pp', target_pct=4.5, actual_pct=3.4)
    # --- §13-5 macro + U3 ---
    ev('U3-warning-all-five', **u3)
    ev('U3-crisis-all-five', **dict(u3, macro_state='CRISIS'))
    ev('U3-normal-no-code', **dict(u3, macro_state='NORMAL'))
    ev('U3-r3-fired-blocks', **dict(u3, excess_20=-0.08))
    ev('U3-explained-below-70', **dict(u3, market_explained_ratio_60=0.69))
    ev('U3-quality-below-50', **dict(u3, q_industry_pct=49))
    ev('U3-debt-1.5-fails', **dict(u3, net_debt_to_ebitda=1.5))
    ev('U3-coverage-8-fails', **dict(u3, interest_coverage=8))
    ev('U3-unknown-ratio', **dict(u3, market_explained_ratio_60=None))
    ev('U3-macro-unknown', **dict(u3, macro_state=None))
    ev('macro-warning-cyclical-stops-expansion', memberships={'cyclical': 1.0}, macro_state='WARNING', actual_pct=3.5, operating_margin_5y_position=0.1)
    ev('macro-warning-noncyclical-split-x2', macro_state='WARNING', actual_pct=3.5)
    ev('macro-crisis-stops-U1-U2', macro_state='CRISIS', actual_pct=3.5, v_now=60, market_explained_ratio_60=0.2)
    ev('macro-crisis-W2-off', held=False, actual_pct=None, target_pct=None, leaderboard_rank=5, v_now=60, macro_state='CRISIS', market_explained_ratio_60=0.2)
    ev('macro-crisis-W2-allowed-u3-2-5', held=False, actual_pct=None, target_pct=None, leaderboard_rank=5, v_now=60, macro_state='CRISIS',
       market_explained_ratio_60=0.8, excess_20=-0.01)
    ev('U3-cyclical-crisis-peak-ignored', **dict(u3, macro_state='CRISIS', memberships={'cyclical': 1.0}, operating_margin_5y_position=0.95))
    # --- §14 v2 basis ---
    ev('v2-R2-percentile-10-own-worse', basis='v2', q_now=60, g_now=50, own_value_worsened=True)
    ev('v2-R2-relative-only-E4', basis='v2', q_now=60, g_now=50, own_value_worsened=False)
    ev('v2-R2-own-unknown-E4', basis='v2', q_now=60, g_now=50, own_value_worsened=None)
    ev('v2-qg-drop-9-no-R2', basis='v2', q_now=61, g_now=51, v_now=60)
    ev('v2-quality-Q-6', basis='v2', memberships={'quality': 1.0}, q_now=64, own_value_worsened=True)
    ev('v2-dividend-cut-immediate', basis='v2', memberships={'dividend': 1.0}, dividend_cut=True, own_value_worsened=False)
    ev('v2-U1-v-pct-below-standard', basis='v2', v_now=60, v_industry_pct=59)
    ev('v2-U1-expectation-failed', basis='v2', v_now=60, expectation_check_passed=False)
    ev('v2-U1-core-unknown', basis='v2', v_now=60, v_industry_pct=None)
    ev('v2-U1-value-75-strictest', basis='v2', memberships={'growth': 1.0, 'value': 0.5}, v_now=65, v_industry_pct=74)
    ev('v2-value-trap-gate', basis='v2', v_now=60, value_trap_gate=True)
    ev('v2-value-trap-gate-U3', basis='v2', value_trap_gate=True, **u3)
    ev('v2-gate-unknown', basis='v2', v_now=60, value_trap_gate=None)
    ev('v1-value-trap-not-on-v2', basis='v2', memberships={'value': 1.0}, v_now=60, q_decline_streak_quarters=3, v_industry_pct=80)
    # --- §13-6/8/9 E4 causes, §13-7 missing Q·G ---
    ev('E4-13F-three-full-exits', thirteenf_full_exit_managers=3)
    ev('E4-13F-two-no-code', thirteenf_full_exit_managers=2)
    ev('E4-structural-news', structural_news=True)
    ev('E4-all-causes', leaderboard_signal='REASSESS', thirteenf_full_exit_managers=4, structural_news=True)
    ev('13-7-qg-missing-E3-fixed', symbol='042700', q_now=None, q_prev=None, g_now=None, g_prev=None, qg_source_missing=True)
    ev('13-7-post-earnings-H1', symbol='8035', q_now=None, q_prev=None, g_now=None, g_prev=None, qg_source_missing=True,
       quarterly_check_due=True, post_earnings_check_due=True)
    for case_id, args in [('e4-observe-50', [0.10, 0.20, 3, None]), ('e4-near-75', [0.75, 1.0, 5, None]), ('e4-reassess-100', [0.5, 0.5, 3, None]),
                          ('e4-none-below-50', [0.05, 0.20, 4, None]), ('e4-insufficient-history', [0.30, 0.20, 2.9, None]),
                          ('e4-user-override', [0.20, 0.50, 1, 0.20]), ('e4-user-not-reached', [0.19, 0.20, 5, 0.20])]:
        c.append({'id': case_id, 'synthetic': True, 'operation': 'e4_level', 'input': {'args': args}})
    # --- transitions (§4 every row, then §3 rows) ---
    for frm, choice in [('R1', 'R1_FILING'), ('R2', 'R2_THESIS_BROKEN'), ('R2', 'R2_COMPANY_GUIDANCE'), ('R2', 'R2_SECTOR_CYCLE'),
                        ('R2', 'R2_ONE_OFF'), ('R2', 'R2_NONE'), ('R3', 'R3_STRUCTURAL'), ('R3', 'R3_TEMPORARY'), ('R3', 'R3_UNDECIDABLE'),
                        ('T1', 'T1_MAINTAIN'), ('U1', 'U1_COMPANY'), ('U1', 'U1_UNCLEAR'), ('U2', 'U2_COMPANY'), ('U2', 'U2_UNCLEAR'),
                        ('E1', 'E1_REFLECTED'), ('E4', 'E4_CHANGED'), ('H1', 'H1_BROKEN'), ('W2', 'W2_PROCEED'),
                        ('R1', 'R1_NEWS'), ('T1', 'T1_REDUCE'), ('U1', 'U1_SECTOR_MARKET'), ('U2', 'U2_SECTOR_MARKET'), ('U2', 'U2_DEPOSIT'),
                        ('T2', 'T2_DEPOSIT'), ('T2', 'T2_TRIM'), ('T3', 'T3_TRIM'), ('E4', 'E4_NORMAL'), ('E5', 'E5_DIFFERENT'),
                        ('H1', 'H1_WEAKENED'), ('H2', 'H2_RELEASE'), ('R4', 'R4_OVERDUE')]:
        tr('tr-' + choice, frm, choice)
    tr('tr-R2_SECTOR_CYCLE-cyclical', 'R2', 'R2_SECTOR_CYCLE', {'memberships': {'cyclical': 1.0}})
    tr('tr-R2_NONE-value-30d', 'R2', 'R2_NONE', {'memberships': {'value': 1.0}})
    tr('tr-R3_TEMPORARY-v-improved', 'R3', 'R3_TEMPORARY', {'v_improved': True})
    tr('tr-U1_SECTOR_MARKET-growth-4-splits', 'U1', 'U1_SECTOR_MARKET', {'memberships': {'growth': 1.0}})
    tr('tr-U2_SECTOR_MARKET-defensive-2-splits', 'U2', 'U2_SECTOR_MARKET', {'memberships': {'defensive': 1.0}})
    tr('tr-unknown-row', 'X1', 'X1_WAIT')
    tr('tr-U3_STAGED', 'U3', 'U3_STAGED')
    tr('tr-U1-warning-splits-x2', 'U1', 'U1_SECTOR_MARKET', {'macro_state': 'WARNING'})
    tr('tr-W2-crisis-third', 'W2', 'W2_PROCEED', {'macro_state': 'CRISIS'})
    tr('tr-R2_NONE-v2-basis', 'R2', 'R2_NONE', {'basis': 'v2', 'memberships': {'defensive': 1.0}})
    # --- §3 ordered criteria ---
    cr('R2-majority-broken', 'R2', {'thesis_status': ['BROKEN', 'BROKEN', 'VALID']})
    cr('R2-half-broken-not-majority-needs-guidance', 'R2', {'thesis_status': ['BROKEN', 'VALID']})
    cr('R2-guidance-cut-peers-differ', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': True, 'peers_differ': True})
    cr('R2-sector-cycle', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': False, 'peers_differ': False, 'peers_same_direction': 2})
    cr('R2-one-off', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': False, 'peers_differ': True, 'peers_same_direction': 1, 'drop_excluding_one_offs': 2.4})
    cr('R2-one-off-boundary-none', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': False, 'peers_differ': True, 'peers_same_direction': 1, 'drop_excluding_one_offs': 2.5})
    cr('R2-quality-q-metric', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': False, 'peers_differ': True, 'peers_same_direction': 0, 'drop_excluding_one_offs': 1.4, 'drop_metric': 'q'}, {'memberships': {'quality': 1.0}})
    cr('R2-quality-qg-metric-missing', 'R2', {'thesis_status': ['VALID'], 'guidance_mid_lowered': False, 'peers_differ': True, 'peers_same_direction': 0, 'drop_excluding_one_offs': 1.0}, {'memberships': {'quality': 1.0}})
    cr('T1-expensive', 'T1', {'safety_margin_pct': -5, 'implied_growth': 0.2, 'actual_growth_3y': 0.1})
    cr('T1-else-maintain', 'T1', {'safety_margin_pct': 5, 'implied_growth': 0.2, 'actual_growth_3y': 0.1})
    cr('T1-unknown', 'T1', {'safety_margin_pct': None, 'implied_growth': 0.2})
    cr('T1-v2-reduce', 'T1', {'v_industry_pct': 29, 'expectation_check_passed': False}, {'basis': 'v2'})
    cr('T1-v2-pct-30-maintain', 'T1', {'v_industry_pct': 30, 'expectation_check_passed': False}, {'basis': 'v2'})
    cr('T1-v2-expectation-ok', 'T1', {'v_industry_pct': 10, 'expectation_check_passed': True}, {'basis': 'v2'})
    cr('T2-2pp-deposit', 'T2', {'excess_pp': 2})
    cr('T2-over-2pp-trim', 'T2', {'excess_pp': 2.1})
    cr('H1-one-broken', 'H1', {'thesis_status': ['BROKEN', 'VALID']})
    cr('H1-two-weakened', 'H1', {'thesis_status': ['WEAKENED', 'WEAKENED', 'VALID']})
    cr('H1-maintain', 'H1', {'thesis_status': ['WEAKENED', 'VALID']})
    cr('R5-release', 'R5', {'condition_met': True, 'extensions_used': 1})
    cr('R5-extend-once', 'R5', {'condition_met': False, 'extensions_used': 0})
    cr('R5-second-time-decide', 'R5', {'condition_met': False, 'extensions_used': 1})
    cr('W2-all-five', 'W2', {'checks': [True, True, True, True, True]})
    cr('W2-one-fails', 'W2', {'checks': [True, True, False, True, True]})
    cr('W2-unknown-item', 'W2', {'checks': [True, None, True, True, True]})
    cr('E2-not-mechanical', 'E2', {})
    # --- §6-2 type rules and §7 sector lookup ---
    for case_id, metrics in [
            ('types-quality-all-pass', {'roic_avg_3y': 0.2, 'operating_margin_std_5y_pp': 2, 'net_debt_to_ebitda': 1.0}),
            ('types-quality-one-fails', {'roic_avg_3y': 0.2, 'operating_margin_std_5y_pp': 3, 'net_debt_to_ebitda': 1.0}),
            ('types-quality-unknown', {'roic_avg_3y': 0.2, 'net_debt_to_ebitda': 1.0}),
            ('types-value-history-only', {'pe_discount_to_own_5y_avg': 0.25}),
            ('types-cyclical-semis', {'sector_subgroup': 'semiconductors'}),
            ('types-cyclical-volatility', {'sector_subgroup': 'software_internet', 'sector_group_candidate': None, 'revenue_volatility_5y_rank_pct': 0.7}),
            ('types-defensive-both', {'sector_group_candidate': 'DEFENSIVE', 'revenue_volatility_5y_rank_pct': 0.3}),
            ('types-defensive-not-candidate', {'sector_group_candidate': 'CYCLICAL', 'revenue_volatility_5y_rank_pct': 0.1})]:
        c.append({'id': case_id, 'synthetic': True, 'operation': 'classify_types_v0', 'input': {'metrics': metrics}})
    for case_id, symbol, etf in [('sector-doc-assignment', 'ETN', None), ('sector-user-assigned', '8035', None),
                                 ('sector-etf-unique', 'SYNX', 'XLV'), ('sector-etf-ambiguous', 'SYNY', 'XLI'), ('sector-none', 'SYNZ', None)]:
        c.append({'id': case_id, 'synthetic': True, 'operation': 'sector_for', 'input': {'symbol': symbol, 'etf': etf}})
    return c


def run(cfg, case):
    i = case['input']
    op = case['operation']
    if op == 'evaluate':
        return P.evaluate(cfg, i['situation'], i['mode'])
    if op == 'transition':
        return P.transition(cfg, i['from'], i['choice'], i['ctx'])
    if op == 'criteria':
        return P.criteria(cfg, i['code'], i['facts'], i['ctx'])
    if op == 'classify_types_v0':
        return P.classify_types_v0(cfg, i['metrics'])
    if op == 'portfolio_limits':
        return P.portfolio_limits(cfg, i['rows'], i['cash_pct'])
    if op == 'e4_level':
        return P.e4_level(cfg, *i['args'])
    if op == 'sector_for':
        return P.sector_for(cfg, i['symbol'], i['etf'])
    raise ValueError(op)


def build():
    cfg = P.load_config()
    out = []
    for case in cases():
        case['expected_json'] = json.dumps(run(cfg, case), ensure_ascii=False, sort_keys=True)
        out.append(case)
    return {'schema': 'playbook-reference/1', 'config_version': cfg['config_version'], 'cases': out}


if __name__ == '__main__':
    data = build()
    if '--write' in sys.argv:
        FIXTURE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(data['cases']), 'cases')
