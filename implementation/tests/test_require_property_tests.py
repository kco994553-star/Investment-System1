"""tools/require_property_tests.py and its place in the required build job (owner 2026-11-05, #489 hand-over)."""
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import require_property_tests as R  # noqa: E402

PAGES = ROOT.parent / '.github/workflows/cockpit-pages.yml'
PROPS = sorted(R.module_tests())


def report(*cases):
    body = ''.join(cases)
    return f'<testsuites><testsuite name="pytest" tests="{len(cases)}">{body}</testsuite></testsuites>'


def case(name, cls=R.MODULE_CLASS, kid=''):
    return f'<testcase classname="{cls}" name="{name}" time="0.1">{kid}</testcase>'


def test_pins_are_exact_and_name_hypothesis():
    pins = R.pins()
    assert pins['hypothesis'] and all(v and '*' not in v for v in pins.values())


def test_missing_or_other_version_is_a_named_failure():
    def missing(name):
        raise metadata.PackageNotFoundError(name)
    assert R.check_installed({'hypothesis': '6.148.7'}, missing) == 'PROPERTY_DEPENDENCY_MISSING hypothesis'
    assert R.check_installed({'hypothesis': '6.148.7'}, lambda n: '6.0.0') == 'PROPERTY_DEPENDENCY_VERSION hypothesis'
    assert R.check_installed({'hypothesis': '6.148.7'}, lambda n: '6.148.7') is None


def test_module_skip_is_a_failure_not_a_pass():
    # What pytest 9.1.1 writes when importorskip skips the whole module: one skipped testcase, classname "", named after it.
    skipped = case(R.MODULE_CLASS, cls='', kid='<skipped type="pytest.skip" message="Install"/>')
    problem, counts = R.check_report(report(skipped, case('x', cls='tests.research.test_technical_screen_fixtures')), set(PROPS))
    assert problem == 'PROPERTY_TESTS_SKIPPED' and counts['skipped'] == 1 and counts['property_passed'] == 0


def test_all_property_tests_must_pass_and_be_present():
    full = report(*(case(n) for n in PROPS))
    assert R.check_report(full, set(PROPS)) == (None, {'tests': len(PROPS), 'skipped': 0, 'failed': 0, 'property_passed': len(PROPS)})
    assert R.check_report(report(*(case(n) for n in PROPS[1:])), set(PROPS))[0] == 'PROPERTY_TESTS_MISSING'
    failing = report(*(case(n, kid='<failure message="x"/>' if i == 0 else '') for i, n in enumerate(PROPS)))
    assert R.check_report(failing, set(PROPS))[0] == 'PROPERTY_TESTS_FAILED'
    assert R.check_report(report(), set())[0] == 'PROPERTY_TESTS_MISSING'


def test_property_module_defines_the_five_handed_over_properties():
    assert len(PROPS) == 5


def test_required_build_job_installs_pins_and_refuses_a_skip():
    text = PAGES.read_text(encoding='utf-8')
    build = text.split('\n  build:\n', 1)[1].split('\n  deploy:\n', 1)[0]
    assert 'python -m pip install pytest==9.1.1 jsonschema==4.26.0 -r tests/research/dependencies/technical-properties.txt\n' in build
    gate = build.index('- name: Technical property tests must run (Hypothesis, no skip)\n')
    suite = build.index('- name: Full Python unit suite\n')
    assert build.index('-r tests/research/dependencies/technical-properties.txt') < gate < suite
    step = build[gate:suite]
    assert '--junitxml="$RUNNER_TEMP/technical-properties.xml" tests/research/test_technical_properties.py tests/research/test_technical_screen_fixtures.py\n' in step
    assert 'python tools/require_property_tests.py "$RUNNER_TEMP/technical-properties.xml"\n' in step
    assert 'continue-on-error' not in step and '|| true' not in step
