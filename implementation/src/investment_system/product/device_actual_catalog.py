"""Public identity metadata for a device-only portfolio; never reads device data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP_PATH = 'docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json'
THEME_PATH = 'docs/strategy_theme_owner/v1_1_cycle_20261008/CURRENT_TARGET_THEME_ASSIGNMENTS.json'
TARGET_PATH = 'docs/portfolio_target_owner/TARGET_v0.yaml'
MAP_SHA256 = '5b68c5a884e54ae4aefaa18de935efb12f2dabeb0109d5c6039d9c5736a280ce'
TARGET_SHA256 = 'a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b'
THEME_SHA256 = '67c912ba5b0e5e3592a72cc713e07707e32517f749990b36e3ed284ced60b1f0'
THEME_EN = {'semi_equipment': 'Semiconductor equipment', 'ai_semi': 'AI and semiconductors',
            'big_tech': 'Big Tech', 'other_industrial': 'Other industrials'}


def reject_private_holdings(value) -> None:
    """Fail closed before any output is written; errors never echo input values."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            keys = {str(k).lower() for k in item}
            schema = item.get('schema', '')
            if (isinstance(schema, str) and schema.startswith('device-actual-holdings/')
                    or 'device_actual' in keys
                    or {'quantity', 'average_cost', 'currency'}.issubset(keys)):
                raise ValueError('private holdings are forbidden in a public build')
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def public_actual_catalog(root: Path = ROOT) -> dict:
    root = Path(root)
    raw = (root / MAP_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAP_SHA256:
        raise ValueError('identity source hash mismatch')
    target = (root / TARGET_PATH).read_bytes()
    if hashlib.sha256(target).hexdigest() != TARGET_SHA256:
        raise ValueError('TARGET source hash mismatch')
    mapping = json.loads(raw)
    theme_raw = (root / THEME_PATH).read_bytes()
    if hashlib.sha256(theme_raw).hexdigest() != THEME_SHA256:
        raise ValueError('theme source hash mismatch')
    assignments = json.loads(theme_raw)
    if (mapping['source_root_sha256'] != TARGET_SHA256
            or assignments['identity_map_sha256'] != MAP_SHA256
            or assignments['catalog_source_sha256'] != TARGET_SHA256
            or assignments['source_values_changed'] is not False):
        raise ValueError('identity source lineage mismatch')
    rows, members = mapping['rows'], assignments['assignments']
    if len(rows) != 19 or len(members) != 19:
        raise ValueError('identity source must contain the reviewed 19 instruments')
    instruments = []
    for index, (row, member) in enumerate(zip(rows, members)):
        source = row['target_row']
        if (row['row_index'] != index or member['row_index'] != index
                or row['mapping_status'] != 'RESOLVED_CURRENT_TARGET_SCOPE'
                or row['security_ref'] != member['security_ref']
                or source['theme_id'] != member['theme_id']
                or source['weight_units'] != member['weight_units']):
            raise ValueError('identity source membership mismatch')
        currency = row['current_listing_observation'].get('currency')
        if source['ticker_hint'] == '8035': currency = 'JPY'
        elif source['ticker_hint'] == '042700': currency = 'KRW'
        if currency not in {'USD', 'JPY', 'KRW'}:
            raise ValueError('identity source currency unavailable')
        instruments.append({'row_index': index, 'label': source['label'],
            'ticker': source['ticker_hint'], 'theme_id': source['theme_id'],
            'target_units': source['weight_units'],
            'security_reference': row['security_ref'], 'currency': currency})
    if (sum(i['target_units'] for i in instruments) + assignments['cash_units']
            != assignments['total_units']):
        raise ValueError('identity source denominator mismatch')
    catalog = {'schema': 'DEVICE_ACTUAL_CATALOG/1',
        'target_root_version': 'v0', 'target_root_sha256': TARGET_SHA256,
        'identity_map_version': mapping['version'], 'identity_map_sha256': MAP_SHA256,
        'total_units': assignments['total_units'],
        'themes': [{'theme_id': c['theme_id'], 'label': c['label'],
                    'label_en': THEME_EN[c['theme_id']], 'target_units': c['target_units']}
                   for c in assignments['catalog']], 'instruments': instruments}
    reject_private_holdings(catalog)
    return catalog
