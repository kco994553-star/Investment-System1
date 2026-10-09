"""Public build boundaries; holdings used here are synthetic and in memory only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from investment_system.product.web_mvp import ROOT, build, repository_bundle


MAP = 'docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json'
THEMES = 'docs/strategy_theme_owner/v1_1_cycle_20261008/CURRENT_TARGET_THEME_ASSIGNMENTS.json'


def test_public_build_has_exact_19_refs_and_target_metadata_without_holdings(tmp_path):
    build(tmp_path)
    path = tmp_path / 'actual-catalog.json'
    assert path.exists(), 'public device identity catalog is not built'
    catalog = json.loads(path.read_text())
    mapping = json.loads((ROOT / MAP).read_text())
    themes = json.loads((ROOT / THEMES).read_text())
    assert catalog['schema'] == 'DEVICE_ACTUAL_CATALOG/1'
    assert len(catalog['instruments']) == 19
    assert [i['security_reference'] for i in catalog['instruments']] == [r['security_ref'] for r in mapping['rows']]
    assert [i['target_units'] for i in catalog['instruments']] == [a['weight_units'] for a in themes['assignments']]
    assert sum(i['target_units'] for i in catalog['instruments']) == catalog['total_units'] == 10000
    assert catalog['identity_map_sha256'] == hashlib.sha256((ROOT / MAP).read_bytes()).hexdigest()
    assert catalog['target_root_sha256'] == mapping['source_root_sha256']
    assert catalog['instruments'][11]['ticker'] == 'GOOGL'
    assert catalog['instruments'][3]['currency'] == 'JPY'
    assert catalog['instruments'][4]['currency'] == 'KRW'
    serialized = path.read_text()
    for field in ('quantity', 'average_cost', 'positions', 'holdings'):
        assert '"' + field + '"' not in serialized
    assert (tmp_path / 'data.json').read_text() == json.dumps(repository_bundle(), ensure_ascii=False)


def test_catalog_rejects_tampered_identity_source(tmp_path):
    from investment_system.product.device_actual_catalog import public_actual_catalog
    for relative in (MAP, THEMES, 'docs/portfolio_target_owner/TARGET_v0.yaml'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    mapping = json.loads((tmp_path / MAP).read_text())
    mapping['rows'][11]['security_ref']['value'] = 'SYNTHETIC_UNREVIEWED'
    (tmp_path / MAP).write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match='identity source'):
        public_actual_catalog(tmp_path)


@pytest.mark.parametrize('placement', ['root', 'section', 'renamed'])
def test_build_rejects_device_holdings_before_writing_files(tmp_path, placement):
    bundle = deepcopy(repository_bundle())
    # Synthetic payload is only in memory. No filled device export is a fixture.
    private = {'schema': 'device-actual-holdings/1', 'kind': 'ACTUAL',
               'themes': [{'theme_id': 'semi_equipment', 'holdings': [
                   {'security_reference': {'scheme': 'ISIN', 'value': 'USN070592100'},
                    'quantity': '2', 'average_cost': '3', 'currency': 'USD'}]}]}
    if placement == 'root':
        bundle['device_actual'] = private
    elif placement == 'section':
        bundle['portfolio']['private_backup'] = private
    else:
        bundle['renamed'] = private['themes'][0]['holdings']
    with pytest.raises(ValueError, match='private holdings') as exc:
        build(tmp_path, bundle=bundle)
    assert 'USN070592100' not in str(exc.value)
    assert not list(tmp_path.iterdir())


def test_cockpit_has_local_input_link_and_separate_summary_container(tmp_path):
    build(tmp_path)
    html = (tmp_path / 'index.html').read_text()
    script = (tmp_path / 'app.js').read_text()
    assert 'device-actual.js' in html and 'device-actual.css' in html
    assert '#actual' in script
    assert 'device-actual-summary' in script
    assert 'DeviceActual.mount' in script and 'DeviceActual.summary' in script


def test_catalog_rejects_tampered_theme_catalog(tmp_path):
    from investment_system.product.device_actual_catalog import public_actual_catalog
    for relative in (MAP, THEMES, 'docs/portfolio_target_owner/TARGET_v0.yaml'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    themes = json.loads((tmp_path / THEMES).read_text())
    themes['catalog'][0]['target_units'] += 1
    (tmp_path / THEMES).write_text(json.dumps(themes))
    with pytest.raises(ValueError, match='theme source'):
        public_actual_catalog(tmp_path)


def test_cockpit_blocks_external_scripts_and_form_submission(tmp_path):
    build(tmp_path)
    html = (tmp_path / 'index.html').read_text()
    assert 'http-equiv="Content-Security-Policy"' in html
    assert "script-src 'self'" in html
    assert "form-action 'none'" in html
    assert "object-src 'none'" in html


def test_cockpit_loads_local_market_module_before_actual_and_mounts_key_settings(tmp_path):
    build(tmp_path)
    html = (tmp_path / 'index.html').read_text()
    assert 'device-market.js' in html
    assert html.index('device-market.js') < html.index('device-actual.js')
    assert (tmp_path / 'device-market.js').exists()
    script = (tmp_path / 'app.js').read_text()
    assert 'DeviceActual.settings' in script
    assert 'device-api-settings' in script
    assert "connect-src 'self'" in html


def test_google_sheet_assets_config_and_minimal_csp(tmp_path):
    from html.parser import HTMLParser
    build(tmp_path)
    class PolicyParser(HTMLParser):
        policy = ''
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy':
                self.policy = attrs['content']
    parser = PolicyParser()
    html = (tmp_path / 'index.html').read_text()
    parser.feed(html)
    directives = {parts[0]: parts[1:] for raw in parser.policy.split(';') if (parts := raw.split())}
    assert directives['script-src'] == ["'self'", 'https://accounts.google.com/gsi/client']
    assert directives['connect-src'] == ["'self'", 'https://sheets.googleapis.com', 'https://oauth2.googleapis.com']
    assert directives['frame-src'] == ["'self'", 'https://accounts.google.com']
    assert 'unsafe-inline' not in parser.policy and 'unsafe-eval' not in parser.policy
    for name in ('app-config.js', 'google-sheet-core.js', 'google-sheet-quotes.js', 'google-sheet-quotes.css'):
        assert (tmp_path / name).is_file() and name in html
    assert html.index('google-sheet-core.js') < html.index('google-sheet-quotes.js') < html.index('app.js')
    config = (tmp_path / 'app-config.js').read_text()
    assert 'googleSheetsClientId' in config and 'apps.googleusercontent.com' in config
    assert 'client_secret' not in config and 'spreadsheet_id' not in config
    assert 'GoogleSheetQuotes.mount' in (tmp_path / 'app.js').read_text()


@pytest.mark.parametrize('payload', [
    {'schema': 'device-market-data/1', 'quotes': [], 'fx': []},
    {'market_data': {'quotes': [{'price': '2', 'currency': 'USD'}]}},
    {'fx': [{'currency': 'JPY', 'rate': '3'}]},
    {'api_settings': {'provider': None}},
    {'api_key': 'SYNTHETIC_PRIVATE_TEST_VALUE'},
    {'apiKey': 'SYNTHETIC_PRIVATE_TEST_VALUE'},
    {'appSecret': 'SYNTHETIC_PRIVATE_TEST_VALUE'},
    {'accessToken': 'SYNTHETIC_PRIVATE_TEST_VALUE'},
    {'schema': 'device-google-sheet-settings/1', 'enabled': False},
    {'schema': 'device-market-import-history/1', 'entries': []},
    {'spreadsheetId': '_'.join(['synthetic'] * 5)},
    {'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/' + '_'.join(['synthetic'] * 5)},
    {'renamed': '.'.join(['ya29', 'constructed_runtime_token'])},
])
def test_build_rejects_private_quotes_fx_and_credential_inputs(tmp_path, payload):
    bundle = deepcopy(repository_bundle())
    bundle['renamed_private'] = payload
    with pytest.raises(ValueError, match='private device data') as exc:
        build(tmp_path, bundle=bundle)
    assert 'SYNTHETIC_PRIVATE_TEST_VALUE' not in str(exc.value)
    assert not list(tmp_path.iterdir())
