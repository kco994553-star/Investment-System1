"""stage_private_dual_333_switch.py (owner 2026-11-13 「새 Q 결과 전환·인수 상태 정리」 §1): a new 3/3/3 result version is switched in one
step only when the delivery, the evaluation / reference input basis, the distribution and the all-bin routing all pass their own
staging checks and name the same result version; every refusal keeps the existing, working bundle byte for byte. The bundle is
test-made by the shared node fixture (tools/web_app_dual_fixture.js: q333 held1057 + projection proof + distribution + bins)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_333_switch as tool  # noqa: E402

GEN = r"""const DF=require(process.argv[1]),fs=require('fs'),path=require('path');const out=process.argv[2],edit=process.argv[3];
let d=DF.q333('held1057');if(edit==='other_result')d=DF.q333('held1057','unknown-gate');
const base=DF.q333('held1057'),dist=DF.distribution(base),bins=DF.bins(dist);
const w=(dir,files)=>{fs.mkdirSync(dir,{recursive:true});for(const[k,v]of Object.entries(files))fs.writeFileSync(path.join(dir,k),v);};
w(path.join(out,'delivery'),d.files);fs.writeFileSync(path.join(out,'input-lineage.json'),DF.lineage());
w(path.join(out,'distribution'),Object.fromEntries(Object.entries(dist).filter(([k])=>k.startsWith('distribution'))));
w(path.join(out,'bins'),Object.fromEntries(Object.entries(bins).filter(([k])=>k.startsWith('bin'))));"""


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _bundle(tmp_path, name='new', edit=''):
    out = tmp_path / name
    subprocess.run(['node', '-e', GEN, str(ROOT / 'tools' / 'web_app_dual_fixture.js'), str(out), edit], check=True, timeout=60)
    return out


def _data(tmp_path, bundle):
    b = next(iter(json.loads((bundle / 'delivery' / 'summary.json').read_text())['boards'].values()))
    ev, ref = b['evaluation_population'], b['reference_population']
    ctx = {'valuation_date': ev['valuation_date'], 'result_identity': {'input_hash': ref['input_hash']},
           'population': {'id': ev['id'], 'version': ev['version'], 'members_hash': ev['members_hash'], 'denominator': ev['code_rows']}}
    data = tmp_path / 'data'
    (data / 'classification' / 'expanded').mkdir(parents=True, exist_ok=True)
    (data / 'classification' / 'expanded' / 'coverage.json').write_text(json.dumps({'scopes': {'held_financial_subsample': {'context': ctx}}}))
    return data


def _args(bundle, data, **over):
    a = {'--scope': 'held1057', '--data-dir': data, '--delivery': bundle / 'delivery', '--manifest-sha256': _sha(bundle / 'delivery' / 'manifest.json'),
         '--distribution': bundle / 'distribution', '--distribution-sha256': _sha(bundle / 'distribution' / 'distribution-manifest.json'),
         '--bins': bundle / 'bins', '--bins-sha256': _sha(bundle / 'bins' / 'bin-manifest.json'),
         '--input-lineage': bundle / 'input-lineage.json', '--input-lineage-sha256': _sha(bundle / 'input-lineage.json')}
    a.update(over)
    return [x for k, v in a.items() if v is not None for x in (k, str(v))]


def _tree(d: Path) -> dict:
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob('*')) if p.is_file()}


def test_a_complete_bundle_switches_in_one_step_with_its_record(tmp_path, capsys):
    b = _bundle(tmp_path)
    data = _data(tmp_path, b)
    assert tool.main(_args(b, data)) == 0, capsys.readouterr().out
    out = data / 'classification' / 'dual-333' / 'held1057'
    names = set(_tree(out))
    assert {'manifest.json', 'summary.json', 'input-lineage.json', 'switch.json', 'distribution/distribution-manifest.json', 'bins/bin-manifest.json'} <= names
    for p in (b / 'delivery').iterdir():
        assert (out / p.name).read_bytes() == p.read_bytes(), 'byte for byte'
    rec = json.loads((out / 'switch.json').read_text())
    summary = json.loads((out / 'summary.json').read_text())['boards']
    assert rec['schema_version'] == 'qgv-dual-333-switch/1' and rec['results'] == {k: v['result_hash'] for k, v in summary.items()}
    assert rec['replaced_results'] is None and rec['new_score_calculations'] == 0
    line = capsys.readouterr().out
    assert line.startswith('STAGE_PRIVATE_DUAL_333_SWITCH scope=held1057 switched ') and 'replaced=none' in line
    assert not any(p.name.startswith('.switch-') for p in data.iterdir()), 'the shadow copy is removed'
    # the next switch names what it replaces
    assert tool.main(_args(b, data)) == 0
    assert json.loads((out / 'switch.json').read_text())['replaced_results'] == rec['results']


@pytest.mark.parametrize('case,code', [
    ('other_result', 'DISTRIBUTION:BOARD_MISMATCH:U2-333'),
    ('no_bins', 'BINS:MANIFEST_PIN_MISMATCH'),
    ('no_proof', 'INPUT_PROOF_REQUIRED'),
    ('anchor_for_held', 'INPUT_PROOF_REQUIRED'),
    ('bad_pin', 'QGV:MANIFEST_PIN_MISMATCH'),
    ('other_distribution_for_bins', 'BINS:SOURCE_DISTRIBUTION_MISMATCH'),
])
def test_refusals_keep_the_existing_bundle(tmp_path, capsys, case, code):
    good = _bundle(tmp_path, 'good')
    data = _data(tmp_path, good)
    assert tool.main(_args(good, data)) == 0
    keep = _tree(data / 'classification' / 'dual-333' / 'held1057')
    capsys.readouterr()
    b = _bundle(tmp_path, 'new', 'other_result' if case == 'other_result' else '')
    over = {}
    if case == 'no_bins':
        over = {'--bins-sha256': '0' * 64}
    elif case == 'no_proof':
        over = {'--input-lineage': None, '--input-lineage-sha256': None}
    elif case == 'anchor_for_held':
        over = {'--anchor': b / 'input-lineage.json', '--anchor-sha256': '1' * 64}
    elif case == 'bad_pin':
        over = {'--manifest-sha256': '2' * 64}
    elif case == 'other_distribution_for_bins':
        m = json.loads((b / 'bins' / 'bin-manifest.json').read_text())
        m['source_manifest_sha256'] = '3' * 64
        (b / 'bins' / 'bin-manifest.json').write_text(json.dumps(m))
        over = {'--bins-sha256': _sha(b / 'bins' / 'bin-manifest.json')}
    assert tool.main(_args(b, data, **over)) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_DUAL_333_SWITCH refused=' + code + ' kept=existing'
    assert _tree(data / 'classification' / 'dual-333' / 'held1057') == keep, 'the working bundle is unchanged'
    assert not any(p.name.startswith('.switch-') for p in data.iterdir())


def test_same_version_checks_beyond_the_per_part_tools(tmp_path, capsys):
    b = _bundle(tmp_path)
    data = _data(tmp_path, b)
    assert tool.main(_args(b, data)) == 0
    d = data / 'classification' / 'dual-333' / 'held1057'
    assert tool._same_version(d, 'held1057')['code_rows'] == 3
    di = json.loads((d / 'distribution' / 'distribution-index.json').read_text())
    k = next(iter(di['boards']))
    di['boards'][k]['result_hash'] = 'f' * 64
    (d / 'distribution' / 'distribution-index.json').write_text(json.dumps(di))
    with pytest.raises(tool.SwitchError, match='DISTRIBUTION_OTHER_RESULT'):
        tool._same_version(d, 'held1057')
    capsys.readouterr()
    assert tool.main(_args(b, ROOT / 'x')) == 1 and 'refused=DATA_DIR_INSIDE_PUBLIC_REPOSITORY' in capsys.readouterr().out


# A new input version with Codex's two input anchors (qgv-dual-input-anchors/1, #534 fe29867c): the trust chain goes to an EARLIER
# pinned handoff (handoff-manifest -> bundle-manifest -> both source snapshots), the anchors bind every board and the index; the clock
# record keeps calculated_at null with its reason. Test-made preserved handoff; the anchors come from the shared node fixture.
GEN_ANCHORS = r"""const DF=require(process.argv[1]),fs=require('fs'),path=require('path');const out=process.argv[2];
const d=DF.q333('held1057');fs.writeFileSync(path.join(out,'input-anchors.json'),DF.inputAnchors(d));fs.writeFileSync(path.join(out,'delivery-clocks.json'),DF.clocks());"""


def _preserved(tmp_path, bundle, edit=None):
    subprocess.run(['node', '-e', GEN_ANCHORS, str(ROOT / 'tools' / 'web_app_dual_fixture.js'), str(bundle)], check=True, timeout=60)
    x = json.loads((bundle / 'input-anchors.json').read_text())
    pres = tmp_path / 'preserved'
    pres.mkdir()
    bm = {'schema_version': 'qgv-q-input-private-bundle/1', 'execution_sha': x['execution_sha'], 'files': [x['source_files']['evaluation'], x['source_files']['reference']]}
    (pres / 'bundle-manifest.json').write_text(json.dumps(bm))
    bdesc = {'path': 'bundle-manifest.json', 'size': (pres / 'bundle-manifest.json').stat().st_size, 'sha256': _sha(pres / 'bundle-manifest.json')}
    hm = {'schema_version': 'qgv-q-input-handoff/1', 'repo': x['preservation']['repo'], 'ref': x['preservation']['ref'], 'path': x['preservation']['path'], 'files': [bdesc]}
    (pres / 'handoff-manifest.json').write_text(json.dumps(hm))
    x['preservation']['handoff_manifest_sha256'] = _sha(pres / 'handoff-manifest.json')
    x['preservation']['bundle_manifest'] = bdesc
    if edit:
        edit(x, pres)
    (bundle / 'input-anchors.json').write_text(json.dumps(x))
    return pres


def _anchored_args(b, data, pres, root=None, **over):
    a = _args(b, data, **{'--input-lineage': None, '--input-lineage-sha256': None})
    extra = {'--input-anchors': b / 'input-anchors.json', '--input-anchors-sha256': _sha(b / 'input-anchors.json'), '--clocks': b / 'delivery-clocks.json',
             '--clocks-sha256': _sha(b / 'delivery-clocks.json'), '--preserved-handoff': pres, '--preserved-root-sha256': root or _sha(pres / 'handoff-manifest.json')}
    extra.update(over)
    return a + [x for k, v in extra.items() if v is not None for x in (k, str(v))]


def test_a_new_input_version_switches_only_through_both_anchors(tmp_path, capsys):
    b = _bundle(tmp_path)
    data = _data(tmp_path, b)
    pres = _preserved(tmp_path, b)
    assert tool.main(_anchored_args(b, data, pres)) == 0, capsys.readouterr().out
    out = data / 'classification' / 'dual-333' / 'held1057'
    assert (out / 'input-anchors.json').read_bytes() == (b / 'input-anchors.json').read_bytes() and (out / 'delivery-clocks.json').is_file()
    assert not (out / 'input-lineage.json').exists(), 'one input basis per bundle'
    rec = json.loads((out / 'switch.json').read_text())
    assert rec['input_basis'] == 'INPUT_ANCHORS' and rec['pins']['preserved_root'] == _sha(pres / 'handoff-manifest.json')


@pytest.mark.parametrize('case,code', [
    ('root_from_elsewhere', 'PRESERVATION_ROOT_HASH'),
    ('other_bundle', 'PRESERVATION_BUNDLE'),
    ('other_snapshot', 'PRESERVATION_SOURCE:evaluation'),
    ('other_execution', 'PRESERVATION_EXECUTION'),
    ('lineage_as_anchor', 'INPUT_ANCHORS_SCHEMA'),
    ('other_reference', 'REFERENCE_INPUT_BINDING'),
    ('clock_without_reason', 'CLOCKS_SCHEMA'),
    ('with_lineage_too', 'INPUT_ANCHORS_ARGUMENTS'),
])
def test_anchor_refusals_keep_the_existing_bundle(tmp_path, capsys, case, code):
    good = _bundle(tmp_path, 'good')
    data = _data(tmp_path, good)
    assert tool.main(_args(good, data)) == 0
    keep = _tree(data / 'classification' / 'dual-333' / 'held1057')
    capsys.readouterr()
    b = _bundle(tmp_path, 'new')

    def edit(x, pres):
        if case == 'other_bundle':
            x['preservation']['bundle_manifest']['sha256'] = 'e' * 64
        elif case == 'other_snapshot':
            x['source_files']['evaluation']['sha256'] = 'e' * 64
        elif case == 'other_execution':
            x['execution_sha'] = '3' * 40
        elif case == 'lineage_as_anchor':
            x['schema_version'] = 'qgv-dual-input-projection-proof/1'
        elif case == 'other_reference':
            x['expected_reference']['input_hash'] = 'e' * 64
    pres = _preserved(tmp_path, b, edit)
    over = {}
    if case == 'root_from_elsewhere':
        over['root'] = 'd' * 64
    if case == 'clock_without_reason':
        c = json.loads((b / 'delivery-clocks.json').read_text())
        c['calculated_at_reason'] = ''
        (b / 'delivery-clocks.json').write_text(json.dumps(c))
    args = _anchored_args(b, data, pres, over.get('root'))
    if case == 'with_lineage_too':
        args += ['--input-lineage', str(b / 'input-lineage.json'), '--input-lineage-sha256', _sha(b / 'input-lineage.json')]
    assert tool.main(args) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_DUAL_333_SWITCH refused=' + code + ' kept=existing'
    assert _tree(data / 'classification' / 'dual-333' / 'held1057') == keep
