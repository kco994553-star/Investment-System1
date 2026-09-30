// Presentation/navigation E2E using existing Web MVP build. Public fixtures only.
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
(async()=>{
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844}});
  const page=await context.newPage(), errors=[],checks=[];
  page.on("pageerror",e=>errors.push(e.message));
  const out="implementation/reports/web_mvp";
  fs.mkdirSync(out,{recursive:true});
  async function check(name,fn) {await fn();checks.push(name);}
  async function go(route) {
    await page.goto("http://127.0.0.1:8765/web-mvp-demo/#"+route);
    await page.waitForFunction(()=>typeof window.investmentSearch==="function");
  }
  async function locale(value) {
    await go("settings");await page.locator("#display-locale").selectOption(value);
    assert.equal(await page.locator("html").getAttribute("lang"),value);
  }
  try {
    await check("global search exact/alias/prefix/fuzzy same canonical route",async()=>{
      await go("home");
      for(const q of ["NVDA","nvda","NVIDIA","NVIDIA Corporation","엔비디아","nvida","nvdia","엔디비아","nvd","엔비디"]) {
        await page.locator("#global-search").fill(q);
        assert.equal(await page.locator("#global-results li").first().getAttribute("data-entity-id"),"COMPANY:nvda",q);
        assert.equal(await page.locator("#global-results li").first().locator("a").getAttribute("href"),"#company/nvda");
      }
      await page.locator("#global-search").fill("nvida");
      await page.locator("#global-search").press("ArrowDown");
      await page.keyboard.press("Enter");
      await page.getByRole("heading",{name:"NVDA",exact:true}).waitFor();
      assert.ok(page.url().endsWith("#company/nvda"));
      await go("companies");await page.locator("#search").fill("엔디비아");
      assert.equal(await page.locator("#company-list li").count(),1);
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
    // Supply finished public producer snapshots, including all numeric sections and source language.
    await page.route("**/data.json",async route=>{
      const response=await route.fetch(),b=await response.json();
      const env=data=>({state:"DEMO",as_of:"2024-12-31",source:"public presentation test",data});
      b.technical=env({nvda:{regime:"TREND_UP",execution_zone:"ADD",invalidation:"Original invalidation",volatility:0.123}});
      b.macro=env({state:"NORMAL",regime:"EXPANSION",indicators:{CPIAUCSL:300.2,growth:0.04}});
      b.portfolio.data.return=0.125;b.portfolio.data.market_value=12345.67;
      b.leaderboard=env({rows:[{company_id:"nvda",ticker:"NVDA",rank:2,total_score:90.79},{company_id:"asml",ticker:"ASML",rank:1,total_score:91}]});
      b.news=env([
        {event_id:"en",headline:"Original English headline",summary:"Original English summary",summary_localized:{"ko-KR":"한국어 요약","en-US":"English summary"},source_language:"en",available_at:"2024-12-31",source_original:{ticker:"NVDA",cik:"0001045810",accession:"0001045810-24-000264",source_url:"https://www.sec.gov/Archives/",provenance:"original",raw_source_data:"raw SEC filing"}},
        {event_id:"ko",headline:"한국어 원문 제목",summary:"한국어 원문 요약",source_language:"ko",available_at:"2024-12-31"}
      ]);
      await route.fulfill({response,json:b});
    });
    await check("ko/en UI, persistence, QGV/Technical/Macro/Portfolio/Leaderboard/source_original unchanged",async()=>{
      await go("settings");
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
      await go("leaderboard");await page.getByRole("heading",{name:"Company rankings"}).waitFor();
      assert.deepEqual(await page.locator("main .list a b").allTextContents(),["#2 NVDA","#1 ASML"]);
      await locale("ko-KR");
      assert.equal(await page.evaluate(()=>JSON.stringify(D)),before);
      await go("home");await page.getByRole("heading",{name:"오늘의 투자 화면"}).waitFor();
    });
    await check("source language filter independent; localized summaries retain raw originals",async()=>{
      await go("settings");await page.locator("#source-language").selectOption("en");
      await page.locator("#display-locale").selectOption("en-US");
      assert.equal(await page.locator("#source-language").inputValue(),"en");
      await go("news");
      assert.equal(await page.locator("#news-list>li").count(),1);
      assert.ok((await page.locator("#news-list").innerText()).includes("English summary"));
      assert.ok((await page.locator("#news-list pre").innerText()).includes("Original English summary"));
      await locale("ko-KR");assert.equal(await page.locator("#source-language").inputValue(),"en");
      await go("news");assert.equal(await page.locator("#news-list>li").count(),1);
      assert.ok((await page.locator("#news-list").innerText()).includes("한국어 요약"));
      await go("settings");await page.locator("#source-language").selectOption("ko");
      assert.equal(await page.locator("#display-locale").inputValue(),"ko-KR");
      await go("news");assert.ok((await page.locator("#news-list").innerText()).includes("한국어 원문 제목"));
      await go("settings");await page.locator("#source-language").selectOption("all");
    });
    await page.unroute("**/data.json");
    await check("existing News Network labels use global display locale and preserve model",async()=>{
      await locale("en-US");await go("news");await page.locator("#show-network").click();
      const f=page.frameLocator("#network-frame");
      await f.getByRole("button",{name:"Focus selected company"}).waitFor();
      const before=await page.locator("#network-frame").evaluate(e=>JSON.stringify(e.contentWindow.rigState().viewport));
      assert.equal(await f.locator("html").getAttribute("lang"),"en-US");
      await page.locator("#network-frame").evaluate(e=>e.contentWindow.postMessage({type:"display_locale",locale:"ko-KR"},location.origin));
      await f.getByRole("button",{name:"선택 기업 집중"}).waitFor();
      assert.equal(await page.locator("#network-frame").evaluate(e=>JSON.stringify(e.contentWindow.rigState().viewport)),before);
    });
    await check("research controls localized, Frozen payload/preview unchanged",async()=>{
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
        await go("settings");await page.locator("#global-search").fill("NVIDIA Corporation");
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      }
    });
    await check("storage failure preserves settings source",async()=>{
      const broken=await browser.newContext();
      await broken.addInitScript(()=>localStorage.setItem("investment.web.v1.settings","{broken"));
      const p=await broken.newPage();await p.goto("http://127.0.0.1:8765/web-mvp-demo/#settings");
      await p.locator("#display-locale").selectOption("en-US");
      assert.equal(await p.evaluate(()=>localStorage.getItem("investment.web.v1.settings")),"{broken");
      await broken.close();
    });
    assert.deepEqual(errors,[]);
    await page.screenshot({path:out+"/global-language-search.png",fullPage:true});
    fs.writeFileSync(out+"/global-language-search-browser.json",JSON.stringify({passed:true,checks,errors},null,2));
  } catch(e) {
    await page.screenshot({path:out+"/global-language-search-failure.png",fullPage:true});
    fs.writeFileSync(out+"/global-language-search-browser.json",JSON.stringify({passed:false,checks,errors,error:String(e),stack:e.stack},null,2));
    throw e;
  } finally {await browser.close();}
})();
