"""Prepare only the existing G3 test vector against the new exact upstream source."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from investment_system.product.web_mvp import build, validate_bundle

root = Path(__file__).resolve().parent
source = Path('/workspace/web-g3-state-upstream-readonly')
head = 'e91dc773af600ff66d31575ce3774490a0b0be8c'
parent = '2b53b27fe0f570557159d02552911e9e1cc7be9c'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == head
bundle = json.loads((root.parent / 'test-vector.schema1.json').read_text())
validate_bundle(bundle)
assert not (root / 'isolated-web').exists()
build(root / 'isolated-web', bundle=bundle)
asset = 'implementation/src/investment_system/product/web_assets/app.js'
before = subprocess.check_output(['git', 'show', parent + ':' + asset], cwd=source)
after = (source / asset).read_bytes()
def research_marker(raw):
    return raw[raw.index(b'function researchMarker('):raw.index(b'\nfunction guardSections(')]
assert research_marker(before) == research_marker(after)
probe = (root.parent / 'upstream-2b53b27/browser_g3_still_live.js').read_text()
probe = probe.replace(parent, head).replace('STILL_REPRODUCED_UPSTREAM:', 'STILL_REPRODUCED_PRESENTATION_CHILD:')
assert not (root / 'browser_g3_still_live.js').exists()
(root / 'browser_g3_still_live.js').write_text(probe)
receipt = {'exact_source_head': head, 'parent': parent, 'existing_G3_probe_only': True,
           'new_app_sha256': sha256(after).hexdigest(), 'parent_app_sha256': sha256(before).hexdigest(),
           'researchMarker_byte_identical_to_parent': True, 'researchMarker_sha256': sha256(research_marker(after)).hexdigest(),
           'bundle_builder_admission': 'STILL_ACCEPTED', 'source_mutations': 0, 'real_data_provider_calls': 0,
           'raw_data_json_sha256': sha256((root / 'isolated-web/data.json').read_bytes()).hexdigest()}
(root / 'probe-preparation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'head': head, 'researchMarker_byte_identical': True, 'builder_admission': 'STILL_ACCEPTED'}))
