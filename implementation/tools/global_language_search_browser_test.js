// Presentation/navigation E2E on the public Pages build (PAGES_COCKPIT_URL). Public build and in-memory test vectors only.
//
// Current contract (GSQ-010 public price boundary): the public build ships no producer company rows and app.js never
// renders data.json producer sections, so global search offers INDUSTRY / MACRO entities only and company identities live in
// the price-free device directory. Producer-section presentation (numbers, rankings, news) is therefore exercised on
// test vectors assigned to the page's in-memory model (D), never served and never persisted.
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const base=new URL(process.env.PAGES_COCKPIT_URL||"http://127.0.0.1:9003/Investment-System1/");
base.hash="";
if(!base.pathname.endsWith("/")) base.pathname+="/";
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.WEB_TEST_CHROMIUM_PATH?{executablePath:process.env.WEB_TEST_CHROMIUM_PATH}:{})});
  const traffic={external:0,unsafe:0,failed_responses:0};
  const guard=async route=>{
    const request=route.request(),url=new URL(request.url());
    if(request.method()!=="GET"||request.postData()) {traffic.unsafe++;await route.abort();return;}
    if(url.origin!==base.origin||!url.pathname.startsWith(base.pathname)) {traffic.external++;await route.abort();return;}
    await route.continue();
  };
  // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
  const responses=page=>page.on("response",response=>{
    if(response.status()>=400&&!(response.status()===404&&response.url()===new URL("sec-public-inputs.json",base).href)) traffic.failed_responses++;
  });
  const context=await browser.newContext({viewport:{width:390,height:844}});
  await context.route("**/*",guard);
  const page=await context.newPage(), errors=[],checks=[];
  page.on("pageerror",e=>errors.push(e.message));
  responses(page);
  const out=path.resolve(process.env.GLOBAL_LANGUAGE_SEARCH_EVIDENCE_DIR||process.env.PAGES_COCKPIT_EVIDENCE_DIR||path.join(os.tmpdir(),"global-language-search-evidence"));
  fs.mkdirSync(out,{recursive:true});
  async function check(name,fn) {await fn();checks.push(name);console.log("PASS browser "+name);}
  async function go(route) {
    await page.goto(new URL("#"+route,base).href);
    await page.reload();
    await page.waitForFunction(()=>typeof window.investmentSearch==="function"&&!!document.querySelector("main h1"));
  }
  async function locale(value) {
    await go("settings");await page.locator("#display-locale").selectOption(value);
    assert.equal(await page.locator("html").getAttribute("lang"),value);
  }
  // Finished public producer snapshots, including numeric sections and source language, assigned to the page model only.
  async function seed() {
    await page.evaluate(()=>{
      const env=data=>({state:"DEMO",as_of:"2024-12-31",source:"public presentation test",data});
      D.technical=env({nvda:{regime:"TREND_UP",execution_zone:"ADD",invalidation:"Original invalidation",volatility:0.123}});
      D.macro=env({state:"NORMAL",regime:"EXPANSION",indicators:{CPIAUCSL:300.2,growth:0.04}});
      D.portfolio=env({role:"test vector",return:0.125,market_value:12345.67,currency:"USD",holdings:[]});
      D.leaderboard=env({rows:[{company_id:"nvda",ticker:"NVDA",rank:2,total_score:90.79},{company_id:"asml",ticker:"ASML",rank:1,total_score:91}]});
      D.news=env([
        {event_id:"en",headline:"Original English headline",summary:"Original English summary",summary_localized:{"ko-KR":"한국어 요약","en-US":"English summary"},source_language:"en",available_at:"2024-12-31",source_original:{ticker:"NVDA",cik:"0001045810",accession:"0001045810-24-000264",source_url:"https://www.sec.gov/Archives/",provenance:"original",raw_source_data:"raw SEC filing"}},
        {event_id:"ko",headline:"한국어 원문 제목",summary:"한국어 원문 요약",source_language:"ko",available_at:"2024-12-31"}
      ]);
      render();
    });
  }
  try {
    await check("global search exact/alias/prefix/fuzzy resolve one canonical route",async()=>{
      await go("home");
      const expected={"INDUSTRY:semiconductor":["반도체","semiconductor","Semiconductors","반도","semiconducter"],"MACRO:CPIAUCSL":["CPI","cpi","소비자 물가","소비자물가지수"]};
      for(const [entity,queries] of Object.entries(expected)) for(const q of queries) {
        await page.locator("#global-search").fill(q);
        assert.equal(await page.locator("#global-results li").first().getAttribute("data-entity-id"),entity,q);
        assert.equal(await page.locator("#global-results li").first().locator("a").getAttribute("href"),"#entity/"+encodeURIComponent(entity),q);
      }
      await page.locator("#global-search").fill("semiconducter");
      await page.locator("#global-search").press("ArrowDown");
      await page.keyboard.press("Enter");
      await page.getByRole("heading",{name:"반도체",exact:true}).waitFor();
      assert.ok(page.url().endsWith("#entity/INDUSTRY%3Asemiconductor"));
      // Company identities are found in the price-free directory (ticker / English name), not fabricated by global search.
      for(const q of ["NVDA","엔비디아"]) {
        await page.locator("#global-search").fill(q);
        assert.equal(await page.locator("#global-results [data-entity-id^='COMPANY:']").count(),0,q);
      }
      await go("companies");await page.locator("#search").fill("ASML");
      assert.equal(await page.locator("#company-list li").count(),1);
      assert.equal(await page.locator("#company-list li a").getAttribute("href"),"#company/asml");
      await page.locator("#global-search").fill("unrelated penguin");
      assert.equal(await page.locator("#global-results [data-entity-id]").count(),0);
    });
    await check("industry and macro navigation; no fake investor",async()=>{
      await page.locator("#global-search").fill("반도체");
      await page.locator("#global-results a").first().click();
      await page.getByRole("heading",{name:"반도체",exact:true}).waitFor();
      await page.locator("#global-search").fill("CPI");
      await page.locator("#global-results a").first().click();
      await page.getByRole("heading",{name:"소비자물가지수",exact:true}).waitFor();
      await page.locator("#global-search").fill("버핏");
      assert.equal(await page.locator("#global-results [data-entity-id]").count(),0);
      await page.locator("#global-search").press("Escape");
    });
    await check("ko/en UI, persistence, QGV/Technical/Macro/Portfolio/Leaderboard/source_original unchanged",async()=>{
      await go("settings");await seed();
      const before=await page.evaluate(()=>JSON.stringify(D));
      const interests=await page.evaluate(()=>JSON.stringify(prefs));
      await page.locator("#display-locale").selectOption("en-US");
      assert.equal(await page.getByRole("heading",{name:"Settings",exact:true}).count(),1);
      assert.equal(await page.evaluate(()=>JSON.stringify(D)),before);
      assert.equal(await page.evaluate(()=>JSON.stringify(prefs)),interests);
      await page.reload();await page.getByRole("heading",{name:"Settings",exact:true}).waitFor();
      assert.equal(await page.locator("#display-locale").inputValue(),"en-US");
      await go("home");await page.getByRole("heading",{name:"Today's investment view"}).waitFor();
      await go("portfolio");await page.getByRole("heading",{name:"My portfolio"}).waitFor();
      await go("leaderboard");await page.getByRole("heading",{name:"Company research"}).waitFor();
      await seed();
      assert.deepEqual(await page.locator("main .list a b").allTextContents(),["#2 NVDA","#1 ASML"]);
      const leaderboardBefore=await page.evaluate(()=>JSON.stringify(D));
      await page.evaluate(()=>{location.hash="#settings";});
      await page.locator("#display-locale").selectOption("ko-KR");
      assert.equal(await page.locator("html").getAttribute("lang"),"ko-KR");
      assert.equal(await page.evaluate(()=>JSON.stringify(D)),leaderboardBefore);
      await page.evaluate(()=>{location.hash="#leaderboard";});
      await page.getByRole("heading",{name:"기업 연구"}).waitFor();
      assert.deepEqual(await page.locator("main .list a b").allTextContents(),["#2 NVDA","#1 ASML"]);
      await go("home");await page.getByRole("heading",{name:"오늘의 투자 화면"}).waitFor();
    });
    await check("source language filter independent; localized summaries retain raw originals",async()=>{
      await go("settings");await page.locator("#source-language").selectOption("en");
      await page.locator("#display-locale").selectOption("en-US");
      assert.equal(await page.locator("#source-language").inputValue(),"en");
      await go("news");await seed();
      assert.equal(await page.locator("#news-list>li").count(),1);
      assert.ok((await page.locator("#news-list").innerText()).includes("English summary"));
      assert.ok((await page.locator("#news-list pre").textContent()).includes("Original English summary"));
      await locale("ko-KR");assert.equal(await page.locator("#source-language").inputValue(),"en");
      await go("news");await seed();assert.equal(await page.locator("#news-list>li").count(),1);
      assert.ok((await page.locator("#news-list").innerText()).includes("한국어 요약"));
      await go("settings");await page.locator("#source-language").selectOption("ko");
      assert.equal(await page.locator("#display-locale").inputValue(),"ko-KR");
      await go("news");await seed();assert.ok((await page.locator("#news-list").innerText()).includes("한국어 원문 제목"));
      await go("settings");await page.locator("#source-language").selectOption("all");
    });
    await check("existing News Network labels use global display locale; no network page is served",async()=>{
      // Track D's relationship page is not part of the public build: the network pane stays a NOT_AVAILABLE notice.
      await locale("en-US");await go("news");
      assert.deepEqual(await page.locator(".toolbar button").allTextContents(),["News","Network"]);
      await page.locator("#show-network").click();
      assert.equal(await page.locator("#network-pane").isVisible(),true);
      assert.ok((await page.locator("#network-pane").innerText()).includes("Fact = confirmed relationship"));
      assert.ok((await page.locator("#network-pane").innerText()).includes("NOT_AVAILABLE"));
      assert.equal(await page.locator("#network-frame").count(),0);
      await locale("ko-KR");await go("news");
      assert.deepEqual(await page.locator(".toolbar button").allTextContents(),["뉴스","관계망"]);
      await page.locator("#show-network").click();
      assert.ok((await page.locator("#network-pane").innerText()).includes("Fact = 확인된 관계"));
      assert.equal(await page.locator("#network-frame").count(),0);
    });
    await check("research controls localized, Frozen payload/preview unchanged",async()=>{
      await locale("en-US");
      await go("research");const f=page.frameLocator("#research-frame");
      await f.getByText("Filters · Starter · Bundle",{exact:true}).waitFor();
      await f.locator("#list li").first().click();
      await f.getByRole("button",{name:"Copy",exact:true}).waitFor();
      const before=await f.locator("#plv1-data").textContent(),preview=await f.locator("#pv").innerText();
      // Parent sends only the presentation preference; Frozen body and variables remain source_original.
      await page.evaluate(()=>document.querySelector("#research-frame").contentWindow.postMessage({type:"display_locale",locale:"ko-KR"},location.origin));
      await f.getByRole("button",{name:"Copy (복사)",exact:true}).waitFor();
      assert.equal(await f.locator("#plv1-data").textContent(),before);
      assert.equal(await f.locator("#pv").innerText(),preview);
    });
    await check("mobile/desktop search and settings without overflow",async()=>{
      for(const width of [360,390,1280]) {
        await page.setViewportSize({width,height:844});
        await go("settings");await page.locator("#global-search").fill("Consumer Price Index");
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      }
    });
    await check("storage failure preserves settings source",async()=>{
      const broken=await browser.newContext();
      await broken.route("**/*",guard);
      await broken.addInitScript(()=>localStorage.setItem("investment.web.v1.settings","{broken"));
      const p=await broken.newPage();responses(p);await p.goto(new URL("#settings",base).href);
      await p.locator("#display-locale").selectOption("en-US");
      assert.equal(await p.evaluate(()=>localStorage.getItem("investment.web.v1.settings")),"{broken");
      await broken.close();
    });
    await check("no external calls, unsafe requests, failed responses or page errors",async()=>{
      assert.deepEqual(traffic,{external:0,unsafe:0,failed_responses:0});
      assert.deepEqual(errors,[]);
    });
    console.log(JSON.stringify({passed:true,checks,errors}));
    fs.writeFileSync(path.join(out,"global-language-search-browser.json"),JSON.stringify({passed:true,checks,errors,traffic},null,2));
  } catch(e) {
    fs.writeFileSync(path.join(out,"global-language-search-browser.json"),JSON.stringify({passed:false,checks,errors,traffic,error:String(e),stack:e.stack},null,2));
    console.error("FAIL "+String(e).split("\n")[0]);
    process.exitCode=1;
  } finally {await browser.close();}
})();
