"""Python reference for the device S13 custom type PREVIEW (web_assets/device-profiles.js).

Pure functions: published price-free metrics (company-types-pricefree.json) and published Q/G factors
(sec-qg-factors.json) under the official type_config copy versus a device-only custom copy. V needs prices,
so it stays None and type-adjusted scores stay unavailable. Nothing here is stored, published or used by the
forward ledger, virtual trading or official screens.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from .company_types import calculate_company_types
from .type_config import compile_custom_config

TARGET_IDS = ('asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft',
              'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok')
PILLARS = ('Q', 'G', 'V')


def official_copy():
    config = json.loads(Path(__file__).with_name('type_config_v1.json').read_text())
    config['status'] = 'CUSTOM_PREVIEW'
    return config


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _qg(factors):
    from investment_system.contracts.enums import ProfileKind, QualityState
    from investment_system.contracts.models import FactorObservation
    from .strategy_preview import recalculate_strategy_preview
    observations = {}
    for name, value in (factors or {}).items():
        if isinstance(value, dict) and value.get('score') is not None and value.get('state') != 'NOT_AVAILABLE':
            quality = QualityState('OK' if value.get('state') == 'LIVE' else 'STALE_DATA')
            observations[name] = FactorObservation(name, value['score'], value['score'], quality, 'device-type-preview')
    try:
        result = recalculate_strategy_preview(observations, None, ProfileKind.GENERAL_CORPORATE)
    except ValueError:
        return {'Q': None, 'G': None, 'V': None}
    score = lambda axis: result.axes[axis].score if axis in result.axes and _number(result.axes[axis].score) else None
    return {'Q': score('Q'), 'G': score('G'), 'V': None}


def type_preview(types_payload, qg_payload, custom):
    """Companies with at least one published finite metric, sorted by id (device typePreview)."""
    rows = ((types_payload or {}).get('data') or {}).get('companies') if isinstance(types_payload, dict) else None
    if not isinstance(rows, dict):
        return {'state': 'NOT_AVAILABLE', 'reason': 'PUBLIC_TYPE_METRICS_NOT_AVAILABLE', 'rows': []}
    try:
        official, mine = compile_custom_config(official_copy()), compile_custom_config(custom)
    except ValueError:
        return {'state': 'INVALID_INPUT', 'reason': 'TYPE_CONFIG_INVALID', 'rows': []}
    qg_rows = ((qg_payload or {}).get('data') or {}).get('companies') if isinstance(qg_payload, dict) else None
    out = []
    for cid, record in rows.items():
        metrics = {k: v for k, v in ((record or {}).get('metrics') or {}).items() if _number(v)}
        if not metrics:
            continue
        qgv = _qg(((qg_rows or {}).get(cid) or {}).get('factors'))

        def run(config):
            try:
                r = calculate_company_types(metrics=metrics, original_qgv=qgv, config=config)
            except ValueError:
                return None
            return {'selected_types': r['selected_types'], 'weights': r['weights'],
                    'adjusted_score': r['adjusted_score'], 'reason_codes': r['reason_codes']}
        out.append({'company_id': cid, 'official': run(official), 'mine': run(mine)})
    out.sort(key=lambda r: r['company_id'])
    return {'state': 'PREVIEW' if out else 'NOT_AVAILABLE', 'reason': None if out else 'PUBLIC_TYPE_METRICS_NOT_AVAILABLE', 'rows': out}


def _same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if _number(a) and _number(b):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def config_diff(official, custom):
    """Changed leaves (status excluded). Arrays of objects with ids are matched by id."""
    out = []

    def is_obj(x):
        return isinstance(x, dict)

    def walk(a, b, path):
        if path == 'status':
            return
        if isinstance(a, list) and isinstance(b, list) and all(is_obj(x) and isinstance(x.get('id'), str) for x in a + b):
            ids = list(dict.fromkeys([x['id'] for x in a] + [x['id'] for x in b]))
            for i in ids:
                walk(next((x for x in a if x['id'] == i), None), next((x for x in b if x['id'] == i), None), path + '.' + i)
            return
        if is_obj(a) and is_obj(b):
            for key in sorted(set(a) | set(b)):
                walk(a.get(key), b.get(key), path + '.' + key if path else key)
            return
        if not _same(a, b):
            out.append({'path': path, 'official': copy.deepcopy(a), 'mine': copy.deepcopy(b)})
    walk(official, custom, '')
    return out


def target_type_preview(types_payload, qg_payload, custom, ids=TARGET_IDS):
    """Every TARGET company: official vs custom types and Q/G/V weights, or NOT_AVAILABLE with a reason."""
    base = type_preview(types_payload, qg_payload, custom)
    if base['state'] == 'INVALID_INPUT':
        return {'state': 'INVALID_INPUT', 'reason': base['reason'], 'rows': [], 'diff': []}
    by_id = {r['company_id']: r for r in base['rows']}
    companies = ((types_payload or {}).get('data') or {}).get('companies') if isinstance(types_payload, dict) else None
    rows = []
    for cid in ids:
        r = by_id.get(cid)
        if r is None:
            reason = 'COMPANY_NOT_IN_PUBLIC_FILE' if isinstance(companies, dict) and cid not in companies else 'PUBLIC_TYPE_METRICS_NOT_AVAILABLE'
            rows.append({'company_id': cid, 'state': 'NOT_AVAILABLE', 'reason': reason, 'official': None, 'mine': None, 'types_changed': None, 'weight_delta': None})
        elif r['official'] is None or r['mine'] is None:
            rows.append({'company_id': cid, 'state': 'NOT_AVAILABLE', 'reason': 'TYPE_ENGINE_INVALID_INPUT', 'official': None, 'mine': None, 'types_changed': None, 'weight_delta': None})
        else:
            rows.append({'company_id': cid, 'state': 'PREVIEW', 'reason': None, 'official': r['official'], 'mine': r['mine'],
                         'types_changed': r['official']['selected_types'] != r['mine']['selected_types'],
                         'weight_delta': {p: r['mine']['weights'][p] - r['official']['weights'][p] for p in PILLARS}})
    ok = any(r['state'] == 'PREVIEW' for r in rows)
    return {'state': 'PREVIEW' if ok else 'NOT_AVAILABLE', 'reason': None if ok else 'PUBLIC_TYPE_METRICS_NOT_AVAILABLE',
            'rows': rows, 'diff': config_diff(official_copy(), custom)}
