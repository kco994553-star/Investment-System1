"""SEC SIC -> industry group, v0 (2026-10-11 user decision). Pure, no IO beyond the packaged config.

The draft table is adopted as an uncalibrated default. It is not a cyclical/defensive classification:
only the table's explicit candidate labels are carried, and the membership itself stays NOT_AVAILABLE
(type_config/1 still lists the revenue-volatility ramp and combination as unresolved). Missing SIC,
0000 or a SIC outside every range is NOT_AVAILABLE, never 0 or a guessed group. No GICS data.
"""
import copy
import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name('sic_industry_groups_v0.json')
CONFIG_VERSION = 'sic_industry_groups/v0'
CANDIDATES = ('CYCLICAL_CANDIDATE', 'DEFENSIVE_CANDIDATE')
_ID = re.compile(r'[a-z][a-z0-9_]{0,63}')


def _ranges(value):
    if not isinstance(value, list) or not value:
        return None
    out = []
    for r in value:
        if (not isinstance(r, list) or len(r) != 2 or any(type(x) is not int for x in r)
                or not 1 <= r[0] <= r[1] <= 9999):
            return None
        out.append((r[0], r[1]))
    return out


def validate_sic_config(cfg):
    """Return reason codes; an empty list means usable."""
    errors = []
    if not isinstance(cfg, dict) or cfg.get('schema_version') != 1 or cfg.get('config_version') != CONFIG_VERSION:
        return ['SIC_CONFIG_INVALID']
    if cfg.get('status') != 'V0_UNCALIBRATED_DEFAULT' or cfg.get('gics_used') is not False:
        errors.append('SIC_CONFIG_STATUS_INVALID')
    groups, subs = cfg.get('groups'), cfg.get('subgroups')
    if not isinstance(groups, list) or not groups or not isinstance(subs, list):
        return errors + ['SIC_CONFIG_INVALID']
    seen, spans = set(), []
    for g in groups:
        ranges = _ranges(g.get('sic_ranges')) if isinstance(g, dict) else None
        if (ranges is None or not isinstance(g.get('id'), str) or not _ID.fullmatch(g['id']) or g['id'] in seen
                or not isinstance(g.get('name'), str) or not g['name'].strip()
                or not isinstance(g.get('name_en'), str) or not g['name_en'].strip()
                or g.get('cyclical_defensive_candidate') not in (None,) + CANDIDATES):
            return errors + ['SIC_GROUP_INVALID']
        seen.add(g['id'])
        spans.extend((lo, hi, g['id']) for lo, hi in ranges)
    spans.sort()
    if any(a[1] >= b[0] for a, b in zip(spans, spans[1:])):
        errors.append('SIC_GROUP_OVERLAP')
    sub_seen, sub_spans = set(), []
    for s in subs:
        ranges = _ranges(s.get('sic_ranges')) if isinstance(s, dict) else None
        if (ranges is None or not isinstance(s.get('id'), str) or not _ID.fullmatch(s['id']) or s['id'] in sub_seen
                or s.get('group') not in seen or not isinstance(s.get('name'), str) or not s['name'].strip()
                or not isinstance(s.get('name_en'), str) or not s['name_en'].strip()):
            return errors + ['SIC_SUBGROUP_INVALID']
        sub_seen.add(s['id'])
        for lo, hi in ranges:
            if not any(glo <= lo and hi <= ghi and gid == s['group'] for glo, ghi, gid in spans):
                errors.append('SIC_SUBGROUP_OUTSIDE_GROUP')
            sub_spans.append((lo, hi))
    sub_spans.sort()
    if any(a[1] >= b[0] for a, b in zip(sub_spans, sub_spans[1:])):
        errors.append('SIC_SUBGROUP_OVERLAP')
    return list(dict.fromkeys(errors))


def load_sic_config():
    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    errors = validate_sic_config(cfg)
    if errors:
        raise ValueError('|'.join(errors))
    return copy.deepcopy(cfg)


def normalize_sic(value):
    """SEC submissions carry SIC as a string such as '3674'. Return 4 digits, or None if missing/0000."""
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,4}', value.strip()):
        return None
    code = value.strip().zfill(4)
    return None if code == '0000' else code


def classify_sic(value, config=None):
    """{'sic','group','subgroup','cyclical_defensive_candidate','reason_code'}; no guessing."""
    cfg = load_sic_config() if config is None else config
    sic = normalize_sic(value)
    out = {'sic': sic, 'group': None, 'subgroup': None, 'cyclical_defensive_candidate': None, 'reason_code': None}
    if sic is None:
        out['reason_code'] = 'SIC_NOT_AVAILABLE'
        return out
    code = int(sic)
    group = next((g for g in cfg['groups'] if any(lo <= code <= hi for lo, hi in g['sic_ranges'])), None)
    if group is None:
        out['reason_code'] = 'SIC_UNMATCHED'
        return out
    sub = next((s for s in cfg['subgroups'] if s['group'] == group['id']
                and any(lo <= code <= hi for lo, hi in s['sic_ranges'])), None)
    out.update(group=group['id'], subgroup=sub['id'] if sub else None,
               cyclical_defensive_candidate=group['cyclical_defensive_candidate'])
    return out
