"""Read-only CI execution-source observations for PIW-D001/D002.

Provider context is recorded, not authenticated by this utility. Workflow source
uses github.workflow_sha/ref separately from the audited subject and checkout.
The exact local Git workflow bytes and tracked verifier working bytes are hashed.
Missing source, dirty/extra verifier files, malformed context and substitutions
are UNAVAILABLE; never fall back to the subject SHA. No network or source content
is executed. Raw FPIA status and exit code are untouched. Numeric job ID must be
joined from the authoritative Actions API by run/attempt/job key afterwards.
An independently accepted verifier/launcher and runtime attestation are still
required: observations, including OBSERVED_BYTE_MATCH, are not acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

MAX_CONTEXT_BYTES = 1024
FIELDS = ('repository', 'workflow_sha', 'workflow_ref', 'event_sha',
          'subject_sha', 'run_id', 'run_attempt', 'job_key', 'event_name')
SHA = re.compile(r'[0-9a-f]{40}')
REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}')


def _sha(value):
    return type(value) is str and SHA.fullmatch(value) and value != '0' * 40


def _git(repo, *args):
    # Never use caller Git overrides or replacement objects for byte identity.
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LANG': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    p = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull,
                        '-C', str(repo), *args], env=env, capture_output=True)
    if p.returncode:
        raise ValueError('Git object unavailable')
    return p.stdout


def _blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def collect_receipt(context, repo, verifier_path, *, workflow_source=False):
    result = {'schema': 'FPIA_CI_SOURCE_OBSERVATION/1', 'status': 'UNAVAILABLE',
              'authentication': 'NOT_VERIFIED', 'integration_acceptance': 'BLOCKED',
              'scope': 'PROVIDER_CONTEXT_AND_LOCAL_BYTES_ONLY', 'errors': []}
    errors = result['errors']
    if type(context) is not dict or set(context) != set(FIELDS):
        errors.append('exact allowlisted runtime fields required')
        return result
    if any(type(v) is not str or len(v) > MAX_CONTEXT_BYTES for v in context.values()):
        errors.append('runtime values must be bounded strings')
        return result
    for name in ('workflow_sha', 'event_sha', 'subject_sha'):
        if not _sha(context[name]):
            errors.append(name + ' unavailable or malformed')
    if not REPO.fullmatch(context['repository']):
        errors.append('repository unavailable or malformed')
    prefix = context['repository'] + '/'
    workflow, separator, ref = context['workflow_ref'].removeprefix(prefix).partition('@')
    if (not context['workflow_ref'].startswith(prefix) or not separator or not ref.startswith('refs/')
            or not re.fullmatch(r'\.github/workflows/[A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml', workflow)):
        errors.append('workflow ref does not bind a valid repository workflow path')
    if (type(verifier_path) is not str or not verifier_path
            or Path(verifier_path).is_absolute()
            or any(x in ('', '.', '..') for x in verifier_path.split('/'))):
        errors.append('verifier path must be a bounded repository-relative directory')
    for name in ('run_id', 'run_attempt'):
        v = context[name]
        if not re.fullmatch(r'[1-9][0-9]{0,19}', v) or int(v) >= 2 ** 64:
            errors.append(name + ' unavailable or malformed')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,99}', context['job_key']):
        errors.append('job key unavailable or malformed')
    if context['event_name'] not in ('pull_request', 'workflow_dispatch'):
        errors.append('event outside the current FPIA workflow scope')
    if errors:
        return result
    result['repository'] = context['repository']
    result['execution'] = {'run_id': int(context['run_id']), 'run_attempt': int(context['run_attempt']),
                           'job_key': context['job_key'], 'numeric_job_id': 'UNAVAILABLE',
                           'event_name': context['event_name'], 'event_sha': context['event_sha']}
    result['workflow'] = {'path': workflow, 'source_commit': context['workflow_sha'],
                          'provider_ref': context['workflow_ref'], 'blob': 'UNAVAILABLE'}
    result['subject_sha'] = context['subject_sha']
    repo = Path(repo).resolve()
    try:
        parent = repo
        for part in verifier_path.split('/'):
            parent = parent / part
            if parent.is_symlink():
                raise ValueError('linked verifier directory')
        head = _git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        binding = 'WORKFLOW_SOURCE' if workflow_source else 'SUBJECT'
        result['checkout'] = {'head': head, 'binding': binding}
        expected = context['workflow_sha'] if workflow_source else context['subject_sha']
        if head != expected:
            errors.append('checkout HEAD does not equal the explicit ' + binding)
        wf = _git(repo, 'show', context['workflow_sha'] + ':' + workflow)
        blob = _git(repo, 'rev-parse', '--verify', context['workflow_sha'] + ':' + workflow).decode().strip()
        if _blob(wf) != blob:
            errors.append('workflow blob disagrees with exact Git bytes')
        result['workflow'].update(blob=blob, sha256=hashlib.sha256(wf).hexdigest(), bytes=len(wf))
        rows = _git(repo, 'ls-tree', '-rz', '--full-tree', head, '--', verifier_path).split(b'\0')
        manifest = []
        tracked = set()
        for row in rows:
            if not row:
                continue
            info, raw_path = row.split(b'\t', 1)
            mode, kind, raw_blob = info.decode().split()
            path = raw_path.decode('utf-8')
            tracked.add(path)
            p = repo / path
            if mode not in ('100644', '100755') or kind != 'blob' or not stat.S_ISREG(p.lstat().st_mode):
                errors.append('verifier source is not a regular tracked file: ' + path)
                continue
            data = p.read_bytes()
            if _blob(data) != raw_blob:
                errors.append('verifier working bytes differ from Git: ' + path)
            manifest.append({'path': path, 'git_blob': raw_blob,
                             'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        if not tracked or verifier_path + '/track_c_fpia_child.py' not in tracked:
            errors.append('verifier/launcher manifest is incomplete')
        # Include ignored files: ignore rules are not an execution-scope boundary.
        for root, dirs, names in os.walk(repo / verifier_path, followlinks=False):
            for name in dirs + names:
                p = Path(root) / name
                relative = p.relative_to(repo).as_posix()
                if p.is_symlink() or (p.is_file() and relative not in tracked):
                    errors.append('extra or linked verifier working file: ' + relative)
        result['verifier_observation'] = {'commit': head, 'files': manifest,
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest(),
            'authority': 'NOT_VERIFIED'}
    except (ValueError, OSError, UnicodeError, subprocess.TimeoutExpired):
        errors.append('workflow/verifier source bytes unavailable')
    if not errors:
        result['status'] = 'OBSERVED_BYTE_MATCH'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--verifier-path', required=True)
    parser.add_argument('--workflow-source', action='store_true',
                        help='Require verifier checkout HEAD to equal workflow_sha; retain real subject separately')
    args = parser.parse_args()
    context = {name: os.environ.get('FPIA_' + name.upper(), '') for name in FIELDS}
    result = collect_receipt(context, args.repo, args.verifier_path, workflow_source=args.workflow_source)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if result['status'] == 'OBSERVED_BYTE_MATCH' else 2


if __name__ == '__main__':
    raise SystemExit(main())
