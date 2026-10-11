/* S04 company summary and S05 company analysis (design canvas). Presentation only: no new methodology,
   weights or thresholds. Public inputs are price-free; anything that needs a price or an approval stays
   NOT_AVAILABLE. Industry (SIC group v0) and strategy theme (v0) chips come from classification-screens.js. ACTUAL is read from this device only and is never replaced by TARGET. */
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
 const CS=g.ClassificationScreens,cls=CS&&screens?screens[CS.FILE]:null,T=tr(locale),rec=record(screens,'company-types-pricefree.json',id),picked=rec&&rec.state!=='NOT_AVAILABLE'?selectTypes(rec.memberships):null;
 const items=[['industry',T('산업','Industry'),CS?CS.industryChip(cls,id,locale):na('',locale)],
  ['theme',T('전략 테마','Strategy theme'),CS?CS.themeChip(cls,id,locale):na('',locale)],
  ['type',T('투자 유형','Investment type'),picked&&picked.length?picked.map(t=>'<span class="badge LIVE" data-type-chip="'+esc(t)+'">'+esc(typeName(t,locale))+' '+esc(num(rec.memberships[t],locale,2))+'</span>').join(' ')+' <span class="small">'+esc(T('소속도 0.3 이상','membership ≥ 0.3'))+'</span>'
   :na(rec?T('소속도 0.3 이상 유형 없음 또는 자료 없음','No type with membership ≥ 0.3, or no data'):T('공개 유형 자료가 연결되지 않았습니다.','Public type data is not connected.'),locale)]];
 return '<section class="card" data-company-card="classification"><h2>'+esc(T('분류 3축','Three classification axes'))+'</h2><ul class="axis-chips">'+items.map(([k,name,body])=>'<li data-axis="'+k+'"><b>'+esc(name)+'</b> '+body+'</li>').join('')+'</ul><p class="small">'+esc(T('산업 / 전략 테마 / 투자 유형은 서로 다른 축입니다. 서로 대신 채우지 않습니다.','Industry / strategy theme / investment type are separate axes. None substitutes for another.'))+'</p></section>';
}
function dataBadges(screens,locale,withPit){
 const T=tr(locale),p=screens?.['sec-qg-factors.json'],state=p?p.state:'NOT_AVAILABLE',aged=p&&state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(p.as_of)>p.stale_after_seconds*1000;
 return '<div class="chips data-badges" data-company-badges><span class="badge '+esc(state)+'" data-badge="data">'+esc(state)+'</span>'+(aged?'<span class="badge freshness STALE">STALE</span>':'')+'<span class="badge">'+esc(p?T('기준 ','As of ')+p.as_of:T('기준 시각 없음','No as-of'))+'</span><span class="badge">'+esc(T('점수 기준 v1 · 보정 전','Score basis v1 · uncalibrated'))+'</span><span class="badge NOT_AVAILABLE">'+esc(T('시세 NOT_AVAILABLE','Price NOT_AVAILABLE'))+'</span>'+(withPit?'<span class="badge" data-badge="pit">'+esc('PIT '+(p&&p.data.availability_basis?p.data.availability_basis:'NOT_AVAILABLE'))+'</span>':'')+'</div>';
}
function nextEarnings(screens,id,locale){
 const T=tr(locale),rec=record(screens,'sec-filing-windows.json',id),s=rec&&g.PublicScreens&&g.PublicScreens.earningsStatus?g.PublicScreens.earningsStatus(rec):null;
 if(s&&s.status==='CONFIRMED')return '<span class="badge LIVE" data-earnings-status="CONFIRMED">'+esc(T('확인','Confirmed'))+'</span> <span data-next-earnings>'+esc(s.date)+'</span> <span class="small">'+esc(T('실적 발표 · SEC 8-K Item 2.02','Earnings release · SEC 8-K Item 2.02'))+'</span>';
 const w=s&&s.status==='ESTIMATED'?s.window:null;
 if(!w)return na(T('공시 시기 패턴 자료 없음','No filing-timing pattern'),locale);
 return '<span class="badge" data-earnings-status="ESTIMATED">'+esc(T('추정','Estimated'))+'</span> <span data-next-earnings>'+esc(w.form+' '+w.start+'–'+w.end+' · D-'+w.days_until_start)+'</span> <span class="small">'+esc(T('예상 시기 · 확정일 아님','Estimated timing · not a confirmed date'))+'</span>';
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
  +'<section class="card" data-company-card="value"><h2>'+esc(T('가치 (이 기기)','Value (this device)'))+'</h2><div id="company-value" data-company-value>'+valueHtml({locale,compact:true})+'</div><p>'+link('#analysis/'+encodeURIComponent(id),T('가치·시나리오 자세히 →','Value / scenarios details →'))+'</p></section>'
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
 const value=panel('value',T('가치·시나리오','Value / scenarios'),'<div id="company-value" data-company-value>'+valueHtml({locale})+'</div>',true);
 const compare=panel('compare',T('비교·컨센서스','Compare / consensus'),'<dl class="kv">'+naRow(T('동종 비교','Peer comparison'),T('업종군 v0 연결됨 · 동종 비교 기준 미정','Industry group v0 connected · peer-comparison basis undefined'),locale)+naRow(T('컨센서스','Consensus'),T('공급원 없음','No source'),locale)+'</dl>',true);
 return '<a class="parent-link" href="#company/'+encodeURIComponent(id)+'" data-analysis-back>'+esc('← '+ticker+' '+T('요약','summary'))+'</a>'+ctx.headerHtml+dataBadges(screens,locale,true)+tabs+overview+business+financials+events+factors+value+compare;
}
// Value view (v1+dcf_v1_1_default). Public FCFE and the forward DCF are price-free; the price is this device's own quote, used in RAM only.
const V_LABEL={fundamental_value:['핵심 가치','Fundamental value'],peer_relative_value:['동종 상대가치','Peer-relative value'],historical_valuation:['과거 밸류에이션','Historical valuation'],sector_context:['업종 맥락','Sector context'],theme_premium_discount:['테마 프리미엄·할인','Theme premium / discount'],reverse_dcf:['역DCF','Reverse DCF'],margin_of_safety:['안전마진','Margin of safety']};
const QUOTE_SOURCE={MANUAL:['기기 수동 시세','Device manual quote'],API:['기기 API 시세','Device API quote'],GOOGLEFINANCE:['기기 Google 시트 시세','Device Google Sheet quote'],PRIVATE_HISTORY_CLOSE:['비공개 일별 이력 종가','Private daily history close']};
const COMPONENT_LABEL={long_term_debt_issuance:['장기차입 발행','Long-term debt issuance'],long_term_debt_repayment:['장기차입 상환','Long-term debt repayment'],net_short_term_borrowing:['단기차입 순증감','Net short-term borrowing']};
const DCF_DEFAULTS={V1_1_UNCALIBRATED_DEFAULT:['v1.1 UNCALIBRATED 기본값','v1.1 UNCALIBRATED default','v1+dcf_v1_1_default'],V1_UNCALIBRATED_DEFAULT:['v1 UNCALIBRATED 기본값','v1 UNCALIBRATED default','v1+dcf_v1_default']};
function accnText(a){return typeof a==='string'&&/^\d{18}$/.test(a)?a.slice(0,10)+'-'+a.slice(10,12)+'-'+a.slice(12):'—';}
function valueHtml({locale,row=null,result=null,quote=null,compact=false,params=g.DeviceValuation?g.DeviceValuation.parameters():null}){
 const T=tr(locale),en=locale==='en-US'?1:0,reasons=list=>(list||[]).join(' · '),pct=v=>typeof v==='number'&&Number.isFinite(v)?(v<0?'−':'')+num(Math.abs(v)*100,locale)+'%':'—';
 const p=params&&typeof params==='object'?params:null,preset=p&&Object.hasOwn(DCF_DEFAULTS,p.status)?DCF_DEFAULTS[p.status]:null,rule=p&&p.explicit_growth_rule&&typeof p.explicit_growth_rule==='object'?p.explicit_growth_rule:null;
 const badges='<p class="chips data-badges"><span class="badge" data-dcf-badge>'+esc(preset?preset[en]+T(' · 나중에 수정 가능',' · editable later'):T('사용자 설정 · 보정 전','Custom · uncalibrated'))+'</span><span class="badge" data-dcf-version>'+esc(result?result.version:(preset?preset[2]:'v1+dcf_custom'))+'</span></p>';
 const ruleText=rule?T(' · 명시기간 성장률 h = 자사 3년 매출 CAGR, ',' · explicit growth h = own 3-year revenue CAGR clamped to ')+pct(rule.lower)+'~'+pct(rule.upper)+T(' 범위로 제한 (PROVISIONAL)',' (PROVISIONAL)'):T(' · 명시기간 성장률 h 미결정',' · explicit growth h undecided');
 const paramLine=p?'<p class="small" data-dcf-params>'+esc(T('기본값(나중에 수정 가능): 명시 ','Defaults (editable later): explicit '))+esc(String(p.explicit_years))+esc(T('년 · 할인율 ','y · discount rate '))+esc(pct(p.discount_rate))+esc(T(' · 영구성장 ',' · terminal growth '))+esc(pct(p.terminal_growth))+esc(T(' · 역DCF 탐색 ',' · reverse-DCF bracket '))+esc(pct(p.solver&&p.solver.growth_lower))+'~'+esc((p.solver&&p.solver.growth_upper>0?'+':'')+pct(p.solver&&p.solver.growth_upper))+esc(ruleText)+'</p>':'<p>'+na('DCF_PARAMETERS_UNAVAILABLE',locale)+'</p>';
 const f=row&&row.fcfe?row.fcfe:null,fcfeOk=f&&f.state!=='NOT_AVAILABLE',gaap={'us-gaap':'US GAAP','ifrs-full':'IFRS'}[f&&f.taxonomy]||null;
 const fcfe=fcfeOk?'<span class="num">'+esc(f.currency+' '+num(f.fcfe_per_share,locale,2))+'</span> <span class="small">'+esc(T('회계연도 종료 ','FY end ')+f.fiscal_period_end+' · '+f.form+(gaap?' · '+gaap:'')+' · accn '+accnText(f.accn))+'</span> <span class="badge '+esc(f.state)+'">'+esc(f.state)+'</span>'
  :na(f?reasons(f.reason_codes):T('공개 SEC 가치 입력이 없습니다','No public SEC valuation input'),locale);
 const zero=f&&f.components?Object.keys(COMPONENT_LABEL).filter(k=>f.components[k]&&f.components[k].assumed_zero===true):[];
 const zeroRow=zero.length?'<dt>'+esc(T('미보고 항목','Unreported lines'))+'</dt><dd data-value="assumed-zero"><span class="badge">'+esc(T('미보고 → 0 가정','Not reported → assumed 0'))+'</span> <span class="small">'+esc(zero.map(k=>COMPONENT_LABEL[k][en]).join(' · ')+' (NOT_REPORTED_ASSUMED_ZERO)')+'</span></dd>':'';
 const partial=f&&f.components?Object.keys(COMPONENT_LABEL).filter(k=>f.components[k]&&f.components[k].reason==='BORROWING_PAIR_PARTIAL'):[];
 const partialRow=partial.length?'<dt>'+esc(T('한쪽만 보고된 차입 쌍','Half-reported borrowing pair'))+'</dt><dd data-value="pair-partial"><span class="badge">'+esc(T('미보고 쪽 → 0 가정','Unreported side → assumed 0'))+'</span> <span class="small">'+esc(partial.map(k=>COMPONENT_LABEL[k][en]+': '+f.components[k].concepts.join(', ')).join(' · ')+' (BORROWING_PAIR_PARTIAL)')+'</span></dd>':'';
 const basis=p&&typeof p.currency==='string'?p.currency:null,qc=quote&&typeof quote.currency==='string'?quote.currency:null,cc=f&&typeof f.currency==='string'?f.currency:null;
 const ccyMismatch=cc&&(basis&&cc!==basis||qc&&cc!==qc);
 const ccyRow=ccyMismatch?'<dt>'+esc(T('통화','Currency'))+'</dt><dd data-value="currency-basis">'+na('CURRENCY_BASIS_UNCONFIRMED',locale)+' <span class="small">'+esc(T('보고 통화 ','Reported currency ')+cc+(qc&&qc!==cc?T(' · 가격 통화 ',' · price currency ')+qc:'')+(basis&&basis!==cc?T(' · 기준 통화 ',' · basis currency ')+basis:'')+T(' · 환율 변환 없음',' · no FX conversion'))+'</span></dd>':'';
 const q=quote?'<span data-value-quote-source="'+esc(quote.source||'')+'">'+esc((QUOTE_SOURCE[quote.source]||['기기 시세','Device quote'])[en])+'</span> <span class="small">'+esc((quote.as_of||'—')+(quote.stale?' · STALE':'')+' · '+T('RAM 전용 · 저장·전송 안 함','RAM only · not stored or sent'))+'</span>'
  :na(T('이 기기에 이 종목 시세가 없습니다 (NO_DEVICE_PRICE)','No device quote for this company (NO_DEVICE_PRICE)'),locale);
 const rev=result&&result.reverse_dcf.state!=='NOT_AVAILABLE'?'<span class="num" data-implied-growth>'+esc(pct(result.reverse_dcf.implied_growth))+'</span> <span class="small">'+esc(T('현재 기기 가격이 함의하는 명시 '+(p?p.explicit_years:'—')+'년 연 FCFE 성장률','Annual FCFE growth over the explicit '+(p?p.explicit_years:'—')+' years implied by the device price'))+'</span>'
  :na(result?reasons(result.reverse_dcf.reason_codes):'NO_DEVICE_PRICE',locale);
 const eg=result&&result.explicit_growth?result.explicit_growth:null;
 const growth=eg&&eg.state!=='NOT_AVAILABLE'?'<span class="num" data-explicit-growth>'+esc(pct(eg.value))+'</span> <span class="small">'+esc(T('3년 매출 CAGR ','3-year revenue CAGR ')+pct(eg.revenue_cagr_3y)+(eg.clamped?T(' → 범위 제한 적용',' → clamped'):'')+' · PROVISIONAL')+'</span>'
  :na(eg?reasons(eg.reason_codes):(rule?'EXPLICIT_GROWTH_NOT_AVAILABLE':'EXPLICIT_GROWTH_UNDECIDED'),locale);
 const d=result?result.dcf:null;
 const dcf=d&&d.state!=='NOT_AVAILABLE'?'<span class="num" data-dcf-value>'+esc((f&&f.currency?f.currency+' ':'')+num(d.value_per_share,locale,2))+'</span> <span class="small">'+esc(T('주당 · FCFE/주 기준 · 가격 미사용','per share · FCFE per share · no price used'))+'</span> <span class="badge">'+esc(d.state)+'</span>'
  :na(d?reasons(d.reason_codes):'FCFE_NOT_AVAILABLE',locale);
 const m=result?result.v_factors.margin_of_safety:null;
 const mos=m&&m.state!=='NOT_AVAILABLE'?'<span class="num" data-mos-score>'+esc(num(m.score,locale))+'</span> <span class="small">'+esc(T('점수 · 보수가치 0.75×DCF 내재가치 vs 기기 가격 (승인 v1 매핑)','score · conservative value 0.75×DCF value vs device price (approved v1 mapping)'))+'</span>'
  :na(m?m.reason:'DCF_NOT_AVAILABLE',locale);
 let html=badges+paramLine+'<dl class="kv"><dt>'+esc(T('FCFE/주 (공개 SEC)','FCFE / share (public SEC)'))+'</dt><dd data-value="fcfe">'+fcfe+'</dd>'+zeroRow+partialRow+ccyRow
  +'<dt>'+esc(T('가격','Price'))+'</dt><dd data-value="quote">'+q+'</dd>'
  +'<dt>'+esc(T('역DCF 내재 성장률','Reverse-DCF implied growth'))+'</dt><dd data-value="reverse">'+rev+'</dd>'
  +'<dt>'+esc(T('명시기간 성장률 h','Explicit growth h'))+'</dt><dd data-value="growth">'+growth+'</dd>'
  +'<dt>'+esc(T('DCF 내재가치','DCF intrinsic value'))+'</dt><dd data-value="dcf">'+dcf+'</dd>'
  +'<dt>'+esc(T('안전마진','Margin of safety'))+'</dt><dd data-value="mos">'+mos+'</dd>'
  +(compact?'':'<dt>'+esc(T('시나리오','Scenarios'))+'</dt><dd data-value="scenarios">'+na('',locale)+'</dd>')+'</dl>';
 if(!compact){
  const rows=Object.keys(V_LABEL).map(k=>{const x=result?result.v_factors[k]:{score:null,state:'NOT_AVAILABLE',reason:k==='margin_of_safety'?'DCF_NOT_AVAILABLE':'NO_DEVICE_PRICE'},ok=x.state!=='NOT_AVAILABLE';
   return '<tr data-v-factor="'+k+'"><td>'+esc(V_LABEL[k][en])+'</td><td class="num" data-v-score>'+(ok?esc(num(x.score,locale)):'—')+'</td><td><span class="badge '+esc(ok?'LIVE':'NOT_AVAILABLE')+'">'+esc(x.state)+'</span></td><td class="small">'+esc(x.reason)+'</td></tr>';});
  html+='<h3>'+esc(T('V 요소 (이 기기 계산 · 보정 전)','V factors (computed on this device · uncalibrated)'))+'</h3><div class="table-wrap"><table data-v-table><thead><tr><th>'+esc(T('요소','Factor'))+'</th><th>'+esc(T('점수','Score'))+'</th><th>'+esc(T('상태','State'))+'</th><th>'+esc(T('사유','Reason'))+'</th></tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
 }
 return html+'<p class="small" data-value-note>'+esc(T('FCFE = 영업현금흐름 − 설비투자 + 순차입, 희석주식수 기준(같은 회계연도·통화·공시). 공시에 없는 차입 항목은 0으로 가정해 표시하고, 핵심 항목(영업현금흐름·설비투자·희석주식수)은 0으로 채우지 않습니다. 통화 변환은 하지 않습니다. 가격은 이 기기 RAM에서만 쓰며 저장·전송하지 않습니다. V 종합 점수는 만들지 않습니다.','FCFE = operating cash flow − capital expenditure + net borrowing, per diluted share (same fiscal year, currency and filing). Borrowing lines the filing does not report are shown as assumed 0; core lines (operating cash flow, capex, diluted shares) are never zero-filled. No currency conversion. The price is used only in this device’s RAM and is never stored or sent. No overall V score is made.'))+'</p>';
}
async function mountValue(host,{locale,id,ticker=null,catalogPromise=null,inputsPromise=null,quote=null,compact=false,win=g}){
 if(!host)return;const V=win.DeviceValuation;if(!V)return;const token=host.__valueToken=(host.__valueToken||0)+1;
 let payload=null;try{payload=await inputsPromise;}catch(_){}
 let q=quote&&typeof quote.price==='number'&&Number.isFinite(quote.price)&&quote.price>0?quote:null;
 if(!q&&ticker&&catalogPromise){let catalog=null;try{catalog=await catalogPromise;}catch(_){}if(catalog)q=await V.deviceQuote(win,catalog,ticker);}
 if(!host.isConnected||host.__valueToken!==token)return;
 const row=V.row(payload,id),result=V.view({row,quote:q?{price:q.price,currency:q.currency}:null});
 host.innerHTML=valueHtml({locale,row,result,quote:q?{source:q.source,as_of:q.as_of,stale:q.stale===true,currency:q.currency}:null,compact});
}
function wireTabs(rootEl){
 if(!rootEl)return;const tabs=[...rootEl.querySelectorAll('[data-analysis-tab]')];
 const select=key=>{for(const b of tabs){const on=b.dataset.analysisTab===key;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;}for(const p of rootEl.querySelectorAll('[data-analysis-panel]'))p.hidden=p.dataset.analysisPanel!==key;};
 tabs.forEach((b,i)=>{b.addEventListener('click',()=>select(b.dataset.analysisTab));b.addEventListener('keydown',e=>{const d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0;if(!d)return;e.preventDefault();const n=tabs[(i+d+tabs.length)%tabs.length];select(n.dataset.analysisTab);n.focus();});});
}
return Object.freeze({esc,na,fmtPct,fmtPp,num,tr,typeName,record,selectTypes,qgAxes,classification,summary,analysis,mountHolding,mountValue,valueHtml,wireTabs,TYPES});
});
