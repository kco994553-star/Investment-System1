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

/* Favorites and personal copies (directive §10), stored on THIS BROWSER only ("이 브라우저 기준" = this browser profile's
   localStorage for this site). Read once when the page loads and written only on an explicit click, every access in
   try/catch. The official catalog (title, body, variables, checks, preview, Copy) is never modified: a personal copy is a
   separate text labelled 개인 수정본, filled with the same checked values. No account sync exists (needs a new backend). */
const PL_FAV_KEY="investment.web.v1.prompt-favorites",PL_COPY_KEY="investment.web.v1.prompt-personal-copies",PL_MAX_CHARS=50000,PL_MAX_COPIES=100;
const PL_TEXT={
  view:["보기 · 이 브라우저 기준","View · this browser"],all:["전체","All"],fav:["즐겨찾기만","Favorites only"],mine:["개인 수정본 있는 것만","With a personal copy"],
  domains:["영역 바로가기","Jump to domain"],domainAll:["전체 영역","All domains"],
  storeNote:["즐겨찾기와 개인 수정본은 이 브라우저 기준으로 저장됩니다.","Favorites and personal copies are saved for this browser only."],
  storeMore:["‘이 브라우저 기준’이란?","What does “this browser” mean?"],
  storeDetail:["지금 쓰는 이 브라우저 프로필의 사이트 저장소에만 저장됩니다. 같은 컴퓨터라도 다른 브라우저·다른 프로필·다른 사용자 계정, 그리고 다른 기기와는 공유되지 않으며, 사이트 데이터를 지우거나 비공개 창을 닫으면 사라질 수 있습니다. 로그인 계정 동기화는 아직 없습니다(신규 백엔드 필요). 저장하지 못하면 화면에 알려 드리고 공식 원문 복사는 그대로 쓸 수 있습니다.","Saved only in this browser profile's storage for this site. Other browsers, other profiles, other users of the same computer and other devices do not share it, and clearing site data or closing a private window can remove it. There is no account sync yet (a new backend is required). If saving fails you are told, and copying the official text still works."],
  missingDomains:["뉴스·포트폴리오·백테스트 프롬프트는 공식 카탈로그에 아직 없습니다(새 카탈로그 버전과 소유자 승인 필요).","News, portfolio and backtest prompts are not in the official catalog yet (a new catalog version and owner approval are required)."],
  favOn:["★ 즐겨찾기 해제","★ Remove favorite"],favOff:["☆ 즐겨찾기","☆ Add favorite"],favMark:["즐겨찾기","Favorite"],mineMark:["개인 수정본","Personal copy"],
  official:["공식 원문 · 변경 불가","Official text · read-only"],
  personal:["개인 수정본","Personal copy"],personalBadge:["이 브라우저 기준","This browser"],
  personalHelp:["공식 원문은 바뀌지 않습니다. 개인 수정본은 이 브라우저에만 저장되고, 위에서 입력한 같은 변수 값으로 채워 복사합니다.","The official text never changes. A personal copy is saved in this browser only and is filled with the same variable values entered above."],
  make:["공식 원문으로 개인 수정본 만들기","Start a personal copy from the official text"],body:["개인 수정본 본문 ({{변수}} 표시는 그대로 두세요)","Personal copy text (keep the {{variable}} markers)"],
  save:["개인 수정본 저장","Save personal copy"],remove:["개인 수정본 삭제","Delete personal copy"],copy:["개인 수정본 채워서 복사","Fill and copy personal copy"],
  saved:["이 브라우저에 개인 수정본을 저장했습니다.","Personal copy saved in this browser."],removed:["개인 수정본을 삭제했습니다.","Personal copy deleted."],
  confirmRemove:["이 브라우저의 개인 수정본을 삭제할까요? 공식 원문은 그대로입니다.","Delete this browser's personal copy? The official text is unchanged."],
  storeFail:["이 브라우저 저장소를 쓸 수 없어 저장하지 못했습니다(비공개 창·저장소 차단 등).","Could not save: this browser's storage is unavailable (private window, blocked storage, …)."],
  tooLong:["개인 수정본은 50,000자까지 저장합니다.","Personal copies are limited to 50,000 characters."],tooMany:["개인 수정본은 100개까지 저장합니다. 다른 수정본을 지운 뒤 저장하세요.","Up to 100 personal copies. Delete one first."],
  empty:["본문이 비어 있습니다.","The text is empty."],notReady:["필수 변수를 먼저 채우세요(공식 원문과 같은 검사).","Fill the required variables first (same checks as the official text)."],
  unknownVars:["선언되지 않은 변수가 남아 있습니다: ","Undeclared variables remain: "],copied:["개인 수정본(공식 원문 아님)을 채워서 복사했습니다.","Copied the filled personal copy (not the official text)."],
  copyFail:["클립보드를 쓸 수 없습니다. 본문을 직접 복사하세요.","Clipboard unavailable. Copy the text yourself."],
  same:["공식 원문과 같음","Same as the official text"],differs:["공식 원문과 다름","Differs from the official text"],unsaved:["저장 안 됨","Not saved"],
  base:["기준 원문 ","Based on "],versionChanged:[" · 공식 원문 버전이 바뀌었습니다. 새 원문과 비교해 보세요."," · The official version changed; compare with the new text."],savedAt:[" · 저장 ",' · saved ']
};
const plText=key=>PL_TEXT[key][displayLocale==="en-US"?1:0];
const PL_DOMAINS={FUNDAMENTAL:["펀더멘털","Fundamental"],TECHNICAL:["기술적 분석","Technical"],DISCOVERY:["기업 발굴","Discovery"],MACRO:["매크로","Macro"],CROSS_VALIDATION:["교차 검증","Cross-validation"]};
const plKnown=new Set(DATA.prompts.map(p=>p.prompt_id));
function plRead(key){try{return JSON.parse(localStorage.getItem(key)||"null");}catch(_){return null;}}
function plWrite(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch(_){return false;}}
const plState=(()=>{
  const fav=plRead(PL_FAV_KEY),copies=plRead(PL_COPY_KEY),out={fav:new Set(),copies:{}};
  if(Array.isArray(fav))for(const id of fav)if(plKnown.has(id))out.fav.add(id);
  if(copies&&typeof copies==="object"&&!Array.isArray(copies))for(const [id,c] of Object.entries(copies))
    if(plKnown.has(id)&&c&&typeof c.body==="string")out.copies[id]={body:c.body.slice(0,PL_MAX_CHARS),saved_at:String(c.saved_at||""),content_version:String(c.content_version||"")};
  return out;
})();
// Aside: view filter, domain shortcuts (existing domains only) and the storage note.
const plAside=document.createElement("div");plAside.className="pl-personal-aside";plAside.dataset.promptPersonalAside="";
document.getElementById("f-kw").after(plAside);
function plRenderAside(){
  const view=document.getElementById("pl-view")?.value||"all",domain=document.getElementById("f-domain").value;
  const domains=[...new Set(DATA.prompts.map(p=>p.domain))];
  plAside.innerHTML=`<label for="pl-view">${esc(plText("view"))}</label><select id="pl-view" data-prompt-view>${["all","fav","mine"].map(v=>`<option value="${v}"${v===view?" selected":""}>${esc(plText(v))}${v==="fav"?" ("+plState.fav.size+")":v==="mine"?" ("+Object.keys(plState.copies).length+")":""}</option>`).join("")}</select>
    <div class="pl-domains" role="group" aria-label="${esc(plText("domains"))}" data-prompt-domains>${[["",plText("domainAll")],...domains.map(d=>[d,PL_DOMAINS[d]?PL_DOMAINS[d][displayLocale==="en-US"?1:0]:d])].map(([d,l])=>`<button type="button" data-prompt-domain="${esc(d)}" aria-pressed="${d===domain}">${esc(l)}</button>`).join("")}</div>
    <p class="muted pl-note" data-prompt-missing-domains>${esc(plText("missingDomains"))}</p>
    <details class="pl-store" data-prompt-storage-note><summary>${esc(plText("storeNote"))} ${esc(plText("storeMore"))}</summary><p class="muted">${esc(plText("storeDetail"))}</p></details>`;
  document.getElementById("pl-view").onchange=()=>{list();};
  plAside.querySelectorAll("[data-prompt-domain]").forEach(b=>b.onclick=()=>{const s=document.getElementById("f-domain");s.value=b.dataset.promptDomain;s.dispatchEvent(new Event("change"));});
}
// Counts and pressed states only (keeps keyboard focus on the clicked control).
function plSyncAside(){
  const domain=document.getElementById("f-domain").value;
  plAside.querySelectorAll("[data-prompt-domain]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.promptDomain===domain)));
  for(const o of plAside.querySelectorAll("#pl-view option"))o.textContent=plText(o.value)+(o.value==="fav"?" ("+plState.fav.size+")":o.value==="mine"?" ("+Object.keys(plState.copies).length+")":"");
}
document.getElementById("f-domain").addEventListener("change",plSyncAside);
// List: favorite/personal marks and the view filter, applied after the original list() renders.
function plDecorateList(){
  const view=document.getElementById("pl-view")?.value||"all";let shown=0;
  for(const li of document.querySelectorAll("#list li[data-id]")){
    const id=li.dataset.id,fav=plState.fav.has(id),mine=Object.hasOwn(plState.copies,id);
    li.querySelector(".pl-mark")?.remove();li.querySelector(".pl-mine")?.remove();
    if(fav){const m=document.createElement("span");m.className="pl-mark";m.dataset.promptFavMark="";m.textContent="♥ ";m.setAttribute("aria-label",plText("favMark"));li.prepend(m);}
    if(mine){const m=document.createElement("span");m.className="badge pl-mine";m.dataset.promptMineMark="";m.textContent=plText("mineMark");li.querySelector(".code")?.before(m);}
    li.hidden=(view==="fav"&&!fav)||(view==="mine"&&!mine);if(!li.hidden)shown++;
  }
  if(view!=="all"){const c=document.getElementById("count");c.textContent=shown+" / "+DATA.prompts.length+" · "+plText(view);}
}
new MutationObserver(plDecorateList).observe(document.getElementById("list"),{childList:true});
// Detail: favorite toggle, official-text label and the personal copy panel. Rebuilt whenever select() replaces #detail.
let plDraft=null;
function plFillPersonal(body){
  const r=plvCheck({...cur,body},vals),left=[...new Set((r.text.match(/\{\{[a-z_]+\}\}/g)||[]))];
  return {text:r.text,ready:r.ready&&!left.length,missing:!r.ready,left};
}
function plRenderDetail(){
  const detail=document.getElementById("detail");if(!cur||!document.getElementById("pv")||detail.querySelector("[data-prompt-personal]"))return;
  const id=cur.prompt_id,saved=plState.copies[id],title=detail.querySelector("h2");
  const fav=document.createElement("button");fav.type="button";fav.id="pl-fav";fav.dataset.promptFavorite=id;
  const favPaint=()=>{const on=plState.fav.has(id);fav.textContent=plText(on?"favOn":"favOff");fav.setAttribute("aria-pressed",String(on));};favPaint();
  fav.onclick=()=>{const next=new Set(plState.fav);next.has(id)?next.delete(id):next.add(id);
    if(plWrite(PL_FAV_KEY,[...next])){plState.fav=next;favPaint();plSyncAside();list();}else plSay(plText("storeFail"));};
  title.after(fav);
  const label=document.createElement("p");label.className="pl-official";label.dataset.promptOfficialLabel="";label.innerHTML=`<span class="badge">${esc(plText("official"))}</span> <span class="code">${esc(DATA.content_version)} · ${esc(id)}</span>`;
  document.getElementById("pv").before(label);
  const panel=document.createElement("section");panel.id="pl-personal";panel.dataset.promptPersonal=id;panel.setAttribute("aria-labelledby","pl-personal-title");
  document.getElementById("copied").after(panel);plPaintPanel(panel,saved?saved.body:plDraft&&plDraft.id===id?plDraft.body:null);
}
function plSay(text){const s=document.getElementById("pl-status");if(s)s.textContent=text;}
function plPaintPanel(panel,body){
  const id=cur.prompt_id,saved=plState.copies[id],editing=typeof body==="string";
  panel.innerHTML=`<h3 id="pl-personal-title">${esc(plText("personal"))} <span class="badge">${esc(plText("personalBadge"))}</span></h3><p class="muted">${esc(plText("personalHelp"))}</p>`
    +(editing?`<label for="pl-body">${esc(plText("body"))}</label><textarea id="pl-body" data-prompt-personal-body rows="10" maxlength="${PL_MAX_CHARS}"></textarea>
      <p class="muted" data-prompt-personal-meta></p>
      <div class="pl-actions"><button type="button" data-prompt-personal-save>${esc(plText("save"))}</button><button type="button" data-prompt-personal-copy>${esc(plText("copy"))}</button>${saved?`<button type="button" data-prompt-personal-delete>${esc(plText("remove"))}</button>`:""}</div>`
     :`<div class="pl-actions"><button type="button" data-prompt-personal-make>${esc(plText("make"))}</button></div>`)
    +`<p id="pl-status" class="muted" role="status"></p>`;
  if(!editing){panel.querySelector("[data-prompt-personal-make]").onclick=()=>{plDraft={id,body:cur.body};plPaintPanel(panel,cur.body);panel.querySelector("#pl-body").focus();};return;}
  const area=panel.querySelector("#pl-body"),meta=panel.querySelector("[data-prompt-personal-meta]");area.value=body;
  const paintMeta=()=>{const s=plState.copies[id],dirty=!s||s.body!==area.value;
    meta.textContent=(area.value===cur.body?plText("same"):plText("differs"))+(dirty?" · "+plText("unsaved"):"")+(s?" · "+plText("base")+s.content_version+plText("savedAt")+s.saved_at+(s.content_version!==DATA.content_version?plText("versionChanged"):""):"");};
  paintMeta();area.oninput=()=>{plDraft={id,body:area.value};paintMeta();};
  panel.querySelector("[data-prompt-personal-save]").onclick=()=>{
    const text=area.value;if(!text.trim()){plSay(plText("empty"));return;}if(text.length>PL_MAX_CHARS){plSay(plText("tooLong"));return;}
    if(!Object.hasOwn(plState.copies,id)&&Object.keys(plState.copies).length>=PL_MAX_COPIES){plSay(plText("tooMany"));return;}
    const next={...plState.copies,[id]:{body:text,saved_at:new Date().toISOString(),content_version:DATA.content_version}};
    if(!plWrite(PL_COPY_KEY,next)){plSay(plText("storeFail"));return;}
    plState.copies=next;plDraft=null;plPaintPanel(panel,text);plSay(plText("saved"));plSyncAside();list();};
  const del=panel.querySelector("[data-prompt-personal-delete]");
  if(del)del.onclick=()=>{if(!confirm(plText("confirmRemove")))return;const next={...plState.copies};delete next[id];
    if(!plWrite(PL_COPY_KEY,next)){plSay(plText("storeFail"));return;}plState.copies=next;plDraft=null;plPaintPanel(panel,null);plSay(plText("removed"));plSyncAside();list();};
  panel.querySelector("[data-prompt-personal-copy]").onclick=()=>{
    const r=plFillPersonal(area.value);if(r.missing){plSay(plText("notReady"));return;}if(r.left.length){plSay(plText("unknownVars")+r.left.join(", "));return;}
    const done=()=>plSay(plText("copied")),fallback=()=>{area.focus();area.select();plSay(plText("copyFail"));};
    if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(r.text).then(done,fallback);else fallback();};
}
new MutationObserver(plRenderDetail).observe(document.getElementById("detail"),{childList:true});
window.addEventListener("message",e=>{
  if(e.source===parent&&e.origin===location.origin&&e.data?.type==="display_locale"&&AppLanguage.LOCALES.includes(e.data.locale)){
    plRenderAside();plDecorateList();const panel=document.getElementById("pl-personal");
    if(panel&&cur){const area=panel.querySelector("#pl-body");plPaintPanel(panel,area?area.value:null);}
    const fav=document.getElementById("pl-fav");if(fav&&cur)fav.textContent=plText(plState.fav.has(cur.prompt_id)?"favOn":"favOff");
    const label=document.querySelector("[data-prompt-official-label] .badge");if(label)label.textContent=plText("official");
  }
});
plRenderAside();plDecorateList();plRenderDetail();
