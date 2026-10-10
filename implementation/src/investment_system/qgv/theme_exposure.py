"""Supplied SEC theme evidence and device overrides; Q/G/V unaffected.

No N-PORT fetch/identity inference, ETF recommendations or model connection.
Pending baskets/normalization remain NOT_AVAILABLE. Never serialize input text.
"""
import math
import re


def _number(value):
    try: return type(value) in (float, int) and math.isfinite(value)
    except OverflowError: return False


def _themes(config):
    if not isinstance(config, dict) or config.get('schema_version') != 1 or config.get('role') != 'EXPOSURE_ONLY' or (type(config.get('maximum_display')) is not int or config['maximum_display'] != 2) or not isinstance(config.get('config_version'), str): raise ValueError('THEME_CONFIG_INVALID')
    if config.get('membership_rule') is not None: raise ValueError('MEMBERSHIP_RULE_UNAPPROVED')
    themes = config.get('themes')
    if not isinstance(themes, list) or not 1 <= len(themes) <= 128: raise ValueError('THEME_CONFIG_INVALID')
    seen = set()
    for t in themes:
        if not isinstance(t, dict) or not isinstance(t.get('id'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', t['id']) or t['id'] in seen or not isinstance(t.get('name'), str) or not t['name'].strip(): raise ValueError('THEME_CONFIG_INVALID')
        seen.add(t['id']); etfs = t.get('etfs'); keywords = t.get('keywords')
        if not isinstance(etfs, list) or not isinstance(keywords, list): raise ValueError('THEME_CONFIG_INVALID')
        tickers = []
        for e in etfs:
            if not isinstance(e, dict) or not isinstance(e.get('ticker'), str) or not re.fullmatch(r'[A-Z][A-Z0-9.]{0,15}', e['ticker']) or e['ticker'] in tickers: raise ValueError('THEME_CONFIG_INVALID')
            tickers.append(e['ticker'])
        if any(not isinstance(k, str) or not k.strip() or len(k) > 128 for k in keywords) or len(set(keywords)) != len(keywords): raise ValueError('THEME_CONFIG_INVALID')
    return themes


def summarize_theme_exposure(*, config, etf_evidence, item1_text=None, market='US', industry_default=None, overrides=None):
    """Caller supplies source-verified, as-of eligible evidence for one issuer.

    ETF evidence rows: held bool, portfolio_weight 0..1 or None, SEC_NPORT.
    This function doesn't authenticate filing IDs, match securities or choose
    dates. All rule proposals remain inactive. Manual overrides are device-only.
    """
    themes = _themes(config)
    if not isinstance(etf_evidence, dict) or market not in ('US', 'KR', 'JP') or item1_text is not None and (not isinstance(item1_text, str) or len(item1_text) > 4_000_000): raise ValueError('INPUT_INVALID')
    if overrides is None: overrides = {}
    ids = {t['id'] for t in themes}
    if not isinstance(overrides, dict) or any(k not in ids or not _number(v) or not 0 <= v <= 1 for k, v in overrides.items()): raise ValueError('OVERRIDE_INVALID')
    result = {}; reasons = ['BASKET_APPROVAL_PENDING', 'MEMBERSHIP_NORMALIZATION_PENDING']
    if market != 'US': reasons.append('DART_EDINET_NOT_CONNECTED')
    for t in themes:
        held = 0; eligible = 0; weights = {}; invalid = False; missing = []; invalid_etfs = []
        for etf in t['etfs']:
            ticker = etf['ticker']; row = etf_evidence.get(ticker)
            if row is None: missing.append(ticker); continue
            if not isinstance(row, dict) or type(row.get('held')) is not bool or row.get('source') != 'SEC_NPORT': invalid = True; invalid_etfs.append(ticker); continue
            weight = row.get('portfolio_weight')
            if weight is not None and (not _number(weight) or not 0 <= weight <= 1) or row['held'] is False and weight not in (None, 0): invalid = True; invalid_etfs.append(ticker); continue
            eligible += 1
            if row['held']: held += 1; weights[ticker] = weight
        counts = None
        if market == 'US' and item1_text is not None:
            counts = {k: len(re.findall(r'(?<![A-Za-z0-9])' + re.escape(k) + r'(?![A-Za-z0-9])', item1_text, re.I)) for k in t['keywords']}
        # KR/JP evidence must not silently substitute for DART/EDINET coverage.
        if market != 'US': eligible = 0; weights = {}; counts = None; missing = [e['ticker'] for e in t['etfs']]; invalid_etfs = []
        member = overrides.get(t['id'])
        result[t['id']] = {'name': t['name'], 'membership': member,
            'state': 'DEVICE_PREVIEW' if member is not None else 'NOT_AVAILABLE',
            'membership_source': 'DEVICE_OVERRIDE' if member is not None else None,
            'held_etf_count': held if eligible else None, 'eligible_etf_count': eligible if market == 'US' else None,
            'missing_etfs': missing, 'invalid_etfs': invalid_etfs, 'reported_weights': weights, 'keyword_counts': counts,
            'reason_codes': ['ETF_EVIDENCE_INVALID'] if invalid else []}
    ordered = sorted((t for t in themes if overrides.get(t['id'], 0) > 0), key=lambda t: -overrides[t['id']])
    display = [{'id': t['id'], 'name': t['name'], 'membership': overrides[t['id']]} for t in ordered[:config['maximum_display']]]
    return {'role': 'EXPOSURE_ONLY', 'config_version': config['config_version'],
        'state': 'DEVICE_PREVIEW' if overrides else 'NOT_AVAILABLE', 'themes': result,
        'display': display, 'industry_default': industry_default if market != 'US' else None,
        'override_role': 'DEVICE_PREVIEW' if overrides else None, 'reason_codes': reasons}
