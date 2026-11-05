"""tools/require_property_tests.py and its place in the required build job (owner 2026-11-05, #489 hand-over)."""
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import require_property_tests as R  # noqa: E402

PAGES = ROOT.parent / '.github/workflows/cockpit-pages.yml'
EXPECTED = R.expected_tests()
PROPS = sorted(n for c, n in EXPECTED if c == R.MODULE_CLASS)


def report(*cases):
    body = ''.join(cases)
    return f'<testsuites><testsuite name="pytest" tests="{len(cases)}">{body}</testsuite></testsuites>'


def case(cls, name, kid=''):
    return f'<testcase classname="{cls}" name="{name}" time="0.1">{kid}</testcase>'


def full(skip=(), kid_for=None):
    return report(*(case(c, n, (kid_for or {}).get(n, '')) for c, n in sorted(EXPECTED) if n not in skip))


def test_pins_are_exact_and_name_hypothesis():
    pins = R.pins()
    assert pins['hypothesis'] and all(v and '*' not in v for v in pins.values())


def test_missing_or_other_version_is_a_named_failure():
    def missing(name):
        raise metadata.PackageNotFoundError(name)
    assert R.check_installed({'hypothesis': '6.148.7'}, missing) == 'PROPERTY_DEPENDENCY_MISSING hypothesis'
    assert R.check_installed({'hypothesis': '6.148.7'}, lambda n: '6.0.0') == 'PROPERTY_DEPENDENCY_VERSION hypothesis'
    assert R.check_installed({'hypothesis': '6.148.7'}, lambda n: '6.148.7') is None


def test_expected_set_is_five_properties_and_two_fixture_tests():
    assert len(PROPS) == 5 and len(EXPECTED) == 7


def test_module_skip_is_a_failure_not_a_pass():
    # What pytest 9.1.1 writes when importorskip skips the whole module: one skipped testcase, classname "", named after it.
    fixtures = [case(c, n) for c, n in sorted(EXPECTED) if c == R.FIXTURES_CLASS]
    xml = report(case('', R.MODULE_CLASS, '<skipped type="pytest.skip" message="Install"/>'), *fixtures)
    problem, counts = R.check_report(xml, EXPECTED)
    assert problem == 'PROPERTY_TESTS_SKIPPED'
    assert (counts['collected'], counts['passed'], counts['skipped'], counts['property_passed']) == (3, 2, 1, 0)


def test_all_expected_tests_must_pass_be_present_and_be_the_only_ones():
    assert R.check_report(full(), EXPECTED) == (None, {'expected': 7, 'collected': 7, 'passed': 7, 'skipped': 0, 'failed': 0, 'property_passed': 5})
    assert R.check_report(full(skip={PROPS[0]}), EXPECTED)[0] == 'PROPERTY_TESTS_MISSING'
    assert R.check_report(full(kid_for={PROPS[0]: '<failure message="x"/>'}), EXPECTED)[0] == 'PROPERTY_TESTS_FAILED'
    extra = full().replace('</testsuite>', case(R.MODULE_CLASS, 'test_unexpected') + '</testsuite>')
    assert R.check_report(extra, EXPECTED)[0] == 'PROPERTY_TESTS_COUNT'
    assert R.check_report(report(), set())[0] == 'PROPERTY_TESTS_MISSING'


def test_required_build_job_installs_pins_refuses_a_skip_and_repeats_the_result_at_the_end():
    text = PAGES.read_text(encoding='utf-8')
    build = text.split('\n  build:\n', 1)[1].split('\n  deploy:\n', 1)[0]
    assert 'python -m pip install pytest==9.1.1 jsonschema==4.26.0 -r tests/research/dependencies/technical-properties.txt\n' in build
    gate = build.index('- name: Technical property tests must run (Hypothesis, no skip)\n')
    suite = build.index('- name: Full Python unit suite\n')
    repeat = build.index('- name: Technical property result (repeated at the end of the log)\n')
    assert build.index('-r tests/research/dependencies/technical-properties.txt') < gate < suite < repeat
    step = build[gate:suite]
    assert step.index('python tools/require_property_tests.py --installed') < step.index('python -m pytest')
    assert '--junitxml="$RUNNER_TEMP/technical-properties.xml" tests/research/test_technical_properties.py tests/research/test_technical_screen_fixtures.py' in step
    assert 'python tools/require_property_tests.py "$RUNNER_TEMP/technical-properties.xml" > "$RUNNER_TEMP/technical-properties-result.txt" || { cat "$RUNNER_TEMP/technical-properties-result.txt"; exit 1; }\n' in step
    assert 'continue-on-error' not in step and '|| true' not in step
    tail = build[repeat:]
    assert '        if: always()\n' in tail and 'PROPERTY_RESULT_MISSING' in tail
    assert tail.count('\n      - ') <= 1, 'the repeat is the last step of the build job before upload'
