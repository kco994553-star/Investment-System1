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
