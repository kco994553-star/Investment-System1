(()=>{
 const catalog=window.CHART_INVENTORY;
 const groups={A:'시장 가격 차트',B:'Technical',C:'QGV',D:'Analyst / Consensus',E:'Portfolio',F:'Simulation / Backtest',G:'Macro',H:'Leaderboard / 기업 상세',I:'추가 Spec 시각화',J:'이번 점검의 추가 명시 요구',K:'Macro Candidate 확장'};
 const states={R:'READY (해당 감사 범위)',I:'입력 의존 구현',P:'PARTIAL',S:'SPEC_ONLY / 구현 미발견',H:'PLACEHOLDER',U:'미재감사 / 미확인'};
 const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;return x;};
 const search=document.querySelector('#inventory-search'),select=document.querySelector('#inventory-group'),host=document.querySelector('#inventory-rows');
 for(const [value,label]of Object.entries(groups)){const option=el('option',`${value}. ${label}`);option.value=value;select.append(option);}
 function render(){
  const query=search.value.trim().toLocaleLowerCase();
  const matcher=/^[a-z]+$/i.test(query)?new RegExp('(^|[^A-Za-z])'+query+'(?=$|[^A-Za-z])','i'):null;
  const matches=r=>{const value=[r.id,r.name,r.gap,r.details,r.latest_note].join(' ');return matcher?matcher.test(value):value.toLocaleLowerCase().includes(query);};
  const rows=catalog.items.filter(r=>(!select.value||r.group===select.value)&&(!query||matches(r)));
  document.querySelector('#inventory-count').textContent=`${catalog.counts.total_rows}개 요구 항목: 핵심81 + 추가 Spec24 + Candidate8 · 표시 ${rows.length}개`;
  host.replaceChildren();
  for(const row of rows){
   const item=el('details');item.className='inventory-row';item.dataset.id=row.id;
   item.append(el('summary',`${row.id} · ${row.name}`));const state=el('p',row.latest_state);state.className='state';item.append(state,el('p',row.latest_note));
   if(row.details)item.append(el('p',row.details));
   const dl=el('dl');for(const [i,name]of ['L1 원본','L2 계산','L3 계약','L4 화면','L5 검증'].entries()){dl.append(el('dt',name),el('dd',`Canonical: ${states[row.c[i]]} / 기존 PR40 감사: ${states[row.t[i]]}`));}item.append(dl);
   item.append(el('p',`기존 gap / 후속 확인: ${row.gap}`));
   const evidence=el('ul');for(const ref of row.evidence){const li=el('li');const a=el('a',ref.path);a.href=`https://github.com/kco994553-star/Investment-System1/blob/${ref.sha}/${ref.path.split('/').map(encodeURIComponent).join('/')}`;li.append(a,el('span',` — ${ref.note}`));evidence.append(li);}item.append(evidence);host.append(item);
  }
 }
 search.addEventListener('input',render);select.addEventListener('change',render);render();window.__inventoryLab={catalog,render};
})();
