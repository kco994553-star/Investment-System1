// Isolated proposal. No publication grant, HTTP client, MCP server or financial model.
import { createHash } from 'node:crypto';

export const VERSION = 'CHART_CANDIDATE/0.1';
export function fail(message) { throw new Error(message); }
const text = (v, name) => typeof v === 'string' && v.trim() ? v : fail(`${name}: required`);
function instant(v, name) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d\d:\d\d)$/.test(v) || !Number.isFinite(Date.parse(v))) fail(`${name}: timezone-aware timestamp required`);
  const [y,m,d]=v.slice(0,10).split('-').map(Number);
  const calendar=new Date(0);calendar.setUTCFullYear(y,m-1,d);calendar.setUTCHours(0,0,0,0);
  if(calendar.getUTCFullYear()!==y||calendar.getUTCMonth()!==m-1||calendar.getUTCDate()!==d) fail(`${name}: invalid calendar date`);
  return new Date(v).toISOString();
}
function number(v, name) {
  if (v === null || v === undefined) return null;
  if (typeof v !== 'number' || !Number.isFinite(v)) fail(`${name}: finite number or null required`);
  return v;
}
export const hash = bytes => createHash('sha256').update(bytes).digest('hex');

// Input is the original persisted provider response bytes, never prose rewritten by an LLM.
export function normalizeStoredResponse(bytes, ctx) {
  if (!Buffer.isBuffer(bytes)) fail('original bytes required');
  if (hash(bytes) !== ctx.raw_sha256) fail('raw hash mismatch');
  if (typeof ctx.synthetic !== 'boolean') fail('synthetic flag required');
  if (!['API','MCP','FIXTURE'].includes(ctx.transport)) fail('unknown transport');
  if (ctx.transport === 'FIXTURE' && !ctx.synthetic) fail('fixture cannot be real');
  if (ctx.transport === 'MCP') {
    text(ctx.mcp_server, 'MCP server'); text(ctx.mcp_tool, 'MCP tool');
    text(ctx.upstream_evidence_ref, 'original upstream evidence');
  }
  const symbol = text(ctx.symbol, 'symbol');
  const asOf = instant(ctx.as_of, 'as_of');
  const fetchedAt = instant(ctx.fetched_at, 'fetched_at');
  const raw = JSON.parse(bytes.toString('utf8'));
  let points;
  let basis;
  let timezone = null;
  let currency = null;
  if (ctx.provider === 'yahoo-chart') {
    const results = raw.chart?.result;
    if (!Array.isArray(results) || results.length !== 1 || raw.chart.error) fail('one successful Yahoo result required');
    const r = results[0];
    if (r.meta?.symbol !== symbol) fail('source identity mismatch');
    if ((r.meta.dataGranularity ?? ctx.request?.interval) !== '1d') fail('daily interval evidence required');
    // Never use parse_chart's missing-timestamp=>now or missing-currency=>USD defaults.
    timezone = r.meta.exchangeTimezoneName ?? null;
    currency = r.meta.currency ?? null;
    if (!Array.isArray(r.timestamp)) fail('timestamp array missing');
    const q = r.indicators?.quote?.[0];
    if (!q) fail('quote missing');
    points = r.timestamp.map((t, i) => {
      if (typeof t !== 'number' || !Number.isFinite(t)) fail('invalid epoch timestamp');
      return {time: new Date(t * 1000).toISOString(), open:q.open?.[i] ?? null,
        high:q.high?.[i] ?? null, low:q.low?.[i] ?? null, close:q.close?.[i] ?? null,
        volume:q.volume?.[i] ?? null};
    });
    // adjclose is deliberately not substituted into quote OHLC.
    basis = 'UNVERIFIED_PROVIDER_QUOTE';
  } else if (ctx.provider === 'alpaca') {
    if (ctx.request?.timeframe !== '1Day' || ctx.request?.adjustment !== 'raw') fail('prototype supports explicit 1Day/raw only');
    text(ctx.request.feed, 'feed');
    text(ctx.request.currency, 'request currency');
    if (raw.next_page_token) fail('incomplete pagination');
    if (!raw.bars || Array.isArray(raw.bars) || Object.keys(raw.bars).length !== 1 || !Array.isArray(raw.bars[symbol])) fail('one matching symbol bars map required');
    points = raw.bars[symbol].map(b => ({time:b.t,open:b.o,high:b.h,low:b.l,close:b.c,volume:b.v}));
    currency = ctx.request.currency;
    // Request declaration is provenance, not independent provider-vintage verification.
    basis = 'RAW_REQUEST_DECLARED';
  } else fail('unsupported provider');
  const series = points.map(p => ({...p,...Object.fromEntries(['open','high','low','close','volume'].map(k=>[k,number(p[k],k)])), available_at:null, availability_reason:'PROVIDER_AVAILABILITY_UNVERIFIED',
    session_end:null, finality:'UNKNOWN'}));
  const doc = {
    contract:VERSION, chart_kind:'DAILY_OHLCV', as_of:asOf,
    identity:{company_id:text(ctx.company_id,'company_id'),security_id:text(ctx.security_id,'security_id'),listing_id:text(ctx.listing_id,'listing_id'),symbol},
    interval:'1Day', currency, timezone, price_basis:basis,
    quote_state:'UNKNOWN', synthetic:ctx.synthetic,
    data_state:ctx.synthetic ? 'DEMO' : 'NOT_AVAILABLE', publication_grant:null,
    pit_status:'NOT_VERIFIED', source_vintage:null, corporate_action_refs:[],
    provenance:{provider:ctx.provider,artifact_id:text(ctx.artifact_id,'artifact_id'),raw_sha256:ctx.raw_sha256,
      raw_bytes:bytes.length,fetched_at:fetchedAt,source_reference:text(ctx.source_reference,'source_reference'),
      transport:ctx.transport,mcp_server:ctx.mcp_server ?? null,mcp_tool:ctx.mcp_tool ?? null,
      upstream_evidence_ref:ctx.upstream_evidence_ref ?? null,request:ctx.request ?? null},
    points:series,
  };
  validateCandidate(doc);
  return doc;
}

export function validateCandidate(doc) {
  if (doc.contract !== VERSION || doc.chart_kind !== 'DAILY_OHLCV' || doc.interval !== '1Day') fail('wrong contract');
  if (typeof doc.synthetic !== 'boolean') fail('synthetic flag required');
  for(const key of ['company_id','security_id','listing_id','symbol']) text(doc.identity?.[key],`identity.${key}`);
  if(!doc.provenance || !['yahoo-chart','alpaca'].includes(doc.provenance.provider)) fail('provenance required');
  for(const key of ['artifact_id','source_reference']) text(doc.provenance[key],`provenance.${key}`);
  if(!/^[0-9a-f]{64}$/.test(doc.provenance.raw_sha256)) fail('raw hash required');
  if(!Number.isInteger(doc.provenance.raw_bytes)||doc.provenance.raw_bytes<0) fail('raw byte count required');
  instant(doc.provenance.fetched_at,'fetched_at');
  if(!['API','MCP','FIXTURE'].includes(doc.provenance.transport)) fail('transport required');
  if(doc.provenance.transport==='FIXTURE'&&!doc.synthetic) fail('fixture cannot be real');
  if(doc.provenance.transport==='MCP') for(const key of ['mcp_server','mcp_tool','upstream_evidence_ref']) text(doc.provenance[key],key);
  const basis=doc.provenance.provider==='yahoo-chart'?'UNVERIFIED_PROVIDER_QUOTE':'RAW_REQUEST_DECLARED';
  if(doc.price_basis!==basis||doc.quote_state!=='UNKNOWN'||doc.source_vintage!==null) fail('unsupported verified metadata claim');
  if (doc.pit_status !== 'NOT_VERIFIED' || doc.publication_grant !== null) fail('prototype cannot certify PIT/publication');
  if (doc.data_state !== (doc.synthetic === true ? 'DEMO' : 'NOT_AVAILABLE')) fail('production label prohibited');
  const cutoff = Date.parse(instant(doc.as_of,'as_of'));
  if (!Array.isArray(doc.points)) fail('points required');
  let previous = -Infinity;
  for (const p of doc.points) {
    const stamp = Date.parse(instant(p.time,'bar time'));
    if (stamp <= previous) fail('duplicate or out-of-order time');
    if (stamp > cutoff) fail('observation after as_of');
    previous = stamp;
    for (const key of ['open','high','low','close','volume']) {
      if (!Object.hasOwn(p,key) || p[key] === undefined) fail(`${key}: explicit null required`);
      number(p[key],key);
    }
    if (p.volume !== null && p.volume < 0) fail('negative volume');
    if(p.high!==null && [p.open,p.close,p.low].some(v=>v!==null&&p.high<v)) fail('invalid OHLC envelope');
    if(p.low!==null && [p.open,p.close,p.high].some(v=>v!==null&&p.low>v)) fail('invalid OHLC envelope');
    if (p.available_at !== null || p.session_end !== null || p.finality !== 'UNKNOWN' || p.availability_reason !== 'PROVIDER_AVAILABILITY_UNVERIFIED') fail('availability requires future verified adapter');
  }
  return doc;
}

export function renderInput(doc) {
  validateCandidate(doc);
  if (doc.data_state !== 'DEMO' || !doc.synthetic) fail('real publication not enabled');
  return doc.points.map(p => ({time:Date.parse(p.time)/1000,
    ...( ['open','high','low','close'].every(k=>p[k]!==null) ? {open:p.open,high:p.high,low:p.low,close:p.close} : {} ),
    volume:p.volume}));
}
