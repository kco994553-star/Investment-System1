/* S03 portfolio (design canvas): badges, three required visualisations and the theme TARGET-vs-ACTUAL table.
   ACTUAL weights come only from this device (RAM, via DeviceActual.ramView); TARGET is never used as ACTUAL.
   Industry composition uses the SIC industry group v0 and the concentration warning the theme v0 default (> 40%),
   both from classification-screens.js (2026-10-11 user decision, uncalibrated); without it they stay NOT_AVAILABLE. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.PortfolioScreen=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const C=g.CompanyScreen,{esc,na,fmtPct,fmtPp,tr,typeName}=C;
const RING='<svg class="ring" viewBox="0 0 36 36" width="64" height="64" role="img" aria-label="';
function ring(ratio,label){
 const filled=Math.max(0,Math.min(1,ratio))*100;
 return RING+esc(label)+'"><circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--line)" stroke-width="4"></circle><circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--accent)" stroke-width="4" stroke-dasharray="'+filled.toFixed(2)+' '+(100-filled).toFixed(2)+'" transform="rotate(-90 18 18)"></circle></svg>';
}
/* Owner draft "투자시스템 화면 시안 (손그림 칠판)" (design lane D4): menu 5.1 is laid out as the numbered stamp sections of
   function 6.1 포트폴리오 구성 (6.1.1–6.1.5). The stamp numbers are function numbers, not menu numbers (the menu strip keeps
   5 / 5.1). Presentation only: the same badges, visuals, TARGET facts, ACTUAL summary and virtual card as before, grouped;
   6.1.1 reads only the states those already show (no count, amount or weight of its own). */
const FN=Object.freeze({'6.1.1':['종류 구분','Kinds'],'6.1.2':['모델 후보와 선정','Model candidates and selection'],'6.1.3':['비중과 조건','Weights and conditions'],
 '6.1.4':['입력과 버전','Inputs and versions'],'6.1.5':['개인·모의 구성 관리','Personal and paper sets']});
function fnSec(fn,locale,body){const T=tr(locale);
 return '<section class="pf-sec" data-fn="'+fn+'" aria-labelledby="pf-fn-'+fn.replace(/\./g,'-')+'"><h2 class="pf-head" id="pf-fn-'+fn.replace(/\./g,'-')+'"><span class="ia-sec" data-fn-stamp>'+fn+'</span> '+esc(T(...FN[fn]))+'</h2>'+body+'</section>';}
// 6.1.1: model · mine · paper, each with the state the screen already knows (model: not built; mine: the ACTUAL badge state;
// paper: whether this page holds shadow-ledger judgements from the report). Links only; nothing is computed here.
function kinds({locale,ram=null,virtual=null}){
 const T=tr(locale),js=virtual&&virtual.judgements&&typeof virtual.judgements==='object'&&Object.keys(virtual.judgements).length>0;
 const mine=!ram?['NOT_AVAILABLE',T('읽는 중','Reading')]:ram.state==='AVAILABLE'?['LIVE',T('시세 반영','Valued with quotes')]:ram.reason==='NO_ACTUAL'?['NOT_AVAILABLE',T('기기에 보유 없음','No holdings on this device')]
  :ram.reason==='READ_FAILED'?['NOT_AVAILABLE',T('기기 보유를 열 수 없음','Device holdings could not be opened')]:['NOT_AVAILABLE',T('입력됨 · 시세 부족','Entered · quotes incomplete')];
 const card=(kind,title,badge,body,href,link)=>'<article class="pf-kind" data-kind="'+kind+'"><h3>'+esc(title)+'</h3><p class="pf-kind-state">'+badge+'</p><p class="small">'+esc(body)+'</p><a href="'+href+'">'+esc(link)+'</a></article>';
 return card('model',T('모델 적합 포트폴리오','Model portfolio'),'<span class="badge NOT_AVAILABLE pf-mark" data-kind-state="NOT_COMPUTED">'+esc(T('미산출','Not computed'))+'</span>',
   T('전략 규칙대로 만드는 기준 포트폴리오 · 생성기 없음','Reference portfolio built by the strategy rules · no generator yet'),'#model',T('모델 포트폴리오 →','Model portfolio →'))
  +card('mine',T('내 포트폴리오 (실제)','My portfolio (actual)'),'<span class="badge '+mine[0]+'" data-kind-state="'+mine[0]+'">'+esc(mine[1])+'</span>',
   T('실제 보유(ACTUAL) · 이 기기에만 저장 · 공개하지 않음','Actual holdings · stored on this device only · never published'),'#actual',T('실제 보유 입력 →','Actual holdings →'))
  +card('paper',T('모의 포트폴리오','Paper portfolio'),'<span class="badge '+(js?'LIVE':'NOT_AVAILABLE')+'" data-kind-state="'+(js?'LIVE':'NOT_AVAILABLE')+'">'+esc(js?T('그림자 장부 판단 있음 · 이 페이지','Shadow-ledger judgements · this page'):T('보고서에서 계산 전','Not computed on the report yet'))+'</span>',
   T('가상 매매 세트 A~D + 규칙대로 했다면(그림자 장부) · 가상 기록','Virtual sets A–D + “had the rules been followed” (shadow ledger) · virtual records'),'#report/mock',T('모의 일일 보고 →','Paper daily report →'));
}
function shell(locale,virtual=null){
 const T=tr(locale),en=locale==='en-US';
 return '<p class="small pf-legend" data-fn-legend="6.1">'+esc(T('기능 6.1 포트폴리오 구성 (메뉴 5.1) · 상자의 번호는 기능 번호이며 메뉴 번호가 아닙니다.','Function 6.1 Portfolio composition (menu 5.1) · the stamp numbers are function numbers, not menu numbers.'))+'</p>'
  +fnSec('6.1.1',locale,'<div class="pf-kinds" data-portfolio-kinds>'+kinds({locale,ram:null,virtual})+'</div>')
  +fnSec('6.1.2',locale,'<div class="pf-pair"><section class="card" data-model-candidates><h2>'+esc(T('모델 후보','Model candidates'))+'</h2><p><span class="badge NOT_AVAILABLE pf-mark">'+esc(T('미산출','Not computed'))+'</span> '+esc(T('모델 후보를 만드는 생성기가 아직 없습니다. 실데이터 QGV 연결 전에는 MODEL을 만들지 않고, TARGET으로 대신 채우지 않습니다.','There is no generator for model candidates yet. No MODEL before real-data QGV, and TARGET never fills in for it.'))+'</p><a href="#model">'+esc(T('모델 · TARGET · ACTUAL 비교 →','Model · TARGET · ACTUAL →'))+'</a></section>'
   +'<section class="card" data-target-v0-facts><h2>TARGET v0 · 출발점·비교 기준</h2><p>반도체 묶음 55% · 업종 묶음 상한(40%) 초과</p><a href="#playbook">TARGET v1 작성 →</a></section></div>')
  +fnSec('6.1.3',locale,'<div id="portfolio-visuals" data-portfolio-visuals>'+visuals({locale,catalog:null,ram:null,screens:null,idByTicker:new Map()})+'</div>')
  +fnSec('6.1.4',locale,'<div class="chips data-badges" data-portfolio-badges>'+badges({locale,catalog:null,ram:null})+'</div>'
   +'<section class="card" data-portfolio-card="actual"><h2>ACTUAL · '+(en?'This device':'이 기기')+'</h2><a href="#actual" class="button">'+(en?'Enter / manage ACTUAL holdings':'ACTUAL 입력·관리')+'</a><div id="device-actual-summary" aria-live="polite"></div></section>')
  +fnSec('6.1.5',locale,'<div data-portfolio-virtual>'+virtualCard(locale,virtual)+'</div>'
   +'<nav class="chips pf-sets" data-portfolio-sets aria-label="'+esc(T('모의 세트와 플레이북','Paper sets and playbook'))+'">'+[['#report/mock-set_a',T('세트 A','Set A')],['#report/mock-set_b',T('세트 B','Set B')],['#report/mock-set_c',T('세트 C','Set C')],['#report/mock-set_d',T('세트 D','Set D')],['#report/mock-compare',T('세트 비교','Compare sets')],['#playbook',T('플레이북 · 산 이유·무효화 조건','Playbook · reasons and invalidation')]].map(([h,l])=>'<a href="'+h+'">'+esc(l)+'</a>').join('')+'</nav>'
   +'<p class="small">'+esc(T('세트 B·C·D는 내 비공개 구글 시트에 정의합니다. 가상 기록이며 실제 계좌와 합치지 않습니다.','Sets B, C and D are defined in your private Google Sheet. Virtual records, never merged with the real account.'))+'</p>')
  +'<p class="small">'+esc(T('보유 정보는 이 기기에만 저장되며 공개 저장소·Pages에 올라가지 않습니다. 매수·매도 지시 아님 · 주문 기능 없음.','Holdings stay on this device and never reach the public repository or Pages. Not a buy/sell instruction · no order function.'))+'</p>';
}
/* Virtual judgements of the shadow ledger ("규칙대로 했다면") as computed on S17 (투자 일일보고서) in this page's RAM:
   {date, judgements:{cid: engine judgement}, names:{cid: ticker}}. Same chips, order and reason labels as S17
   (VirtualTrading.judgementHtml / reasonsHtml / compareRows) and the fixed disclaimer. Nothing here runs the rules,
   fetches prices or stores anything; without an S17 result the card reads NOT_AVAILABLE. */
function virtualCard(locale,virtual){
 const VT=g.VirtualTrading,T=tr(locale);if(!VT)return '';
 let h='<section class="card" data-portfolio-card="virtual"><h2>'+esc(T('가상 판단 · 그림자 장부','Virtual judgements · shadow ledger'))+' '+VT.disclaimerHtml(locale)+'</h2>';
 const js=virtual&&virtual.judgements&&typeof virtual.judgements==='object'?virtual.judgements:null;
 if(!js||!Object.keys(js).length)return h+'<p data-virtual-state="NOT_AVAILABLE">'+na(T('투자 일일보고서에서 그림자 장부를 계산하면 같은 판단이 여기에 표시됩니다.','Run the shadow ledger on the investment daily report to show the same judgements here.'),locale)+'</p><a href="#report/real">'+esc(T('투자 일일보고서 →','Investment daily report →'))+'</a></section>';
 const names=virtual.names||{},rows=Object.keys(js).map(cid=>({company:cid,main:js[cid].main,j:js[cid]})).sort(VT.compareRows);
 h+='<p class="small" data-virtual-date="'+esc(virtual.date||'')+'">'+esc(T('기준 완료 거래일 ','Completed session ')+(virtual.date||'NOT_AVAILABLE')+T(' · 실제 계좌 지시가 아닌 "규칙대로 했다면"의 가상 기록',' · a virtual "had the rules been followed" record, not an account instruction'))+'</p>';
 h+='<ul class="vt-list" data-virtual-list>'+rows.map(r=>'<li data-virtual-company="'+esc(r.company)+'"><b>'+esc(names[r.company]||r.company)+'</b>'+VT.judgementHtml(r.j,{locale})+VT.reasonsHtml(VT.reasonCodes(r.j),{locale})+'</li>').join('')+'</ul>';
 return h+'<p class="small" data-level-priority>'+esc(T('우선순위: ','Priority: ')+VT.priorityText(locale))+'</p></section>';
}
function badges({locale,catalog,ram}){
 const T=tr(locale);let actual,quote;
 if(!ram||ram.reason==='NO_ACTUAL'||ram.reason==='READ_FAILED')actual='ACTUAL NOT_AVAILABLE · '+T('기기에 보유 없음','no holdings on this device');
 else if(ram.state==='AVAILABLE')actual='ACTUAL · '+T('시세 반영','valued with quotes');
 else actual='ACTUAL · '+T('입력됨, 시세 부족','entered, quotes incomplete');
 // D10: quote_as_of = the oldest CONFIRMED price time/date only; unconfirmed prices and the read time are named apart.
 const PT=g.PriceTime,unc=ram&&ram.quote_unconfirmed>0?ram.quote_unconfirmed:0,read=ram&&ram.quote_read_at&&PT?PT.clock(ram.quote_read_at):null;
 quote=ram&&(ram.quote_as_of||unc)?[ram.quote_as_of?T('가격 기준 ','Price time ')+(PT&&PT.clock(ram.quote_as_of)||ram.quote_as_of):null,unc?(PT?T(PT.UNCONFIRMED_KO,PT.UNCONFIRMED_EN):'UNCONFIRMED')+' '+unc+T('건',' rows'):null,read?T('읽은 시각 ','Read at ')+read:null].filter(Boolean).join(' · '):T('시세 기준 NOT_AVAILABLE','Quote time NOT_AVAILABLE');
 return '<span class="badge" data-badge="target">'+esc('TARGET '+T('사용자 ','user ')+(catalog&&catalog.target_root_version?catalog.target_root_version:'NOT_AVAILABLE'))+'</span>'
  +'<span class="badge '+(ram&&ram.state==='AVAILABLE'?'LIVE':'NOT_AVAILABLE')+'" data-badge="actual">'+esc(actual)+'</span>'
  +'<span class="badge NOT_AVAILABLE" data-badge="quote">'+esc(quote)+'</span>'+(ram&&ram.stale?'<span class="badge freshness STALE">STALE</span>':'')
  +'<span class="badge NOT_AVAILABLE" data-badge="quarter">'+esc(T('분기 스냅샷 NOT_AVAILABLE · 현재 기기 값','Quarter snapshot NOT_AVAILABLE · current device values'))+'</span>';
}
// Weights of positions with a usable ACTUAL weight, joined to public price-free memberships. Null memberships are never zero-filled.
function typeExposure({ram,screens,idByTicker}){
 const file=screens&&screens['company-types-pricefree.json'];
 if(!ram)return{ok:false,reason:'LOADING'};
 if(ram.state!=='AVAILABLE')return{ok:false,reason:ram.reason==='NO_ACTUAL'||ram.reason==='READ_FAILED'?ram.reason:'NO_QUOTES'};
 if(!file||!file.data)return{ok:false,reason:'NO_PUBLIC_TYPES'};
 const rows=ram.rows.filter(r=>Number.isFinite(r.weight)&&r.weight>0);
 if(!rows.length)return{ok:false,reason:'NO_POSITIONS'};
 const perType=Object.fromEntries(C.TYPES.map(t=>[t,{value:0,covered:0,unknown:0}])),combos=new Map();let unclassified=0,nodata=0;
 for(const r of rows){
  const rec=C.record(screens,'company-types-pricefree.json',idByTicker.get(r.ticker)),usable=rec&&rec.state!=='NOT_AVAILABLE';
  for(const t of C.TYPES){const m=usable?rec.memberships[t]:null;if(typeof m==='number'){perType[t].value+=r.weight*m;perType[t].covered+=r.weight;}else perType[t].unknown+=r.weight;}
  if(!usable){nodata+=r.weight;continue;}
  const picked=C.selectTypes(rec.memberships);
  if(!picked||!picked.length){unclassified+=r.weight;continue;}
  const key=picked.join('+');combos.set(key,(combos.get(key)||0)+r.weight);
 }
 return{ok:true,perType,combos:[...combos.entries()].sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:1)),unclassified,nodata};
}
function whyNot(reason,locale){
 const T=tr(locale);
 return reason==='NO_ACTUAL'?T('기기에 ACTUAL 보유가 없습니다. TARGET으로 대신 계산하지 않습니다.','No ACTUAL holdings on this device. TARGET is not used instead.')
  :reason==='LOADING'?T('기기 보유를 읽는 중입니다.','Reading device holdings.')
  :reason==='READ_FAILED'?T('기기 보유 데이터를 열 수 없습니다.','Device holdings could not be opened.')
  :reason==='NO_PUBLIC_TYPES'?T('공개 유형 자료가 연결되지 않았습니다.','Public type data is not connected.')
  :reason==='NO_POSITIONS'?T('양수 보유가 없습니다.','No positive holdings.')
  :T('시세·환율이 모두 입력되어야 ACTUAL 비중을 계산합니다.','ACTUAL weights need every quote and FX rate entered.');
}
function visuals({locale,catalog,ram,screens,idByTicker}){
 const T=tr(locale),ex=typeExposure({ram,screens,idByTicker});
 const CS=g.ClassificationScreens,cls=screens&&CS?screens[CS.FILE]:null;
 const industry=CS?CS.industryCard({locale,ram,payload:cls,idByTicker}):'<section class="card" data-portfolio-card="industry"><h2>'+esc(T('산업 구성','Industry composition'))+'</h2><p>'+na(T('SEC SIC→업종군 표가 사용자 승인 대기라 자료 없음입니다. 전략 테마로 대신 채우지 않습니다.','The SEC SIC to industry-group table awaits your approval. Strategy themes do not fill this in.'),locale)+'</p></section>';
 let types,combos;
 if(!ex.ok){
  const reason=na(whyNot(ex.reason,locale),locale);
  types='<section class="card" data-portfolio-card="types"><h2>'+esc(T('투자 유형 구성','Investment-type composition'))+'</h2><p>'+reason+'</p></section>';
  combos='<section class="card" data-portfolio-card="combos"><h2>'+esc(T('유형 중복 조합','Type-overlap combinations'))+'</h2><p>'+reason+'</p></section>';
 }else{
  types='<section class="card" data-portfolio-card="types"><h2>'+esc(T('투자 유형 구성','Investment-type composition'))+'</h2><p class="small">'+esc(T('유형별로 독립 계산 · 중복이 있어 합계가 100%를 넘을 수 있음 · 소속도 가중 ACTUAL 비중','Each type is independent · overlap can push the total above 100% · membership-weighted ACTUAL share'))+'</p><div class="ring-grid">'
   +C.TYPES.map(t=>{const p=ex.perType[t];if(!p.covered)return '<div class="ring-cell" data-type="'+t+'"><b>'+esc(typeName(t,locale))+'</b><div>'+na('',locale)+'</div></div>';
    return '<div class="ring-cell" data-type="'+t+'"><b>'+esc(typeName(t,locale))+'</b>'+ring(p.value,typeName(t,locale)+' '+fmtPct(p.value,locale))+'<div class="num" data-type-value>'+esc(fmtPct(p.value,locale))+'</div>'+(p.unknown>0?'<div class="small">'+esc(T('자료 없음 ','No data '))+esc(fmtPct(p.unknown,locale))+'</div>':'')+'</div>';}).join('')+'</div></section>';
  const row=(label,ratio,attr)=>'<li data-combo="'+esc(attr)+'"><span>'+esc(label)+'</span><span class="num">'+esc(fmtPct(ratio,locale))+'</span></li>';
  combos='<section class="card" data-portfolio-card="combos"><h2>'+esc(T('유형 중복 조합','Type-overlap combinations'))+'</h2><p class="small">'+esc(T('정확한 조합 기준(공식 혼합 규칙) · 합계 100% · 미분류와 자료 없음은 따로 표시','Exact combinations (official mixing rule) · total 100% · unclassified and no-data shown separately'))+'</p><ul class="combo-list">'
   +ex.combos.map(([key,w])=>row(key.split('+').map(t=>typeName(t,locale)).join(' + '),w,key)).join('')+(ex.unclassified>0?row(T('미분류','Unclassified'),ex.unclassified,'unclassified'):'')+(ex.nodata>0?row(T('자료 없음','No data'),ex.nodata,'nodata'):'')+'</ul></section>';
 }
 return '<h2 class="section-title">'+esc(T('분기 필수 시각화','Required quarterly visuals'))+'</h2><div class="grid three">'+industry+types+combos+'</div>'+themeTable({locale,catalog,ram,screens,idByTicker});
}
function themeTable({locale,catalog,ram,screens,idByTicker}){
 const T=tr(locale),usable=ram&&ram.state==='AVAILABLE';
 const head='<section class="card" data-portfolio-card="themes"><h2>'+esc(T('전략 테마 목표 대비 실제','Strategy theme: TARGET vs ACTUAL'))+'</h2><p class="small">'+esc(T('산업과 다른 축입니다. ACTUAL은 이 기기의 보유·시세가 있을 때만 표시합니다.','A different axis from industry. ACTUAL appears only when this device has holdings and quotes.'))+'</p>';
 if(!catalog)return head+'<p>'+na(T('공개 카탈로그를 불러오는 중이거나 열 수 없습니다.','The public catalog is loading or could not be opened.'),locale)+'</p>'+concentration(locale,{catalog,ram,screens,idByTicker})+'</section>';
 const rows=catalog.themes.map(th=>{const target=th.target_units/catalog.total_units,r=usable?ram.themes.find(x=>x.theme_id===th.theme_id):null,w=r&&Number.isFinite(r.weight)?r.weight:null;
  return '<tr data-theme-row="'+esc(th.theme_id)+'"><td>'+esc(locale==='en-US'?th.label_en:th.label)+'</td><td class="num">'+esc(fmtPct(target,locale))+'</td><td class="num" data-theme-actual>'+esc(fmtPct(w,locale))+'</td><td class="num" data-theme-delta>'+esc(w===null?'—':fmtPp(w-target,locale))+'</td></tr>';}).join('');
 return head+'<div class="table-wrap"><table data-theme-table><thead><tr><th>'+esc(T('테마','Theme'))+'</th><th>TARGET</th><th>ACTUAL</th><th>'+esc(T('차이','Gap'))+'</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="small">TARGET '+esc(catalog.target_root_version)+(usable?'':' · ACTUAL — = NOT_AVAILABLE')+'</p>'+concentration(locale,{catalog,ram,screens,idByTicker})+'</section>';
}
function concentration(locale,ctx={}){const T=tr(locale),CS=g.ClassificationScreens;if(CS)return CS.concentrationBlock({locale,ram:ctx.ram,payload:ctx.screens?ctx.screens[CS.FILE]:null,catalog:ctx.catalog,idByTicker:ctx.idByTicker});return '<p data-concentration>'+esc(T('테마 쏠림 경고','Theme concentration warning'))+' '+na(T('경고 임계값이 아직 정해지지 않았습니다.','No warning threshold has been defined yet.'),locale)+'</p>';}
function paint(host,{locale,catalog,ram,screens,idByTicker,virtual=null}){
 if(!host)return;
 const badgeHost=host.querySelector('[data-portfolio-badges]'),visualHost=host.querySelector('[data-portfolio-visuals]'),virtualHost=host.querySelector('[data-portfolio-virtual]'),kindHost=host.querySelector('[data-portfolio-kinds]');
 if(kindHost)kindHost.innerHTML=kinds({locale,ram,virtual});
 if(badgeHost)badgeHost.innerHTML=badges({locale,catalog,ram});
 if(visualHost)visualHost.innerHTML=visuals({locale,catalog,ram,screens,idByTicker:idByTicker||new Map()});
 if(virtualHost)virtualHost.innerHTML=virtualCard(locale,virtual);
}
return Object.freeze({shell,paint,typeExposure,virtualCard,kinds});
});
