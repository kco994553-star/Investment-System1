"""Production-shaped state presentation: freshness badges, persisted withheld metadata, ko/en strings.

The browser behaviour is tested by tools/web_state_presentation_browser_test.js on the fixture built by
tools/build_web_state_presentation_fixture.py. These tests pin the mirror of producers/freshness.py,
the locale entries and the presentation-only boundary without a browser.
"""
import importlib.util
import json
import re
from pathlib import Path

from investment_system.producers import freshness
from investment_system.producers.contract import SECTION_NAMES
from investment_system.product.web_mvp import STATES, validate_bundle

IMPL = Path(__file__).resolve().parents[1]
ASSETS = IMPL / 'src/investment_system/product/web_assets'
APP = (ASSETS / 'app.js').read_text(encoding='utf-8')
LOCALE = (ASSETS / 'locale.js').read_text(encoding='utf-8')
BRIDGE = (ASSETS / 'network-bridge.js').read_text(encoding='utf-8')
INDEX = (ASSETS / 'index.html').read_text(encoding='utf-8')
STYLE = (ASSETS / 'style.css').read_text(encoding='utf-8')
_spec = importlib.util.spec_from_file_location('web_state_fixture', IMPL / 'tools/build_web_state_presentation_fixture.py')
fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixture)


def _ui() -> dict:
    ui = json.loads(re.search(r'const UI=(\{.*?\});\n', LOCALE).group(1))
    for extra in re.findall(r'Object\.assign\(UI,(\{.*\})\);\n', LOCALE):
        ui.update(json.loads(extra))
    return ui


def _js_object(name: str) -> dict:
    m = re.search(r'const ' + name + r'=Object\.freeze\((\{[^}]*\})\);', APP)
    assert m, name
    return json.loads(re.sub(r'([{,])([A-Za-z_]+):', r'\1"\2":', m.group(1)))


def test_freshness_values_mirror_producer_freshness_exactly():
    m = re.search(r'const FRESHNESS=Object\.freeze\(\[([^\]]*)\]\);', APP)
    assert m
    assert json.loads('[' + m.group(1) + ']') == [freshness.FRESH, freshness.STALE, freshness.NOT_USABLE,
                                                  freshness.NOT_APPLICABLE]
    labels = _js_object('FRESHNESS_LABEL')
    assert set(labels) == {freshness.FRESH, freshness.STALE, freshness.NOT_USABLE}  # NOT_APPLICABLE: no badge
    # The Web adds no data state, no grant and no research display mode.
    assert STATES == {'LIVE', 'FROZEN_SNAPSHOT', 'DEMO', 'NOT_AVAILABLE'}
    assert 'DISPLAY_RESEARCH' not in APP


def test_stale_is_its_own_badge_with_its_own_style_rule():
    assert '" · STALE"' not in APP and '· STALE' not in APP
    assert 'class="badge freshness ${f}"' in APP
    for selector in ('.badge.LIVE', '.badge.freshness.FRESH', '.badge.freshness.STALE', '.badge.freshness.NOT_USABLE'):
        assert re.search(re.escape(selector) + r'\s*\{', STYLE), selector


def test_every_ui_string_has_ko_and_en_entries():
    ui = _ui()
    keys = set(re.findall(r'\bt\("((?:[^"\\]|\\.)*)"\)', APP))
    keys |= set(_js_object('FRESHNESS_LABEL').values()) | set(_js_object('META_LABEL').values())
    keys |= {re.search(r'const NOT_USABLE_REASON="([^"]+)";', APP).group(1), '관심기업'}
    keys |= set(re.findall(r'data-i18n="([^"]+)"', INDEX))
    missing = sorted(k for k in keys if not (ui.get(k, {}).get('ko-KR', '').strip() and ui.get(k, {}).get('en-US', '').strip()))
    assert not missing
    assert ui['데이터를 불러오는 중…']['en-US'] == 'Loading data…'


def test_listed_hard_coded_strings_go_through_i18n():
    assert '<p role="status" data-i18n="데이터를 불러오는 중…">' in INDEX
    for literal in ('" holdings"', '<h2>News / Relationships</h2>', 'block("qgv","QGV context"', 'block("technical","Technical context"',
                    'block("macro","Macro context"', ',"Prompt → Context', 'title="Prompt Library"', 'title="News Network"',
                    'notice("가져오기 실패: "'):
        assert literal not in APP, literal
    assert '"★ 관심기업"' not in BRIDGE and '"☆ 관심기업"' not in BRIDGE
    assert 'AppLanguage.text("관심기업", displayLocale)' in BRIDGE


def test_render_errors_fall_back_to_data_unavailable():
    m = re.search(r'function render\(\) \{(.*?)\n\}', APP, re.S)
    assert m and 'try {renderRoute();}' in m.group(1) and 'showUnavailable()' in m.group(1)
    assert 'window.addEventListener("hashchange", () => D && render());' in APP
    assert '.catch(showUnavailable)' in APP


def test_fixture_is_assembler_shaped_and_build_is_presentation_only(tmp_path):
    out, evidence = tmp_path / 'web', tmp_path / 'evidence'
    m = fixture.build_fixture(out, evidence)
    served = json.loads((out / 'data.json').read_text(encoding='utf-8'))
    assert served == fixture.fixture_bundle()
    for name in ('app.js', 'locale.js', 'style.css', 'index.html'):
        assert (out / name).read_bytes() == (ASSETS / name).read_bytes()
    persisted = {n: (s['state'], s['freshness'], s['reason_code']) for n, s in served['producer_manifest']['sections'].items()}
    assert persisted['macro'] == ('LIVE', freshness.FRESH, None)
    assert persisted['technical'] == ('LIVE', freshness.STALE, None)
    assert persisted['changes'] == ('LIVE', freshness.FRESH, None)
    assert persisted['leaderboard'] == ('NOT_AVAILABLE', freshness.NOT_USABLE, 'EXPIRED_NOT_USABLE')
    assert served['leaderboard']['data'] is None and served['leaderboard']['producer']['freshness'] == freshness.NOT_USABLE
    assert persisted['qgv'] == ('NOT_AVAILABLE', freshness.NOT_APPLICABLE, 'RESEARCH_DISPLAY_GRANT_NONE')
    # The view-time STALE of `changes` holds for the pinned browser clock.
    assert served['changes']['expires_at'] < m['browser_clock'].replace('Z', '+00:00')
    raw = (out / 'data.json').read_text(encoding='utf-8')
    assert not any(p in raw for p in fixture.WITHHELD_PROBES)
    for name in m['variants']:
        variant = json.loads((evidence / name).read_text(encoding='utf-8'))
        validate_bundle(variant)
        assert set(SECTION_NAMES) <= set(variant)
        assert {variant[s]['state'] for s in SECTION_NAMES} <= STATES
    assert m['research_display'] == m['frozen_grant'] == m['live_grant'] == 'NONE'
