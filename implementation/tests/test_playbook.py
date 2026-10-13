"""Signal playbook v1 (docs/playbook/PLAYBOOK_V1.md): Python reference == fixture, device config copy == JSON, JS == Python."""
import importlib.util
import json
from pathlib import Path
import subprocess

from investment_system.qgv import playbook as P

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/playbook_reference_v1.json'
DOC = ROOT / 'docs/playbook/PLAYBOOK_V1.md'


def _reference():
    spec = importlib.util.spec_from_file_location('playbook_reference', ROOT / 'tools/playbook_reference.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_matches_python_reference():
    assert json.loads(FIXTURE.read_text(encoding='utf-8')) == json.loads(json.dumps(_reference().build(), ensure_ascii=False))


def test_device_config_copy_matches_json():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(ROOT / 'src/investment_system/product/web_assets/playbook-config-defaults.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == P.load_config()


def test_every_config_entry_carries_version_and_decision_state():
    cfg = P.load_config()
    assert (cfg['status'], cfg['calibration']) == ('v0', 'UNCALIBRATED')
    for key in ('levels', 'codes', 'transitions', 'type_profiles', 'type_rules_v0', 'special_rules', 'sector_checks', 'assignments'):
        for entry in cfg[key]:
            assert entry['version'] and entry['decision'] in cfg['decision_states'] or entry['decision'] == 'TYPE_CONFIG_V1', (key, entry)
    for key in ('defaults', 'rule_constants'):
        for name, entry in cfg[key].items():
            assert entry['version'] == 'v0' and entry['decision'] == 'UNCALIBRATED', name
    for key in ('conviction_choice', 'cooccurrence', 'type_membership', 'type_tie_order', 'financial_exception', 'evidence_grades', 'conviction',
                'record_fields', 'scoring_basis', 'v2_adjustments', 'macro', 'rebalancing', 'target_change', 'reassess_thresholds',
                'missing_qg_markets', 'thirteenf', 'news', 'operations'):
        assert cfg[key]['version'] and cfg[key]['decision'], key


def test_section_12_defaults_are_in_the_config_in_doc_order():
    text = DOC.read_text(encoding='utf-8')
    section = text[text.index('## 12. 기본값 (v0)'):text.index('## 13.')]
    labels = [line.split('|')[1].strip() for line in section.splitlines() if line.startswith('| ') and not line.startswith('| 항목') and not line.startswith('|---')]
    assert labels == ['비중 Band', '기본 R2 임계', '기본 V 임계', '기본 안전마진', '기본 재확인 간격', '기본 분할 횟수', 'R2 일회성 판정',
                      'R1 공시 확인 시 즉시 축소', 'R5 보류 연장', 'T2 입금 조정 한도', 'W2 진입', 'E1 실적 기간', '테마 쏠림', '확신 보유 상한', '확신 보유 점검']
    d = P.load_config()['defaults']
    assert [P.num({'defaults': d, 'rule_constants': {}}, k) for k in ('band_min_pp', 'band_target_ratio', 'r2_qg_points', 'v_points', 'safety_margin_pct',
            'recheck_days', 'split_count', 'r2_one_off_ratio', 'r5_max_extensions', 't2_deposit_limit_pp', 'w2_rank_max', 'w2_v_improve_points',
            'e1_days_before', 'theme_concentration_pct', 'conviction_cap_pct', 'conviction_review_months', 'conviction_review_risk_count')] == \
        [1, 0.2, 5, 10, 15, 14, 3, 0.5, 1, 2, 50, 10, 7, 40, 30, 12, 2]
    assert P.num(P.load_config(), 'r1_cut_fraction') == 1 / 3


def test_type_profiles_match_section_6_1_and_14():
    cfg = P.load_config()
    rows = {p['type']: (p['r2'], p['v_points'], p['safety_margin_pct'], p['recheck_days'], p['split_count']) for p in cfg['type_profiles']}
    assert rows == {'default': ({'qg': 5}, 10, 15, 14, 3), 'growth': ({'qg': 5, 'g': 7}, 15, 10, 14, 4), 'value': ({'qg': 5, 'q': 4}, 10, 25, 30, 3),
                    'dividend': ({'qg': 5, 'dividend_cut': True}, 10, 15, 30, 3), 'quality': ({'q': 3}, 15, 10, 30, 3),
                    'cyclical': ({'qg': 8}, 10, 20, 14, 4), 'defensive': ({'qg': 4}, 10, 15, 30, 2)}
    v2 = cfg['v2_adjustments']
    for r in v2['r2']:  # §14-1 = 2 × §6-1
        base = rows[r['type']][0]
        assert {k: (v * 2 if k != 'dividend_cut' else v) for k, v in base.items()} == {k: v for k, v in r.items() if k != 'type'}
    assert {r['type']: r['v_pct'] for r in v2['v_pct_standard']} == {'default': 60, 'growth': 50, 'value': 75, 'dividend': 60, 'quality': 50, 'cyclical': 70, 'defensive': 60}


def test_doc_prompts_are_kept_verbatim_in_the_doc():
    text = DOC.read_text(encoding='utf-8')
    assert text.startswith('# 신호 행동 기준(플레이북) v1\n')
    assert text.count('{공통 머리말}') == 6 and '[Investment-System1 · 신호 점검 프롬프트 v1]' in text


def test_javascript_engine_matches_python_vectors():
    out = subprocess.run(['node', '--test', str(ROOT / 'tools/playbook_node_test.js')], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-4000:] + out.stderr[-2000:]


def test_oct13_decisions_core_quarter_and_sic():
    cfg=P.load_config()
    assert {'W1','E4'} <= set(P.active_codes(cfg))
    base={'symbol':'SYN','held':True,'q_now':70,'g_now':70,'q_prev':70,'g_prev':70,
          'q_prev2':80,'g_prev2':80,'memberships':{},'macro_state':'NORMAL'}
    r=P.evaluate(cfg,base)
    assert r['primary']['code']=='R2'
    assert r['qg']['r2_hits'][0]['comparison']=='TWO_QUARTERS'
    assert P.sector_for(cfg,'SYN','XLK',3827)['sector']=='semi_equipment'
    assert P.sector_for(cfg,'SYN','XLI',3826)['sector']=='industrial_automation'
    assert P.sector_for(cfg,'SYN','XLK',9999)['sector']=='technology_hardware'
    typ=P.classify_types_v0(cfg,{'sic':5912,'revenue_volatility_5y_rank_pct':.2,
            'roic_avg_3y':.2,'operating_margin_std_5y_pp':2.9,'net_debt_to_ebitda':1})
    assert typ['quality']['member'] is True
    assert typ['defensive']['member'] is True
    info=P.evaluate(cfg,{'structural_news':True,'macro_state':'NORMAL'})
    assert info['primary']['code']=='E4' and info['choices']==[]


def test_quality_maintenance_macro_unavailable_and_trap_inclusive():
    cfg=P.load_config()
    r=P.evaluate(cfg,{'held':True,'memberships':{'quality':1},'q_now':70,'q_prev':70,
        'g_now':60,'g_prev':66,'v_now':70,'v_prev20':40,'macro_state':'CRISIS','macro_available_count':0})
    assert r['qg']['maintained'] is False
    assert r['macro']['state'] is None and r['macro']['label']=='매크로 확인 불가'


def test_strict_sic_invalid_input_never_crashes_or_classifies():
    cfg = P.load_config()
    for sic in ('', 'NA', True, False, 3559.9, float('inf'), float('nan'), -1, 10000, ' 3559'):
        assert P.sic_candidate(cfg, sic) is None
        assert P.sector_for(cfg, 'SYN', 'XLK', sic) == {'sector': 'technology_hardware', 'source': 'ETF_FALLBACK'}
    assert P.sic_candidate(cfg, '3559') == 'CYCLICAL'


def test_integral_sic_float_matches_javascript_numeric_representation():
    assert P.sic_candidate(P.load_config(), 3559.0) == 'CYCLICAL'
    assert P.sector_for(P.load_config(), 'SYN', 'XLK', 3827.0)['sector'] == 'semi_equipment'
