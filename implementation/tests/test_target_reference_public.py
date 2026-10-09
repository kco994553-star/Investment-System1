"""Pages-only public TARGET reference; no device data or stale display authority."""
import hashlib
import base64
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from investment_system.product.device_actual_catalog import (
    ROOT, MAP_PATH, TARGET_PATH, THEME_PATH, TARGET_SHA256, MAP_SHA256,
    THEME_SHA256, public_actual_catalog,
)
from investment_system.product.web_mvp import build

TOOL = Path(__file__).resolve().parents[1] / 'tools/build_pages_cockpit.py'
SOURCE_URL = ('https://raw.githubusercontent.com/kco994553-star/Investment-System1/'
              'refs/heads/claude/investment-system-top500-validation-alrugm/'
              'implementation/docs/portfolio_target_owner/TARGET_v0.yaml')
ASSETS = Path(__file__).resolve().parents[1] / 'src/investment_system/product/target_reference_assets'

# Real production script, metadata/source bytes and WebCrypto; only DOM, fetch
# and timers are modeled here. Native browser CSP/CORS/layout needs Playwright.
RUNTIME_HARNESS = r'''
const fs=require('node:fs'),vm=require('node:vm'),webcrypto=require('node:crypto').webcrypto;
const p=JSON.parse(fs.readFileSync(0,'utf8')),root=Buffer.from(p.source,'base64'),source=p.url,realTimer=setTimeout;
const check=(ok,msg)=>{if(!ok)throw Error(msg)};
class E{constructor(){this.dataset={};this.children=[];this.events={};this.textContent='';this.value=''}append(...x){this.children.push(...x)}replaceChildren(...x){this.children=x;this.textContent=''}setAttribute(){}addEventListener(n,f){this.events[n]=f}}
function setup(){
 const els={};for(const s of ['[data-target-output]','[data-target-status]','#target-language','[data-target-reason]','[data-target-verified]','#target-recheck'])els[s]=new E;
 const events={},m={mode:'good',resolve:null,entered:null,sourceCalls:0};
 const doc={currentScript:{src:'https://test.invalid/project/target.js'},documentElement:{},querySelector:s=>els[s],querySelectorAll:()=>[],createElement:()=>new E,addEventListener:(n,f)=>events[n]=f,visibilityState:'visible'};
 const buffer=b=>Uint8Array.from(b).buffer;
 const ctx={document:doc,navigator:{language:'en'},window:{addEventListener:(n,f)=>events[n]=f},URL,TextDecoder,Intl,Date,AbortController,Error,Number,Set,Array,Uint8Array,Promise,crypto:{subtle:{digest:(a,b)=>m.mode==='digest-stall'&&Buffer.from(b).equals(root)?new Promise(()=>{}):webcrypto.subtle.digest(a,b)}},setTimeout:(f,t)=>realTimer(f,Math.min(t,100)),clearTimeout};
 ctx.fetch=async(url,options)=>{
  check(options.credentials==='omit'&&options.cache==='no-store'&&options.referrerPolicy==='no-referrer'&&options.redirect==='error','privacy');
  if(url!==source){check(url==='https://test.invalid/project/target-reference.json','metadata URL');let raw=p.metadata;if(m.mode==='metadata-tamper'){const data=JSON.parse(raw);data.catalog.instruments[0].target_units+=1;raw=JSON.stringify(data)}return{ok:true,arrayBuffer:async()=>buffer(Buffer.from(raw))}}
  m.sourceCalls++;const mode=m.mode;
  if(mode==='offline'||mode==='redirect')throw Error('NOT_AVAILABLE');
  if(mode==='missing')return{ok:false};
  if(mode==='header-stall')return new Promise(()=>{});
  if(mode==='body-stall')return{ok:true,arrayBuffer:()=>new Promise(()=>{})};
  if(mode==='held')return{ok:true,arrayBuffer:()=>new Promise(r=>{m.resolve=()=>r(buffer(root));m.entered()})};
  return{ok:true,arrayBuffer:async()=>buffer(mode==='changed'?Buffer.from('changed source'):root)};
 };
 vm.runInNewContext(p.js,ctx);
 const state=()=>els['[data-target-status]'].dataset.state,empty=()=>els['[data-target-output]'].children.length===0;
 const wait=async expected=>{for(let i=0;i<100;i++){if(state()===expected&&(expected!=='NOT_AVAILABLE'||/cannot be verified|확인할 수 없습니다/.test(els['[data-target-reason]'].textContent)))return;await new Promise(r=>realTimer(r,5))}throw Error('expected '+expected+', got '+state())};
 return{m,els,events,state,empty,wait,ctx};
}
(async()=>{
 for(const mode of ['changed','missing','offline','redirect','header-stall','body-stall','digest-stall','metadata-tamper']){
  const h=setup();h.events.pageshow();await h.wait('REFERENCE_VALIDATED');check(!h.empty(),'valid output absent');
  const prior=h.m.sourceCalls;h.m.mode=mode;h.events.visibilitychange();check(h.empty(),'not synchronously cleared');
  await h.wait(['changed','metadata-tamper'].includes(mode)?'INVALIDATED':'NOT_AVAILABLE');check(h.empty(),'denied output present');
  if(mode==='metadata-tamper')check(h.m.sourceCalls===prior,'tampered metadata fetched root');
  h.els['#target-language'].value='ko';h.els['#target-language'].events.change();check(h.empty(),'locale resurrected');console.log('PASS '+mode);
 }
 const noCrypto=setup();noCrypto.ctx.crypto=undefined;noCrypto.events.pageshow();await noCrypto.wait('NOT_AVAILABLE');check(noCrypto.empty()&&noCrypto.m.sourceCalls===0,'missing crypto displayed/fetched');console.log('PASS missing crypto');
 const h=setup();h.m.mode='held';const entered=new Promise(r=>h.m.entered=r);h.events.pageshow();await entered;
 h.m.mode='changed';h.events.pageshow();await h.wait('INVALIDATED');h.m.resolve();await new Promise(r=>realTimer(r,20));
 check(h.state()==='INVALIDATED'&&h.empty(),'superseded success resurrected');console.log('PASS superseded body success');
})().catch(e=>{console.error(e.message);process.exitCode=1});
'''


def load_tool():
    spec = importlib.util.spec_from_file_location('target_pages_build', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TargetReferencePublicTest(unittest.TestCase):
    def test_pages_build_binds_reviewed_catalog_and_metadata_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            self.assertTrue((out / 'target.html').exists(), 'Pages-only TARGET route is missing')
            raw = (out / 'target-reference.json').read_bytes()
            metadata = json.loads(raw)
            self.assertEqual(metadata['schema'], 'PUBLIC_TARGET_REFERENCE/1')
            self.assertEqual(metadata['role'], 'PUBLIC_READ_ONLY_REFERENCE')
            self.assertEqual(metadata['source_url'], SOURCE_URL)
            self.assertEqual(metadata['expected_target_root_sha256'], TARGET_SHA256)
            self.assertEqual(metadata['lineage'], {
                'target_root_sha256': TARGET_SHA256,
                'identity_map_sha256': MAP_SHA256,
                'theme_assignments_sha256': THEME_SHA256,
                'source_values_changed': False,
            })
            self.assertEqual(metadata['catalog'], public_actual_catalog())
            self.assertIn('<a href="target.html">TARGET · 공개 참고 / Public reference</a>', (out / 'index.html').read_text())
            self.assertNotIn('PUBLIC_TARGET_REFERENCE_LINK', (out / 'index.html').read_text())
            js = (out / 'target.js').read_text()
            self.assertIn(hashlib.sha256(raw).hexdigest(), js)
            self.assertNotIn('__TARGET_METADATA_SHA256__', js)
            self.assertEqual(len(metadata['catalog']['instruments']), 19)
            for prohibited in ['quantity', 'average_cost', 'price', 'fx_rate', 'device_actual']:
                self.assertNotIn('"' + prohibited + '"', raw.decode())

    def test_generic_builder_does_not_add_the_public_route(self):
        with tempfile.TemporaryDirectory() as folder:
            out = build(Path(folder) / 'generic')
            self.assertFalse((out / 'target.html').exists())
            self.assertFalse((out / 'target-reference.json').exists())
            self.assertNotIn('href="target.html"', (out / 'index.html').read_text())

    def test_bad_pages_link_marker_fails_before_output(self):
        for marker in ['', '<!-- PUBLIC_TARGET_REFERENCE_LINK -->' * 2]:
            with self.subTest(marker_count=marker.count('PUBLIC_TARGET_REFERENCE_LINK')):
                tool = load_tool()
                original = Path.read_text
                def changed_read(path, *args, **kwargs):
                    if path == ASSETS.parent / 'web_assets/index.html':
                        return marker
                    return original(path, *args, **kwargs)
                with tempfile.TemporaryDirectory() as folder:
                    out = Path(folder) / 'site'
                    with patch.object(Path, 'read_text', changed_read):
                        with self.assertRaisesRegex(ValueError, '^Pages TARGET link marker must appear exactly once$'):
                            tool.build_public_cockpit(out)
                    self.assertFalse(out.exists())

    def test_only_target_csp_can_connect_to_fixed_public_root(self):
        self.assertTrue((ASSETS / 'target.html').exists(), 'TARGET assets are missing')
        html = (ASSETS / 'target.html').read_text()
        self.assertIn("connect-src 'self' " + SOURCE_URL + ';', html)
        self.assertIn("default-src 'none'", html)
        self.assertIn("base-uri 'none'", html)
        self.assertIn("form-action 'none'", html)
        self.assertNotIn('unsafe-inline', html)
        main = (ASSETS.parent / 'web_assets/index.html').read_text()
        self.assertIn("connect-src 'self'", main)
        self.assertNotIn('raw.githubusercontent.com', main)

    def test_runtime_has_no_storage_or_query_routing_and_no_polling(self):
        self.assertTrue((ASSETS / 'target.js').exists(), 'TARGET verifier is missing')
        js = (ASSETS / 'target.js').read_text()
        for prohibited in ['localStorage', 'sessionStorage', 'indexedDB', 'location.search',
                           'URLSearchParams', 'setInterval', 'innerHTML', 'serviceWorker']:
            self.assertNotIn(prohibited, js)
        for required in ['credentials: "omit"', 'cache: "no-store"',
                         'referrerPolicy: "no-referrer"', 'redirect: "error"',
                         'crypto.subtle.digest', 'pageshow', 'visibilitychange']:
            self.assertIn(required, js)

    def test_source_root_drift_fails_before_any_public_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'source'
            for name in [MAP_PATH, TARGET_PATH, THEME_PATH]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, destination)
            target = root / TARGET_PATH
            target.write_bytes(target.read_bytes() + b'\n# changed canonical root\n')
            with self.assertRaisesRegex(ValueError, '^TARGET source hash mismatch$'):
                public_actual_catalog(root)
            out = Path(folder) / 'public'
            tool = load_tool()
            with patch.object(tool, 'public_actual_catalog', side_effect=lambda: public_actual_catalog(root), create=True):
                with self.assertRaisesRegex(ValueError, '^TARGET source hash mismatch$'):
                    tool.build_public_cockpit(out)
            self.assertFalse(out.exists(), 'Root drift must fail before public files are written')

    def test_real_byte_runtime_denial_and_harness_detects_stale_output(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node runtime required for JS semantics check')
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            payload = {'js': (out / 'target.js').read_text(),
                'metadata': (out / 'target-reference.json').read_text(),
                'source': base64.b64encode((ROOT / TARGET_PATH).read_bytes()).decode(),
                'url': SOURCE_URL}
            def run(value):
                return subprocess.run([node, '-e', RUNTIME_HARNESS], input=json.dumps(value),
                    text=True, capture_output=True, timeout=10)
            result = run(payload)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('PASS body-stall', result.stdout)
            self.assertIn('PASS superseded body success', result.stdout)
            # Mutation qualification: prove this harness turns RED if a run
            # leaves the old numeric display in place instead of clearing it.
            payload['js'] = payload['js'].replace('output.replaceChildren();',
                'if (state === "REFERENCE_VALIDATED") output.replaceChildren();')
            red = run(payload)
            self.assertNotEqual(red.returncode, 0)
            self.assertIn('not synchronously cleared', red.stderr)


if __name__ == '__main__':
    unittest.main()
