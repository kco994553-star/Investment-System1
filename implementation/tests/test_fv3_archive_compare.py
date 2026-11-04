import pytest
import json
from pathlib import Path
import subprocess
import sys
from investment_system.research import fv3_archive_compare as c


def archive_row(score):
    return {'axes': {a: {'score': score} for a in 'QGV'}, 'total': score, 'rank': 1, 'cik': '0000000001'}


def link(code, sid):
    return {'code': code, 'security_id': sid, 'namespace': 'TEST_SECURITY', 'valid_from': '2018-01-01',
            'valid_to': '2019-01-01', 'evidence': 'synthetic dated security record'}


def reconstructed(sid, score, **extra):
    return {'security_id': sid, 'namespace': 'TEST_SECURITY', 'as_of': '2018-02-16', 'calc_version': 'calc/test',
            'scores': {a: score for a in ('Q', 'G', 'V', 'total')}, 'input_manifest_sha256': 'a' * 64,
            'source_commit': 'b' * 40, **extra}


def compare(rows, recon, links):
    return c.compare_rows(rows, recon, links, as_of='2018-02-16', calc_version='calc/test')


def test_same_cik_different_securities_are_compared_separately_on_common_sample():
    result = compare({'NYSE:A': archive_row(80), 'NYSE:B': archive_row(60)},
                     [reconstructed('one', 50), reconstructed('two', 70)], [link('NYSE:A', 'one'), link('NYSE:B', 'two')])
    assert result['counts']['matched_securities'] == 2
    assert result['counts']['comparable_total'] == 2
    assert [r['score_deltas']['total'] for r in result['comparisons']] == [-30, 10]
    assert [r['sample_rank_delta'] for r in result['comparisons']] == [1, -1]
    assert result['rank_scope'] == 'COMMON_VALID_SAMPLE_ONLY'


def test_unlinked_archive_is_zero_comparisons_not_zero_scores():
    result = compare({'NYSE:A': archive_row(80)}, None, [])
    assert result['counts']['identity_linked'] == 0
    assert result['counts']['comparable_total'] == 0
    assert result['comparisons'] == []
    assert result['missing_inputs'] == ['DATED_SECURITY_IDENTITY_LINKS', 'PIT_RECONSTRUCTED_QGV']
    assert result['historical_whole_market_denominator'] is None


@pytest.mark.parametrize('extra,reason', [({'as_of': '2018-02-15'}, 'AS_OF_MISMATCH'), ({'calc_version': 'calc/other'}, 'CALC_VERSION_MISMATCH')])
def test_date_and_version_mismatches_cannot_be_compared(extra, reason):
    result = compare({'NYSE:A': archive_row(80)}, [reconstructed('one', 70, **extra)], [link('NYSE:A', 'one')])
    assert result['counts']['comparable_total'] == 0
    assert result['unmatched'][0]['reason'] == reason


def test_expired_or_issuer_links_do_not_become_fixed_security_ids():
    for changed in ({'valid_to': '2018-02-16'}, {'namespace': 'CIK'}):
        result = compare({'NYSE:A': archive_row(80)}, [], [{**link('NYSE:A', 'one'), **changed}])
        assert result['counts']['identity_linked'] == 0


def test_missing_axis_and_total_keep_null_and_duplicate_reconstruction_is_refused():
    r = reconstructed('one', 70)
    r['scores']['V'] = None
    r['scores']['total'] = None
    result = compare({'NYSE:A': archive_row(80)}, [r], [link('NYSE:A', 'one')])
    assert result['comparisons'][0]['score_deltas']['V'] is None
    assert result['comparisons'][0]['sample_rank_delta'] is None
    assert result['counts']['comparable_axes'] == {'Q': 1, 'G': 1, 'V': 0}
    with pytest.raises(ValueError, match='DUPLICATE_RECONSTRUCTION_KEY'):
        compare({'NYSE:A': archive_row(80)}, [r, r], [link('NYSE:A', 'one')])


def test_cli_archive_only_completes_with_explicit_missing_inputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / 'tests/fixtures/qgv_official_vectors_v1.json').read_text())
    archive = tmp_path / 'archive.json'
    archive.write_text(fixture['base_text'])
    out = tmp_path / 'comparison.json'
    proc = subprocess.run([sys.executable, str(root / 'tools/fv3_archive_compare.py'),
                           '--archive', str(archive), '--output', str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(out.read_text())
    assert result['counts']['archive_codes'] == 30
    assert result['counts']['comparable_total'] == 0
    assert result['computation_status'] == 'NOT_COMPUTED'
    assert result['missing_inputs'] == ['DATED_SECURITY_IDENTITY_LINKS', 'PIT_RECONSTRUCTED_QGV']


def test_identity_owned_by_an_ambiguous_code_cannot_leak_to_another_code():
    result = compare({'NYSE:A': archive_row(80), 'NYSE:B': archive_row(60)},
                     [reconstructed('one', 70)],
                     [link('NYSE:A', 'one'), link('NYSE:A', 'two'), link('NYSE:B', 'one')])
    assert result['counts']['identity_linked'] == 0
    assert result['counts']['matched_securities'] == 0
    assert result['reason_counts'] == {'SECURITY_IDENTITY_AMBIGUOUS': 2}


@pytest.mark.parametrize('namespace', [' CIK', 'CIK ', '\tTICKER', 'TICKER\n', 'ISSUER ', ' COMPANY_ID '])
def test_noncanonical_reserved_namespaces_never_establish_security_identity(namespace):
    bad = {**link('NYSE:A', 'one'), 'namespace': namespace}
    result = compare({'NYSE:A': archive_row(80)}, [], [bad])
    assert result['counts']['identity_linked'] == 0
    with pytest.raises(ValueError, match='RECONSTRUCTION_ROW_INVALID'):
        compare({'NYSE:A': archive_row(80)}, [reconstructed('one', 70, namespace=namespace)], [bad])
