"""TARGET v1 builder config (owner decision 2026-10-14, follow-ups 2026-10-15): device JS copy == JSON, v0 · UNCALIBRATED, number check off by default."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'src/investment_system/qgv/target_v1_builder_v0.json'
DEVICE = ROOT / 'src/investment_system/product/web_assets/target-v1-config-defaults.js'


def _config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def test_device_config_copy_matches_json():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(DEVICE)], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == _config()


def test_every_section_is_v0_with_a_decision_state():
    cfg = _config()
    assert (cfg['status'], cfg['calibration'], cfg['config_version']) == ('v0', 'UNCALIBRATED', 'target_v1_builder/v0')
    sections = [k for k, v in cfg.items() if isinstance(v, dict)]
    assert sections
    for key in sections:
        assert cfg[key]['version'] == 'v0' and cfg[key]['decision'] in ('UNCALIBRATED', 'OWNER_RULE', 'USER_DECISION_2026-10-15', 'USER_DECISION_2026-10-15_EVENING'), key


def test_owner_numbers_and_number_check_gate():
    cfg = _config()
    assert 'number_check_passed' not in cfg
    # 2026-10-23 user decision: app formula check with test prices passed for the published calc_version; device quote path is a follow-up.
    assert cfg['number_check']['result'] == {'calc_version': 'qgv2-calc/2026-10-17.1', 'passed': True, 'date': '2026-10-23', 'companies': 10}
    assert (cfg['number_check']['result_basis'], cfg['number_check']['device_quote_path']) == ('APP_FORMULA_TEST_PRICE', 'UNVERIFIED_FOLLOW_UP')
    assert cfg['number_check']['result_label_ko'] == '앱 계산식 대조 통과(시험 가격) / 실기기 시세 경로 미검증'
    assert cfg['number_check']['companies_required'] == 10
    sel = cfg['selection']
    assert (sel['count'], sel['core']['count'], sel['core']['pct'], sel['general']['count'], sel['general']['pct']) == (15, 5, 8, 10, 6)
    assert sel['core']['count'] * sel['core']['pct'] + sel['general']['count'] * sel['general']['pct'] == sel['sum_pct'] == 100
    fs = cfg['filters']['financial_safety']
    assert (fs['net_debt_to_ebitda_fail_at_or_above'], fs['interest_coverage_fail_below']) == (3, 3)
    assert (cfg['filters']['axis_min_weight'], cfg['sector_spread']['max_per_subgroup'], cfg['candidates']['count']) == (0.5, 4, 30)
    assert [r['month'] for r in cfg['transition']['rounds']] == ['2026-11', '2027-02', '2027-05'] and cfg['transition']['step_fraction'] == [1, 3]
    assert cfg['review_rule']['before_round'] == 3 and cfg['review_rule']['suggestion_only'] is True
    assert cfg['virtual_sets']['backfill'] is False


def test_follow_up_decisions_2026_10_15():
    cfg = _config()
    assert '2026-10-15' in cfg['decided_followups']
    for key, tag in (('coverage', 'T-COV'), ('rebalance', 'T-REBAL'), ('scoring_prices', 'T-PRICE')):
        assert cfg[key]['decision'] == 'USER_DECISION_2026-10-15', key
        assert cfg[key]['decided'].startswith('2026-10-15') and tag in cfg[key]['decided'], key
    assert cfg['coverage']['ready_min_ratio'] == 0.9
    reb = cfg['rebalance']
    assert (reb['months'], reb['day_rule'], reb['holiday_rule']) == ([2, 5, 8, 11], 'MONDAY_OF_DAYS_15_TO_21', 'NEXT_SESSION')
    sets = cfg['virtual_sets']
    assert sets['rule_ids'] == ['R-B', 'R-C'] and 'T-SET' in sets['naming_decided']
    assert 'B' not in sets and 'C' not in sets and sets['A']['ko'] == '세트 A · TARGET v0'
    for rid in sets['rule_ids']:
        assert sets[rid]['id'] == rid and sets[rid]['source_ko'] == '규칙 지수' and sets[rid]['ko'].startswith(rid + ' · ')
    assert cfg['review_rule']['condition'] == 'R_B_AND_R_C_BELOW_A_AND_SP500'
    sp = cfg['scoring_prices']
    assert (sp['tab'], sp['benchmark'], sp['write'], sp['record_primary_code']) == ('Prices_D', 'SPY', 'USER_BUTTON_WITH_CONFIRM', 'TV1')


def test_owner_supplement_2026_10_15():
    cfg = _config()
    fc = cfg['finalize_check']
    assert fc['decision'] == 'USER_DECISION_2026-10-15_EVENING' and fc['reread'] == 'AT_FINALIZE' and fc['calc_version_required'] is True
    assert fc['legacy_without_calc_version'] == 'FAIL' and fc['source_file'] == 'sec-qgv2.json'
    # 2026-10-15 evening: T-FRESH = 7 days per row acquisition time, never the file as_of; draft basis link.
    assert (fc['freshness_max_days'], fc['freshness_basis'], fc['file_as_of_counts_for_freshness']) == (7, 'ROW_ACQUIRED_AT', False)
    assert 'all_shards=true' in fc['stale_action_ko'] and 'CALC_VERSION_MIXED' in fc['na_row_rule']
    assert fc['draft_basis_compare'] == ['calc_version', 'shard_count', 'shards'] and fc['on_basis_change'] == 'REGENERATE_DRAFT'
    assert (fc['answers_on_regenerate'], fc['financial_safety_recheck']) == ('CARRY_SAME_SYMBOLS', 'SELECTED_AT_FINALIZE')
    assert cfg['number_check']['decision'] == 'USER_DECISION_2026-10-15'
    fs = cfg['filters']['financial_safety']
    assert (fs['missing_for_exclusion'], fs['missing_reason']) == ('EXCLUDED', 'FINANCIAL_SAFETY_NOT_AVAILABLE')
    assert cfg['selection']['name_shortfall'] == 'BLOCK_FINALIZE'
    sch = cfg['schedule']
    assert sch['finalize_window'] == ['2026-11-09', '2026-11-15'] and sch['deadline'] == '2026-11-15'
    assert (sch['if_missed'], sch['unfinalized_round_mode']) == ('POSTPONE', 'RISK_CODE_CHECK_ONLY')
    assert sch['deadline'] < cfg['transition']['rounds'][0]['month'] + '-16'
