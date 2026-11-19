"""Static checks for the scheduled browser-look run (owner 2026-11-18, PR-check time: look-only checks move out of the PR
checks, the manual deploy and the daily verify; boundary, value and data-safety checks stay in them)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT.parent / '.github/workflows/browser-look.yml').read_text()
TOOLS = ROOT / 'tools'


def _names(path):
    return [n for n in (line.split('#', 1)[0].strip() for line in path.read_text().splitlines()) if n]


def test_look_list_is_exactly_the_look_part_and_its_reasons_are_written_down():
    assert _names(TOOLS / 'ci_browser_tests_look.txt') == ['web_state_presentation_look_browser_test.js']
    text = (TOOLS / 'ci_browser_tests_look.txt').read_text()
    for kept in ('pc_layout', 'global_language_search'):
        assert kept in text, kept  # named, with why it stays in the PR check


def test_pr_list_keeps_the_safety_part_and_every_named_value_test():
    listed = set(_names(TOOLS / 'ci_browser_tests.txt'))
    assert 'web_state_presentation_safety_browser_test.js' in listed
    assert 'web_state_presentation_browser_test.js' not in listed and 'web_state_presentation_look_browser_test.js' not in listed
    assert {'pc_layout_browser_test.js', 'global_language_search_browser_test.js'} <= listed
    assert not listed & set(_names(TOOLS / 'ci_browser_tests_look.txt'))


def test_the_two_parts_cover_every_check_and_the_safety_part_holds_the_boundary_and_value_checks():
    for part in ('safety', 'look'):
        wrapper = (TOOLS / f'web_state_presentation_{part}_browser_test.js').read_text()
        assert f'process.env.WEB_STATE_PRESENTATION_PART = "{part}"' in wrapper
        assert 'require("./web_state_presentation_browser_test.js")' in wrapper
    source = (TOOLS / 'web_state_presentation_browser_test.js').read_text()
    assert 'await safetyCheck("public data.json is all NOT_AVAILABLE' in source
    for tag in ('U1', 'U2', 'U4'):
        assert f'await safetyCheck(`${{locale}}: {tag} ' in source and f'await check(`${{locale}}: {tag} ' not in source
    assert source.count('await lookCheck(`${locale}: U3 ') == 2
    assert 'await lookCheck(`${locale}: 390px routes have no horizontal overflow' in source
    # PPA-F08 (ACTUAL never falls back to TARGET) and the final traffic/error check run in every part.
    assert 'await check(`${locale}: PPA-F08 ' in source
    assert 'await check("no page errors, external calls, unsafe requests or failed responses"' in source


def test_it_runs_on_a_schedule_and_gates_nothing():
    assert re.findall(r"- cron: '([^']+)'", WORKFLOW) == ['41 18 * * *']
    assert 'permissions:\n  contents: read\n' in WORKFLOW and WORKFLOW.count('permissions:') == 1
    for word in ('secrets.', 'deploy-pages', 'upload-pages-artifact', 'workflow_run', 'needs:', 'write'):
        assert word not in WORKFLOW, word
    assert 'run_js_tests.sh implementation/tools/ci_browser_tests_look.txt' in WORKFLOW
    paths = WORKFLOW.split('  pull_request:\n', 1)[1].split('permissions:', 1)[0]
    assert '.github/workflows/browser-look.yml' in paths and 'implementation/tools/ci_browser_tests_look.txt' in paths
