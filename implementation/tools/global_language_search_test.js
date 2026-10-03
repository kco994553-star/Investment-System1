// Run the SAME search/locale modules shipped to the browser; no dependencies.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const S=require("../src/investment_system/product/web_assets/entity-search.js");
const L=require("../src/investment_system/product/web_assets/locale.js");
const root=process.argv[2] || "/tmp/web-mvp-demo";
const catalog=JSON.parse(fs.readFileSync(path.join(root,"entities.json"),"utf8"));
const index=S.createIndex(catalog.entities);
let checks=0;
function check(name,fn) {fn();checks++;console.log("PASS "+name);}
for(const query of ["NVDA","nvda","NVIDIA","NVIDIA Corporation","엔비디아","nvida","nvdia","엔디비아","nvd","엔비디"]) {
  check(query+" resolves COMPANY:nvda",()=>{
    const hits=index.search(query);
    assert.equal(hits[0]?.canonical_entity_id,"COMPANY:nvda");
    assert.equal(hits.filter(h=>h.canonical_entity_id==="COMPANY:nvda").length,1);
  });
}
for(const query of ["ASML","에이에스엠엘"]) check(query,()=>assert.equal(index.search(query)[0]?.canonical_entity_id,"COMPANY:asml"));
check("industry",()=>assert.equal(index.search("반도체")[0]?.canonical_entity_id,"INDUSTRY:semiconductor"));
check("macro",()=>assert.equal(index.search("CPI")[0]?.canonical_entity_id,"MACRO:CPIAUCSL"));
check("no fabricated investor",()=>assert.equal(index.search("버핏").length,0));
for(const query of ["zzzzzzzz","unrelated penguin","엔진오일","n"]) check("false-positive "+query,()=>{
  assert.equal(index.search(query).some(h=>h.canonical_entity_id==="COMPANY:nvda" && h.match_type==="FUZZY"),false);
  if(query!=="n") assert.equal(index.search(query).some(h=>h.canonical_entity_id==="COMPANY:nvda"),false);
});
check("normalization",()=>{
  assert.equal(index.search("  ＮＶＤＡ  ")[0].canonical_entity_id,"COMPANY:nvda");
  assert.equal(index.search(" NVIDIA   Corporation. ")[0].canonical_entity_id,"COMPANY:nvda");
  assert.equal(S.normalize("엔비디아"),"엔비디아");
  assert.equal(index.search("  ").length,0);
  assert.equal(index.search("x".repeat(129)).length,0);
});
check("explainability",()=>{
  assert.equal(index.search("NVDA")[0].match_type,"EXACT_TICKER");
  assert.equal(index.search("nvida")[0].match_type,"FUZZY");
  assert.equal(index.search("엔비디")[0].match_type,"PREFIX");
  assert.equal(index.search("  nvda ")[0].original_query,"  nvda ");
});
check("deterministic ties and ranking",()=>{
  const a={entity_type:"COMPANY",canonical_id:"z",canonical_label:"X Name",ticker:"X",aliases:{"en-US":["X"]}};
  const b={entity_type:"COMPANY",canonical_id:"a",canonical_label:"X",ticker:"Y"};
  const c={entity_type:"COMPANY",canonical_id:"b",canonical_label:"Different",ticker:"Z",aliases:{"en-US":["X"]}};
  assert.deepEqual(S.createIndex([a,b,c]).search("x").map(h=>h.canonical_entity_id),["COMPANY:z","COMPANY:a","COMPANY:b"]);
  assert.deepEqual(index.search("n"),S.createIndex([...catalog.entities].reverse()).search("n"));
});
check("registered investor, historical name, duplicate alias",()=>{
  const e={entity_type:"INVESTOR",canonical_id:"registered",canonical_label:"Test Investor",
    aliases:{"ko-KR":["테스트 투자자","테스트 투자자"]},historical_names:["Old Investor"]};
  const i=S.createIndex([e]);
  assert.equal(i.search("테스트 투자자").length,1);
  assert.equal(i.search("Old Investor")[0].canonical_entity_id,"INVESTOR:registered");
  assert.throws(()=>S.createIndex([e,e]));
});
check("ko/en deterministic fallback and terminology",()=>{
  assert.equal(L.text("설정","ko-KR"),"설정");
  assert.equal(L.text("설정","en-US"),"Settings");
  assert.equal(L.fallback({"ko-KR":"한국어","en-US":"English"},"fr-FR","canonical"),"한국어");
  assert.equal(L.fallback({"en-US":"English"},"ko-KR","canonical"),"English");
  assert.equal(L.fallback({},"ko-KR","canonical"),"canonical");
  assert.equal(L.term("free_cash_flow","ko-KR"),"Free Cash Flow(잉여현금흐름)");
});
check("locale/source independence and corrupt storage preservation",()=>{
  const a=L.settings({display_locale:"en-US",source_language:"ko"});
  assert.deepEqual(L.settings({...a,display_locale:"ko-KR"}),{version:1,display_locale:"ko-KR",source_language:"ko"});
  assert.deepEqual(L.settings({...a,source_language:"en"}),{version:1,display_locale:"en-US",source_language:"en"});
  assert.throws(()=>L.settings({display_locale:"fr-FR"}));
  const storage={getItem:()=>"{broken",setItem:()=>{throw Error("must not overwrite");}};
  assert.equal(L.read(storage).writable,false);
});
check("index and locale never mutate producer data or ranks",()=>{
  const before=JSON.stringify(catalog);
  for(const locale of L.LOCALES) {
    for(const e of catalog.entities) L.fallback(e.localized_names,locale,e.canonical_label);
    index.search("nvida"); L.settings({display_locale:locale});
  }
  assert.equal(JSON.stringify(catalog),before);
});
const start=performance.now();
for(let i=0;i<100;i++) index.search("nvida");
const ms=(performance.now()-start)/100;
console.log(JSON.stringify({passed:true,checks,entities:catalog.entities.length,average_query_ms:ms}));
