"""Static checks for the date-shifted browser run (owner 2026-11-16: daily +7, weekly +50, alert only)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT.parent / '.github/workflows/browser-date-shift.yml').read_text()
TOOLS = ROOT / 'tools'
EXCLUDED = {'settings_import_browser_test.js', 'device_actual_browser_test.js', 'sic_theme_v0_browser_test.js',
            'web_app_first_paint_browser_test.js',
            # owner 2026-11-18: the fifth, +50-day CI failure with no date input, cause not established
            'global_language_search_browser_test.js'}


def _names(path):
    return [n for n in (line.split('#', 1)[0].strip() for line in path.read_text().splitlines()) if n]


def test_exclusions_are_exactly_the_five_recorded_tests_each_with_a_reason():
    lines = [l for l in (TOOLS / 'ci_browser_tests_date_shift_exclude.txt').read_text().splitlines()
             if l.strip() and not l.lstrip().startswith('#')]
    assert {l.split('#', 1)[0].strip() for l in lines} == EXCLUDED
    assert all('#' in l and l.split('#', 1)[1].strip() for l in lines)


def test_excluded_tests_stay_in_the_normal_browser_list():
    assert EXCLUDED <= set(_names(TOOLS / 'ci_browser_tests.txt'))


def test_schedules_are_daily_plus7_and_weekly_plus50_only():
    assert re.findall(r"- cron: '([^']+)'", WORKFLOW) == ['17 19 * * *', '47 19 * * 6']
    assert "'17 19 * * *') shifts='7'" in WORKFLOW and "'47 19 * * 6') shifts='50'" in WORKFLOW


def test_it_gates_nothing_and_holds_no_secret_or_write_permission():
    assert 'permissions:\n  contents: read\n' in WORKFLOW
    assert WORKFLOW.count('permissions:') == 1
    for word in ('secrets.', 'deploy-pages', 'upload-pages-artifact', 'workflow_run', 'needs:', 'write'):
        assert word not in WORKFLOW, word


def test_pull_requests_run_it_only_when_the_check_itself_changes():
    paths = WORKFLOW.split('  pull_request:\n', 1)[1].split('permissions:', 1)[0]
    assert re.findall(r'^      - (\S+)$', paths, re.M) == [
        '.github/workflows/browser-date-shift.yml', 'implementation/tools/clock_shift_preload.js',
        'implementation/tools/run_js_tests_date_shift.sh', 'implementation/tools/ci_browser_tests_date_shift_exclude.txt']


def test_normal_checks_do_not_load_the_shift_harness():
    for path in (ROOT.parent / '.github/workflows').glob('*.y*ml'):
        if path.name != 'browser-date-shift.yml':
            text = path.read_text()
            assert 'clock_shift_preload' not in text and 'run_js_tests_date_shift' not in text, path.name
    assert 'clock_shift_preload' not in (TOOLS / 'run_js_tests.sh').read_text()
