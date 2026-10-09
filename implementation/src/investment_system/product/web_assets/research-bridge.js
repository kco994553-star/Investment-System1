// Product-owned accessibility/focus enhancement; canonical body and validation stay upstream.
document.getElementById("list").addEventListener("click", (e) => {
  if (e.target.closest("[data-id]")) {
    const d = document.getElementById("detail");
    d.tabIndex = -1;
    d.scrollIntoView({ block: "start" });
    d.focus();
  }
});
new MutationObserver(() =>
  document.querySelectorAll("#list li").forEach((li) => {
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    li.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        li.click();
      }
    };
  }),
).observe(document.getElementById("list"), { childList: true });
document.querySelectorAll("#list li").forEach((li) => {
  li.tabIndex = 0;
  li.setAttribute("role", "button");
  li.onkeydown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      li.click();
    }
  };
});
// Keep the original controls and listeners; disclose optional metadata and filters on demand.
const sub = document.querySelector("header .sub");
const info = document.createElement("details");
info.innerHTML = "<summary>콘텐츠 버전 · 사용법</summary>";
sub.before(info);
info.append(sub);
const aside = document.querySelector("aside");
const filters = document.createElement("details");
filters.innerHTML = "<summary>Filters(필터) · Starter · Bundle</summary>";
const rows = [...aside.querySelectorAll(".row")];
rows[0].before(filters);
rows.forEach((row) => filters.append(row));
filters.append(document.getElementById("f-starter").closest("label"));

/* Translate control labels only. Frozen catalog/title/body/preview/input remain original. */
let displayLocale="ko-KR";
const controls=new Map([
  ["콘텐츠 버전 · 사용법","콘텐츠 버전 · 사용법"],
  ["Filters(필터) · Starter · Bundle","Filters(필터) · Starter · Bundle"],
  ["Variables (변수)","Variables (변수)"],["Preview (미리보기)","Preview (미리보기)"],
  ["Copy (복사)","Copy (복사)"],["All domains (전체)","All domains (전체)"],
  ["All roles (전체)","All roles (전체)"],["All scopes (전체)","All scopes (전체)"],
  ["No bundle (번들 없음)","No bundle (번들 없음)"],["Ready to copy (복사 가능)","Ready to copy (복사 가능)"],["Copied (복사됨)","Copied (복사됨)"]
]);
for(const [value,key] of [...controls]) controls.set(AppLanguage.text(key,"en-US"),key);
function localizeControls() {
  document.documentElement.lang=displayLocale;
  if(window.plvFieldGuideLocalize) window.plvFieldGuideLocalize(displayLocale);
  // Explicit control selectors prevent source-original catalog and preview mutation.
  for(const e of document.querySelectorAll("summary,#detail h3,#copy,#copied,#status p,select option[value='']")) {
    const key=controls.get(e.textContent);
    if(key) {const value=AppLanguage.text(key,displayLocale);if(e.textContent!==value)e.textContent=value;}
  }
  for(const e of document.querySelectorAll("#status p")) {
    for(const key of ["Missing required (필수 누락)","Invalid (오류)"]) {
      const english=AppLanguage.text(key,"en-US"), desired=AppLanguage.text(key,displayLocale);
      for(const prefix of [key,english]) {
        if(e.textContent.startsWith(prefix+":") && !e.textContent.startsWith(desired+":"))
          e.textContent=desired+e.textContent.slice(prefix.length);
      }
    }
  }
}
try {displayLocale=AppLanguage.read(localStorage).value.display_locale;} catch(e) {}
localizeControls();
new MutationObserver(localizeControls).observe(document.body,{childList:true,subtree:true});
window.addEventListener("message",e=>{
  if(e.source===parent && e.origin===location.origin && e.data?.type==="display_locale" && AppLanguage.LOCALES.includes(e.data.locale)) {
    displayLocale=e.data.locale;localizeControls();
  }
});

// Optional public analysis imports. The parent projects an allowlist from its public read model;
// this page never reads device storage, fetches a snapshot or serializes arbitrary parent objects.
let publicResearchContext={fields:{},companies:[]};
const importText=key=>AppLanguage.text(key,displayLocale);
function publicImportValue(name) {
  const value=publicResearchContext.fields?.[name];if(!value) return null;
  if(["qgv_snapshot_summary","technical_input"].includes(name)) {
    const input=document.querySelector('[data-v="ticker"]') || document.querySelector('[data-v="seed_ticker"]');
    const ticker=input?.value.trim().toUpperCase();
    const matches=publicResearchContext.companies?.filter(company=>company.ticker.toUpperCase()===ticker) || [];
    if(matches.length!==1) return null;
    const rows=value.rows?.filter(row=>row.company_id===matches[0].company_id && row.ticker.toUpperCase()===ticker) || [];
    if(rows.length!==1) return null;
    return {...value,rows};
  }
  return value;
}
function renderPublicImports() {
  for(const slot of document.querySelectorAll('[data-system-import]')) {
    const name=slot.dataset.systemImport,value=publicImportValue(name),button=slot.querySelector('button');
    if(value) {
      if(!button) {
        slot.replaceChildren();const control=document.createElement('button');control.type='button';
        control.dataset.publicImport=name;control.textContent=importText('가져오기');
        control.onclick=()=>{
          const current=publicImportValue(name),field=document.querySelector('[data-v="'+name+'"]');
          if(!current || !field) return;
          field.value=JSON.stringify(current,null,2);field.dispatchEvent(new Event('input',{bubbles:true}));
        };slot.append(control);
      } else if(button.textContent!==importText('가져오기')) button.textContent=importText('가져오기');
    } else {
      let note=slot.querySelector('[data-import-unavailable]');
      if(!note) {slot.replaceChildren();note=document.createElement('span');note.dataset.importUnavailable=name;note.className='muted';slot.append(note);}
      const hasMode=!!document.querySelector('[data-v="input_mode"]'),
        key=hasMode?'현재 앱에 자료 없음 — 직접 입력하거나 STANDALONE 사용':'현재 앱에 자료 없음 — 직접 입력하세요.';
      if(note.textContent!==importText(key)) note.textContent=importText(key);
    }
  }
}
document.getElementById('form')?.addEventListener('input',renderPublicImports);
document.getElementById('detail').addEventListener('input',event=>{
  if(event.target.matches('[data-v="ticker"],[data-v="seed_ticker"]')) renderPublicImports();
});
new MutationObserver(renderPublicImports).observe(document.getElementById('detail'),{childList:true,subtree:true});
window.addEventListener('message',event=>{
  if(event.source!==parent || event.origin!==location.origin || event.data?.type!=='research_public_context') return;
  publicResearchContext=event.data.context || {fields:{},companies:[]};renderPublicImports();
});
if(parent!==window) parent.postMessage({type:'research_public_context_request'},location.origin);
