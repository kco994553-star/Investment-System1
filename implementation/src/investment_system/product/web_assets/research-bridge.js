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
