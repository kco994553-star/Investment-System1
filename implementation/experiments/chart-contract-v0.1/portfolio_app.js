// Render pre-aggregated portfolio exposures; no classification or allocation engine.
(()=>{
 const root=document.querySelector('#portfolio-charts');
 const palette=['#60c7b2','#7fa8ff','#d9ad72','#cd94d9','#8abac8','#b2c779','#c68779','#ab9aea'];
 const neutral='#435269',cashColor='#778ba2';const ns='http://www.w3.org/2000/svg';
 const el=(name,text,cls)=>{const e=document.createElement(name);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const svg=(name,attrs={})=>{const e=document.createElementNS(ns,name);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;};
 const pct=(n,total)=>`${new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2}).format(100*n/total)}%`;
 const exact=(n,total)=>`${n}/${total} 단위`;
 function donut(parts,total,label){
  const wrapper=el('div',undefined,'pf-donut');const chart=svg('svg',{viewBox:'0 0 200 200',role:'img','aria-label':label});
  const title=svg('title');title.textContent=label;chart.append(title);
  const radius=72;const circumference=2*Math.PI*radius;let offset=0;
  for(const part of parts){if(!part.units)continue;const len=circumference*part.units/total;
   const segment=svg('circle',{cx:100,cy:100,r:radius,fill:'none',stroke:part.color,'stroke-width':24,'stroke-dasharray':`${len} ${circumference-len}`,'stroke-dashoffset':-offset,transform:'rotate(-90 100 100)'});
   const info=svg('title');info.textContent=`${part.label}: ${pct(part.units,total)} (${exact(part.units,total)})`;segment.append(info);chart.append(segment);offset+=len;
  }
  const center=svg('text',{x:100,y:105,'text-anchor':'middle',fill:'#e5ecf7','font-size':18});center.textContent=label;chart.append(center);wrapper.append(chart);
  const legend=el('ul');for(const part of parts){const li=el('li',`${part.label} ${pct(part.units,total)}`);li.style.borderLeft=`4px solid ${part.color}`;li.title=exact(part.units,total);legend.append(li);}wrapper.append(legend);return wrapper;
 }
 function section(title){const card=el('section',undefined,'pf-card');card.append(el('h3',title));return card;}
 function render(key){
  root.replaceChildren();const d=window.PORTFOLIO_CHARTS?.[key];
  if(!d||!['DEMO','REFERENCE'].includes(d.data_state)){document.querySelector('#portfolio-state').textContent='BLOCKED · 표시 가능한 자료 없음';window.__portfolioLab={doc:null,mode:null,render};root.append(el('p','BLOCKED · 이 화면은 검증용 DEMO/목표비중 참고자료만 표시합니다.'));return;}
  const total=d.total_units;
  document.querySelector('#portfolio-state').textContent=d.data_state==='REFERENCE'?'REFERENCE · 기존 목표비중 참고자료 · 실제 계좌 아님':'DEMO · 가상 기업·비중·유형 · 투자 추천 아님';
  const meta=el('p',`${d.portfolio_version} · ${d.weight_basis} · 자료 확인 ${d.as_of} · PIT NOT_VERIFIED`);root.append(meta);
  const industry=section('① 산업군 구성 도넛');
  industry.append(el('p',key==='reference'?'기존 사용자가 정한 4개 목표 배분 그룹입니다. 표준 산업분류(GICS)와는 다릅니다.':'명시적으로 제공된 가상 산업 분류입니다. 현금과 미분류도 전체 분모에 포함합니다.'));
  industry.append(donut(d.industry.buckets.map((b,i)=>({label:b.kind==='CASH'?'현금':b.kind==='UNKNOWN'?'산업 미분류':b.label,units:b.units,color:b.kind==='UNKNOWN'?neutral:b.kind==='CASH'?cashColor:palette[i%palette.length]})),total,'전체 100%'));
  root.append(industry);
  const types=section('② 유형 구성 도넛');types.append(el('p','각 도넛의 분모는 동일한 전체 포트폴리오입니다. 한 종목이 여러 유형에 포함될 수 있어 유형별 노출 합계는 100%를 넘을 수 있습니다. 미분류는 해당 없음으로 간주하지 않습니다.'));
  if(d.types.exposures.every(e=>e.unknown_units===total))types.append(el('p','기업별 유형 배정 근거가 없어 전부 미분류입니다. 가상 예시를 선택하면 중복 유형 표시를 확인할 수 있습니다.','pf-warning'));
  types.append(el('p','확인된 유형 노출: '+d.types.exposures.map(e=>`${e.type} ${pct(e.member_units,total)}`).join(' / ')));
  const rings=el('div',undefined,'pf-type-grid');
  for(const [i,e] of d.types.exposures.entries()){
   const card=el('div');card.dataset.type=e.type;card.append(el('h4',e.type));
   card.append(donut([{label:'확인된 해당 유형',units:e.member_units,color:palette[i%palette.length]},{label:'확인된 비해당',units:e.non_member_units,color:'#253247'},{label:'유형 미분류',units:e.unknown_units,color:neutral},{label:'현금',units:e.cash_units,color:cashColor}],total,pct(e.member_units,total)));rings.append(card);
  }
  types.append(rings);root.append(types);
  const overlap=section('③ 유형 중복 조합 차트');overlap.append(el('p','정확히 같은 유형 조합을 가진 보유분끼리 묶습니다. “성장 + 우량”은 그 두 유형 조합이며, 다른 유형까지 포함한 종목은 별도 조합입니다. 현금·미분류를 포함해 각 보유분은 한 번만 집계합니다.'));
  const list=el('div',undefined,'pf-overlap');
  for(const [i,b] of d.overlap.buckets.entries()){
   const label=b.kind==='CASH'?'현금':b.kind==='UNKNOWN'?'유형 미분류':b.kind==='NO_TYPES'?'명시적으로 유형 없음':b.types.map(t=>`[${t}]`).join(' + ');
   const row=el('div',undefined,'pf-overlap-row');row.append(el('span',label));const track=el('div',undefined,'pf-bar-track');const bar=el('div',undefined,'pf-bar');bar.style.width=`${100*b.units/total}%`;bar.style.background=b.kind==='UNKNOWN'?neutral:palette[i%palette.length];track.append(bar);row.append(track,el('span',`${pct(b.units,total)} · ${exact(b.units,total)}`));list.append(row);
  }
  overlap.append(list);root.append(overlap);
  const details=el('details');details.append(el('summary','보유분별 원본 입력과 분류 확인'));
  const scroll=el('div',undefined,'scroll');const table=el('table');const thead=el('thead');const tr=el('tr');for(const s of ['보유분','비중','산업군','유형'])tr.append(el('th',s));thead.append(tr);table.append(thead);const tbody=el('tbody');
  for(const h of d.holdings){const row=el('tr');for(const v of [h.label,pct(h.weight_units,total),h.industry??'미분류',h.types===null?'미분류':h.types.length?h.types.join(' + '):'명시적으로 없음'])row.append(el('td',v));tbody.append(row);}table.append(tbody);scroll.append(table);details.append(scroll);root.append(details);
  const evidence=el('details');evidence.append(el('summary','계약 및 출처'));const pre=el('pre',JSON.stringify(d,null,2));evidence.append(pre);root.append(evidence);
  window.__portfolioLab={doc:d,mode:key,render};
 }
 document.querySelector('#portfolio-reference').onclick=()=>render('reference');document.querySelector('#portfolio-demo').onclick=()=>render('demo');render('reference');
})();
