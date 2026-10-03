"use strict";
const fs=require("fs"),path=require("path"),crypto=require("crypto"),assert=require("assert");
const {chromium}=require("playwright");
const root=__dirname,dir=path.join(root,"isolated-web");
const hash=file=>crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
(async()=>{
 const browser=await chromium.launch({executablePath:"/usr/bin/chromium",headless:true,args:["--no-sandbox","--disable-background-networking"]});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 let unexpected=0;const errors=[];
 page.on("pageerror",e=>errors.push(e.message));
 await page.route("**/*",async route=>{
  const u=new URL(route.request().url());
  if(u.origin!=="https://g3.invalid"){unexpected++;return route.abort();}
  const rel=u.pathname==="/"?"index.html":u.pathname.slice(1),file=path.resolve(dir,rel);
  if(!file.startsWith(dir+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:"not found"});
  const ext=path.extname(file),type={".html":"text/html",".json":"application/json",".js":"text/javascript",".css":"text/css"}[ext]||"application/octet-stream";
  return route.fulfill({status:200,contentType:type,body:fs.readFileSync(file)});
 });
 await page.goto("https://g3.invalid/index.html#company/G3_SYNTHETIC_TEST_VECTOR_ONLY");
 await page.locator("#content h1").waitFor();
 await page.waitForFunction(()=>document.querySelector("#content")?.innerText.includes("11.11"));
 const visible=await page.locator("#content").innerText();
 const badge=await page.locator(".badge.LIVE").allTextContents();
 assert(visible.includes("11.11")&&badge.some(x=>x==="LIVE"));
 await page.screenshot({path:path.join(root,"g3-live-research-mobile.png"),fullPage:true});
 const receipt={source_head:"2b53b27fe0f570557159d02552911e9e1cc7be9c",scope:"HAND_BUILT_TEST_VECTOR_ONLY",actual_browser:true,
  browser_reproduction:"STILL_REPRODUCED_UPSTREAM: direct PROVISIONAL_RESEARCH qgv11.11 renders LIVE",
  live_badges:badge,rendered_test_value:"11.11",visible_text:visible,page_errors:errors,external_page_requests:unexpected,
  original_data_json_sha256:hash(path.join(dir,"data.json")),original_app_js_sha256:hash(path.join(dir,"app.js")),
  actual_network_data_access:"NONE: all page requests fulfilled from isolated local files",grants_issued:0};
 fs.writeFileSync(path.join(root,"reproduction-browser-receipt.json"),JSON.stringify(receipt,null,2)+"\n");
 console.log(JSON.stringify({browser_reproduction:receipt.browser_reproduction,page_errors:errors,external_page_requests:unexpected}));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
