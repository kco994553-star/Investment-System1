"""Read-only exact generator replay; outputs evidence only, no repository edits."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PYTHON = '/workspace/validation-venv311/bin/python'
RECEIPTS = Path('/workspace/takeover-evidence/c28-evidence-32-33')
TREES = Path('/workspace/c28-evidence-audit-trees')
FOUR = {'available_at', 'data_stamp_refs', 'source_vintages', 'input_hash'}


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(name, value):
    (RECEIPTS / name).write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + '\n')


def difference(before, after, path=''):
    result = []
    if type(before) is not type(after):
        return [{'kind': 'CHANGED_TYPE', 'path': path, 'before': before, 'after': after}]
    if isinstance(before, dict):
        for key in sorted(set(before) | set(after)):
            child = path + '/' + key
            if key not in before:
                result.append({'kind': 'ADDED', 'path': child, 'after': after[key]})
            elif key not in after:
                result.append({'kind': 'REMOVED', 'path': child, 'before': before[key]})
            else:
                result.extend(difference(before[key], after[key], child))
    elif isinstance(before, list):
        if len(before) != len(after):
            result.append({'kind': 'LEN', 'path': path, 'before': len(before), 'after': len(after)})
        else:
            for i, (a, b) in enumerate(zip(before, after)):
                result.extend(difference(a, b, path + '/' + str(i)))
    elif before != after:
        result.append({'kind': 'CHANGED', 'path': path, 'before': before, 'after': after})
    return result


def run_exact(number, side):
    impl = TREES / f'pr{number}-{side}' / 'implementation'
    relative = 'tools/producer_engine_fingerprint.py' if number == 32 else 'docs/entity_metadata/evidence/numeric_fingerprint.py'
    tool = impl / relative
    argument = impl / 'src' if number == 32 else impl
    outputs = []
    command = [PYTHON, str(tool), str(argument)]
    for repeat in (1, 2):
        p = subprocess.run(command, cwd=impl, capture_output=True)
        (RECEIPTS / f'pr{number}-{side}-stdout-{repeat}.json').write_bytes(p.stdout)
        (RECEIPTS / f'pr{number}-{side}-stderr-{repeat}.log').write_bytes(p.stderr)
        if p.returncode:
            raise RuntimeError((number, side, p.returncode, p.stderr.decode()))
        outputs.append(p.stdout)
    assert outputs[0] == outputs[1]
    info = {'command': command, 'tool_sha256': hash_bytes(tool.read_bytes()),
            'stdout_sha256': hash_bytes(outputs[0]), 'repeatable': True, 'return_code': 0}
    if number == 32:
        # Exact tool source, omitting only its final presentation print. Run in
        # another process so each side imports its own source without caching.
        harness = (
            'import sys,json,pathlib\n'
            'p=pathlib.Path(sys.argv[1]);tool=p.read_text();'
            'sys.argv=[str(p),sys.argv[2]];ns={"__name__":"__main__","__file__":str(p)};'
            'exec(compile(tool.rsplit("print(",1)[0],str(p),"exec"),ns);'
            'out={k:ns["norm"](ns[v]) for k,v in '
            '{"qgv":"q","technical":"t","macro":"m","leaderboard":"lb","portfolio_official_book":"book"}.items()};'
            'print(json.dumps(out,sort_keys=True,default=str))\n')
        p = subprocess.run([PYTHON, '-c', harness, str(tool), str(argument)], cwd=impl, capture_output=True)
        assert p.returncode == 0, p.stderr
        (RECEIPTS / f'pr{number}-{side}-normalized.json').write_bytes(p.stdout)
        values = json.loads(p.stdout)
        hashes = {k: hash_bytes(json.dumps(v, sort_keys=True, default=str).encode()) for k, v in values.items()}
        published = json.loads(outputs[0])
        assert all(published[k] == value for k, value in hashes.items())
        info['normalized_harness_hashes_match_exact_tool'] = True
    else:
        values = json.loads(outputs[0])
    return values, info


def main():
    results = {'runtime': sys.version, 'scope': 'Deterministic committed fixture replay; no CAL_VERIFY/Holdout/provider or full-suite invocation'}
    for number in (32, 33):
        before, before_info = run_exact(number, 'before')
        after, after_info = run_exact(number, 'after')
        assert before_info['tool_sha256'] == after_info['tool_sha256']
        diffs = difference(before, after)
        assert all(d['kind'] == 'ADDED' for d in diffs)
        stripped = deepcopy(after)
        if number == 32:
            for section in ('technical', 'macro'):
                for snapshot in stripped[section]:
                    for key in FOUR:
                        del snapshot[key]
            assert len(diffs) == 92
            assert all(d['path'].split('/')[1] in ('technical', 'macro') and d['path'].split('/')[-1] in FOUR
                       and d['after'] == (None if d['path'].split('/')[-1] in ('available_at', 'input_hash') else []) for d in diffs)
            assert stripped == before
            stripped_hashes = {k: hash_bytes(json.dumps(v, sort_keys=True, default=str).encode()) for k,v in stripped.items()}
            details = {'lineage_additions': 92, 'investment_existing_field_differences': 0,
                       'stripped_equals_before': True, 'stripped_hashes': stripped_hashes}
        else:
            for snapshot in stripped['technical'].values():
                for key in FOUR:
                    del snapshot[key]
            for key in FOUR:
                del stripped['macro'][key]
            report_additions = set(after['reports_sha256']) - set(before['reports_sha256'])
            assert len(report_additions) == 27
            assert all(after['reports_sha256'][k] == v for k,v in before['reports_sha256'].items())
            for key in report_additions:
                del stripped['reports_sha256'][key]
            assert stripped == before
            exact_reconstruction = (json.dumps(stripped, sort_keys=True, ensure_ascii=False, default=str) + '\n').encode()
            assert hash_bytes(exact_reconstruction) == before_info['stdout_sha256']
            lineage_diffs = [d for d in diffs if d['path'].split('/')[1] in ('technical', 'macro')]
            assert len(lineage_diffs) == 44 and len(diffs) == 71
            assert all(d['path'].split('/')[-1] in FOUR and d['after'] == (None if d['path'].split('/')[-1] in ('available_at', 'input_hash') else []) for d in lineage_diffs)
            details = {'lineage_additions': 44, 'added_report_inventory_entries': sorted(report_additions),
                       'unchanged_existing_report_entries': len(before['reports_sha256']),
                       'investment_existing_field_differences': 0, 'stripped_equals_before': True,
                       'exact_reconstructed_stdout_sha256': hash_bytes(exact_reconstruction)}
        results[str(number)] = {'before': before_info, 'after': after_info, 'field_diff_count': len(diffs), **details}
        write_json(f'pr{number}-field-level-diff.json', diffs)
    write_json('independent-offline-fingerprint-replay.json', results)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
