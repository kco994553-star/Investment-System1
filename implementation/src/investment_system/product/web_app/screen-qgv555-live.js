/* QGV 555 · 시총 Top500 · 사용자 설정 screens (IS2.qgv555Live; owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49;
   Codex #537 beaadbd2 research.qgv_555 / top500_selection through the development engine route).
   One RAM state for this page load; nothing is sent when a page opens.
   - 2.1 (screen-qgv-live.js asks selector() inside 2.1.1): 모집단 기존504 / 시총 Top500 / 확장 연구 × 모형 기존 공식 / U1-555 /
     S1-555 / 내 설정. Only 기존504 × 기존 공식 goes on to the existing table; every other pair is its own state panel (no result of
     another model or population under the chosen name). The Top500 lines come from the engine's selection (public view).
   - 2.2.7 (fill(): its own block after the sector settings body): 「555 계약 불러오기」 (a click: qgv555_context + both synthetic
     selections) → 모형 → 범위(S1: 섹터·회계모형; only complete recipes edit) → Q/G/V → 5역할 → 지표 추가·교체·역할 안 비중 →
     「실제 재계산」 (qgv555_preview: Codex run() of the edited and the before setting on the same synthetic input) → 전후 비교 ·
     커버리지 단계 · 역할 10분위 · 기업 상세 → 저장 (the engine's replay record of the shown preview of this exact setting, this
     device only, IS2.store.qgv555) / 변경 취소 / 기본값 복원 / 이 범위 되돌리기 / 저장 설정 재현 (qgv555_replay).
   - Only the latest request's answer is shown; an answer for another setting or another model is dropped (counted).
   - Scores, ranks, deciles, nominal / effective weights, coverage: the engine's answer as returned. The published site has no
     engine route: 계산 실행 경로 연결 전. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const Q=()=>I.qgv555;
const REQ='sector-qgv-engine-request/1';
const S={pop:'universe504',model:'OFFICIAL',load:'IDLE',code:null,ctx:null,selections:null,selKind:'SYNTHETIC_COMPLETE',
 cand:'U1-555',scope:'COMMON',axis:'Q',edit:null,addRole:null,query:'',preview:null,pendingId:null,current:null,dropped:0,msg:null,err:null,
 company:null,detail:null,decRole:'q_profitability',dec:null,replay:null,savedStale:false,stored:{},storedModelRole:'q_profitability'};
const listeners=new Set();
const changed=()=>{for(const f of[...listeners]){try{f();}catch(_){}}};
let seq=0;const rid=()=>'q555-'+(++seq)+'-'+Math.random().toString(36).slice(2,8);
const ENGINE_TEXT={ENGINE_NOT_CONNECTED:'계산 실행 경로 연결 전 · 이 사이트에는 엔진 경로가 없음',ENGINE_UNREACHABLE:'계산 실행 경로에 닿지 못함',MODEL_UNKNOWN:'모형 이름이 맞지 않음',
 MODEL_RESPONSE_MISMATCH:'답한 모형이 요청과 다름 · 쓰지 않음',DUPLICATE_CANONICAL_METRIC:'같은 지표(별칭)를 한 역할에 두 번 넣을 수 없음',DUPLICATE_SAME_FORMULA_METRIC:'같은 산식의 지표를 한 역할에 두 번 넣을 수 없음',
 AXIS_WEIGHTS:'축 비중은 0 이상이고 합이 0보다 커야 함',ROLE_WEIGHTS:'축마다 역할 비중 합이 0보다 커야 함',METRIC_WEIGHTS:'역할마다 지표 비중 합이 0보다 커야 함',SECTOR_AXIS_WEIGHTS:'섹터 축 비중이 맞지 않음',
 UNSUPPORTED_METRIC_VARIANT:'이 축에 없는 지표',SAVED_INPUT_MISMATCH:'저장 때 입력과 다름 · 재현 아님',
 SAVED_ENGINE_VERSION_REQUIRED:'저장 때 엔진 판이 필요 · 재현 아님',SAVED_NOT_REPRODUCED:'저장 설정을 다시 계산한 결과가 저장 결과와 다름 · 이전 결과로 쓰지 않음',SAVED_ENGINE_OR_CONFIGURATION_MISMATCH:'저장 설정과 비교 기준 설정이 다름 · 쓰지 않음',BEFORE_SOURCE:'비교 기준(전)이 저장 결과 재현이 아님 · 쓰지 않음',SAVED_INVALID:'저장 기록 형식이 맞지 않음',ABORTED:'화면을 떠나 멈춤',LATE_ANSWER:'늦게 온 답 · 쓰지 않음',MODEL_MISMATCH:'답한 모형이 요청과 다름 · 쓰지 않음',
 CONFIG_MISMATCH:'답의 설정이 요청한 설정과 다름 · 쓰지 않음',INPUT_MISMATCH:'답의 평가·참조 입력이 이 경로의 기준과 다름 · 쓰지 않음',PAGE_GAP:'페이지가 이어지지 않음(누락·순서 어긋남) · 붙이지 않음',
 AUTH_REQUIRED:'로그인 필요 · 비공개 영역에서 로그인한 뒤 다시',KIS_SERIES_NOT_FOUND:'보관 결과가 전달 위치에 없음(배치 전)',AUTH_FORBIDDEN:'이 계정은 읽을 수 없음',RATE_LIMITED:'요청 간격 제한 · 잠시 뒤 다시',
 EVALUATION_ANCHOR:'평가 입력이 독립 기준과 다름 · 쓰지 않음',REFERENCE_ANCHOR:'참조 입력이 독립 기준과 다름 · 쓰지 않음',MEMBER_HASH:'파일이 목록표의 해시와 다름 · 쓰지 않음',MANIFEST_HASH:'목록표가 배치 기록과 다름 · 쓰지 않음',INDEX_HASH:'색인이 목록표와 다름 · 쓰지 않음'};
const say=c=>{const k=String(c||'').split(':')[0];return ENGINE_TEXT[k]||(/^POLICY_CHANGE/.test(k)?'정책 값은 이 화면에서 바꿀 수 없음':'엔진이 거절함');};
const EDIT_TEXT={WEIGHT_INVALID:'비중은 0 이상의 숫자',METRIC_NOT_SELECTED:'선택되지 않은 지표',ROLE_LAST_METRIC:'역할의 마지막 지표는 뺄 수 없음 · 역할 제외를 쓰세요',
 ALIAS_DUPLICATE:'같은 지표(별칭)를 이 역할에 두 번 고를 수 없음',AXIS_MISMATCH:'다른 축의 지표',ACCOUNTING_NOT_APPLICABLE:'이 회계모형에 부적합 · 대안을 보세요',
 ACCOUNTING_RECIPE_PREPARING:'이 회계모형의 555 정의 준비 중',NOT_IMPLEMENTED:'계산 구현 전 지표',SETTING_SCOPE:'범위를 먼저 고르세요',BASE_VERSION_MISSING:'원래 기본 설정 판을 찾지 못함 · 복원하지 않음',ROLE_UNKNOWN:'알 수 없는 역할',METRIC_UNKNOWN:'알 수 없는 지표'};
const editText=c=>EDIT_TEXT[String(c).split(':')[0]]||'설정을 바꾸지 못함';
const PROB={AXIS_WEIGHTS:'축 비중 합이 0',ROLE_WEIGHTS:'역할 비중 합이 0',METRIC_WEIGHTS:'지표 비중 합이 0'};
const chip=(label,on,attrs={})=>h('button',{type:'button',class:'chip','aria-pressed':String(!!on),...attrs},label);
const group=(label,...kids)=>h('div',{class:'scroll',role:'group','aria-label':label},...kids);
const num=(label,value,k,on,attrs={})=>h('input',{type:'number',min:0,step:1,value,inputmode:'decimal','aria-label':label,dataset:{k},onchange:e=>on(Number(e.target.value)),...attrs});
const SC=Q;
function scopeText(sc){if(sc==='COMMON')return'통합 공통';const[sec,t]=String(sc).split('|'),T=I.taxonomy;return(T&&typeof T.sectorName==='function'?T.sectorName(sec):sec)+' · '+(SC().TEMPLATE_TEXT[t]||t);}
async function call(op,fields,signal){const req={schema_version:REQ,op,request_id:rid(),...fields};
 try{return{req,res:await I.data.engine(req,{signal})};}catch(e){return{req,res:{ok:false,request_id:req.request_id,code:e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE')}};}}
const savedAll=()=>{let r=null;try{r=I.store.qgv555.read();}catch(_){r=null;}return r&&r.state==='OK'?r.value.records:{};};
const savedOf=model_id=>savedAll()[model_id]||null;

/* ---- one load (a click) */
async function load(signal){if(S.load==='LOADING')return;S.load='LOADING';S.code=null;changed();
 const a=await call('qgv555_context',{},signal);if(!a.res||a.res.ok!==true){S.load='ERROR';S.code=a.res&&a.res.code;changed();return;}
 let ctx;try{ctx=Q().checkContext(a.res);}catch(e){S.load='ERROR';S.code='CONTEXT '+e.message;changed();return;}
 const sel={};for(const k of['SYNTHETIC_COMPLETE','SYNTHETIC_ROSTER_UNPROVEN']){const b=await call('qgv555_population',{input_id:k},signal);
  if(b.res&&b.res.ok===true){try{sel[k]=Q().checkView(b.res.view);}catch(_){sel[k]=null;}}}
 S.ctx=ctx;S.selections=sel;S.load='READY';pick('U1-555','COMMON');changed();}
// A saved setting comes back on restart; a record of other inputs (anchors differ) keeps its setting but is not this input's result.
function pick(cand,scope){const sv=savedOf(Q().MODELS[cand].model_id);S.cand=cand;S.scope=scope;S.edit=sv?Object.freeze(JSON.parse(JSON.stringify(sv.configuration))):Q().start(S.ctx,cand);S.savedStale=!!sv&&!Q().savedMatches(sv,S.ctx.anchors);
 S.preview=null;S.pendingId=null;S.current=null;S.err=null;S.msg=null;S.company=null;S.detail=null;S.dec=null;S.replay=null;}

/* ---- 2.1 selector (inside 2.1.1) */
function selector({redraw}){const M=Q();if(!M)return{el:null,official:true};
 const set=fn=>()=>{fn();redraw();};
 const pops=group('모집단',...Object.entries(M.POPULATIONS).map(([k,p])=>chip(p.label,S.pop===k,{dataset:{q5Pop:k,k:'q5-pop-'+k},onclick:set(()=>{S.pop=k;})})));
 const models=group('모형 (555)',...Object.entries(M.MODELS).map(([k,m])=>chip(m.label,S.model===k,{dataset:{q5Model:k,k:'q5-model-'+k},onclick:set(()=>{S.model=k;})})));
 const official=S.pop==='universe504'&&S.model==='OFFICIAL';
 const sel=S.selections?S.selections[S.selKind]:null,pv=M.populationView(S.pop,S.pop==='top500'?sel:null,'SYNTHETIC');
 const head=h('div',{dataset:{q5Select:''}},h('p',{class:'hand'},'모집단과 모형을 따로 고름 · 필터는 점수를 바꾸지 않음 · 재계산은 1.2의 555 설정에서'),pops,models,
  h('p',{class:'reason',dataset:{q5PopText:S.pop}},pv.text));
 if(official)return{el:head,official:true};
 const saved=Object.values(savedAll())[0]||null,st=M.boardState(S.pop,S.model,{officialLoaded:true,saved,selection:sel}),m=M.MODELS[S.model];
 const panel=h('div',{class:'sk state-card',dataset:{q5Board:st.state}},I.parts.mascot('plain'),h('b',null,M.POPULATIONS[S.pop].label,' × ',m.label),
  h('span',{class:'reason',dataset:{q5BoardText:''}},st.text),m.model_id?h('span',{class:'meta',dataset:{q5Ids:''}},'모형 ',m.model_id,' · ',M.KIND_TEXT[m.kind]):null);
 const kinds=S.pop==='top500'&&S.selections?group('Top500 합성 선정',...[['SYNTHETIC_COMPLETE','명부 근거 있음'],['SYNTHETIC_ROSTER_UNPROVEN','명부 근거 없음']].map(([k,l])=>
  chip('합성 · '+l,S.selKind===k,{dataset:{q5SelKind:k,k:'q5-sel-'+k},onclick:set(()=>{S.selKind=k;})}))):null;
 const lines=h('ul',{class:'news-lines',dataset:{q5PopLines:pv.state}},...pv.lines.map(t=>h('li',null,t)),
  h('li',{dataset:{q5Counts:''}},'산출 수 · 참조집단: 이 모집단의 결과 전달 전'),h('li',null,'시총 선정 순위와 QGV 순위는 다른 열 · QGV 순위는 결과 전달 뒤에만'));
 const stored=storedBlock(M,redraw);
 return{el:h('div',null,head,panel,kinds,lines,stored),official:false};}

/* ---- 2.1 보관 결과 읽기 (r2, private Worker; each step a click; each file's bytes checked against the staged manifest) */
const sha256=async b=>{const d=await crypto.subtle.digest('SHA-256',b);return[...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('');};
const codeOf=e=>String(e&&e.message||e||'').split(' ')[0];
function storedBlock(M,redraw){const scope=M.STORED_SCOPE[S.pop],key=S.model;if(!scope||!(key==='U1-555'||key==='S1-555'))return null;
 const T=S.stored[scope]||(S.stored[scope]={st:null,busy:false,err:null,rows:{},groups:null});
 const read=(e,list,then)=>{if(T.busy)return;T.busy=true;T.err=null;redraw();let p;try{p=I.prices.kisRead(e,list);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(then).catch(err=>{T.err=say(codeOf(err))+' · 이전 화면은 그대로';}).finally(()=>{T.busy=false;redraw();});};
 const btn=(k,label,on,dis)=>h('button',{type:'button',class:'btn',disabled:T.busy||!!dis,dataset:{k},onclick:on},label);
 const err=T.err?h('p',{class:'hand err',role:'alert',dataset:{q5StoredErr:''}},T.err):null;
 if(!T.st)return h('div',{class:'lb',dataset:{q5Stored:'IDLE'}},h('p',{class:'reason'},'보관 결과 · ',M.SCOPE_TEXT[scope],' · 계산 담당 실자료(r2) · 로그인한 비공개 영역에서만 · 이 화면에서 재계산 아님'),
  btn('q5-stored-load',T.busy?'불러오는 중 · 3개 · 요청 간격 5초':'보관 결과 불러오기',e=>read(e,[['classification','q555_stage/'+scope],['classification','q555_manifest/'+scope],['classification','q555_file/'+scope+'/index']],
   async([stage,manifest,index])=>{const st=await M.checkStored({stage:stage&&stage.body,manifest,index},{scope,sha256});T.st=st;T.rows={};T.groups=st.index.groups_layout==='SHARDED'?null:M.storedGroups(st,[]);})),err);
 const b=M.storedBoard(T.st,key),cov=b.coverage,st=M.stages(cov),rows=T.rows[key],n=b.files.length,next=rows?rows.i+1:0;
 const td=v=>h('td',null,v),th=t=>h('th',{scope:'col'},t);
 const table=rows?h('div',{class:'tbl-wrap'},h('table',{class:'tbl lb-tbl',dataset:{q5StoredTable:key}},h('caption',null,'보관 결과 묶음 '+(rows.i+1)+'/'+n+' · 생산자 순서 그대로 · 화면 재정렬 없음'),
  h('thead',null,h('tr',null,th('기업'),th('Q'),th('G'),th('V'),th('총점'),th('순위'),th('활성 역할'),th('15역할'),th('관문'))),
  h('tbody',null,...rows.list.map(r=>h('tr',{dataset:{q5StoredRow:r.company_id}},td([r.company_id,...r.flags.map(f=>h('span',{class:'chip',dataset:{q5Flag:f.code}},f.text))]),td(M.score(r.Q)),td(M.score(r.G)),td(M.score(r.V)),
   td(r.total===null?'없음':M.score(r.total)+(r.partial?' · 부분 합계(순위 제외)':' · 완전')),td(r.rank?r.rank+'/'+r.rank_n:'순위 없음'),
   td('Q'+r.active.Q+'/G'+r.active.G+'/V'+r.active.V),td(r.complete?'완결':'미완결'),td(M.GATE_TEXT[r.gate]||r.gate)))))):null;
 const scopes=T.groups?M.storedScopes(T.groups,key,S.storedModelRole):[],rs=scopes.includes(T.rankScope)?T.rankScope:scopes[0];
 const D=T.groups&&rs!==undefined?M.storedDeciles(T.groups,key,S.storedModelRole,rs):null;
 const scopeWord=x=>x==='COMMON'?'공통':scopeText(String(x).replace(/^SECTOR\|/,''));
 return h('div',{class:'lb',dataset:{q5Stored:'SHOWN'}},
  h('ul',{class:'news-lines',dataset:{q5StoredLines:''}},...b.lines.map(t=>h('li',null,t))),
  h('table',{class:'tbl',dataset:{q5StoredCoverage:key}},h('caption',null,'보관 결과 커버리지 · 발행사 수'),h('tbody',null,...st.map(x=>h('tr',null,h('th',{scope:'row'},x.label),td(String(x.value)))))),
  h('p',{class:'reason'},'완전 총점(15역할·세 축·관문)과 부분 합계는 따로 · 부분 합계는 순위·95% 분자에 넣지 않음'),
  btn('q5-stored-rows',rows?(next<n?'다음 묶음('+(next+1)+'/'+n+')':'마지막 묶음'):'기업 표 불러오기(1/'+n+')',e=>{const i=rows?next:0;
   read(e,[['classification','q555_file/'+scope+'/'+b.files[i].replace(/\.json$/,'')]],async([raw])=>{const d=await M.checkStoredFile(T.st,b.files[i].replace(/\.json$/,''),raw,sha256);T.rows[key]={i,list:M.storedRows(d)};});},rows&&next>=n),
  table,
  T.groups?h('div',{dataset:{q5StoredDeciles:key}},h('label',{class:'meta'},'역할 10분위 ',h('select',{dataset:{k:'q5-stored-role'},onchange:e=>{S.storedModelRole=e.target.value;redraw();}},
    ...Object.keys(M.ROLE_TEXT).map(r=>h('option',{value:r,selected:r===S.storedModelRole},M.roleText(r))))),
   scopes.length>1?h('label',{class:'meta'},' 순위 범위 ',h('select',{dataset:{k:'q5-stored-scope'},onchange:e=>{T.rankScope=e.target.value;redraw();}},
    ...scopes.map(x=>h('option',{value:x,selected:x===rs},scopeWord(x))))):null,
   D?h('div',{class:'scroll',role:'group','aria-label':'10분위'},...D.bands.map((c,i)=>h('span',{class:'chip',dataset:{q5StoredBand:String(i+1)}},'D'+(i+1)+' '+c))):h('p',{class:'meta'},'이 역할의 구간 없음'),
   D?h('p',{class:'meta'},'D10 = 상위 · 유효 '+D.valid+'/'+D.n+' · 범위 '+scopeWord(D.scope)+(scopes.length>1?' · 섹터별 순위 · 이어 붙인 통합 순위 아님':'')+' · 생산자 구간 그대로'):null)
   :btn('q5-stored-groups','역할 10분위 불러오기('+(T.st.index.group_files||[]).length+'개)',e=>{const names=T.st.index.group_files.map(f=>f.replace(/\.json$/,''));
    read(e,names.map(nm=>['classification','q555_file/'+scope+'/'+nm]),async(raws)=>{const parts=[];for(let i=0;i<names.length;i++)parts.push(await M.checkStoredFile(T.st,names[i],raws[i],sha256));T.groups=M.storedGroups(T.st,parts);});}),
  err);}

/* ---- 2.2.7 */
function fill(route,{body}){const signal=route.signal;
 const box=h('section',{class:'sq-555',dataset:{q5Block:''},'aria-label':'QGV 555 설정'});
 if(!body.parentNode||body.parentNode.querySelector('[data-q5-block]'))return;body.parentNode.appendChild(box);
 const focusKey=()=>{const a=document.activeElement;return a&&box.contains(a)&&a.dataset&&a.dataset.k?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const el=box.querySelector('[data-k="'+CSS.escape(k)+'"]');if(el&&!el.disabled)el.focus({preventScroll:true});};
 const paint=()=>{if(signal.aborted){listeners.delete(paint);return;}const k=focusKey();box.replaceChildren(...view().flat(Infinity).filter(Boolean));refocus(k);};
 listeners.add(paint);signal.addEventListener('abort',()=>listeners.delete(paint),{once:true});
 const key=()=>S.edit?JSON.stringify(S.edit):null;
 const act=fn=>()=>{try{fn();S.err=null;}catch(e){S.err=editText(e&&e.message);}if(S.preview&&S.preview.key!==key())S.preview=null;changed();};
 async function recalc(){const M=Q(),sv0=savedOf(S.edit.model_id),sv=sv0&&M.savedMatches(sv0,S.ctx.anchors)?sv0:null,before=sv?sv.configuration:S.ctx.configs[S.cand],k=key();
  const req={schema_version:REQ,op:'qgv555_preview',request_id:rid(),model_id:S.edit.model_id,config:S.edit,before_config:before,input_id:'SYNTHETIC_21',...(sv?{saved_before:sv}:{})};
  S.pendingId=req.request_id;S.current=req;S.msg=null;S.err=null;changed();let res=null;
  try{res=await I.data.engine(req,{signal});}catch(e){res={request_id:req.request_id,ok:false,code:e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE')};}
  if(signal.aborted)return;
  if(S.pendingId!==req.request_id||key()!==k){S.dropped++;changed();return;}
  S.pendingId=null;const a=M.previewAnswer(req,res,S.current,S.ctx.anchors);
  if(a.state!=='SHOWN'){S.err='재계산 거절 · '+say(a.code||a.state)+(S.preview?' · 이전 미리보기는 그대로':'');changed();return;}
  const pg=res.page;S.preview={key:k,res,id:res.preview_id,first:pg,cmp:M.compare(pg),rows:[...pg.rows],next:pg.next_offset,saved:!!sv};S.company=null;S.detail=null;S.dec=null;changed();
  void roleDeciles(S.decRole);}
 // The other requests of one shown preview (each answers for that preview only; an answer for an older one is dropped).
 const same=(pv,hash)=>S.preview===pv&&pv.key===key()&&(!hash||hash===pv.first.after_result_hash);
 async function morePage(){const pv=S.preview;if(!pv||pv.next===null)return;const{res}=await call('qgv555_page',{preview_id:pv.id,offset:pv.next},signal);if(signal.aborted)return;
  const a=Q().pageAnswer(pv.first,res,pv.rows.length);if(a.state==='PAGE_GAP'&&same(pv)){S.err=say('PAGE_GAP');changed();return;}if(a.state!=='SHOWN'||!same(pv)){S.dropped++;changed();return;}pv.rows.push(...res.page.rows);pv.next=res.page.next_offset;changed();}
 async function openDetail(id){const pv=S.preview;if(!pv)return;if(S.company===id){S.company=null;S.detail=null;changed();return;}S.company=id;S.detail=null;changed();
  const{res}=await call('qgv555_detail',{preview_id:pv.id,company_id:id},signal);if(signal.aborted)return;
  if(!res||res.ok!==true||!same(pv,res.after_result_hash)||res.model_id!==S.edit.model_id||S.company!==id){S.dropped++;changed();return;}S.detail=res.row;changed();}
 async function roleDeciles(role){const pv=S.preview;if(!pv)return;S.decRole=role;S.dec=null;changed();
  const{res}=await call('qgv555_role',{preview_id:pv.id,role},signal);if(signal.aborted)return;
  if(!res||res.ok!==true||!same(pv,res.after_result_hash)||res.role!==S.decRole){S.dropped++;changed();return;}S.dec=Q().deciles(res);changed();}
 // 저장: inside the click (the store's action gate), the engine's replay record that came with the shown preview of this exact setting.
 function save(e){const p=S.preview;if(!p||p.key!==key())return;const sv=p.res.saved;
  if(!sv||sv.result_hash!==p.first.after_result_hash||JSON.stringify(sv.configuration)!==JSON.stringify(S.edit)){S.err='저장하지 못함 · 엔진 기록이 보인 미리보기와 다름';changed();return;}
  try{I.store.qgv555.save(e,sv);S.msg='이 기기에 저장함 · '+S.cand+' · 결과 '+sv.result_hash.slice(0,12)+'… · 합성 입력';S.err=null;}catch(err){S.err='저장하지 못함 · '+String(err&&err.message);}changed();}
 async function replay(){const sv=savedOf(S.edit.model_id);if(!sv)return;S.replay={state:'PENDING'};changed();const{res}=await call('qgv555_replay',{saved:sv},signal);if(signal.aborted)return;
  S.replay=res&&res.ok===true?{state:res.reproduced?'REPRODUCED':'DIFFERENT',hash:res.result_hash}:{state:'REFUSED',code:res&&res.code};changed();}
 function view(){const M=Q();
  const head=[h('h3',{class:'stamp sub',tabindex:'-1'},'2.2.7 QGV 555 설정 · 5역할 · 내 설정'),
   h('p',{class:'hand'},'축마다 평가 역할 5개(기존 공식 15역할) · 한 역할 안의 여러 지표는 그 역할 몫을 나눔 · 333 후보 채택 아님 · 화면은 설정값만 다루고 점수·순위·비중은 엔진 답')];
  if(S.load!=='READY')return[head,h('div',{class:'sk state-card',dataset:{q5Load:S.load}},I.parts.mascot(S.load==='ERROR'?'alarm':'plain'),
   h('b',null,S.load==='ERROR'?'불러오지 못함':'555 계약 · 합성 입력'),h('span',{class:'reason'},S.load==='ERROR'?say(S.code):'계산 담당 요소 목록·기본 설정·회계모형 정의와 Top500 합성 선정 · 누를 때만 부름'),
   h('button',{type:'button',class:'btn',disabled:S.load==='LOADING',dataset:{k:'q5-load'},onclick:()=>{void load(signal);}},S.load==='LOADING'?'불러오는 중':'555 계약 불러오기'))];
  const ctx=S.ctx,c=S.edit,sc=S.scope,roles=M.rolesOf(c,sc),cnt=M.activeCount(c,sc),sums=M.sums(c,ctx,sc),probs=M.problems(c,ctx,sc);
  const pv=S.preview&&S.preview.key===key()?S.preview:null,row=pv?(pv.rows.find(r=>r.after&&r.after.weights&&r.after.weights.length)||null):null;
  const editable=(ctx.recipes[M.templateOf(sc)]||{}).state==='DEFINED_GENERAL';
  const models=group('555 모형',...['U1-555','S1-555'].map(k=>chip(M.MODELS[k].label,S.cand===k,{dataset:{q5M2:k,k:'q5-m2-'+k},
   onclick:act(()=>pick(k,k==='U1-555'?'COMMON':M.scopes(ctx,'S1-555').find(x=>x.state==='DEFINED_GENERAL').scope))})));
  const scopeSel=S.cand==='S1-555'?h('label',{class:'meta'},'섹터·회계모형 ',h('select',{dataset:{k:'q5-scope'},onchange:e=>act(()=>{S.scope=e.target.value;S.preview=null;S.company=null;})()},
   ...M.scopes(ctx,'S1-555').map(x=>h('option',{value:x.scope,selected:x.scope===sc},scopeText(x.scope)+(x.state==='DEFINED_GENERAL'?'':' · 준비 중'))))):null;
  const sv=savedOf(c.model_id);
  const base=h('p',{class:'meta',dataset:{q5Base:''}},'원본 참조 ',c.candidate,' 기본 설정 ',c.version,' · ',scopeText(sc),' · ',M.KIND_TEXT[M.MODELS[S.cand].kind],' · ',M.recipeLine(ctx,sc),
   ' · 다른 섹터·회계모형으로 자동 복사하지 않음',sv?' · 내 설정 저장됨(결과 '+sv.result_hash.slice(0,12)+'…)'+(S.savedStale?' · 저장 때 입력과 지금 입력이 다름 · 설정만 불러옴, 재현 대상 아님':''):'');
  const axes=h('div',{class:'scroll',role:'group','aria-label':'축 비중',dataset:{q5Axes:''}},...M.AXES.map(a=>h('label',{class:'chip'},a+' ',
   num(a+' 축 비중',sums.axes[a],'q5-axis-'+a,v=>act(()=>{S.edit=M.setAxis(S.edit,ctx,sc,a,v);})(),{disabled:!editable}))),
   h('span',{class:'meta'},'합 ',String(sums.axis),' · 엔진이 합에 대한 비율로 씀'+(S.cand==='S1-555'?' · 이 섹터의 축 비중만 바뀜':'')));
  const tabs=group('축',...M.AXES.map(a=>chip(a+' · 활성 '+cnt[a]+'/5',S.axis===a,{dataset:{q5Tab:a,k:'q5-tab-'+a},onclick:act(()=>{S.axis=a;S.addRole=null;})})));
  const roleIds=Object.keys(roles).filter(r=>roles[r].axis===S.axis);
  const roleBlocks=roleIds.map(r=>roleBlock(M,ctx,c,sc,r,roles[r],row,editable));
  const problems=probs.length?h('ul',{class:'news-lines',dataset:{q5Problems:String(probs.length)}},...probs.map(p=>h('li',{class:'hand err'},PROB[p.code]||p.code,' · ',p.where))):
   h('p',{class:'meta',dataset:{q5Problems:'0'}},'설정 합계 이상 없음 · 엔진 검사는 재계산 때');
  const fam=M.families(ctx,c,sc,row);
  const overlap=h('details',{class:'why',dataset:{q5Overlap:String(fam.length)}},h('summary',null,'정보 중복 · 같은 원입력 계열 '+fam.length+'개 ▸'),
   h('p',{class:'reason'},'같은 원입력을 여러 지표·역할·축에서 읽음 · 감점·숨은 비중 조정 없음 · 노출 비중은 미리보기 뒤 엔진 답'),
   h('ul',{class:'news-lines'},...fam.map(f=>h('li',{dataset:{q5Family:f.family}},h('b',null,f.family),' · ',f.roles.map(M.roleText).join(', '),' · ',f.cross_axis?'축을 넘음 · ':'',
    f.nominal===null?'노출 비중 미리보기 전':'명목 '+M.pct(f.nominal)+' · 실효 '+M.pct(f.effective)+'(첫 기업)'))));
  const pend=S.pendingId!==null;
  const run=h('div',{class:'conn',dataset:{q5Run:''}},h('span',{class:'chip',dataset:{q5Active:cnt.text}},'활성 역할 ',cnt.text),
   h('button',{type:'button',class:'btn mine',disabled:pend||probs.length>0||!editable,dataset:{k:'q5-recalc'},onclick:()=>{void recalc();}},pend?'재계산 요청 중':'실제 재계산'),
   h('button',{type:'button',class:'btn',disabled:!pv,title:'보이는 미리보기가 지금 설정의 것일 때만',dataset:{k:'q5-save'},onclick:e=>save(e)},'저장'),
   h('button',{type:'button',class:'btn',dataset:{k:'q5-cancel'},onclick:act(()=>{const s=savedOf(c.model_id);S.edit=s?Object.freeze(JSON.parse(JSON.stringify(s.configuration))):M.start(ctx,S.cand);S.msg='변경 취소 · '+(s?'저장한 설정':'기본 설정');})},'변경 취소'),
   h('button',{type:'button',class:'btn',dataset:{k:'q5-restore'},onclick:act(()=>{S.edit=M.restore(ctx,S.edit);S.msg='기본값 복원 · '+S.edit.candidate+' 기본 설정 '+S.edit.version;})},'기본값 복원'),
   S.cand==='S1-555'?h('button',{type:'button',class:'btn',dataset:{k:'q5-restore-scope'},onclick:act(()=>{S.edit=M.restoreScope(S.edit,sc);S.msg='이 범위 되돌리기 · '+scopeText(sc);})},'이 범위 되돌리기'):null,
   sv?h('button',{type:'button',class:'btn',disabled:(S.replay&&S.replay.state==='PENDING')||S.savedStale,dataset:{k:'q5-replay'},onclick:()=>{void replay();}},'저장 설정 재현'):null);
  const msg=S.err?h('p',{class:'hand err',role:'alert',dataset:{q5Err:''}},S.err):S.msg?h('p',{class:'hand',dataset:{q5Msg:''}},S.msg):null;
  const rp=S.replay?h('p',{class:S.replay.state==='REPRODUCED'?'hand':'hand err',dataset:{q5Replay:S.replay.state}},{PENDING:'재현 요청 중',REPRODUCED:'재현됨 · 저장 결과와 같은 결과 해시 '+(S.replay.hash||'').slice(0,12)+'…',
   DIFFERENT:'재현 안 됨 · 결과 해시가 다름',REFUSED:'재현 거절 · '+say(S.replay.code)}[S.replay.state]):null;
  return[head,models,scopeSel,base,axes,tabs,h('div',{dataset:{q5Roles:S.axis}},...roleBlocks),problems,overlap,run,msg,rp,previewBlock(M,pv,pend)];}
 function roleBlock(M,ctx,c,sc,r,x,row,editable){const on=x.weight>0;const R=M.ROLE_TEXT[r]||[r,''];
  const rows=Object.entries(x.metrics).map(([m,w])=>{const k=M.card(ctx,m,c,sc,r,row);if(!k)return h('li',null,m);
   return h('li',{dataset:{q5Factor:m}},h('b',null,k.name),' ',h('span',{class:'meta'},k.formula),' ',
    h('label',{class:'meta'},'역할 안 비중 ',num(k.name+' 역할 안 비중',w,'q5-share-'+m,v=>act(()=>{S.edit=M.setMetric(S.edit,sc,r,m,v);})(),{disabled:!editable})),' ',
    h('button',{type:'button',class:'lk',disabled:!editable,dataset:{k:'q5-rm-'+m},onclick:act(()=>{S.edit=M.removeMetric(S.edit,sc,r,m);})},'빼기'),
    h('div',{class:'meta'},k.weights),h('div',{class:'meta'},'원입력 계열 ',k.family));});
  const adding=S.addRole===r;
  return h('div',{class:'lb',dataset:{q5Role:r,q5RoleOn:String(on)}},
   h('div',{class:'lb-head'},h('b',null,R[0]),h('span',{class:'meta'},R[1]),
    h('label',{class:'meta'},'역할 비중 ',num(R[0]+' 역할 비중',x.weight,'q5-role-'+r,v=>act(()=>{S.edit=M.setRole(S.edit,sc,r,v);})(),{disabled:!editable})),
    h('span',{class:'meta'},on?'활성':'제외(비중 0)'),
    on&&editable?h('button',{type:'button',class:'lk',dataset:{k:'q5-ex-'+r},onclick:act(()=>{S.edit=M.excludeRole(S.edit,sc,r);})},'역할 제외'):null),
   h('ul',{class:'news-lines'},...rows),
   editable?h('button',{type:'button',class:'btn',dataset:{k:'q5-add-'+r},'aria-expanded':String(adding),onclick:act(()=>{S.addRole=adding?null:r;S.query='';})},adding?'지표 목록 닫기':'지표 추가·교체'):null,
   adding?cards(M,ctx,c,sc,r,row):null);}
 function cards(M,ctx,c,sc,r,row){const axis=M.rolesOf(c,sc)[r].axis,chosen=Object.keys(M.rolesOf(c,sc)[r].metrics),q=S.query.trim(),hit=q?new Set(M.search(ctx,q)):null;
  const list=Object.values(ctx.catalog).filter(e=>e.axis===axis&&(!hit||hit.has(e.canonical_id)));
  return h('div',{dataset:{q5Cards:r}},h('label',{class:'meta'},'찾기 ',h('input',{type:'search',value:S.query,'aria-label':'지표 이름·별칭 찾기',dataset:{k:'q5-q'},oninput:e=>{S.query=e.target.value;changed();}})),
   h('p',{class:'meta'},'이 축의 지표 '+list.length+'개 · 다른 역할의 기본 지표도 적합하면 고를 수 있음'),
   h('ul',{class:'news-lines'},...list.map(e=>{const k=M.card(ctx,e.canonical_id,c,sc,r,row),sel=chosen.includes(e.canonical_id);
    return h('li',{dataset:{q5Card:e.canonical_id,q5Selectable:String(k.selectable&&!sel)}},h('b',null,k.name),' ',...k.badges.map(t=>h('span',{class:'tag'},t)),
     h('div',{class:'meta',dataset:{q5Assign:k.roles.length?'DEFAULT':'UNASSIGNED'}},k.assignment,' · ',k.formula,' · 적용 ',k.templates),
     h('div',{class:'meta'},k.status,' · ',k.recommendation,' · 원입력 계열 ',k.family),
     k.aliases.length?h('div',{class:'meta'},'별칭 ',k.aliases.join(', '),' (같은 지표로 한 번만)'):null,
     h('details',{class:'why'},h('summary',null,'근거 ▸'),h('p',{class:'meta'},k.evidence)),
     k.why?h('div',{class:'meta',dataset:{q5Why:k.why}},editText(k.why),k.alternatives.length?' · 대안 '+k.alternatives.join(' · '):''):null,
     !sel&&!k.why?h('span',null,h('button',{type:'button',class:'lk',dataset:{k:'q5-pick-'+e.canonical_id},onclick:act(()=>{S.edit=M.addMetric(ctx,S.edit,S.scope,r,e.canonical_id);})},'추가(역할 몫 나눔)'),
      ...chosen.map(v=>[' ',h('button',{type:'button',class:'lk',dataset:{k:'q5-swap-'+v+'-'+e.canonical_id},onclick:act(()=>{S.edit=M.replaceMetric(ctx,S.edit,S.scope,r,v,e.canonical_id);})},(ctx.catalog[M.canonical(ctx,v)]||{display_name:v}).display_name+' 대신')])):null);})));}
 function previewBlock(M,pv,pend){
  if(!pv)return h('div',{class:'sk state-card',role:'status',dataset:{q5Preview:pend?'PENDING':'NONE'}},h('b',null,'전후 미리보기'),
   h('span',{class:'reason'},pend?'요청 중 · 끝나기 전 답은 보이지 않음':'재계산 전 · 같은 입력에서 엔진이 계산한 전후만 보임 · 이전 결과를 새 설정 이름으로 보이지 않음'),
   S.dropped?h('span',{class:'meta',dataset:{q5Dropped:String(S.dropped)}},'버린 늦은 답 ',String(S.dropped)):null);
  const C=pv.cmp,cov=M.stages(C.coverage.after),covB=M.stages(C.coverage.before);
  const th=(t,sub)=>h('th',{scope:'col'},t,sub?h('small',{class:'sub'},sub):null),td=v=>h('td',null,v);
  const ax=(r,a)=>{const x=r.axes[a];return M.score(x.after)+(x.transition&&M.TRANSITION[x.transition]?' · '+M.TRANSITION[x.transition]:'');};
  const rows=pv.rows.map(x=>h('tr',{dataset:{q5Row:x.company_id}},
   h('td',null,h('button',{type:'button',class:'lk','aria-expanded':String(S.company===x.company_id),dataset:{k:'q5-co-'+x.company_id},onclick:()=>{void openDetail(x.company_id);}},x.company_id)),
   td(M.score(x.before.total)+(x.before.rank?' · '+x.before.rank+'위':'')),td(ax(x,'Q')),td(ax(x,'G')),td(ax(x,'V')),
   td(M.score(x.after.total)+(x.after.partial_total?' 부분':'')),td(x.after.rank?x.after.rank+'위':'순위 없음'),
   td('Q'+x.after.active_roles.Q+'/G'+x.after.active_roles.G+'/V'+x.after.active_roles.V)));
  const roleIds=Object.keys(S.edit.roles),D=S.dec;
  return h('div',{class:'lb',dataset:{q5Preview:'SHOWN'}},
   h('div',{class:'lb-head'},h('b',null,'전후 미리보기 · 엔진 답'),h('span',{class:'meta',dataset:{q5RecalcKind:'SYNTHETIC'}},'합성 입력 재계산 · 실자료 재계산 아님 · ',pv.res.input_id)),
   h('p',{class:'reason',dataset:{q5PopEffect:C.population}},C.scope==='SETTINGS_ONLY_FIXED_INPUT_AND_POPULATIONS'?'설정 효과만 · 같은 평가·참조 입력과 모집단 고정 · 모집단 효과는 이 비교에서 평가하지 않음(별도 비교)':'비교 범위 '+C.scope),
   h('p',{class:'meta',dataset:{q5BeforeSource:pv.res.before_source}},pv.res.before_source==='SAVED_REPLAYED'?'전 = 저장한 내 설정을 같은 입력으로 다시 계산한 결과(저장 결과 해시와 같음)':'전 = 비교 기준 설정을 같은 입력으로 계산'),
   h('p',{class:'meta',dataset:{q5Versions:''}},'평가 입력 ',C.versions.evaluation.slice(0,10),'… · 참조 입력 ',C.versions.reference.slice(0,10),'… · 분류 ',C.versions.classification,
    ' · 결과 전 ',C.versions.before.slice(0,10),'… → 후 ',C.versions.after.slice(0,10),'… · 계산 ',C.versions.calculated_at),
   h('table',{class:'tbl',dataset:{q5Coverage:'SHOWN'}},h('caption',null,'커버리지 단계 · 발행사 수 · 전 → 후'),
    h('tbody',null,...cov.map((st,i)=>h('tr',null,h('th',{scope:'row'},st.label),td(String(covB[i].value)+' → '+String(st.value)))))),
   h('div',{class:'tbl-wrap'},h('table',{class:'tbl lb-tbl',dataset:{q5Table:''}},h('caption',null,'기업 '+pv.rows.length+'/'+C.row_count+' · 전 총점 → 후 축·총점·순위 · 엔진 순서 그대로'),
    h('thead',null,h('tr',null,th('기업'),th('전 총점'),th('Q'),th('G'),th('V'),th('총점'),th('순위',M.KIND_TEXT[M.MODELS[S.cand].kind].split(' · ')[0]),th('활성 역할'))),h('tbody',null,...rows))),
   pv.next!==null?h('button',{type:'button',class:'btn',dataset:{k:'q5-more'},onclick:()=>{void morePage();}},'다음 기업 보기('+pv.rows.length+'/'+C.row_count+')'):null,
   S.company?detailBlock(M,S.company):null,
   h('div',{dataset:{q5Deciles:S.decRole,q5DecState:D?'SHOWN':'PENDING'}},h('label',{class:'meta'},'역할 10분위 ',h('select',{dataset:{k:'q5-dec-role'},onchange:e=>{void roleDeciles(e.target.value);}},
     ...roleIds.map(r=>h('option',{value:r,selected:r===S.decRole},M.roleText(r))))),
    D?h('div',{class:'scroll',role:'group','aria-label':'10분위'},...D.bands.map((n,i)=>h('span',{class:'chip',dataset:{q5Band:String(i+1)}},'D'+(i+1)+' '+n))):h('p',{class:'meta'},'구간 불러오는 중'),
    D?h('p',{class:'meta'},'D10 = 상위 · 유효 '+D.valid+'/'+D.n+' · 구간 밖 '+D.other+' · 상위 20개로 대신하지 않음 · 동점은 엔진의 저장 순서 규칙'):null));}
 function detailBlock(M,id){const pr=S.preview.rows.find(r=>r.company_id===id),d=S.detail?M.detail(S.detail,pr):null;
  if(!d)return h('p',{class:'meta',dataset:{q5Detail:'PENDING'}},id,' 상세 불러오는 중');
  const metricLine=m=>h('li',null,m.metric,m.substitute_for?h('span',{class:'chip',dataset:{q5Flag:'SUBSTITUTE_METRIC'}},'대체 지표 · '+m.substitute_for+' 대신'):'',...m.flags.map(f=>h('span',{class:'chip',dataset:{q5Flag:f.code}},f.text)),' ',M.score(m.score),' · ',m.reason?(M.REASON_TEXT[m.reason]||m.reason):'참조 '+m.reference_n,' · 설정 '+m.weight,
   m.w?' · 명목 '+M.pct(m.w.nominal)+' · 결측 재배분 뒤 '+M.pct(m.w.missing_redistributed_before_gate)+' · 관문 뒤 '+M.pct(m.w.after_gate):'');
  const roleLine=r=>h('li',{dataset:{q5DetailRole:r.role}},h('b',null,r.name),' ',M.score(r.score),r.decile_status==='VALID'?' · D'+r.decile:'',r.selected?'':' · 제외',r.partial?' · 일부 지표만':'',
   h('ul',null,...r.metrics.map(metricLine)));
  const axisBox=x=>h('details',{class:'why',open:x.axis===S.axis},h('summary',null,x.axis,' ',M.score(x.score),' ▸'),h('ul',{class:'news-lines'},...x.roles.map(roleLine)));
  return h('div',{class:'lb',dataset:{q5Detail:id}},
   h('div',{class:'lb-head'},h('b',null,id),...d.flags.map(f=>h('span',{class:'chip',dataset:{q5Flag:f.code}},f.text)),h('span',{class:'meta'},'총점 ',M.score(d.total),d.partial?' 부분 합계':'',' · ',M.GATE_TEXT[d.gate]||d.gate,d.complete?' · 15역할 모두':'',' · 활성 Q',d.active.Q,'/G',d.active.G,'/V',d.active.V)),
   ...d.axes.map(axisBox));}
 changed();}
function subscribe(fn,signal){listeners.add(fn);if(signal)signal.addEventListener('abort',()=>listeners.delete(fn),{once:true});}
const isOfficial=()=>S.pop==='universe504'&&S.model==='OFFICIAL';
I.qgv555Live=Object.freeze({selector,fill,subscribe,isOfficial,state:()=>S});
})();
