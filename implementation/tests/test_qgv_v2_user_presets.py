"""User presets v0.1 (owner decision 2026-10-18 '프리셋 v0.1 후보 정의') and the PERSONAL_PREVIEW weight-stage diagnostic.

Checks: the three CANDIDATE_UNVALIDATED definitions (own ids and version, axis sums 100, inner weights == the official 15-factor
weights), the official default and code presets untouched, Python == JS (definitions, scores and weight stages of every candidate
on the existing vector fixtures), scores byte-identical with and without the diagnostic, and the stages consistent with the
engine's own computation ((c) sums to 100 and uses exactly the factors that produced the total)."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from investment_system.qgv import qgv_v2 as m
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
from investment_system.qgv.type_config import load_official_type_config

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src/investment_system/product/web_assets/qgv-v2.js'
OFFICIAL = ROOT / 'tests/fixtures/qgv_v2_vectors_v1.json'
CUSTOM = ROOT / 'tests/fixtures/qgv_v2_custom_vectors_v1.json'
IDS = ('user-preset/aggressive@0.1', 'user-preset/balanced@0.1', 'user-preset/defensive@0.1')
EPS = 1e-9

# Node side: definitions, and for every (input, preset, gate, type weights) the JS result with weight stages plus whether the
# result without the diagnostic is byte-identical to it minus `weight_stages`.
NODE = r"""
const V=require(process.argv[1]),fs=require('fs'),runs=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const out={constants:{schema:V.USER_PRESET_SCHEMA,status:V.USER_PRESET_STATUS,stages:V.WEIGHT_STAGES_SCHEMA,ids:Object.keys(V.USER_PRESETS)},
 presets:Object.keys(V.USER_PRESETS).map(id=>V.userPreset(id)),runs:[]};
for(const r of runs){const opts={weights:V.userPreset(r.preset).weights,gate:r.gate,typeWeights:r.type_weights};
 const plain=V.scoreUniverse(structuredClone(r.companies),structuredClone(r.market),opts),diag=V.scoreUniverse(structuredClone(r.companies),structuredClone(r.market),{...opts,weightStages:true});
 const stripped=structuredClone(diag);for(const k of Object.keys(stripped))delete stripped[k].weight_stages;
 out.runs.push({result:diag,identical:JSON.stringify(stripped)===JSON.stringify(plain)});}
let official=false;try{V.scoreUniverse({},{},{weightStages:true});}catch(e){official=e.message;}out.official_refused=official;
process.stdout.write(JSON.stringify(out));
"""


class UserPresetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_official_type_config().to_dict()
        cls.params = load_default_dcf_parameters()
        cls.official = json.loads(OFFICIAL.read_text(encoding='utf-8'))
        cls.custom = json.loads(CUSTOM.read_text(encoding='utf-8'))
        # Every candidate on: the 7 official vector inputs (gate as in the case; the growth-typed rows exercise the type stage),
        # the score_rows universe (published Q/G axes), and one gate-off / type-weights-off run.
        inputs = [(c['id'], c['input']['companies'], c['input']['synthetic_market'], c['input']['gate']) for c in cls.official['cases']]
        scored = next(c for c in cls.custom['cases'] if c['id'] == 'scored-official-forced-recompute')['input']['synthetic_market']
        inputs.append(('scored-universe', cls.custom['scored_universe'], scored, None))
        cls.runs = [{'case': cid, 'companies': comp, 'market': mk, 'gate': gate, 'type_weights': True, 'preset': pid}
                    for cid, comp, mk, gate in inputs for pid in IDS]
        first = cls.official['cases'][0]['input']
        cls.runs += [{'case': 'gate-off', 'companies': first['companies'], 'market': first['synthetic_market'], 'gate': False, 'type_weights': True, 'preset': IDS[0]},
                     {'case': 'types-off', 'companies': first['companies'], 'market': first['synthetic_market'], 'gate': None, 'type_weights': False, 'preset': IDS[2]}]
        cls.py = [cls.score(cls, r, weight_stages=True) for r in cls.runs]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'runs.json'
            path.write_text(json.dumps(cls.runs), encoding='utf-8')
            proc = subprocess.run(['node', '-e', NODE, str(JS), str(path)], capture_output=True, text=True, check=True)
        cls.js = json.loads(proc.stdout)

    def score(self, run, **kw):
        return m.score_universe(copy.deepcopy(run['companies']), copy.deepcopy(run['market']), type_config=self.cfg, parameters=self.params,
                                gate=run['gate'], weights=m.user_preset(run['preset'])['weights'], type_weights=run['type_weights'], **kw)

    def test_definitions_are_the_owner_values_with_the_official_inner_weights(self):
        self.assertEqual(tuple(m.USER_PRESETS), IDS)
        want = {IDS[0]: ('aggressive', '공격형', {'Q': 30, 'G': 50, 'V': 20}), IDS[1]: ('balanced', '균형형', {'Q': 40, 'G': 30, 'V': 30}),
                IDS[2]: ('defensive', '수비형', {'Q': 55, 'G': 15, 'V': 30})}
        for pid, (key, name, axis) in want.items():
            d = m.user_preset(pid)
            self.assertEqual((d['id'], d['key'], d['name'], d['version']), (pid, key, name, '0.1'))
            self.assertEqual(d['status'], 'CANDIDATE_UNVALIDATED')
            self.assertFalse(d['official_default'])
            self.assertTrue(d['type_weights'] and d['gate'])  # type adjustment and value-trap gate default ON
            self.assertEqual(d['weights']['axis'], axis)
            self.assertEqual(sum(axis.values()), 100)
            self.assertEqual(d['weights']['inner'], {p: dict(m.WEIGHTS[p]) for p in m.PILLARS})
            self.assertEqual(d['weights'], m.validate_weights(d['weights']))
            d['weights']['inner']['Q']['q_profitability'] = 99  # a copy: never the engine's constants
            self.assertEqual(m.WEIGHTS['Q']['q_profitability'], 25)
        with self.assertRaises(ValueError):
            m.user_preset('balanced')  # the code preset id is not a user preset (no rename / remap)
        # The official default and the four code presets are unchanged.
        self.assertEqual(m.DEFAULT_PRESET, 'balanced')
        self.assertEqual({k: v['weights'] for k, v in m.PRESETS.items()},
                         {'balanced': {'Q': 34, 'G': 33, 'V': 33}, 'quality': {'Q': 50, 'G': 25, 'V': 25}, 'growth': {'Q': 30, 'G': 50, 'V': 20}, 'value': {'Q': 25, 'G': 20, 'V': 55}})

    def test_js_definitions_equal_python(self):
        self.assertEqual(self.js['constants'], {'schema': m.USER_PRESET_SCHEMA, 'status': m.USER_PRESET_STATUS, 'stages': m.WEIGHT_STAGES_SCHEMA, 'ids': list(IDS)})
        self.assertEqual(self.js['presets'], [m.user_preset(i) for i in IDS])
        self.assertEqual(self.js['official_refused'], 'WEIGHT_STAGES_PERSONAL_ONLY')

    def test_js_scores_and_weight_stages_equal_python(self):
        self.assertEqual(len(self.js['runs']), len(self.runs))
        for run, py, js in zip(self.runs, self.py, self.js['runs']):
            py, out = json.loads(json.dumps(py)), js['result']
            self.assertEqual(set(py), set(out))
            for code in py:
                # The DCF '참고 범위' (not a factor, not weighted) uses pow() and may differ in the last bit, as in qgv_v2_node_test.js;
                # every other field — scores, flags, weights and the weight stages — is exactly equal.
                a, b = py[code].pop('reference_range'), out[code].pop('reference_range')
                self.assertEqual(py[code], out[code], (run['case'], run['preset'], code))
                self.assertEqual(a.keys(), b.keys())
                for k in a:
                    if isinstance(a[k], float):
                        self.assertAlmostEqual(a[k], b[k], delta=max(1e-9, abs(a[k]) * 1e-9))
                    else:
                        self.assertEqual(a[k], b[k])

    def test_the_diagnostic_never_changes_a_score(self):
        for run, py, js in zip(self.runs, self.py, self.js['runs']):
            self.assertTrue(js['identical'], (run['case'], run['preset']))
            plain = self.score(run)
            stripped = copy.deepcopy(py)
            for r in stripped.values():
                r.pop('weight_stages')
            self.assertEqual(json.dumps(stripped, sort_keys=True), json.dumps(plain, sort_keys=True), (run['case'], run['preset']))
        with self.assertRaises(ValueError) as ctx:
            m.score_universe({}, {}, type_config=self.cfg, parameters=self.params, weight_stages=True)
        self.assertEqual(str(ctx.exception), 'WEIGHT_STAGES_PERSONAL_ONLY')
        # The official vectors are still reproduced exactly after personal runs (no shared state).
        for case in self.official['cases']:
            i = case['input']
            out = m.score_universe(copy.deepcopy(i['companies']), copy.deepcopy(i['synthetic_market']), type_config=self.cfg, parameters=self.params,
                                   preset=i['preset'], gate=i['gate'])
            self.assertEqual(json.loads(json.dumps(out)), case['expected'], case['id'])
            self.assertTrue(all('weight_stages' not in r for r in out.values()))

    def test_stages_match_the_engine_computation(self):
        seen = {'TYPE_WEIGHTS': 0, 'VALUE_TRAP_GATE': 0, 'MISSING': 0, 'AXIS_NOT_AVAILABLE': 0, 'TOTAL_NOT_AVAILABLE': 0, 'RENORMALIZED': 0, 'published': 0}
        for run, res in zip(self.runs, self.py):
            tree = m.user_preset(run['preset'])['weights']
            for code, r in res.items():
                ws = r['weight_stages']
                self.assertEqual(ws['schema'], m.WEIGHT_STAGES_SCHEMA)
                # (a) base = the preset axis weights (they sum to 100) and the official inner weights.
                self.assertEqual(ws['base']['axis'], {p: float(tree['axis'][p]) for p in m.PILLARS})
                self.assertEqual(ws['base']['inner'], {p: {f: float(w) for f, w in m.WEIGHTS[p].items()} for p in m.PILLARS})
                # (b) type stage = the very weights the total uses.
                self.assertEqual(ws['type_adjusted']['axis'], r['weights'])
                if run['type_weights']:
                    fb = {p: float(self.cfg['fallback']['weights'][p]) for p in m.PILLARS}
                    self.assertEqual(ws['type_adjusted']['axis'], m.composite_weights(tree['axis'], r['type_weights'], fb))
                    if r['selected_types']:
                        self.assertTrue(ws['type_adjusted']['changes'], code)
                        seen['TYPE_WEIGHTS'] += 1
                else:
                    self.assertEqual(ws['type_adjusted']['changes'], [])
                a = ws['applied']
                reasons = {c['reason'] for c in a['changes']}
                for k in seen:
                    seen[k] += k in reasons
                if r['total'] is None:
                    self.assertEqual(a['state'], 'NOT_AVAILABLE')
                    self.assertEqual(a['reason'], r['total_reason'])
                    self.assertTrue(all(v is None for v in a['axis'].values()))
                    continue
                self.assertEqual(a['state'], 'READY')
                self.assertAlmostEqual(sum(a['axis'].values()), 100.0, delta=EPS)
                used_axes = {p for p in m.PILLARS if a['axis'][p] > 0}
                self.assertEqual(used_axes, {p for p in m.PILLARS if r['axes'][p]['score'] is not None and r['weights'][p] > 0
                                             and not (p == 'V' and r['value_trap_gate'])}, code)
                self.assertEqual(a['axis']['V'] == 0, r['value_trap_gate'] or r['axes']['V']['score'] is None)
                if r['value_trap_gate'] and r['axes']['V']['score'] is not None:
                    self.assertEqual(a['axis_status']['V']['status'], 'VALUE_TRAP_GATE')
                    self.assertIn('VALUE_TRAP_GATE', reasons)
                total = 0.0
                for p in used_axes:
                    total += a['axis'][p] * r['axes'][p]['score'] / 100.0
                self.assertAlmostEqual(total, r['total'], delta=EPS, msg=code)
                # (c) per factor: positive exactly for the factors that produced the total, summing to 100.
                factors_used = {f for p in used_axes for f in m.WEIGHTS[p] if r['factors'][f]['score'] is not None and tree['inner'][p][f] > 0}
                self.assertEqual({f for f, v in a['factor'].items() if v}, factors_used, code)
                self.assertAlmostEqual(sum(a['factor'].values()), 100.0, delta=EPS)
                for f, st in a['factor_status'].items():
                    self.assertEqual(st['status'] == 'USED', f in factors_used, (code, f))
                    if st['status'] == 'MISSING':
                        self.assertEqual(st['reason'], r['factors'][f]['reason'])
                for p in used_axes:
                    self.assertAlmostEqual(sum(a['inner'][p].values()), 100.0, delta=EPS)
                    if a['inner_basis'][p] == 'PUBLISHED' and run['case'] != 'scored-universe':
                        continue  # synthetic published axes are not built from these factors; the score_rows universe is
                    acc = 0.0
                    for f in m.WEIGHTS[p]:
                        if r['factors'][f]['score'] is not None:
                            acc += a['inner'][p][f] * r['factors'][f]['score'] / 100.0
                    self.assertAlmostEqual(acc, r['axes'][p]['score'], delta=1e-9, msg=(code, p))
                    seen['published'] += a['inner_basis'][p] == 'PUBLISHED'
        for k, n in seen.items():
            self.assertGreater(n, 0, k)


if __name__ == '__main__':
    unittest.main()
