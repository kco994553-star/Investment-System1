"""stage_private_qgv333_qinput.py (owner 2026-11-13 「3/3/3 화면 연결 우선」 §1, §3): the producer's Q input recovery diagnostic
summary and comparison staged byte for byte under classification/dual-333/qinput/ with Main's qgv-333-q-input-delivery/1 index,
only when pinned, consistent, and chained to the staged EPS step; the review clocks come from the archive's pinned snapshots; the
calculation time absent stays null; every refusal keeps the existing copy. The handoff is test-made (the producer's shape, made-up counts)."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_qgv333_qinput as tool  # noqa: E402

DAY, OLD, NEW = '2026-11-04', '2026-11-04T02:29:35Z', '2026-11-13T11:57:04+00:00'
MODELS = ('U2-333', 'U1-333', 'S1-333')
SCOPES = ('operating504', 'held1057')


def _b(doc) -> bytes:
    return (json.dumps(doc) + '\n').encode()


def _ctx(**over):
    c = {'schema_version': 'sector-qgv-review-context/1', 'original_snapshot_hash': 'a' * 64, 'valuation_date': DAY, 'input_cutoff': NEW,
         'reviewed_at': NEW, 'reviews': [{'claim_id': 'x'}], 'original_input_cutoff': OLD, 'result_kind': 'RETROSPECTIVE_REVIEW',
         'historical_system_pit_complete': False}
    c.update(over)
    return c


def _docs():
    diag = {s: {'denominator_issuers': 3, 'code_rows': 3, 'primary_q_causes': {'Q_AVAILABLE': 2, 'ACCOUNTING_NOT_APPLICABLE': 1},
                'gate_diagnostic': {'DECISION_KNOWN_NOT_NECESSARILY_PASS': 3}, 'official_input_linkage': {'PERCENTILE_LINKED': 2, 'PERCENTILE_NOT_LINKED': 1},
                'whole_market_denominator': None} for s in SCOPES}
    comp = {s: {m: {'stages': {'Q': {'before': 1, 'after': 2}}, 'before_result_hash': 'c' * 64, 'after_result_hash': 'e' * 64,
                    'before_bindings': {'evaluation': {'valuation_date': DAY, 'as_of': OLD}},
                    'after_bindings': {'evaluation': {'valuation_date': DAY, 'as_of': NEW}}} for m in MODELS} for s in SCOPES}
    return {'diagnostic-summary.json': diag, 'comparison.json': comp, 'preparation-summary.json': {'as_of': NEW, 'source_snapshots_reused': True},
            'verification.json': {'passed': True, 'checked_at': '2026-11-13T12:00:39+00:00'}, 'contexts': {s: _ctx() for s in tool.SNAPSHOTS}}


def _handoff(tmp_path, edit=None, eps_after='c'):
    d = tmp_path / 'h'
    d.mkdir(parents=True)
    docs = _docs()
    if edit:
        edit(docs)
    members, buf = [], io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for snap, ctx in docs.pop('contexts').items():
            b = _b({'snapshot_id': snap, 'rows': [], 'review_context': ctx})
            info = tarfile.TarInfo('./transformed/' + snap + '/snapshot.json')
            info.size = len(b)
            tar.addfile(info, io.BytesIO(b))
            members.append({'path': 'transformed/' + snap + '/snapshot.json', 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    out = {n: _b(doc) for n, doc in docs.items()}
    out['bundle-manifest.json'] = _b({'schema_version': 'qgv-q-input-private-bundle/1', 'producer_sha': '1' * 40, 'execution_sha': '2' * 40, 'files': members})
    out['private-run-bundle.tar.gz'] = buf.getvalue()
    files = []
    for name, b in out.items():
        (d / name).write_bytes(b)
        files.append({'path': name, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    m = {'schema_version': 'qgv-q-input-handoff/1', 'visibility': 'PRIVATE_RESEARCH', 'path': 'handoffs/test', 'producer_sha': '1' * 40,
         'execution_sha': '2' * 40, 'files': files}
    raw = _b(m)
    (d / 'handoff-manifest.json').write_bytes(raw)
    data = tmp_path / 'data'
    eps = data / 'classification' / 'dual-333' / 'eps'
    eps.mkdir(parents=True)
    (eps / 'eps-index.json').write_bytes(b'{}\n')
    (eps / 'run-comparison.json').write_bytes(_b({s: {m: {'after_result_hash': eps_after * 64} for m in MODELS} for s in SCOPES}))
    return d, hashlib.sha256(raw).hexdigest(), data


def _main(h, pin, data):
    return tool.main(['--handoff', str(h), '--handoff-manifest-sha256', pin, '--data-dir', str(data)])


def test_stages_the_two_files_byte_for_byte_with_the_clocks_and_chain(tmp_path, capsys):
    h, pin, data = _handoff(tmp_path)
    assert _main(h, pin, data) == 0
    out = data / 'classification' / 'dual-333' / 'qinput'
    assert sorted(p.name for p in out.iterdir()) == ['comparison.json', 'diagnostic-summary.json', 'q-index.json']
    for n in ('comparison.json', 'diagnostic-summary.json'):
        assert (out / n).read_bytes() == (h / n).read_bytes(), 'byte for byte'
    idx = json.loads((out / 'q-index.json').read_text())
    assert idx['schema_version'] == 'qgv-333-q-input-delivery/1' and idx['result_delivery'] is None
    assert idx['clocks'] == {'valuation_date': DAY, 'original_input_cutoff': OLD, 'input_cutoff': NEW, 'reviewed_at': NEW,
                             'producer_verified_at': '2026-11-13T12:00:39+00:00', 'calculated_at': None}, 'calculation time absent stays null'
    assert idx['result_kind'] == 'RETROSPECTIVE_REVIEW' and idx['historical_system_pit_complete'] is False
    assert idx['review_records'] == {s: 1 for s in tool.SNAPSHOTS} and idx['source_snapshots_reused'] is True
    assert idx['continues']['boards'] == 6
    assert idx['continues']['eps_comparison_sha256'] == hashlib.sha256((data / 'classification/dual-333/eps/run-comparison.json').read_bytes()).hexdigest()
    line = capsys.readouterr().out
    assert line.startswith('STAGE_PRIVATE_QGV333_QINPUT index sha256=') and 'result_delivery=none' in line and NEW not in line


@pytest.mark.parametrize('code,edit', [
    ('DIAGNOSTIC_SUM:held1057.gate_diagnostic', lambda d: d['diagnostic-summary.json']['held1057']['gate_diagnostic'].update(DECISION_KNOWN_NOT_NECESSARILY_PASS=2)),
    ('DIAGNOSTIC_SUM:operating504.primary_q_causes', lambda d: d['diagnostic-summary.json']['operating504']['primary_q_causes'].pop('ACCOUNTING_NOT_APPLICABLE')),
    ('DIAGNOSTIC_SCHEMA:operating504', lambda d: d['diagnostic-summary.json']['operating504'].update(whole_market_denominator=501)),
    ('Q_COUNT_DISAGREE:held1057.U1-333', lambda d: d['comparison.json']['held1057']['U1-333']['stages']['Q'].update(after=3)),
    ('DATE_MISMATCH:operating504.S1-333', lambda d: d['comparison.json']['operating504']['S1-333']['after_bindings']['evaluation'].update(as_of=OLD)),
    ('REVIEW_CONTEXT_DISAGREE', lambda d: d['contexts']['held'].update(reviewed_at='2026-11-14T00:00:00Z')),
    ('REVIEW_CONTEXT_KIND', lambda d: [c.update(historical_system_pit_complete=True) for c in d['contexts'].values()]),
    ('REVIEW_CONTEXT:transformed/operating/snapshot.json', lambda d: d['contexts']['operating'].update(schema_version='sector-qgv-review-context/2')),
    ('PREPARATION_SCHEMA', lambda d: d['preparation-summary.json'].update(as_of=OLD)),
    ('COMPARISON_SCHEMA', lambda d: d['comparison.json']['held1057'].pop('S1-333')),
])
def test_refusals_keep_the_existing_copy(tmp_path, capsys, code, edit):
    h, pin, data = _handoff(tmp_path, edit)
    keep = data / 'classification' / 'dual-333' / 'qinput'
    keep.mkdir()
    (keep / 'q-index.json').write_bytes(b'old')
    assert _main(h, pin, data) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_QGV333_QINPUT refused=' + code
    assert (keep / 'q-index.json').read_bytes() == b'old' and sorted(p.name for p in keep.iterdir()) == ['q-index.json']


def test_the_chain_to_the_staged_eps_step_and_the_pins(tmp_path, capsys):
    h, pin, data = _handoff(tmp_path, eps_after='9')
    assert _main(h, pin, data) == 1 and 'refused=CHAIN_MISMATCH:operating504.U2-333' in capsys.readouterr().out, 'another EPS step: never mixed'
    h2, pin2, data2 = _handoff(tmp_path / 'b')
    (data2 / 'classification' / 'dual-333' / 'eps' / 'eps-index.json').unlink()
    assert _main(h2, pin2, data2) == 1 and 'refused=EPS_STEP_NOT_STAGED' in capsys.readouterr().out
    assert _main(h2, '0' * 64, data2) == 1
    h3, pin3, data3 = _handoff(tmp_path / 'c')
    (h3 / 'comparison.json').write_bytes((h3 / 'comparison.json').read_bytes() + b' ')
    assert _main(h3, pin3, data3) == 1 and 'refused=FILE_MISMATCH:comparison.json' in capsys.readouterr().out
    assert _main(h3, pin3, ROOT / 'x') == 1 and 'DATA_DIR_INSIDE_PUBLIC_REPOSITORY' in capsys.readouterr().out


def test_a_snapshot_not_matching_the_bundle_manifest_is_refused(tmp_path, capsys, monkeypatch):
    h, pin, data = _handoff(tmp_path)
    real = tool._contexts

    def tampered(archive, members):
        members = {k: {**v, 'sha256': '0' * 64} if k.endswith('held/snapshot.json') else v for k, v in members.items()}
        return real(archive, members)
    monkeypatch.setattr(tool, '_contexts', tampered)
    assert _main(h, pin, data) == 1 and 'refused=SNAPSHOT_MISMATCH:transformed/held/snapshot.json' in capsys.readouterr().out
