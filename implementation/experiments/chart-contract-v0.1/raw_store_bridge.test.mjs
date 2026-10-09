import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile, readdir, rm, symlink} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fixture} from './fixture.mjs';
import {hash, renderInput} from './contract.mjs';
import {readYahooRawCandidate, inspectStoredArtifact} from './raw_store_bridge.mjs';

async function stored(t, alter = {}) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'chart-raw-store-'));
  t.after(() => rm(root, {recursive:true, force:true}));
  await mkdir(path.join(root,'manifests')); await mkdir(path.join(root,'blobs'));
  const bytes = alter.bytes ?? fixture().bytes;
  const manifest = {artifact_id:'yahoo_chart:DEMO:5y',source_kind:'YAHOO_CHART',
    source_url:'https://query1.finance.yahoo.com/v8/finance/chart/DEMO?interval=1d&range=5y',
    fetched_at:'2024-01-14T00:00:00+00:00',sha256:hash(bytes),bytes:bytes.length,
    content_type:'application/json;charset=utf-8',fetcher:'existing-fetcher v1',http_status:200,notes:'',...alter.manifest};
  const manifestPath = path.join(root,'manifests/yahoo_chart__DEMO__5y.json');
  const blobPath = path.join(root,'blobs/yahoo_chart__DEMO__5y');
  await writeFile(manifestPath,JSON.stringify(manifest)); await writeFile(blobPath,bytes);
  return {root,manifestPath,blobPath,bytes,manifest,args:{root,artifact_id:manifest.artifact_id,range:'5y',
    identity:{company_id:'caller-company',security_id:'caller-security',listing_id:'caller-listing',symbol:'DEMO'},
    as_of:'2024-01-13T00:00:00Z'}};
}

test('reads exact stored layout and preserves bytes/metadata without writing or publishing', async t => {
  const s = await stored(t); const before = await readFile(s.manifestPath);
  const {candidate:c,evidence:e} = await readYahooRawCandidate(s.args);
  assert.equal(c.points.length,12); assert.equal(c.points[3].volume,0); assert.equal(c.points[4].volume,null);
  assert.equal(c.provenance.raw_sha256,hash(s.bytes)); assert.equal(e.manifest_sha256,hash(before));
  assert.deepEqual(c.identity,s.args.identity); assert.equal(c.synthetic,false);
  assert.equal(c.data_state,'NOT_AVAILABLE'); assert.equal(c.pit_status,'NOT_VERIFIED');
  assert.equal(c.publication_grant,null); assert.equal(c.points[0].available_at,null);
  assert.throws(() => renderInput(c), /real publication not enabled/);
  assert.deepEqual(await readFile(s.manifestPath),before); assert.deepEqual(await readFile(s.blobPath),s.bytes);
  assert.deepEqual((await readdir(s.root)).sort(),['blobs','manifests']);
});

test('identity fields cannot override bridge production withholding', async t => {
  const s=await stored(t);s.args.identity.synthetic=true;s.args.identity.transport='FIXTURE';
  const {candidate:c}=await readYahooRawCandidate(s.args);
  assert.equal(c.synthetic,false);assert.equal(c.provenance.transport,'API');assert.equal(c.data_state,'NOT_AVAILABLE');
});

test('preflight works without company identity and does not create a candidate or acquisition timestamp', async t => {
  const s=await stored(t);
  const result=await inspectStoredArtifact({root:s.root,artifact_id:s.manifest.artifact_id,symbol:'DEMO',range:'5y'});
  assert.equal(result.inspection,'STORED_BYTES_AND_SHAPE_ONLY');assert.equal(result.chart_candidate_created,false);
  assert.equal(result.evidence.store_persisted_at,s.manifest.fetched_at);assert.equal(result.evidence.acquisition_at,null);
  assert.equal(result.schema.point_count,12);assert.equal(result.schema.fields.volume.non_null_count,11);
  assert.equal(result.pit_status,'NOT_VERIFIED');assert.equal(result.publication_grant,null);
  assert.equal(Object.hasOwn(result,'candidate'),false);
});

test('requires explicit company/security/listing identity', async t => {
  const s=await stored(t);
  for(const key of ['company_id','security_id','listing_id']) {
    const identity={...s.args.identity};delete identity[key];
    await assert.rejects(readYahooRawCandidate({...s.args,identity}),new RegExp(key));
  }
});

test('rejects artifact traversal and mismatched symbol/range before IO', async t => {
  const s=await stored(t);
  for(const artifact_id of ['../../outside','yahoo_chart:OTHER:5y','yahoo_chart:DEMO:1y'])
    await assert.rejects(readYahooRawCandidate({...s.args,artifact_id}),/artifact identity/);
  for(const symbol of ['../DEMO','DEMO__5y','DEMO/child'])
    await assert.rejects(readYahooRawCandidate({...s.args,identity:{...s.args.identity,symbol}}),/unsafe symbol/);
});

test('rejects hash and byte count mismatch', async t => {
  for(const manifest of [{sha256:'0'.repeat(64)},{bytes:1},{bytes:'123'}]) {
    const s=await stored(t,{manifest});await assert.rejects(readYahooRawCandidate(s.args),/integrity|SHA\/size/);
  }
});

test('rejects manifest source/artifact/status/content-type/fetcher mismatches', async t => {
  for(const manifest of [{source_kind:'OTHER'},{artifact_id:'yahoo_chart:OTHER:5y'},{http_status:403},
    {http_status:null},{content_type:'text/html'},{fetcher:''}]) {
    const s=await stored(t,{manifest});s.args.artifact_id='yahoo_chart:DEMO:5y';
    await assert.rejects(readYahooRawCandidate(s.args));
  }
});

test('rejects foreign source URL, identity mismatch, wrong/duplicate interval or range', async t => {
  const prefix='https://query1.finance.yahoo.com/v8/finance/chart/DEMO';
  for(const source_url of [
    'https://evil.example/v8/finance/chart/DEMO?interval=1d&range=5y',
    'http://query1.finance.yahoo.com/v8/finance/chart/DEMO?interval=1d&range=5y',
    'https://query1.finance.yahoo.com/v8/finance/chart/OTHER?interval=1d&range=5y',
    `${prefix}?interval=1m&range=5y`,`${prefix}?interval=1d&range=1y`,
    `${prefix}?interval=1d&range=5y&interval=1m`,`${prefix}?interval=1d&range=5y&range=5y`,
    `${prefix}?interval=1d&range=5y&events=div`,`${prefix}?interval=1d&range=5y#fragment`]) {
    const s=await stored(t,{manifest:{source_url}});await assert.rejects(readYahooRawCandidate(s.args),/source URL|source request/);
  }
});

test('rejects missing raw bytes rather than reconstructing from manifest', async t => {
  const s=await stored(t);await rm(s.blobPath);await assert.rejects(readYahooRawCandidate(s.args),/ENOENT/);
});

test('rejects leaf and parent symlink redirection even to an in-store file', async t => {
  const s=await stored(t);const alternate=path.join(s.root,'alternate');await writeFile(alternate,s.bytes);
  await rm(s.blobPath);await symlink(alternate,s.blobPath);
  await assert.rejects(readYahooRawCandidate(s.args),/symlink/);
  await rm(path.join(s.root,'blobs'),{recursive:true});await mkdir(path.join(s.root,'redirect'));
  await symlink(path.join(s.root,'redirect'),path.join(s.root,'blobs'));
  await assert.rejects(readYahooRawCandidate(s.args),/symlink/);
});

test('rejects symlink store root', async t => {
  const s=await stored(t);const link=`${s.root}-link`;t.after(()=>rm(link,{force:true}));await symlink(s.root,link);
  await assert.rejects(readYahooRawCandidate({...s.args,root:link}),/symlink/);
});

test('rejects malformed fetch timestamps and bar after ingestion', async t => {
  for(const fetched_at of ['2024-01-14','2024-02-30T00:00:00Z','2024-01-01T00:00:00Z','2024-01-14T24:00:00Z']) {
    const s=await stored(t,{manifest:{fetched_at}});await assert.rejects(readYahooRawCandidate(s.args));
  }
});

test('preflight independently rejects malformed persistence timestamp', async t => {
  const s=await stored(t,{manifest:{fetched_at:'2024-01-14T24:00:00Z'}});
  await assert.rejects(inspectStoredArtifact({root:s.root,artifact_id:s.manifest.artifact_id,symbol:'DEMO',range:'5y'}),/invalid clock/);
});

test('rejects non-regular blob before reading', async t => {
  const s=await stored(t);await rm(s.blobPath);await mkdir(s.blobPath);
  await assert.rejects(readYahooRawCandidate(s.args),/regular store file/);
});

test('retrospective fetch is permitted only as NOT_VERIFIED, never as available_at', async t => {
  const s=await stored(t,{manifest:{fetched_at:'2025-01-01T00:00:00Z'}});
  const {candidate:c}=await readYahooRawCandidate(s.args);
  assert.equal(c.pit_status,'NOT_VERIFIED');assert.equal(c.source_vintage,null);
  assert.ok(c.points.every(p=>p.available_at===null));
});

test('rejects payload symbol mismatch and malformed quote alignment', async t => {
  for(const mutate of [r=>{r.meta.symbol='OTHER';},r=>{r.indicators.quote[0].open.pop();},r=>{r.indicators.quote.push({});}]) {
    const raw=JSON.parse(fixture().bytes);mutate(raw.chart.result[0]);
    const s=await stored(t,{bytes:Buffer.from(JSON.stringify(raw))});await assert.rejects(readYahooRawCandidate(s.args));
  }
});

test('preflight rejects malformed quote container',async t=>{const raw=JSON.parse(fixture().bytes);raw.chart.result[0].indicators.quote=[[]];const s=await stored(t,{bytes:Buffer.from(JSON.stringify(raw))});await assert.rejects(inspectStoredArtifact({root:s.root,artifact_id:s.manifest.artifact_id,symbol:'DEMO',range:'5y'}),/quote object/);});
