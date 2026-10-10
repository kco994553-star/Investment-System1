/* S04 company summary and S05 company analysis (design canvas). Presentation only: no new methodology,
   weights or thresholds. Public inputs are price-free; anything that needs a price, a SIC mapping or an
   approval stays NOT_AVAILABLE. ACTUAL is read from this device only and is never replaced by TARGET. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.CompanyScreen=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const TYPES=['growth','quality','cyclical','defensive'];
const TYPE_LABEL={growth:['성장','Growth'],quality:['우량','Quality'],cyclical:['경기민감','Cyclical'],defensive:['경기방어','Defensive']};
const FACTOR_LABEL={competitive_advantage:['경쟁우위','Competitive advantage'],roic_wacc:['ROIC−WACC','ROIC − WACC'],market_position:['시장 지위','Market position'],fcf_quality:['FCF 품질','FCF quality'],margin_quality:['마진 품질','Margin quality'],financial_health:['재무 건전성','Financial health'],management_quality:['경영진 품질','Management quality'],
 next_3_5y_growth:['향후 3~5년 성장','Next 3-5y growth'],growth_efficiency:['성장 효율','Growth efficiency'],revenue_growth:['매출 성장','Revenue growth'],eps_fcf_per_share_growth:['주당 EPS·FCF 성장','EPS / FCF per share growth'],growth_durability:['성장 지속성','Growth durability'],excess_growth_vs_industry:['업종 대비 초과성장','Excess growth vs industry']};
const TABS=[['summary','종합','Overview'],['business','사업·경쟁','Business'],['financials','재무','Financials'],['events','주가·이벤트','Price / events'],['factors','QGV 요소','QGV factors'],['value','가치·시나리오','Value / scenarios'],['compare','비교·컨센서스','Compare / consensus']];
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const na=(reason,locale)=>'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>'+(reason?' <span class="small">'+esc(reason)+'</span>':'');
const num=(v,locale,digits=1)=>new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v);
const fmtPct=(ratio,locale)=>typeof ratio==='number'&&Number.isFinite(ratio)?num(ratio*100,locale)+'%':'—';
const fmtPp=(ratio,locale)=>typeof ratio==='number'&&Number.isFinite(ratio)?(ratio>0?'+':ratio<0?'−':'')+num(Math.abs(ratio)*100,locale)+' %p':'—';
const typeName=(id,locale)=>TYPE_LABEL[id]?TYPE_LABEL[id][locale==='en-US'?1:0]:id;
const factorName=(id,locale)=>FACTOR_LABEL[id]?FACTOR_LABEL[id][locale==='en-US'?1:0]:id;
function record(screens,file,id){const p=screens?.[file];return p&&p.data&&p.data.companies&&Object.hasOwn(p.data.companies,id)?p.data.companies[id]:null;}
// Official mixing rule of type_config/1 (minimum_membership, maximum_types, exclusive_pairs, CONFIG_ORDER tie-break).
function selectTypes(memberships,config=g.TypeConfigDefaults){
 const mix=config&&config.mixing;if(!mix||!memberships)return null;
 const order=config.types.map(t=>t.id);
 const candidates=TYPES.filter(id=>typeof memberships[id]==='number'&&memberships[id]>=mix.minimum_membership).sort((a,b)=>memberships[b]-memberships[a]||order.indexOf(a)-order.indexOf(b));
 const out=[];for(const id of candidates){if(out.length>=mix.maximum_types)break;if(mix.exclusive_pairs.some(([x,y])=>(id===x&&out.includes(y))||(id===y&&out.includes(x))))continue;out.push(id);}
 return out;
}
function qgAxes(rec,engine=g.EnginePreview){
 if(!rec||rec.state==='NOT_AVAILABLE'||!engine||!rec.factors)return null;
 const observations={};for(const[f,v]of Object.entries(rec.factors))if(v&&v.score!==null&&v.state!=='NOT_AVAILABLE')observations[f]={score:v.score,quality:v.state==='LIVE'?'OK':'STALE_DATA'};
 const result=engine.strategy({observations});if(!result||!result.axes)return null;
 return{Q:result.axes.Q,G:result.axes.G,available:Object.keys(observations).length,total:Object.keys(rec.factors).length,state:rec.state};
}
function axisCell(axis,locale){
 const T=tr(locale);if(!axis||axis.score===null)return na('',locale);
 return '<span class="num">'+esc(num(axis.score,locale))+'</span>'+(axis.coverage==='READY'?'':' <span class="badge partial">'+esc(T('부분 · 누락 ','Partial · missing '))+axis.missing_factor_count+'</span>');
}
function classification(screens,id,locale){
 const T=tr(locale),rec=record(screens,'company-types-pricefree.json',id),picked=rec&&rec.state!=='NOT_AVAILABLE'?selectTypes(rec.memberships):null;
 const items=[['industry',T('산업','Industry'),na(T('SEC SIC→업종군 표가 사용자 승인 대기입니다.','The SEC SIC to industry-group table awaits your approval.'),locale)],
  ['theme',T('전략 테마','Strategy theme'),na(T('테마 바스켓이 사용자 승인 대기입니다.','Theme baskets await your approval.'),locale)],
  ['type',T('투자 유형','Investment type'),picked&&picked.length?picked.map(t=>'<span class="badge LIVE" data-type-chip="'+esc(t)+'">'+esc(typeName(t,locale))+' '+esc(num(rec.memberships[t],locale,2))+'</span>').join(' ')+' <span class="small">'+esc(T('소속도 0.3 이상','membership ≥ 0.3'))+'</span>'
   :na(rec?T('소속도 0.3 이상 유형 없음 또는 자료 없음','No type with membership ≥ 0.3, or no data'):T('공개 유형 자료가 연결되지 않았습니다.','Public type data is not connected.'),locale)]];
 return '<section class="card" data-company-card="classification"><h2>'+esc(T('분류 3축','Three classification axes'))+'</h2><ul class="axis-chips">'+items.map(([k,name,body])=>'<li data-axis="'+k+'"><b>'+esc(name)+'</b> '+body+'</li>').join('')+'</ul><p class="small">'+esc(T('산업 / 전략 테마 / 투자 유형은 서로 다른 축입니다. 서로 대신 채우지 않습니다.','Industry / strategy theme / investment type are separate axes. None substitutes for another.'))+'</p></section>';
}
function dataBadges(screens,locale,withPit){
 const T=tr(locale),p=screens?.['sec-qg-factors.json'],state=p?p.state:'NOT_AVAILABLE',aged=p&&state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(p.as_of)>p.stale_after_seconds*1000;
 return '<div class="chips data-badges" data-company-badges><span class="badge '+esc(state)+'" data-badge="data">'+esc(state)+'</span>'+(aged?'<span class="badge freshness STALE">STALE</span>':'')+'<span class="badge">'+esc(p?T('기준 ','As of ')+p.as_of:T('기준 시각 없음','No as-of'))+'</span><span class="badge">'+esc(T('점수 기준 v1 · 보정 전','Score basis v1 · uncalibrated'))+'</span><span class="badge NOT_AVAILABLE">'+esc(T('시세 NOT_AVAILABLE','Price NOT_AVAILABLE'))+'</span>'+(withPit?'<span class="badge" data-badge="pit">'+esc('PIT '+(p&&p.data.availability_basis?p.data.availability_basis:'NOT_AVAILABLE'))+'</span>':'')+'</div>';
}
function nextEarnings(screens,id,locale){
 const T=tr(locale),rec=record(screens,'sec-filing-windows.json',id),w=rec&&g.PublicScreens?g.PublicScreens.nextFilingWindow(rec):null;
 if(!w)return na(T('공시 시기 패턴 자료 없음','No filing-timing pattern'),locale);
 return '<span data-next-earnings>'+esc(w.form+' '+w.start+'–'+w.end+' · D-'+w.days_until_start)+'</span> <span class="small">'+esc(T('예상 시기 · 확정일 아님','Estimated timing · not a confirmed date'))+'</span>';
}
function qgvBody(screens,id,locale){
 const T=tr(locale),rec=record(screens,'sec-qg-factors.json',id),axes=qgAxes(rec);
 return '<dl class="kv"><dt>Q</dt><dd data-qgv="Q">'+(axes?axisCell(axes.Q,locale):na('',locale))+'</dd><dt>G</dt><dd data-qgv="G">'+(axes?axisCell(axes.G,locale):na('',locale))+'</dd>'
  +'<dt>V</dt><dd data-qgv="V">'+na(T('가격 필요 · 공개 파일에 가격 없음','Needs prices · public files carry none'),locale)+'</dd></dl>'
  +(axes?'<p class="small">'+esc(T('Q·G는 공식 가중치로 이 기기에서 계산한 미리보기입니다 · 요소 ','Q and G are a preview computed on this device with the official weights · factors '))+axes.available+'/'+axes.total+'</p>':'<p class="small">'+esc(T('공개 Q·G 요소 자료가 없습니다.','No public Q/G factor data.'))+'</p>');
}
function holdingPlaceholder(locale){
 const T=tr(locale);
 return '<h2>'+esc(T('내 보유','My holding'))+'</h2><p>'+na(T('공개 카탈로그를 불러오는 중이거나 이 기업이 TARGET에 없습니다.','Loading the public catalog, or this company is not in TARGET.'),locale)+'</p><a href="#actual">'+esc(T('ACTUAL 입력·관리 →','Enter / manage ACTUAL →'))+'</a>';
}
function holdingHtml({locale,catalog,inst,ram}){
 const T=tr(locale),theme=catalog.themes.find(x=>x.theme_id===inst.theme_id),target=inst.target_units/catalog.total_units;
 const row=ram&&ram.state==='AVAILABLE'?ram.rows.find(r=>r.ticker===inst.ticker&&Number.isFinite(r.weight)):null;
 const why=!ram||ram.state==='NOT_AVAILABLE'&&ram.reason==='NO_ACTUAL'?T('기기에 보유가 없습니다','No holdings on this device'):T('시세가 부족해 평가할 수 없습니다','Not enough quotes to value');
 return '<h2>'+esc(T('내 보유','My holding'))+'</h2><dl class="kv"><dt>'+esc(T('전략 테마','Strategy theme'))+'</dt><dd data-holding="theme">'+esc(locale==='en-US'?theme.label_en:theme.label)+'</dd>'
  +'<dt>TARGET · '+esc(catalog.target_root_version)+'</dt><dd data-holding="target">'+esc(fmtPct(target,locale))+'</dd>'
  +'<dt>ACTUAL</dt><dd data-holding="actual">'+(row?esc(fmtPct(row.weight,locale)):'— <span class="small">NOT_AVAILABLE</span>')+'</dd>'
  +'<dt>'+esc(T('차이','Gap'))+'</dt><dd data-holding="delta">'+(row?esc(fmtPp(row.weight-target,locale)):'—')+'</dd></dl>'
  +'<p class="small">'+esc(row?T('ACTUAL은 이 기기의 보유·시세로만 계산합니다(RAM).','ACTUAL is computed only from this device (RAM).'):T('ACTUAL 없음: ','ACTUAL unavailable: ')+why+T(' · TARGET으로 채우지 않습니다.',' · TARGET is not used as a substitute.'))+'</p><a href="#actual">'+esc(T('ACTUAL 입력·관리 →','Enter / manage ACTUAL →'))+'</a>';
}
async function mountHolding(host,{locale,ticker,catalogPromise,actual=g.DeviceActual,view=g}){
 if(!host)return;let catalog=null;try{catalog=await catalogPromise;}catch(_){}
 if(!host.isConnected)return;
 const inst=catalog&&ticker?catalog.instruments.find(i=>i.ticker===ticker):null;
 if(!inst){host.innerHTML=holdingPlaceholder(locale);return;}
 let ram=null;try{ram=actual&&actual.ramView?await actual.ramView(view,catalog):null;}catch(_){ram=null;}
 if(host.isConnected)host.innerHTML=holdingHtml({locale,catalog,inst,ram});
}
function summary(ctx){
 const{locale,id,screens}=ctx,T=tr(locale),link=(href,text)=>'<a href="'+href+'">'+esc(text)+'</a>';
 return ctx.headerHtml+dataBadges(screens,locale,false)
  +'<p class="small" data-price-na>'+esc(T('현재가·일간 등락','Price and daily move'))+' '+na(T('공개 파일에 가격 없음','Public files carry no prices'),locale)+'</p>'
  +classification(screens,id,locale)
  +'<section class="card" id="company-holding" data-company-card="holding">'+holdingPlaceholder(locale)+'</section>'
  +'<div id="company-groups">'+ctx.groupsHtml+'</div>'
  +'<section class="card" data-company-card="qgv"><h2><span class="flow-number">1</span> QGV</h2>'+qgvBody(screens,id,locale)
  +'<dl class="kv"><dt>'+esc(T('리더보드 순위','Leaderboard rank'))+'</dt><dd data-qgv="rank">'+na('',locale)+'</dd><dt>'+esc(T('재평가 신호','Re-evaluation signal'))+'</dt><dd data-qgv="reeval">'+na('',locale)+'</dd><dt>'+esc(T('다음 실적','Next earnings'))+'</dt><dd>'+nextEarnings(screens,id,locale)+'</dd></dl>'
  +'<p>'+link('#analysis/'+encodeURIComponent(id),T('기업분석 자세히 보기 →','Open company analysis →'))+'</p></section>'
  +'<section class="card" data-company-card="technical"><h2><span class="flow-number">2</span> '+esc(T('기술','Technical'))+'</h2><div id="private-history-chart"></div><dl class="kv"><dt>'+esc(T('상태·국면','State / regime'))+'</dt><dd>'+na('',locale)+'</dd></dl><p>'+link('#technical',T('기술적 분석에서 이어 보기 →','Continue in technical analysis →'))+'</p></section>'
  +'<section class="card" data-company-card="macro"><h2><span class="flow-number">3</span> '+esc(T('매크로 영향','Macro impact'))+'</h2><p>'+na(T('시장 국면·업종 영향·종목 영향이 아직 검증되지 않았습니다.','Market regime, industry and company impact are not yet validated.'),locale)+'</p><p>'+link('#macro',T('매크로 보기 →','Open macro →'))+'</p></section>'
  +'<section class="card" data-company-card="news"><h2>'+esc(T('뉴스·관계','News / relations'))+'</h2><p>'+na(T('공개 뉴스·관계망 자료가 연결되지 않았습니다.','No public news or relationship data connected.'),locale)+'</p><p>'+link('#news/'+encodeURIComponent(id),T('뉴스·관계망 화면 →','News / network screen →'))+'</p></section>'
  +'<section class="card" data-company-card="vmr"><h2>'+esc(T('가격 맥락 (VMR)','Price context (VMR)'))+'</h2><p>'+na(T('정상 범위 대비 위치는 가격이 필요합니다.','Position vs normal range needs prices.'),locale)+'</p></section>'
  +'<h2 class="section-title">'+esc(T('근거 자료','Source data'))+'</h2><div id="sec-reported-panel"></div><div id="public-qg"></div><div id="public-types"></div><div id="public-filings"></div>'+(ctx.candidateHtml||'');
}
function factorTable(screens,id,locale){
 const T=tr(locale),rec=record(screens,'sec-qg-factors.json',id),W=g.ProfileDefaults&&g.ProfileDefaults.weights;
 if(!W)return '<p>'+na('',locale)+'</p>';
 const rows=['Q','G'].flatMap(axis=>Object.keys(W[axis]).map(f=>{const v=rec&&rec.factors?rec.factors[f]:null,ok=v&&v.score!==null&&v.state!=='NOT_AVAILABLE';
  return '<tr data-factor="'+f+'"><td>'+axis+'</td><td>'+esc(factorName(f,locale))+'</td><td class="num">'+esc(num(W[axis][f],locale,0))+'%</td><td class="num" data-factor-score>'+(ok?esc(num(v.score,locale)):'—')+'</td><td><span class="badge '+esc(ok?v.state:'NOT_AVAILABLE')+'">'+esc(ok?v.state:'NOT_AVAILABLE')+'</span></td></tr>';}));
 return '<div class="table-wrap"><table data-factor-table><thead><tr><th>'+esc(T('축','Axis'))+'</th><th>'+esc(T('요소','Factor'))+'</th><th>'+esc(T('공식 가중치','Official weight'))+'</th><th>'+esc(T('점수','Score'))+'</th><th>'+esc(T('상태','State'))+'</th></tr></thead><tbody>'+rows.join('')+'</tbody></table></div>'
  +'<p class="small">'+esc(T('V 요소 7개는 가격이 필요해 ','The 7 V factors need prices: '))+na('',locale)+' · '+esc(T('근거: SEC companyfacts·submissions 공개 관측(보정 전).','Evidence: SEC companyfacts / submissions public observations (uncalibrated).'))+'</p>';
}
function panel(key,title,body,hidden){return '<section class="card analysis-panel" role="tabpanel" id="analysis-panel-'+key+'" aria-labelledby="analysis-tab-'+key+'" data-analysis-panel="'+key+'"'+(hidden?' hidden':'')+'><h2>'+esc(title)+'</h2>'+body+'</section>';}
function naRow(label,reason,locale,attr){return '<dt>'+esc(label)+'</dt><dd'+(attr?' data-na="'+attr+'"':'')+'>'+na(reason,locale)+'</dd>';}
function analysis(ctx){
 const{locale,id,screens,ticker}=ctx,T=tr(locale),rec=record(screens,'sec-qg-factors.json',id),axes=qgAxes(rec);
 const tabs='<div class="chips screen-tabs analysis-tabs" role="tablist" aria-label="'+esc(T('기업분석 탭','Analysis tabs'))+'">'+TABS.map(([k,ko,en],i)=>'<button type="button" role="tab" id="analysis-tab-'+k+'" data-analysis-tab="'+k+'" aria-controls="analysis-panel-'+k+'" aria-selected="'+(i===0)+'" tabindex="'+(i===0?0:-1)+'">'+esc(T(ko,en))+'</button>').join('')+'</div>';
 const overview=panel('summary',T('종합','Overview'),'<dl class="kv">'+naRow(T('종합 매력도','Overall attractiveness'),T('V가 가격 필요로 없어 종합하지 않습니다.','V needs prices, so no overall score is made.'),locale,'overall')
  +'<dt>'+esc(T('신뢰도','Confidence'))+'</dt><dd data-confidence>'+na('',locale)+'</dd></dl><p class="small" data-confidence-note>'+esc(T('신뢰도: 확률 아님. 데이터 충분도와 근거 일관성을 뜻합니다.','Confidence: not a probability. It means data sufficiency and evidence consistency.'))+(axes?' '+esc(T('현재 공개 요소 ','Public factors now: '))+axes.available+'/'+axes.total+'.':'')+'</p>'+qgvBody(screens,id,locale),false);
 const business=panel('business',T('사업·경쟁','Business / competition'),'<dl class="kv">'+naRow(T('사업 설명','Business description'),T('연간 보고서 출처 연결 전','Annual-report source not connected'),locale)+naRow(T('경쟁우위·열위','Strengths / weaknesses'),'',locale)+naRow(T('시장 지위','Market position'),T('요소 점수는 QGV 요소 탭','Factor score is in the QGV factors tab'),locale)+naRow(T('시장 점유율','Market share'),T('출처·추정 여부 표시 전 자료 없음','No sourced, estimate-flagged data'),locale)+naRow(T('매출 구성','Revenue mix'),'',locale)+'</dl>'+classification(screens,id,locale).replace('class="card"','class="subcard"'),true);
 const financials=panel('financials',T('재무','Financials'),'<div id="sec-reported-panel"></div><dl class="kv">'+naRow(T('재무 추이 (L03)','Financial trend (L03)'),T('공개 SEC 보고 패널만 연결됨','Only the public SEC reported panel is connected'),locale)+naRow(T('주주환원 (L06)','Shareholder returns (L06)'),'',locale)+'</dl>',true);
 const events=panel('events',T('주가·이벤트','Price / events'),'<p><a href="#company/'+encodeURIComponent(id)+'" data-chart-link>'+esc(T('요약 화면의 가격 차트 열기 →','Open the price chart on the summary →'))+'</a> · <a href="#technical">'+esc(T('기술적 분석 →','Technical analysis →'))+'</a></p><dl class="kv"><dt>E '+esc(T('실적 시기','Earnings timing'))+'</dt><dd>'+nextEarnings(screens,id,locale)+'</dd>'
  +['P '+T('제품','Product'),'L '+T('법률·규제','Legal / regulatory'),'M '+T('경영','Management'),'R '+T('재평가 신호','Re-evaluation signal'),'B·S '+T('내 거래','My trades')].map(x=>'<dt>'+esc(x)+'</dt><dd>'+na('',locale)+'</dd>').join('')+'</dl>',true);
 const factors=panel('factors',T('QGV 요소','QGV factors'),factorTable(screens,id,locale),true);
 const value=panel('value',T('가치·시나리오','Value / scenarios'),'<dl class="kv">'+naRow('DCF · '+T('역DCF','reverse DCF'),T('가격과 사용자 승인 가정 필요','Needs prices and approved assumptions'),locale)+naRow(T('안전마진','Margin of safety'),T('가격 필요','Needs prices'),locale)+naRow(T('시나리오','Scenarios'),'',locale)+'</dl>',true);
 const compare=panel('compare',T('비교·컨센서스','Compare / consensus'),'<dl class="kv">'+naRow(T('동종 비교','Peer comparison'),T('SIC→업종군 표 승인 대기','SIC group table awaits approval'),locale)+naRow(T('컨센서스','Consensus'),T('공급원 없음','No source'),locale)+'</dl>',true);
 return '<a class="parent-link" href="#company/'+encodeURIComponent(id)+'" data-analysis-back>'+esc('← '+ticker+' '+T('요약','summary'))+'</a>'+ctx.headerHtml+dataBadges(screens,locale,true)+tabs+overview+business+financials+events+factors+value+compare;
}
function wireTabs(rootEl){
 if(!rootEl)return;const tabs=[...rootEl.querySelectorAll('[data-analysis-tab]')];
 const select=key=>{for(const b of tabs){const on=b.dataset.analysisTab===key;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;}for(const p of rootEl.querySelectorAll('[data-analysis-panel]'))p.hidden=p.dataset.analysisPanel!==key;};
 tabs.forEach((b,i)=>{b.addEventListener('click',()=>select(b.dataset.analysisTab));b.addEventListener('keydown',e=>{const d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0;if(!d)return;e.preventDefault();const n=tabs[(i+d+tabs.length)%tabs.length];select(n.dataset.analysisTab);n.focus();});});
}
return Object.freeze({esc,na,fmtPct,fmtPp,num,tr,typeName,record,selectTypes,qgAxes,classification,summary,analysis,mountHolding,wireTabs,TYPES});
});
