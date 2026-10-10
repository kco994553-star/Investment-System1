/* S03 portfolio (design canvas): badges, three required visualisations and the theme TARGET-vs-ACTUAL table.
   ACTUAL weights come only from this device (RAM, via DeviceActual.ramView); TARGET is never used as ACTUAL.
   Industry composition stays NOT_AVAILABLE until the SIC mapping is approved. No concentration threshold exists yet. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.PortfolioScreen=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const C=g.CompanyScreen,{esc,na,fmtPct,fmtPp,tr,typeName}=C;
const RING='<svg class="ring" viewBox="0 0 36 36" width="64" height="64" role="img" aria-label="';
function ring(ratio,label){
 const filled=Math.max(0,Math.min(1,ratio))*100;
 return RING+esc(label)+'"><circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--line)" stroke-width="4"></circle><circle cx="18" cy="18" r="15.9155" fill="none" stroke="var(--accent)" stroke-width="4" stroke-dasharray="'+filled.toFixed(2)+' '+(100-filled).toFixed(2)+'" transform="rotate(-90 18 18)"></circle></svg>';
}
function shell(locale){
 const T=tr(locale);
 return '<div class="chips data-badges" data-portfolio-badges>'+badges({locale,catalog:null,ram:null})+'</div>'
  +'<div id="portfolio-visuals" data-portfolio-visuals>'+visuals({locale,catalog:null,ram:null,screens:null,idByTicker:new Map()})+'</div>'
  +'<p class="small">'+esc(T('보유 정보는 이 기기에만 저장되며 공개 저장소·Pages에 올라가지 않습니다. 매수·매도·주문 기능은 없습니다.','Holdings stay on this device and never reach the public repository or Pages. There is no buy, sell or order feature.'))+'</p>';
}
function badges({locale,catalog,ram}){
 const T=tr(locale);let actual,quote;
 if(!ram||ram.reason==='NO_ACTUAL'||ram.reason==='READ_FAILED')actual='ACTUAL NOT_AVAILABLE · '+T('기기에 보유 없음','no holdings on this device');
 else if(ram.state==='AVAILABLE')actual='ACTUAL · '+T('시세 반영','valued with quotes');
 else actual='ACTUAL · '+T('입력됨, 시세 부족','entered, quotes incomplete');
 quote=ram&&ram.quote_as_of?T('시세 기준 ','Quotes as of ')+ram.quote_as_of:T('시세 기준 NOT_AVAILABLE','Quote time NOT_AVAILABLE');
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
 const industry='<section class="card" data-portfolio-card="industry"><h2>'+esc(T('산업 구성','Industry composition'))+'</h2><p>'+na(T('SEC SIC→업종군 표가 사용자 승인 대기라 자료 없음입니다. 전략 테마로 대신 채우지 않습니다.','The SEC SIC to industry-group table awaits your approval. Strategy themes do not fill this in.'),locale)+'</p></section>';
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
 return '<h2 class="section-title">'+esc(T('분기 필수 시각화','Required quarterly visuals'))+'</h2><div class="grid three">'+industry+types+combos+'</div>'+themeTable({locale,catalog,ram});
}
function themeTable({locale,catalog,ram}){
 const T=tr(locale),usable=ram&&ram.state==='AVAILABLE';
 const head='<section class="card" data-portfolio-card="themes"><h2>'+esc(T('전략 테마 목표 대비 실제','Strategy theme: TARGET vs ACTUAL'))+'</h2><p class="small">'+esc(T('산업과 다른 축입니다. ACTUAL은 이 기기의 보유·시세가 있을 때만 표시합니다.','A different axis from industry. ACTUAL appears only when this device has holdings and quotes.'))+'</p>';
 if(!catalog)return head+'<p>'+na(T('공개 카탈로그를 불러오는 중이거나 열 수 없습니다.','The public catalog is loading or could not be opened.'),locale)+'</p>'+concentration(locale)+'</section>';
 const rows=catalog.themes.map(th=>{const target=th.target_units/catalog.total_units,r=usable?ram.themes.find(x=>x.theme_id===th.theme_id):null,w=r&&Number.isFinite(r.weight)?r.weight:null;
  return '<tr data-theme-row="'+esc(th.theme_id)+'"><td>'+esc(locale==='en-US'?th.label_en:th.label)+'</td><td class="num">'+esc(fmtPct(target,locale))+'</td><td class="num" data-theme-actual>'+esc(fmtPct(w,locale))+'</td><td class="num" data-theme-delta>'+esc(w===null?'—':fmtPp(w-target,locale))+'</td></tr>';}).join('');
 return head+'<div class="table-wrap"><table data-theme-table><thead><tr><th>'+esc(T('테마','Theme'))+'</th><th>TARGET</th><th>ACTUAL</th><th>'+esc(T('차이','Gap'))+'</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="small">TARGET '+esc(catalog.target_root_version)+(usable?'':' · ACTUAL — = NOT_AVAILABLE')+'</p>'+concentration(locale)+'</section>';
}
function concentration(locale){const T=tr(locale);return '<p data-concentration>'+esc(T('테마 쏠림 경고','Theme concentration warning'))+' '+na(T('경고 임계값이 아직 정해지지 않았습니다.','No warning threshold has been defined yet.'),locale)+'</p>';}
function paint(host,{locale,catalog,ram,screens,idByTicker}){
 if(!host)return;
 const badgeHost=host.querySelector('[data-portfolio-badges]'),visualHost=host.querySelector('[data-portfolio-visuals]');
 if(badgeHost)badgeHost.innerHTML=badges({locale,catalog,ram});
 if(visualHost)visualHost.innerHTML=visuals({locale,catalog,ram,screens,idByTicker:idByTicker||new Map()});
}
return Object.freeze({shell,paint,typeExposure});
});
