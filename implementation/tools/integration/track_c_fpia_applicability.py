"""Read-only PIW-D006 preflight. No branch-name inputs or integration grants.

Reference/namespace are derived only after the existing authenticated CDR loader.
This executes no subject Python, Frozen tools or tests. Existing raw FPIA is unchanged.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import tempfile


def _git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def subject_decision(repo, reference, subject, namespace, modules):
    """Classify Git facts using a namespace supplied by the authenticated caller.

    This internal classification is not itself authentication or audit acceptance.
    Unknown/dynamic executable imports conservatively prevent OUTSIDE_SCOPE.
    """
    result = {'schema': 'FPIA_APPLICABILITY/1', 'subject': subject, 'reference': reference,
              'status': 'UNAVAILABLE', 'fpia_status': 'NOT_RUN',
              'authentication': 'NOT_VERIFIED', 'integration_acceptance': 'BLOCKED',
              'reasons': []}
    try:
        for sha in (reference, subject):
            if not re.fullmatch(r'[0-9a-f]{40}', sha or ''):
                raise ValueError('exact commit SHA required')
            _git(repo, 'cat-file', '-e', sha + '^{commit}')
        if _git(repo, 'rev-parse', '--is-shallow-repository').strip() != b'false':
            raise ValueError('shallow object store')
        ancestry = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor',
                                  reference, subject], capture_output=True)
        if ancestry.returncode == 0:
            result['status'] = 'APPLIES'
            result['reasons'] = ['AUTHENTICATED_REFERENCE_ANCESTOR']
            return result
        if ancestry.returncode != 1:
            raise ValueError('ancestry unavailable')
        if not modules:
            raise ValueError('authenticated module namespace unavailable')
        entries = _git(repo, 'ls-tree', '-rz', '--full-tree', subject).split(b'\0')
        blockers = []
        for entry in filter(None, entries):
            meta, raw_path = entry.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            path = raw_path.decode('utf-8', 'strict')
            if namespace(path):
                blockers.append({'path': path, 'reason': 'TRACK_C_CONTENT_WITHOUT_REFERENCE_ANCESTRY'})
                continue
            if mode == '120000' or kind != 'blob':
                blockers.append({'path': path, 'reason': 'INDIRECT_CONTENT_UNCLASSIFIED'})
                continue
            raw = _git(repo, 'cat-file', 'blob', blob)
            executable = mode == '100755' or raw.startswith(b'#!')
            if not executable and not path.endswith(('.py', '.pyw', '.sh', '.yml', '.yaml', '.js', '.ts')):
                continue
            data = raw.decode('utf-8', 'strict')
            if any(m in data or m.replace('.', '/') in data for m in modules):
                blockers.append({'path': path, 'reason': 'TRACK_C_IMPORT_OR_EXECUTABLE_MENTION'})
            elif path.endswith(('.py', '.pyw')):
                try:
                    tree = ast.parse(data, filename=path)
                except (SyntaxError, ValueError):
                    blockers.append({'path': path, 'reason': 'UNPARSEABLE_EXECUTABLE_SOURCE'})
                    continue
                # Parent-module imports, e.g. `from investment_system import evl`.
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        blockers.append({'path': path, 'reason': 'CALL_TARGET_UNCLASSIFIED'})
                    if isinstance(node, ast.ImportFrom) and (node.level or any(a.name == '*' for a in node.names)):
                        blockers.append({'path': path, 'reason': 'RELATIVE_OR_STAR_IMPORT_UNCLASSIFIED'})
                    if isinstance(node, ast.ImportFrom) and node.module:
                        imported = [node.module + '.' + a.name for a in node.names]
                        if any(n == m or n.startswith(m + '.') for n in imported for m in modules):
                            blockers.append({'path': path, 'reason': 'TRACK_C_IMPORT'})
                    if isinstance(node, (ast.Name, ast.Attribute)):
                        name = node.id if isinstance(node, ast.Name) else node.attr
                        if name in {'importlib', 'import_module', '__import__', 'run_module',
                                    'eval', 'exec', 'runpy'}:
                            blockers.append({'path': path, 'reason': 'DYNAMIC_EXECUTION_UNCLASSIFIED'})
            else:
                # Non-Python executable sources cannot prove absence of dynamic imports.
                blockers.append({'path': path, 'reason': 'NON_PYTHON_EXECUTION_UNCLASSIFIED'})
        result['status'] = 'BLOCKED' if blockers else 'OUTSIDE_SCOPE_NOT_RUN'
        result['reasons'] = blockers or ['NO_REFERENCE_ANCESTRY_OR_TRACK_C_CONTENT_IMPORTS']
    except (subprocess.CalledProcessError, OSError, ValueError, UnicodeError) as exc:
        result['reasons'] = [str(exc)[-500:]]
    return result


def authenticated_preflight(repo, subject, register, cdr):
    import track_c_fpia as fpia
    with tempfile.TemporaryDirectory(prefix='fpia-applicability-') as work:
        audit = fpia.Audit(repo, subject, register, cdr, work, {})
        audit.check_caller_repository()
        T = audit.resolve(subject, '--tree')
        G = audit.resolve(register, '--register-commit')
        audit.populate([T, G])
        auth = fpia.fauth.authenticate(audit.sb, G, cdr, audit.fetch_refs,
                                       audit.opts['authority_remote'])
        if auth['status'] != 'PASS':
            return {'schema': 'FPIA_APPLICABILITY/1', 'subject': T, 'register': G,
                    'status': 'UNAVAILABLE', 'fpia_status': 'NOT_RUN',
                    'authentication': 'NOT_VERIFIED', 'integration_acceptance': 'BLOCKED',
                    'reasons': ['REFERENCE_AUTHENTICATION_UNAVAILABLE'], 'authority': auth}
        audit.T, audit.G, audit.R, audit.Vs = T, G, auth['R'], auth['Vs']
        audit.derive()
        if audit.caller_fetch_problems() or audit.sb.is_shallow():
            raise ValueError('incomplete authenticated object store')
        # Sandbox fetched the authenticated reference; caller object store need not contain R.
        result = subject_decision(audit.sb.git_dir, audit.R, T, audit.proj.ns, audit.tcm_R)
        result.update(register=G, authority=auth)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--register-commit', required=True)
    parser.add_argument('--cdr', default='CDR-014')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        result = authenticated_preflight(args.repo, args.tree, args.register_commit, args.cdr)
    except Exception as exc:
        result = {'schema': 'FPIA_APPLICABILITY/1', 'subject': args.tree,
                  'status': 'UNAVAILABLE', 'fpia_status': 'NOT_RUN',
                  'authentication': 'NOT_VERIFIED', 'integration_acceptance': 'BLOCKED',
                  'reasons': [str(exc)[-500:]]}
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(result['status'])
    return 0 if result['status'] in {'APPLIES', 'OUTSIDE_SCOPE_NOT_RUN'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
