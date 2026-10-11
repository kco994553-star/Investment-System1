"""Validator for the user-editable 13F manager style config (manager_styles_v0.json).

Styles and descriptions are a v0 general-assessment label chosen by the user,
not an app recommendation and not an input to any score. A candidate CIK is
only a value to verify against SEC submissions; it is never trusted as is.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

PATH = Path(__file__).with_name('manager_styles_v0.json')
TOP_KEYS = ('schema_version', 'config_version', 'status', 'decided_at', 'label_ko', 'label_en', 'styles', 'managers')
STYLE_KEYS = ('id', 'label_ko', 'label_en', 'reference_only')
MANAGER_KEYS = ('id', 'display_name', 'expected_sec_name', 'candidate_cik', 'styles', 'description_ko', 'description_en')
MAX_MANAGERS = 20  # public generator accepts at most 20 13F pairs
_ID = re.compile(r'[a-z][a-z0-9_]{0,47}')
_CIK = re.compile(r'[0-9]{10}')


class ManagerStylesError(ValueError):
    """Value-free rejection of an invalid manager style config."""


def _need(condition: bool) -> None:
    if not condition:
        raise ManagerStylesError('MANAGER_STYLES_INVALID')


def _text(value: object, limit: int) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= limit and value == value.strip()
            and not any(ord(ch) < 32 or ch in '<>' for ch in value))


def normalize_name(value: str) -> str:
    """Case/whitespace normalization only: no punctuation or suffix stripping."""
    return ' '.join(value.split()).casefold()


def validate_manager_styles(config: object) -> dict:
    _need(isinstance(config, dict) and tuple(sorted(config)) == tuple(sorted(TOP_KEYS)))
    _need(type(config['schema_version']) is int and config['schema_version'] == 1)
    _need(isinstance(config['config_version'], str) and re.fullmatch(r'manager_styles/v[0-9]{1,3}', config['config_version']) is not None)
    _need(config['status'] in ('V0_UNCALIBRATED',))
    _need(isinstance(config['decided_at'], str) and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', config['decided_at']) is not None)
    _need(_text(config['label_ko'], 80) and _text(config['label_en'], 120))
    styles = config['styles']
    _need(isinstance(styles, list) and 0 < len(styles) <= 32)
    style_ids = []
    for style in styles:
        _need(isinstance(style, dict) and tuple(sorted(style)) == tuple(sorted(STYLE_KEYS)))
        _need(isinstance(style['id'], str) and _ID.fullmatch(style['id']) is not None and style['id'] not in style_ids)
        _need(_text(style['label_ko'], 40) and _text(style['label_en'], 40) and type(style['reference_only']) is bool)
        style_ids.append(style['id'])
    managers = config['managers']
    _need(isinstance(managers, list) and 0 < len(managers) <= MAX_MANAGERS)
    ids, ciks = set(), set()
    for manager in managers:
        _need(isinstance(manager, dict) and tuple(sorted(manager)) == tuple(sorted(MANAGER_KEYS)))
        _need(isinstance(manager['id'], str) and _ID.fullmatch(manager['id']) is not None and manager['id'] not in ids)
        ids.add(manager['id'])
        _need(_text(manager['display_name'], 80) and _text(manager['expected_sec_name'], 150))
        cik = manager['candidate_cik']
        # null keeps a manager listed as NOT_AVAILABLE (CIK_NOT_CONFIGURED); never guessed.
        _need(cik is None or isinstance(cik, str) and _CIK.fullmatch(cik) is not None and int(cik) > 0 and cik not in ciks)
        if cik is not None:
            ciks.add(cik)
        tags = manager['styles']
        _need(isinstance(tags, list) and 0 < len(tags) <= len(style_ids) and len(set(tags)) == len(tags)
              and all(isinstance(tag, str) and tag in style_ids for tag in tags))
        _need(_text(manager['description_ko'], 300) and _text(manager['description_en'], 300))
    return config


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result)
        result[key] = value
    return result


def load_manager_styles(path: Path | str = PATH) -> dict:
    def reject(_value):
        raise ManagerStylesError('MANAGER_STYLES_INVALID')
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_unique, parse_constant=reject)
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise ManagerStylesError('MANAGER_STYLES_INVALID') from None
    return validate_manager_styles(config)
