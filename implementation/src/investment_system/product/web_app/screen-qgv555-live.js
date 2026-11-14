/* QGV 555 · 시총 Top500 · 사용자 설정 screens (IS2.qgv555Live; owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).
   Two places, one RAM state for this page load (nothing stored, nothing sent when a page opens):
   - 2.1 리더보드 (screen-qgv-live.js asks selector() inside 2.1.1): 모집단 기존504 / 시총 Top500 / 확장 연구 and 모형 기존 공식 /
     U1-555 통합 / S1-555 섹터 / 내 설정. Only 기존504 × 기존 공식 shows the existing table (screen-qgv-live.js, unchanged); every
     other pair shows IS2.qgv555.boardState and the population's header lines (선정 기준일 · 적용일 · 원래 분모 · 산출 수 · 참조집단),
     never another model's or population's result under the chosen name. A filter never changes a score: recalculation is 2.2.7.
   - 2.2.7 555 설정 (fill(): its own block after the sector settings body): 모형 선택 → Q/G/V → 5역할 확인 → 지표 교체·비중 → 실제
     재계산 → 전후 미리보기 → 저장/취소/기본값 복원. The editor is IS2.qgv555 (setting values only: sums, active count Q3/G4/V5,
     nominal = 설정값의 곱, input families). 「555 합성 계약 불러오기」 (a click) asks the development engine route for Main's
     SYNTHETIC proposal files (qgv555_context); 「실제 재계산」 asks qgv555_preview, which the route refuses with
     ENGINE_CONTRACT_PENDING until Codex delivers the 555 engine: the preview then says so and shows no number. 저장 needs the
     engine's record of the shown preview of this exact setting, so it stays off while there is none (no local fallback store).
   - 상세 (axis → 5 roles → factors) and 10분위 (D1–D10 in full, D10 = top, ties / valid N / band counts / missing) and the coverage
     stages (input → raw → factor → axis → all three → gate known / pass → total; Top500 95% = 475/500) are the engine's answer:
     each names its state until then, never a top-20 list in place of the ten bands, never 501 / 1057 / whole-market denominators.
   The published site has no engine route: ENGINE_NOT_CONNECTED, said as such. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const Q=()=>I.qgv555;
const REQ='sector-qgv-engine-request/1';
const S={pop:'universe504',model:'OFFICIAL',load:'IDLE',code:null,bundle:null,population:null,popCode:null,
 model2:'U1-555',scope:'COMMON',axis:'Q',edit:null,base:null,query:'',addRole:null,preview:null,pendingId:null,dropped:0,msg:null,err:null,saved:null};
const listeners=new Set();
const changed=()=>{for(const f of[...listeners]){try{f();}catch(_){}}};
let seq=0;const rid=()=>'q555-'+(++seq)+'-'+Math.random().toString(36).slice(2,8);
const sha256=async b=>{const d=await crypto.subtle.digest('SHA-256',b);return[...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('');};
const ENGINE_TEXT={ENGINE_NOT_CONNECTED:'계산 실행 경로 연결 전 · 이 사이트에는 엔진 경로가 없음',ENGINE_UNREACHABLE:'계산 실행 경로에 닿지 못함',
 ENGINE_CONTRACT_PENDING:'재계산 엔진 계약 전',MODEL_UNKNOWN:'모형 이름이 맞지 않음',ABORTED:'화면을 떠나 멈춤'};
const scopeText=sc=>{if(sc==='COMMON')return'통합 공통';const[sec,t]=String(sc).split('|'),T=I.taxonomy;return(T&&typeof T.sectorName==='function'?T.sectorName(sec):sec)+' · '+(Q().TEMPLATE_TEXT[t]||t);};
const say=c=>ENGINE_TEXT[c]||(/^[A-Z0-9_]+$/.test(String(c))?'엔진이 거절함':String(c||'알 수 없는 거절'));
const chip=(label,on,attrs={})=>h('button',{type:'button',class:'chip','aria-pressed':String(!!on),...attrs},label);
const group=(label,...kids)=>h('div',{class:'scroll',role:'group','aria-label':label},...kids);

/* ---- one load of the synthetic contract (a click) */
async function load(signal){if(S.load==='LOADING')return;S.load='LOADING';S.code=null;changed();
 let res=null;try{res=await I.data.engine({schema_version:REQ,op:'qgv555_context',request_id:rid()},{signal});}
 catch(e){S.load='ERROR';S.code=e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE');changed();return;}
 if(!res||res.ok!==true){S.load='ERROR';S.code=res&&res.code||'ENGINE_ANSWER_INVALID';changed();return;}
 const b=Q().checkBundle(res.catalog,res.presets);if(!b.ok){S.load='ERROR';S.code='계약 형식 거부 '+b.code+' · '+b.path;changed();return;}
 const p=await Q().checkPopulation(res.population,sha256);
 S.bundle=b.value;S.population=p.ok?p.value:null;S.popCode=p.ok?null:p.code+' · '+p.path;S.load='READY';pick(S.model2,S.model2==='U1-555'?'COMMON':Q().scopesOf(S.bundle,'S1-555')[0]);changed();}
function pick(model,scope){const p=Q().presetFor(S.bundle,model,scope);if(!p)return;S.model2=model;S.scope=scope;S.base=p;S.edit=Q().start(p);S.preview=null;S.pendingId=null;S.err=null;S.msg=null;}

/* ---- 2.1 selector (inside 2.1.1) */
// redraw: the leaderboard's own redraw. Returns {el, official}: official=true only for 기존504 × 기존 공식 (the existing table).
function selector({redraw}){const M=Q();if(!M)return{el:null,official:true};
 const set=fn=>()=>{fn();redraw();};
 const pops=group('모집단',...Object.entries(M.POPULATIONS).map(([k,p])=>chip(p.label,S.pop===k,{dataset:{q5Pop:k,k:'q5-pop-'+k},onclick:set(()=>{S.pop=k;})})));
 const models=group('모형 (555)',...Object.entries(M.MODELS).map(([k,m])=>chip(m.label,S.model===k,{dataset:{q5Model:k,k:'q5-model-'+k},onclick:set(()=>{S.model=k;})})));
 const official=S.pop==='universe504'&&S.model==='OFFICIAL';
 const pv=M.populationView(S.pop,S.pop==='top500'?S.population:null);
 const head=h('div',{dataset:{q5Select:''}},h('p',{class:'hand'},'모집단과 모형을 따로 고름 · 필터는 점수를 바꾸지 않음 · 재계산은 1.2의 555 설정에서'),pops,models,
  h('p',{class:'reason',dataset:{q5PopText:S.pop}},pv.text));
 if(official)return{el:head,official:true};
 const st=M.boardState(S.pop,S.model,{officialLoaded:true,savedConfig:S.saved,population:S.population});
 const m=M.MODELS[S.model];
 const panel=h('div',{class:'sk state-card',dataset:{q5Board:st.state}},I.parts.mascot('plain'),h('b',null,M.POPULATIONS[S.pop].label,' × ',m.label),
  h('span',{class:'reason',dataset:{q5BoardText:''}},st.text),
  m.model_id?h('span',{class:'meta',dataset:{q5Ids:''}},'모형 ',m.model_id,' · 기본 설정 ',m.preset_id,' · 계산 담당 확정 전 제안'):null);
 const lines=h('ul',{class:'news-lines',dataset:{q5PopLines:pv.state}},...pv.lines.map(t=>h('li',null,t)),
  h('li',{dataset:{q5Counts:''}},'원래 분모 · 산출 수 · 참조집단: '+(S.pop==='top500'&&S.population?'원래 분모 '+S.population.n+' 고유 발행사 · 산출 수와 참조집단은 엔진 답 전':'엔진 답 전 · 표시 없음')),
  h('li',null,'시총 선정 순위와 QGV 순위는 다른 열 · QGV 순위는 결과 전달 뒤에만'));
 return{el:h('div',null,head,panel,lines),official:false};}

/* ---- 2.2.7 555 설정 */
function fill(route,{body}){const signal=route.signal;
 const box=h('section',{class:'sq-555',dataset:{q5Block:''},'aria-label':'QGV 555 설정'});
 if(body.parentNode&&!body.parentNode.querySelector('[data-q5-block]'))body.parentNode.appendChild(box);else return;
 const focusKey=()=>{const a=document.activeElement;return a&&box.contains(a)&&a.dataset&&a.dataset.k?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const el=box.querySelector('[data-k="'+CSS.escape(k)+'"]');if(el&&!el.disabled)el.focus({preventScroll:true});};
 const paint=()=>{if(signal.aborted){listeners.delete(paint);return;}const k=focusKey();box.replaceChildren(...view().flat(Infinity).filter(Boolean));refocus(k);};
 listeners.add(paint);signal.addEventListener('abort',()=>listeners.delete(paint),{once:true});
 const act=fn=>()=>{try{fn();S.err=null;}catch(e){S.err=errText(String(e&&e.message||e));}S.preview=S.preview&&S.preview.key===key()?S.preview:null;changed();};
 const key=()=>S.edit?JSON.stringify(S.edit):null;
 async function recalc(){const M=Q(),req={schema_version:REQ,op:'qgv555_preview',request_id:rid(),model_id:S.edit.model_id,config:S.edit},k=key();
  S.pendingId=req.request_id;S.preview=null;S.msg=null;changed();let res=null;
  try{res=await I.data.engine(req,{signal});}catch(e){res={request_id:req.request_id,ok:false,code:e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE')};}
  if(signal.aborted)return;
  if(S.pendingId!==req.request_id||key()!==k){S.dropped++;changed();return;}// an older answer, or one for another edit
  S.pendingId=null;const a=M.previewAnswer(req,res,req);
  S.preview={key:k,state:a.state==='ENGINE_NOT_CONNECTED'&&res&&res.code?res.code:a.state,code:res&&res.code||null};changed();}
 function view(){const M=Q();
  const head=[h('h3',{class:'stamp sub',tabindex:'-1'},'2.2.7 QGV 555 설정 · 5역할 · 내 설정'),
   h('p',{class:'hand'},'축마다 평가 역할 5개 · 한 역할 안의 여러 지표는 그 역할 몫을 나눔 · 333 후보 채택 아님 · 화면은 설정값만 다루고 점수·순위·실효 비중은 엔진 답')];
  if(S.load!=='READY')return[head,h('div',{class:'sk state-card',dataset:{q5Load:S.load}},I.parts.mascot(S.load==='ERROR'?'alarm':'plain'),
   h('b',null,S.load==='ERROR'?'불러오지 못함':'555 계약 · 합성 자료'),h('span',{class:'reason'},S.load==='ERROR'?say(S.code):'요소 목록·기본 설정·Top500 모집단 합성 자료(계산 담당 확정 전 제안) · 누를 때만 부름'),
   h('button',{type:'button',class:'btn',disabled:S.load==='LOADING',dataset:{k:'q5-load'},onclick:()=>{void load(signal);}},S.load==='LOADING'?'불러오는 중':'555 합성 계약 불러오기'))];
  const B=S.bundle,c=S.edit,cat=B.catalog,sums=M.sums(c,cat),cnt=M.activeCount(c);
  // ① 모형 선택 · 범위
  const models=group('555 모형',...['U1-555','S1-555'].map(k=>chip(M.MODELS[k].label,S.model2===k,{dataset:{q5M2:k,k:'q5-m2-'+k},
   onclick:act(()=>pick(k,k==='U1-555'?'COMMON':M.scopesOf(B,'S1-555')[0]))})));
  const scopes=S.model2==='S1-555'?h('label',{class:'meta'},'섹터·회계모형 ',h('select',{dataset:{k:'q5-scope'},onchange:e=>act(()=>pick('S1-555',e.target.value))()},
   ...M.scopesOf(B,'S1-555').map(s=>h('option',{value:s,selected:s===S.scope},scopeText(s))))):null;
  const ids=h('p',{class:'meta',dataset:{q5Base:''}},'원본 참조 ',c.base.preset_id,' · ',c.base.version,' · ',scopeText(c.base.scope),' · ',M.KIND_TEXT[M.MODELS[S.model2].kind],
   ' · ',B.data_kind==='SYNTHETIC'?'합성 자료':'실자료',' · 다른 회계모형으로 자동 복사하지 않음');
  // ② Q/G/V 축 비중
  const axes=h('div',{class:'scroll',role:'group','aria-label':'축 비중',dataset:{q5Axes:''}},...M.AXES.map(a=>h('label',{class:'chip'},a+' ',
   h('input',{type:'number',min:0,max:10000,step:100,value:c.axis_weights[a],inputmode:'numeric','aria-label':a+' 축 비중(만분율)',dataset:{k:'q5-axis-'+a},
    onchange:e=>act(()=>{S.edit=M.setAxis(S.edit,a,Number(e.target.value));})()}))),h('span',{class:'meta'},'합 ',String(sums.axis),' / 10000'));
  const tabs=group('축',...M.AXES.map(a=>chip(a+' · '+cnt[a]+'역할',S.axis===a,{dataset:{q5Tab:a,k:'q5-tab-'+a},onclick:act(()=>{S.axis=a;S.addRole=null;})})));
  // ③ 5역할 · ④ 지표 교체·비중
  const roles=cat.roles[S.axis].map(r=>roleBlock(M,cat,c,S.axis,r,sums));
  const problems=sums.problems.length?h('ul',{class:'news-lines',dataset:{q5Problems:String(sums.problems.length)}},...sums.problems.map(p=>h('li',{class:'hand err'},probText(p.code),' · ',pathText(p.path)))):
   h('p',{class:'meta',dataset:{q5Problems:'0'}},'합계 맞음 · 엔진 검사는 재계산 때');
  const ov=M.overlap(c,cat);
  const overlap=h('details',{class:'why',dataset:{q5Overlap:String(ov.length)}},h('summary',null,'정보 중복 · 같은 원입력 계열 '+ov.length+'개 ▸'),
   h('p',{class:'reason'},'같은 정보를 여러 역할·축에서 읽으면 합산 명목 노출을 보임 · 감점·숨은 비중 조정 없음'),
   h('ul',{class:'news-lines'},...ov.map(e=>h('li',{dataset:{q5Family:e.family}},h('b',null,e.name),' · ',e.roles.join(', '),' · ',e.cross_axis?'축을 넘음 · ':'','합산 명목 ',e.exposure))));
  // ⑤ 재계산 · ⑥ 전후 미리보기 · ⑦ 저장/취소/복원
  const pend=S.pendingId!==null,pv=S.preview&&S.preview.key===key()?S.preview:null;
  const run=h('div',{class:'conn',dataset:{q5Run:''}},h('span',{class:'chip',dataset:{q5Active:cnt.text}},'활성 역할 ',cnt.text),
   h('button',{type:'button',class:'btn mine',disabled:pend||sums.problems.length>0,dataset:{k:'q5-recalc'},onclick:()=>{void recalc();}},pend?'재계산 요청 중':'실제 재계산'),
   h('button',{type:'button',class:'btn',disabled:true,title:'엔진이 이 설정의 미리보기를 저장 기록으로 돌려준 뒤에만',dataset:{k:'q5-save',q5SaveOff:'NO_ENGINE_RECORD'}},'저장'),
   h('button',{type:'button',class:'btn',dataset:{k:'q5-cancel'},onclick:act(()=>{S.edit=M.start(S.base);})},'변경 취소'),
   h('button',{type:'button',class:'btn',dataset:{k:'q5-restore'},onclick:act(()=>{S.edit=M.restore(S.edit,B);S.msg='기본값 복원 · '+S.edit.base.preset_id+' · '+S.edit.base.version+' · '+scopeText(S.edit.base.scope);})},'기본값 복원'));
  const preview=h('div',{class:'sk state-card',role:'status',dataset:{q5Preview:pv?pv.state:(pend?'PENDING':'NONE')}},
   h('b',null,'전후 미리보기'),h('span',{class:'reason'},pv?(M.PREVIEW_STATE[pv.state]||say(pv.state)):pend?'요청 중 · 끝나기 전 답은 보이지 않음':'재계산 전 · 같은 입력의 전후 비교는 엔진 답으로만'),
   h('span',{class:'meta'},'모집단 효과와 설정 효과를 따로 · 산출 수·분모·원인·명목/재배분/관문 뒤 비중·계열 기여·버전은 엔진 답 전'),
   S.dropped?h('span',{class:'meta',dataset:{q5Dropped:String(S.dropped)}},'버린 늦은 답 ',String(S.dropped)):null);
  const msg=S.err?h('p',{class:'hand err',role:'alert',dataset:{q5Err:''}},S.err):S.msg?h('p',{class:'hand',dataset:{q5Msg:''}},S.msg):null;
  return[head,models,scopes,ids,axes,tabs,h('div',{dataset:{q5Roles:S.axis}},...roles),problems,overlap,run,msg,preview,detailBlock(M,cat,c),decileBlock(),coverageBlock()];}
 function roleBlock(M,cat,c,a,r,sums){const x=c.axes[a][r.role_id],on=x.weight>0&&Object.keys(x.factors).length>0;
  const rows=Object.entries(x.factors).map(([v,share])=>{const f=cat.factors.find(g=>g.variant_id===v);const k=M.card(cat,f,c);
   const variants=f.variant_group?cat.factors.filter(g=>g.variant_group===f.variant_group&&g.variant_id!==v&&M.selectable(g,c.scope).ok):[];
   return h('li',{dataset:{q5Factor:v}},h('b',null,k.name),' ',h('span',{class:'meta'},k.formula),' ',
    h('label',{class:'meta'},'역할 안 ',h('input',{type:'number',min:0,max:10000,step:100,value:share,inputmode:'numeric','aria-label':k.name+' 역할 안 비중(만분율)',dataset:{k:'q5-share-'+v},
     onchange:e=>act(()=>{S.edit=M.setShare(S.edit,a,r.role_id,v,Number(e.target.value));})()})),' ',
    variants.length?h('select',{'aria-label':k.name+' 기간·공식 변형',dataset:{k:'q5-var-'+v},onchange:e=>act(()=>{if(e.target.value)S.edit=M.chooseVariant(S.edit,cat,v,e.target.value);})()},
     h('option',{value:''},'변형 선택'),...variants.map(g=>h('option',{value:g.variant_id},g.display_name+' · '+g.period))):null,' ',
    h('button',{type:'button',class:'lk',dataset:{k:'q5-rm-'+v},onclick:act(()=>{S.edit=M.removeFactor(S.edit,a,r.role_id,v);})},'빼기'),
    h('div',{class:'meta'},k.weights),k.overlap.length?h('div',{class:'meta',dataset:{q5CardOverlap:''}},'중복 ',k.overlap.join(' · ')):null,
    k.composite?h('div',{class:'meta',dataset:{q5Composite:v}},'복합 내부 ',...f.composite.components.map(p=>h('label',null,p.variant_id+' ',
     h('input',{type:'number',min:p.min_weight,max:p.max_weight,step:100,value:c.composites[v]?c.composites[v][p.variant_id]:p.default_weight,inputmode:'numeric','aria-label':k.name+' 내부 '+p.variant_id,dataset:{k:'q5-comp-'+v+'-'+p.variant_id},
      onchange:e=>act(()=>{S.edit=M.setComposite(S.edit,cat,v,p.variant_id,Number(e.target.value));})()}),' ')),' (허용 범위 밖은 거절)'):null);});
  const adding=S.addRole===a+'.'+r.role_id;
  return h('div',{class:'lb',dataset:{q5Role:r.role_id,q5RoleOn:String(on)}},
   h('div',{class:'lb-head'},h('b',null,r.name),h('span',{class:'meta'},r.economic_role),
    h('label',{class:'meta'},'역할 비중 ',h('input',{type:'number',min:0,max:10000,step:100,value:x.weight,inputmode:'numeric','aria-label':r.name+' 역할 비중(만분율)',dataset:{k:'q5-role-'+r.role_id},
     onchange:e=>act(()=>{S.edit=M.setRole(S.edit,a,r.role_id,Number(e.target.value));})()})),
    h('span',{class:'meta'},on?'활성':'제외(0)'),
    on?h('button',{type:'button',class:'lk',dataset:{k:'q5-ex-'+r.role_id},onclick:act(()=>{S.edit=M.excludeRole(S.edit,a,r.role_id);})},'역할 제외'):null),
   rows.length?h('ul',{class:'news-lines'},...rows):h('p',{class:'meta'},'선택한 지표 없음'),
   h('button',{type:'button',class:'btn',dataset:{k:'q5-add-'+r.role_id},'aria-expanded':String(adding),onclick:act(()=>{S.addRole=adding?null:a+'.'+r.role_id;S.query='';})},adding?'지표 목록 닫기':'지표 추가·교체'),
   adding?cards(M,cat,c,a,r):null);}
 function cards(M,cat,c,a,r){const fs=cat.factors.filter(f=>f.axis===a&&f.role_id===r.role_id),chosen=Object.keys(c.axes[a][r.role_id].factors);
  const q=S.query.trim(),hit=q?new Set(M.search(cat,q)):null;
  return h('div',{dataset:{q5Cards:r.role_id}},h('label',{class:'meta'},'찾기 ',h('input',{type:'search',value:S.query,'aria-label':'지표 이름·별칭 찾기',dataset:{k:'q5-q'},oninput:e=>{S.query=e.target.value;changed();}})),
   h('ul',{class:'news-lines'},...fs.filter(f=>!hit||hit.has(f.variant_id)).map(f=>{const k=M.card(cat,f,c),sel=chosen.includes(f.variant_id);
    return h('li',{dataset:{q5Card:f.variant_id,q5Selectable:String(k.selectable)}},h('b',null,k.name),' ',...k.badges.map(t=>h('span',{class:'chip'},t)),
     h('div',{class:'meta'},k.role,' · ',k.formula,' · 적용 ',k.templates),h('div',{class:'meta'},k.status,' · ',k.families,' · ',k.data),
     k.aliases.length?h('div',{class:'meta'},'별칭 ',k.aliases.join(', '),' (같은 지표로 한 번만)'):null,
     k.evidence?h('details',{class:'why'},h('summary',null,'근거 ▸'),h('p',{class:'meta'},k.evidence)):null,
     !k.selectable&&k.alternatives.length?h('div',{class:'meta',dataset:{q5Alt:''}},'대안 ',k.alternatives.join(' · ')):null,
     k.selectable&&!sel?h('span',null,h('button',{type:'button',class:'lk',dataset:{k:'q5-pick-'+f.variant_id},onclick:act(()=>{S.edit=M.addFactor(S.edit,cat,f.variant_id);})},'추가(역할 몫 나눔)'),
      ...chosen.map(v=>[' ',h('button',{type:'button',class:'lk',dataset:{k:'q5-swap-'+v+'-'+f.variant_id},onclick:act(()=>{S.edit=M.replaceFactor(S.edit,cat,v,f.variant_id);})},cat.factors.find(g=>g.variant_id===v).display_name+' 대신')])):null);})));}
 function detailBlock(M,cat,c){return h('details',{class:'why',dataset:{q5Detail:''}},h('summary',null,'상세 · 축 → 5역할 → 지표 ▸'),
  h('ul',{class:'news-lines'},...M.AXES.map(a=>h('li',null,h('b',null,a,' ',M.pct(c.axis_weights[a],10000)),
   h('ul',null,...cat.roles[a].map(r=>{const x=c.axes[a][r.role_id];return h('li',null,r.name,' ',M.pct(x.weight,10000),' · ',
    Object.keys(x.factors).map(v=>cat.factors.find(f=>f.variant_id===v).display_name+' '+M.pct(x.factors[v],10000)).join(', ')||'지표 없음');}))))),
  h('p',{class:'meta'},'기업별 축·역할·지표 점수와 실효 비중은 엔진 답 전'));}
 function decileBlock(){return h('div',{class:'lb',dataset:{q5Deciles:'NOT_DELIVERED'}},h('div',{class:'lb-head'},h('b',null,'요소 10분위'),h('span',{class:'meta'},'D1~D10 전체 · D10 = 상위')),
  h('div',{class:'scroll',role:'group','aria-label':'10분위'},...Array.from({length:10},(_,i)=>h('span',{class:'chip wait'},'D'+(i+1)))),
  h('p',{class:'reason'},'555 결과 전달 전 · 상위 20개로 대신하지 않음 · 전달 뒤 동점·유효 N·구간별 수·결측을 함께 보임'));}
 function coverageBlock(){const steps=['입력','원값','요소','축','세 축 모두','관문 판정','관문 통과','총점'];
  return h('div',{class:'lb',dataset:{q5Coverage:'NOT_DELIVERED'}},h('div',{class:'lb-head'},h('b',null,'커버리지 단계'),h('span',{class:'meta'},'일부 점수와 15역할 모두 완비는 따로')),
   h('ol',{class:'news-lines'},...steps.map(t=>h('li',null,t,' ',h('b',null,'엔진 답 전')))),
   h('p',{class:'reason'},'Top500 95% 목표 = 475/500 · 501·1057·전체시장 분모와 섞지 않음 · QGV·기술·매크로는 같은 스냅숏 기준'));}
 changed();}
const PROB={AXIS_SUM:'축 비중 합이 10000이 아님',ROLE_SUM:'역할 비중 합이 10000이 아님',FACTOR_SUM:'역할 안 지표 비중 합이 10000이 아님',ROLE_EMPTY:'비중이 있는 역할에 지표 없음',
 ROLES_NOT_FIVE:'역할이 5개가 아님',WEIGHT_INVALID:'비중 값이 0~10000 정수가 아님',NOT_FIT:'이 회계모형에 부적합',PENDING_DEFINITION:'정의 확정 전 지표',FACTOR_ROLE_UNKNOWN:'다른 역할의 지표'};
const probText=c=>PROB[c]||c;
const ERR={ALIAS_DUPLICATE:'같은 지표(별칭)를 두 번 고를 수 없음',PENDING_DEFINITION:'정의 확정 전 지표 · 선택 불가',NOT_FIT:'이 회계모형에 부적합 · 대안을 보세요',
 COMPOSITE_BOUNDS:'복합 지표 내부 비중이 허용 범위 밖',WEIGHT_INVALID:'비중은 0~10000 정수',FACTOR_ROLE_MISMATCH:'다른 역할의 지표로는 교체할 수 없음',VARIANT_GROUP_MISMATCH:'같은 개념의 변형만',
 BASE_PRESET_MISSING:'원본 기본 설정을 찾지 못함 · 복원하지 않음'};
const errText=c=>ERR[c]||'설정을 바꾸지 못함';
const pathText=p=>{const[a,b,c]=String(p).split('.');if(a==='axis_weights')return'축 비중';const R=S.bundle&&b?S.bundle.catalog.roles[b]:null,r=R&&c?R.find(x=>x.role_id===c):null;return b+(r?' '+r.name:'');};
function subscribe(fn,signal){listeners.add(fn);if(signal)signal.addEventListener('abort',()=>listeners.delete(fn),{once:true});}
const isOfficial=()=>S.pop==='universe504'&&S.model==='OFFICIAL';
I.qgv555Live=Object.freeze({selector,fill,subscribe,isOfficial,state:()=>S});
})();
