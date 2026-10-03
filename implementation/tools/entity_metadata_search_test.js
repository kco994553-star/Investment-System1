/* Exhaustive Top-500 resolution check with the shipped search module.
   Usage: node tools/entity_metadata_search_test.js <built-dir> [report.json] */
"use strict";
const fs = require("fs"), path = require("path");
const S = require("../src/investment_system/product/web_assets/entity-search.js");
const dir = process.argv[2];
const entities = JSON.parse(fs.readFileSync(path.join(dir, "entities.json"), "utf8")).entities;
const idx = S.createIndex(entities);
const companies = entities.filter(e => e.entity_type === "COMPANY");
const kinds = {
  ticker: e => [e.ticker], canonical_name: e => [e.canonical_label],
  "en-US": e => [e.localized_names?.["en-US"], ...(e.aliases?.["en-US"] || [])],
  "ko-KR": e => [e.localized_names?.["ko-KR"], ...(e.aliases?.["ko-KR"] || [])],
  listing_ticker: e => e.aliases?.und || [],
  historical_name: e => e.historical_names || [], historical_ticker: e => e.historical_tickers || [],
};
// Labels owned by more than one entity are legitimately ambiguous (distinct candidates, no silent pick).
const owners = new Map();
for (const e of entities) for (const f of Object.values(kinds)) for (const v of f(e)) if (v) {
  const k = S.normalize(v), set = owners.get(k) || new Set(); set.add(e.entity_type + ":" + e.canonical_id); owners.set(k, set);
}
const report = {n_companies: companies.length, by_kind: {}, failures: []};
let fail = 0;
for (const [kind, f] of Object.entries(kinds)) {
  const r = report.by_kind[kind] = {labels: 0, top1: 0, shared_label_candidates: 0};
  for (const e of companies) for (const v of new Set(f(e).filter(Boolean))) {
    r.labels++;
    const id = "COMPANY:" + e.canonical_id, hits = idx.search(v, {limit: 50});
    if (hits[0]?.canonical_entity_id === id) { r.top1++; continue; }
    if (owners.get(S.normalize(v)).size > 1 && hits.some(h => h.canonical_entity_id === id && h.rank === hits[0].rank)) {
      r.shared_label_candidates++; continue;
    }
    fail++; report.failures.push({id, kind, label: v, got: hits.slice(0, 3).map(h => [h.canonical_entity_id, h.match_type])});
  }
}
// Duplicate entity / false-positive guards.
const ids = entities.map(e => e.entity_type + ":" + e.canonical_id);
if (new Set(ids).size !== ids.length) { fail++; report.failures.push("duplicate canonical entity"); }
if (companies.length !== 500) { fail++; report.failures.push("company entity count " + companies.length); }
for (const [q, want] of [["MS", "COMPANY:ms"], ["반도체", "INDUSTRY:semiconductor"], ["CPI", "MACRO:CPIAUCSL"]]) {
  const got = idx.search(q)[0]?.canonical_entity_id;
  if (got !== want) { fail++; report.failures.push({q, want, got}); }
}
if (idx.search("x").some(h => h.match_type === "FUZZY")) { fail++; report.failures.push("short fuzzy"); }
report.pass = fail === 0;
if (process.argv[3]) fs.writeFileSync(process.argv[3], JSON.stringify(report, null, 1) + "\n");
console.log(JSON.stringify({pass: report.pass, by_kind: report.by_kind, failures: report.failures.slice(0, 20)}, null, 1));
process.exit(fail ? 1 : 0);
