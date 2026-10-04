// Read-only experiment adapter for ingestion/raw_store.py's exact on-disk layout.
// A checked manifest proves persisted-byte lineage, not source availability or PIT.
import {constants} from 'node:fs';
import {lstat, open, realpath} from 'node:fs/promises';
import path from 'node:path';
import {normalizeStoredResponse, hash, fail, instant} from './contract.mjs';

function required(value, label) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label}: required`);
  return value;
}

async function readConfined(root, relative) {
  // Never trust a path in the manifest. Every component is constructed locally;
  // symlinks (including within the store) and non-regular files are rejected.
  const filename = path.join(root, relative);
  for (const item of [root, path.dirname(filename), filename]) {
    const stat = await lstat(item);
    if (stat.isSymbolicLink() || await realpath(item) !== item) fail('store path symlink prohibited');
    if (item === filename ? !stat.isFile() : !stat.isDirectory()) fail('regular store file and directories required');
  }
  const file = await open(filename, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = await file.stat();
    if (!before.isFile()) fail('regular store file required');
    const bytes = await file.readFile();
    const after = await file.stat();
    const named = await lstat(filename);
    if (before.dev !== named.dev || before.ino !== named.ino || named.isSymbolicLink() ||
        before.size !== after.size || before.mtimeMs !== after.mtimeMs || before.ctimeMs !== after.ctimeMs ||
        await realpath(filename) !== filename) fail('store changed during read');
    return bytes;
  } finally { await file.close(); }
}

async function loadStoredArtifact({root, artifact_id, symbol, range}) {
  required(root, 'root'); required(artifact_id, 'artifact_id'); required(range, 'range');
  required(symbol, 'symbol');
  if (!/^[A-Za-z0-9^][A-Za-z0-9.^=-]*$/.test(symbol) || symbol.includes('__')) fail('unsafe symbol');
  if (!/^(?:\d+(?:d|mo|y)|ytd|max)$/.test(range)) fail('unsupported range syntax');
  if (artifact_id !== `yahoo_chart:${symbol}:${range}`) fail('artifact identity/range mismatch');
  const store = path.resolve(root);
  const basename = artifact_id.replaceAll(':', '__');
  const manifestBytes = await readConfined(store, `manifests/${basename}.json`);
  const manifest = JSON.parse(manifestBytes.toString('utf8'));
  if (manifest.artifact_id !== artifact_id) fail('manifest artifact mismatch');
  if (manifest.source_kind !== 'YAHOO_CHART') fail(`unsupported source_kind: ${manifest.source_kind}`);
  if (manifest.http_status !== 200) fail('successful HTTP 200 evidence required');
  if (!Number.isSafeInteger(manifest.bytes) || manifest.bytes < 0 || !/^[0-9a-f]{64}$/.test(manifest.sha256)) fail('manifest byte integrity fields invalid');
  required(manifest.fetcher, 'manifest fetcher');
  instant(manifest.fetched_at,'manifest fetched_at');
  if (typeof manifest.content_type !== 'string' || !/^application\/json(?:\s*;|$)/i.test(manifest.content_type)) fail('JSON content type required');
  const url = new URL(required(manifest.source_url, 'source_url'));
  if (url.protocol !== 'https:' || !['query1.finance.yahoo.com','query2.finance.yahoo.com'].includes(url.hostname) ||
      url.port || url.username || url.password || url.hash ||
      decodeURIComponent(url.pathname) !== `/v8/finance/chart/${symbol}`) fail('Yahoo source URL identity invalid');
  if (url.searchParams.getAll('interval').length !== 1 || url.searchParams.get('interval') !== '1d' ||
      url.searchParams.getAll('range').length !== 1 || url.searchParams.get('range') !== range ||
      [...url.searchParams.keys()].some(key => !['interval','range'].includes(key))) fail('Yahoo source request interval/range invalid');
  const bytes = await readConfined(store, `blobs/${basename}`);
  if (bytes.length !== manifest.bytes || hash(bytes) !== manifest.sha256) fail('stored bytes SHA/size mismatch');
  const raw = JSON.parse(bytes.toString('utf8'));
  if (!Array.isArray(raw.chart?.result) || raw.chart.result.length !== 1 || raw.chart.error) fail('one successful Yahoo result required');
  const result = raw.chart?.result?.[0];
  if (result?.meta?.symbol !== symbol) fail('source identity mismatch');
  if ((result.meta.dataGranularity ?? '1d') !== '1d') fail('daily interval evidence required');
  if (!Array.isArray(result.timestamp) || result.timestamp.some(t => typeof t !== 'number' || !Number.isFinite(t) || !Number.isFinite(new Date(t*1000).getTime()))) fail('valid timestamp array required');
  const quotes=result.indicators?.quote;
  if (!Array.isArray(quotes) || quotes.length !== 1 || !quotes[0] || typeof quotes[0] !== 'object' || Array.isArray(quotes[0])) fail('one quote object required');
  const quote = quotes[0];
  for (const key of ['open','high','low','close','volume']) {
    if (quote[key] !== undefined && (!Array.isArray(quote[key]) || quote[key].length !== result.timestamp?.length)) fail(`quote ${key} timestamp alignment invalid`);
  }
  return {bytes, manifest, result, evidence:{manifest_sha256:hash(manifestBytes), artifact_id, source_kind:manifest.source_kind,
    http_status:manifest.http_status, fetcher:manifest.fetcher, content_type:manifest.content_type,
    raw_sha256:manifest.sha256, raw_bytes:manifest.bytes,
    // Existing RawDatasetStore assigns this at persistence. It is not the HTTP
    // acquisition timestamp and never certifies historical market availability.
    fetched_at:manifest.fetched_at, store_persisted_at:manifest.fetched_at,
    acquisition_at:null, acquisition_evidence_ref:null, slot:'LATEST_STORED_RECORD',
    limitations:['ACQUISITION_TIME_NOT_IN_STORE_SCHEMA','PIT_NOT_VERIFIED','PUBLICATION_DISABLED']}};
}

/** Byte/shape preflight only: no chart candidate or inferred security identity. */
export async function inspectStoredArtifact(options) {
  const {result,evidence} = await loadStoredArtifact(options);
  const quote=result.indicators.quote[0];
  return {inspection:'STORED_BYTES_AND_SHAPE_ONLY',evidence,
    schema:{provider_symbol:result.meta.symbol,request_interval:'1d',request_range:options.range,
      point_count:result.timestamp.length,currency:result.meta.currency ?? null,
      timezone:result.meta.exchangeTimezoneName ?? null,
      first_observation:result.timestamp.length?new Date(result.timestamp[0]*1000).toISOString():null,
      last_observation:result.timestamp.length?new Date(result.timestamp.at(-1)*1000).toISOString():null,
      fields:Object.fromEntries(['open','high','low','close','volume'].map(key=>[key,{
        present:Array.isArray(quote[key]),non_null_count:quote[key]?.filter(v=>v!==null).length ?? 0}]))},
    chart_candidate_created:false,pit_status:'NOT_VERIFIED',publication_grant:null};
}

/**
 * Read an existing latest-slot Yahoo record. No directory creation or writes.
 * identity must come from the caller's established identity mapping; ticker is
 * only cross-checked, never promoted into company/security/listing identity.
 * as_of is the requested observation cutoff, NOT a PIT decision-time claim.
 * Historical history/ slots and other providers are deliberately unsupported.
 */
export async function readYahooRawCandidate({root, artifact_id, identity, range, as_of}) {
  for (const key of ['company_id','security_id','listing_id','symbol']) required(identity?.[key], `identity.${key}`);
  const symbol=identity.symbol;
  const {bytes,manifest,evidence}=await loadStoredArtifact({root,artifact_id,symbol,range});
  const candidate = normalizeStoredResponse(bytes, {
    provider:'yahoo-chart', transport:'API', synthetic:false,
    company_id:identity.company_id, security_id:identity.security_id, listing_id:identity.listing_id, symbol,
    artifact_id, as_of, fetched_at:manifest.fetched_at, raw_sha256:manifest.sha256,
    source_reference:manifest.source_url, request:{interval:'1d', range},
  });
  // A bar dated after ingestion is not supported by this offline bridge.
  if (candidate.points.some(p => Date.parse(p.time) > Date.parse(candidate.provenance.fetched_at))) fail('bar observation after fetch timestamp');
  return {
    candidate,
    evidence:{...evidence,identity_origin:'CALLER_SUPPLIED_NOT_INFERRED',
      limitations:[...evidence.limitations,'IDENTITY_MAPPING_NOT_INDEPENDENTLY_VERIFIED']},
  };
}
