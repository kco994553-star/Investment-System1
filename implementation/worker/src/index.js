// One module supports both Wrangler and the Cloudflare dashboard editor.
const ORIGIN = 'https://kco994553-star.github.io';
const TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo';
const YAHOO_ROOT = 'https://query1.finance.yahoo.com/v8/finance/chart/';
// Approved Universe504 snapshot; listing share classes use the provider symbol BRK-B/BF-B.
// Keep this literal in the dashboard-compatible module. The contract test checks the complete Universe.
const US_SYMBOLS = [
  'MMM', 'AOS', 'ABT', 'ABBV', 'ACN', 'ADBE', 'AMD', 'AES', 'AFL', 'A', 'APD', 'ABNB',
  'AKAM', 'ALB', 'ARE', 'ALGN', 'ALLE', 'LNT', 'ALL', 'GOOGL', 'GOOG', 'MO', 'AMZN', 'AMCR',
  'AEE', 'AEP', 'AXP', 'AIG', 'AMT', 'AWK', 'AMP', 'AME', 'AMGN', 'APH', 'ADI', 'AON',
  'APA', 'APO', 'AAPL', 'AMAT', 'APP', 'APTV', 'ACGL', 'ADM', 'ARES', 'ANET', 'AJG', 'AIZ',
  'T', 'ATO', 'ADSK', 'ADP', 'AZO', 'AVY', 'AXON', 'BKR', 'BALL', 'BAC', 'BAX', 'BDX',
  'BRK-B', 'BBY', 'TECH', 'BIIB', 'BLK', 'BX', 'XYZ', 'BNY', 'BA', 'BKNG', 'BSX', 'BMY',
  'AVGO', 'BR', 'BRO', 'BF-B', 'BLDR', 'BG', 'BXP', 'CHRW', 'CDNS', 'CPT', 'COF', 'CAH',
  'CCL', 'CARR', 'CVNA', 'CASY', 'CAT', 'CBOE', 'CBRE', 'CDW', 'COR', 'CNC', 'CNP', 'CF',
  'CRL', 'SCHW', 'CHTR', 'CVX', 'CMG', 'CB', 'CHD', 'CIEN', 'CI', 'CINF', 'CTAS', 'CSCO',
  'C', 'CFG', 'CLX', 'CME', 'CMS', 'KO', 'CTSH', 'COHR', 'COIN', 'CL', 'CMCSA', 'FIX',
  'COP', 'ED', 'STZ', 'CEG', 'COO', 'CPRT', 'GLW', 'CPAY', 'CTVA', 'CSGP', 'COST', 'CRH',
  'CRWD', 'CCI', 'CSX', 'CMI', 'CVS', 'DHR', 'DRI', 'DDOG', 'DVA', 'DECK', 'DE', 'DELL',
  'DAL', 'DVN', 'DXCM', 'FANG', 'DLR', 'DG', 'DLTR', 'D', 'DPZ', 'DASH', 'DOV', 'DOW',
  'DHI', 'DTE', 'DUK', 'DD', 'ETN', 'EBAY', 'ECHO', 'ECL', 'EIX', 'EW', 'ELV', 'EME',
  'EMR', 'ETR', 'EOG', 'EQT', 'EFX', 'EQIX', 'ERIE', 'ESS', 'EL', 'EG', 'EVRG', 'ES',
  'EXC', 'EXE', 'EXPE', 'EXPD', 'EXR', 'XOM', 'FFIV', 'FDS', 'FICO', 'FAST', 'FRT', 'FDX',
  'FDXF', 'FERG', 'FIS', 'FITB', 'FSLR', 'FE', 'FISV', 'FLEX', 'F', 'FTNT', 'FTV', 'FOXA',
  'FOX', 'BEN', 'FCX', 'GRMN', 'IT', 'GE', 'GEHC', 'GEV', 'GEN', 'GNRC', 'GD', 'GIS',
  'GM', 'GPC', 'GILD', 'GPN', 'GL', 'GDDY', 'GS', 'HAL', 'HIG', 'HAS', 'HCA', 'DOC',
  'HSIC', 'HSY', 'HPE', 'HLT', 'HD', 'HONA', 'HON', 'HRL', 'HST', 'HWM', 'HPQ', 'HUBB',
  'HUM', 'HBAN', 'HII', 'IBM', 'IEX', 'IDXX', 'ITW', 'INCY', 'IR', 'PODD', 'INTC', 'IBKR',
  'ICE', 'IFF', 'IP', 'INTU', 'ISRG', 'IVZ', 'INVH', 'IQV', 'IRM', 'JBHT', 'JBL', 'JKHY',
  'J', 'JNJ', 'JCI', 'JPM', 'KVUE', 'KDP', 'KEY', 'KEYS', 'KMB', 'KIM', 'KMI', 'KKR',
  'KLAC', 'KHC', 'KR', 'LHX', 'LH', 'LRCX', 'LVS', 'LDOS', 'LEN', 'LII', 'LLY', 'LIN',
  'LYV', 'LMT', 'L', 'LOW', 'LULU', 'LITE', 'LYB', 'MTB', 'MPC', 'MAR', 'MRSH', 'MLM',
  'MRVL', 'MAS', 'MA', 'MKC', 'MCD', 'MCK', 'MDT', 'MRK', 'META', 'MET', 'MTD', 'MGM',
  'MCHP', 'MU', 'MSFT', 'MAA', 'MRNA', 'TAP', 'MDLZ', 'MPWR', 'MNST', 'MCO', 'MS', 'MOS',
  'MSI', 'MSCI', 'NDAQ', 'NTAP', 'NFLX', 'NEM', 'NWSA', 'NWS', 'NEE', 'NKE', 'NI', 'NDSN',
  'NSC', 'NTRS', 'NOC', 'NCLH', 'NRG', 'NUE', 'NVDA', 'NVR', 'NXPI', 'ORLY', 'OXY', 'ODFL',
  'OMC', 'ON', 'OKE', 'ORCL', 'OTIS', 'PCAR', 'PKG', 'PLTR', 'PANW', 'PSKY', 'PH', 'PAYX',
  'PYPL', 'PNR', 'PEP', 'PFE', 'PCG', 'PM', 'PSX', 'PNW', 'PNC', 'PPG', 'PPL', 'PFG',
  'PG', 'PGR', 'PLD', 'PRU', 'PEG', 'PTC', 'PSA', 'PHM', 'PWR', 'QCOM', 'DGX', 'Q',
  'RL', 'RJF', 'RDDT', 'RTX', 'O', 'REG', 'REGN', 'RF', 'RSG', 'RMD', 'RVTY', 'HOOD',
  'ROK', 'ROL', 'ROP', 'ROST', 'RCL', 'SPGI', 'CRM', 'SNDK', 'SBAC', 'SLB', 'STX', 'SRE',
  'NOW', 'SHW', 'SPG', 'SWKS', 'SJM', 'SW', 'SNA', 'SOLV', 'SO', 'LUV', 'SWK', 'SBUX',
  'STT', 'STLD', 'STE', 'SYK', 'SMCI', 'SYF', 'SNPS', 'SYY', 'TMUS', 'TROW', 'TTWO', 'TPR',
  'TRGP', 'TGT', 'TEL', 'TDY', 'TER', 'TSLA', 'TXN', 'TPL', 'TXT', 'TMO', 'TJX', 'TKO',
  'TTD', 'TSCO', 'TT', 'TDG', 'TRV', 'TRMB', 'TFC', 'TYL', 'TSN', 'USB', 'UBER', 'UDR',
  'ULTA', 'UNP', 'UAL', 'UPS', 'URI', 'UNH', 'UHS', 'VLO', 'VEEV', 'VTR', 'VLTO', 'VRSN',
  'VRSK', 'VZ', 'VRTX', 'VRT', 'VTRS', 'VICI', 'V', 'VST', 'VMRK', 'VMC', 'WRB', 'GWW',
  'WAB', 'WMT', 'DIS', 'WBD', 'WM', 'WAT', 'WEC', 'WFC', 'WELL', 'WST', 'WDC', 'WY',
  'WSM', 'WMB', 'WTW', 'WDAY', 'WYNN', 'XEL', 'XYL', 'YUM', 'ZBRA', 'ZBH', 'ZTS', 'ASML',
];
// Benchmark ETFs for virtual trading (GSQ-018 D-22 price route 1): S&P 500 proxy, SIC sector ETFs, comparison series and HYG/IEF credit stress inputs.
const BENCHMARK_SYMBOLS = ['SPY', 'SMH', 'XLK', 'XLV', 'XLE', 'XLB', 'XLP', 'XLY', 'XLC', 'XLU', 'XLRE', 'XLF', 'XLI', 'VUG', 'QUAL', 'HYG', 'IEF'];
const MARKETS = new Map([...US_SYMBOLS, ...BENCHMARK_SYMBOLS].map((symbol) => [symbol, { currency: 'USD', timezone: 'America/New_York' }]));
MARKETS.set('042700.KS', { currency: 'KRW', timezone: 'Asia/Seoul' });
MARKETS.set('8035.T', { currency: 'JPY', timezone: 'Asia/Tokyo' });
// FX for the KRW virtual ledger (USD/KRW, JPY/KRW). Device RAM only; Yahoo quotes currencies on the London-time CCY venue.
const FX_SYMBOLS = ['KRW=X', 'JPYKRW=X'];
for (const symbol of FX_SYMBOLS) MARKETS.set(symbol, { currency: 'KRW', timezone: 'Europe/London' });
const RANGES = new Set(['1mo', '3mo', '6mo', '1y', '2y', '5y']);
const MAX_BODY_BYTES = 512 * 1024;
const MAX_BARS = 1500;
const MIN_SPACING_MS = 5000;
const WINDOW_MS = 60_000;
// After admission, every upstream read of the request (GitHub contents, the release asset API and the asset bytes, Yahoo and its
// fallbacks) runs inside one deadline (owner 2026-11-28): each call keeps its own timeout, cut to the time left, and at the
// deadline plus a short grace the request's upstream reads and bodies are aborted. The lease therefore outlives every live
// request (deadline + grace + the release call), and a request the runtime kills (CPU limit, error 1102; no finally, no
// release) frees the slot LEASE_MS after its admission. Spacing and the per-minute cap are unchanged.
const LEASE_MS = 15_000;
const UPSTREAM_DEADLINE_MS = 10_000;
const UPSTREAM_ABORT_GRACE_MS = 250;
const LIMITER_TIMEOUT_MS = 2000;
export const LIMITER_TIMING = Object.freeze({ LEASE_MS, UPSTREAM_DEADLINE_MS, UPSTREAM_ABORT_GRACE_MS, LIMITER_TIMEOUT_MS, MIN_SPACING_MS, WINDOW_MS });
// Workers fetch throws a TypeError for redirect 'error' and for cache 'no-store' with any cf.cacheTtl other than -1.
// 'no-store' already bypasses the edge cache. Redirect answers are rejected in upstreamFetch and are never followed.
const NO_CACHE = { cache: 'no-store', cf: { cacheEverything: false }, redirect: 'manual' };

class Failure extends Error {
  constructor(code, status) { super(code); this.code = code; this.status = status; }
}

async function closeAndFail(response, code, status) {
  try { await response.body?.cancel(); } catch { /* Return only the fixed error. */ }
  throw new Failure(code, status);
}

function headers(origin) {
  const result = new Headers({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'private, no-store, max-age=0',
    'Vary': 'Origin',
    'X-Content-Type-Options': 'nosniff',
  });
  if (origin === ORIGIN) result.set('Access-Control-Allow-Origin', ORIGIN);
  return result;
}

function failureResponse(error, origin, extraHeaders = {}) {
  const responseHeaders = headers(origin);
  for (const [key, value] of Object.entries(extraHeaders)) responseHeaders.set(key, value);
  return new Response(JSON.stringify({ error: { code: error.code } }), { status: error.status, headers: responseHeaders });
}

function positiveInteger(value) {
  const number = typeof value === 'number' ? value : typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : NaN;
  return Number.isSafeInteger(number) && number > 0 ? number : null;
}

function validateQuery(url) {
  // Reject alternate encodings, empty fields, duplicates, and every extra parameter. '=' (FX symbols) only as %3D.
  if (url.hash || !/^\?(?:symbol=(?:[A-Z0-9.\-]|%3D)+&range=[a-z0-9]+|range=[a-z0-9]+&symbol=(?:[A-Z0-9.\-]|%3D)+)$/.test(url.search)) {
    throw new Failure('REQUEST_INVALID', 400);
  }
  const symbol = url.searchParams.get('symbol');
  const range = url.searchParams.get('range');
  if (!MARKETS.has(symbol) || !RANGES.has(range)) throw new Failure('REQUEST_INVALID', 400);
  return { symbol, range };
}

async function readJson(response, limit, invalidCode, oversizedCode, status) {
  const advertised = response.headers.get('Content-Length');
  if (advertised && /^\d+$/.test(advertised) && Number(advertised) > limit) {
    await response.body?.cancel();
    throw new Failure(oversizedCode, status);
  }
  if (!response.body) throw new Failure(invalidCode, status);
  const reader = response.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > limit) {
        await reader.cancel();
        throw new Failure(oversizedCode, status);
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new Failure(invalidCode, status); }
}

function sessionStatus(timestamp, regular, readAt) {
  if (!regular || !Number.isSafeInteger(regular.start) || !Number.isSafeInteger(regular.end)
    || regular.start <= 0 || regular.end <= regular.start || regular.end - regular.start > 86400) return 'UNKNOWN';
  const nowSeconds = Math.floor(readAt / 1000);
  if (timestamp > nowSeconds || timestamp >= regular.end) return 'UNKNOWN';
  if (timestamp < regular.start || nowSeconds >= regular.end) return 'COMPLETE';
  return nowSeconds >= regular.start ? 'IN_PROGRESS' : 'UNKNOWN';
}

function normalizeHistory(payload, symbol, range, readAt) {
  const invalid = () => { throw new Failure('YAHOO_FORMAT_CHANGED', 502); };
  const unavailable = () => { throw new Failure('HISTORY_UNAVAILABLE', 404); };
  const chart = payload?.chart;
  if (!chart || typeof chart !== 'object' || Array.isArray(chart)) invalid();
  if (chart.error != null || chart.result === null || (Array.isArray(chart.result) && chart.result.length === 0)) unavailable();
  if (!Array.isArray(chart.result) || chart.result.length !== 1) invalid();
  const result = chart.result[0];
  const meta = result?.meta;
  const market = MARKETS.get(symbol);
  if (!meta || meta.symbol !== symbol || meta.currency !== market.currency || meta.exchangeTimezoneName !== market.timezone
    || typeof meta.exchangeName !== 'string' || !/^[A-Za-z0-9._ -]{1,40}$/.test(meta.exchangeName)
    || meta.dataGranularity !== '1d') invalid();
  const timestamps = result.timestamp;
  if (!Array.isArray(timestamps)) invalid();
  if (timestamps.length === 0) unavailable();
  if (timestamps.length > MAX_BARS) throw new Failure('YAHOO_TOO_LARGE', 502);
  const quotes = result.indicators?.quote;
  if (!Array.isArray(quotes) || quotes.length !== 1 || !quotes[0] || typeof quotes[0] !== 'object') invalid();
  const quote = quotes[0];
  for (const key of ['open', 'high', 'low', 'close', 'volume']) {
    if (!Array.isArray(quote[key]) || quote[key].length !== timestamps.length) invalid();
  }
  let adjusted = null;
  if (result.indicators.adjclose !== undefined) {
    const series = result.indicators.adjclose;
    if (!Array.isArray(series) || series.length !== 1 || !Array.isArray(series[0]?.adjclose) || series[0].adjclose.length !== timestamps.length) invalid();
    adjusted = series[0].adjclose;
  }
  let previous = 0, hasClose = false;
  const price = (value) => {
    if (value === null) return null;
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) invalid();
    return value;
  };
  const volume = (value) => {
    if (value === null) return null;
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) invalid();
    return value;
  };
  const bars = timestamps.map((timestamp, index) => {
    if (!Number.isSafeInteger(timestamp) || timestamp <= previous || timestamp > Math.floor(readAt / 1000)) invalid();
    previous = timestamp;
    const close = price(quote.close[index]);
    hasClose ||= close !== null;
    return {
      timestamp, open: price(quote.open[index]), high: price(quote.high[index]), low: price(quote.low[index]), close,
      adjusted_close: adjusted ? price(adjusted[index]) : null, volume: volume(quote.volume[index]),
      session_status: sessionStatus(timestamp, meta.currentTradingPeriod?.regular, readAt),
    };
  });
  if (!hasClose) unavailable();
  return {
    schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: market.currency,
    exchange: meta.exchangeName, timezone: market.timezone, interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN',
    read_at: new Date(readAt).toISOString(), bars,
  };
}

// Provider dates are session labels, not intraday execution timestamps.
function calendarDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const time = Date.parse(value + 'T00:00:00Z');
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? value : null;
}

function localDate(time, timezone) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(time);
  const get = (name) => parts.find((p) => p.type === name).value;
  return get('year') + '-' + get('month') + '-' + get('day');
}

function dateWindow(range, readAt, timezone) {
  const end = localDate(readAt, timezone), date = new Date(end + 'T00:00:00Z'), day = date.getUTCDate();
  date.setUTCDate(1);
  date.setUTCMonth(date.getUTCMonth() - ({ '1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60 })[range]);
  const last = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
  date.setUTCDate(Math.min(day, last));
  return { start: date.toISOString().slice(0, 10), end };
}

function fallbackBar(row, day, end, code, adjusted = null) {
  const invalid = () => { throw new Failure(code, 502); };
  const fields = ['open', 'high', 'low', 'close'];
  if (!calendarDate(day) || !fields.every((k) => typeof row[k] === 'number' && Number.isFinite(row[k]) && row[k] > 0)
    || row.low > Math.min(row.open, row.close) || row.high < Math.max(row.open, row.close) || row.low > row.high
    || typeof row.volume !== 'number' || !Number.isFinite(row.volume) || row.volume < 0
    || (adjusted !== null && (typeof adjusted !== 'number' || !Number.isFinite(adjusted) || adjusted <= 0))) invalid();
  return { timestamp: Date.parse(day + 'T00:00:00Z') / 1000, session_date: day,
    open: row.open, high: row.high, low: row.low, close: row.close, adjusted_close: adjusted, volume: row.volume,
    session_status: day < end ? 'COMPLETE' : 'UNKNOWN' };
}

function fallbackResult(provider, symbol, range, readAt, exchange, bars) {
  if (!bars.length) throw new Failure('HISTORY_UNAVAILABLE', 404);
  const market = MARKETS.get(symbol);
  return { schema: 'private-history/1', provider, symbol, range, currency: market.currency, exchange,
    timezone: market.timezone, interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN',
    timestamp_kind: 'PROVIDER_SESSION_LABEL', read_at: new Date(readAt).toISOString(), bars };
}

function providerSecret(env, name) {
  const value = env[name];
  return typeof value === 'string' && /^[\x21-\x7e]{1,4096}$/.test(value) ? value : null;
}

function krxNumber(value) {
  if (typeof value !== 'string' || !/^(?:\d+|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d+)?$/.test(value)) throw new Failure('KRX_FORMAT_CHANGED', 502);
  const result = Number(value.replaceAll(',', ''));
  if (!Number.isFinite(result)) throw new Failure('KRX_FORMAT_CHANGED', 502);
  return result;
}

// ---------- Private KIS area (design PRIVATE_AREA_KIS_DESIGN_20261031.md §5.5 / §17.2, PRIVATE_AREA_NO_ZT_ACCESS_20261031.md §4) ----------
// Two routes, both behind the same Google owner check and rate limiter as /history: GET /kis/status and GET /kis/stock.
// The four older per-file routes (/kis/chart, /kis/analysis, /kis/technical, /kis/qgv), which no panel has read since the
// 2026-11-20 screen switch, are gone (owner 2026-11-26): they are unknown paths now, ROUTE_NOT_FOUND 404 before any check.
// /kis/status reads status/private-area.json (private-area-status/1, WORKER_READ_TOKEN_EXPIRY_20261115.md, DC-53) of the data
// branch of the private repository with a read-only token and answers only the rebuilt expiry fields and a fixed state code.
// GET /kis/stock?symbol=<KEY> (kis-stock-view/1, KIS_STOCK_VIEW_RELEASES_20261120.md §1, §5) or ?part=qgv. The query is exactly
// one of those two strings: KEY matches ^[A-Z][A-Z0-9-]{0,9}$, with no other parameter, no fragment and no alternate encoding.
// The Worker keeps no list of symbols: the key is checked for its syntax only, and whether it is served is decided only by the
// pinned shard of the published generation (or, while that root is absent, by the single index's entry). A key that is not
// there is KIS_SERIES_NOT_FOUND (404).
// The stock route is the one redirect exception (owner 2026-11-20): only the asset API's 302 to release-assets.githubusercontent.com
// is followed, exactly once and with no credentials. Every other upstream call keeps upstreamFetch / github() and their
// redirect refusal unchanged. Nothing is cached, logged or followed otherwise; the token, its expiry variable and every
// upstream body stay out of every response.
const KIS_REPO = 'kco994553-star/investment-system1-kis-private';
const KIS_BRANCH = 'data';
const GITHUB_API = 'https://api.github.com';
const DAY_MS = 86_400_000;

// ---------- /kis/stock: one stock's complete view from a private release asset ----------
const KIS_STOCK_ROUTE = '/kis/stock';
const KIS_STOCK_INDEX_PATH = 'views/kis-stock-index.json';
// The one other answer of the stock route (owner 2026-11-21): the index's QGV object, the same release generation.
const KIS_STOCK_QGV_QUERY = '?part=qgv';
const KIS_STOCK_INDEX_MAX_BYTES = 262_144;
// The producer's uncompressed limit (#571); the gzip object is never larger either.
const KIS_STOCK_MAX_BYTES = 1_800_000;
const KIS_ASSET_HOST = 'release-assets.githubusercontent.com';
const HEX64 = /^[0-9a-f]{64}$/;
const plainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const exactKeys = (v, keys) => plainObject(v) && Object.keys(v).length === keys.length && keys.every((k) => Object.hasOwn(v, k));
const pinnedSize = (v) => Number.isSafeInteger(v) && v > 0 && v <= KIS_STOCK_MAX_BYTES;
const hex64 = (v) => typeof v === 'string' && HEX64.test(v);

function kisAssetEntryValid(v, withSymbol) {
  const keys = ['asset_id', 'name', 'bytes', 'sha256', 'json_bytes', 'json_sha256'];
  if (withSymbol) keys.push('symbol');
  return exactKeys(v, keys) && Number.isSafeInteger(v.asset_id) && v.asset_id > 0
    && typeof v.name === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$/.test(v.name)
    && pinnedSize(v.bytes) && pinnedSize(v.json_bytes) && hex64(v.sha256) && hex64(v.json_sha256)
    && (!withSymbol || (typeof v.symbol === 'string' && /^[A-Z][A-Z0-9./_-]{0,15}$/.test(v.symbol)));
}

// kis-stock-asset-index/1, the top level and the one entry this request needs (owner 2026-11-21 proposal A, CPU on the free
// plan): exact top-level keys, schema, scope, day, tag, generation and the qgv entry; then, for a stock request, the requested
// key's own entry (its presence is the only membership rule), its exact keys and ranges, and an asset id other than the qgv
// one. The other entries are not read here: the publish workflow checks every entry's shape and that every asset id is
// distinct before it writes the index, and each answer is still held to its own size and sha256 pins below. Returns the entry, 'MISSING' or 'INVALID'.
export function kisStockIndexEntry(value, symbol) {
  if (!exactKeys(value, ['schema', 'publication_scope', 'evaluation_day', 'release_tag', 'generation_sha256', 'stocks', 'qgv'])
    || value.schema !== 'kis-stock-asset-index/1' || value.publication_scope !== 'OWNER_PRIVATE_ONLY'
    || calendarDate(value.evaluation_day) === null
    || typeof value.release_tag !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value.release_tag)
    || !hex64(value.generation_sha256) || !plainObject(value.stocks) || !kisAssetEntryValid(value.qgv, false)) return 'INVALID';
  if (symbol === null) return value.qgv;
  if (!Object.hasOwn(value.stocks, symbol)) return 'MISSING';
  const entry = value.stocks[symbol];
  return kisAssetEntryValid(entry, true) && entry.asset_id !== value.qgv.asset_id ? entry : 'INVALID';
}

// ---------- /kis/stock bundle path (owner 2026-11-22: GitHub private release bundles + 64 index shards) ----------
// views/kis-stock-packs.json (kis-stock-pack-root/1) names one generation, its qgv asset, its bundle assets (sha256 → asset id,
// bytes) and the size and sha256 of each of the 64 shards views/kis-stock-packs/NN.json (kis-stock-pack-shard/1). A shard maps
// a symbol to [bundle, offset, length, sha256, json_bytes, json_sha256]; the Worker reads that member alone with one Range
// request on the same single release-asset redirect and returns its gzip bytes. While the root file is absent (404) the
// single index above is read exactly as before, so this reader can be deployed before any bundle is published.
const KIS_PACK_ROOT_PATH = 'views/kis-stock-packs.json';
const KIS_PACK_SHARD_DIR = 'views/kis-stock-packs/';
const KIS_PACK_BUCKETS = 64;
const KIS_PACK_SHARD_MAX_BYTES = 262_144;
const KIS_PACK_MAX_BYTES = 1_800_000;
const GENERATION_KEYS = ['publication_scope', 'evaluation_day', 'release_tag', 'generation_sha256'];

// The root's top level, the qgv entry and the one shard pin and bundle a request needs (the publish workflow checks the rest).
export function kisPackRoot(value) {
  if (!exactKeys(value, ['schema', ...GENERATION_KEYS, 'buckets', 'bucket_rule', 'qgv', 'packs', 'shards'])
    || value.schema !== 'kis-stock-pack-root/1' || value.publication_scope !== 'OWNER_PRIVATE_ONLY'
    || calendarDate(value.evaluation_day) === null
    || typeof value.release_tag !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value.release_tag)
    || !hex64(value.generation_sha256) || value.buckets !== KIS_PACK_BUCKETS || value.bucket_rule !== 'sha256(symbol)[0]>>2'
    || !kisAssetEntryValid(value.qgv, false) || !plainObject(value.packs) || !plainObject(value.shards)) return null;
  return value;
}

export async function kisPackBucket(symbol) {
  return parseInt((await sha256Hex(new TextEncoder().encode(symbol))).slice(0, 2), 16) >> 2;
}
export const kisPackShardName = (bucket) => String(bucket).padStart(2, '0') + '.json';

export function kisPackShardPin(root, bucket) {
  const pin = root.shards[kisPackShardName(bucket)];
  return exactKeys(pin, ['bytes', 'sha256']) && Number.isSafeInteger(pin.bytes) && pin.bytes > 0
    && pin.bytes <= KIS_PACK_SHARD_MAX_BYTES && hex64(pin.sha256) ? pin : null;
}

// The requested member of a pinned shard: the entry with its bundle's asset id and size, 'MISSING' or 'INVALID'. The shard's
// own stock map is the only membership rule: a syntactically valid key that is not there is 'MISSING'.
export function kisPackMember(shard, root, bucket, symbol) {
  if (!exactKeys(shard, ['schema', ...GENERATION_KEYS, 'bucket', 'stocks']) || shard.schema !== 'kis-stock-pack-shard/1'
    || GENERATION_KEYS.some((k) => shard[k] !== root[k]) || shard.bucket !== bucket || !plainObject(shard.stocks)) return 'INVALID';
  if (!Object.hasOwn(shard.stocks, symbol)) return 'MISSING';
  const e = shard.stocks[symbol];
  if (!exactKeys(e, ['pack', 'offset', 'bytes', 'sha256', 'json_bytes', 'json_sha256']) || !hex64(e.pack) || !Object.hasOwn(root.packs, e.pack)
    || !Number.isSafeInteger(e.offset) || e.offset < 0 || !pinnedSize(e.bytes) || !pinnedSize(e.json_bytes)
    || !hex64(e.sha256) || !hex64(e.json_sha256)) return 'INVALID';
  const pack = root.packs[e.pack];
  if (!exactKeys(pack, ['asset_id', 'bytes']) || !Number.isSafeInteger(pack.asset_id) || pack.asset_id <= 0
    || pack.asset_id === root.qgv.asset_id || !Number.isSafeInteger(pack.bytes) || pack.bytes <= 0 || pack.bytes > KIS_PACK_MAX_BYTES
    || e.offset + e.bytes > pack.bytes) return 'INVALID';
  return { asset_id: pack.asset_id, pack_bytes: pack.bytes, offset: e.offset, bytes: e.bytes, sha256: e.sha256 };
}

// A Range answer is accepted only as 206 with exactly 'bytes <first>-<last>/<bundle size>' for the requested member.
export function kisRangeAnswerOk(response, member) {
  const last = member.offset + member.bytes - 1;
  return response.status === 206 && response.headers.get('Content-Range') === 'bytes ' + member.offset + '-' + last + '/' + member.pack_bytes;
}

// The asset API's answer. Only a 302 whose Location is an absolute https URL on exactly the release asset host (default port,
// no user info) is accepted; the normalised URL is returned. Anything else is null.
export function kisAssetRedirectTarget(response) {
  if (response.status !== 302 || response.type === 'opaqueredirect' || response.redirected === true) return null;
  const location = response.headers.get('Location');
  if (typeof location !== 'string' || location.length > 8192 || !/^[\x21-\x7e]+$/.test(location)
    || !location.startsWith('https://' + KIS_ASSET_HOST + '/')) return null;
  let url;
  try { url = new URL(location); } catch { return null; }
  if (url.protocol !== 'https:' || url.hostname !== KIS_ASSET_HOST || url.port !== '' || url.username !== '' || url.password !== '') return null;
  return url.href;
}

// Reads a stream up to limit bytes; one byte more cancels it (overCode, 502). A broken stream is brokenCode.
async function readCapped(stream, limit, overCode, brokenCode, brokenStatus) {
  const reader = stream.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      let step;
      try { step = await reader.read(); } catch { throw new Failure(brokenCode, brokenStatus); }
      if (step.done) break;
      length += step.value.byteLength;
      if (length > limit) {
        try { await reader.cancel(); } catch { /* Return only the fixed error. */ }
        throw new Failure(overCode, 502);
      }
      chunks.push(step.value);
    }
  } finally { try { reader.releaseLock(); } catch { /* Already released. */ } }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}

// A pinned body (shard, member): with Content-Length exactly the pin, one native whole-body read (CPU: no per-chunk loop in the
// isolate); otherwise the capped loop above, so a missing or other Content-Length still reads at most the pin. The caller then
// checks the size and the sha256 pin as before. A read failure is brokenCode either way.
async function readPinned(response, pinned, overCode, brokenCode, brokenStatus) {
  if (response.headers.get('Content-Length') === String(pinned)) {
    let buffer;
    try { buffer = await response.arrayBuffer(); } catch { throw new Failure(brokenCode, brokenStatus); }
    return new Uint8Array(buffer);
  }
  return readCapped(response.body, pinned, overCode, brokenCode, brokenStatus);
}

async function sha256Hex(bytes) {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('');
}

// Today as an Asia/Seoul calendar date (UTC+9, no daylight saving), 'YYYY-MM-DD'.
export function seoulToday(nowMs) { return new Date(nowMs + 9 * 3_600_000).toISOString().slice(0, 10); }

// The read token's recorded expiry (§4.4 rows 1–2 and the OK / EXPIRING tail). The date is rebuilt by the Worker; the raw
// variable is never echoed. Exact NEVER is the owner's explicit no-expiry setting; absence is still invalid.
export function kisTokenDate(env, nowMs) {
  const token = env.PRIVATE_REPO_READ_TOKEN;
  if (typeof token !== 'string' || !/^[\x21-\x7e]{1,4096}$/.test(token)) return { state: 'UNSET', code: 'TOKEN_UNSET', expires_on: null, days_left: null };
  const raw = env.PRIVATE_REPO_READ_TOKEN_EXPIRES_ON;
  if (typeof raw === 'string' && /^(?:github_pat_|ghp_|gho_|ghu_|ghs_|ghr_)/.test(raw.trim())) return { state: 'UNSET', code: 'TOKEN_DATE_IS_TOKEN', expires_on: null, days_left: null };
  if (raw === 'NEVER') return { state: 'NO_EXPIRY', code: null, expires_on: null, days_left: null };
  const m = typeof raw === 'string' ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw) : null;
  const date = m ? new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))) : null;
  const today = seoulToday(nowMs), todayMs = Date.parse(today + 'T00:00:00Z');
  if (!date || date.toISOString().slice(0, 10) !== raw || date.getTime() > todayMs + 367 * DAY_MS) return { state: 'UNSET', code: 'TOKEN_DATE_INVALID', expires_on: null, days_left: null };
  const expiresOn = date.toISOString().slice(0, 10), daysLeft = Math.round((date.getTime() - todayMs) / DAY_MS);
  if (daysLeft <= 0) return { state: 'EXPIRED', code: 'TOKEN_EXPIRED', expires_on: expiresOn, days_left: daysLeft };
  return { state: daysLeft <= 14 ? 'EXPIRING' : 'OK', code: null, expires_on: expiresOn, days_left: daysLeft };
}

// One GitHub answer to the read token's state (§4.4 rows 3–7). null means "fine, use the body". A 401 is a near-expiry only for a
// dated token within two days of its date; for a NEVER token (days_left null) it is always TOKEN_REJECTED, never a guessed expiry.
export function kisUpstreamState(response, tokenDate) {
  const s = response.status;
  if (s >= 200 && s <= 299) return null;
  if (response.type === 'opaqueredirect' || s === 0 || (s >= 300 && s <= 399)) return { state: 'ERROR', code: 'REPO_MOVED', http: 502 };
  if (s === 401) return tokenDate.days_left !== null && tokenDate.days_left <= 2 ? { state: 'EXPIRED', code: 'TOKEN_EXPIRED', http: 503 } : { state: 'REJECTED', code: 'TOKEN_REJECTED', http: 503 };
  if (s === 403 || s === 429) {
    const limited = response.headers.get('x-ratelimit-remaining') === '0' || response.headers.has('retry-after');
    return limited ? { state: 'RATE_LIMITED', code: 'UPSTREAM_RATE_LIMITED', http: 503 } : { state: 'REJECTED', code: 'TOKEN_REJECTED', http: 503 };
  }
  return { state: 'ERROR', code: 'UPSTREAM_UNAVAILABLE', http: 503 };
}

// /kis/stock?symbol=<KEY> only (no other parameter, no fragment, no alternate encoding: the raw query string itself must match).
// Syntax only; membership is decided by the pinned shard or the single index entry.
export function kisStockSymbol(url) {
  if (url.hash || !/^\?symbol=[A-Z][A-Z0-9-]{0,9}$/.test(url.search)) throw new Failure('REQUEST_INVALID', 400);
  return url.search.slice('?symbol='.length);
}

export function createHandler({ fetch: fetchImpl = globalThis.fetch, now = Date.now, setTimeout: schedule = globalThis.setTimeout, clearTimeout: cancel = globalThis.clearTimeout } = {}) {
  async function timed(milliseconds, code, status, operation) {
    const controller = new AbortController();
    let timer;
    const deadline = new Promise((_, reject) => {
      timer = schedule(() => { controller.abort(); reject(new Failure(code, status)); }, milliseconds);
    });
    try { return await Promise.race([operation(controller.signal), deadline]); }
    finally { cancel(timer); }
  }

  // The post-admission upstream phase of one request: until = its deadline; signal aborts at the deadline plus the grace (a
  // backstop for a body still streaming); end() at the request's end, before the release.
  function startPhase() {
    const controller = new AbortController();
    const timer = schedule(() => controller.abort(), UPSTREAM_DEADLINE_MS + UPSTREAM_ABORT_GRACE_MS);
    return { until: now() + UPSTREAM_DEADLINE_MS, signal: controller.signal, end() { cancel(timer); } };
  }
  // One upstream call inside the phase: its own timeout cut to the time left (none left: the call's own timeout failure, not
  // started), and its signal also aborted by the phase.
  function bounded(phase, milliseconds, code, status, operation) {
    const left = Math.min(milliseconds, phase.until - now());
    if (!(left > 0)) return Promise.reject(new Failure(code, status));
    return timed(left, code, status, (signal) => operation(AbortSignal.any([signal, phase.signal])));
  }

  // Every upstream request. A 3xx, an opaque redirect (status 0) or a followed redirect gets the same fixed error
  // as a failed upstream answer. The Location is never read or fetched and the body is never passed through.
  async function upstreamFetch(url, init, code, status) {
    const response = await fetchImpl(url, { ...init, ...NO_CACHE });
    const redirect = response.type === 'opaqueredirect' || response.redirected === true || response.status === 0
      || (response.status >= 300 && response.status <= 399);
    return redirect ? closeAndFail(response, code, status) : response;
  }

  async function authenticate(request, env) {
    if (typeof env.ALLOWED_EMAIL !== 'string' || !env.ALLOWED_EMAIL || env.ALLOWED_EMAIL.trim() !== env.ALLOWED_EMAIL
      || typeof env.GOOGLE_CLIENT_ID !== 'string' || !env.GOOGLE_CLIENT_ID || env.GOOGLE_CLIENT_ID.trim() !== env.GOOGLE_CLIENT_ID) throw new Failure('CONFIG_UNAVAILABLE', 503);
    const authorization = request.headers.get('Authorization');
    if (!authorization || authorization.length > 8192 || !/^Bearer [A-Za-z0-9._~+\/-]+=*$/i.test(authorization)) throw new Failure('AUTH_FORBIDDEN', 403);
    let info;
    try {
      info = await timed(5000, 'AUTH_UNAVAILABLE', 503, async (signal) => {
        const response = await upstreamFetch(TOKENINFO_URL, {
          method: 'POST', signal,
          headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', Authorization: authorization },
        }, 'AUTH_UNAVAILABLE', 503);
        if ([400, 401, 403].includes(response.status)) return closeAndFail(response, 'AUTH_FORBIDDEN', 403);
        if (!response.ok) return closeAndFail(response, 'AUTH_UNAVAILABLE', 503);
        return readJson(response, 32 * 1024, 'AUTH_UNAVAILABLE', 'AUTH_UNAVAILABLE', 503);
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure('AUTH_UNAVAILABLE', 503);
    }
    if (!info || info.aud !== env.GOOGLE_CLIENT_ID || info.email !== env.ALLOWED_EMAIL
      || ![true, 'true'].includes(info.email_verified) || positiveInteger(info.expires_in) === null
      || (Object.hasOwn(info, 'exp') && (positiveInteger(info.exp) === null || Number(info.exp) <= Math.floor(now() / 1000)))) throw new Failure('AUTH_FORBIDDEN', 403);
  }

  async function admit(env) {
    try {
      const namespace = env.HISTORY_RATE_LIMITER;
      const stub = namespace.get(namespace.idFromName('history-owner-v1'));
      const { status, result } = await timed(LIMITER_TIMEOUT_MS, 'RATE_LIMIT_UNAVAILABLE', 503, async (signal) => {
        const response = await stub.fetch('https://history-rate.internal/admit', { method: 'POST', signal });
        return { status: response.status, result: await response.json() };
      });
      if (status === 429 && result.allowed === false && positiveInteger(result.retry_after) !== null) {
        return { denied: true, retryAfter: result.retry_after };
      }
      if (status !== 200 || result.allowed !== true || positiveInteger(result.lease) === null) throw new Error();
      return { stub, lease: result.lease };
    } catch { throw new Failure('RATE_LIMIT_UNAVAILABLE', 503); }
  }

  async function history(symbol, range, phase) {
    try {
      return await bounded(phase, 10_000, 'YAHOO_TIMEOUT', 504, async (signal) => {
        const response = await upstreamFetch(`${YAHOO_ROOT}${symbol}?interval=1d&range=${range}`, {
          method: 'GET', signal, headers: { Accept: 'application/json' },
        }, 'YAHOO_UNAVAILABLE', 503);
        if ([401, 403, 429].includes(response.status)) return closeAndFail(response, 'YAHOO_BLOCKED', 502);
        if (response.status === 404) return closeAndFail(response, 'HISTORY_UNAVAILABLE', 404);
        if (!response.ok) return closeAndFail(response, 'YAHOO_UNAVAILABLE', 503);
        const payload = await readJson(response, MAX_BODY_BYTES, 'YAHOO_FORMAT_CHANGED', 'YAHOO_TOO_LARGE', 502);
        return normalizeHistory(payload, symbol, range, now());
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure('YAHOO_UNAVAILABLE', 503);
    }
  }

  async function fallbackHistory(symbol, range, env, yahooError, phase) {
    const provider = US_SYMBOLS.includes(symbol) || BENCHMARK_SYMBOLS.includes(symbol) ? 'TIINGO' : symbol === '042700.KS' ? 'KRX' : null;
    const secret = provider && providerSecret(env, provider + '_API_KEY');
    // Existing installs remain Yahoo-only until the corresponding Secret is set.
    if (!secret || !yahooError || !(yahooError.code.startsWith('YAHOO_') || yahooError.code === 'HISTORY_UNAVAILABLE')) throw yahooError;
    if (provider === 'KRX' && range !== '1mo') throw new Failure('KRX_RANGE_UNSUPPORTED', 422);
    // No upstream time left after Yahoo (the post-admission deadline): Yahoo's own answer, no fallback request.
    if (!(phase.until - now() > 0)) throw yahooError;
    const readAt = now(), window = dateWindow(range, readAt, MARKETS.get(symbol).timezone);
    try {
      return await bounded(phase, 15_000, provider + '_TIMEOUT', 504, async (signal) => {
        const request = async (url, limit = MAX_BODY_BYTES) => {
          if (signal.aborted) throw new Failure(provider + '_TIMEOUT', 504);
          const response = await upstreamFetch(url, { method: 'GET', signal,
            headers: provider === 'TIINGO' ? { Accept: 'application/json', Authorization: 'Token ' + secret } : { Accept: 'application/json', AUTH_KEY: secret } },
          provider + '_UNAVAILABLE', 503);
          if (!response.ok) return closeAndFail(response, provider + '_UNAVAILABLE', 503);
          return readJson(response, limit, provider + '_FORMAT_CHANGED', provider + '_TOO_LARGE', 502);
        };
        if (provider === 'TIINGO') {
          const root = 'https://api.tiingo.com/tiingo/daily/' + symbol.toLowerCase();
          const meta = await request(root, 32 * 1024);
          if (!meta || typeof meta.ticker !== 'string' || meta.ticker.toUpperCase() !== symbol
            || !['NASDAQ', 'NYSE', 'NYSE ARCA', 'NYSE MKT', 'BATS'].includes(meta.exchangeCode)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
          const rows = await request(root + '/prices?startDate=' + window.start + '&endDate=' + window.end + '&resampleFreq=daily');
          if (!Array.isArray(rows)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
          if (rows.length > MAX_BARS) throw new Failure('TIINGO_TOO_LARGE', 502);
          let previous = '';
          const bars = rows.map((row) => {
            if (!row || typeof row.date !== 'string' || !/^\d{4}-\d{2}-\d{2}T00:00:00(?:\.000)?Z$/.test(row.date)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
            const day = row.date.slice(0, 10);
            if (day <= previous || day < window.start || day > window.end) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
            previous = day;
            return fallbackBar(row, day, window.end, 'TIINGO_FORMAT_CHANGED', row.adjClose === undefined ? null : row.adjClose);
          });
          return fallbackResult('Tiingo EOD', symbol, range, readAt, meta.exchangeCode, bars);
        }
        const bars = [], start = Date.parse(window.start + 'T00:00:00Z'), end = Date.parse(window.end + 'T00:00:00Z');
        // One market-wide response per calendar day. No long-range truncation or cache.
        if ((end - start) / 86400000 + 1 > 32) throw new Failure('KRX_RANGE_UNSUPPORTED', 422);
        for (let time = start; time <= end; time += 86400000) {
          const date = new Date(time);
          if ([0, 6].includes(date.getUTCDay())) continue;
          const day = date.toISOString().slice(0, 10), compact = day.replaceAll('-', '');
          const payload = await request('https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd?basDd=' + compact, 1024 * 1024);
          if (!payload || !Array.isArray(payload.OutBlock_1) || payload.OutBlock_1.length > 5000) throw new Failure('KRX_FORMAT_CHANGED', 502);
          const rows = payload.OutBlock_1.filter((row) => row && row.ISU_CD === '042700');
          if (rows.length > 1) throw new Failure('KRX_FORMAT_CHANGED', 502);
          if (!rows.length) continue; // Holidays and missing listings remain absent.
          const row = rows[0];
          if (row.BAS_DD !== compact || row.MKT_NM !== 'KOSPI') throw new Failure('KRX_FORMAT_CHANGED', 502);
          bars.push(fallbackBar({ open: krxNumber(row.TDD_OPNPRC), high: krxNumber(row.TDD_HGPRC), low: krxNumber(row.TDD_LWPRC),
            close: krxNumber(row.TDD_CLSPRC), volume: krxNumber(row.ACC_TRDVOL) }, day, window.end, 'KRX_FORMAT_CHANGED'));
        }
        return fallbackResult('KRX OPEN API', symbol, range, readAt, 'KOSPI', bars);
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure(provider + '_UNAVAILABLE', 503);
    }
  }

  // One GET to the private repository with the read token. Redirects are never followed (upstreamFetch keeps redirect
  // 'manual' and turns a 3xx into REPO_MOVED below); network failures and time-outs are UPSTREAM_UNAVAILABLE.
  async function github(path, env, accept, phase) {
    try {
      return await bounded(phase, 8000, 'UPSTREAM_UNAVAILABLE', 503, (signal) => fetchImpl(GITHUB_API + path, {
        method: 'GET', signal, ...NO_CACHE,
        headers: { Accept: accept, Authorization: 'Bearer ' + env.PRIVATE_REPO_READ_TOKEN, 'User-Agent': 'investment-system1-private-worker', 'X-GitHub-Api-Version': '2022-11-28' },
      }));
    } catch { return null; }
  }
  const kisFailure = (state) => new Failure(state.code, state.http);
  const json200 = (value, origin) => new Response(JSON.stringify(value), { status: 200, headers: headers(origin) });

  async function kisStatus(env, origin, phase) {
    const date = kisTokenDate(env, now());
    if (date.state === 'UNSET' || date.state === 'EXPIRED') return json200({ schema: 'kis-status/1', ...date }, origin);
    // Contents access is required: Metadata permission alone must not report a usable read token.
    const response = await github('/repos/' + KIS_REPO + '/contents/status/private-area.json?ref=' + KIS_BRANCH, env, 'application/vnd.github.raw+json', phase);
    if (!response) return json200({ schema: 'kis-status/1', ...date, state: 'ERROR', code: 'UPSTREAM_UNAVAILABLE' }, origin);
    const bad = response.status === 404 ? { state: 'REJECTED', code: 'TOKEN_NO_ACCESS' } : kisUpstreamState(response, date);
    if (bad) {
      try { await response.body?.cancel(); } catch { /* Never echo an upstream body. */ }
      return json200({ schema: 'kis-status/1', ...date, state: bad.state, code: bad.code }, origin);
    }
    let record;
    try { record = await readJson(response, 16384, 'TOKEN_STATUS_INVALID', 'TOKEN_STATUS_INVALID', 502); }
    catch { return json200({ schema: 'kis-status/1', ...date, state: 'ERROR', code: phase.signal.aborted ? 'UPSTREAM_UNAVAILABLE' : 'TOKEN_STATUS_INVALID' }, origin); }
    const recorded = record?.worker_read_token;
    const captured = typeof record?.run_at === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(record.run_at) ? Date.parse(record.run_at) : NaN;
    if (record?.schema !== 'private-area-status/1' || record.publication_scope !== 'OWNER_PRIVATE_ONLY'
      || !Number.isFinite(captured) || new Date(captured).toISOString().replace('.000Z', 'Z') !== record.run_at
      || !recorded || recorded.verification !== 'NOT_CHECKED' || !['NO_EXPIRY', 'OK', 'EXPIRING', 'EXPIRED'].includes(recorded.state)) {
      return json200({ schema: 'kis-status/1', ...date, state: 'ERROR', code: 'TOKEN_STATUS_INVALID' }, origin);
    }
    // Recompute at capture time, so a valid historical day's countdown does not become a false mismatch today.
    const expected = kisTokenDate({ PRIVATE_REPO_READ_TOKEN: env.PRIVATE_REPO_READ_TOKEN,
      PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: recorded.state === 'NO_EXPIRY' ? 'NEVER' : recorded.expires_on }, captured);
    if (['state', 'code', 'expires_on', 'days_left'].some(k => recorded[k] !== expected[k])) {
      return json200({ schema: 'kis-status/1', ...date, state: 'ERROR', code: 'TOKEN_STATUS_INVALID' }, origin);
    }
    if (expected.expires_on !== date.expires_on || (expected.state === 'NO_EXPIRY') !== (date.state === 'NO_EXPIRY')) {
      return json200({ schema: 'kis-status/1', ...date, state: 'ERROR', code: 'TOKEN_EXPIRY_MISMATCH' }, origin);
    }
    return json200({ schema: 'kis-status/1', ...date }, origin);
  }

  // /kis/stock?symbol=… (a stock's view) or ?part=qgv (the QGV object): index (1 GitHub read) → asset API (1, read token,
  // redirect 'manual') → the one accepted 302 target (1, no credentials, redirect 'manual', no second hop) → size and sha256
  // pins of the gzip → the gzip bytes as published, Content-Encoding gzip (no inflate, no parse here; the app checks the content).
  // No Location, token or body ever reaches an error.
  // One release asset (or, with range, one member of a bundle): asset API (read token, redirect 'manual') → the one accepted
  // 302 target (no credentials, redirect 'manual', no second hop) → size and sha256 pins of the bytes.
  async function kisAssetBytes(entry, env, date, range, phase) {
    const gzipped = await bounded(phase, 15_000, 'UPSTREAM_UNAVAILABLE', 503, async (signal) => {
      let api;
      try {
        api = await fetchImpl(GITHUB_API + '/repos/' + KIS_REPO + '/releases/assets/' + entry.asset_id, {
          method: 'GET', signal, ...NO_CACHE,
          headers: { Accept: 'application/octet-stream', Authorization: 'Bearer ' + env.PRIVATE_REPO_READ_TOKEN, 'User-Agent': 'investment-system1-private-worker', 'X-GitHub-Api-Version': '2022-11-28' },
        });
      } catch { throw new Failure('UPSTREAM_UNAVAILABLE', 503); }
      const target = kisAssetRedirectTarget(api);
      if (target === null) {
        // Token and availability answers keep their existing codes; every other answer (a 200 stream, another 3xx, a bad
        // Location, 404) is the fixed redirect refusal.
        const s = api.status, state = s === 401 || s === 403 || s === 429 || s >= 500 ? kisUpstreamState(api, date) : null;
        return closeAndFail(api, state ? state.code : 'KIS_STOCK_ASSET_REDIRECT', state ? state.http : 502);
      }
      try { await api.body?.cancel(); } catch { /* The redirect body is never read. */ }
      const assetHeaders = { 'User-Agent': 'investment-system1-private-worker' };
      if (range) assetHeaders.Range = 'bytes=' + entry.offset + '-' + (entry.offset + entry.bytes - 1);
      let asset;
      try {
        asset = await fetchImpl(target, { method: 'GET', signal, ...NO_CACHE, headers: assetHeaders });
      } catch { throw new Failure('UPSTREAM_UNAVAILABLE', 503); }
      if (asset.type === 'opaqueredirect' || asset.redirected === true || asset.status === 0 || (asset.status >= 300 && asset.status <= 399)) {
        return closeAndFail(asset, 'KIS_STOCK_ASSET_REDIRECT', 502);
      }
      // A bundle member must come back as exactly the requested 206 range; a 200 (whole bundle) or another range is a pin
      // refusal and is never read. Any other status is the fixed availability answer.
      if (range && (asset.status === 200 || asset.status === 206) && !kisRangeAnswerOk(asset, entry)) return closeAndFail(asset, 'KIS_STOCK_PIN', 502);
      if (asset.status !== (range ? 206 : 200)) return closeAndFail(asset, 'UPSTREAM_UNAVAILABLE', 503);
      const advertised = asset.headers.get('Content-Length');
      if (advertised && /^\d+$/.test(advertised) && Number(advertised) > entry.bytes) return closeAndFail(asset, 'KIS_STOCK_PIN', 502);
      if (!asset.body) throw new Failure('KIS_STOCK_PIN', 502);
      return readPinned(asset, entry.bytes, 'KIS_STOCK_PIN', 'UPSTREAM_UNAVAILABLE', 503);
    });
    if (gzipped.byteLength !== entry.bytes || await sha256Hex(gzipped) !== entry.sha256) throw new Failure('KIS_STOCK_PIN', 502);
    return gzipped;
  }

  // A pinned JSON file of the data branch: the raw bytes up to limit, then (when pin) their size and sha256, then the parse.
  async function kisDataFile(path, env, date, limit, pin, phase) {
    const response = await github('/repos/' + KIS_REPO + '/contents/' + path + '?ref=' + KIS_BRANCH, env, 'application/vnd.github.raw+json', phase);
    if (!response) throw new Failure('UPSTREAM_UNAVAILABLE', 503);
    if (response.status === 404) { try { await response.body?.cancel(); } catch { /* Not read. */ } return null; }
    const bad = kisUpstreamState(response, date);
    if (bad) return closeAndFail(response, bad.code, bad.http);
    if (!pin) return readJson(response, limit, 'KIS_STOCK_INDEX_INVALID', 'KIS_STOCK_INDEX_INVALID', 502);
    if (!response.body) throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
    const bytes = await readPinned(response, pin.bytes, 'KIS_STOCK_INDEX_INVALID', 'UPSTREAM_UNAVAILABLE', 503);
    if (bytes.byteLength !== pin.bytes || await sha256Hex(bytes) !== pin.sha256) throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
    try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); } catch { throw new Failure('KIS_STOCK_INDEX_INVALID', 502); }
  }

  // /kis/stock?symbol=… (a stock's view) or ?part=qgv (the QGV object). With views/kis-stock-packs.json present: root (1 GitHub
  // read) → the symbol's shard (1 read, size and sha256 pinned by the root) → asset API (1) → one Range read of the member on
  // the accepted 302 target (1). Without it: the single index (1) → asset API (1) → the whole asset (1), as before.
  // The gzip bytes go out as published, Content-Encoding gzip (no inflate, no parse here; the app checks the content).
  // No Location, token or body ever reaches an error.
  async function kisStock(symbol, part, env, origin, phase) {
    const date = kisTokenDate(env, now());
    if (date.state === 'UNSET' || date.state === 'EXPIRED') throw new Failure(date.code, 503);
    let gzipped;
    const rootValue = await kisDataFile(KIS_PACK_ROOT_PATH, env, date, KIS_STOCK_INDEX_MAX_BYTES, null, phase);
    if (rootValue !== null) {
      const root = kisPackRoot(rootValue);
      if (root === null) throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
      if (part === 'qgv') gzipped = await kisAssetBytes(root.qgv, env, date, false, phase);
      else {
        const bucket = await kisPackBucket(symbol), pin = kisPackShardPin(root, bucket);
        if (pin === null) throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
        const shard = await kisDataFile(KIS_PACK_SHARD_DIR + kisPackShardName(bucket), env, date, KIS_PACK_SHARD_MAX_BYTES, pin, phase);
        if (shard === null) throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
        const member = kisPackMember(shard, root, bucket, symbol);
        if (member === 'INVALID') throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
        if (member === 'MISSING') throw new Failure('KIS_SERIES_NOT_FOUND', 404);
        gzipped = await kisAssetBytes(member, env, date, true, phase);
      }
    } else {
      const response = await github('/repos/' + KIS_REPO + '/contents/' + KIS_STOCK_INDEX_PATH + '?ref=' + KIS_BRANCH, env, 'application/vnd.github.raw+json', phase);
      if (!response) throw new Failure('UPSTREAM_UNAVAILABLE', 503);
      if (response.status === 404) return closeAndFail(response, 'KIS_SERIES_NOT_FOUND', 404);
      const bad = kisUpstreamState(response, date);
      if (bad) return closeAndFail(response, bad.code, bad.http);
      const index = await readJson(response, KIS_STOCK_INDEX_MAX_BYTES, 'KIS_STOCK_INDEX_INVALID', 'KIS_STOCK_INDEX_INVALID', 502);
      const entry = kisStockIndexEntry(index, part === 'qgv' ? null : symbol);
      if (entry === 'INVALID') throw new Failure('KIS_STOCK_INDEX_INVALID', 502);
      if (entry === 'MISSING') throw new Failure('KIS_SERIES_NOT_FOUND', 404);
      gzipped = await kisAssetBytes(entry, env, date, false, phase);
    }
    // Light read (owner 2026-11-21, CPU headroom on the free plan): the pinned gzip bytes go out as they are, with
    // Content-Encoding: gzip; the browser inflates them and the app's reader checks the view (kis-private.js stockParts and
    // its three readers, or validateQgv). encodeBody 'manual' keeps the runtime from compressing them a second time.
    const responseHeaders = headers(origin);
    responseHeaders.set('Content-Encoding', 'gzip');
    if (date.state === 'EXPIRING') { responseHeaders.set('X-Private-Token-Expires-On', date.expires_on); responseHeaders.set('Access-Control-Expose-Headers', 'X-Private-Token-Expires-On'); }
    return new Response(gzipped, { status: 200, headers: responseHeaders, encodeBody: 'manual' });
  }

  return async function handle(request, env) {
    const origin = request.headers.get('Origin');
    if (origin !== ORIGIN) return failureResponse(new Failure('ORIGIN_FORBIDDEN', 403));
    try {
      const url = new URL(request.url);
      const kis = url.pathname === '/kis/status' || url.pathname === KIS_STOCK_ROUTE;
      if (url.pathname !== '/history' && !kis) throw new Failure('ROUTE_NOT_FOUND', 404);
      if (!['GET', 'OPTIONS'].includes(request.method)) throw new Failure('METHOD_NOT_ALLOWED', 405);
      let symbol = null, range = null, part = null;
      if (url.pathname === '/kis/status') { if (url.search || url.hash) throw new Failure('REQUEST_INVALID', 400); }
      else if (url.pathname === KIS_STOCK_ROUTE && url.search === KIS_STOCK_QGV_QUERY && !url.hash) part = 'qgv';
      else if (kis) symbol = kisStockSymbol(url);
      else ({ symbol, range } = validateQuery(url));
      if (request.method === 'OPTIONS') {
        if (request.headers.get('Access-Control-Request-Method') !== 'GET'
          || request.headers.get('Access-Control-Request-Headers')?.trim().toLowerCase() !== 'authorization') throw new Failure('REQUEST_INVALID', 400);
        const responseHeaders = headers(origin);
        responseHeaders.delete('Content-Type');
        responseHeaders.set('Access-Control-Allow-Methods', 'GET');
        responseHeaders.set('Access-Control-Allow-Headers', 'Authorization');
        responseHeaders.set('Access-Control-Max-Age', '0');
        return new Response(null, { status: 204, headers: responseHeaders });
      }
      await authenticate(request, env);
      const admission = await admit(env);
      if (admission.denied) return failureResponse(new Failure('RATE_LIMITED', 429), origin, { 'Retry-After': String(admission.retryAfter) });
      let response;
      const phase = startPhase();
      try {
        if (url.pathname === '/kis/status') response = await kisStatus(env, origin, phase);
        else if (url.pathname === KIS_STOCK_ROUTE) response = await kisStock(symbol, part, env, origin, phase);
        else {
          let result;
          try { result = await history(symbol, range, phase); }
          catch (error) { result = await fallbackHistory(symbol, range, env, error, phase); }
          response = new Response(JSON.stringify(result), { status: 200, headers: headers(origin) });
        }
      } catch (error) { response = failureResponse(error instanceof Failure ? error : new Failure(kis ? 'UPSTREAM_UNAVAILABLE' : 'YAHOO_UNAVAILABLE', 503), origin); }
      finally {
        phase.end();
        try {
          await timed(LIMITER_TIMEOUT_MS, 'RATE_LIMIT_UNAVAILABLE', 503, async (signal) => {
            const released = await admission.stub.fetch('https://history-rate.internal/release', {
              method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lease: admission.lease }),
            });
            if (released.status !== 204) throw new Error();
          });
        } catch { response = failureResponse(new Failure('RATE_LIMIT_UNAVAILABLE', 503), origin); }
      }
      return response;
    } catch (error) { return failureResponse(error instanceof Failure ? error : new Failure('CONFIG_UNAVAILABLE', 503), origin); }
  };
}

function rateRecord(value, now) {
  if (value === undefined) return { times: [], activeLease: 0, leaseUntil: 0, nextLease: 0 };
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.keys(value).sort().join(',') !== 'activeLease,leaseUntil,nextLease,times'
    || !Array.isArray(value.times) || value.times.length > 12
    || !value.times.every((time, index) => Number.isSafeInteger(time) && time >= 0 && time <= now && (index === 0 || time > value.times[index - 1]))
    || !['activeLease', 'leaseUntil', 'nextLease'].every((key) => Number.isSafeInteger(value[key]) && value[key] >= 0)
    || value.activeLease > value.nextLease) throw new Error();
  return { ...value, times: value.times.filter((time) => time > now - WINDOW_MS) };
}

// This object stores only request times and numeric lease counters for one owner.
export class HistoryRateLimiter {
  constructor(state, env, { now = Date.now } = {}) { this.storage = state.storage; this.env = env; this.now = now; }

  async fetch(request) {
    const origin = request.headers.get('Origin');
    try {
      const path = new URL(request.url).pathname;
      if (request.method !== 'POST' || !['/admit', '/release'].includes(path)) throw new Error();
      const cap = this.env.REQUESTS_PER_MINUTE === undefined ? 12 : positiveInteger(this.env.REQUESTS_PER_MINUTE);
      if (cap === null || cap > 12) throw new Error();
      let lease;
      if (path === '/release') {
        if (Number(request.headers.get('Content-Length')) > 128) throw new Error();
        const body = await request.text();
        if (body.length > 128) throw new Error();
        const data = JSON.parse(body);
        if (Object.keys(data).length !== 1 || positiveInteger(data.lease) === null) throw new Error();
        lease = data.lease;
      }
      return await this.storage.transaction(async (storage) => {
        const now = this.now();
        if (!Number.isSafeInteger(now) || now < 0) throw new Error();
        const record = rateRecord(await storage.get('rate'), now);
        if (record.activeLease && record.leaseUntil <= now) { record.activeLease = 0; record.leaseUntil = 0; }
        if (path === '/release') {
          if (record.activeLease === lease) { record.activeLease = 0; record.leaseUntil = 0; }
          await storage.put('rate', record);
          return new Response(null, { status: 204, headers: headers(origin) });
        }
        const last = record.times.at(-1);
        const waitUntil = Math.max(
          record.activeLease ? record.leaseUntil : now,
          last === undefined ? now : last + MIN_SPACING_MS,
          record.times.length >= cap ? record.times[0] + WINDOW_MS : now,
        );
        if (waitUntil > now) {
          await storage.put('rate', record);
          return new Response(JSON.stringify({ allowed: false, retry_after: Math.max(1, Math.ceil((waitUntil - now) / 1000)) }), { status: 429, headers: headers(origin) });
        }
        record.nextLease = record.nextLease >= Number.MAX_SAFE_INTEGER ? 1 : record.nextLease + 1;
        record.activeLease = record.nextLease;
        record.leaseUntil = now + LEASE_MS;
        record.times.push(now);
        await storage.put('rate', record);
        return new Response(JSON.stringify({ allowed: true, lease: record.activeLease }), { status: 200, headers: headers(origin) });
      });
    } catch { return failureResponse(new Failure('RATE_LIMIT_UNAVAILABLE', 503), origin); }
  }
}

// Isolate start-up (owner 2026-11-28, CPU on the free plan): the pure checks run once on synthetic constants, so their first-run
// compile and regexes are paid when the isolate starts instead of inside the first stock read. No I/O, no timers, no crypto;
// nothing is kept, and a failure here is ignored (a warm-up must never stop the Worker from starting).
(() => {
  try {
    const h = '0'.repeat(64), g = { publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: '2000-01-01', release_tag: 'x', generation_sha256: h };
    const asset = { asset_id: 1, name: 'x', bytes: 1, sha256: h, json_bytes: 1, json_sha256: h };
    const root = kisPackRoot({ schema: 'kis-stock-pack-root/1', ...g, buckets: KIS_PACK_BUCKETS, bucket_rule: 'sha256(symbol)[0]>>2', qgv: asset,
      packs: { [h]: { asset_id: 2, bytes: 10 } }, shards: { '00.json': { bytes: 1, sha256: h } } });
    kisPackShardPin(root, 0);
    kisPackMember({ schema: 'kis-stock-pack-shard/1', ...g, bucket: 0, stocks: { A: { pack: h, offset: 0, bytes: 1, sha256: h, json_bytes: 1, json_sha256: h } } }, root, 0, 'A');
    kisTokenDate({ PRIVATE_REPO_READ_TOKEN: 'x', PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, 0);
    kisTokenDate({ PRIVATE_REPO_READ_TOKEN: 'x', PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2000-01-02' }, 0);
    kisStockSymbol(new URL('https://pre-run.invalid/kis/stock?symbol=A'));
    positiveInteger('1');
  } catch { /* A warm-up only. */ }
})();
const handle = createHandler();
export default { fetch(request, env) { return handle(request, env); } };
