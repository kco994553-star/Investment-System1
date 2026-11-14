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

Research models (owner 2026-11-11 「QGV 후속 연결」 §1; Codex #529 `research.dual_qgv`, DUAL_QGV.md): a request that carries `model`
is a research request and is never answered by the sector default engine. `model` is INTEGRATED or SECTOR and `model_id` names one
preregistered candidate explicitly: INTEGRATED → unified-roa-core/0.1.0 (U1) or unified-sales-core/0.1.0 (U2), SECTOR →
sector-reduced-core/0.1.0 (S1). No candidate is chosen for the caller (no default, best or adopted one); an unknown model, a
missing or mismatched model_id, or a config other than that candidate is refused. context / view answer Codex's
candidate_configs() and evidence_catalog(); preview calls run_board(config, evaluation, reference, request_id) on Codex's pinned
dual synthetic evaluation and reference snapshots (two inputs, never one); save calls save_board; replay calls replay_board with the
retained original inputs and request id (qgv-dual-saved/1 only; a sector saved record is refused, not converted); after a restart
(nothing retained) it reads the pinned inputs again from their fixed manifest and replays only on the pair the saved bindings name. Every answer names
the requested model and model_id, and the engine result must carry the same model_id and configuration hash, otherwise
MODEL_RESPONSE_MISMATCH. A request without `model` keeps the sector default behaviour below unchanged.
The 3/3/3 candidates (owner 2026-11-13; Codex #534 `research.qgv_333`, QGV_333.md) are named the same way: INTEGRATED →
unified-333-eps/0.1.0 (U2-333) or unified-333-persistence/0.1.0 (U1-333), SECTOR → sector-333/0.1.0 (S1-333); their config is
qgv_333.candidate_configs()[key] (qgv-dual-config/2), run, saved and replayed by the same dual_qgv calls (config/2 dispatches to
Codex's fixed validator); view answers the S1-333 recipe of the asked sector × accounting model as the contract states it.

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
from investment_system.research import dual_qgv  # noqa: E402
from investment_system.research import qgv_333  # noqa: E402
from investment_system.research import qgv_555  # noqa: E402
from investment_system.research import qgv_555_preview  # noqa: E402
from investment_system.research.top500_selection import select_top500  # noqa: E402
from investment_system.research.sector_qgv_registry import (ENGINE, MAPPING, MODEL, NORMALIZATION, SECTORS,  # noqa: E402
                                                             TEMPLATES)

REQUEST = 'sector-qgv-engine-request/1'
MAIN_REQUEST = 'sector-qgv-main-request/1'
RESPONSE = 'sector-qgv-engine-response/1'
FIXTURES = ROOT / 'docs' / 'research' / 'sector_qgv'
OPS = ('context', 'view', 'preview', 'save', 'comparisons', 'comparison', 'replay',
       'qgv555_context', 'qgv555_preview', 'qgv555_page', 'qgv555_detail', 'qgv555_role', 'qgv555_replay', 'qgv555_population')
# QGV 555 · 시총 Top500 (owner 2026-11-14, DC-49; Codex #537 a22ce2a4 research.qgv_555 / qgv_555_preview / top500_selection,
# called unchanged; synthetic inputs only — the server resolves them, a request never names an input hash):
#   qgv555_context    catalog(), accounting_recipes(), configuration(U1-555 / S1-555), selectable_metrics(role, template) for every
#                     role × template, the sector axis defaults
#   qgv555_preview    qgv_555_preview.preview() of the before / after setting on the fixture pair (identity() of each as the
#                     expected anchors), first preview_page() (20 rows), and the after result's replay record (qgv-555-saved/1,
#                     Main's projection: the fields replay() reads, no rows); the whole preview stays here (never sent)
#   qgv555_page       preview_page() of a kept preview at an offset
#   qgv555_detail     one company's after row of a kept preview (axis → roles → metrics, the engine's own row)
#   qgv555_role       one role's engine decile / rank per row of a kept preview's after result (the screen counts D1..D10)
#   qgv555_replay     Codex replay(saved, e, ref): REPRODUCED only when the result hash is the saved one
#   qgv555_population top500_view(select_top500()) on a synthetic candidate job (COMPLETE, or with the roster unproven)
# The published site has no engine route.
QGV555_MODELS = {'unified-555/0.1.0': 'U1-555', 'sector-555/0.1.0': 'S1-555'}
QGV555_INPUTS = ('SYNTHETIC_21',)
QGV555_SAVED = 'qgv-555-saved/1'
QGV555_SAVED_KEYS = ('configuration', 'evaluation', 'reference', 'bindings', 'calculated_at', 'result_hash')
QGV555_POPULATIONS = ('SYNTHETIC_COMPLETE', 'SYNTHETIC_ROSTER_UNPROVEN')
QGV555_PAGE = 20
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

# Research models (Codex #529): request model → the candidates it may name explicitly (candidate_configs() keys).
DUAL_MODELS = {'INTEGRATED': {'unified-roa-core/0.1.0': 'U1', 'unified-sales-core/0.1.0': 'U2',
                              'unified-333-eps/0.1.0': 'U2-333', 'unified-333-persistence/0.1.0': 'U1-333'},
               'SECTOR': {'sector-reduced-core/0.1.0': 'S1', 'sector-333/0.1.0': 'S1-333'}}
# The 3/3/3 candidates' configs come from Codex's qgv_333 (config/2), the reduced ones from dual_qgv (config/1); never one for the other.
Q333 = ('U2-333', 'U1-333', 'S1-333')
DUAL_OPS = ('context', 'view', 'preview', 'save', 'replay')
DUAL_FIXTURES = FIXTURES / 'dual-synthetic'
# Codex's dual synthetic manifest (6766962236 §1); each input file's bytes must be the ones it pins.
DUAL_MANIFEST_SHA256 = '65c5e549848981e7d2c211575cf3a192c2e30bb3eb04790b0cd6bd1716952446'
# The dual synthetic inputs: Codex's evaluation / reference pair as pinned, and QG_ONLY (cases.json QG_ONLY: the two V core
# observations removed from every matching evaluation and reference row; a documented change of that synthetic pair).
DUAL_INPUTS = ('DUAL_BOTH_VALID', 'DUAL_QG_ONLY')
DUAL_INPUT_TEXT = {'DUAL_BOTH_VALID': '합성 · 세 축 모두 있음', 'DUAL_QG_ONLY': '합성 · Q/G만 있음(V 핵심 관측 없음)'}
DUAL_V_CORE = ('ep_ttm_diluted', 'common_bp')


def _top500_job(kind):
    """A synthetic top500-input/1 candidate job (510 issuers, one common class each; the shape of Codex's own test job). kind
    SYNTHETIC_ROSTER_UNPROVEN leaves the candidate roster without completeness evidence."""
    day, ts = '2026-11-04', '2026-11-04T22:00:00Z'
    issuers = []
    for i in range(510):
        sid = 'synthetic-security-%04d' % i
        issuers.append(dict(issuer_id='synthetic-issuer-%04d' % i, ticker='SYN%d' % i, eligibility='ELIGIBLE', classes_complete=True,
            representative_security_id=sid, representative_evidence=['synthetic-primary-listing'], classes=[dict(
                economic_class_id='synthetic-class-%04d' % i, security_id=sid, security_kind='COMMON', exchange='NYSE',
                identity_status='VERIFIED', identity_evidence=['synthetic-identity'], valid_from=day, valid_to=None, observed_on=day,
                available_at=ts, corporate_action_status='VERIFIED', corporate_action_evidence=['synthetic-action-ledger'],
                shares_basis='ACTUAL_CLASS_OUTSTANDING', shares=1000, price=2000 - i, price_basis='RAW_CLOSE', currency='USD',
                fx_to_usd=1, price_security_id=sid, price_day=day, shares_day=day, evidence=['synthetic-price-and-shares'])]))
    coverage = dict(status='COMPLETE', evidence=['synthetic-roster-audit'], expected_issuers=[r['issuer_id'] for r in issuers])
    if kind == 'SYNTHETIC_ROSTER_UNPROVEN':
        coverage = dict(status='UNKNOWN', evidence=[], expected_issuers=[])
    return dict(schema_version='top500-input/1', evaluation_day=day, input_cutoff=ts, apply_at='2026-11-05T14:30:00Z',
        population_id='synthetic-us-candidates', population_version='1', policy=dict(version='top500-research/0.1.0',
        status='RESEARCH_PROPOSAL', markets=['NYSE', 'NASDAQ', 'NYSE_AMERICAN', 'BATS'],
        included_kinds=['COMMON', 'ADR', 'FOREIGN_COMMON', 'REIT'], cadence='DAILY_CLOSE'), coverage=coverage, issuers=issuers)


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


def dual_inputs(input_id):
    """(evaluation, reference) of the named dual synthetic input: Codex's pinned pair, or its QG_ONLY change (applied to copies)."""
    if input_id not in DUAL_INPUTS:
        raise Refused('INPUT_UNKNOWN')
    raw_manifest = (DUAL_FIXTURES / 'manifest.json').read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != DUAL_MANIFEST_SHA256:
        raise Refused('SYNTHETIC_INPUT_HASH_MISMATCH')
    pins = {f['path']: f['sha256'] for f in json.loads(raw_manifest)['files']}
    out = []
    for name in ('evaluation.json', 'reference.json'):
        raw = (DUAL_FIXTURES / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pins.get(name):
            raise Refused('SYNTHETIC_INPUT_HASH_MISMATCH')
        data = json.loads(raw)
        if json.loads(raw_manifest).get('data_kind') != 'SYNTHETIC':
            raise Refused('SYNTHETIC_INPUT_NOT_SYNTHETIC')
        out.append(data)
    evaluation, reference = out
    if input_id == 'DUAL_QG_ONLY':
        for rows in (evaluation['rows'], reference['rows']):
            for row in rows:
                for variant in DUAL_V_CORE:
                    row['observations'].pop(variant, None)
    return evaluation, reference


def _dual_candidate(req):
    """(model, model_id, key, candidate config) of a research request; refused unless both are named and known."""
    model, model_id = req.get('model'), req.get('model_id')
    if model not in DUAL_MODELS:
        raise Refused('MODEL_UNKNOWN')
    if model_id is None:
        raise Refused('MODEL_ID_REQUIRED')
    if model_id not in DUAL_MODELS[model]:
        raise Refused('MODEL_ID_UNKNOWN')
    key = DUAL_MODELS[model][model_id]
    config = (qgv_333.candidate_configs() if key in Q333 else dual_qgv.candidate_configs())[key]
    if config['model_id'] != model_id:
        raise Refused('MODEL_RESPONSE_MISMATCH')
    if 'config' in req and req['config'] != config:
        raise Refused('CONFIG_NOT_CANDIDATE')
    return model, model_id, key, config


def _dual_result_check(result, model_id, config):
    if result.get('model_id') != model_id or result.get('bindings', {}).get('model_hash') != dual_qgv.digest(config):
        raise Refused('MODEL_RESPONSE_MISMATCH')


class Bridge:
    def __init__(self, env=None):
        self.kept = {}
        self.kept_dual = {}
        self.kept_555 = {}
        self.private = private_comparisons(env)

    def handle(self, req):
        if not isinstance(req, dict) or req.get('schema_version') != REQUEST:
            raise Refused('REQUEST_SCHEMA')
        op, rid = req.get('op'), req.get('request_id')
        if op not in OPS:
            raise Refused('OP_UNKNOWN')
        if not isinstance(rid, str) or not REQUEST_ID.fullmatch(rid):
            raise Refused('REQUEST_ID_INVALID')
        if op.startswith('qgv555_'):
            return self._qgv555(op, req)
        if 'model' in req or 'model_id' in req:
            # A research request: never the sector default engine, never a silent fallback to it.
            if op not in DUAL_OPS:
                raise Refused('MODEL_OP_UNSUPPORTED')
            model, model_id, key, config = _dual_candidate(req)
            body = getattr(self, '_dual_' + op)(req, rid, key, config)
            return {'model': model, 'model_id': model_id, **body}
        return getattr(self, '_' + op)(req, rid)

    # ---- QGV 555 (Codex #537 research.qgv_555 / qgv_555_preview / top500_selection, called unchanged; synthetic inputs only)
    def _qgv555(self, op, req):
        try:
            return self._qgv555_op(op, req)
        except (ValueError, KeyError, TypeError) as exc:
            raise Refused(_code(exc)) from None

    def _kept555(self, req):
        kept = self.kept_555.get(req.get('preview_id'))
        if kept is None:
            raise Refused('PREVIEW_NOT_KEPT')
        return kept

    def _qgv555_op(self, op, req):
        if op == 'qgv555_context':
            return {'data_kind': 'SYNTHETIC', 'catalog': qgv_555.catalog(), 'recipes': qgv_555.accounting_recipes(),
                    'configs': {k: qgv_555.configuration(k) for k in ('U1-555', 'S1-555')},
                    'selectable': {t: {r: qgv_555_preview.selectable_metrics(r, t) for r in qgv_555.SPECS} for t in TEMPLATES},
                    'sectors': [{'sector_id': k, 'axis_weights': dict(zip('QGV', v))} for k, v in SECTORS.items()],
                    'templates': list(TEMPLATES),
                    'inputs': [{'input_id': 'SYNTHETIC_21', 'label': '합성 · 21개 발행사(Codex fixture)', 'data_kind': 'SYNTHETIC'}]}
        if op == 'qgv555_population':
            if req.get('input_id') not in QGV555_POPULATIONS:
                raise Refused('INPUT_UNKNOWN')
            return {'data_kind': 'SYNTHETIC', 'view': qgv_555_preview.top500_view(select_top500(_top500_job(req['input_id'])))}
        if op == 'qgv555_replay':
            saved = req.get('saved')
            if not isinstance(saved, dict) or saved.get('schema_version') != QGV555_SAVED or set(saved) != {'schema_version', *QGV555_SAVED_KEYS}:
                raise Refused('SAVED_INVALID')
            e, ref = qgv_555.fixture()
            result = qgv_555.replay(saved, e, ref)
            return {'data_kind': 'SYNTHETIC', 'reproduced': result['result_hash'] == saved['result_hash'], 'result_hash': result['result_hash']}
        if op == 'qgv555_page':
            off = req.get('offset')
            return {'data_kind': 'SYNTHETIC', 'page': qgv_555_preview.preview_page(self._kept555(req)['preview'], offset=off, limit=QGV555_PAGE)}
        if op == 'qgv555_detail':
            after = self._kept555(req)['preview']['after_result']
            row = next((r for r in after['rows'] if r['company_id'] == req.get('company_id')), None)
            if row is None:
                raise Refused('COMPANY_UNKNOWN')
            return {'data_kind': 'SYNTHETIC', 'model_id': after['model_id'], 'after_result_hash': after['result_hash'], 'row': row}
        if op == 'qgv555_role':
            after = self._kept555(req)['preview']['after_result']
            role = req.get('role')
            if role not in qgv_555.SPECS:
                raise Refused('ROLE_UNKNOWN')
            return {'data_kind': 'SYNTHETIC', 'role': role, 'after_result_hash': after['result_hash'], 'n': len(after['rows']),
                    'rows': [{'company_id': r['company_id'], **{k: r['roles'][role].get(k) for k in ('decile', 'decile_status', 'rank', 'rank_n')}} for r in after['rows']]}
        # qgv555_preview
        model_id, config, before = req.get('model_id'), req.get('config'), req.get('before_config')
        if model_id not in QGV555_MODELS:
            raise Refused('MODEL_UNKNOWN')
        if req.get('input_id') not in QGV555_INPUTS:
            raise Refused('INPUT_UNKNOWN')
        for c in (config, before):
            if not isinstance(c, dict) or c.get('model_id') != model_id:
                raise Refused('MODEL_RESPONSE_MISMATCH')
        e, ref = qgv_555.fixture()
        preview = qgv_555_preview.preview({'schema_version': 'qgv-555-preview-request/1', 'request_id': req['request_id'],
                                           'before': copy.deepcopy(before), 'after': copy.deepcopy(config)}, e, ref,
                                          expected_evaluation=qgv_555.identity(e), expected_reference=qgv_555.identity(ref))
        after = preview['after_result']
        if after['model_id'] != model_id:
            raise Refused('MODEL_RESPONSE_MISMATCH')
        self.kept_555[preview['result_hash']] = {'preview': preview}
        while len(self.kept_555) > MAX_KEPT_PREVIEWS:
            self.kept_555.pop(next(iter(self.kept_555)))
        saved = {'schema_version': QGV555_SAVED, **{k: copy.deepcopy(after[k]) for k in QGV555_SAVED_KEYS}}
        return {'data_kind': 'SYNTHETIC', 'model_id': model_id, 'input_id': req['input_id'], 'preview_id': preview['result_hash'],
                'page': qgv_555_preview.preview_page(preview, offset=0, limit=QGV555_PAGE), 'saved': saved}

    # ---- research models (Codex #529 research.dual_qgv, called unchanged)
    def _dual_context(self, req, rid, key, config):
        return {'versions': {'model_id': config['model_id'], 'model_version': config['version'], 'adapter_version': config['execution_version'],
                             'config_schema': config['schema_version'], 'board_schema': dual_qgv.SCHEMA},
                'candidate': key, 'config': config, 'config_hash': dual_qgv.digest(config),
                'evidence': dual_qgv.evidence_catalog(),
                'inputs': [{'input_id': k, 'label': DUAL_INPUT_TEXT[k], 'data_kind': 'SYNTHETIC'} for k in DUAL_INPUTS]}

    def _dual_view(self, req, rid, key, config):
        if config['kind'] == 'COMMON':
            return {'candidate': key, 'kind': 'COMMON', 'preset': config['uniform_preset'], 'config_hash': dual_qgv.digest(config)}
        sector, template = _scope(req)
        if key in Q333:
            current = config['scoped_presets'].get(sector + '|' + template)
            if current is None:
                raise Refused('SCOPE_UNKNOWN')
            return {'candidate': key, 'kind': 'SECTOR', 'sector_id': sector, 'accounting_template': template, 'preset': current,
                    'config_hash': dual_qgv.digest(config)}
        try:
            current = engine.preset(config['sector_config'], sector, template)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'candidate': key, 'kind': 'SECTOR', 'sector_id': sector, 'accounting_template': template, 'preset': current,
                'config_hash': dual_qgv.digest(config)}

    def _dual_preview(self, req, rid, key, config):
        input_id = req.get('input_id')
        evaluation, reference = dual_inputs(input_id)
        try:
            result = dual_qgv.run_board(config, evaluation, reference, request_id=rid)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        _dual_result_check(result, config['model_id'], config)
        # kept: the result with its own two inputs and request id (save checks it; replay uses all of them unchanged).
        self.kept_dual[result['result_hash']] = (copy.deepcopy(config), copy.deepcopy(result), copy.deepcopy(evaluation),
                                                  copy.deepcopy(reference), rid, input_id)
        while len(self.kept_dual) > MAX_KEPT_PREVIEWS:
            self.kept_dual.pop(next(iter(self.kept_dual)))
        return {'candidate': key, 'input_id': input_id, 'data_kind': 'SYNTHETIC', 'kind': 'SYNTHETIC_RECALCULATION', 'board': result}

    def _dual_save(self, req, rid, key, config):
        result_hash = req.get('result_hash')
        if result_hash not in self.kept_dual:
            raise Refused('PREVIEW_NOT_FOUND')
        kept_config, result, *_ = self.kept_dual[result_hash]
        if kept_config != config:
            raise Refused('MODEL_RESPONSE_MISMATCH')
        try:
            saved = dual_qgv.save_board(config, result)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise Refused(_code(exc)) from None
        return {'candidate': key, 'saved': saved, 'data_kind': 'SYNTHETIC'}

    def _dual_replay(self, req, rid, key, config):
        saved = req.get('saved')
        if not isinstance(saved, dict):
            raise Refused('SAVED_CONFIG_INVALID')
        if saved.get('schema_version') != 'qgv-dual-saved/1':
            # e.g. a sector-qgv saved record: kept as it is by the caller, never converted to a research record
            raise Refused('SAVED_SCHEMA_MISMATCH')
        if (saved.get('configuration') or {}).get('model_id') != config['model_id']:
            raise Refused('MODEL_RESPONSE_MISMATCH')
        if saved.get('result_hash') in self.kept_dual:
            _, retained, evaluation, reference, original_rid, input_id = self.kept_dual[saved['result_hash']]
            try:
                out = dual_qgv.replay_board(copy.deepcopy(saved), copy.deepcopy(evaluation), copy.deepcopy(reference), original_rid)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise Refused(_code(exc)) from None
            _dual_result_check(out, config['model_id'], config)
            return {'candidate': key, 'input_id': input_id, 'data_kind': 'SYNTHETIC', 'kind': 'EXACT_REPLAY', 'input_source': 'RETAINED_IN_PROCESS',
                    'retained_result_hash': retained['result_hash'], 'board': out}
        # Not held in this process (a restarted bridge, or memory dropped): the pinned inputs are read again from their fixed
        # manifest (dual_inputs re-checks every byte) and Codex's replay_board is tried on each; it accepts only the pair whose
        # identities are the saved bindings and whose result is the saved result. The request id is not part of the result hash.
        # Nothing matching → RETAINED_INPUT_NOT_FOUND: the record stays as it is, nothing is recomputed on another input.
        for input_id in DUAL_INPUTS:
            evaluation, reference = dual_inputs(input_id)
            try:
                out = dual_qgv.replay_board(copy.deepcopy(saved), evaluation, reference, rid)
            except ValueError as exc:
                if str(exc) == 'DUAL_REPLAY_INPUT_MISMATCH':
                    continue
                raise Refused(_code(exc)) from None
            except (KeyError, TypeError, AttributeError) as exc:
                raise Refused(_code(exc)) from None
            _dual_result_check(out, config['model_id'], config)
            return {'candidate': key, 'input_id': input_id, 'data_kind': 'SYNTHETIC', 'kind': 'EXACT_REPLAY', 'input_source': 'PINNED_INPUT_REREAD',
                    'retained_result_hash': saved['result_hash'], 'board': out}
        raise Refused('RETAINED_INPUT_NOT_FOUND')

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
