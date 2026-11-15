"""Central V publication workflow wiring (PR-C, GSQ-024; design CENTRAL_V_PUBLICATION_DESIGN_20261018.md §3, §6; plan
CENTRAL_V_DC02_PLAN_20261024.md section 2 PR-C, owner decisions D2/D9/D10 of 2026-10-24).

- sec-daily-public-inputs.yml collect: pinned setup-node early (D10); the V step after the ledger and before the classification
  step (continue-on-error, own time limit, the two new Secrets in its env only, C parser built into $RUNNER_TEMP, the artifact
  guard last); the private dated history step (D9) right after it, holding only the raw-repo write token;
- verify: the price-free check of the published files (tools/qgv_official_check.py) and the unit tests, continue-on-error;
- deploy comments of both workflows state the publication rule; cockpit-pages.yml preserves the live publication;
- the V step's own shell is run locally (missing Secrets -> NOT_RUN, supply failure -> last good kept, a stopped publisher ->
  the job goes on), and the two new tools (check, history) are tested on the publisher's real output.

Plain-text workflow reads (CI has no YAML parser). Synthetic publications only (tests/test_qgv_official.py builders), an
in-memory private release store, no network.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from investment_system.qgv import qgv_official as qo
from investment_system.universe import sec_qgv2
from tests.test_forward_validation_ledger import RawStore
from tests.test_public_price_boundary import prohibit_network  # noqa: F401  (autouse: every test here is offline)
from tests.test_qgv_official import CANARY, KEY, NOW, base_payload, synthetic_day, tool as publisher
from investment_system.providers import iex_hist

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DAILY = REPO / '.github/workflows/sec-daily-public-inputs.yml'
PAGES = REPO / '.github/workflows/cockpit-pages.yml'
V_STEP = 'Publish the central QGV from one IEX HIST day (prices in RAM only; scores, ranks, reasons and counts only)'
HISTORY_STEP = 'Copy a new central QGV publication to the private dated history (scores only, no prices)'
VERIFY_STEP = 'Check the central QGV publication without prices (strict reader, status, unit tests)'
NODE_PIN = 'uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4'
GUARD_LINE = 'python implementation/tools/pages_artifact_guard.py --artifact-dir "$RUNNER_TEMP/public-cockpit"'
NO_SECRETS = 'env -u QGV_OFFICIAL_HMAC_KEY -u RAW_REPO_READ_TOKEN '
V_GUARD_LINES = [NO_SECRETS + GUARD_LINE + " || { echo 'QGV_OFFICIAL_GUARD_REFUSED'; "
                 'rm -f "$RUNNER_TEMP/public-cockpit/qgv-official.json" "$RUNNER_TEMP/public-cockpit/qgv-official-status.json"; '
                 'refused=1; }',
                 '[ -z "${refused:-}" ] && ' + NO_SECRETS + GUARD_LINE]


def _load(name):
    spec = importlib.util.spec_from_file_location('qgv_workflow_' + name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_tool, history_tool = _load('qgv_official_check'), _load('qgv_official_history')


# ---- plain-text workflow reads ------------------------------------------------------------------------------------------
def jobs_of(text):
    body, jobs, name = text.split('\njobs:\n', 1)[1], {}, None
    for line in body.splitlines():
        m = re.match(r'^  ([a-z_]+):$', line)
        if m:
            name = m.group(1)
            jobs[name] = []
        elif name is not None:
            jobs[name].append(line)
    return {k: '\n'.join(v) for k, v in jobs.items()}


def steps_of(job):
    """Steps in file order, each starting after its '- ', comment lines dropped."""
    chunks = ('\n' + job.split('\n    steps:\n', 1)[1]).split('\n      - ')[1:]
    return ['\n'.join(l for l in c.splitlines() if not l.lstrip().startswith('#')).rstrip() for c in chunks]


def named(steps, name):
    found = [s for s in steps if s.startswith('name: ' + name + '\n')]
    assert len(found) == 1, name
    return found[0]


def env_of(step):
    block = step.split('\n        env:\n', 1)[1] if '\n        env:\n' in step else ''
    return dict(re.findall(r'^          ([A-Z_]+): (.+)$', block.split('\n        run:', 1)[0], re.M))


def run_lines(step):
    if '\n        run: |\n' in step:
        return [l.strip() for l in step.split('\n        run: |\n', 1)[1].splitlines() if l.strip()]
    return [step.split('\n        run: ', 1)[1].strip()]


@pytest.fixture(scope='module')
def daily():
    text = DAILY.read_text()
    return text, jobs_of(text)


# ---- collect: setup-node (D10) -----------------------------------------------------------------------------------------
def test_collect_pins_the_same_node_as_verify_early_and_never_fails_on_it(daily):
    text, jobs = daily
    collect, verify = steps_of(jobs['collect']), steps_of(jobs['verify'])
    node = [i for i, s in enumerate(collect) if s.startswith(NODE_PIN)]
    assert len(node) == 1 and [s for s in verify if s.startswith(NODE_PIN)]
    step = collect[node[0]]
    assert "node-version: '22'" in step and 'continue-on-error: true' in step
    names = [s.split('\n', 1)[0] for s in collect]
    assert names[node[0] - 1] == 'name: Record run context (event, mode, start time, observation day, shard)'
    assert node[0] < names.index('name: Offline public boundary regression (GSQ-010)') < names.index('name: ' + V_STEP)
    assert text.count('actions/setup-node@') == 2


# ---- collect: the V step ------------------------------------------------------------------------------------------------
def test_the_v_step_sits_after_the_ledger_and_before_classification(daily):
    _, jobs = daily
    names = [s.split('\n', 1)[0] for s in steps_of(jobs['collect'])]
    ledger = names.index('name: Append forward validation ledger (price-free, append-only)')
    assert names[ledger + 1] == 'name: ' + V_STEP and names[ledger + 2] == 'name: ' + HISTORY_STEP
    assert names[ledger + 3].startswith('name: Collect SEC SIC, 10-K Item 1')
    assert names[-1] == 'name: Upload checked public SEC Pages artifact'


def test_the_v_step_holds_its_two_secrets_only_continues_on_error_and_ends_with_the_guard(daily):
    text, jobs = daily
    step = named(steps_of(jobs['collect']), V_STEP)
    assert '        continue-on-error: true\n' in step and '        timeout-minutes: 15\n' in step
    assert step.split('\n')[1] == '        id: central_v' and text.count('steps.central_v.') == 1
    assert env_of(step) == {'QGV_OFFICIAL_HMAC_KEY': '${{ secrets.QGV_OFFICIAL_HMAC_KEY }}',
                            'RAW_REPO_READ_TOKEN': '${{ secrets.RAW_REPO_READ_TOKEN }}', 'QGV_MONTHEND_STAMP': "'20261023'"}
    lines = run_lines(step)
    # Only the publisher holds the two Secrets: cc and the guard run without them (the publisher pops them before its children).
    assert lines[0] == (NO_SECRETS + 'cc -O2 -o "$RUNNER_TEMP/iex_last_trade" implementation/tools/iex_tops/iex_last_trade.c '
                        "|| echo 'QGV_OFFICIAL_PARSER_BUILD_FAILED'")
    assert lines[1] == ('timeout -k 30s 12m python implementation/tools/qgv_official_publish.py --out "$RUNNER_TEMP/public-cockpit" '
                        '--parser "$RUNNER_TEMP/iex_last_trade" --monthend-stamp "$QGV_MONTHEND_STAMP" --monthend-shards 6 '
                        '--raw-token-env RAW_REPO_READ_TOKEN --hmac-key-env QGV_OFFICIAL_HMAC_KEY '
                        '|| { echo "QGV_OFFICIAL_STEP_STOPPED exit=$?"; rm -f "$RUNNER_TEMP"/public-cockpit/.qgv-official*; }')
    # A guard refusal stays inside the step: the V files go and the step fails (history skipped); otherwise the step ends with
    # the artifact guard like every step that writes the artifact (test_public_price_boundary sink test).
    assert lines[2:] == V_GUARD_LINES and step.endswith(GUARD_LINE)
    # One source each: the Secrets appear in this step only; the parser file and the month-end stamp are the recorded ones.
    for secret in ('secrets.QGV_OFFICIAL_HMAC_KEY', 'secrets.RAW_REPO_READ_TOKEN'):
        assert text.count(secret) == 1
    assert 'RAW_REPO_TOKEN' not in step.replace('RAW_REPO_READ_TOKEN', '') and 'uses:' not in step
    assert (ROOT / 'tools/iex_tops/iex_last_trade.c').is_file()
    facts = (ROOT / 'docs/qgv_scoring_standard/CENTRAL_V_PROBE_U8_FACTS_20261024.md').read_text()
    assert 'iex-v4-monthend-20261023-shard0..5' in facts and '`--monthend-stamp 20261023`, 샤드 수 6' in facts
    assert publisher.DEFAULT_RAW_TOKEN_ENV == 'RAW_REPO_READ_TOKEN' and publisher.DEFAULT_HMAC_ENV == 'QGV_OFFICIAL_HMAC_KEY'


def test_the_history_step_holds_only_the_raw_repo_write_token(daily):
    _, jobs = daily
    step = named(steps_of(jobs['collect']), HISTORY_STEP)
    assert '        continue-on-error: true\n' in step and '        timeout-minutes: 5\n' in step   # a stall ends this step only
    # Only after a V step that succeeded as a whole (publisher and its artifact guard): a file the guard refused is never copied.
    assert "        if: steps.central_v.outcome == 'success'\n" in step
    assert env_of(step) == {'RAW_REPO_TOKEN': '${{ secrets.RAW_REPO_TOKEN }}'}
    assert run_lines(step) == ['python implementation/tools/qgv_official_history.py --artifact-dir "$RUNNER_TEMP/public-cockpit"']
    assert '--out' not in step and 'uses:' not in step


def test_verify_checks_the_published_files_and_runs_the_unit_tests_without_secrets(daily):
    _, jobs = daily
    steps = steps_of(jobs['verify'])
    names = [s.split('\n', 1)[0] for s in steps]
    step = named(steps, VERIFY_STEP)
    assert names.index('name: Unpack and re-inspect the artifact deploy would publish') < names.index('name: ' + VERIFY_STEP) \
        < names.index('name: Verify device features and price-free pages locally')
    assert [s for s in steps[:names.index('name: ' + VERIFY_STEP)] if s.startswith(NODE_PIN)]   # node before the JS twin test
    assert '        continue-on-error: true\n' in step and 'secrets.' not in jobs['verify'] and 'env:' not in step
    assert '        timeout-minutes: 8\n' in step                    # a hang ends this step only, never the verify job
    lines = run_lines(step)
    assert 'python implementation/tools/qgv_official_check.py --artifact-dir "$RUNNER_TEMP/public-cockpit" || rc=1' in lines
    tests = next(l for l in lines if 'pytest' in l)
    for name in ('tests/test_qgv_official.py', 'tests/test_iex_hist.py', 'tests/test_qgv_official_guards.py'):
        assert name in tests
    assert lines[-1] == 'exit "$rc"' and any('QGV_OFFICIAL_VERIFY_FAILED' in l for l in lines)


@pytest.mark.parametrize('workflow', [DAILY, PAGES])
def test_deploy_comments_state_the_publication_rule(workflow):
    deploy = workflow.read_text().split('\n  deploy:\n', 1)[1]
    comment = ' '.join(l.strip().lstrip('# ') for l in deploy.splitlines() if l.strip().startswith('#'))
    for phrase in ('qgv-official.json', 'same publication_id must carry the same bytes', 'CHANGED, refused',
                   'earlier price_basis_date', 'earlier inputs_as_of, is OLDER (refused)', 'failing the strict reader is refused',
                   'withholds the publication only (PAGES_FRESHNESS_PUBLICATION_WITHHELD', 'D-CV16 (a)',
                   'qgv-official-status.json is never compared'):
        assert phrase in comment, phrase


def test_the_manual_deploy_preserves_the_live_publication_once():
    text = PAGES.read_text()
    line = 'python implementation/tools/qgv_official_publish.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"'
    start = text.index('- name: Preserve previously published validated SEC observations for UI deployment')
    step = text[start:text.index('\n      - ', start + 10)]
    assert text.count('qgv_official_publish.py') == 1 and line in step
    assert step.index('macro_evidence.py --preserve-only') < step.index(line) < step.index('pages_artifact_guard.py')
    assert "if: github.event_name == 'workflow_dispatch' && !inputs.replay_20261020" in step
    assert 'QGV_OFFICIAL_HMAC_KEY' not in text and 'RAW_REPO_READ_TOKEN' not in text


# ---- the V step's own shell, run locally ---------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp('cockpit') / 'site'
    _load('build_pages_cockpit').build_public_cockpit(out)
    (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(base_payload()))
    return out


LIVE_404 = """import io, urllib.error, urllib.request
_open = urllib.request.OpenerDirector.open
def open(self, fullurl, *args, **kwargs):
    url = getattr(fullurl, 'full_url', fullurl)
    if isinstance(url, str) and url.startswith('https://kco994553-star.github.io/'):
        raise urllib.error.HTTPError(url, 404, 'Not Found', {}, io.BytesIO(b''))
    return _open(self, fullurl, *args, **kwargs)
urllib.request.OpenerDirector.open = open
"""


def _runner(tmp_path, built_site, *, secrets, shim=None, live='404'):
    """$RUNNER_TEMP with the built price-free site plus this run's sec-qgv2.json, a `python` on PATH and a proxy on a closed
    local port (every source request fails at once; nothing leaves the machine). live='404': the live Pages copy answers 404
    as before the first publication (a test-only sitecustomize on PYTHONPATH); live='closed': the live read fails like the
    rest (LIVE_UNREACHABLE)."""
    runner = tmp_path / 'runner'
    shutil.copytree(built_site, runner / 'public-cockpit')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    real = bin_dir / 'python-real'
    real.symlink_to(sys.executable)
    (bin_dir / 'python').write_text(shim or f'#!/bin/sh\nexec "{real}" "$@"\n')
    (bin_dir / 'python').chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(PATH=f'{bin_dir}:{env.get("PATH", "/usr/bin:/bin")}', RUNNER_TEMP=str(runner), HTTPS_PROXY='http://127.0.0.1:9',
               HTTP_PROXY='http://127.0.0.1:9', NO_PROXY='', no_proxy='', QGV_MONTHEND_STAMP='20261023',
               QGV_OFFICIAL_HMAC_KEY=secrets.get('hmac', ''), RAW_REPO_READ_TOKEN=secrets.get('token', ''))
    env.pop('PYTHONPATH', None)
    if live == '404':
        site = tmp_path / 'live404'
        site.mkdir()
        (site / 'sitecustomize.py').write_text(LIVE_404)
        env['PYTHONPATH'] = str(site)
    return runner, env


def _run_step(name, env):
    """The step's `run: |` block exactly as GitHub runs it (bash -e -o pipefail), from the repository root."""
    step = named(steps_of(jobs_of(DAILY.read_text())['collect']), name)
    script = '\n'.join(run_lines(step)) + '\n'
    return subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', script], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=600)


def _receipt(stdout):
    return json.loads(next(l for l in stdout.splitlines() if l.startswith('{')))


@pytest.mark.skipif(not shutil.which('cc'), reason='no C compiler')
def test_the_v_step_without_secrets_is_not_run_and_the_job_goes_on(tmp_path, built_site):
    runner, env = _runner(tmp_path, built_site, secrets={})
    run = _run_step(V_STEP, env)
    assert run.returncode == 0, run.stdout[-2000:]
    lines = run.stdout.splitlines()
    assert lines[0] == 'QGV_OFFICIAL attempt=NO_OFFICIAL_YET reason=HMAC_KEY_MISSING published=NONE basis=- rows=0 ranked=0 supplied=-'
    assert _receipt(run.stdout)['pages_artifact_guard'] == 'PASS'
    assert (runner / 'iex_last_trade').is_file()                        # the parser is built outside the artifact
    out = runner / 'public-cockpit'
    assert not (out / qo.FILENAME).exists() and not list(out.glob('.qgv-official*'))
    status = json.loads((out / qo.STATUS_FILENAME).read_bytes())
    qo.require_status(status)
    assert (status['attempt_state'], status['reason_code'], status['official_publication_id']) == ('NO_OFFICIAL_YET', 'HMAC_KEY_MISSING', None)
    # The read token alone is not enough either (HMAC key first), and the key alone stops at the missing token.
    runner2, env2 = _runner(tmp_path / 'b', built_site, secrets={'hmac': 'synthetic-test-key-0123456789'})
    run = _run_step(V_STEP, env2)
    assert run.returncode == 0 and run.stdout.splitlines()[0].startswith('QGV_OFFICIAL attempt=NO_OFFICIAL_YET reason=MONTHEND_TOKEN_MISSING ')
    # The history step after it skips; the verify-job check accepts the files.
    history = _run_step(HISTORY_STEP, dict(env, RAW_REPO_TOKEN=''))
    assert (history.returncode, history.stdout) == (0, 'QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION\n')
    result = check_tool.inspect(out)
    assert check_tool.ok(result) and check_tool.line(result) == (
        'QGV_OFFICIAL_CHECK publication=ABSENT status=VALID consistent=YES new=NO attempt=NO_OFFICIAL_YET '
        'reason=HMAC_KEY_MISSING basis=- rows=0 ranked=0')


@pytest.mark.skipif(not shutil.which('cc'), reason='no C compiler')
def test_the_v_step_with_secrets_and_no_source_is_supply_failed_and_green(tmp_path, built_site):
    # cc and the artifact guard record the names in their environment: neither may see the two Secrets (review 2026-10-24)
    shim = ('#!/bin/sh\ncase "$1" in *pages_artifact_guard.py) env | cut -d= -f1 >> "$RUNNER_TEMP/guard-env.txt";; esac\n'
            f'exec "{tmp_path / "bin" / "python-real"}" "$@"\n')
    runner, env = _runner(tmp_path, built_site, secrets={'hmac': 'synthetic-test-key-0123456789', 'token': 'synthetic-token'},
                          shim=shim)
    (tmp_path / 'ccwrap').mkdir()
    (tmp_path / 'ccwrap' / 'cc').write_text(f'#!/bin/sh\nenv | cut -d= -f1 > "$RUNNER_TEMP/cc-env.txt"\nexec "{shutil.which("cc")}" "$@"\n')
    (tmp_path / 'ccwrap' / 'cc').chmod(0o755)
    env['PATH'] = f'{tmp_path / "ccwrap"}:{env["PATH"]}'
    run = _run_step(V_STEP, env)
    for name in ('cc-env.txt', 'guard-env.txt'):
        keys = set((runner / name).read_text().split())
        assert 'PATH' in keys and not {'QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN'} & keys, name
    assert run.returncode == 0, run.stdout[-2000:]
    first = run.stdout.splitlines()[0]
    assert first.startswith('QGV_OFFICIAL attempt=NO_OFFICIAL_YET reason=IEX_') and ' published=NONE ' in first
    assert 'ROUTE_NOT_ALLOWED' not in first                              # the real entry script is the approved route
    assert _receipt(run.stdout)['pages_artifact_guard'] == 'PASS'
    for secret in ('synthetic-test-key-0123456789', 'synthetic-token'):
        assert secret not in run.stdout + run.stderr
        assert all(secret not in p.read_text(errors='replace') for p in (runner / 'public-cockpit').iterdir() if p.is_file())


def test_a_stopped_publisher_leaves_no_partial_file_and_the_job_goes_on(tmp_path, built_site):
    """A publisher stopped by the step's own time limit (exit 124) mid-write: the fixed line, the partial file removed, the
    guard passes, the step exits 0 (no cc needed: the parser build failure is a fixed line too)."""
    shim = ('#!/bin/sh\ncase "$1" in *qgv_official_publish.py) '
            ': > "$RUNNER_TEMP/public-cockpit/.qgv-official.json.partial"; exit 124;; esac\n'
            f'exec "{tmp_path / "bin" / "python-real"}" "$@"\n')
    runner, env = _runner(tmp_path, built_site, secrets={}, shim=shim)
    env['PATH'] = f'{tmp_path / "nocc"}:{env["PATH"]}'
    (tmp_path / 'nocc').mkdir()
    (tmp_path / 'nocc' / 'cc').write_text('#!/bin/sh\nexit 1\n')
    (tmp_path / 'nocc' / 'cc').chmod(0o755)
    run = _run_step(V_STEP, env)
    assert run.returncode == 0, run.stdout[-2000:]
    assert run.stdout.splitlines()[:2] == ['QGV_OFFICIAL_PARSER_BUILD_FAILED', 'QGV_OFFICIAL_STEP_STOPPED exit=124']
    assert _receipt(run.stdout)['pages_artifact_guard'] == 'PASS'
    assert not list((runner / 'public-cockpit').glob('.qgv-official*'))


@pytest.mark.skipif(not shutil.which('cc'), reason='no C compiler')
def test_the_v_step_with_an_unreachable_live_copy_is_not_run_and_never_claims_no_publication(tmp_path, built_site):
    """Network blocked for the live read too (closed proxy): after its retries the publisher computes nothing and writes
    NOT_RUN / LIVE_UNREACHABLE (never NO_OFFICIAL_YET); the step and the job go on."""
    runner, env = _runner(tmp_path, built_site, secrets={'hmac': 'synthetic-test-key-0123456789', 'token': 'synthetic-token'},
                          live='closed')
    run = _run_step(V_STEP, env)
    assert run.returncode == 0, run.stdout[-2000:]
    assert run.stdout.splitlines()[0] == ('QGV_OFFICIAL attempt=NOT_RUN reason=LIVE_UNREACHABLE published=NONE basis=- rows=0 '
                                          'ranked=0 supplied=-')
    assert _receipt(run.stdout)['pages_artifact_guard'] == 'PASS'
    out = runner / 'public-cockpit'
    status = json.loads((out / qo.STATUS_FILENAME).read_bytes())
    qo.require_status(status)
    assert (status['attempt_state'], status['reason_code'], status['official_publication_id']) == ('NOT_RUN', 'LIVE_UNREACHABLE', None)
    assert not (out / qo.FILENAME).exists()
    assert check_tool.ok(check_tool.inspect(out))


def test_a_guard_refusal_stays_inside_the_v_step(tmp_path, built_site):
    """Review 2026-10-24: if the V step's own artifact guard refuses the V files (a future guard-vs-validator mismatch, or
    anything a guard-only rule catches), they are removed, the guard passes on the rest, the step fails (continue-on-error;
    the history step is skipped) and the next required step's guard passes: the collect job, upload and deploy go on."""
    shim = ('#!/bin/sh\ncase "$1" in *qgv_official_publish.py) '
            'printf \'{"schema":"qgv-official/1","rows":{"NYSE:ABT":{"price":1}}}\' > "$RUNNER_TEMP/public-cockpit/qgv-official.json"; '
            'printf \'{"attempt_state":"OK"}\' > "$RUNNER_TEMP/public-cockpit/qgv-official-status.json"; '
            'echo "QGV_OFFICIAL attempt=OK reason=- published=NEW basis=2026-10-13 rows=1 ranked=0 supplied=1/1"; exit 0;; esac\n'
            f'exec "{tmp_path / "bin" / "python-real"}" "$@"\n')
    runner, env = _runner(tmp_path, built_site, secrets={}, shim=shim)
    env['PATH'] = f'{tmp_path / "nocc"}:{env["PATH"]}'
    (tmp_path / 'nocc').mkdir()
    (tmp_path / 'nocc' / 'cc').write_text('#!/bin/sh\nexit 1\n')
    (tmp_path / 'nocc' / 'cc').chmod(0o755)
    run = _run_step(V_STEP, env)
    assert run.returncode == 1                                         # the step fails (continue-on-error in the workflow)
    assert 'QGV_OFFICIAL_GUARD_REFUSED' in run.stdout.splitlines()
    receipts = [json.loads(l) for l in run.stdout.splitlines() if l.startswith('{')]
    assert [r['pages_artifact_guard'] for r in receipts] == ['FAIL']    # the refusal; no final guard run after it
    out = runner / 'public-cockpit'
    assert not (out / qo.FILENAME).exists() and not (out / qo.STATUS_FILENAME).exists()
    # the next required step ends with the plain guard: it passes on the same directory
    nxt = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', GUARD_LINE + '\n'], cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=600)
    assert nxt.returncode == 0 and _receipt(nxt.stdout)['pages_artifact_guard'] == 'PASS'


# ---- tools/qgv_official_check.py and tools/qgv_official_history.py on the publisher's real output ------------------------
LATER = NOW + dt.timedelta(hours=1)          # same New York day (shard_day), a later run


def _artifact(tmp_path):
    out = tmp_path / 'artifact'
    out.mkdir()
    payload = base_payload()
    (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(payload))
    parser = tmp_path / 'parser'
    parser.write_text('')
    return out, payload, str(parser)


def _publish(out, parser, *, day=None, previous=None, now=NOW, fail=None):
    def fetch_day(keys, basis, parser=None, workdir=None):
        if fail:
            raise iex_hist.IexHistError(fail)
        return day
    return publisher.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=previous, raw_token='t',
                         hmac_key=KEY, now=now, workdir=out.parent / 'w', fetch_day=fetch_day, read_store=lambda s, n: {},
                         clock=lambda: now)


@pytest.fixture
def published(tmp_path):
    out, payload, parser = _artifact(tmp_path)
    s = _publish(out, parser, day=synthetic_day(payload, canary_key='NYSE:ABT'))
    assert (s['attempt'], s['published']) == ('OK', 'NEW')
    return out, payload, parser


def test_check_a_new_publication_is_valid_consistent_and_new(published):
    out, _, _ = published
    result = check_tool.inspect(out)
    official = qo.parse((out / qo.FILENAME).read_bytes())
    assert check_tool.ok(result) and (result['publication'], result['status'], result['consistent'], result['new']) == ('VALID', 'VALID', True, True)
    assert check_tool.line(result) == (f"QGV_OFFICIAL_CHECK publication=VALID status=VALID consistent=YES new=YES attempt=OK reason=- "
                                       f"basis=2026-10-13 rows={len(official['rows'])} ranked={official['coverage']['ranked']}")
    assert str(CANARY)[:6] not in check_tool.line(result)


def test_check_a_kept_copy_is_consistent_but_not_new(published, tmp_path):
    out, payload, parser = published
    live = tmp_path / 'live.json'
    live.write_bytes((out / qo.FILENAME).read_bytes())
    for kw in ({'fail': 'MD5_MISMATCH'}, {'day': synthetic_day(payload, canary_key='NYSE:ABT')}):   # KEPT_LAST_GOOD, KEPT_SAME_ID
        s = _publish(out, parser, previous=str(live), now=LATER, **kw)
        assert s['published'] in ('KEPT_LAST_GOOD', 'KEPT_SAME_ID')
        result = check_tool.inspect(out)
        assert check_tool.ok(result) and result['consistent'] is True and result['new'] is False
        assert history_tool.skip_reason(result) == 'NOT_NEW'


def test_check_refuses_invalid_or_disagreeing_files(published, tmp_path):
    out, _, _ = published
    body = (out / qo.FILENAME).read_bytes()
    status = json.loads((out / qo.STATUS_FILENAME).read_bytes())
    # a status that names another publication
    (out / qo.STATUS_FILENAME).write_text(json.dumps(dict(status, official_publication_id='qgvpub-' + 'f' * 64)))
    result = check_tool.inspect(out)
    assert result['consistent'] is False and not check_tool.ok(result) and history_tool.skip_reason(result) == 'STATUS_MISMATCH'
    assert check_tool.main(['--artifact-dir', str(out)]) == 1
    # a status that says no publication exists while one is shipped
    (out / qo.STATUS_FILENAME).write_text(json.dumps(dict(status, attempt_state='NO_OFFICIAL_YET', reason_code='X',
                                                          official_publication_id=None, official_price_basis_date=None,
                                                          official_verified_at=None)))
    assert check_tool.inspect(out)['consistent'] is False
    # a broken status and a broken publication
    (out / qo.STATUS_FILENAME).write_text('{"schema":1}')
    assert check_tool.inspect(out)['status'] == 'INVALID'
    (out / qo.FILENAME).write_bytes(body.replace(b'"OFFICIAL"', b'"DRAFT"', 1))
    result = check_tool.inspect(out)
    assert result['publication'] == 'INVALID' and not check_tool.ok(result) and history_tool.skip_reason(result) == 'PUBLICATION_INVALID'
    # a symlinked publication is never followed
    (out / qo.FILENAME).unlink()
    (tmp_path / 'elsewhere.json').write_bytes(body)
    (out / qo.FILENAME).symlink_to(tmp_path / 'elsewhere.json')
    assert check_tool.inspect(out)['publication'] == 'INVALID'


def test_check_absent_files_are_normal(tmp_path, capsys):
    (tmp_path / 'empty').mkdir()
    assert check_tool.main(['--artifact-dir', str(tmp_path / 'empty')]) == 0
    assert capsys.readouterr().out == ('QGV_OFFICIAL_CHECK publication=ABSENT status=ABSENT consistent=- new=NO attempt=- reason=- '
                                       'basis=- rows=0 ranked=0\n')
    assert check_tool.main(['--artifact-dir', str(tmp_path / 'missing')]) == 2


def test_history_uploads_a_new_publication_once_under_its_basis_day(published, capsys):
    out, _, _ = published
    body = (out / qo.FILENAME).read_bytes()
    official = qo.parse(body)
    store = RawStore()
    line = history_tool.run(out, environ={'RAW_REPO_TOKEN': 'synthetic-setting'}, call=store)
    digest = hashlib.sha256(body).hexdigest()
    assert line == (f'QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-2026-10-13 bytes={len(body)} sha256={digest} '
                    'inputs=UPLOADED')
    assert history_tool.warning(line) is None
    assets = store.releases['qgv-official-2026-10-13']['assets']
    name = official['publication_id'] + '.json'
    # The inputs the publication was built from (owner decision 2026-11-15): the artifact's sec-qgv2.json, byte for byte, named
    # by the publication's own recorded inputs sha256, beside the publication pair in the same release.
    inputs = (out / sec_qgv2.FILENAME).read_bytes()
    inputs_sha = official['inputs'][0]['sha256']
    assert official['inputs'][0]['file'] == sec_qgv2.FILENAME and hashlib.sha256(inputs).hexdigest() == inputs_sha
    inputs_name = f'inputs-{inputs_sha}.json'
    assert set(assets) == {name, name + '.sha256', inputs_name, inputs_name + '.sha256'}
    assert assets[name][1] == body and assets[name + '.sha256'][1] == f'{digest}  {name}\n'.encode()
    assert qo.parse(assets[name][1]) == official                     # the public bytes: scores only, the strict reader passes
    assert assets[inputs_name][1] == inputs and assets[inputs_name + '.sha256'][1] == f'{inputs_sha}  {inputs_name}\n'.encode()
    sec_qgv2.require_qgv2(sec_qgv2.parse_json(assets[inputs_name][1]))   # the public input file, the strict reader passes
    posts = sum(1 for m, _, _ in store.calls if m == 'POST')
    again = history_tool.run(out, environ={'RAW_REPO_TOKEN': 'synthetic-setting'}, call=store)
    assert again.endswith(' already_present inputs=ALREADY_PRESENT') and sum(1 for m, _, _ in store.calls if m == 'POST') == posts
    assert history_tool.warning(again) is None
    assert all(url.startswith(('https://api.github.com/repos/kco994553-star/investment-system1-raw/',
                               'https://uploads.github.com/repos/kco994553-star/investment-system1-raw/')) for _, url, _ in store.calls)


def test_history_keeps_a_second_publication_of_the_same_basis_day_beside_the_first(published, tmp_path):
    out, payload, parser = published
    store = RawStore()
    first = qo.parse((out / qo.FILENAME).read_bytes())
    assert 'RAW_UPLOADED' in history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store)
    live = tmp_path / 'live.json'
    live.write_bytes((out / qo.FILENAME).read_bytes())
    s = _publish(out, parser, previous=str(live), now=LATER, day=synthetic_day(payload, price_of={'NYSE:ABT': 77.25}))
    assert s['published'] == 'NEW'
    second = qo.parse((out / qo.FILENAME).read_bytes())
    assert second['publication_id'] != first['publication_id'] and second['times']['price_basis_date'] == first['times']['price_basis_date']
    line = history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store)
    assert 'RAW_UPLOADED tag=qgv-official-2026-10-13' in line and ' already_present' not in line
    # Same sec-qgv2.json under both publications: its inputs pair is already there and is never uploaded again.
    assert second['inputs'][0]['sha256'] == first['inputs'][0]['sha256'] and line.endswith(' inputs=ALREADY_PRESENT')
    names = set(store.releases['qgv-official-2026-10-13']['assets'])
    inputs_name = f"inputs-{first['inputs'][0]['sha256']}.json"
    assert {first['publication_id'] + '.json', second['publication_id'] + '.json', inputs_name, inputs_name + '.sha256'} <= names
    assert len(names) == 6


def test_history_skips_without_a_new_publication_or_a_token(published, tmp_path, capsys):
    out, payload, parser = published
    store = RawStore()
    assert history_tool.run(out, environ={}, call=store) == 'QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED' and store.calls == []
    (out / qo.STATUS_FILENAME).unlink()
    assert history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store) == 'QGV_OFFICIAL_HISTORY skipped=STATUS_ABSENT'
    (out / qo.FILENAME).unlink()
    assert history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store) == 'QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION'
    assert store.calls == []
    assert history_tool.main(['--artifact-dir', str(out)]) == 0
    assert capsys.readouterr().out == 'QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION\n'
    assert history_tool.main(['--artifact-dir', str(tmp_path / 'missing')]) == 2


@pytest.mark.parametrize('store,code', [(RawStore(status=403), 'RAW_UPLOAD_FAILED code=RELEASE_LOOKUP_FAILED inputs=NOT_ATTEMPTED'),
                                        (RawStore(broken=True), 'RAW_UPLOAD_FAILED code=UNEXPECTED inputs=NOT_ATTEMPTED')])
def test_history_upload_failures_are_one_fixed_line(published, store, code):
    out, _, _ = published
    line = history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store)
    assert line == 'QGV_OFFICIAL_HISTORY ' + code
    # The inputs were not kept either: visible as a warning (the step still exits 0).
    assert history_tool.warning(line) == '::warning::QGV_OFFICIAL_HISTORY inputs NOT_ATTEMPTED'


# ---- the inputs bundle beside the publication (owner decision 2026-11-15) ---------------------------------------------
SECRET_SETTING = 'synthetic-token-canary-7f3a9c'


class InputsFailStore(RawStore):
    """The release and the publication pair work; uploads of the inputs pair answer `fail` (an HTTP status) or raise."""

    def __init__(self, fail):
        super().__init__()
        self.fail = fail

    def __call__(self, method, url, *, data=None, headers=None, auth=True):
        if method == 'POST' and 'name=inputs-' in url:
            self.calls.append((method, url, auth))
            if self.fail == 'raise':
                raise OSError(f'synthetic failure https://x-access-token:{SECRET_SETTING}@uploads.github.com/{url}')
            return self.fail, {}, b''
        return super().__call__(method, url, data=data, headers=headers, auth=auth)


def _main(out, store, monkeypatch, capsys):
    """tools/qgv_official_history.py main as the workflow runs it (token in the env, the release store behind `http`)."""
    monkeypatch.setenv('RAW_REPO_TOKEN', SECRET_SETTING)
    monkeypatch.setattr(history_tool.raw_store_release, 'http', store)
    code = history_tool.main(['--artifact-dir', str(out)])
    return code, capsys.readouterr()


def _publication_kept(out, store):
    official = qo.parse((out / qo.FILENAME).read_bytes())
    assets = store.releases['qgv-official-2026-10-13']['assets']
    name = official['publication_id'] + '.json'
    assert assets[name][1] == (out / qo.FILENAME).read_bytes() and name + '.sha256' in assets
    return official, assets


def _never_leaks(printed, out):
    assert SECRET_SETTING not in printed and 'https://' not in printed and '@' not in printed
    assert '{' not in printed and '"' not in printed                   # no file contents
    assert str(CANARY)[:6] not in printed


def test_history_inputs_uploaded_by_main_print_no_warning_and_no_token(published, monkeypatch, capsys):
    out, _, _ = published
    store = RawStore()
    code, printed = _main(out, store, monkeypatch, capsys)
    official, assets = _publication_kept(out, store)
    lines = printed.out.splitlines()
    assert code == 0 and len(lines) == 1 and lines[0].startswith('QGV_OFFICIAL_HISTORY RAW_UPLOADED ')
    assert lines[0].endswith(' inputs=UPLOADED') and '::warning::' not in printed.out and printed.err == ''
    assert f"inputs-{official['inputs'][0]['sha256']}.json" in assets
    _never_leaks(printed.out, out)


def test_history_inputs_never_replace_an_existing_asset(published):
    out, _, _ = published
    store = RawStore()
    official = qo.parse((out / qo.FILENAME).read_bytes())
    inputs_name = f"inputs-{official['inputs'][0]['sha256']}.json"
    store.releases['qgv-official-2026-10-13'] = {'id': 7, 'assets': {inputs_name: (8, b'kept-as-it-was')}}
    line = history_tool.run(out, environ={'RAW_REPO_TOKEN': 's'}, call=store)
    assets = store.releases['qgv-official-2026-10-13']['assets']
    # Only the missing sha256 file is added; the present asset keeps its bytes (no replace, no delete).
    assert line.endswith(' inputs=UPLOADED') and assets[inputs_name] == (8, b'kept-as-it-was')
    assert assets[inputs_name + '.sha256'][1] == f"{official['inputs'][0]['sha256']}  {inputs_name}\n".encode()
    assert not [u for m, u, _ in store.calls if m == 'POST' and u.endswith('name=' + inputs_name)]
    assert not [m for m, _, _ in store.calls if m in ('DELETE', 'PATCH', 'PUT')]


def test_history_inputs_hash_mismatch_warns_and_still_uploads_the_publication(published, monkeypatch, capsys):
    out, _, _ = published
    path = out / sec_qgv2.FILENAME
    path.write_bytes(path.read_bytes() + b' ')                          # not the bytes the publication was built from
    store = RawStore()
    code, printed = _main(out, store, monkeypatch, capsys)
    _, assets = _publication_kept(out, store)
    assert code == 0 and printed.out.splitlines()[0] == '::warning::QGV_OFFICIAL_HISTORY inputs HASH_MISMATCH'
    assert printed.out.splitlines()[1].startswith('QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-2026-10-13 ')
    assert printed.out.splitlines()[1].endswith(' inputs=HASH_MISMATCH') and len(printed.out.splitlines()) == 2
    assert not [n for n in assets if n.startswith('inputs-')]
    assert not [u for m, u, _ in store.calls if 'name=inputs-' in u]
    _never_leaks(printed.out, out)


@pytest.mark.parametrize('damage,expected', [('unlink', 'MISSING'), ('symlink', 'UNREADABLE'), ('directory', 'UNREADABLE')])
def test_history_inputs_missing_or_unreadable_warns(published, monkeypatch, capsys, tmp_path, damage, expected):
    out, _, _ = published
    path = out / sec_qgv2.FILENAME
    body = path.read_bytes()
    path.unlink()
    if damage == 'symlink':                                             # the same bytes behind a link are never followed
        (tmp_path / 'elsewhere-qgv2.json').write_bytes(body)
        path.symlink_to(tmp_path / 'elsewhere-qgv2.json')
    elif damage == 'directory':
        path.mkdir()
    store = RawStore()
    code, printed = _main(out, store, monkeypatch, capsys)
    _, assets = _publication_kept(out, store)
    lines = printed.out.splitlines()
    assert code == 0 and lines == ['::warning::QGV_OFFICIAL_HISTORY inputs ' + expected, lines[1]] and len(lines) == 2
    assert lines[1].startswith('QGV_OFFICIAL_HISTORY RAW_UPLOADED ') and lines[1].endswith(' inputs=' + expected)
    assert not [n for n in assets if n.startswith('inputs-')]
    _never_leaks(printed.out, out)


@pytest.mark.parametrize('fail,expected', [(500, 'UPLOAD_FAILED_HTTP_500'), (422, 'UPLOAD_FAILED_HTTP_422'),
                                           ('raise', 'UPLOAD_FAILED')])
def test_history_inputs_upload_failure_warns_and_exits_0(published, monkeypatch, capsys, fail, expected):
    out, _, _ = published
    store = InputsFailStore(fail)
    code, printed = _main(out, store, monkeypatch, capsys)
    _, assets = _publication_kept(out, store)                           # the publication copy still happened
    lines = printed.out.splitlines()
    assert code == 0 and len(lines) == 2 and lines[0] == '::warning::QGV_OFFICIAL_HISTORY inputs ' + expected
    assert lines[1].startswith('QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-2026-10-13 ')
    assert lines[1].endswith(' inputs=' + expected) and ' code=' not in lines[1]
    assert not [n for n in assets if n.startswith('inputs-')] and [u for m, u, _ in store.calls if 'name=inputs-' in u]
    _never_leaks(printed.out + printed.err, out)


def test_history_warning_lines_are_fixed_codes_only():
    pattern = re.compile(r'::warning::QGV_OFFICIAL_HISTORY inputs [A-Z0-9_]+')
    for code in ('MISSING', 'UNREADABLE', 'HASH_MISMATCH', 'UPLOAD_FAILED_HTTP_500', 'UPLOAD_FAILED', 'NOT_ATTEMPTED'):
        note = history_tool.warning(f'QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=t bytes=1 sha256=x inputs={code}')
        assert note == '::warning::QGV_OFFICIAL_HISTORY inputs ' + code and pattern.fullmatch(note)
    for line in ('QGV_OFFICIAL_HISTORY skipped=NOT_NEW', 'QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED',
                 'QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=t bytes=1 sha256=x inputs=UPLOADED',
                 'QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=t bytes=1 sha256=x already_present inputs=ALREADY_PRESENT'):
        assert history_tool.warning(line) is None


def test_history_and_check_never_touch_a_price_route_or_the_publication_secrets():
    for name in ('qgv_official_history', 'qgv_official_check'):
        src = (ROOT / 'tools' / (name + '.py')).read_text()
        assert not re.search(r'\biex_(?:hist|monthend)\b|iextrading|googleapis', src), name
        assert 'QGV_OFFICIAL_HMAC_KEY' not in src and 'RAW_REPO_READ_TOKEN' not in src and 'GITHUB_STEP_SUMMARY' not in src
        assert 'print(token' not in src and 'environ[' not in src
    assert 'write_' not in (ROOT / 'tools/qgv_official_check.py').read_text()
