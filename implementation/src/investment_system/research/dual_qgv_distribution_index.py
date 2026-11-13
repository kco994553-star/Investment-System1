"""Pinned, bounded bin routing over saved distribution files. No score calculation."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import re
from .dual_qgv import json_bytes
from .dual_qgv_delivery import MAX_BYTES, require
from .dual_qgv_distribution import STORED
from .sector_qgv import digest


def sha(data):
    return hashlib.sha256(data).hexdigest()


def descriptor(path, data):
    return dict(path=path, size=len(data), sha256=sha(data))


def validate_distribution(files, expected_manifest_sha256):
    """Validate a complete batch against an independently pinned manifest.

    This validates saved delivery/partition integrity, not the original financial
    inputs or scoring implementation. Missing shards never become empty bins.
    """
    require('distribution-manifest.json' in files, 'MANIFEST_MISSING')
    raw = files['distribution-manifest.json']
    require(sha(raw) == expected_manifest_sha256, 'MANIFEST_PIN')
    manifest = json.loads(raw)
    require(manifest['schema_version'] == 'qgv-dual-factor-distribution-manifest/1', 'MANIFEST_SCHEMA')
    listed = {f['path']: f for f in manifest['files']}
    require(len(listed) == len(manifest['files']), 'DUPLICATE_FILE')
    require(set(files) == set(listed) | {'distribution-manifest.json'}, 'FILE_SET')
    for name, f in listed.items():
        require(re.fullmatch(r'distribution-(index|[0-9]{3})\.json', name) is not None, 'FILE_PATH')
        require(len(files[name]) <= MAX_BYTES and descriptor(name, files[name]) == f, 'FILE_HASH')
    idx = json.loads(files['distribution-index.json'])
    require(idx['schema_version'] == 'qgv-dual-factor-distribution/1', 'INDEX_SCHEMA')
    require(idx['display_policy'] == manifest['display_policy'] == STORED, 'STORED_POLICY')
    require(idx['scope'] == manifest['scope'] and idx['data_kind'] == manifest['data_kind'], 'SCOPE')
    require(idx['minimum_reference_score_n'] == 20 and idx['minimum_stored_evaluation_decile_n'] == 10, 'MINIMUM_POLICY')
    require(idx['rank_policy'] == 'UNROUNDED_FACTOR_SCORE_DESC_COMPANY_ID_ASC_ORDINAL', 'RANK_POLICY')
    ids = [r['company_id'] for r in idx['companies']]
    require(len(set(ids)) == len(ids), 'COMPANY_DUPLICATE')
    groups = {g['group_id']: g for g in idx['groups']}
    require(len(groups) == len(idx['groups']), 'GROUP_DUPLICATE')
    rows, locations = defaultdict(list), defaultdict(dict)
    for name in sorted(listed):
        if name == 'distribution-index.json':
            continue
        part = json.loads(files[name])
        require(part['schema_version'] == 'qgv-dual-factor-distribution-part/1', 'PART_SCHEMA')
        for chunk in part['parts']:
            gid = chunk['group_id']
            require(gid in groups, 'UNKNOWN_GROUP')
            for row in chunk['rows']:
                require(row['company_id'] not in locations[gid], 'GROUP_MEMBERS')
                locations[gid][row['company_id']] = name
                rows[gid].append(row)
    source_results = {k:dict(result_hash=b['result_hash'], sha256=b['source_result_sha256']) for k,b in idx['boards'].items()}
    require(source_results == manifest['source_results'], 'SOURCE_RESULT_CONTEXT')
    populations = [b['evaluation_population'] for b in idx['boards'].values()]
    require(populations and all(p == populations[0] for p in populations) and populations[0]['code_rows'] == len(ids), 'EVALUATION_CONTEXT')
    factor_members = defaultdict(set)
    for gid, g in groups.items():
        require(gid == g['board']+'|'+g['ranking_scope']+'|'+g['variant_id'] and g['board'] in idx['boards'], 'GROUP_ID')
        require(g['ranking_scope'] == 'COMMON' if g['board'] != 'S1' else g['ranking_scope'].startswith('SECTOR|'), 'GROUP_SCOPE')
        members = {r['company_id'] for r in rows[gid]}
        require(len(rows[gid]) == g['evaluation_rows_in_scope'] and members <= set(ids), 'GROUP_MEMBERS')
        require(set(g['files']) == set(locations[gid].values()) and len(g['files']) == len(set(g['files'])), 'GROUP_FILES')
        key = (g['board'], g['variant_id'])
        require(not (factor_members[key] & members), 'MULTIPLE_SCOPES')
        factor_members[key].update(members)
        valid = [r for r in rows[gid] if r['score'] is not None]
        n = len(valid)
        require(n == g['evaluation_valid_n'], 'EVALUATION_N')
        require(sorted(r['rank'] for r in valid) == list(range(1, n+1)) and all(r['rank_n'] == n for r in valid), 'RANK_INTEGRITY')
        require(not valid or g['reference_valid_n'] >= 20, 'REFERENCE_MINIMUM')
        ordered = sorted(valid, key=lambda r:r['rank'])
        require(ordered == sorted(valid, key=lambda r:(-r['score'], r['company_id'])), 'STORED_ORDER')
        for r in rows[gid]:
            require(r['decile'] == r['stored_decile'], 'DECILE_PARTITION')
            if r['score'] is None:
                require(r['rank'] is None and r['decile'] is None, 'DECILE_PARTITION')
            elif n < 10:
                require(r['decile'] is None and r['decile_status'] == 'SAMPLE_LT_10', 'DECILE_PARTITION')
            else:
                require(type(r['decile']) is int and 1 <= r['decile'] <= 10 and r['decile_status'] == 'VALID', 'DECILE_PARTITION')
        ds = [r['decile'] for r in ordered] if n >= 10 else []
        require(ds == sorted(ds, reverse=True), 'DECILE_ORDER')
        counts = Counter(r['decile'] for r in rows[gid] if r['decile'] is not None)
        require(g['bins'] == [dict(decile=d, count=counts[d]) for d in range(10,0,-1)], 'BIN_COUNTS')
        require(sum(counts.values()) == (n if n >= 10 else 0), 'DECILE_PARTITION')
        if n >= 10:
            require(counts[10] == counts[1] == n//10, 'EXTREME_BIN_COUNT')
        reasons = Counter(r['decile_status'] for r in rows[gid] if r['decile'] is None)
        require(g['unavailable_count'] == sum(reasons.values()) and g['unavailable_reasons'] == dict(reasons), 'UNAVAILABLE_COUNTS')
        require(g['comparison_group'] == dict(role='EVALUATION_VALID',unit='EVALUATION_CODE_ROW',n=n,members_hash=digest(sorted(r['company_id'] for r in valid))), 'COMPARISON_CONTEXT')
    require(all(m == set(ids) for m in factor_members.values()), 'FACTOR_COVERAGE')
    return idx, rows, locations, listed


def bin_index_artifacts(files, *, expected_manifest_sha256, max_bytes=MAX_BYTES):
    """Small routing companion. Reuses member file bytes; never writes them again."""
    require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, 'SIZE_LIMIT')
    idx, rows, locations, listed = validate_distribution(files, expected_manifest_sha256)
    out, batch, routes = {}, [], []
    def payload(items):return dict(schema_version='qgv-dual-factor-bins-part/1', groups=items)
    def flush():
        if batch:
            name = f'bins-{len(out):03}.json'
            out[name] = payload(batch[:])
            for g in batch:routes.append(dict(group_id=g['group_id'], path=name))
            batch.clear()
    for group in idx['groups']:
        g = deepcopy(group)
        for b in g['bins']:
            members = sorted((r for r in rows[g['group_id']] if r['decile'] == b['decile']),key=lambda r:r['rank'])
            b.update(first_rank=members[0]['rank'] if members else None,
                     last_rank=members[-1]['rank'] if members else None,
                     members_hash=digest([r['company_id'] for r in members]),
                     member_files=[deepcopy(listed[p]) for p in sorted({locations[g['group_id']][r['company_id']] for r in members})])
        g.update(binned_evaluation_n=sum(b['count'] for b in g['bins']),
                 partition_status='COMPLETE' if g['evaluation_valid_n']>=10 else 'SAMPLE_LT_10' if g['evaluation_valid_n'] else 'NO_VALID_SCORE')
        require(len(json_bytes(payload([g]))) <= max_bytes, 'GROUP_SIZE')
        if len(json_bytes(payload(batch+[g]))) > max_bytes:flush()
        batch.append(g)
    flush()
    out['bin-index.json'] = dict(schema_version='qgv-dual-factor-bins/1', scope=idx['scope'], data_kind=idx['data_kind'],
        source_distribution_manifest=descriptor('distribution-manifest.json', files['distribution-manifest.json']),
        source_index=deepcopy(listed['distribution-index.json']), display_policy=STORED,
        boards=deepcopy(idx['boards']), bands=deepcopy(idx['bands']), groups=routes,
        rank_policy=idx['rank_policy'], minimum_reference_score_n=20, minimum_stored_evaluation_decile_n=10,
        tie_policy='PRESERVE_STORED_ORDINAL_COMPANY_ID_BOUNDARIES',
        remainder_policy='D10_D1_FLOOR_N_OVER_10;MIDDLE_REMAINDER_D9_TO_D2',
        new_score_calculations=0, additional_factor_score_contribution=0, filter_changes_population=False,
        whole_market_denominator=None, whole_market_coverage=None)
    out['bin-manifest.json'] = dict(schema_version='qgv-dual-factor-bins-manifest/1',
        scope=idx['scope'], data_kind=idx['data_kind'], source_manifest_sha256=expected_manifest_sha256,
        files=[descriptor(k,json_bytes(v)) for k,v in sorted(out.items())])
    require(all(len(json_bytes(v)) <= max_bytes for v in out.values()), 'OUTPUT_SIZE')
    return out


def main(argv=None):
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--source-manifest-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args(argv)
    require(not any(p.is_symlink() or not p.is_file() for p in args.source_dir.iterdir()), 'SOURCE_ENTRY')
    files = {p.name:p.read_bytes() for p in args.source_dir.iterdir()}
    out = bin_index_artifacts(files, expected_manifest_sha256=args.source_manifest_sha256)
    if out['bin-index.json']['data_kind'] != 'SYNTHETIC':
        dest = args.output_dir.resolve()
        require(not any((p/'.git').exists() for p in (dest,*dest.parents)), 'PRIVATE_OUTPUT_IN_CHECKOUT')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name,value in out.items():(args.output_dir/name).write_bytes(json_bytes(value))
    print(json.dumps(dict(status='ALL_BINS_VALIDATED',groups=len(out['bin-index.json']['groups']),files=len(out),new_score_calculations=0)))


if __name__ == '__main__':
    import sys
    try:main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        code=str(error) if isinstance(error,ValueError) and re.fullmatch(r'[A-Z_]+',str(error)) else type(error).__name__
        print(json.dumps(dict(status='FAILED',error=code)),file=sys.stderr)
        raise SystemExit(1)
