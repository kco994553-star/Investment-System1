"""M3 share_class_groups/v0: economically identical listed classes summed and ranked once (synthetic data only)."""
import copy
import dataclasses
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from investment_system.universe import private_subset as ps
from investment_system.universe import sec_universe_shares as shares_module
from investment_system.universe.share_class_groups import (
    CONFIG_STATUS, CONFIG_VERSION, LABEL_KO, SHARE_CLASS_GROUPS_V0, validate_share_class_groups,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/m3_share_class_groups_reference_v0.json'
SEC_TICKERS = ROOT / 'experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/sec_tickers_exchange_original.json'


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_t_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_is_regenerated_from_python_reference():
    fixture = json.loads(FIXTURE.read_text())
    assert fixture == json.loads(json.dumps(load_tool('m3_share_class_groups_reference').build()))
    assert fixture['config'] == SHARE_CLASS_GROUPS_V0
    assert len(fixture['cases']) == 14 and all(c['synthetic'] is True for c in fixture['cases'])


def test_fixture_records_are_valid_public_rows():
    cut = datetime(2030, 2, 10, 13, tzinfo=timezone.utc)
    for case in json.loads(FIXTURE.read_text())['cases']:
        for code, row in case['input']['records'].items():
            assert shares_module._record(code, row, cut, timedelta(days=14)) in shares_module.STATES


def test_reference_refuses_live_cases():
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        load_tool('m3_share_class_groups_reference').replay({'synthetic': False, 'input': {}}, SHARE_CLASS_GROUPS_V0)


def test_config_is_v0_uncalibrated_and_only_lists_universe_pairs():
    codes = shares_module.universe_codes()
    assert validate_share_class_groups(SHARE_CLASS_GROUPS_V0, codes) is SHARE_CLASS_GROUPS_V0
    assert SHARE_CLASS_GROUPS_V0['config_version'] == CONFIG_VERSION == 'share_class_groups/v0'
    assert SHARE_CLASS_GROUPS_V0['config_status'] == CONFIG_STATUS == 'V0_UNCALIBRATED'
    assert [(g['group_id'], g['cik'], tuple(g['codes'])) for g in SHARE_CLASS_GROUPS_V0['groups']] == [
        ('alphabet', '0001652044', ('NASDAQ:GOOGL', 'NASDAQ:GOOG')),
        ('fox', '0001754301', ('NASDAQ:FOXA', 'NASDAQ:FOX')),
        ('news_corp', '0001564708', ('NASDAQ:NWSA', 'NASDAQ:NWS')),
    ]
    # Conversion ratio != 1 classes are never grouped.
    assert not any(c.startswith(('NYSE:BRK', 'NYSE:BF')) for g in SHARE_CLASS_GROUPS_V0['groups'] for c in g['codes'])


@pytest.mark.skipif(not SEC_TICKERS.exists(), reason='archived SEC ticker/exchange metadata required')
def test_every_group_is_a_same_cik_listing_set_in_the_universe():
    """Archived official company_tickers_exchange.json: each group's codes are exactly that CIK's Universe listings."""
    data = json.loads(SEC_TICKERS.read_text())
    index = {}
    for row in data['data']:
        rec = dict(zip(data['fields'], row))
        index.setdefault((rec['exchange'], rec['ticker']), rec['cik'])
    by_cik = {}
    for code in shares_module.universe_codes():
        venue, symbol = code.split(':')
        cik = index.get(({'NASDAQ': 'Nasdaq', 'NYSE': 'NYSE'}.get(venue), symbol.replace('.', '-')))
        if cik is not None:
            by_cik.setdefault(str(cik).zfill(10), []).append(code)
    multi = {cik: sorted(c) for cik, c in by_cik.items() if len(c) > 1}
    assert {g['cik']: sorted(g['codes']) for g in SHARE_CLASS_GROUPS_V0['groups']} == multi


@pytest.mark.parametrize('mutate', [
    lambda c: c.update(config_status='CALIBRATED'),
    lambda c: c['groups'][0].update(codes=['NASDAQ:GOOGL']),
    lambda c: c['groups'][0].update(cover_class_count=1),
    lambda c: c['groups'][1]['codes'].__setitem__(0, 'NASDAQ:GOOG'),
    lambda c: c['groups'][1].update(cik='0001652044'),
    lambda c: c['groups'][0].update(ratio=1),
    lambda c: c['groups'][0]['codes'].__setitem__(1, 'NASDAQ:GOOGL'),
])
def test_config_validator_refuses_malformed_groups(mutate):
    config = copy.deepcopy(SHARE_CLASS_GROUPS_V0)
    mutate(config)
    with pytest.raises(ValueError, match='SHARE_CLASS_GROUPS_INVALID'):
        validate_share_class_groups(config)


def test_unknown_code_is_refused_against_universe():
    config = copy.deepcopy(SHARE_CLASS_GROUPS_V0)
    config['groups'][0]['codes'][1] = 'NASDAQ:ZZZZ'
    assert validate_share_class_groups(config) is config
    with pytest.raises(ValueError, match='SHARE_CLASS_GROUPS_INVALID'):
        validate_share_class_groups(config, shares_module.universe_codes())


def test_group_result_has_no_price_field_and_label():
    fields = {f.name for f in dataclasses.fields(ps.ShareClassGroupCheck)}
    assert not any('price' in f for f in fields)
    case = next(c for c in json.loads(FIXTURE.read_text())['cases'] if c['id'] == 'alphabet_two_classes_summed_ranked_once')
    group = case['expected']['groups'][0]
    assert group['quality_label'] == LABEL_KO and group['effective_cap'] == 5800 * 150 + 5400 * 151
    assert group['member_shares'] == [5800, 5400] and group['cover_class_count'] == 3


def test_existing_public_shares_vectors_unchanged_with_groups_enabled():
    """No v1 vector uses a grouped code: adding prepare_share_class_groups keeps every selection identical."""
    v1 = load_tool('m3_public_shares_reference')
    fixture = json.loads((ROOT / 'tests/fixtures/m3_public_shares_reference_v1.json').read_text())
    groups_ref = load_tool('m3_share_class_groups_reference')
    for case in fixture['cases']:
        with_groups = groups_ref.replay(case, SHARE_CLASS_GROUPS_V0)
        assert with_groups['groups'] == []
        expected = case['expected']['selection']
        assert {k: with_groups['selection'][k] for k in expected} == expected
        assert v1.replay(case) == case['expected']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_device_config_equals_python_copy():
    script = ("const g=require(process.argv[1]);console.log(JSON.stringify(g.CONFIG))")
    out = subprocess.run(['node', '-e', script, str(ROOT / 'src/investment_system/product/web_assets/share-class-groups.js')],
                         text=True, capture_output=True, check=True).stdout
    assert json.loads(out) == SHARE_CLASS_GROUPS_V0
