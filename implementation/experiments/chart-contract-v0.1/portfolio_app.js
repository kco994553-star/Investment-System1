// Render pre-aggregated portfolio exposures; no classification or allocation engine.
(()=>{
 const root=document.querySelector('#portfolio-charts');
 const requestedLocale=new URLSearchParams(location.search).get('lang');
 if(['ko','en'].includes(requestedLocale))document.documentElement.lang=requestedLocale;
 const copy=(ko,en)=>document.documentElement.lang==='en'?en:ko;
 const palette=['#60c7b2','#7fa8ff','#d9ad72','#cd94d9','#8abac8','#b2c779','#c68779','#ab9aea'];
 const neutral='#435269',cashColor='#778ba2';const ns='http://www.w3.org/2000/svg';
 const el=(name,text,cls)=>{const e=document.createElement(name);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const svg=(name,attrs={})=>{const e=document.createElementNS(ns,name);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;};
 const pct=(n,total)=>`${new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(100*n/total)}%`;
 const exact=(n,total)=>`${n}/${total} 단위`;
 function donut(parts,total,label,description=label){
  const wrapper=el('div',undefined,'pf-donut');const chart=svg('svg',{viewBox:'0 0 200 200',role:'img','aria-label':description,'data-denominator':total,'data-unit':'weight_units'});
  const title=svg('title');title.textContent=description;chart.append(title);
  const radius=72;const circumference=2*Math.PI*radius;let offset=0;
  for(const part of parts){if(part.units===0)continue;const len=circumference*part.units/total;
   const segment=svg('circle',{cx:100,cy:100,r:radius,fill:'none',stroke:part.color,'stroke-width':24,'stroke-dasharray':`${len} ${circumference-len}`,'stroke-dashoffset':-offset,transform:'rotate(-90 100 100)'});
   const info=svg('title');info.textContent=`${part.label}: ${pct(part.units,total)} (${exact(part.units,total)})`;segment.append(info);chart.append(segment);offset+=len;
  }
  const center=svg('text',{x:100,y:105,'text-anchor':'middle',fill:'#e5ecf7','font-size':18});center.textContent=label;chart.append(center);wrapper.append(chart);
  const legend=el('ul');for(const part of parts){const li=el('li',`${part.label} ${pct(part.units,total)} · ${exact(part.units,total)}`);li.style.borderLeft=`4px solid ${part.color}`;legend.append(li);}wrapper.append(legend);return wrapper;
 }
 function section(title,dimension,availability='AVAILABLE'){
  const card=el('section',undefined,'pf-card');card.append(el('h3',title));
  if(dimension){card.dataset.dimension=dimension;card.dataset.availability=availability;card.setAttribute('aria-label',`${title} · ${availability}`);}return card;
 }
 function unavailable(title,dimension,reason){const card=section(title,dimension,'NOT_AVAILABLE');card.append(el('p',`NOT_AVAILABLE · ${reason}`,'pf-warning'));return card;}
 const unitValue=n=>Number.isSafeInteger(n)&&n>=0;
 const partition=(rows,total)=>Array.isArray(rows)&&rows.every(r=>r&&unitValue(r.units))&&rows.reduce((n,r)=>n+r.units,0)===total;
 function validUserSource(d){
  // Exact serialized identity covers rows, supplied Theme units, metadata and pre-aggregates.
  // No classification/allocation is recomputed here. The build snapshot is local display evidence.
  const expected=window.TARGET_V0_REFERENCE_CANONICAL;
  try{return typeof expected==='string'&&JSON.stringify(d)===expected;}catch{return false;}
 }
 function validProjection(d,key){
  // Selected mode defines the allowed source; payload flags cannot relabel another lane.
  const expectedState=key==='reference'?'REFERENCE':key==='demo'?'DEMO':null;
  if(!d||!expectedState||d.weight_basis!=='TARGET'||d.data_state!==expectedState||d.data_kind!==(key==='reference'?'USER_SPEC_REFERENCE':'SYNTHETIC_FIXTURE'))return false;
  if(key==='reference'&&!validUserSource(d))return false;
  if(key==='demo'&&Object.hasOwn(d,'source_metadata'))return false;
  const total=d.total_units;if(!unitValue(total)||total===0||!unitValue(d.cash_units)||d.cash_units>total)return false;
  if(!Array.isArray(d.holdings)||!d.holdings.every(h=>h&&unitValue(h.weight_units)&&(h.types===null||Array.isArray(h.types)))||d.holdings.reduce((n,h)=>n+h.weight_units,d.cash_units)!==total)return false;
  if(d.industry?.denominator_units!==total||!partition(d.industry.buckets,total)||d.overlap?.denominator_units!==total||!partition(d.overlap.buckets,total))return false;
  if(!d.industry.buckets.every(b=>['INDUSTRY','UNKNOWN','CASH'].includes(b.kind)&&typeof b.label==='string'))return false;
  if(!d.overlap.buckets.every(b=>['MEMBERSHIP','NO_TYPES','UNKNOWN','CASH'].includes(b.kind)&&Array.isArray(b.types)&&b.types.every(t=>typeof t==='string')&&(b.kind==='MEMBERSHIP'?b.types.length>0:b.types.length===0)))return false;
  if(d.types?.denominator_units!==total||!Array.isArray(d.types.exposures)||!d.types.exposures.every(e=>e&&typeof e.type==='string'&&['member_units','non_member_units','unknown_units','cash_units'].every(k=>unitValue(e[k]))&&e.member_units+e.non_member_units+e.unknown_units+e.cash_units===total))return false;
  return typeof d.as_of==='string'&&typeof d.source==='string'&&typeof d.portfolio_version==='string';
 }
 const missingExposure=e=>e.unknown_units>0&&e.member_units===0&&e.non_member_units===0;
 const exposureText=(e,total)=>missingExposure(e)?`${e.type} NOT_AVAILABLE · 미분류`:`${e.type} ${pct(e.member_units,total)}${e.unknown_units>0?' 하한(최소)':''}`;
 function render(key){
  window.__portfolioLab={doc:null,mode:null,render};
  document.querySelector('#portfolio-heading').textContent=key==='demo'?'Portfolio · DEMO · SAMPLE':key==='actual'?'ACTUAL · NOT_AVAILABLE':'TARGET v0 · USER';
  document.querySelector('#portfolio-source-tag').textContent=key==='demo'?'SAMPLE · SYNTHETIC_FIXTURE':key==='actual'?'ACTUAL source · NOT_AVAILABLE':'USER source · TARGET';
  document.querySelector('#portfolio').setAttribute('aria-label',key==='demo'?'SAMPLE Portfolio DEMO':key==='actual'?'ACTUAL NOT_AVAILABLE':'TARGET v0 USER');
  root.replaceChildren();root.dataset.mode=key;root.dataset.basis=key==='actual'?'ACTUAL':'TARGET';
  for(const mode of ['reference','demo','actual'])document.querySelector(`#portfolio-${mode}`).setAttribute('aria-pressed',String(mode===key));
  const meta=el('p',undefined,'pf-meta');meta.id='portfolio-meta';root.append(meta);
  if(key==='actual'){
   root.dataset.state='NOT_AVAILABLE';document.querySelector('#portfolio-state').textContent='ACTUAL · NOT_AVAILABLE · '+copy('실제 계좌 자료 미제공','actual account source not supplied');
   meta.textContent='ACTUAL · source / as_of / effective_at / available_at: NOT_AVAILABLE · unit: weight_units · denominator total_units: NOT_AVAILABLE · '+copy('TARGET 대체 없음','no TARGET replacement');
   for(const [dimension,title]of [['GICS','GICS'],['STRATEGY_THEME','Strategy Theme / Portfolio Bucket'],['INVESTMENT_TYPE','Investment Type'],['TYPE_OVERLAP','Type Overlap']])root.append(unavailable(title,dimension,copy('ACTUAL 원본·분모가 없어 표시할 수 없습니다. TARGET 자료로 대체하지 않습니다.','ACTUAL source and denominator are unavailable. TARGET values are never substituted.')));
   window.__portfolioLab={doc:null,mode:'actual',render};return;
  }
  const d=window.PORTFOLIO_CHARTS?.[key];
  if(!validProjection(d,key)){root.dataset.state='BLOCKED';document.querySelector('#portfolio-heading').textContent='Portfolio · BLOCKED';document.querySelector('#portfolio-source-tag').textContent='BLOCKED · source validation failed';document.querySelector('#portfolio').setAttribute('aria-label','Portfolio BLOCKED');document.querySelector('#portfolio-state').textContent='BLOCKED · '+copy('표시 가능한 자료 없음','no displayable source');meta.textContent='BLOCKED · source / as_of / unit / denominator: NOT_AVAILABLE';window.__portfolioLab={doc:null,mode:null,render};root.append(el('p','BLOCKED · '+copy('누락된 값은 0으로 대체하지 않습니다.','Missing values are not replaced with zero.')));return;}
  const total=d.total_units;const isReference=d.data_state==='REFERENCE';
  root.dataset.state=d.data_state;
  const source=d.source_metadata;
  document.querySelector('#portfolio-state').textContent=isReference&&source?'TARGET v0 · USER · REFERENCE · '+copy('사용자 채택 목표 · 실제 계좌 아님','user-adopted target · no actual account'):d.data_state==='REFERENCE'?'SAMPLE · REFERENCE · TARGET · 기존 목표비중 참고자료 · 실제 계좌 아님':'SAMPLE · DEMO · TARGET · 가상 기업·비중·유형 · 투자 추천 아님';
  if(isReference&&source){
   meta.style.overflowWrap='anywhere';
   meta.textContent=`TARGET ${source.version} · USER · ${source.source_path} · SHA256 ${source.source_sha256} · adopted_at: ${source.declared_clocks.adopted_at} = ${source.adopted_at_utc} · effective_at: ${source.declared_clocks.effective_at} = ${source.effective_at_utc} · available_at: ${source.declared_clocks.available_at} = ${source.available_at_utc} · ${copy('기록된 관측·추출 stamp','recorded observation/extraction stamp')}: ${d.as_of} · ${copy('Security 매핑','Security mapping')}: ${source.mapping.admitted}/${source.mapping.total} · ${copy('미확정','unresolved')} ${source.mapping.unresolved} · unit: weight_units · denominator: ${total} · cash: ${d.cash_units} · ${copy('소급 적용 없음 · 역사 PIT 미인증','no backdating · historical PIT NOT_VERIFIED')} · QGV: ${d.qgv_version}`;
  }else meta.textContent=`${d.portfolio_version} · basis: ${d.weight_basis} · source: ${d.source} · as_of 관측·추출 stamp (UTC): ${d.as_of} — 권위 있는 효력 시점 아님 · effective_at: ${d.effective_at??'NOT_AVAILABLE (미제공)'} · available_at (Portfolio): ${d.available_at??'NOT_AVAILABLE (미제공)'} · classification.available_at: ${d.classification?.available_at??'NOT_AVAILABLE (미제공)'} · unit: weight_units (제공된 정수 단위), 표시 % · denominator total_units: ${total} (현금 ${d.cash_units} 단위 및 미분류 포함) · PIT NOT_VERIFIED`;
  root.append(unavailable('GICS','GICS','GICS 기업별 배정 및 근거가 제공되지 않았습니다. 사용자 배분 그룹이나 가상 산업을 GICS로 대체하지 않습니다.'));
  const industry=section(isReference?'Strategy Theme / Portfolio Bucket':'보조 예시 · 가상 산업 분류 (GICS 아님)',isReference?'STRATEGY_THEME':null);
  industry.append(el('p',isReference?copy('사용자가 정한 4개 TARGET 목표 배분 그룹입니다. Strategy Theme / Portfolio Bucket이며 표준 산업분류(GICS)가 아닙니다.','Four user-defined TARGET groups: Strategy Theme / Portfolio Bucket. GICS assignments are NOT_AVAILABLE.'):'명시적으로 제공된 가상 산업 분류입니다. Strategy Theme나 GICS 배정이 아닙니다. 현금과 미분류도 전체 분모에 포함합니다.'));
  industry.append(donut(d.industry.buckets.map((b,i)=>({label:b.kind==='CASH'?'현금':b.kind==='UNKNOWN'?(isReference?'Theme 미분류':'가상 산업 미분류'):b.label,units:b.units,color:b.kind==='UNKNOWN'?neutral:b.kind==='CASH'?cashColor:palette[i%palette.length]})),total,'전체 100%',`${isReference?'TARGET Strategy Theme':'SAMPLE 가상 산업'} · 전체 ${total} weight_units · 현금 및 미분류 포함`));
  if(!isReference){root.append(unavailable('Strategy Theme / Portfolio Bucket','STRATEGY_THEME','이 가상 fixture에는 Strategy Theme 배정이 없습니다. 가상 산업을 Theme로 재해석하지 않습니다.'));industry.dataset.auxiliary='FICTIONAL_INDUSTRY';}
  root.append(industry);
  const allUnknown=d.types.exposures.length===0||d.types.exposures.every(missingExposure);
  const partial=d.types.exposures.some(e=>e.unknown_units>0);
  const types=section('Investment Type · 유형 구성','INVESTMENT_TYPE',allUnknown?'NOT_AVAILABLE':partial?'PARTIAL':'AVAILABLE');types.append(el('p','각 도넛의 분모는 동일한 전체 포트폴리오입니다. 한 종목이 여러 유형에 포함될 수 있어 유형별 노출 합계는 100%를 넘을 수 있습니다. 미분류는 해당 없음으로 간주하지 않습니다.'));
  if(allUnknown)types.append(el('p',d.types.exposures.length===0?'NOT_AVAILABLE · 제공된 Investment Type catalog가 비어 있어 유형 노출을 표시할 수 없습니다.':'NOT_AVAILABLE · 기업별 유형 배정 근거가 없어 전부 미분류입니다. 가상 예시를 선택하면 중복 유형 표시를 확인할 수 있습니다.','pf-warning'));
  types.append(el('p','확인된 유형 노출: '+d.types.exposures.map(e=>exposureText(e,total)).join(' / ')));
  if(partial&&!allUnknown)types.append(el('p','PARTIAL · 확인된 해당 유형 비중은 하한입니다. 미분류 범위를 별도로 표시하며, 알려진 부분만 100%로 재정규화하지 않습니다.','pf-warning'));
  const rings=el('div',undefined,'pf-type-grid');
  for(const [i,e] of d.types.exposures.entries()){
   const card=el('div');card.dataset.type=e.type;card.dataset.availability=missingExposure(e)?'NOT_AVAILABLE':e.unknown_units>0?'PARTIAL':'AVAILABLE';card.dataset.memberUnits=e.member_units;card.dataset.unknownUnits=e.unknown_units;card.append(el('h4',e.type));
   if(missingExposure(e))card.append(el('p',`NOT_AVAILABLE · 미분류 · 알려진 유형 비중 없음 · 미분류 범위 ${pct(e.unknown_units,total)} (${exact(e.unknown_units,total)}) · 현금 ${pct(e.cash_units,total)} (${exact(e.cash_units,total)})`,'pf-warning'));
   else{
    card.append(el('p',`확인된 해당 유형 ${e.unknown_units>0?'하한(최소) ':''}${pct(e.member_units,total)} · 미분류 범위 ${pct(e.unknown_units,total)} (${exact(e.unknown_units,total)})`));
    card.append(donut([{label:'확인된 해당 유형'+(e.unknown_units>0?' (하한)':''),units:e.member_units,color:palette[i%palette.length]},{label:'확인된 비해당',units:e.non_member_units,color:'#253247'},{label:'유형 미분류',units:e.unknown_units,color:neutral},{label:'현금',units:e.cash_units,color:cashColor}],total,pct(e.member_units,total)+(e.unknown_units>0?' 하한':''),`${e.type} · 확인된 해당 유형 ${pct(e.member_units,total)}${e.unknown_units>0?' 하한':''} · 분모 ${total} weight_units`));
   }rings.append(card);
  }
  types.append(rings);root.append(types);
  const unknownOverlap=d.overlap.buckets.filter(b=>b.kind==='UNKNOWN').reduce((n,b)=>n+b.units,0);
  const allOverlapUnknown=unknownOverlap>0&&unknownOverlap+d.cash_units===total;
  const overlap=section('Type Overlap · 유형 중복 조합','TYPE_OVERLAP',allOverlapUnknown?'NOT_AVAILABLE':unknownOverlap>0?'PARTIAL':'AVAILABLE');overlap.append(el('p','Investment Type의 완전히 확인된 동일 유형 조합에서 파생합니다. 정확히 같은 유형 조합을 가진 보유분끼리 묶습니다. “성장 + 우량”은 그 두 유형 조합이며, 다른 유형까지 포함한 종목은 별도 조합입니다. 현금·미분류를 포함해 각 보유분은 한 번만 집계합니다. 유형별 노출 합계와 달리 조합 분할의 분모는 전체 100%입니다. 미분류는 빈 유형 조합이 아닙니다.'));
  const list=el('div',undefined,'pf-overlap');
  if(allOverlapUnknown)overlap.append(el('p','NOT_AVAILABLE · 유형 조합 미분류 · 원본 유형 배정이 없어 확인된 조합을 표시할 수 없습니다.','pf-warning'));
  else for(const [i,b] of d.overlap.buckets.entries()){
   const label=b.kind==='CASH'?'현금':b.kind==='UNKNOWN'?'유형 미분류':b.kind==='NO_TYPES'?'명시적으로 유형 없음':b.types.map(t=>`[${t}]`).join(' + ');
   const row=el('div',undefined,'pf-overlap-row');row.append(el('span',label));const track=el('div',undefined,'pf-bar-track');const bar=el('div',undefined,'pf-bar');bar.style.width=`${100*b.units/total}%`;bar.style.background=b.kind==='UNKNOWN'?neutral:palette[i%palette.length];track.append(bar);row.append(track,el('span',`${pct(b.units,total)} · ${exact(b.units,total)}`));list.append(row);
  }
  overlap.append(list);root.append(overlap);
  const details=el('details');details.append(el('summary','보유분별 원본 입력과 분류 확인'));
  const scroll=el('div',undefined,'scroll');const table=el('table');const thead=el('thead');const tr=el('tr');const headings=['보유분','TARGET 비중',isReference?'Strategy Theme / Portfolio Bucket':'가상 산업 (GICS 아님)','Investment Type'];if(source)headings.push('ticker_hint','listing','weight_units');for(const s of headings)tr.append(el('th',s));thead.append(tr);table.append(thead);const tbody=el('tbody');
  const suppliedRows=new Map((source?.source_rows||[]).map(r=>[r.source_pointer,r]));
  for(const h of d.holdings){const row=el('tr');const values=[h.label,pct(h.weight_units,total),h.industry??'미분류',h.types===null?'미분류':h.types.length?h.types.join(' + '):'명시적으로 없음'];if(source){const supplied=suppliedRows.get(h.holding_id);values.push(supplied.ticker_hint,supplied.listing,String(supplied.weight_units));}for(const v of values)row.append(el('td',v));tbody.append(row);}table.append(tbody);scroll.append(table);details.append(scroll);root.append(details);
  const evidence=el('details');evidence.append(el('summary','계약 및 출처'));const pre=el('pre',JSON.stringify(d,null,2));evidence.append(pre);root.append(evidence);
  window.__portfolioLab={doc:d,mode:key,render};
 }
 document.querySelector('#portfolio-reference').onclick=()=>render('reference');document.querySelector('#portfolio-demo').onclick=()=>render('demo');document.querySelector('#portfolio-actual').onclick=()=>render('actual');render('reference');
})();
