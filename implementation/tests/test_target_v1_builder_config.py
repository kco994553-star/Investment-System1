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
        assert cfg[key]['version'] == 'v0' and cfg[key]['decision'] in ('UNCALIBRATED', 'OWNER_RULE', 'USER_DECISION_2026-10-15'), key


def test_owner_numbers_and_number_check_gate():
    cfg = _config()
    assert cfg['number_check_passed'] is False
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
