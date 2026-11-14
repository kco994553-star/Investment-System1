/* Personal-sheet V orchestration only. No provider, persistence or raw V formula.
 * The trusted Python preparer validates the financial/security/price contract;
 * this boundary checks independently supplied pins over the exact UTF-8 packet.
 * Raw reported/WAD V, percentiles and axis availability use the existing QgvV2.
 * Peer replacement/role aggregation mirrors research/qgv_555.py; ordinal bins
 * mirror dual_qgv._rank_factors (including code-order tie splits and N < 10).
 */
(function(root, factory) {
  const node = typeof module === 'object' && module.exports;
  const api = factory(node ? require('../product/web_assets/qgv-v2.js') : root.QgvV2,
    node ? require('node:crypto') : null, root.crypto);
  if (node) module.exports = api;
  else { root.PersonalSheetV = api; root.OwnerPriceV = api; }
})(typeof globalThis === 'object' ? globalThis : this, function(V2, nodeCrypto, browserCrypto) {
  'use strict';
  const NAMESPACE = 'PERSONAL_SHEET_V';
  const RAW_KEYS = ['central::ebit_yield', 'central::fcf_yield', 'central::own_history', 'central::gap'];
  const DIRECTIONS = {'central::ebit_yield': 1, 'central::fcf_yield': 1,
    'central::own_history': 1, 'central::gap': -1};
  const V_ROLES = ['v_earnings_yield', 'v_fcf_yield', 'v_vs_industry', 'v_vs_own_history', 'v_expectation_check'];
  const AXES = ['Q', 'G', 'V'];
  const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const score = v => v === null || finite(v) && v >= 0 && v <= 100;
  const own = (v, key) => Object.hasOwn(v, key);
  const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const need = (condition, code) => { if (!condition) throw Error(code); };
  const pyString = v => v === null || v === undefined ? 'None' : String(v);

  function equal(a, b) {
    if (a === b) return true;
    if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => equal(v, b[i]));
    if (!object(a) || !object(b)) return false;
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every(k => own(b, k) && equal(a[k], b[k]));
  }

  async function sha256(text) {
    if (nodeCrypto) return nodeCrypto.createHash('sha256').update(text, 'utf8').digest('hex');
    need(browserCrypto && browserCrypto.subtle && typeof TextEncoder === 'function', 'PERSONAL_SHA256_UNAVAILABLE');
    const result = await browserCrypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(result), n => n.toString(16).padStart(2, '0')).join('');
  }

  function validateEntry(entry) {
    need(object(entry) && typeof entry.company_id === 'string' && entry.company_id.length > 0 &&
      (entry.issuer_id === null || typeof entry.issuer_id === 'string') &&
      typeof entry.ranking_scope === 'string' && typeof entry.supported === 'boolean' &&
      typeof entry.reference_included === 'boolean' && object(entry.company) &&
      [null, 'GENERAL', 'FINANCIAL'].includes(entry.company.profile) &&
      (entry.quote === null || object(entry.quote)) && object(entry.raw_reasons) &&
      object(entry.base_axes) && score(entry.base_axes.Q) && score(entry.base_axes.G) &&
      ['PASS', 'VALUE_EXCLUDED', 'UNKNOWN'].includes(entry.gate_status) && object(entry.axis_weights) &&
      AXES.every(a => finite(entry.axis_weights[a]) && entry.axis_weights[a] >= 0) &&
      AXES.reduce((sum, a) => sum + entry.axis_weights[a], 0) > 0 && object(entry.roles) &&
      Object.keys(entry.roles).length === V_ROLES.length && V_ROLES.every(role => own(entry.roles, role)),
      'PERSONAL_PACKET_ENTRY');
    for (const role of V_ROLES) {
      const spec = entry.roles[role];
      need(object(spec) && spec.axis === 'V' && finite(spec.weight) && spec.weight >= 0 &&
        object(spec.metrics) && Object.values(spec.metrics).every(w => finite(w) && w >= 0),
        'PERSONAL_PACKET_ROLE');
    }
    need(V_ROLES.some(role => entry.roles[role].weight > 0), 'PERSONAL_PACKET_ROLE');
    need(Object.entries(entry.raw_reasons).every(([key, reason]) => RAW_KEYS.includes(key) &&
      typeof reason === 'string' && reason.length > 0), 'PERSONAL_PACKET_RAW_REASONS');
  }

  function ownerWire(packet) {
    return packet.schema_version === 'owner-price-v-packet/1';
  }

  function validateOwnerProfile(packet) {
    need(['OWNER_PRIVATE_KIS_V', NAMESPACE].includes(packet.namespace), 'OWNER_PACKET_SCOPE');
    const context = packet.context;
    const fields = ['context_id', 'evaluation_day', 'evaluated_at', 'input_cutoff',
      'provider', 'price_definition', 'evaluation_mode'];
    need(Object.keys(context).length === fields.length && fields.every(key => own(context, key)),
      'OWNER_PACKET_CONTEXT');
    const kis = packet.namespace === 'OWNER_PRIVATE_KIS_V';
    need(kis ? context.provider === 'KIS' && context.price_definition === 'KIS_DAILY_CLOSE' &&
      context.evaluation_mode === 'EXPLICIT_EOD_ASOF' :
      context.provider === 'GOOGLEFINANCE' && context.price_definition === 'GOOGLEFINANCE_CURRENT' &&
      context.evaluation_mode === 'CURRENT', 'OWNER_PACKET_PROVIDER');
    const availability = packet.availability_context;
    need(object(availability) && availability.evaluation_mode === context.evaluation_mode &&
      availability.historical_pit_proven === false &&
      availability.reconstruction === 'ACTUAL_INPUT_CUTOFF_NOT_HISTORICAL_SYSTEM_HOLDINGS' &&
      availability.official_top500_eligible === false && availability.research_coverage_claim === false,
      'OWNER_AVAILABILITY_CONTEXT');
  }

  // Disclosures come from the validated preparer. Never echo embedded quoted
  // prices/market values if a malformed packet places them inside metadata.
  function disclosureCopy(value) {
    if (Array.isArray(value)) return value.map(disclosureCopy);
    if (!object(value)) return value;
    const forbidden = new Set(['price', 'prices', 'quote', 'quotes', 'close', 'open',
      'high', 'low', 'month_closes', 'raw_bars', 'price_e4', 'close_e4',
      'market_cap', 'marketcap', 'issuer_mcap', 'ev', 'enterprise_value']);
    const out = {};
    for (const [key, item] of Object.entries(value)) {
      need(!forbidden.has(key.toLowerCase()), 'OWNER_METADATA_PRICE_FIELD');
      Object.defineProperty(out, key, {value: disclosureCopy(item), enumerable: true,
        configurable: true, writable: true});
    }
    return out;
  }

  function validatePacket(packet) {
    need(object(packet) && object(packet.context) && object(packet.configuration) &&
      ['U1-555', 'S1-555'].includes(packet.configuration.candidate) && packet.configuration.minimum === 8 &&
      object(packet.evaluation_original) && object(packet.reference_original) &&
      object(packet.evaluation_effective) && object(packet.reference_effective) &&
      Array.isArray(packet.evaluation) && Array.isArray(packet.reference), 'PERSONAL_PACKET_SCHEMA');
    if (ownerWire(packet)) validateOwnerProfile(packet);
    else {
      need(packet.schema_version === 'personal-sheet-v-packet/1' &&
        packet.namespace === NAMESPACE, 'PERSONAL_PACKET_SCHEMA');
      const context = packet.context;
      // Older hand-built packets have no supplier fields. Preserve those while
      // rejecting a supplied source pair that the legacy preparer never allows.
      if (own(context, 'provider') || own(context, 'price_definition')) {
        need(context.provider === 'GOOGLEFINANCE' && context.price_definition === 'GOOGLEFINANCE_CURRENT' ||
          context.provider === 'IEX_HIST' && context.price_definition === 'IEX_LAST_REGULAR_SESSION_TRADE',
          'PERSONAL_PACKET_PROVIDER');
      }
    }
    for (const entries of [packet.evaluation, packet.reference]) {
      const ids = new Set();
      for (const entry of entries) {
        validateEntry(entry);
        need(!ids.has(entry.company_id), 'PERSONAL_PACKET_DUPLICATE_MEMBER');
        ids.add(entry.company_id);
      }
    }
  }

  function rawValues(entries, parameters) {
    const companies = {}, quotes = {};
    entries.forEach((entry, i) => {
      const key = String(i);
      // Whitelist these two fields: memberships and cyclical flags cannot select
      // normalized earnings for this reported-flow variant, even in a packet.
      companies[key] = {profile: entry.company.profile, v_inputs: entry.company.v_inputs};
      if (entry.quote !== null) quotes[key] = entry.quote;
    });
    const options = {typeWeights: false};
    if (parameters !== undefined) options.parameters = parameters;
    const calculated = V2.scoreUniverse(companies, quotes, options);
    return entries.map((entry, i) => {
      const value = calculated[String(i)], detail = value.detail;
      const raw = {'central::ebit_yield': detail.ebit_yield, 'central::fcf_yield': detail.fcf_yield,
        'central::own_history': value.factors.v_vs_own_history.score, 'central::gap': detail.expectation_gap};
      const reason = {'central::ebit_yield': value.factors.v_earnings_yield.reason,
        'central::fcf_yield': value.factors.v_fcf_yield.reason,
        'central::own_history': value.factors.v_vs_own_history.reason,
        'central::gap': value.factors.v_expectation_check.reason};
      for (const key of RAW_KEYS) {
        if (own(entry.raw_reasons, key)) { raw[key] = null; reason[key] = entry.raw_reasons[key]; }
        else if (raw[key] !== null) reason[key] = null;
      }
      return {entry, raw, reason};
    });
  }

  function scopes(entry, role, candidate) {
    if (candidate === 'S1-555') return [['sector', entry.sector_id, entry.accounting_template]];
    return role === 'v_vs_industry' ? [['industry', entry.industry_group], ['all']] : [['all']];
  }

  function inScope(entry, scope) {
    if (scope[0] === 'all') return true;
    if (scope[0] === 'industry') return entry.industry_group === scope[1];
    return entry.sector_id === scope[1] && entry.accounting_template === scope[2];
  }

  function metricScore(value, role, metric, weight, reference, candidate, minimum) {
    const {entry, raw, reason} = value;
    const connected = own(DIRECTIONS, metric), applicable = entry.accounting_template === 'GENERAL';
    // Catalog applicability belongs to the role observation. Keep the raw-kernel
    // diagnostics separately, including unsupported rows retained in the roster.
    const number = connected && applicable ? raw[metric] : null;
    const item = {metric, raw: number, score: null,
      reason: connected ? applicable ? reason[metric] : 'ACCOUNTING_NOT_APPLICABLE' : 'PERSONAL_VARIANT_NOT_CONNECTED',
      reference_n: 0, reference_scope: null, weight};
    if (!entry.supported) { item.reason = entry.support_reason || 'PERSONAL_ROW_NOT_SUPPORTED'; return item; }
    if (weight === 0) { item.reason = 'DISABLED_IN_SETTING'; return item; }
    if (number === null) return item;
    // qgv_555.run adopts the already-computed own-history percentile directly;
    // its minimum-three past values belong to QgvV2, not the peer minimum-eight.
    if (metric === 'central::own_history') {
      item.score = number;
      item.reason = null;
      item.reference_scope = 'OWN_HISTORY';
      return item;
    }
    for (const scope of scopes(entry, role, candidate)) {
      const population = reference.filter(other => other.entry.issuer_id !== entry.issuer_id &&
        inScope(other.entry, scope) && other.raw[metric] !== null).map(other => DIRECTIONS[metric] * other.raw[metric]);
      population.push(DIRECTIONS[metric] * number);
      item.reference_n = population.length;
      item.reference_scope = scope.map(pyString).join('|');
      if (population.length >= minimum) {
        item.score = V2.percentile(DIRECTIONS[metric] * number, population);
        item.reason = null;
        return item;
      }
    }
    item.reason = 'PEER_SAMPLE_SMALL';
    return item;
  }

  function rankItems(rows, get) {
    const groups = new Map();
    for (const row of rows) {
      const item = get(row);
      Object.assign(item, {rank: null, rank_n: 0, decile: null, decile_status: 'NO_VALID_SCORE'});
      if (item.score === null) continue;
      if (!groups.has(row.ranking_scope)) groups.set(row.ranking_scope, []);
      groups.get(row.ranking_scope).push(row);
    }
    for (const group of groups.values()) {
      group.sort((a, b) => get(b).score - get(a).score || compare(a.company_id, b.company_id));
      const n = group.length, bins = [];
      if (n >= 10) {
        const k = Math.floor(n / 10), middle = n - 2 * k, q = Math.floor(middle / 8), rem = middle % 8;
        for (let i = 0; i < k; i++) bins.push(10);
        for (let i = 0; i < 8; i++) for (let j = 0; j < q + (i < rem ? 1 : 0); j++) bins.push(9 - i);
        for (let i = 0; i < k; i++) bins.push(1);
      }
      group.forEach((row, i) => Object.assign(get(row), {rank: i + 1, rank_n: n,
        decile: bins.length ? bins[i] : null, decile_status: bins.length ? 'VALID' : 'SAMPLE_LT_10'}));
    }
  }

  function calculateRows(packet) {
    const evaluation = rawValues(packet.evaluation, packet.parameters), seen = new Map();
    const reference = rawValues([...packet.reference].sort((a, b) => compare(a.company_id, b.company_id)), packet.parameters)
      .filter(value => {
        const entry = value.entry;
        if (!entry.reference_included || !entry.issuer_id) return false;
        const prior = seen.get(entry.issuer_id);
        if (prior) {
          const sameRaw = RAW_KEYS.every(key => prior.raw[key] === null && value.raw[key] === null ||
            finite(prior.raw[key]) && finite(value.raw[key]) && prior.raw[key] === value.raw[key]);
          const sameScope = ['industry_group', 'sector_id', 'accounting_template', 'ranking_scope']
            .every(key => prior.entry[key] === entry[key]);
          need(sameRaw && sameScope, 'PERSONAL_ISSUER_POINT_CONFLICT');
          return false;
        }
        seen.set(entry.issuer_id, value); return true;
      });
    const rows = evaluation.map(value => {
      const {entry, raw} = value, roles = {}, metrics = {}, roleScores = {}, roleWeights = {};
      for (const role of V_ROLES) {
        const spec = entry.roles[role], items = Object.entries(spec.metrics).map(([metric, weight]) =>
          metricScore(value, role, metric, weight, reference, packet.configuration.candidate, packet.configuration.minimum));
        let used = 0, total = 0;
        for (const item of items) {
          if (item.score !== null) { used += item.weight; total += item.weight * item.score; }
          metrics[role + '|' + item.metric] = {...item};
        }
        roles[role] = {score: used > 0 ? total / used : null, metrics: items};
        roleScores[role] = roles[role].score; roleWeights[role] = spec.weight;
      }
      const axes = {Q: entry.base_axes.Q, G: entry.base_axes.G, V: V2.axisScore(roleScores, 'V', roleWeights).score};
      const valid = AXES.filter(a => axes[a] !== null), weights = entry.axis_weights;
      const included = valid.filter(a => !(a === 'V' && entry.gate_status === 'VALUE_EXCLUDED'));
      const enough = valid.reduce((sum, a) => sum + weights[a], 0) >= AXES.reduce((sum, a) => sum + weights[a], 0) * .5;
      let total = null, used = 0, weighted = 0;
      for (const a of included) { used += weights[a]; weighted += weights[a] * axes[a]; }
      if (enough && used > 0 && entry.gate_status !== 'UNKNOWN') total = weighted / used;
      return {company_id: entry.company_id, issuer_id: entry.issuer_id, ranking_scope: entry.ranking_scope,
        raw, metrics, roles, axes, gate_status: entry.gate_status, total,
        partial_total: total !== null && valid.length < 3, rank: null, rank_n: 0};
    }).sort((a, b) => compare(a.company_id, b.company_id));
    for (const role of V_ROLES) rankItems(rows, row => row.roles[role]);
    const metricKeys = new Set(rows.flatMap(row => Object.keys(row.metrics)));
    for (const key of metricKeys) {
      const applicable = rows.filter(row => own(row.metrics, key));
      rankItems(applicable, row => row.metrics[key]);
      const split = key.indexOf('|'), role = key.slice(0, split), metric = key.slice(split + 1);
      for (const row of applicable) {
        const ranked = row.metrics[key], item = row.roles[role].metrics.find(item => item.metric === metric);
        for (const field of ['rank', 'rank_n', 'decile', 'decile_status']) item[field] = ranked[field];
      }
    }
    const groups = new Map();
    for (const row of rows) {
      if (row.total === null || row.partial_total) continue;
      if (!groups.has(row.ranking_scope)) groups.set(row.ranking_scope, []);
      groups.get(row.ranking_scope).push(row);
    }
    for (const group of groups.values()) {
      group.sort((a, b) => b.total - a.total || compare(a.company_id, b.company_id));
      group.forEach((row, i) => { row.rank = i + 1; row.rank_n = group.length; });
    }
    return rows;
  }

  async function calculate(payloadText, {expected_payload_sha256, expected_evaluation,
    expected_reference, expected_configuration_hash} = {}) {
    need(typeof payloadText === 'string' && typeof expected_payload_sha256 === 'string' &&
      /^[0-9a-f]{64}$/.test(expected_payload_sha256) &&
      await sha256(payloadText) === expected_payload_sha256, 'PERSONAL_PAYLOAD_HASH');
    let packet;
    try { packet = JSON.parse(payloadText); } catch (_) { throw Error('PERSONAL_PACKET_FORMAT'); }
    validatePacket(packet);
    need(object(expected_evaluation) && equal(packet.evaluation_original, expected_evaluation), 'PERSONAL_EVALUATION_ANCHOR');
    need(object(expected_reference) && equal(packet.reference_original, expected_reference), 'PERSONAL_REFERENCE_ANCHOR');
    // Python's canonical numeric spelling is preserved in the exact packet hash;
    // never introduce a JS reserialization hash for the same configuration.
    need(typeof expected_configuration_hash === 'string' && /^[0-9a-f]{64}$/.test(expected_configuration_hash) &&
      packet.configuration_hash === expected_configuration_hash, 'PERSONAL_CONFIGURATION_ANCHOR');
    need(V2 && typeof V2.scoreUniverse === 'function' && typeof V2.percentile === 'function' &&
      typeof V2.axisScore === 'function', 'PERSONAL_COMMON_ENGINE_UNAVAILABLE');
    const result = {schema_version: ownerWire(packet) ? 'owner-price-v-js-result/1' : 'personal-sheet-v-js-result/1',
      namespace: packet.namespace, evaluation_original: packet.evaluation_original,
      reference_original: packet.reference_original, rows: calculateRows(packet)};
    if (ownerWire(packet)) {
      result.storage = 'EPHEMERAL_ONLY';
      result.official = false;
      result.research_coverage_claim = false;
      result.filter_recalculates = false;
      result.availability_context = disclosureCopy(packet.availability_context);
      const entries = new Map(packet.evaluation.map(entry => [entry.company_id, entry]));
      for (const row of result.rows) {
        const entry = entries.get(row.company_id);
        for (const key of ['capitalization_basis', 'price_metadata', 'provenance', 'nonprice']) {
          if (own(entry, key)) row[key] = disclosureCopy(entry[key]);
        }
      }
    }
    return result;
  }

  return Object.freeze({calculate});
});
