"""run_js_tests_parallel.js runs every manifest entry once, keeps the failure line run_js_tests.sh prints, runs solo tests last."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
WORKFLOWS = ROOT.parent / '.github/workflows'
NODE = shutil.which('node')


def _repo(tmp_path, tests):
    tools = tmp_path / 'implementation/tools'
    tools.mkdir(parents=True)
    shutil.copy(TOOLS / 'run_js_tests_parallel.js', tools)
    for name, body in tests.items():
        (tools / name).write_text(body)
    (tmp_path / 'manifest.txt').write_text(''.join(n + '\n' for n in tests))
    return tmp_path


def _run(root, *extra):
    return subprocess.run([NODE, 'implementation/tools/run_js_tests_parallel.js', 'manifest.txt', '--groups', '3', *extra],
                          cwd=root, capture_output=True, text=True, timeout=120)


def test_every_entry_runs_once_and_solo_runs_last(tmp_path):
    log = tmp_path / 'order.txt'
    tests = {f't{i}_test.js': f"require('fs').appendFileSync({str(log)!r}, 't{i}\\n');" for i in range(7)}
    root = _repo(tmp_path, tests)
    (root / 'solo.txt').write_text('t3_test.js\n')
    r = _run(root, '--solo', 'solo.txt')
    assert r.returncode == 0, r.stdout
    assert r.stdout.splitlines()[-1] == 'MANIFEST_OK tests=7'
    order = log.read_text().split()
    assert sorted(order) == sorted(f't{i}' for i in range(7)) and order[-1] == 't3'
    assert r.stdout.count('RUN ') == 7


def test_a_failure_fails_the_run_with_the_same_line_as_run_js_tests(tmp_path):
    root = _repo(tmp_path, {'ok_test.js': 'process.exitCode=0;', 'bad_test.js': 'process.exitCode=4;'})
    r = _run(root)
    assert r.returncode == 4
    assert 'CI_TEST_FAILED bad_test.js exit=4' in r.stdout and 'MANIFEST_OK' not in r.stdout


def test_daily_verify_names_the_failing_entry(tmp_path):
    root = _repo(tmp_path, {'ok_test.js': 'process.exitCode=0;', 'bad_test.js': 'process.exitCode=1;'})
    r = subprocess.run(['bash', str(TOOLS / 'daily_verify_step.sh'), 'manifest.txt', NODE, 'implementation/tools/run_js_tests_parallel.js',
                        'manifest.txt', '--groups', '2'], cwd=root, capture_output=True, text=True, timeout=120)
    assert r.returncode == 1 and 'DAILY_VERIFY_FAILED test=bad_test.js exit=1' in r.stdout


def test_stale_solo_and_empty_manifest_are_refused(tmp_path):
    root = _repo(tmp_path, {'ok_test.js': ''})
    (root / 'solo.txt').write_text('gone_test.js\n')
    assert 'STALE_SOLO_ENTRY gone_test.js' in _run(root, '--solo', 'solo.txt').stdout
    (root / 'manifest.txt').write_text('# nothing\n')
    assert 'EMPTY_TEST_MANIFEST' in _run(root).stdout


def test_both_workflows_run_the_whole_browser_list_through_it():
    solo = [l.split('#')[0].strip() for l in (TOOLS / 'ci_browser_tests_solo.txt').read_text().splitlines() if l.split('#')[0].strip()]
    listed = [l.split('#')[0].strip() for l in (TOOLS / 'ci_browser_tests.txt').read_text().splitlines() if l.split('#')[0].strip()]
    assert solo and set(solo) <= set(listed)
    for name in ('cockpit-pages.yml', 'sec-daily-public-inputs.yml'):
        text = (WORKFLOWS / name).read_text()
        assert 'run_js_tests_parallel.js implementation/tools/ci_browser_tests.txt --groups 3' in text, name
        assert 'run_js_tests.sh implementation/tools/ci_browser_tests.txt' not in text, name
