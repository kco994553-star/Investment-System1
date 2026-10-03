"""Production-shaped state presentation: freshness badges, persisted withheld metadata, ko/en strings.

The browser behaviour is tested by tools/web_state_presentation_browser_test.js on the fixture built by
tools/build_web_state_presentation_fixture.py. These tests pin the mirror of producers/freshness.py,
the locale entries and the presentation-only boundary without a browser.
"""
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from investment_system.producers import freshness
from investment_system.producers.contract import SECTION_NAMES, parse_ts
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


def _function_body(name: str) -> str:
    m = re.search(r'\nfunction ' + name + r'\([^)]*\) \{\n(.*?)\n\}\n', APP, re.S)
    assert m, name
    return m.group(1)


def test_persisted_fresh_alone_never_yields_fresh():
    body = _function_body('freshnessOf')
    # FRESH requires a string expires_at that Date.parse turns into a finite instant ahead of the clock;
    # an unparsable or absent expires_at fails closed as STALE whatever freshness was persisted.
    assert 'Number.isFinite(' in body and 'persisted==="FRESH"' not in body


def test_unparsable_expiry_variants_are_contract_valid_and_persisted_fresh():
    variants = fixture.variants(fixture.fixture_bundle())
    clock = parse_ts(fixture.BROWSER_CLOCK, 'clock')
    assert len(fixture.UNPARSABLE_EXPIRY) == 3
    for name, form in fixture.UNPARSABLE_EXPIRY.items():
        v = variants[name]
        validate_bundle(v)
        changes = v['changes']
        assert changes['expires_at'] == changes['producer']['expires_at'] == form
        expires = parse_ts(form, 'expires_at')  # the producer contract (and so the assembler) accepts the form
        assert expires.replace(microsecond=0) == datetime(2026, 1, 3, tzinfo=timezone.utc)
        assert fixture.NOW < expires < clock
        assert changes['producer']['freshness'] == v['producer_manifest']['sections']['changes']['freshness'] == freshness.FRESH
        # Only changes.expires_at differs from the served bundle.
        base = fixture.fixture_bundle()
        assert {k: x for k, x in v.items() if k not in ('changes', 'producer_manifest')} == \
            {k: x for k, x in base.items() if k not in ('changes', 'producer_manifest')}


_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,63}')


def _token(v) -> bool:
    return isinstance(v, str) and 0 < len(v) <= 64 and not re.search(r'\s', v)


def _persisted(bundle: dict, key: str):
    name, *path = key.split('.')
    v = bundle[name]['producer']
    for k in path:
        v = v[k]
    return v


def test_displayed_identifiers_are_restricted_to_code_and_token_shapes():
    assert 'const REASON_CODE=/^[A-Z][A-Z0-9_]{0,63}$/;' in APP
    meta = _function_body('persistedMeta')
    assert 'metaCode(p.reason_code) || metaCode(m.reason_code)' in meta and '.map(metaToken)' in meta
    bundle = fixture.fixture_bundle()
    # Every identifier the producer path persists in the served fixture keeps its display.
    for name in SECTION_NAMES:
        p = bundle[name]['producer']
        assert p['reason_code'] is None or _CODE.fullmatch(p['reason_code']), name
        assert _token(p['methodology']['id']) and _token(p['methodology']['version']), name
    variant = fixture.variants(bundle)['variant-free-text-metadata.json']
    validate_bundle(variant)
    for key, value in fixture.FREE_TEXT.items():
        assert _persisted(variant, key) == value
        shaped = _CODE.fullmatch(value) if key.endswith('reason_code') else _token(value)
        assert not shaped and sum(probe in value for probe in fixture.FREE_TEXT_PROBES) == 1, key
    for key, value in fixture.EDGE.items():
        assert _persisted(variant, key) == value and len(value) == 64
        assert _CODE.fullmatch(value) if key.endswith('reason_code') else _token(value)
    for name in ('qgv', 'portfolio', 'relationships', 'news'):  # the manifest copy carries the same value
        assert variant['producer_manifest']['sections'][name]['reason_code'] == variant[name]['producer']['reason_code']
