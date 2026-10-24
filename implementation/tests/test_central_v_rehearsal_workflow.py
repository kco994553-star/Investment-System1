"""Central V rehearsal workflow (GSQ-024 "검증 먼저", owner instruction 2026-10-24 item 3b): .github/workflows/central-v-rehearsal.yml
and tools/central_v_rehearsal_report.py; doc docs/qgv_scoring_standard/CENTRAL_V_REHEARSAL_20261025.md.

Pinned: push-only trigger on claude/central-v-rehearsal; no raw-repo write token, no upload, deploy, cache, ledger, history or job
summary; the publication's two Secrets only in the presence job (as yes/no comparisons) and in the V step, SEC_USER_AGENT only in
the presence job and the SEC collection steps; ubuntu-24.04; every checkout without credentials; the V step byte for byte the
production one; the collection steps the production commands. The presence job, the measurement steps, the check step and the
verdict tool are run locally (synthetic publication from tests/test_qgv_official.py builders, no network).

Plain-text workflow reads (CI has no YAML parser); one extra YAML parse when PyYAML happens to be installed.
"""
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from investment_system.providers import iex_hist
from investment_system.qgv import qgv_official as qo
from investment_system.universe import sec_qgv2
from tests.test_public_price_boundary import prohibit_network  # noqa: F401  (autouse: every test here is offline)
from tests.test_qgv_official import CANARY, KEY, NOW, base_payload, synthetic_day, tool as publisher
from tests.test_qgv_official_workflow import V_STEP, env_of, jobs_of, named, run_lines, steps_of

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
REHEARSAL = REPO / '.github/workflows/central-v-rehearsal.yml'
DAILY = REPO / '.github/workflows/sec-daily-public-inputs.yml'
DOC = ROOT / 'docs/qgv_scoring_standard/CENTRAL_V_REHEARSAL_20261025.md'
BRANCH = 'claude/central-v-rehearsal'
GUARD = 'python implementation/tools/pages_artifact_guard.py --artifact-dir "$RUNNER_TEMP/public-cockpit"'
PINS = ('uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4',
        'uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5',
        'uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4')
PRESENCE_STEP = 'Print presence booleans for the three Secrets and check the start window (names and yes/no only)'
BEFORE_STEP = 'Measure before the V step (time, disk, memory; numbers only)'
AFTER_STEP = 'Measure after the V step (time, disk, memory; numbers only)'
CHECK_STEP = 'Check the V files without prices (artifact guard and strict check, no Secret)'
VERDICT_STEP = 'Rehearsal verdict (fixed codes and counts only)'
START_STEP = 'Record the rehearsal start time'
SEC_STEPS = ('Collect public SEC shares and filing metadata through Codex2 client',
             'Collect Universe504 SEC shard (price-free shares and Q·G factor projections)',
             'Collect SEC SIC, 10-K Item 1 and basket-ETF N-PORT evidence for industry/theme v0',
             'Collect company web domains for build-time logos (SEC website, then Wikidata P856; domains only)',
             'Verify 13F manager CIKs and project reported quantity changes',
             'Collect SEC 8-K current reports for TARGET (title, link, time and item metadata only)')
# Production collect steps the rehearsal leaves out (doc section 2): two need the OpenDART key and feed neither sec-qgv2.json nor
# the V step, the ledger and the D9 history write to the private raw repository, the upload publishes.
LEFT_OUT = {'Collect OpenDART disclosures and periodic financials for 042700 (fixed codes and call count only)',
            'Project collected DART inputs with the same QGV v2 formulae (reference only)',
            'Append forward validation ledger (price-free, append-only)',
            'Copy a new central QGV publication to the private dated history (scores only, no prices)',
            'Upload checked public SEC Pages artifact'}
STAGES = {  # production step name -> (stage name in stages.txt, required)
    'Record run context (event, mode, start time, observation day, shard)': ('run_context', False),
    'Offline public boundary regression (GSQ-010)': ('offline_regression', True),
    'Build and inspect local price-free cockpit': ('cockpit_build', True),
    SEC_STEPS[0]: ('sec_public_inputs', True),
    SEC_STEPS[1]: ('universe_all_shards', True),
    SEC_STEPS[2]: ('sic_theme', True),
    SEC_STEPS[3]: ('domains_logos', True),
    SEC_STEPS[4]: ('thirteen_f', True),
    SEC_STEPS[5]: ('sec_8k', False),
    'Collect news signals for TARGET (GDELT DOC 2.0 and company IR feeds; title, link and time only, never a score input)': ('news', False),
    'Report published Q·G coverage of the final artifact (counts only)': ('published_coverage', False),
}


def _load(name):
    spec = importlib.util.spec_from_file_location('rehearsal_' + name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report_tool = _load('central_v_rehearsal_report')


def _code(text):
    """The workflow without comment lines (the rules below are about what runs, not what the comments say)."""
    return '\n'.join(l for l in text.splitlines() if not l.lstrip().startswith('#'))


@pytest.fixture(scope='module')
def wf():
    text = REHEARSAL.read_text()
    jobs = jobs_of(text)
    return text, jobs, steps_of(jobs['rehearsal'])


def _name(step):
    return step.split('\n', 1)[0][len('name: '):] if step.startswith('name: ') else None


# ---- trigger, permissions, runner ---------------------------------------------------------------------------------------
def test_it_runs_only_when_the_rehearsal_branch_is_pushed(wf):
    text, jobs, _ = wf
    code = _code(text)
    assert '\non:\n  push:\n    branches:\n      - claude/central-v-rehearsal\npermissions:\n' in code
    for trigger in ('schedule', 'cron', 'pull_request', 'workflow_dispatch', 'workflow_run', 'workflow_call', 'repository_dispatch',
                    'tags:', 'paths:', 'branches-ignore'):
        assert trigger not in code, trigger
    assert code.count('branches:') == 1 and code.count(BRANCH) == 1
    assert set(jobs) == {'presence', 'rehearsal'}
    # no other workflow is started by pushing that branch (all others run on pull requests, dispatch or their own branches)
    for path in sorted((REPO / '.github/workflows').glob('*.y*ml')):
        if path != REHEARSAL:
            assert BRANCH not in path.read_text(), path.name


def test_read_only_permissions_own_concurrency_pinned_runner_and_time_limits(wf):
    text, jobs, _ = wf
    code = _code(text)
    assert code.count('permissions:') == 1 and '\npermissions:\n  contents: read\nconcurrency:\n' in code
    for forbidden in ('contents: write', 'pages: write', 'id-token', 'actions: write', 'packages', 'environment:'):
        assert forbidden not in code, forbidden
    assert '\nconcurrency:\n  group: central-v-rehearsal\n  cancel-in-progress: false\njobs:\n' in code
    assert 'group: sec-daily-public-inputs' not in code and 'checked-cockpit-pages' not in code
    assert code.count('runs-on:') == code.count('runs-on: ubuntu-24.04') == 2
    assert '    timeout-minutes: 5\n' in jobs['presence'] and '    timeout-minutes: 140\n' in jobs['rehearsal']
    assert "    needs: presence\n    if: needs.presence.outputs.ready == 'true'\n" in jobs['rehearsal']


def test_no_raw_repo_write_token_upload_deploy_cache_ledger_history_or_summary(wf):
    text, _, steps = wf
    assert 'RAW_REPO_TOKEN' not in text                                  # not even in a comment
    code = _code(text)
    for forbidden in ('actions/upload', 'upload-artifact', 'upload-pages-artifact', 'deploy-pages', 'download-artifact', 'actions/cache',
                      'cache:', 'GITHUB_STEP_SUMMARY', 'GITHUB_ENV', 'GITHUB_PATH', 'git push', 'git commit', 'curl ', 'wget ',
                      'tools/forward_validation_ledger.py', 'tools/qgv_official_history.py', 'tools/dart_daily.py',
                      'tools/project_dart_qgv2.py', 'FORWARD_LEDGER_PREVIOUS_SOURCE',
                      'raw_store_release', 'api.github.com', 'always()', 'pull_request_target'):
        assert forbidden not in code, forbidden
    assert not re.search(r'(?:^|[\s;&|({])gh\s', '\n'.join(l for s in steps if 'run:' in s for l in run_lines(s)))
    uses = re.findall(r'uses: [^\n]+', code)
    assert sorted(uses) == sorted(PINS)
    assert code.count('actions/checkout@') == code.count('persist-credentials: false') == 1
    checkout = next(s for s in steps if s.startswith(PINS[0]))
    assert checkout == PINS[0] + '\n        with:\n          persist-credentials: false'


# ---- Secrets ------------------------------------------------------------------------------------------------------------
def test_secrets_only_in_the_presence_step_the_v_step_and_the_sec_collection_steps(wf):
    text, jobs, steps = wf
    code = _code(text)
    assert set(re.findall(r'secrets\.([A-Z_]+)', code)) == {'QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN', 'SEC_USER_AGENT'}
    # presence: three yes/no comparisons evaluated by GitHub; no value reaches the runner, no checkout, one step
    presence = steps_of(jobs['presence'])
    assert len(presence) == 1 and _name(presence[0]) == PRESENCE_STEP and 'uses:' not in jobs['presence']
    assert env_of(presence[0]) == {f'{n}_SET': "${{ secrets.%s != '' }}" % n
                                   for n in ('QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN', 'SEC_USER_AGENT')}
    # the V step holds the publication's two Secrets, the SEC steps SEC_USER_AGENT only, every other step none
    holders = {}
    for step in steps:
        found = re.findall(r'secrets\.[A-Z_]+', step)
        if found:
            holders[_name(step)] = env_of(step)
    expected = {V_STEP: {'QGV_OFFICIAL_HMAC_KEY': '${{ secrets.QGV_OFFICIAL_HMAC_KEY }}',
                         'RAW_REPO_READ_TOKEN': '${{ secrets.RAW_REPO_READ_TOKEN }}', 'QGV_MONTHEND_STAMP': "'20261023'"}}
    expected.update({name: {'SEC_USER_AGENT': '${{ secrets.SEC_USER_AGENT }}'} for name in SEC_STEPS})
    assert holders == expected
    for name in ('QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN'):
        assert code.count(f'secrets.{name} }}}}') == 1 and code.count(f"secrets.{name} != '' }}}}") == 1
    assert code.count('secrets.SEC_USER_AGENT }}') == len(SEC_STEPS) and code.count("secrets.SEC_USER_AGENT != '' }}") == 1
    # no Secret is ever interpolated into a script, and nothing prints an environment
    for step in (s for s in presence + steps if 'run:' in s):
        script = '\n'.join(run_lines(step))
        assert '${{' not in script, _name(step)
        assert not re.search(r'\b(?:printenv|set -x|declare -p|export -p)\b|\benv\s*(?:$|[|>;])', script, re.M), _name(step)


def test_the_v_step_is_the_production_step_byte_for_byte(wf):
    text, _, steps = wf
    production = named(steps_of(jobs_of(DAILY.read_text())['collect']), V_STEP)
    assert named(steps, V_STEP) == production
    code = _code(text)
    assert code.count('qgv_official_publish.py') == 1 and '--preserve-only' not in code
    assert code.count('steps.central_v.') == 1 and env_of(named(steps, AFTER_STEP)) == {'V_STEP_OUTCOME': '${{ steps.central_v.outcome }}'}


# ---- the collect job reproduced -----------------------------------------------------------------------------------------
def test_step_order_follows_the_collect_job_and_leaves_out_only_the_writing_and_key_steps(wf):
    _, _, steps = wf
    daily = steps_of(jobs_of(DAILY.read_text())['collect'])
    prod_names = [_name(s) or s.split('\n', 1)[0] for s in daily]
    names = [_name(s) or s.split('\n', 1)[0] for s in steps]
    expected = [START_STEP] + [n for n in prod_names if n not in LEFT_OUT]
    expected.insert(expected.index(V_STEP), BEFORE_STEP)
    expected.insert(expected.index(V_STEP) + 1, AFTER_STEP)
    expected.insert(expected.index(AFTER_STEP) + 1, CHECK_STEP)
    expected.append(VERDICT_STEP)
    assert names == expected
    assert set(prod_names) - set(names) == LEFT_OUT
    # the three `uses:` steps are the production ones
    for pin in PINS:
        assert next(s for s in steps if s.startswith(pin)) == next(s for s in daily if s.startswith(pin))


def _production_commands(name, step):
    lines = run_lines(step)
    if name == SEC_STEPS[0]:
        lines = [l.replace(' --macro-v0 --macro-evidence', '') for l in lines]
    if name == SEC_STEPS[1]:
        lines = [l.replace(' $ALL_SHARDS_FLAG', ' --all-shards') for l in lines]
    return lines


def test_stage_steps_run_the_production_commands_record_their_time_and_keep_their_exit_code(wf):
    _, _, steps = wf
    daily = steps_of(jobs_of(DAILY.read_text())['collect'])
    for name, (stage, required) in STAGES.items():
        prod, step = named(daily, name), named(steps, name)
        commands = _production_commands(name, prod)
        lines = run_lines(step)
        assert lines[0] == 's=$(date +%s); rc=0'
        assert lines[1] == (commands[0] + ' || rc=$?' if len(commands) == 1 else '{ ' + ' && '.join(commands) + '; } || rc=$?'), name
        kind = 'required' if required else 'optional'
        assert lines[2] == f'echo "{stage} $s $(date +%s) $rc {kind}" >> "$RUNNER_TEMP/rehearsal-metrics/stages.txt"'
        assert lines[3:] == ['exit "$rc"'] and len(lines) == 4
        # continue-on-error exactly where production has it; same working directory
        assert ('continue-on-error: true' in step) == ('continue-on-error: true' in prod) == (not required), name
        assert ('working-directory: implementation' in step) == ('working-directory: implementation' in prod)
        # env: production's minus the keys the rehearsal must not hold (raw-repo write token, macro keys, the all_shards input)
        env = env_of(prod)
        for key in ('RAW_REPO_TOKEN', 'BEA_USERID', 'CENSUS_API_KEY', 'ALL_SHARDS_FLAG'):
            env.pop(key, None)
        if 'RUN_MODE' in env:
            env['RUN_MODE'] = 'all_shards'
        assert env_of(step) == env, name
        if '--out "$RUNNER_TEMP/public-cockpit"' in lines[1]:            # every step that writes the artifact guards it
            assert lines[1].endswith(' && ' + GUARD + '; } || rc=$?'), name
    assert '--all-shards' in named(steps, SEC_STEPS[1]) and 'ALL_SHARDS_FLAG' not in _code(REHEARSAL.read_text())


def test_measurement_and_verdict_steps_hold_nothing_and_run_after_a_failure_but_not_on_cancel(wf):
    _, _, steps = wf
    for name in (AFTER_STEP, CHECK_STEP, VERDICT_STEP):
        assert '        if: ${{ !cancelled() }}\n' in named(steps, name)
    for name in (BEFORE_STEP, AFTER_STEP, CHECK_STEP):
        assert 'continue-on-error: true' in named(steps, name)
    for name in (START_STEP, BEFORE_STEP, AFTER_STEP, CHECK_STEP, VERDICT_STEP):
        step = named(steps, name)
        assert 'secrets.' not in step and 'uses:' not in step and '--out "$RUNNER_TEMP/public-cockpit"' not in step
    before = run_lines(named(steps, BEFORE_STEP))
    assert any(l.startswith('df -B1 --output=used,avail "$RUNNER_TEMP"') for l in before)
    assert any('du -sb "$RUNNER_TEMP/public-cockpit"' in l for l in before)
    assert any(l.startswith('nohup python implementation/tools/central_v_rehearsal_report.py sample ') and
               l.endswith('> /dev/null 2>&1 < /dev/null &') for l in before)
    assert before[-1] == 'echo "v_start=$(date +%s)" >> "$m/values.txt"'
    after = run_lines(named(steps, AFTER_STEP))
    assert after[1] == 'v_end=$(date +%s)' and 'echo "v_step ${v_start:-NONE} $v_end $v_rc optional" >> "$m/stages.txt"' in after
    assert after.index('echo "v_step ${v_start:-NONE} $v_end $v_rc optional" >> "$m/stages.txt"') < next(
        i for i, l in enumerate(after) if 'sampler.pid' in l)
    check = run_lines(named(steps, CHECK_STEP))
    assert GUARD + ' || grc=$?' in check
    assert 'python implementation/tools/qgv_official_check.py --artifact-dir "$RUNNER_TEMP/public-cockpit" || crc=$?' in check
    assert run_lines(named(steps, VERDICT_STEP)) == [
        'python implementation/tools/central_v_rehearsal_report.py report --metrics-dir "$RUNNER_TEMP/rehearsal-metrics" '
        '--artifact-dir "$RUNNER_TEMP/public-cockpit"']
    assert steps[-1].startswith('name: ' + VERDICT_STEP + '\n')


def test_the_yaml_parses_when_pyyaml_is_available():
    yaml = pytest.importorskip('yaml')
    doc = yaml.safe_load(REHEARSAL.read_text())
    assert doc[True] == {'push': {'branches': [BRANCH]}}                 # PyYAML reads the key `on` as True
    assert doc['permissions'] == {'contents': 'read'} and doc['concurrency']['group'] == 'central-v-rehearsal'
    assert [j['runs-on'] for j in doc['jobs'].values()] == ['ubuntu-24.04', 'ubuntu-24.04']
    steps = doc['jobs']['rehearsal']['steps']
    assert all(s.get('with', {}).get('persist-credentials') is False for s in steps if 'actions/checkout@' in s.get('uses', ''))
    daily = yaml.safe_load(DAILY.read_text())
    prod_v = next(s for s in daily['jobs']['collect']['steps'] if s.get('id') == 'central_v')
    assert next(s for s in steps if s.get('id') == 'central_v') == prod_v


# ---- the presence job, run locally ---------------------------------------------------------------------------------------
def _presence(tmp_path, *, hmac='true', token='true', agent='true', hm='12:00'):
    step = steps_of(jobs_of(REHEARSAL.read_text())['presence'])[0]
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / 'date').write_text('#!/bin/sh\necho "$FAKE_HM"\n')                # the clock of the window check only
    (bin_dir / 'date').chmod(0o755)
    out = tmp_path / 'github_output'
    out.write_text('')
    env = {'PATH': f'{bin_dir}:/usr/bin:/bin', 'GITHUB_OUTPUT': str(out), 'FAKE_HM': hm, 'QGV_OFFICIAL_HMAC_KEY_SET': hmac,
           'RAW_REPO_READ_TOKEN_SET': token, 'SEC_USER_AGENT_SET': agent}
    run = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', '\n'.join(run_lines(step)) + '\n'],
                         env=env, capture_output=True, text=True, timeout=60)
    return run, out.read_text()


def test_presence_prints_names_and_yes_no_only_and_lets_the_rehearsal_run(tmp_path):
    run, output = _presence(tmp_path)
    assert (run.returncode, run.stderr) == (0, '')
    assert run.stdout.splitlines() == ['SECRET_PRESENT name=QGV_OFFICIAL_HMAC_KEY present=yes',
                                       'SECRET_PRESENT name=RAW_REPO_READ_TOKEN present=yes',
                                       'SECRET_PRESENT name=SEC_USER_AGENT present=yes',
                                       'REHEARSAL_WINDOW start_utc=12:00 allowed_utc=03:00-19:30 verdict=OK']
    assert output == 'ready=true\n'


@pytest.mark.parametrize('missing', ['hmac', 'token', 'agent'])
def test_a_missing_secret_ends_the_run_before_anything_is_collected(tmp_path, missing):
    run, output = _presence(tmp_path, **{missing: 'false'})
    name = {'hmac': 'QGV_OFFICIAL_HMAC_KEY', 'token': 'RAW_REPO_READ_TOKEN', 'agent': 'SEC_USER_AGENT'}[missing]
    assert run.returncode == 1 and output == 'ready=false\n'
    assert f'SECRET_PRESENT name={name} present=no' in run.stdout.splitlines()
    assert run.stdout.splitlines()[-1] == 'REHEARSAL_VERDICT overall=FAIL reason=NOT_READY collected=NONE downloaded=NONE'


@pytest.mark.parametrize('hm,ok', [('02:59', False), ('03:00', True), ('09:05', True), ('19:29', True), ('19:30', False),
                                   ('22:17', False), ('00:40', False)])
def test_the_start_window_keeps_away_from_the_daily_run(tmp_path, hm, ok):
    run, output = _presence(tmp_path, hm=hm)
    assert (run.returncode == 0) is ok and output == f'ready={str(ok).lower()}\n'
    assert f'REHEARSAL_WINDOW start_utc={hm} allowed_utc=03:00-19:30 verdict={"OK" if ok else "REFUSED"}' in run.stdout


# ---- the measurement, check and verdict steps, run locally ---------------------------------------------------------------
def _runner(tmp_path):
    runner = tmp_path / 'runner'
    runner.mkdir()
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'python').symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(PATH=f'{bin_dir}:{env.get("PATH", "/usr/bin:/bin")}', RUNNER_TEMP=str(runner), HTTPS_PROXY='http://127.0.0.1:9',
               HTTP_PROXY='http://127.0.0.1:9', NO_PROXY='', no_proxy='')
    env.pop('PYTHONPATH', None)
    return runner, env


def _step(name, env, extra=None, cwd=REPO):
    steps = steps_of(jobs_of(REHEARSAL.read_text())['rehearsal'])
    step = named(steps, name)
    if 'working-directory: implementation' in step:
        cwd = ROOT
    return subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', '\n'.join(run_lines(step)) + '\n'], cwd=cwd,
                          env=dict(env, **(extra or {})), capture_output=True, text=True, timeout=300)


def _publish(out, *, fail=None):
    def fetch_day(keys, basis, parser=None, workdir=None):
        if fail:
            raise iex_hist.IexHistError(fail)
        return synthetic_day(base_payload(), canary_key='NYSE:ABT')
    parser = out.parent / 'iex_last_trade'
    parser.write_text('')
    return publisher.run(out=out, parser=str(parser), monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t',
                         hmac_key=KEY, now=NOW, workdir=out.parent / 'qgv-official', fetch_day=fetch_day,
                         read_store=lambda s, n: {}, clock=lambda: NOW + dt.timedelta(minutes=5))


def _sampler_gone(pid, wait=10.0):
    """True once the sampler process has ended (gone, or a zombie nobody reaped)."""
    import time
    end = time.monotonic() + wait
    while time.monotonic() < end:
        try:
            state = next(l for l in Path(f'/proc/{pid}/status').read_text().splitlines() if l.startswith('State:'))
        except (OSError, StopIteration):
            return True
        if 'Z' in state.split()[1]:
            return True
        time.sleep(0.1)
    return False


def _first_sample(path, wait=10.0):
    import time
    end = time.monotonic() + wait
    while time.monotonic() < end and not (path.is_file() and path.read_text().strip()):
        time.sleep(0.05)
    assert path.read_text().strip()


def _rehearse(tmp_path, *, fail=None, v_outcome='success'):
    """The rehearsal's own steps around a synthetic V attempt: start, two real stage steps (cockpit build, coverage), measure
    before (the sampler starts), the publisher on synthetic data (the V step's work), measure after, check, verdict."""
    runner, env = _runner(tmp_path)
    pid_file = runner / 'rehearsal-metrics' / 'sampler.pid'
    try:
        for name in (START_STEP, 'Build and inspect local price-free cockpit'):
            run = _step(name, env)
            assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
        out = runner / 'public-cockpit'
        (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(base_payload()))
        run = _step(BEFORE_STEP, env)
        assert run.returncode == 0 and run.stdout == '', run.stderr
        _first_sample(runner / 'rehearsal-metrics' / 'samples.txt')      # on Actions the V step lasts minutes
        summary = _publish(out, fail=fail)
        run = _step(AFTER_STEP, env, {'V_STEP_OUTCOME': v_outcome})
        assert run.returncode == 0 and run.stdout == '', run.stderr
        assert _sampler_gone(int(pid_file.read_text()))
        run = _step(CHECK_STEP, env)
        assert run.returncode == 0
        assert _step('Report published Q·G coverage of the final artifact (counts only)', env).returncode == 0
        verdict = _step(VERDICT_STEP, env)
    finally:
        if pid_file.is_file():
            subprocess.run(['kill', pid_file.read_text().strip()], capture_output=True)
    return runner, summary, verdict


def _criteria(stdout):
    return {m.group(1): m.group(2) for m in re.finditer(r'^REHEARSAL_CRITERION name=(\S+) .* verdict=(PASS|FAIL)', stdout, re.M)}


@pytest.mark.skipif(not shutil.which('node'), reason='the JS twin needs node')
def test_a_good_attempt_passes_every_criterion_and_prints_counts_only(tmp_path):
    runner, summary, verdict = _rehearse(tmp_path)
    assert (summary['attempt'], summary['published']) == ('OK', 'NEW')
    assert verdict.returncode == 0, verdict.stdout
    lines = verdict.stdout.splitlines()
    assert lines[0].startswith('REHEARSAL_SCOPE publication=NONE raw_repo_write=NONE ledger=NONE history=NONE ')
    stages = [l.split()[1] for l in lines if l.startswith('REHEARSAL_STAGE ')]
    assert stages == ['stage=cockpit_build', 'stage=v_step', 'stage=v_files_check', 'stage=published_coverage']
    assert _criteria(verdict.stdout) == {name: 'PASS' for name in (
        'v_step_time', 'job_time', 'required_steps', 'inputs_calc_version', 'stream_disk_peak', 'universe_last_trade', 'supply',
        'validator', 'js_twin', 'guard', 'attempt_ok')}
    assert lines[-1] == 'REHEARSAL_VERDICT overall=PASS passed=11/11 failed=-'
    v = next(l for l in lines if l.startswith('REHEARSAL_V '))
    assert v.startswith('REHEARSAL_V attempt=OK reason=- published=NEW basis=2026-10-13 requested_basis=2026-10-13 rows=')
    price = next(l for l in lines if l.startswith('REHEARSAL_PRICE '))
    assert ' universe_rows=504 universe_code_count=504 ' in price and ' consistent=YES' in price
    inputs = next(l for l in lines if l.startswith('REHEARSAL_INPUTS '))
    assert ' calc_version=qgv2-calc/2026-10-23.1 records=504 ' in inputs and inputs.endswith(' same_bytes_as_attempt=YES')
    disk = next(l for l in lines if l.startswith('REHEARSAL_DISK '))
    assert re.search(r' samples=[1-9]\d* ', disk) and ' fs_used_before=- ' not in disk
    # the sampler is stopped by the after step, and nothing printed carries a price, a URL or a code list
    assert str(CANARY) not in verdict.stdout and str(CANARY)[:6] not in verdict.stdout
    assert 'http' not in verdict.stdout and 'NYSE:' not in verdict.stdout and 'NASDAQ:' not in verdict.stdout


def test_a_supply_failure_is_reported_as_fail_with_its_reason(tmp_path):
    _, summary, verdict = _rehearse(tmp_path, fail='DOWNLOAD_FAILED')
    assert summary['reason'] == 'IEX_DOWNLOAD_FAILED'
    assert verdict.returncode == 1
    crit = _criteria(verdict.stdout)
    assert crit['attempt_ok'] == crit['validator'] == crit['js_twin'] == crit['universe_last_trade'] == crit['supply'] == 'FAIL'
    assert crit['v_step_time'] == crit['stream_disk_peak'] == crit['guard'] == crit['inputs_calc_version'] == 'PASS'
    assert 'REHEARSAL_CRITERION name=attempt_ok value=NO_OFFICIAL_YET limit=OK verdict=FAIL reason=IEX_DOWNLOAD_FAILED' in verdict.stdout
    assert 'REHEARSAL_CRITERION name=validator value=ABSENT/VALID limit=VALID/VALID verdict=FAIL reason=NOT_MEASURED' in verdict.stdout
    assert 'REHEARSAL_PRICE state=NO_PUBLICATION' in verdict.stdout
    assert verdict.stdout.splitlines()[-1].startswith('REHEARSAL_VERDICT overall=FAIL ')


@pytest.mark.skipif(not shutil.which('node'), reason='the JS twin needs node')
def test_a_v_step_whose_guard_refused_is_a_guard_fail(tmp_path):
    _, _, verdict = _rehearse(tmp_path, v_outcome='failure')
    crit = _criteria(verdict.stdout)
    assert verdict.returncode == 1 and crit['guard'] == 'FAIL' and crit['attempt_ok'] == 'PASS'
    assert 'REHEARSAL_STAGE stage=v_step seconds=' in verdict.stdout and ' outcome=failure' in verdict.stdout


def test_a_failing_stage_step_records_its_exit_code_and_still_fails(tmp_path):
    runner, env = _runner(tmp_path)
    assert _step(START_STEP, env).returncode == 0
    shim = tmp_path / 'bin' / 'python'
    shim.unlink()
    shim.write_text(f'#!/bin/sh\ncase "$1" in *sec_13f_managers.py) exit 3;; esac\nexec "{sys.executable}" "$@"\n')
    shim.chmod(0o755)
    run = _step('Verify 13F manager CIKs and project reported quantity changes', env)
    assert run.returncode == 3
    line = (runner / 'rehearsal-metrics' / 'stages.txt').read_text().split()
    assert line[0] == 'thirteen_f' and line[3:] == ['3', 'required'] and int(line[2]) >= int(line[1])


# ---- the verdict tool on recorded numbers --------------------------------------------------------------------------------
def _metrics(tmp_path, values, stages=(), samples=()):
    m = tmp_path / 'metrics'
    m.mkdir()
    (m / 'values.txt').write_text(''.join(f'{k}={v}\n' for k, v in values.items()))
    (m / 'stages.txt').write_text(''.join(s + '\n' for s in stages))
    (m / 'samples.txt').write_text(''.join(s + '\n' for s in samples))
    art = tmp_path / 'artifact'
    art.mkdir()
    return m, art


def test_nothing_recorded_is_not_measured_and_fails(tmp_path, capsys):
    m, art = _metrics(tmp_path, {})
    assert report_tool.main(['report', '--metrics-dir', str(m), '--artifact-dir', str(art), '--now', '1000']) == 1
    out = capsys.readouterr().out
    crit = _criteria(out)
    assert set(crit.values()) == {'FAIL'} and len(crit) == 11
    assert out.count('reason=NOT_MEASURED') == 11
    assert out.splitlines()[-1] == ('REHEARSAL_VERDICT overall=FAIL passed=0/11 failed=v_step_time,job_time,required_steps,'
                                    'inputs_calc_version,stream_disk_peak,universe_last_trade,supply,validator,js_twin,guard,attempt_ok')
    assert report_tool.main(['report', '--metrics-dir', str(m), '--artifact-dir', str(tmp_path / 'missing')]) == 2


def test_limits_time_disk_and_job_allowance(tmp_path, capsys):
    values = {'job_start': 0, 'v_start': 100, 'v_end': 100 + 721, 'df_before_used': 5 * 10 ** 9, 'df_after_used': 5 * 10 ** 9}
    stages = ['offline_regression 1 50 0 required', 'universe_all_shards 60 99 0 required', 'news 900 950 1 optional']
    samples = [f'{100 + i} {5 * 10 ** 9 + (10 ** 10 + 1 if i == 3 else 0)} {2 ** 30}' for i in range(5)]
    m, art = _metrics(tmp_path, values, stages, samples)
    report_tool.main(['report', '--metrics-dir', str(m), '--artifact-dir', str(art), '--now', str(7200 - 600)])
    out = capsys.readouterr().out
    assert 'REHEARSAL_CRITERION name=v_step_time value=721s limit=720s verdict=FAIL' in out
    assert 'REHEARSAL_CRITERION name=job_time value=7200s limit=7200s verdict=PASS' in out          # 6600 s + 600 s allowance
    assert f'REHEARSAL_CRITERION name=stream_disk_peak value={10 ** 10 + 1}B limit={10 ** 10}B verdict=FAIL' in out
    assert 'REHEARSAL_CRITERION name=required_steps value=2/2 limit=all verdict=PASS' in out        # an optional step may fail
    assert 'REHEARSAL_STAGE stage=news seconds=50 rc=1 kind=optional' in out
    assert f'mem_available_min={2 ** 30}' in out and 'samples=5' in out
    report_tool.main(['report', '--metrics-dir', str(m), '--artifact-dir', str(art), '--now', str(7200 - 599)])
    assert 'REHEARSAL_CRITERION name=job_time value=7201s limit=7200s verdict=FAIL' in capsys.readouterr().out


def test_the_last_trade_threshold_and_the_status_sets():
    assert report_tool.last_trade_needed(504) == 479 and report_tool.last_trade_needed(500) == 475
    assert set(report_tool.MISSING_TRADE) | set(report_tool.RULE_EXCLUDED) | {report_tool.SUPPLIED} == set(iex_hist.STATUS_CODES)
    assert not set(report_tool.MISSING_TRADE) & set(report_tool.RULE_EXCLUDED)
    assert report_tool.STREAM_DISK_LIMIT_BYTES == 10 ** 10 and report_tool.V_STEP_LIMIT_SECONDS == 720
    assert report_tool.JOB_LIMIT_SECONDS == 7200 and report_tool.EXCLUDED_STEPS_ALLOWANCE_SECONDS == 600
    # the limits are the ones the workflows and the probe record
    daily = DAILY.read_text()
    assert 'timeout -k 30s 12m python implementation/tools/qgv_official_publish.py' in daily
    assert "inputs.all_shards && 120 || 40" in daily
    facts = (ROOT / 'docs/qgv_scoring_standard/CENTRAL_V_PROBE_U8_FACTS_20261024.md').read_text()
    assert '한도(45분·디스크 10 GB·결측 5%)' in facts


def test_the_sampler_writes_numbers_only(tmp_path):
    out = tmp_path / 'samples.txt'
    assert report_tool.sample(str(tmp_path), str(out), 0.1, count=3, sleep=lambda _: None) == 0
    rows = [l.split() for l in out.read_text().splitlines()]
    assert len(rows) == 3 and all(len(r) == 3 and all(re.fullmatch(r'-?\d+', x) for x in r) for r in rows)
    assert report_tool.read_samples(out) and int(rows[0][1]) > 0


def test_the_tool_never_touches_a_price_route_a_secret_or_the_network():
    src = (ROOT / 'tools/central_v_rehearsal_report.py').read_text()
    assert not re.search(r'\biex_(?:hist|monthend)\b|iextrading|googleapis|urllib|socket|subprocess', src)
    for name in ('QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN', 'RAW_REPO_TOKEN', 'SEC_USER_AGENT', 'GITHUB_STEP_SUMMARY', 'environ['):
        assert name not in src, name


def test_the_doc_states_what_runs_what_never_happens_the_criteria_and_how_it_starts():
    doc = DOC.read_text()
    for phrase in ('central-v-rehearsal.yml', BRANCH, 'push', 'RAW_UPLOAD_NOT_CONFIGURED', 'REHEARSAL_VERDICT', 'REHEARSAL_CRITERION',
                   'v_step_time', 'job_time', 'stream_disk_peak', 'universe_last_trade', 'supply', 'validator', 'js_twin', 'guard',
                   'attempt_ok', 'required_steps', 'inputs_calc_version', '479/504', '03:00', '19:30', 'SECRET_PRESENT'):
        assert phrase in doc, phrase
    assert not re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', doc)
