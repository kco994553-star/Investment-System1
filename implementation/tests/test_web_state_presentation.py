"""Production-shaped state presentation: freshness badges, persisted withheld metadata, ko/en strings.

The browser behaviour is tested by tools/web_state_presentation_browser_test.js on the fixture built by
tools/build_web_state_presentation_fixture.py. These tests pin the mirror of producers/freshness.py,
the locale entries and the presentation-only boundary without a browser.
"""
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
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
    # Read each JSON dictionary regardless of whitespace or line breaks in locale.js.
    decoder = json.JSONDecoder()
    for extra in re.finditer(r'Object\.assign\(UI,\s*', LOCALE):
        ui.update(decoder.raw_decode(LOCALE, extra.end())[0])
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


def _strict_expiry():
    # app.js EXPIRES_AT as a Python pattern: JS \d is ASCII-only (re.ASCII), and fullmatch is JS ^...$ without the
    # m flag (JS $ does not match before a trailing newline).
    m = re.search(r'\nconst EXPIRES_AT=/\^(.*)\$/;\n', APP)
    assert m
    return re.compile(m.group(1), re.ASCII)


def _offset(hours: int, minutes: int = 0):
    return timezone(timedelta(hours=hours, minutes=minutes if hours >= 0 else -minutes))


def test_only_strict_iso_expires_at_reaches_date_parse():
    assert ('const EXPIRES_AT=/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}(:\\d{2}(\\.\\d{1,9})?)?(Z|[+-]\\d{2}:\\d{2})$/;'
            in APP)
    body = _function_body('freshnessOf')
    assert 'typeof s.expires_at==="string" && EXPIRES_AT.test(s.expires_at)?Date.parse(s.expires_at):NaN' in body
    assert body.count('Date.parse(') == 1
    strict = _strict_expiry()
    # What producers persist: datetime.isoformat() of an aware datetime (the assembler copies it verbatim), with
    # and without fractional seconds, for -23:59..+23:59 offsets, and the Z spelling. All keep FRESH reachable.
    offsets = [timezone.utc, _offset(9), _offset(5, 30), _offset(-12), _offset(14), _offset(23, 59), _offset(-23, 59)]
    for tz in offsets:
        for micro in (0, 1, 123456, 500000, 999999):
            dt = datetime(2026, 1, 3, 0, 0, 0, micro, tzinfo=timezone.utc).astimezone(tz)
            forms = [dt.isoformat()] + [dt.isoformat(timespec=t) for t in ('minutes', 'seconds', 'milliseconds', 'microseconds')]
            if tz is timezone.utc:
                forms += [f.replace('+00:00', 'Z') for f in forms]
            for form in forms:
                assert strict.fullmatch(form), form
                assert parse_ts(form, 'expires_at').utcoffset() == dt.utcoffset()
    bundle = fixture.fixture_bundle()
    for name in SECTION_NAMES:  # every expires_at the served fixture persists keeps its FRESH/STALE view
        if bundle[name].get('expires_at') is not None:
            assert strict.fullmatch(bundle[name]['expires_at']), name
    # Forms the contract accepts but outside the strict form: never handed to Date.parse, so never FRESH.
    for form in (*fixture.UNPARSABLE_EXPIRY.values(), *fixture.MISPARSED_EXPIRY.values(),
                 '2026-01-03 00:00:00+00:00', '2026-01-03t00:00:00+00:00', '2026-01-03T00:00:00+0000',
                 '2026-01-03T00+00:00', '2026-01-03T00:00:00+05:30:15', '2026-01-03T00:00:00.1234567890+00:00'):
        parse_ts(form, 'expires_at')
        assert not strict.fullmatch(form), form
    # Forms the contract rejects (reachable only through a hand-placed data.json): not handed to Date.parse either.
    for form in ('2026-01-03T00:00:00+00:00\n', '\uff12\uff10\uff12\uff16-01-03T00:00:00+00:00', '2026-01-03T00:00:00',
                 '2026-01-03', 'Sat, 03 Jan 2026 00:00:00 GMT', '+275760-09-13T00:00:00.000Z'):
        assert not strict.fullmatch(form), form


def test_misparsed_expiry_variants_are_contract_valid_persisted_fresh_and_outside_the_strict_form():
    bundle = fixture.fixture_bundle()
    variants, m = fixture.variants(bundle), fixture.manifest(bundle)
    strict = _strict_expiry()
    assert set(fixture.MISPARSED_EXPIRY.values()) == {'2026-01-03(00:00+23:59', '2026-01-03\x0000:00+23:59',
                                                      '2026-01-03(00:00:00+00:00'}
    assert m['timezones'] == ['UTC', 'Etc/GMT+12', 'Pacific/Kiritimati', 'Asia/Seoul']
    expected = {'2026-01-03(00:00+23:59': datetime(2026, 1, 2, 0, 1, tzinfo=timezone.utc),
                '2026-01-03\x0000:00+23:59': datetime(2026, 1, 2, 0, 1, tzinfo=timezone.utc),
                '2026-01-03(00:00:00+00:00': datetime(2026, 1, 3, tzinfo=timezone.utc)}
    for name, form in fixture.MISPARSED_EXPIRY.items():
        v = variants[name]
        validate_bundle(v)
        changes = v['changes']
        assert changes['expires_at'] == changes['producer']['expires_at'] == form
        expires = parse_ts(form, 'expires_at')  # the producer contract (and so the assembler) accepts the form
        assert expires == expected[form] and fixture.NOW < expires
        assert changes['producer']['freshness'] == v['producer_manifest']['sections']['changes']['freshness'] == freshness.FRESH
        # Outside the strict form: freshnessOf never hands it to Date.parse, so STALE at every clock in every zone.
        assert not strict.fullmatch(form)
        info = m['misparsed_expiry'][name]
        assert info['form'] == form and parse_ts(info['python_expires_at'], 'clock') == expires
        clocks = [parse_ts(c, 'clock') for c in info['after_expiry_clocks']]
        # Every browser clock the browser test uses is after the Python-parsed expiry (Python: not FRESH).
        assert len(clocks) == 3 and all(c > expires for c in clocks)
        assert parse_ts(fixture.BROWSER_CLOCK, 'clock') > expires
        assert {k: x for k, x in v.items() if k not in ('changes', 'producer_manifest')} == \
            {k: x for k, x in bundle.items() if k not in ('changes', 'producer_manifest')}


def test_strict_expiry_variants_stay_fresh_before_expiry():
    bundle = fixture.fixture_bundle()
    variants, m = fixture.variants(bundle), fixture.manifest(bundle)
    strict = _strict_expiry()
    assert len(fixture.STRICT_EXPIRY) == 6
    forms = set(fixture.STRICT_EXPIRY.values())
    assert any(f.endswith('Z') for f in forms) and any(f[-6] in '+-' for f in forms)
    assert any('.' in f for f in forms) and any('.' not in f for f in forms)
    for name, form in fixture.STRICT_EXPIRY.items():
        v = variants[name]
        validate_bundle(v)
        assert v['changes']['expires_at'] == form and strict.fullmatch(form)
        expires = parse_ts(form, 'expires_at')
        assert expires.replace(microsecond=0) == datetime(2026, 1, 3, tzinfo=timezone.utc)
        assert v['changes']['producer']['freshness'] == freshness.FRESH
        info = m['strict_expiry'][name]
        assert parse_ts(info['fresh_clock'], 'clock') < expires < parse_ts(info['stale_clock'], 'clock')


def test_displayed_count_keys_are_restricted_to_the_code_token_key_shape():
    assert 'const COUNT_KEY=/^[A-Za-z][A-Za-z0-9_]{0,63}$/;' in APP
    body = _function_body('coverageCounts')
    assert body.count('COUNT_KEY.test(k) && Number.isInteger(n)') == 2
    key = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,63}')
    bundle = fixture.fixture_bundle()
    for name in SECTION_NAMES:  # every count key the served fixture persists keeps its display
        v = bundle[name]['producer']['validation']
        for k in [*v.get('coverage_counts', {}), *(k for k in v if k.endswith('_count'))]:
            assert key.fullmatch(k), (name, k)
    variant = fixture.variants(bundle)['variant-free-text-count-keys.json']
    validate_bundle(variant)
    for entries, displayed in ((fixture.FREE_TEXT_COUNT_KEYS, False), (fixture.COUNT_KEY_EDGE, True)):
        for path, counts in entries.items():
            persisted = _persisted(variant, path)
            for k, n in counts.items():
                assert persisted[k] == n and isinstance(n, int)
                assert bool(key.fullmatch(k)) is displayed, k
                assert (fixture.COUNT_KEY_PROBE in k) is not displayed, k
                if path.endswith('.validation'):  # validation.*_count keys
                    assert k.endswith('_count'), k
    assert any(len(k) == 64 for c in fixture.COUNT_KEY_EDGE.values() for k in c)
    assert any(len(k) == 65 for c in fixture.FREE_TEXT_COUNT_KEYS.values() for k in c)
