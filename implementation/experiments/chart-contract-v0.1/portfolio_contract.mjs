// Display-only aggregation: no allocation, market-value calculation or QGV scoring.
export const PORTFOLIO_CHART_VERSION = 'PORTFOLIO_CHART_CANDIDATE/0.1';

const nonempty = (v, name) => {
  if (typeof v !== 'string' || !v.trim() || v !== v.trim()) throw new Error(`${name}: nonempty trimmed string required`);
  return v;
};
function instant(v, name) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(v)) throw new Error(`${name}: UTC ISO timestamp required`);
  const ms = Date.parse(v);
  const normalized = v.replace(/(?:\.(\d{1,3}))?Z$/, (_, f) => `.${(f || '').padEnd(3, '0')}Z`);
  if (!Number.isFinite(ms) || new Date(ms).toISOString() !== normalized) throw new Error(`${name}: invalid timestamp`);
  return ms;
}
function units(v, name) {
  if (!Number.isSafeInteger(v) || v < 0) throw new Error(`${name}: nonnegative safe integer required`);
  return v;
}
function add(a, b) {
  const n = a + b;
  if (!Number.isSafeInteger(n)) throw new Error('unit sum overflow');
  return n;
}
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

/**
 * Every weight is supplied in exact caller-defined units. TARGET is not ACTUAL.
 * Industry: one supplied label per holding, or null (unknown).
 * Types: null is unknown; [] explicitly means no catalog types. All known types
 * must be in the supplied catalog. No labels are inferred from a ticker.
 * Cash is outside corporate taxonomy and remains visible in every view.
 */
export function aggregatePortfolio(input) {
  if (!input || typeof input !== 'object') throw new Error('snapshot required');
  for (const key of ['snapshot_id', 'portfolio_version', 'qgv_version', 'source']) nonempty(input[key], key);
  const asOf = instant(input.as_of, 'as_of');
  if (!['TARGET', 'ACTUAL'].includes(input.weight_basis)) throw new Error('explicit weight_basis required');
  if (!['SYNTHETIC_FIXTURE', 'USER_SPEC_REFERENCE', 'OBSERVED_DATA'].includes(input.data_kind)) throw new Error('explicit data_kind required');
  if (input.data_kind === 'USER_SPEC_REFERENCE' && input.weight_basis !== 'TARGET') throw new Error('reference is TARGET only; never inferred ACTUAL');
  units(input.total_units, 'total_units');
  if (!input.total_units) throw new Error('positive total_units required');
  units(input.cash_units, 'cash_units');
  if (!Array.isArray(input.holdings)) throw new Error('holdings array required');
  if (!Array.isArray(input.type_catalog)) throw new Error('explicit type_catalog required');
  const catalog = [...input.type_catalog];
  catalog.forEach(t => nonempty(t, 'catalog type'));
  if (new Set(catalog).size !== catalog.length) throw new Error('duplicate catalog type');
  catalog.sort();
  const classification = input.classification;
  if (!classification || typeof classification !== 'object') throw new Error('classification provenance required');
  nonempty(classification.version, 'classification.version');
  nonempty(classification.source, 'classification.source');
  if (classification.available_at !== null && instant(classification.available_at, 'classification.available_at') > asOf) throw new Error('classification unavailable at snapshot as_of');

  const industries = new Map(), memberships = new Map(), ids = new Set(), securityIds = new Set();
  const holdings = [];
  const members = new Map(catalog.map(t => [t, 0]));
  let sum = input.cash_units, unknownIndustry = 0, unknownTypes = 0, noTypes = 0;
  for (const h of input.holdings) {
    if (!h || typeof h !== 'object') throw new Error('holding object required');
    nonempty(h.holding_id, 'holding_id');
    if (h.security_id !== null) {
      nonempty(h.security_id, 'security_id (null means unresolved)');
      if (securityIds.has(h.security_id)) throw new Error('duplicate security_id');
      securityIds.add(h.security_id);
    }
    nonempty(h.label, 'holding label');
    if (ids.has(h.holding_id)) throw new Error('duplicate holding_id');
    ids.add(h.holding_id);
    units(h.weight_units, 'weight_units');
    sum = add(sum, h.weight_units);
    if (h.industry === null) unknownIndustry = add(unknownIndustry, h.weight_units);
    else {
      nonempty(h.industry, 'industry (null means unknown)');
      industries.set(h.industry, add(industries.get(h.industry) || 0, h.weight_units));
    }
    if (h.types === null) unknownTypes = add(unknownTypes, h.weight_units);
    else {
      if (!Array.isArray(h.types)) throw new Error('types array or null required');
      h.types.forEach(t => { if (!members.has(t)) throw new Error('type outside supplied catalog'); });
      if (new Set(h.types).size !== h.types.length) throw new Error('duplicate holding type');
      for (const t of h.types) members.set(t, add(members.get(t), h.weight_units));
      if (!h.types.length) noTypes = add(noTypes, h.weight_units);
      else {
        const types = [...h.types].sort();
        const key = JSON.stringify(types);
        const existing = memberships.get(key);
        memberships.set(key, {kind: 'MEMBERSHIP', types, units: add(existing?.units || 0, h.weight_units)});
      }
    }
    holdings.push({holding_id: h.holding_id, security_id: h.security_id, label: h.label, weight_units: h.weight_units, industry: h.industry, types: h.types === null ? null : [...h.types]});
  }
  if (sum !== input.total_units) throw new Error('holdings plus cash must exactly equal total_units');
  const knownCorporate = input.total_units - input.cash_units - unknownTypes;
  const output = {
    contract_version: PORTFOLIO_CHART_VERSION,
    snapshot_id: input.snapshot_id,
    portfolio_version: input.portfolio_version,
    qgv_version: input.qgv_version,
    as_of: input.as_of,
    source: input.source,
    weight_basis: input.weight_basis,
    data_kind: input.data_kind,
    total_units: input.total_units,
    cash_units: input.cash_units,
    classification: {version: classification.version, source: classification.source, available_at: classification.available_at},
    holdings,
    data_state: input.data_kind === 'SYNTHETIC_FIXTURE' ? 'DEMO' : input.data_kind === 'USER_SPEC_REFERENCE' ? 'REFERENCE' : 'NOT_AVAILABLE',
    publication_grant: null,
    pit_status: 'NOT_VERIFIED',
    reasons: ['DISPLAY_AGGREGATION_ONLY', 'NO_QGV_RECALCULATION', 'NO_HISTORICAL_PIT_CERTIFICATION'],
    industry: {
      denominator_units: input.total_units,
      buckets: [...industries].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([label, n]) => ({kind: 'INDUSTRY', label, units: n})).concat([
        {kind: 'UNKNOWN', label: 'Unknown industry', units: unknownIndustry},
        {kind: 'CASH', label: 'Cash', units: input.cash_units},
      ]),
    },
    types: {
      denominator_units: input.total_units,
      exposures: catalog.map(type => ({type, member_units: members.get(type), non_member_units: knownCorporate - members.get(type), unknown_units: unknownTypes, cash_units: input.cash_units})),
      note: 'Independent portfolio-denominator rings. Type memberships may sum above 100%; never renormalize.',
    },
    overlap: {
      denominator_units: input.total_units,
      buckets: [...memberships].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([, bucket]) => bucket).concat([
        {kind: 'NO_TYPES', types: [], units: noTypes},
        {kind: 'UNKNOWN', types: [], units: unknownTypes},
        {kind: 'CASH', types: [], units: input.cash_units},
      ]),
      note: 'Exclusive exact membership sets; not pairwise correlation or probability.',
    },
  };
  return freeze(output);
}

// Recompute from the source snapshot rather than accepting a caller-mutated candidate.
export function renderPortfolioInput(snapshot) {
  const candidate = aggregatePortfolio(snapshot);
  if (candidate.data_state === 'NOT_AVAILABLE') throw new Error('observed portfolio renderer withheld pending integration and provenance validation');
  return candidate;
}
