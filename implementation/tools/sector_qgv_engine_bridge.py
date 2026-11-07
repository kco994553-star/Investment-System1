#!/usr/bin/env python3
"""Development execution route of the sector QGV screen (Main, owner 2026-11-06 「섹터 QGV 실제 연결」).

The screen's 1.2 「가중치 · QGV 구성」 sends one JSON request per click (IS2.data.engine, same origin, POST); this bridge answers it
by calling Codex's common engine (#505) unchanged: `research.sector_qgv` default_config, validate_config, preset and
list_factors, and Codex's Main transport `research.sector_qgv_main.run_preview_request` (before / after preview_qgv,
compare_previews, save_user_config). Nothing here scores, ranks, gates or fills a value:
every number in an answer is the engine's own output. Requests and answers are `sector-qgv-engine-request/1` /
`sector-qgv-engine-response/1` (implementation/docs/frontend_v2/SECTOR_QGV_20261106.md §3).

Inputs are SYNTHETIC only. The one input is Codex's public fixture implementation/docs/research/sector_qgv/synthetic-input.json,
checked against the SHA-256 pinned in synthetic-job.json, plus the named state variants of synthetic-states.json built from it
(each a documented change of that synthetic file, never a real company). A request cannot name a path, a private bundle or any
other input: there is no such field. A real (private) run needs Main's authenticated server and private storage, which are not
built; this bridge is not an authorization boundary and is never deployed (development site and tests only).

Q/G partial comparison (#505 7c2225a3, `sector-qgv-axis-comparison/1`): every preview also carries Codex's own
`research.sector_qgv_partial.compare_axes` of the same before / after previews and configs (`axis`, comparison_id = the
request id). `comparisons` lists the comparison files this process may show and `comparison` returns one by name: Codex's
pinned synthetic file partial-synthetic-comparison.json, plus, ONLY when this development process was started with
SECTOR_QGV_PRIVATE_COMPARISONS (absolute paths of retained private axis-comparison.json files, os.pathsep separated; each
outside every Git checkout, owner-only, at most 8 MiB, of that schema), those files read unchanged. A request still cannot
name a path: it names a listed comparison. Nothing is recomputed; no axis rank, total or market rank is made.

과거 입력으로 결과 재현 (owner 2026-11-07; Codex #514 8a483471 `research.sector_qgv_restore.replay_saved_config`): every preview's
after-preview is kept in this process with the exact snapshot it was computed on (bounded, in memory, never on disk). `replay`
takes a device's saved record (the engine's six-key save_user_config answer, unchanged) and calls Codex's replay with that
retained preview and original snapshot; the answer is the new preview only when Codex confirms every version / hash / result
field is identical, otherwise Codex's refusal code. A record whose preview this process does not hold is
RETAINED_INPUT_NOT_FOUND: nothing is recomputed on the current input under that name (that is the ordinary `preview` op).

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
from investment_system.research import sector_qgv_main as main_bridge  # noqa: E402
from investment_system.research import sector_qgv_partial as partial  # noqa: E402
from investment_system.research.sector_qgv_registry import (ENGINE, MAPPING, MODEL, NORMALIZATION, SECTORS,  # noqa: E402
                                                             TEMPLATES)

REQUEST = 'sector-qgv-engine-request/1'
MAIN_REQUEST = 'sector-qgv-main-request/1'
RESPONSE = 'sector-qgv-engine-response/1'
FIXTURES = ROOT / 'docs' / 'research' / 'sector_qgv'
OPS = ('context', 'view', 'preview', 'save', 'comparisons', 'comparison', 'replay')
MAX_REQUEST_BYTES = 1 << 20
MAX_KEPT_PREVIEWS = 32
REQUEST_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,79}')
# Codex synthetic-states.json cases, built from the synthetic input (FAILED: the engine's own refusal of a duplicate id).
# GATE_EXCLUDED is the value-trap side of the gate (official Q percentile 20 <= GATE_PERCENTILE), as in Codex's
# test_selection_gate_and_strict_missing, so the screen shows all three gate results.
INPUTS = ('NORMAL', 'GATE_UNKNOWN', 'GATE_EXCLUDED', 'PARTIAL', 'STALE', 'MAPPING_UNKNOWN', 'PEER_SAMPLE_SMALL', 'EMPTY',
          'FAILED', 'V_RESUMED')
INPUT_TEXT = {'NORMAL': '합성 · 정상', 'GATE_UNKNOWN': '합성 · 관문 판정 불가 1개', 'GATE_EXCLUDED': '합성 · 관문 V 제외 1개',
              'PARTIAL': '합성 · 필수 요소 결측', 'STALE': '합성 · 오래된 자료', 'MAPPING_UNKNOWN': '합성 · 분류 미확정',
              'PEER_SAMPLE_SMALL': '합성 · 비교집단 19개', 'EMPTY': '합성 · 빈 모집단', 'FAILED': '합성 · 회사 ID 중복(거부)',
              'V_RESUMED': '합성 · V 재개(가격 전달 반영)'}


AXIS = 'sector-qgv-axis-comparison/1'
SYNTHETIC_COMPARISON = ('PARTIAL_SYNTHETIC', FIXTURES / 'partial-synthetic-comparison.json',
                        '18f3d0eff9d58bbb7127d3fbad2902a507b7f218f9c1c83e5c5a26b3c5a5d903')
# Main's synthetic I1-shaped comparison: Codex's compare_axes(input_treatment=True) output, made by
# tools/sector_qgv_axis_main_variants.py and checked byte for byte by tests/test_sector_qgv_bridge.py.
MAIN_SYNTHETIC_I1 = ('MAIN_SYNTHETIC_I1', ROOT / 'tests' / 'fixtures' / 'sector_qgv_axis_i1_synthetic.json')
MAX_COMPARISON_BYTES = 8 << 20


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


def _v_resumed():
    """Codex #505 V resume (sector-qgv-v-resume/1) on its pinned synthetic pack and market delivery: research.sector_qgv_v.resume
    builds the snapshot (Codex's code; nothing is filled here). Hashes are those pinned in v-synthetic-job.json."""
    from investment_system.research.sector_qgv_v import resume
    job = json.loads((FIXTURES / 'v-synthetic-job.json').read_text(encoding='utf-8'))
    if job.get('data_kind') != 'SYNTHETIC':
        raise Refused('SYNTHETIC_INPUT_NOT_SYNTHETIC')
    parts = []
    for key in ('v_pack', 'market_inputs'):
        raw = (ROOT.parent / job[key]['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != job[key]['sha256']:
            raise Refused('SYNTHETIC_INPUT_HASH_MISMATCH')
        data = json.loads(raw)
        if data.get('data_kind') != 'SYNTHETIC':
            raise Refused('SYNTHETIC_INPUT_NOT_SYNTHETIC')
        parts.append(data)
    snapshot, _ = resume(parts[0], parts[1], job['request_id'])
    return snapshot


def synthetic_input(input_id):
    """The synthetic snapshot named input_id (the change each Codex state names, applied to a copy)."""
    if input_id not in INPUTS:
        raise Refused('INPUT_UNKNOWN')
    if input_id == 'V_RESUMED':
        return _v_resumed()
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


def _inside_git(path):
    for d in [path.parent, *path.parents]:
        if (d / '.git').exists():
            return True
    return False


def private_comparisons(env=None):
    """{name: path} of the retained private comparison files named at process start (never by a request)."""
    import os
    import stat
    raw = (os.environ if env is None else env).get('SECTOR_QGV_PRIVATE_COMPARISONS', '')
    out = {}
    for item in [x for x in raw.split(os.pathsep) if x]:
        path = Path(item)
        if not path.is_absolute():
            raise Refused('PRIVATE_PATH_NOT_ABSOLUTE')
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or st.st_size > MAX_COMPARISON_BYTES:
            raise Refused('PRIVATE_FILE_REFUSED')
        if _inside_git(path.resolve()):
            raise Refused('PRIVATE_INSIDE_GIT_CHECKOUT')
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version') != AXIS or not REQUEST_ID.fullmatch(str(data.get('comparison_id'))):
            raise Refused('PRIVATE_NOT_AXIS_COMPARISON')
        if data['comparison_id'] in out or data['comparison_id'] in (SYNTHETIC_COMPARISON[0], MAIN_SYNTHETIC_I1[0]):
            raise Refused('PRIVATE_DUPLICATE_NAME')
        out[data['comparison_id']] = path
    return out


def _synthetic_comparison():
    name, path, pin = SYNTHETIC_COMPARISON
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise Refused('SYNTHETIC_COMPARISON_HASH_MISMATCH')
    return json.loads(raw)


class Bridge:
    def __init__(self, env=None):
        self.kept = {}
        self.private = private_comparisons(env)

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
        # Codex's own Main transport (#505 sector_qgv_main.run_preview_request): before / after preview_qgv, compare_previews
        # and save_user_config for exactly this preview. The screen's 저장 writes that record inside its click.
        try:
            out = main_bridge.run_preview_request(snapshot, {'schema_version': MAIN_REQUEST, 'request_id': rid,
                                                             'before_config': before_config, 'after_config': config})
            # Codex's own Q/G partial comparison of exactly these two previews (no second composition here).
            axis = partial.compare_axes(out['before'], out['after'], out['before_config'], out['after_config'], rid)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        after = out['after']
        # kept: the after-preview with the exact snapshot it was computed on (save checks it; replay uses both unchanged).
        self.kept[after['preview_id']] = (copy.deepcopy(out['after_config']), copy.deepcopy(after), copy.deepcopy(snapshot))
        while len(self.kept) > MAX_KEPT_PREVIEWS:
            self.kept.pop(next(iter(self.kept)))
        return {'input_id': input_id, 'data_kind': 'SYNTHETIC', 'bridge_version': out['bridge_version'], 'before': out['before'],
                'after': after, 'comparison': out['diff'], 'saved': out['saved_config'], 'axis': axis}

    def _comparisons(self, req, rid):
        listed = [(SYNTHETIC_COMPARISON[0], 'SYNTHETIC', _synthetic_comparison()),
                  (MAIN_SYNTHETIC_I1[0], 'SYNTHETIC', json.loads(MAIN_SYNTHETIC_I1[1].read_text(encoding='utf-8')))]
        listed += [(name, 'PRIVATE', json.loads(path.read_text(encoding='utf-8'))) for name, path in self.private.items()]
        return {'comparisons': [{'name': name, 'data_kind': kind, 'comparison_id': c['comparison_id'], 'treatment': c['treatment'],
                                 'valuation_date': c['valuation_date'], 'denominator': c['denominator']}
                                for name, kind, c in listed]}

    def _comparison(self, req, rid):
        name = req.get('name')
        if name == SYNTHETIC_COMPARISON[0]:
            return {'name': name, 'data_kind': 'SYNTHETIC', 'comparison': _synthetic_comparison()}
        if name == MAIN_SYNTHETIC_I1[0]:
            return {'name': name, 'data_kind': 'SYNTHETIC', 'comparison': json.loads(MAIN_SYNTHETIC_I1[1].read_text(encoding='utf-8'))}
        if name in self.private:
            return {'name': name, 'data_kind': 'PRIVATE', 'comparison': json.loads(self.private[name].read_text(encoding='utf-8'))}
        raise Refused('COMPARISON_UNKNOWN')

    def _save(self, req, rid):
        config, preview_id = _config(req.get('config')), req.get('preview_id')
        if preview_id not in self.kept:
            raise Refused('PREVIEW_NOT_FOUND')
        _, preview, _ = self.kept[preview_id]
        try:
            saved = engine.save_user_config(config, preview, request_id=preview['request_id'], expected_preview_id=preview_id)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'saved': saved, 'data_kind': 'SYNTHETIC'}

    def _replay(self, req, rid):
        from investment_system.research.sector_qgv_restore import replay_saved_config
        saved = req.get('saved')
        if not isinstance(saved, dict) or not isinstance(saved.get('preview_id'), str):
            raise Refused('SAVED_CONFIG_INVALID')
        if saved['preview_id'] not in self.kept:
            raise Refused('RETAINED_INPUT_NOT_FOUND')
        _, retained, snapshot = self.kept[saved['preview_id']]
        try:
            out = replay_saved_config(copy.deepcopy(saved), copy.deepcopy(retained), copy.deepcopy(snapshot), rid)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'data_kind': 'SYNTHETIC', 'retained_preview_id': retained['preview_id'], 'preview': out['preview']}


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
    try:
        bridge = Bridge()
    except (Refused, OSError, ValueError) as exc:
        sys.stderr.write('PRIVATE_COMPARISONS_REFUSED ' + (str(exc) if isinstance(exc, Refused) else type(exc).__name__) + '\n')
        return 2
    for line in sys.stdin:
        if not line.strip():
            continue
        out = answer(bridge, line)
        sys.stdout.write(json.dumps(out, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
        sys.stdout.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
