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
      const add = (value, rank, match_type) => {
        if(typeof value === "string" && normalize(value)) fields.push({value:normalize(value),rank,match_type});
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
      const query = normalize(original_query), qlen = Array.from(query).length;
      if(!query || qlen>128) return [];
      const found = [];
      for(const record of records) {
        if(!types.includes(record.entity.entity_type)) continue;
        let best;
        for(const f of record.fields) {
          let rank, match_type, score=0;
          if(f.rank===0 && tickerKey(query)===tickerKey(f.value)) {
            rank=0; match_type="EXACT_TICKER";
          } else if(query===f.value) {rank=f.rank; match_type=f.match_type;}
          else if(f.value.startsWith(query)) {rank=4; match_type="PREFIX";}
          else if(qlen>=2 && f.value.includes(query)) {rank=5; match_type="SUBSTRING";}
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
  return Object.freeze({TYPES,normalize,tickerKey,distance,createIndex});
});
