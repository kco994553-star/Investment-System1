"""Theme v0 membership and the device concentration reference (2026-10-11 user decision).

Membership: a company belongs to a theme when >=1 of the theme's basket ETFs holds it in the
latest supplied SEC N-PORT report, OR the Item 1 of its latest 10-K contains a theme keyword
(literal phrase rule of theme_exposure). Evidence kinds are recorded. "Not a member" is stated
only when every basket ETF was available and none holds it AND the keyword evidence is negative;
otherwise the value is None (NOT_AVAILABLE), never 0. Exposure only: Q/G/V are unaffected.

Pure functions. Item 1 text is RAM-only input and never returned. ETF weights, values and
quantities are not inputs at all. The concentration reference mirrors classification-screens.js
(shared vectors) and runs on device weights only; nothing here is published.
"""
import copy
import json
import math
import re
from pathlib import Path

from .theme_exposure import literal_phrase_counts

CONFIG_PATH = Path(__file__).with_name('theme_config_v0.json')
CONFIG_VERSION = 'theme_config/v0'
EVIDENCE = ('ETF', 'KEYWORD')
KEYWORD_STATES = ('AVAILABLE', 'TEN_K_NOT_FILED', 'NOT_AVAILABLE')
STATUSES = ('WARN', 'OK', 'INDETERMINATE')
_ID = re.compile(r'[a-z][a-z0-9_]{0,63}')
_TICKER = re.compile(r'[A-Z][A-Z0-9.]{0,15}')


def validate_theme_config_v0(cfg):
    if not isinstance(cfg, dict) or cfg.get('schema_version') != 1 or cfg.get('config_version') != CONFIG_VERSION:
        return ['THEME_CONFIG_INVALID']
    errors = []
    if cfg.get('status') != 'V0_UNCALIBRATED_DEFAULT' or cfg.get('role') != 'EXPOSURE_ONLY' or cfg.get('affects_qgv') is not False:
        errors.append('THEME_CONFIG_STATUS_INVALID')
    rule = cfg.get('membership_rule')
    if (not isinstance(rule, dict) or rule.get('kind') != 'ETF_HELD_OR_10K_ITEM1_KEYWORD' or rule.get('combination') != 'OR'
            or not isinstance(rule.get('keyword_evidence'), dict) or rule['keyword_evidence'].get('minimum_count') != 1
            or not isinstance(rule.get('etf_evidence'), dict) or rule['etf_evidence'].get('minimum_etfs_holding') != 1):
        errors.append('THEME_RULE_INVALID')
    warn = cfg.get('concentration_warning')
    if (not isinstance(warn, dict) or type(warn.get('single_theme_max_share')) is not float
            or not 0 < warn['single_theme_max_share'] < 1 or warn.get('comparison') != 'GREATER_THAN'
            or warn.get('scope') != 'DEVICE_RAM_ONLY'):
        errors.append('THEME_CONCENTRATION_INVALID')
    themes = cfg.get('themes')
    if not isinstance(themes, list) or not 1 <= len(themes) <= 128:
        return errors + ['THEME_CONFIG_INVALID']
    seen = set()
    for t in themes:
        if (not isinstance(t, dict) or not isinstance(t.get('id'), str) or not _ID.fullmatch(t['id']) or t['id'] in seen
                or not isinstance(t.get('name'), str) or not t['name'].strip()
                or not isinstance(t.get('name_en'), str) or not t['name_en'].strip()
                or t.get('evidence_strength') not in ('STANDARD', 'WEAK')):
            return errors + ['THEME_INVALID']
        seen.add(t['id'])
        etfs, keywords = t.get('etfs'), t.get('keywords')
        if not isinstance(etfs, list) or not etfs or not isinstance(keywords, list) or not keywords:
            return errors + ['THEME_INVALID']
        tickers = [e.get('ticker') if isinstance(e, dict) else None for e in etfs]
        if any(not isinstance(x, str) or not _TICKER.fullmatch(x) for x in tickers) or len(set(tickers)) != len(tickers):
            return errors + ['THEME_ETF_INVALID']
        if any(not isinstance(k, str) or not k.strip() or len(k) > 128 for k in keywords) or len(set(keywords)) != len(keywords):
            return errors + ['THEME_KEYWORD_INVALID']
    return errors


def load_theme_config_v0():
    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    errors = validate_theme_config_v0(cfg)
    if errors:
        raise ValueError('|'.join(errors))
    return copy.deepcopy(cfg)


def basket_tickers(config):
    """All basket ETF tickers in config order, without duplicates."""
    return list(dict.fromkeys(e['ticker'] for t in config['themes'] for e in t['etfs']))


def theme_memberships(config, *, etf_securities, company_securities, keyword_state, item1_text=None):
    """One company's v0 memberships.

    etf_securities: {ticker: frozenset of 'ISIN:..'/'CUSIP:..' for eligible holdings, or None if unavailable}.
    company_securities: frozenset of the company's own identifiers, or None (no exact join possible).
    keyword_state: AVAILABLE (item1_text supplied), TEN_K_NOT_FILED (submissions show no 10-K) or NOT_AVAILABLE.
    """
    if keyword_state not in KEYWORD_STATES or (keyword_state == 'AVAILABLE') != isinstance(item1_text, str):
        raise ValueError('KEYWORD_EVIDENCE_INVALID')
    if company_securities is not None and (not isinstance(company_securities, frozenset) or not company_securities):
        raise ValueError('COMPANY_SECURITIES_INVALID')
    if not isinstance(etf_securities, dict) or any(v is not None and not isinstance(v, frozenset) for v in etf_securities.values()):
        raise ValueError('ETF_EVIDENCE_INVALID')
    out = {}
    for t in config['themes']:
        held, complete = [], company_securities is not None
        for e in t['etfs']:
            securities = etf_securities.get(e['ticker'])
            if securities is None or company_securities is None:
                complete = False
                continue
            if securities & company_securities:
                held.append(e['ticker'])
        keyword_hit = keyword_state == 'AVAILABLE' and any(n >= 1 for n in literal_phrase_counts(item1_text, t['keywords']).values())
        evidence = (['ETF'] if held else []) + (['KEYWORD'] if keyword_hit else [])
        if evidence:
            member = True
        elif complete and keyword_state in ('AVAILABLE', 'TEN_K_NOT_FILED'):
            member = False
        else:
            member = None
        out[t['id']] = {'member': member, 'evidence': evidence, 'etfs': held}
    return out


def _weight(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def concentration_status(exposure, unknown, threshold):
    """WARN when the known share already exceeds the threshold; OK only when even all unknown share could not."""
    if exposure > threshold:
        return 'WARN'
    if exposure + unknown > threshold:
        return 'INDETERMINATE'
    return 'OK'


def theme_concentration(*, rows, memberships, theme_ids, threshold):
    """Device reference: rows=[{'company_id', 'weight'}] (ACTUAL shares, RAM); memberships={company_id: {theme: bool|None}}.

    A holding with a missing record or a None membership counts as unknown share, never as 0.
    Sums run in row order so Python and JS give identical doubles.
    """
    if type(threshold) is not float or not 0 < threshold < 1:
        raise ValueError('THRESHOLD_INVALID')
    usable = [r for r in rows if _weight(r.get('weight'))]
    themes = []
    for tid in theme_ids:
        exposure = 0.0
        unknown = 0.0
        for r in usable:
            rec = memberships.get(r.get('company_id')) if isinstance(r.get('company_id'), str) else None
            member = rec.get(tid) if isinstance(rec, dict) else None
            if member is True:
                exposure += r['weight']
            elif member is not False:
                unknown += r['weight']
        themes.append({'id': tid, 'exposure': exposure, 'unknown': unknown,
                       'status': concentration_status(exposure, unknown, threshold)})
    order = {tid: i for i, tid in enumerate(theme_ids)}
    warnings = [t['id'] for t in sorted((t for t in themes if t['status'] == 'WARN'), key=lambda t: (-t['exposure'], order[t['id']]))]
    return {'threshold': threshold, 'themes': themes, 'warnings': warnings}
