#!/usr/bin/env python3
"""Development execution route of the sector QGV screen (Main, owner 2026-11-06 「섹터 QGV 실제 연결」).

The screen's 1.2 「가중치 · QGV 구성」 sends one JSON request per click (IS2.data.engine, same origin, POST); this bridge answers it
by calling Codex's common engine `investment_system.research.sector_qgv` (#505) unchanged: default_config, validate_config,
preset, list_factors, preview_qgv, compare_previews and save_user_config. Nothing here scores, ranks, gates or fills a value:
every number in an answer is the engine's own output. Requests and answers are `sector-qgv-engine-request/1` /
`sector-qgv-engine-response/1` (implementation/docs/frontend_v2/SECTOR_QGV_20261106.md §3).

Inputs are SYNTHETIC only. The one input is Codex's public fixture implementation/docs/research/sector_qgv/synthetic-input.json,
checked against the SHA-256 pinned in synthetic-job.json, plus the named state variants of synthetic-states.json built from it
(each a documented change of that synthetic file, never a real company). A request cannot name a path, a private bundle or any
other input: there is no such field. A real (private) run needs Main's authenticated server and private storage, which are not
built; this bridge is not an authorization boundary and is never deployed (development site and tests only).

Transport: one JSON object per line on stdin -> one JSON object per line on stdout (tools/web_app_sector_qgv_engine.js runs it
behind the development site's POST route `sector-qgv-engine`). Errors are fixed codes; no input value, company result or
exception text is printed on stderr.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv.qgv_v2 import GATE_PERCENTILE  # noqa: E402
from investment_system.research import sector_qgv as engine  # noqa: E402
from investment_system.research.sector_qgv_registry import (ENGINE, MAPPING, MODEL, NORMALIZATION, SECTORS,  # noqa: E402
                                                             TEMPLATES)

REQUEST = 'sector-qgv-engine-request/1'
RESPONSE = 'sector-qgv-engine-response/1'
FIXTURES = ROOT / 'docs' / 'research' / 'sector_qgv'
OPS = ('context', 'view', 'preview', 'save')
MAX_REQUEST_BYTES = 1 << 20
MAX_KEPT_PREVIEWS = 8
REQUEST_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,79}')
# Codex synthetic-states.json cases, built from the synthetic input (FAILED: the engine's own refusal of a duplicate id).
# GATE_EXCLUDED is the value-trap side of the gate (official Q percentile 20 <= GATE_PERCENTILE), as in Codex's
# test_selection_gate_and_strict_missing, so the screen shows all three gate results.
INPUTS = ('NORMAL', 'GATE_UNKNOWN', 'GATE_EXCLUDED', 'PARTIAL', 'STALE', 'MAPPING_UNKNOWN', 'PEER_SAMPLE_SMALL', 'EMPTY',
          'FAILED')
INPUT_TEXT = {'NORMAL': '합성 · 정상', 'GATE_UNKNOWN': '합성 · 관문 판정 불가 1개', 'GATE_EXCLUDED': '합성 · 관문 V 제외 1개',
              'PARTIAL': '합성 · 필수 요소 결측', 'STALE': '합성 · 오래된 자료', 'MAPPING_UNKNOWN': '합성 · 분류 미확정',
              'PEER_SAMPLE_SMALL': '합성 · 비교집단 19개', 'EMPTY': '합성 · 빈 모집단', 'FAILED': '합성 · 회사 ID 중복(거부)'}


class Refused(Exception):
    """A fixed refusal code for the screen (never an input value)."""


def _base_input():
    job = json.loads((FIXTURES / 'synthetic-job.json').read_text(encoding='utf-8'))
    raw = (FIXTURES / 'synthetic-input.json').read_bytes()
    if job.get('data_kind') != 'SYNTHETIC' or hashlib.sha256(raw).hexdigest() != job['snapshot']['sha256']:
        raise Refused('SYNTHETIC_INPUT_HASH_MISMATCH')
    data = json.loads(raw)
    if not all('synthetic' in ref for row in data['rows'] for obs in row['observations'].values() for ref in obs['provenance']):
        raise Refused('SYNTHETIC_INPUT_NOT_SYNTHETIC')
    return data


def synthetic_input(input_id):
    """The synthetic snapshot named input_id (the change each Codex state names, applied to a copy)."""
    if input_id not in INPUTS:
        raise Refused('INPUT_UNKNOWN')
    s = copy.deepcopy(_base_input())
    first = next(iter(engine.CATALOG))  # the catalog's first variant: the 'first factor' of synthetic-states.json
    if input_id == 'EMPTY':
        s['members'], s['rows'] = [], []
    elif input_id == 'PARTIAL':
        for row in s['rows']:
            row['observations'].pop(first, None)
    elif input_id == 'STALE':
        for row in s['rows']:
            row['observations'][first]['status'] = 'STALE'
    elif input_id == 'GATE_UNKNOWN':
        s['rows'][0]['gate'] = None
    elif input_id == 'GATE_EXCLUDED':
        s['rows'][0]['gate'] = dict(s['rows'][0]['gate'], q_industry_percentile=20)
    elif input_id == 'MAPPING_UNKNOWN':
        for row in s['rows']:
            row['mapping']['version'] = 'book-sector-map/unknown'
    elif input_id == 'PEER_SAMPLE_SMALL':
        gone = s['rows'].pop()
        s['members'].remove(gone['company_id'])
    elif input_id == 'FAILED':
        s['rows'].append(copy.deepcopy(s['rows'][0]))
    return s


def _config(value):
    if not isinstance(value, dict):
        raise Refused('CONFIG_INVALID')
    return copy.deepcopy(value)


def _scope(req):
    sector, template = req.get('sector_id'), req.get('accounting_template')
    if sector not in SECTORS or template not in TEMPLATES:
        raise Refused('MAPPING_UNRESOLVED')
    return sector, template


def _validation(config):
    try:
        return engine.validate_config(config)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {'valid': False, 'code': _code(exc)}


def _code(exc):
    text = str(exc).split(':', 1)
    head = text[0].strip("'\"")
    code = head if re.fullmatch(r'[A-Z][A-Z0-9_]+', head) else 'INPUT_VALIDATION_FAILED'
    if len(text) == 2 and re.fullmatch(r'[a-z0-9_]+', text[1]):
        return code + ':' + text[1]
    return code


class Bridge:
    def __init__(self):
        self.kept = {}

    def handle(self, req):
        if not isinstance(req, dict) or req.get('schema_version') != REQUEST:
            raise Refused('REQUEST_SCHEMA')
        op, rid = req.get('op'), req.get('request_id')
        if op not in OPS:
            raise Refused('OP_UNKNOWN')
        if not isinstance(rid, str) or not REQUEST_ID.fullmatch(rid):
            raise Refused('REQUEST_ID_INVALID')
        return getattr(self, '_' + op)(req, rid)

    def _context(self, req, rid):
        return {'versions': {'model_version': MODEL, 'engine_version': ENGINE, 'normalization_version': NORMALIZATION,
                             'mapping_version': MAPPING},
                'default_config': engine.default_config(),
                'sectors': [{'sector_id': k, 'axis_weights': dict(zip(('Q', 'G', 'V'), [x * 100 for x in v]))}
                            for k, v in SECTORS.items()],
                'templates': list(TEMPLATES),
                'gate': {'policy': engine.default_config()['gate_policy'], 'value_excluded_at_or_below': GATE_PERCENTILE},
                'inputs': [{'input_id': k, 'label': INPUT_TEXT[k], 'data_kind': 'SYNTHETIC'} for k in INPUTS]}

    def _view(self, req, rid):
        sector, template = _scope(req)
        config = _config(req.get('config'))
        check = _validation(config)
        shown = config if check.get('valid') else engine.default_config()
        try:
            current = engine.preset(shown, sector, template)
            factors = engine.list_factors(shown, sector, template)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'sector_id': sector, 'accounting_template': template, 'validation': check, 'preset': current,
                'default_preset': engine.preset(engine.default_config(), sector, template), 'factors': factors}

    def _preview(self, req, rid):
        config, before_config = _config(req.get('config')), _config(req.get('before_config'))
        input_id = req.get('input_id')
        snapshot = synthetic_input(input_id)
        try:
            before = engine.preview_qgv(before_config, snapshot, rid + ':before')
            after = engine.preview_qgv(config, snapshot, rid)
            comparison = engine.compare_previews(before, after, rid)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        self.kept[after['preview_id']] = (copy.deepcopy(config), after)
        while len(self.kept) > MAX_KEPT_PREVIEWS:
            self.kept.pop(next(iter(self.kept)))
        # The record the screen may store for exactly this preview (the engine's own save check, run now): the device write
        # happens inside the user's 저장 click, which cannot wait for another round trip.
        try:
            saved = engine.save_user_config(config, after, request_id=rid, expected_preview_id=after['preview_id'])
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            saved = {'refused': _code(exc)}
        return {'input_id': input_id, 'data_kind': 'SYNTHETIC', 'before': before, 'after': after, 'comparison': comparison,
                'saved': saved}

    def _save(self, req, rid):
        config, preview_id = _config(req.get('config')), req.get('preview_id')
        if preview_id not in self.kept:
            raise Refused('PREVIEW_NOT_FOUND')
        _, preview = self.kept[preview_id]
        try:
            saved = engine.save_user_config(config, preview, request_id=preview['request_id'], expected_preview_id=preview_id)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'saved': saved, 'data_kind': 'SYNTHETIC'}


def answer(bridge, line):
    rid, op = None, None
    try:
        if len(line.encode('utf-8')) > MAX_REQUEST_BYTES:
            raise Refused('REQUEST_TOO_LARGE')
        try:
            req = json.loads(line)
        except ValueError:
            raise Refused('REQUEST_NOT_JSON') from None
        if isinstance(req, dict):
            rid = req.get('request_id') if isinstance(req.get('request_id'), str) and REQUEST_ID.fullmatch(req['request_id']) else None
            op = req.get('op') if req.get('op') in OPS else None
        body = bridge.handle(req)
        return {'schema_version': RESPONSE, 'op': op, 'request_id': rid, 'ok': True, **body}
    except Refused as exc:
        return {'schema_version': RESPONSE, 'op': op, 'request_id': rid, 'ok': False, 'code': str(exc)}
    except Exception as exc:  # noqa: BLE001 - never a traceback or value on the wire
        return {'schema_version': RESPONSE, 'op': op, 'request_id': rid, 'ok': False, 'code': 'ENGINE_FAILED',
                'reason_type': type(exc).__name__}


def main():
    bridge = Bridge()
    for line in sys.stdin:
        if not line.strip():
            continue
        out = answer(bridge, line)
        sys.stdout.write(json.dumps(out, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
        sys.stdout.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
