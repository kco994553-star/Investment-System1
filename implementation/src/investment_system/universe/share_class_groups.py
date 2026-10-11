"""Device-side `share_class_groups/v0` config (Python copy of web_assets/share-class-groups.js).

User decision 2026-10-11: listed share classes of one issuer that carry the same
per-share economic rights (voting may differ) are summed into one company
market cap and ranked once; every other SHARE_CLASS_BASIS / BASIS_UNCONFIRMED
listing stays excluded. Groups are keyed by SEC CIK and the exact Universe504
listing codes. Classes with a conversion ratio other than 1 (e.g. BRK.A/BRK.B)
are never listed here. `cover_class_count` is the number of classes the
filing cover must report; a cover class without a Universe listing (Alphabet
Class B) is not priced and not included — the screen says so. V0_UNCALIBRATED:
editable later; not a calibrated policy. No prices, shares or ranks here.
"""
import re

CONFIG_VERSION = 'share_class_groups/v0'
CONFIG_STATUS = 'V0_UNCALIBRATED'
LABEL_KO = '경제적 동일 종류 합산 · v0'
LABEL_EN = 'Economically identical classes summed · v0'

SHARE_CLASS_GROUPS_V0 = {
    'config_version': CONFIG_VERSION,
    'config_status': CONFIG_STATUS,
    'decision': 'USER_DECISION_2026_10_11_SUM_ECONOMICALLY_IDENTICAL_CLASSES',
    'basis': 'SAME_PER_SHARE_ECONOMIC_RIGHTS_VOTING_MAY_DIFFER',
    'groups': [
        # Class A (GOOGL, 1 vote) and Class C (GOOG, no vote); unlisted Class B (10 votes) is on the cover but not priced.
        {'group_id': 'alphabet', 'cik': '0001652044', 'codes': ['NASDAQ:GOOGL', 'NASDAQ:GOOG'], 'cover_class_count': 3},
        # Class A (FOXA, non-voting) and Class B (FOX, voting).
        {'group_id': 'fox', 'cik': '0001754301', 'codes': ['NASDAQ:FOXA', 'NASDAQ:FOX'], 'cover_class_count': 2},
        # Class A (NWSA, non-voting) and Class B (NWS, voting).
        {'group_id': 'news_corp', 'cik': '0001564708', 'codes': ['NASDAQ:NWSA', 'NASDAQ:NWS'], 'cover_class_count': 2},
    ],
}

_CODE = re.compile(r'(NASDAQ|NYSE):[A-Z0-9][A-Z0-9.\-]{0,15}')


def validate_share_class_groups(config, codes=None):
    """Strict shape check (mirrors JS ShareClassGroups.validate). Raises ValueError('SHARE_CLASS_GROUPS_INVALID')."""
    def need(ok):
        if not ok:
            raise ValueError('SHARE_CLASS_GROUPS_INVALID')
    need(type(config) is dict and set(config) == {'config_version', 'config_status', 'decision', 'basis', 'groups'})
    need(config['config_version'] == CONFIG_VERSION and config['config_status'] == CONFIG_STATUS)
    need(type(config['decision']) is str and type(config['basis']) is str and type(config['groups']) is list and len(config['groups']) <= 64)
    seen_ids, seen_codes, seen_ciks = set(), set(), set()
    for group in config['groups']:
        need(type(group) is dict and set(group) == {'group_id', 'cik', 'codes', 'cover_class_count'})
        need(type(group['group_id']) is str and re.fullmatch(r'[a-z0-9_]{1,64}', group['group_id']) is not None and group['group_id'] not in seen_ids)
        need(type(group['cik']) is str and re.fullmatch(r'[0-9]{10}', group['cik']) is not None and group['cik'] != '0000000000' and group['cik'] not in seen_ciks)
        members = group['codes']
        need(type(members) is list and 2 <= len(members) <= 8 and len(set(members)) == len(members))
        need(all(type(c) is str and _CODE.fullmatch(c) is not None and c not in seen_codes for c in members))
        need(codes is None or all(c in codes for c in members))
        count = group['cover_class_count']
        need(type(count) is int and len(members) <= count <= 16)
        seen_ids.add(group['group_id']); seen_ciks.add(group['cik']); seen_codes.update(members)
    return config
