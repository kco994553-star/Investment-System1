"""Offline v3 archive/PIT score diagnostic; never operating ledgers or returns.

Evidence links are explicit dated security identifiers, never CIK/ticker inference.
Sample ranks are recalculated on exactly the common valid totals. They are not
the archived operational ranks, v3 top-500 selection, or 9.1 U-A/U-B ranks.
"""
from collections import Counter
from datetime import date
import math
import re

AXES = ('Q', 'G', 'V')
SCORES = (*AXES, 'total')


def _security_namespace(value):
    return (isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9_.:/-]{0,63}', value) is not None
            and value not in ('CIK', 'TICKER', 'ISSUER', 'COMPANY_ID'))


def _day(value):
    return isinstance(value, str) and date.fromisoformat(value).isoformat() == value


def _identity(link, as_of):
    try:
        if (not all(isinstance(link.get(k), str) and link[k].strip() for k in ('code', 'security_id', 'namespace', 'evidence'))
                or not _security_namespace(link['namespace'])):
            return None
        start, end = link['valid_from'], link.get('valid_to')
        if not _day(start) or (end is not None and not _day(end)):
            return None
        if start > as_of or (end is not None and as_of >= end):
            return None
        return link['namespace'], link['security_id']
    except (KeyError, TypeError, ValueError):
        return None


def _reconstructed_index(rows):
    out = {}
    for r in rows:
        try:
            if not all(isinstance(r[k], str) and r[k].strip() for k in ('security_id', 'namespace', 'calc_version')):
                raise ValueError()
            if not _security_namespace(r['namespace']):
                raise ValueError()
            if not _day(r['as_of']) or set(r['scores']) != set(SCORES):
                raise ValueError()
            if not re.fullmatch('[0-9a-f]{64}', r['input_manifest_sha256']) or not re.fullmatch('[0-9a-f]{40}', r['source_commit']):
                raise ValueError()
            for value in r['scores'].values():
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100):
                    raise ValueError()
            key = (r['namespace'], r['security_id'], r['as_of'], r['calc_version'])
        except (KeyError, TypeError, ValueError):
            raise ValueError('RECONSTRUCTION_ROW_INVALID') from None
        if key in out:
            raise ValueError('DUPLICATE_RECONSTRUCTION_KEY')
        out[key] = r
    return out


def compare_rows(archive_rows, reconstructed_rows, links, *, as_of, calc_version):
    if not _day(as_of) or not isinstance(calc_version, str) or not calc_version:
        raise ValueError('COMPARISON_BASIS_INVALID')
    rows = {k: v for k, v in archive_rows.items() if not k.startswith('TARGET:')}
    active = {}
    for link in links:
        identity = _identity(link, as_of)
        if identity is not None and link['code'] in rows:
            active.setdefault(link['code'], []).append(identity)
    # Multiple active links or two code rows pointing at one ID cannot silently
    # collapse share classes or duplicate a company's archived observation.
    candidates = {code: values[0] for code, values in active.items() if len(values) == 1}
    owners = {}
    for code, values in active.items():
        for identity in values:
            owners.setdefault(identity, set()).add(code)
    identities = {code: identity for code, identity in candidates.items() if len(owners[identity]) == 1}
    reconstructed = _reconstructed_index(reconstructed_rows or [])
    comparisons, unmatched = [], []
    for code, row in sorted(rows.items()):
        identity = identities.get(code)
        reason = None
        if identity is None:
            reason = 'SECURITY_IDENTITY_NOT_LINKED' if code not in active else 'SECURITY_IDENTITY_AMBIGUOUS'
        else:
            key = (*identity, as_of, calc_version)
            other = reconstructed.get(key)
            if other is None:
                matches = [k for k in reconstructed if k[:2] == identity]
                reason = ('PIT_RECONSTRUCTION_NOT_LINKED' if not matches else
                          'AS_OF_MISMATCH' if not any(k[2] == as_of for k in matches) else 'CALC_VERSION_MISMATCH')
        if reason:
            unmatched.append({'code': code, 'reason': reason})
            continue
        before = {a: row['axes'][a]['score'] for a in AXES}
        before['total'] = row['total']
        after = other['scores']
        deltas = {a: None if before[a] is None or after[a] is None else after[a] - before[a] for a in SCORES}
        comparisons.append({'code': code, 'namespace': identity[0], 'security_id': identity[1],
                            'as_of': as_of, 'calc_version': calc_version, 'archived_scores': before,
                            'reconstructed_scores': dict(after), 'score_deltas': deltas,
                            'null_reasons': {a: 'ARCHIVED_OR_RECONSTRUCTED_SCORE_MISSING' for a, v in deltas.items() if v is None},
                            'sample_rank_before': None, 'sample_rank_after': None, 'sample_rank_delta': None,
                            'input_manifest_sha256': other['input_manifest_sha256'], 'reconstruction_commit': other['source_commit']})
    valid = [r for r in comparisons if r['score_deltas']['total'] is not None]
    for name, field in (('before', 'archived_scores'), ('after', 'reconstructed_scores')):
        ordered = sorted(valid, key=lambda r: (-r[field]['total'], r['namespace'], r['security_id']))
        for rank, r in enumerate(ordered, 1):
            r['sample_rank_' + name] = rank
    for r in valid:
        r['sample_rank_delta'] = r['sample_rank_after'] - r['sample_rank_before']
    missing = []
    if len(identities) < len(rows):
        missing.append('DATED_SECURITY_IDENTITY_LINKS')
    if not reconstructed:
        missing.append('PIT_RECONSTRUCTED_QGV')
    return {'schema_version': 'fv3-archive-comparison/1', 'result_kind': 'SAMPLE_DIAGNOSTIC',
            'computation_status': 'COMPUTED' if comparisons else 'NOT_COMPUTED',
            'as_of': as_of, 'calc_version': calc_version, 'counts': {
                'archive_codes': len(rows), 'identity_linked': len(identities), 'reconstructed_rows': len(reconstructed),
                'matched_securities': len(comparisons), 'comparable_total': len(valid),
                'comparable_axes': {a: sum(r['score_deltas'][a] is not None for r in comparisons) for a in AXES}},
            'comparisons': comparisons, 'unmatched': unmatched,
            'missing_inputs': missing, 'reason_counts': dict(sorted(Counter(r['reason'] for r in unmatched).items())),
            'rank_scope': 'COMMON_VALID_SAMPLE_ONLY', 'rank_valid_n': len(valid),
            'historical_whole_market_denominator': None, 'performance': None,
            'pit_reconstruction_certified': False, 'operating_ledger_changed': False,
            'limitations': ['Comparison checks evidence fields, not the underlying PIT input manifest contents.',
                            'v3 PIT issuer top-500 and 9.1 U-A/U-B/annual execution are separate.',
                            'Stored operational ranks are not compared across different populations.']}
