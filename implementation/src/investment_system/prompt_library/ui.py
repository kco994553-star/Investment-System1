"""E7 — minimal standalone Prompt Library page (Track E).

Flow: Prompt Library -> Domain / Role / Scope / Starter / Bundle / keyword -> select prompt -> description ->
Variable Fill -> Preview -> Copy. One self-contained static HTML file (no network, no external script, no LLM call);
the catalog is embedded from the validated Frozen catalog. The browser-side checks mirror fill.check_values (same
rules: required / ISO date / input_mode / positive int / as_of not in the future / prior_cutoff < as_of / no braces).

Linking this page into the shared App Shell navigation (contracts.product NAV_PAGES / product.render_app) is a shared
frontend change and is left as INTEGRATION_REQUIRED (Track E status document).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .catalog import Catalog, load_catalog
from .fill import NOT_PROVIDED, VARIABLE_GUIDES, variable_specs

DEFAULT_OUT = Path(__file__).resolve().parents[3] / "reports" / "prompt_library" / "prompt_library.html"


def catalog_payload(cat: Catalog) -> dict:
    """The data the page embeds: Active prompts (canonical bodies verbatim), variable specs, Starter, Bundle IDs."""
    return {
        "content_version": cat.content_version, "schema_version": cat.schema_version, "sha256": cat.sha256,
        "freeze_time": cat.freeze_time, "not_provided": NOT_PROVIDED,
        "starters": list(cat.starters),
        "bundles": [{"number": b.number, "name": b.name, "prompt_ids": list(b.prompt_ids)} for b in cat.bundles],
        "prompts": [{
            "prompt_id": p.prompt_id, "prompt_code": p.prompt_code, "title": p.title, "purpose": p.purpose,
            "domain": p.domain, "role": p.role, "category": p.category, "subcategory": p.subcategory,
            "tags": list(p.tags), "keywords": list(p.keywords), "aliases": list(p.aliases),
            "scopes": list(p.scopes), "system_overlap": p.system_overlap, "body": p.body,
            "variables": [{"name": s.name, "required": s.required, "kind": s.kind, "owner": s.system_input_owner,
                           "hint": s.hint, "guide": VARIABLE_GUIDES[s.name]} for s in variable_specs(p)],
        } for p in cat.active()],
    }


CSS = """
:root{--ink:#14202b;--paper:#f3eee4;--card:#fffdf8;--line:#d8cfc0;--acc:#1d4f61;--muted:#5b6770;--bad:#9a2f1f;--ok:#2d6a3e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ink:#e6e2d9;--paper:#161b1f;--card:#1f262b;--line:#34404a;--acc:#7fb6c9;--muted:#9aa6ad;--bad:#e38b7a;--ok:#8fc79c}}
*{box-sizing:border-box}body{margin:0;font-family:Georgia,"Iowan Old Style",serif;background:var(--paper);color:var(--ink)}
header{padding:16px 20px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:22px}.sub{color:var(--muted);font-size:13px;margin-top:4px}
.wrap{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:0;min-height:calc(100vh - 70px)}
aside{border-right:1px solid var(--line);padding:14px;overflow:auto;max-height:calc(100vh - 70px)}
main{padding:16px 22px;overflow:auto;max-height:calc(100vh - 70px)}
label{display:block;font-size:12px;color:var(--muted);margin:8px 0 3px}
input,select,textarea{width:100%;font:inherit;font-size:13px;padding:6px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
textarea{min-height:60px}.row{display:flex;gap:8px}.row>*{flex:1}
ul{list-style:none;padding:0;margin:10px 0}li{padding:7px 8px;border-bottom:1px solid var(--line);cursor:pointer;font-size:13px}
li:hover,li.on{background:var(--card)}.code{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--muted)}
.badge{display:inline-block;border:1px solid var(--line);font-size:11px;padding:1px 6px;margin:0 4px 4px 0}
pre{white-space:pre-wrap;word-break:break-word;background:var(--card);border:1px solid var(--line);padding:12px;font-size:13px;line-height:1.5}
.bad{color:var(--bad);font-size:13px}.ok{color:var(--ok);font-size:13px}button{font:inherit;padding:7px 14px;border:1px solid var(--acc);background:var(--acc);color:var(--paper);cursor:pointer}
button:disabled{opacity:.45;cursor:not-allowed}.muted{color:var(--muted);font-size:13px}
.field-group{min-width:0;border:1px solid var(--line);border-radius:10px;padding:14px;margin:16px 0}
.field-group legend{font-size:16px;font-weight:700;max-width:100%;padding:0 6px;overflow-wrap:anywhere}
.field-guide{min-width:0;margin:0 0 20px}.field-guide:last-child{margin-bottom:0}
.field-guide>label{font-size:15px;font-weight:700;color:var(--ink);margin:0 0 4px;line-height:1.5}
.field-required,.field-owner{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:2px 6px}
.field-required{margin-left:6px}.field-code-row{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;margin-bottom:6px}
.field-description,.field-source{font-size:13px;line-height:1.6;margin:6px 0;overflow-wrap:anywhere}
.field-source{color:var(--muted)}.field-caption{font-weight:600}
.field-guide input,.field-guide select,.field-guide textarea{min-height:44px;font-size:16px;border-radius:6px;min-width:0;max-width:100%}
.field-guide textarea{min-height:100px;resize:vertical}.field-guide input::placeholder,.field-guide textarea::placeholder{color:var(--muted);opacity:.85}
.field-date-row{display:flex;gap:8px;align-items:stretch;min-width:0}.field-date-row input{flex:1;min-width:0}
.field-date-row button{min-height:44px;flex-shrink:0;border-radius:6px;font-size:13px;padding:8px 12px}
.field-error{display:block;color:var(--bad);font-size:13px;line-height:1.6;overflow-wrap:anywhere}
.field-guide [aria-invalid="true"]{border-color:var(--bad)}
.field-mode-notes{font-size:12px;color:var(--muted);margin:6px 0;padding-left:18px;list-style:disc}
.field-mode-notes li{cursor:default;border:0;padding:2px 0;min-height:0;font-size:12px}.field-mode-notes li:hover{background:transparent}
.field-import-slot{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center}.field-import-slot button{min-height:44px;font-size:13px}
@media (max-width:800px){.wrap{grid-template-columns:1fr}aside,main{max-height:none}aside{border-right:0;border-bottom:1px solid var(--line)}}
"""

JS = r"""
const DATA = JSON.parse(document.getElementById('plv1-data').textContent);
const MODES = ['SYSTEM_CONTEXT', 'STANDALONE'];
function parseInstant(s){ s=s.trim(); if(/^\d{4}-\d{2}-\d{2}$/.test(s)){ const d=new Date(s+'T00:00:00+09:00'); return isNaN(d)?null:d; }
  if(!/(Z|[+-]\d{2}:\d{2})$/.test(s)) return null; const d=new Date(s); return isNaN(d)?null:d; }
function plvCheck(p, values, nowIso){ const norm={}, missing=[], invalid=[];
  const unknown=Object.keys(values).filter(k=>!p.variables.some(v=>v.name===k)).sort();
  for(const v of p.variables){ const t=String(values[v.name]==null?'':values[v.name]).trim();
    if(!t){ if(v.required) missing.push(v.name); else norm[v.name]=DATA.not_provided; continue; }
    if(t.includes('{{')||t.includes('}}')){ invalid.push(v.name+': placeholder braces are not allowed in values'); continue; }
    if(v.kind==='DATE' && !parseInstant(t)){ invalid.push(v.name+': not an ISO date (YYYY-MM-DD) or offset-aware ISO datetime'); continue; }
    if(v.kind==='INPUT_MODE' && !MODES.includes(t)){ invalid.push('input_mode: not in SYSTEM_CONTEXT/STANDALONE'); continue; }
    if(v.kind==='POSITIVE_INT' && !(/^\d+$/.test(t) && parseInt(t,10)>0)){ invalid.push(v.name+': not a positive integer'); continue; }
    norm[v.name]=t; }
  if(norm.as_of){ const a=parseInstant(norm.as_of), now=nowIso?new Date(nowIso):new Date();
    if(a>now) invalid.push('as_of: information cutoff lies in the future');
    if(norm.prior_cutoff){ const pc=parseInstant(norm.prior_cutoff); if(!(pc<a)) invalid.push('prior_cutoff: must be strictly before as_of'); } }
  const bad=new Set(invalid.map(s=>s.split(':')[0]));
  const text=p.body.replace(/\{\{([a-z_]+)\}\}/g,(m,n)=>(n in norm && !bad.has(n))?norm[n]:m);
  return {text, missing, invalid, unknown, ready: !(missing.length||invalid.length||unknown.length)}; }
if (typeof module !== 'undefined') { module.exports = { plvCheck, DATA }; }
"""

JS_UI = r"""
const byId = Object.fromEntries(DATA.prompts.map(p=>[p.prompt_id,p]));
const $=s=>document.querySelector(s); let cur=null; const vals={};
let fieldLocale='ko-KR';
const FIELD_COPY={
  target:['① 분석 대상·조건 (직접 입력)','① Analysis target and conditions (enter yourself)'],system:['② 시스템 결과·분석 방식 (앱에서 복사)','② System results and analysis mode (copy from app)'],
  required:['* 필수','* Required'],optional:['선택','Optional'],description:['무엇을 넣나요?','What to enter:'],source:['어디서 가져오나요?','Where to find it:'],
  today:['오늘 날짜','Today’s date'],modeBlank:['분석 방식을 선택하세요','Choose an analysis mode'],
  SYSTEM_CONTEXT:['SYSTEM_CONTEXT · 시스템 결과 읽기','SYSTEM_CONTEXT · System results'],STANDALONE:['STANDALONE · 자료 직접 제공','STANDALONE · Own data'],
  modeSystem:['SYSTEM_CONTEXT · 시스템 결과 읽기: 기존 결과를 그대로 사용하며 재계산하지 않습니다.','SYSTEM_CONTEXT · Read system results: use existing results without recalculating them.'],
  modeStandalone:['STANDALONE · 자료 직접 제공: 기준 날짜까지 확인한 자료를 직접 붙여넣습니다. 자료가 없으면 INSUFFICIENT_DATA로 종료합니다.','STANDALONE · Provide data yourself: paste evidence available by the cutoff date. Without evidence, stop with INSUFFICIENT_DATA.'],
  missing:['필수 입력입니다. 위 안내에 맞춰 내용을 입력하세요.','Required. Enter a value using the guidance above.'],
  braces:['값에 {{ 또는 }}를 넣지 마세요. 실제 내용을 입력하세요.','Enter actual content without {{ or }} placeholder braces.'],
  date:['YYYY-MM-DD 날짜 또는 시간대가 있는 ISO 시각을 입력하세요.','Enter a YYYY-MM-DD date or an ISO datetime with a timezone.'],
  future:['정보 기준 날짜는 미래일 수 없습니다.','The information cutoff cannot be in the future.'],
  prior:['이전 분석 날짜는 정보 기준 날짜보다 앞서야 합니다.','The prior cutoff must be earlier than the information cutoff.'],
  positive:['1 이상의 정수를 입력하세요.','Enter a positive whole number.'],
  mode:['분석 방식 목록에서 한 가지를 선택하세요.','Choose one of the listed analysis modes.'],
  invalid:['입력 형식을 확인하세요.','Check the value’s format.'],
  QGV:['QGV 결과','QGV results'],QGV_LEADERBOARD:['QGV 후보 목록','QGV candidate list'],
  TECHNICAL:['기술적 분석 결과','Technical results'],MACRO:['매크로 결과','Macro results'],INTEGRATED:['통합 결과','Integrated results']
};
function fieldText(key){return FIELD_COPY[key][fieldLocale==='en-US'?1:0];}
function guideText(v,key){return v.guide[key][fieldLocale];}
function putText(node,value){if(node&&node.textContent!==value)node.textContent=value;}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function opts(sel,items,first){ sel.innerHTML='<option value="">'+first+'</option>'+items.map(([v,l])=>`<option value="${esc(v)}">${esc(l)}</option>`).join(''); }
opts($('#f-domain'),[...new Set(DATA.prompts.map(p=>p.domain))].map(d=>[d,d]),'All domains (전체)');
opts($('#f-role'),['BASIC','EXPAND','CHALLENGE','BLIND-SPOT'].map(r=>[r,r]),'All roles (전체)');
opts($('#f-scope'),['COMPANY','INDUSTRY','THEME','UNIVERSE','MARKET'].map(s=>[s,s]),'All scopes (전체)');
opts($('#f-bundle'),DATA.bundles.map(b=>[b.number,b.number+'. '+b.name]),'No bundle (번들 없음)');
function list(){ const kw=$('#f-kw').value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const d=$('#f-domain').value,r=$('#f-role').value,s=$('#f-scope').value,st=$('#f-starter').checked,b=$('#f-bundle').value;
  let pool=DATA.prompts; if(b){ pool=DATA.bundles.find(x=>String(x.number)===b).prompt_ids.map(id=>byId[id]); }
  const res=pool.filter(p=>(!d||p.domain===d)&&(!r||p.role===r)&&(!s||p.scopes.includes(s))&&(!st||DATA.starters.includes(p.prompt_id))
    &&kw.every(k=>[p.prompt_id,p.prompt_code,p.title,p.purpose,...p.keywords,...p.aliases,...p.tags].join('\n').toLowerCase().includes(k)));
  $('#count').textContent=res.length+' / '+DATA.prompts.length;
  $('#list').innerHTML=res.map((p,i)=>`<li data-id="${p.prompt_id}" class="${cur&&cur.prompt_id===p.prompt_id?'on':''}">${b?(i+1)+'. ':''}${DATA.starters.includes(p.prompt_id)?'★ ':''}${esc(p.title)}<div class="code">${p.prompt_code} · ${p.domain} · ${p.role}</div></li>`).join('');
  document.querySelectorAll('#list li').forEach(li=>li.onclick=()=>select(li.dataset.id)); }
function select(id){ cur=byId[id]; for(const k in vals) delete vals[k];
  $('#detail').innerHTML=`<div class="code">${cur.prompt_code} · ${cur.prompt_id} · ${DATA.content_version}</div><h2>${esc(cur.title)}</h2>
   <div>${[cur.domain,cur.role,cur.category,cur.subcategory,cur.system_overlap].map(x=>`<span class="badge">${esc(x)}</span>`).join('')}</div>
   <p>${esc(cur.purpose)}</p>${cur.aliases.length?`<p class="muted">Aliases (별칭): ${cur.aliases.map(esc).join(' · ')}</p>`:''}
   <h3>Variables (변수)</h3><div id="form"></div><h3>Preview (미리보기)</h3><div id="status"></div><pre id="pv"></pre>
   <button id="copy">Copy (복사)</button> <span id="copied" class="ok"></span>`;
  const system=v=>!!v.owner||v.name==='input_mode';
  $('#form').innerHTML=fieldGroup('target',cur.variables.filter(v=>!system(v)))+fieldGroup('system',cur.variables.filter(system));
  document.querySelectorAll('[data-v]').forEach(el=>el.oninput=el.onchange=()=>{ vals[el.dataset.v]=el.value; render(); });
  const today=document.querySelector('[data-guide-today="as_of"]');
  if(today)today.onclick=()=>{
    const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
    const input=document.getElementById('plv-as_of');input.value=parts.year+'-'+parts.month+'-'+parts.day;input.dispatchEvent(new Event('input',{bubbles:true}));
  };
  $('#copy').onclick=copy; render(); list(); }
function fieldGroup(group,variables){return variables.length?`<fieldset class="field-group" data-guide-group="${group}"><legend data-guide-group-label="${group}">${esc(fieldText(group))}</legend>${variables.map(fieldMarkup).join('')}</fieldset>`:'';}
function fieldMarkup(v){
  const name=esc(v.name),id='plv-'+name,attrs=`id="${id}" data-v="${name}" aria-required="${v.required}" aria-describedby="${id}-description ${id}-source ${id}-error"`;
  let control=v.kind==='INPUT_MODE'?`<select ${attrs}><option value="" data-guide-mode="blank">${esc(fieldText('modeBlank'))}</option>${MODES.map(mode=>`<option value="${mode}" data-guide-mode="${mode}">${esc(fieldText(mode))}</option>`).join('')}</select>`
    :(v.kind==='DATE'||v.kind==='POSITIVE_INT'||['ticker','company','seed_ticker','seed_company','market','period','horizon'].includes(v.name))?`<input ${attrs} placeholder="${esc(guideText(v,'placeholder'))}" autocomplete="off">`
    :`<textarea ${attrs} placeholder="${esc(guideText(v,'placeholder'))}"></textarea>`;
  if(v.name==='as_of')control=`<div class="field-date-row">${control}<button type="button" data-guide-today="as_of">${esc(fieldText('today'))}</button></div>`;
  const modeHelp=v.kind==='INPUT_MODE'?`<ul class="field-mode-notes"><li data-guide-mode-help="modeSystem">${esc(fieldText('modeSystem'))}</li><li data-guide-mode-help="modeStandalone">${esc(fieldText('modeStandalone'))}</li></ul>`:'';
  return `<div class="field-guide" data-field-guide="${name}"><label for="${id}"><span data-guide-label="${name}">${esc(guideText(v,'label'))}</span><span class="field-required" data-guide-required="${name}">${esc(fieldText(v.required?'required':'optional'))}</span></label>
    <p class="field-description" id="${id}-description"><span class="field-caption" data-guide-caption="description">${esc(fieldText('description'))}</span> <span data-guide-description="${name}">${esc(guideText(v,'description'))}</span></p>
    ${control}${modeHelp}<span class="field-error" id="${id}-error" data-field-error="${name}"></span>
    <p class="field-source" id="${id}-source"><span class="field-caption" data-guide-caption="source">${esc(fieldText('source'))}</span> <span data-guide-source="${name}">${esc(guideText(v,'source'))}</span>${v.owner?` <span class="field-import-slot" data-system-import="${name}"></span>`:''}</p>
    <div class="field-code-row"><code class="code" data-guide-variable="${name}">${name}</code>${v.owner?`<span class="field-owner" data-guide-owner="${name}">${esc(fieldText(v.owner))}</span>`:''}</div></div>`;
}
function invalidReason(reason){
  if(reason.includes('placeholder braces'))return 'braces';
  if(reason.includes('not an ISO date'))return 'date';
  if(reason.includes('lies in the future'))return 'future';
  if(reason.includes('strictly before as_of'))return 'prior';
  if(reason.includes('not a positive integer'))return 'positive';
  if(reason.includes('not in SYSTEM_CONTEXT/STANDALONE'))return 'mode';
  return 'invalid';
}
function renderFieldErrors(result){
  for(const v of cur.variables){
    const reasons=result.invalid.filter(reason=>reason.split(':')[0]===v.name).map(reason=>fieldText(invalidReason(reason)));
    if(result.missing.includes(v.name))reasons.unshift(fieldText('missing'));
    const input=document.getElementById('plv-'+v.name),invalid=String(reasons.length>0);if(input.getAttribute('aria-invalid')!==invalid)input.setAttribute('aria-invalid',invalid);
    putText(document.querySelector(`[data-field-error="${v.name}"]`),reasons.join(' '));
  }
}
function plvFieldGuideLocalize(locale){
  fieldLocale=locale==='en-US'?'en-US':'ko-KR';if(!cur)return;
  for(const v of cur.variables){
    for(const key of ['label','description','source'])putText(document.querySelector(`[data-guide-${key}="${v.name}"]`),guideText(v,key));
    const input=document.getElementById('plv-'+v.name);if(v.kind!=='INPUT_MODE'&&input.placeholder!==guideText(v,'placeholder'))input.placeholder=guideText(v,'placeholder');
    putText(document.querySelector(`[data-guide-required="${v.name}"]`),fieldText(v.required?'required':'optional'));
    if(v.owner)putText(document.querySelector(`[data-guide-owner="${v.name}"]`),fieldText(v.owner));
  }
  document.querySelectorAll('[data-guide-group-label]').forEach(node=>putText(node,fieldText(node.dataset.guideGroupLabel)));
  document.querySelectorAll('[data-guide-caption]').forEach(node=>putText(node,fieldText(node.dataset.guideCaption)));
  document.querySelectorAll('[data-guide-mode]').forEach(node=>putText(node,fieldText(node.dataset.guideMode==='blank'?'modeBlank':node.dataset.guideMode)));
  document.querySelectorAll('[data-guide-mode-help]').forEach(node=>putText(node,fieldText(node.dataset.guideModeHelp)));
  putText(document.querySelector('[data-guide-today="as_of"]'),fieldText('today'));
  renderFieldErrors(plvCheck(cur,vals));
}
window.plvFieldGuideLocalize=plvFieldGuideLocalize;
function render(){ const r=plvCheck(cur,vals); $('#pv').textContent=r.text; $('#copy').disabled=!r.ready; $('#copied').textContent='';
  renderFieldErrors(r);
  $('#status').innerHTML=r.ready?'<p class="ok">Ready to copy (복사 가능)</p>':
    (r.missing.length?`<p class="bad">Missing required (필수 누락): ${r.missing.join(', ')}</p>`:'')+(r.invalid.length?`<p class="bad">Invalid (오류): ${r.invalid.map(esc).join(' / ')}</p>`:''); }
function copy(){ const r=plvCheck(cur,vals); if(!r.ready) return;
  const done=()=>{$('#copied').textContent='Copied (복사됨)';};
  if(navigator.clipboard&&window.isSecureContext){ navigator.clipboard.writeText(r.text).then(done,fallback); } else fallback();
  function fallback(){ const t=document.createElement('textarea'); t.value=r.text; document.body.appendChild(t); t.select(); try{document.execCommand('copy'); done();}catch(e){} t.remove(); } }
['#f-kw','#f-domain','#f-role','#f-scope','#f-starter','#f-bundle'].forEach(s=>{$(s).oninput=$(s).onchange=list;});
list();
const h=decodeURIComponent(location.hash.slice(1)); if(byId[h]) select(h);  // deep link: page.html#plv1.tech.001
"""


def render_html(cat: Catalog | None = None) -> str:
    cat = cat or load_catalog()
    data = json.dumps(catalog_payload(cat), ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prompt Library v1</title><style>{CSS}</style></head><body>
<header><h1>Prompt Library v1</h1><div class="sub">{html.escape(cat.content_version)} · Frozen {html.escape(cat.freeze_time)} ·
{len(cat.prompts)} Active · sha256 {cat.sha256[:12]}… — Copy-first: 변수 입력 → 미리보기 → 복사해서 원하는 AI에 붙여넣기.
결과는 투자결정이 아니라 추가 Research입니다.</div></header>
<div class="wrap"><aside>
<label>Keyword (검색)</label><input id="f-kw" placeholder="e.g. Margin, Delta, 경쟁">
<div class="row"><div><label>Domain</label><select id="f-domain"></select></div><div><label>Role</label><select id="f-role"></select></div></div>
<div class="row"><div><label>Scope</label><select id="f-scope"></select></div><div><label>Bundle</label><select id="f-bundle"></select></div></div>
<label><input type="checkbox" id="f-starter" style="width:auto"> Starter only (★ 시작 Prompt)</label>
<div class="muted" id="count"></div><ul id="list"></ul></aside>
<main id="detail"><p class="muted">왼쪽에서 Prompt를 선택하세요. ★ = Starter 6. Bundle은 순서대로 쓰는 Prompt 묶음이며 본문을 복제하지 않습니다.</p></main></div>
<script type="application/json" id="plv1-data">{data}</script>
<script>{JS}{JS_UI}</script></body></html>
"""


def write_html(out: Path | None = None, cat: Catalog | None = None) -> Path:
    path = Path(out) if out else DEFAULT_OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(cat), encoding="utf-8")
    return path
