from hashlib import sha256
import json
from pathlib import Path
import subprocess
from investment_system.product.web_mvp import build, validate_bundle

root=Path(__file__).resolve().parent
source=Path('/workspace/web-g3-upstream-readonly')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
assert head=='2b53b27fe0f570557159d02552911e9e1cc7be9c'
bundle=json.loads((root.parent/'test-vector.schema1.json').read_text())
validate_bundle(bundle)
build(root/'isolated-web',bundle=bundle)
paths=['implementation/src/investment_system/product/web_mvp.py',
 'implementation/src/investment_system/product/web_assets/app.js',
 'implementation/src/investment_system/product/web_assets/locale.js',
 'implementation/src/investment_system/product/web_assets/index.html']
data={}
for p in paths:
 baseline=subprocess.check_output(['git','show','675d0d298fbaab5b8473ed048a561ef84e2f3e78:'+p],cwd=source)
 current=(source/p).read_bytes()
 data[p]={'baseline675_sha256':sha256(baseline).hexdigest(),'upstream2b_sha256':sha256(current).hexdigest(),
          'byte_identical':baseline==current}
receipt={'upstream_head':head,'upstream_base':'f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36',
 'baseline_source_head':'675d0d298fbaab5b8473ed048a561ef84e2f3e78',
 'original_direct_methodology_bundle_admission':'STILL_ACCEPTED',
 'source_preservation':data,'source_mutations_by_reviewer':0,'real_data_provider_calls':0}
(root/'upstream-source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
