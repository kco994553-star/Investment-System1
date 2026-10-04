// Offline replay of exact captured public response bytes. No network in tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {hash} from './contract.mjs';
import {inspectStoredArtifact, readYahooRawCandidate} from './raw_store_bridge.mjs';
import {auditYahooStore} from './store_cli.mjs';
const root=fileURLToPath(new URL('./evidence/2026-10-04-source/raw-store',import.meta.url));
const opts={root,artifact_id:'yahoo_chart:NVDA:5d',symbol:'NVDA',range:'5d'};

test('captured real response replays offline with original bytes and five complete OHLCV rows',async()=>{
  const bytes=await readFile(`${root}/blobs/yahoo_chart__NVDA__5d`);
  assert.equal(hash(bytes),'469e185faec7925e724efdc23546967e86f6b3ccbc3ba8d05a2767f968f722a6');
  const source=JSON.parse(bytes).chart.result[0];
  for(const key of ['open','high','low','close','volume'])assert(source.indicators.quote[0][key].every(Number.isFinite));
  const r=await inspectStoredArtifact(opts);
  assert.equal(r.schema.point_count,5);assert.equal(r.schema.currency,'USD');assert.equal(r.schema.timezone,'America/New_York');
  for(const field of Object.values(r.schema.fields))assert.deepEqual(field,{present:true,non_null_count:5});
  assert.equal(r.chart_candidate_created,false);assert.equal(r.evidence.acquisition_at,null);
  const acquisition=JSON.parse(await readFile(new URL('./evidence/2026-10-04-source/fetch-evidence.json',import.meta.url),'utf8'));
  assert.equal(acquisition.sha256,hash(bytes));assert.equal(acquisition.bytes,bytes.length);
  assert(Date.parse(acquisition.started_at)<=Date.parse(acquisition.completed_at));
  assert(Date.parse(acquisition.completed_at)<Date.parse(r.evidence.store_persisted_at));
});

test('real source remains blocked without fabricated security/listing identity',async()=>{
  await assert.rejects(readYahooRawCandidate({...opts,identity:{symbol:'NVDA'},as_of:'2026-10-04T10:25:00Z'}),/identity.company_id/);
});

test('store audit reports source preflight separately from financial and PIT validation',async()=>{
  const audit=await auditYahooStore(root);
  assert.equal(audit.manifest_count,1);assert.equal(audit.counts.BYTES_AND_SHAPE_CHECKED,1);
  assert.equal(audit.financial_validity,'NOT_EVALUATED');assert.equal(audit.identity_binding,'NOT_EVALUATED');
  assert.equal(audit.historical_PIT,'NOT_VERIFIED');
});
