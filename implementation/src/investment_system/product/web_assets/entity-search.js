/* Shared browser/Node search implementation. Ranking is navigation only. */
(function(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EntitySearch = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function() {
  "use strict";
  const TYPES = Object.freeze(["COMPANY", "INDUSTRY", "INVESTOR", "MACRO", "THEME", "PORTFOLIO", "NEWS", "PROMPT"]);
  const cmp = (a,b) => a < b ? -1 : a > b ? 1 : 0;
  function normalize(query) {
    return String(query ?? "").normalize("NFKC").toLowerCase()
      .replace(/[’‘]/g, "'").replace(/[‐‑‒–—−]/g, "-")
      .replace(/[^\p{L}\p{N}]+/gu, " ").trim().replace(/\s+/g, " ");
  }
  function tickerKey(query) { return normalize(query).replace(/ /g, ""); }
  function distance(a,b) {
    a = Array.from(a); b = Array.from(b);
    const d = Array.from({length:a.length+1}, () => Array(b.length+1).fill(0));
    for(let i=0;i<=a.length;i++) d[i][0]=i;
    for(let j=0;j<=b.length;j++) d[0][j]=j;
    for(let i=1;i<=a.length;i++) for(let j=1;j<=b.length;j++) {
      d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
      if(i>1 && j>1 && a[i-1]===b[j-2] && a[i-2]===b[j-1])
        d[i][j]=Math.min(d[i][j],d[i-2][j-2]+1);
    }
    return d[a.length][b.length];
  }
  function createIndex(entities) {
    const seen = new Set();
    const records = entities.map(entity => {
      if(!TYPES.includes(entity.entity_type) || typeof entity.canonical_id !== "string" ||
         !entity.canonical_id || typeof entity.canonical_label !== "string" || !entity.canonical_label)
        throw Error("Invalid canonical entity");
      const e = JSON.parse(JSON.stringify(entity));
      const key = e.entity_type + ":" + e.canonical_id;
      if(seen.has(key)) throw Error("Duplicate canonical entity: " + key);
      seen.add(key);
      const fields = [];
      // Each field is also kept without spaces so Korean and English names match case- and space-insensitively.
      const add = (value, rank, match_type) => {
        if(typeof value === "string" && normalize(value)) fields.push({value:normalize(value),compact:tickerKey(value),rank,match_type});
      };
      add(e.ticker,0,"EXACT_TICKER");
      add(e.canonical_label,1,"EXACT_CANONICAL_NAME");
      Object.entries(e.localized_names || {}).sort(([a],[b])=>cmp(a,b)).forEach(([,v])=>add(v,2,"EXACT_LOCALIZED_NAME"));
      Object.entries(e.aliases || {}).sort(([a],[b])=>cmp(a,b)).forEach(([locale,vs])=>
        vs.forEach(v=>add(v,3,locale==="ko-KR"?"LOCALIZED_ALIAS":"EXACT_ALIAS")));
      (e.historical_names || []).forEach(v=>add(v,3,"EXACT_ALIAS"));
      (e.historical_tickers || []).forEach(v=>add(v,3,"EXACT_ALIAS"));
      return {entity:e,key,fields};
    });
    function search(original_query, {limit=20, types=TYPES}={}) {
      const query = normalize(original_query), qlen = Array.from(query).length, qc = tickerKey(query);
      if(!query || qlen>128) return [];
      const found = [];
      for(const record of records) {
        if(!types.includes(record.entity.entity_type)) continue;
        let best;
        for(const f of record.fields) {
          let rank, match_type, score=0;
          if(f.rank===0 && tickerKey(query)===tickerKey(f.value)) {
            rank=0; match_type="EXACT_TICKER";
          } else if(query===f.value || (qc && qc===f.compact)) {rank=f.rank; match_type=f.match_type;}
          else if(f.value.startsWith(query) || (qc && f.compact.startsWith(qc))) {rank=4; match_type="PREFIX";}
          else if(qlen>=2 && (f.value.includes(query) || f.compact.includes(qc))) {rank=5; match_type="SUBSTRING";}
          else if(qlen>=4 && Array.from(f.value).length<=128) {
            const len=Array.from(f.value).length, maxDist=qlen>=8?2:1;
            if(Math.abs(qlen-len)>maxDist) continue;
            const edits=distance(query,f.value), ratio=edits/Math.max(qlen,len);
            if(edits>maxDist || ratio>0.25) continue;
            rank=6; match_type="FUZZY"; score=ratio;
          } else continue;
          const candidate={rank,match_type,score,matched_label:f.value};
          if(!best || rank<best.rank || (rank===best.rank && (score<best.score ||
            (score===best.score && cmp(f.value,best.matched_label)<0)))) best=candidate;
        }
        if(best) found.push({entity:record.entity, canonical_entity_id:record.key,
          original_query:String(original_query), normalized_query:query, ...best});
      }
      found.sort((a,b)=>a.rank-b.rank || a.score-b.score ||
        cmp(a.canonical_entity_id,b.canonical_entity_id));
      return found.slice(0, Math.max(0, Math.min(1000, limit)));
    }
    function resolve(type,id) { return records.find(r=>r.entity.entity_type===type && r.entity.canonical_id===id)?.entity; }
    return Object.freeze({search,resolve});
  }
  // Company search entities from price-free identities only: the TARGET device directory (ticker + catalog label) and
  // public Universe504 codes (code + ticker). With the reviewed names table (KR-NAMES, `company-names-ko.json`) each entity
  // also carries its Korean name, English (SEC) name and sourced aliases, looked up by the same key the app uses
  // (company_id or Universe code; never a ticker). No prices, caps or ranks are read or indexed.
  const VENUE = /^(NYSE|NASDAQ|BATS):[A-Z0-9][A-Z0-9.\-]{0,15}$/;
  function companyEntities(identities, universeCodes, names) {
    const out = [], tickers = new Set(), ids = new Set();
    const named = e => {
      const r = names && typeof names.get === "function" ? names.get(e.canonical_id) : null;
      if(!r) return e;
      const localized = {}, aliases = {};
      if(r.ko_name) localized["ko-KR"] = r.ko_name;
      if(r.en_name) localized["en-US"] = r.en_name;
      for(const a of r.aliases) (aliases[a.lang === "ko" ? "ko-KR" : "en-US"] ||= []).push(a.text);
      return {...e, localized_names:localized, aliases, names:r};
    };
    for(const c of identities || []) {
      if(!c || typeof c.company_id !== "string" || typeof c.ticker !== "string" || typeof c.name !== "string" || !c.name) continue;
      tickers.add(c.ticker.replaceAll(".", "-")); ids.add(c.company_id);
      out.push(named({entity_type:"COMPANY", canonical_id:c.company_id, canonical_label:c.name, ticker:c.ticker, scope:"TARGET"}));
    }
    for(const [code, companyId] of Object.entries(universeCodes || {}).sort(([a],[b])=>cmp(a,b))) {
      if(!VENUE.test(code)) continue;
      const ticker = code.slice(code.indexOf(":")+1);
      if(tickers.has(ticker.replaceAll(".", "-")) || (typeof companyId === "string" && ids.has(companyId))) continue;
      out.push(named({entity_type:"COMPANY", canonical_id:code, canonical_label:code, ticker, scope:"UNIVERSE504"}));
    }
    return out;
  }
  /* KR-NAMES (owner decision 2026-10-18): the reviewed company-name table. Display and search only: it never enters a QGV
     calculation, company identity, ranking or record. Records are keyed by TARGET company_id or Universe code; a code linked
     to a TARGET company is found through that record's universe_code. A missing or invalid file means "no names" (English /
     ticker fallback), never a missing company. */
  const NAMES_FILE = "company-names-ko.json", NAMES_SCHEMA = "company-names-ko/1";
  const STATUSES = ["OFFICIAL", "COMMON", "UNREGISTERED"];
  const str = (v, n) => typeof v === "string" && v.length > 0 && v.length <= n;
  const opt = (v, n) => v === null || str(v, n);
  function nameIndex(payload) {
    if(!payload || payload.schema !== NAMES_SCHEMA || !Array.isArray(payload.records) || payload.records.length > 1100) return null;
    const map = new Map();
    for(const r of payload.records) {
      if(!r || !str(r.key, 64) || !["TARGET_COMPANY_ID","UNIVERSE_CODE"].includes(r.key_kind) || !opt(r.universe_code, 32) ||
         !str(r.ticker, 16) || !str(r.exchange, 16) || !opt(r.en_name, 160) || !opt(r.en_source, 300) || !opt(r.ko_name, 80) ||
         !STATUSES.includes(r.ko_status) || (r.ko_status === "UNREGISTERED") !== (r.ko_name === null) || !opt(r.ko_source, 300) ||
         !opt(r.class_label, 1) || !opt(r.share_class_note, 200) || !Array.isArray(r.aliases) || r.aliases.length > 12 ||
         r.aliases.some(a => !a || !str(a.text, 80) || !["ko","en"].includes(a.lang) || !str(a.source, 300))) return null;
      const rec = Object.freeze({key:r.key, key_kind:r.key_kind, universe_code:r.universe_code, cik:r.cik ?? null, ticker:r.ticker,
        exchange:r.exchange, share_class_note:r.share_class_note, class_label:r.class_label, en_name:r.en_name, en_source:r.en_source,
        ko_name:r.ko_name, ko_status:r.ko_status, ko_source:r.ko_source, aliases:Object.freeze(r.aliases.map(a => Object.freeze({text:a.text, lang:a.lang, source:a.source})))});
      for(const id of new Set([r.key, r.universe_code].filter(Boolean))) { if(map.has(id)) return null; map.set(id, rec); }
    }
    return Object.freeze({get:id => map.get(id) || null, count:payload.records.length, codes:() => [...new Set(map.values())].filter(r => r.universe_code).map(r => [r.universe_code, r.key_kind === "TARGET_COMPANY_ID" ? r.key : null])});
  }
  async function loadNames(view) {
    try {
      const r = await view.fetch(NAMES_FILE, {cache:"no-store", credentials:"omit", redirect:"error"});
      return r.ok ? nameIndex(await r.json()) : null;
    } catch(_) { return null; }
  }
  // Name part: Korean name (ko-KR) or English (SEC) name, with the share-class letter when one issuer has several codes.
  function companyName(rec, locale) {
    if(!rec) return null;
    const base = locale === "en-US" ? (rec.en_name || rec.ko_name) : (rec.ko_name || rec.en_name);
    if(!base) return null;
    return rec.class_label ? base + (locale === "en-US" ? " Class " : " ") + rec.class_label : base;
  }
  // "한국어명 · 티커"; without a Korean name "English name · TICKER"; without both, the ticker alone.
  function companyTitle(rec, ticker, locale) {
    const name = companyName(rec, locale), t = rec && rec.ticker || ticker || "";
    return name ? name + " · " + t : t;
  }
  return Object.freeze({TYPES,normalize,tickerKey,distance,createIndex,companyEntities,NAMES_FILE,NAMES_SCHEMA,nameIndex,loadNames,companyName,companyTitle});
});
