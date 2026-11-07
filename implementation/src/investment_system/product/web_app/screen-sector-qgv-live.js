/* 1. QGV · 1.2 가중치 · QGV 구성 — sector QGV factor choice and recalculation on Codex's common engine (feature 2.2.1–2.2.7;
   owner 2026-11-06 「섹터별 QGV 요소 선택·재계산」 and 「섹터 QGV 실제 연결」; engine #505 `research/sector_qgv`).
   screen-qgv.js gives this file the 1.2 section body; it fills it after IS2.ready.
   - Nothing is sent when the page opens: 「계산 엔진 연결」 (a click) asks the engine route for its context (versions, default
     config, sectors, templates, gate policy, synthetic inputs). Every later request is a click too: a scope change asks the
     engine for that scope's preset and factor list (list_factors), 「결과 미리보기」 runs preview_qgv on the edited config and on
     the saved (or default) config and compare_previews on the two, and returns the engine's save_user_config record for it.
   - The screen edits settings only (IS2.sectorQgv: axis / role / factor basis points, add / remove / replace, scope). Defaults,
     badges' facts, validation, scores, strict missing, the official-Q gate (관문 통과 · V 제외 · 판정 불가), totals, ranks and
     coverage are the engine's answer, shown as it is; 판정 불가 has no final score and no rank here either.
   - Only the latest request's answer is shown: an answer whose request_id is not the active one, or whose config / input is not
     the current one, is dropped (counted in data-sq-dropped). A refused preview never replaces the last good one, and a preview
     of another config is hidden as stale.
   - 저장 stores the engine's save_user_config record of the shown, current preview on this device only (IS2.store.sectorQgv: no
     account sync, not in a backup). A newer engine default never rewrites it. 변경 취소 returns to the saved (or default)
     config; 기본값 복원 drops this scope's override (stored only after the next preview and 저장).
   - Q/G 부분 비교 (#505 7c2225a3, sector-qgv-axis-comparison/1; screen-sector-qgv-axis-live.js): every preview answer carries
     Codex's compare_axes of the same two previews, drawn under the preview; 「비교 파일 목록」 (a click) lists the engine's comparison
     files (Codex's synthetic D1; retained private D1 / I1 only on a development process started with them) and one opens on a click.
   - Inputs are SYNTHETIC (Codex's synthetic fixture and its named states); the published site has no engine route and says so.
   View state lives in RAM for this page load. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const X=()=>I.sectorQgv;
const V={viewLoading:false,conn:'IDLE',code:null,ctx:null,sector:'INFORMATION_TECHNOLOGY',template:'GENERAL',input:'NORMAL',saved:null,savedState:'EMPTY',work:null,
 view:null,viewId:null,edit:null,cmp:{state:'IDLE',list:null,code:null,name:null,el:null,pending:null},axis:'Q',scope:'CONTEXT',adv:false,query:'',only:true,shown:null,pendingId:null,dropped:0,msg:null,err:null,coverage:null};
let NF=null;const fmt=v=>(NF||(NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}))).format(v);
const pct=bp=>fmt(bp/100)+'%';
const copy=v=>JSON.parse(JSON.stringify(v));

function fill(route,{body}){
 const signal=route.signal,S=X();
 const focusKey=()=>{const a=document.activeElement;return a&&body.contains(a)&&a.dataset&&a.dataset.k?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const el=body.querySelector('[data-k="'+CSS.escape(k)+'"]');if(el&&!el.disabled)el.focus({preventScroll:true});};
 const card=(state,words,why,alert,...more)=>h('div',{class:'sk state-card',role:alert?'alert':null,dataset:{sqState:state}},I.parts.mascot(alert?'alarm':'plain'),h('b',null,words),why?h('span',{class:'reason'},why):null,...more);
 const draw=()=>{if(!signal.aborted)paint();};
 // One engine request; never throws: {req, res, chk}.
 async function call(op,fields){const req=S.request(op,fields);let res=null;
  try{res=await I.data.engine(req,{signal});}catch(e){return {req,res:null,chk:{ok:false,code:e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE')}};}
  return {req,res,chk:S.check(op,req,res,V.ctx)};}
 const factorsBy=()=>new Map((V.view?V.view.factors:[]).map(f=>[f.variant_id,f]));
 const scopes=()=>V.ctx.sectors.flatMap(s=>V.ctx.templates.map(t=>({sector_id:s.sector_id,accounting_template:t})));
 function current(){if(!V.edit)return null;const r=V.scope==='ALL'?S.applyAll(V.work,V.edit,scopes(),V.view.factors):{config:S.withScope(V.work,V.edit),applied:[S.scopeKey(V.sector,V.template)],skipped:[]};
  return {...r,key:JSON.stringify(r.config)+'|'+V.input};}
 const dirty=()=>V.view&&JSON.stringify(V.edit)!==JSON.stringify(V.view.preset);

 // ---- engine steps (each started by a click)
 async function connect(){V.conn='CONNECTING';V.code=null;draw();const{res,chk}=await call('context');
  if(!chk.ok){V.conn=signal.aborted?'IDLE':'ERROR';V.code=chk.code;draw();return;}
  V.ctx=res;V.conn='READY';readSaved();V.work=V.savedState==='OK'?copy(V.saved.config):copy(res.default_config);if(!res.inputs.some(x=>x.input_id===V.input))V.input=res.inputs[0].input_id;
  if(signal.aborted)return;await loadView();}
 function readSaved(){const st=I.store.sectorQgv.read();V.saved=null;V.savedState=st.state;
  if(st.state==='OK'){V.saved=copy(st.value);if(st.value.config.base_preset_id!==V.ctx.versions.model_version)V.savedState='BASE_DIFFERS';}}
 async function loadView(){const req=S.request('view',{config:V.work,sector_id:V.sector,accounting_template:V.template});V.viewId=req.request_id;V.viewLoading=true;draw();
  let res=null,chk;try{res=await I.data.engine(req,{signal});chk=S.check('view',req,res,V.ctx);}catch(e){chk={ok:false,code:String(e&&e.message||'ENGINE_UNREACHABLE')};}
  if(req.request_id!==V.viewId){V.dropped++;draw();return;}// a later scope's request is the current one
  V.viewLoading=false;if(signal.aborted)return;// left the screen: the next visit offers 다시 불러오기 (a click)
  if(!chk.ok){V.err=S.errorText(chk.code);draw();return;}
  V.view=res;V.edit=copy(res.preset);V.err=null;draw();}
 async function preview(){const cur=current();if(!cur)return;
  const before=V.savedState==='OK'?V.saved.config:V.ctx.default_config,fields={config:cur.config,before_config:before,input_id:V.input};
  const req0=S.request('preview',fields);V.pendingId=req0.request_id;V.msg=null;V.err=null;draw();
  let res=null,chk;try{res=await I.data.engine(req0,{signal});chk=S.check('preview',req0,res,V.ctx);}catch(e){chk={ok:false,code:String(e&&e.message||'ENGINE_UNREACHABLE')};}
  if(signal.aborted){if(V.pendingId===req0.request_id)V.pendingId=null;return;}
  const now=current();if(req0.request_id!==V.pendingId||!now||now.key!==cur.key){if(req0.request_id===V.pendingId)V.pendingId=null;V.dropped++;draw();return;}// an older answer, or one for another edit
  V.pendingId=null;if(!chk.ok){V.err='미리보기 거부 · '+S.errorText(chk.code)+' · 이전 결과는 그대로';draw();return;}
  V.shown={key:cur.key,config:cur.config,res,skipped:cur.skipped,input:V.input};V.coverage=res.after.coverage;draw();}
 function save(e){const cur=current(),sh=V.shown;if(!sh||!cur||sh.key!==cur.key||sh.res.saved.refused)return;
  try{I.store.sectorQgv.save(e,sh.res.saved);V.saved=copy(sh.res.saved);V.savedState='OK';V.work=copy(sh.res.saved.config);V.err=null;
   V.msg='이 기기에 저장함 · 엔진 저장 기록 · 미리보기 '+sh.res.saved.preview_id.slice(0,12)+' · 설정 '+sh.res.saved.canonical_config_hash.slice(0,12);}
  catch(err){V.err='저장하지 못함 · '+String(err&&err.message);}draw();}
 function keepEdit(){if(dirty())V.work=S.withScope(V.work,V.edit);}
 // Comparison files (each step a click): the list, then one comparison by its listed name.
 async function listComparisons(){V.cmp.state='LOADING';V.cmp.code=null;draw();const{res,chk}=await call('comparisons');if(signal.aborted)return;
  if(!chk.ok){V.cmp.state='ERROR';V.cmp.code=chk.code;draw();return;}V.cmp.state='READY';V.cmp.list=res.comparisons;draw();}
 async function openComparison(name){V.cmp.pending=name;V.cmp.code=null;draw();const{req,res,chk}=await call('comparison',{name});if(signal.aborted)return;
  if(V.cmp.pending!==req.name){V.dropped++;draw();return;}V.cmp.pending=null;
  if(!chk.ok){V.cmp.code=chk.code;draw();return;}V.cmp.code=null;V.cmp.name=name;V.cmp.el=I.sectorQgvAxisLive.render(res.comparison,{kind:res.data_kind,name});draw();}
 function comparisonsBlock(){const C=V.cmp;
  const intro=h('p',{class:'reason'},'저장된 Q/G 부분 비교 파일 · 엔진이 만든 비교를 그대로 읽음 · 합성 예시(D1) · 비공개 실자료(D1 요소·비중, I1 분류 보완)는 승인된 개발 환경에서만');
  if(C.state==='IDLE'||C.state==='ERROR'||C.state==='LOADING')return h('section',{class:'sq-axis-files',dataset:{sqAxisFiles:C.state}},intro,
   C.state==='ERROR'?h('p',{class:'hand err'},S.errorText(C.code)):null,
   h('button',{type:'button',class:'btn',disabled:C.state==='LOADING',dataset:{k:'sq-axis-list'},onclick:()=>{void listComparisons();}},C.state==='LOADING'?'불러오는 중…':'비교 파일 목록'));
  return h('section',{class:'sq-axis-files',dataset:{sqAxisFiles:'READY'}},intro,
   h('div',{class:'links',role:'group','aria-label':'비교 파일'},...C.list.map(x=>h('button',{type:'button',class:'btn'+(C.name===x.name?' solid':''),'aria-pressed':String(C.name===x.name),
    dataset:{k:'sq-axis-open-'+x.name,sqAxisFile:x.name,sqAxisFileKind:x.data_kind},onclick:()=>{void openComparison(x.name);}},
    x.comparison_id,' · ',x.data_kind==='PRIVATE'?'비공개 실자료':'합성',' · ',I.sectorQgvAxis.text(I.sectorQgvAxis.TREATMENT_TEXT,x.treatment).split(' (')[0],' · ',x.valuation_date))),
   C.pending?h('p',{class:'pending',role:'status'},'비교 불러오는 중'):null,C.code?h('p',{class:'hand err',dataset:{sqAxisFileCode:C.code}},S.errorText(C.code)):null,C.el);}

 function paint(){
  const k=focusKey();
  if(V.conn==='IDLE'||V.conn==='CONNECTING'||V.conn==='ERROR'){
   const btn=h('button',{type:'button',class:'btn solid',disabled:V.conn==='CONNECTING',dataset:{k:'sq-connect'},onclick:()=>{void connect();}},V.conn==='CONNECTING'?'연결 중…':V.conn==='ERROR'?'다시 연결':'계산 엔진 연결');
   body.replaceChildren(V.conn==='ERROR'?card('ERROR',S.errorText(V.code),'공식 QGV(1.1 리더보드)는 그대로',true):card('IDLE','계산 엔진 연결 전','누를 때만 계산 엔진에 요청 · 화면은 점수를 계산하지 않음'),btn,
    h('p',{class:'hand'},'연결하면: 섹터·회계모형 → Q/G/V 비중 → 요소 교체·추가 → 결과 미리보기(공통 엔진 재계산) → 내 설정으로 저장 · 변경 취소 · 기본값 복원'),
    h('p',{class:'reason'},'계산: Codex 공통 엔진 sector_qgv · 입력은 합성 자료만 · 공식 QGV·순위·TARGET은 바뀌지 않음'));
   if(V.conn==='ERROR')body.dataset.sqCode=V.code;else delete body.dataset.sqCode;refocus(k);return;}
  delete body.dataset.sqCode;
  const c=V.ctx,vs=c.versions;
  const status=h('p',{class:'sk status-line',dataset:{sqEngine:vs.engine_version}},'모델 ',vs.model_version,' · 엔진 ',vs.engine_version,' · 정규화 ',vs.normalization_version,' · 분류 ',vs.mapping_version,' · 계산 Codex 공통 엔진');
  const gate=h('p',{class:'reason',dataset:{sqGatePolicy:c.gate.policy}},'관문 ',c.gate.policy,' · 공식 Q 업종 분위 ',String(c.gate.value_excluded_at_or_below),' 이하이면 V 제외 · 공식 분위가 없으면 판정 불가(최종 점수·순위 없음) · 관문은 엔진이 판정');
  const store=h('p',{class:'reason',dataset:{sqStorage:'DEVICE'}},'내 설정은 이 기기(이 브라우저)에만 저장 · 다른 기기와 동기화 안 됨 · 백업 파일에 들어가지 않음');
  const initial=h('p',{class:'reason',dataset:{sqInitial:''}},'기본값 · 초기 설정 = 비교검증으로 조정할 시작값 · 성과 검증 완료가 아님 · 기업 유형 태그는 점수에 영향 없음 · 공식 QGV(1.1)는 그대로');
  const notes=[];
  if(V.savedState==='BASE_DIFFERS')notes.push(h('p',{class:'hand err',dataset:{sqSaved:'BASE_DIFFERS'}},'저장한 설정의 기준('+V.saved.config.base_preset_id+')이 지금 엔진 기본값('+vs.model_version+')과 다름 · 자동으로 바꾸지 않음 · 지금은 기본값으로 편집'));
  if(V.savedState==='INVALID')notes.push(h('p',{class:'hand err',dataset:{sqSaved:'INVALID'}},'이 기기의 저장 설정을 읽을 수 없음 · 덮어쓰지 않음',
   h('button',{type:'button',class:'btn',dataset:{k:'sq-clear-bad'},onclick:e=>{try{I.store.sectorQgv.clear(e);V.savedState='EMPTY';V.saved=null;}catch(_){V.err='지우지 못함';}draw();}},'저장 설정 지우기')));
  if(V.savedState==='OK')notes.push(h('p',{class:'reason',dataset:{sqSaved:'OK'}},'저장된 내 설정 · 미리보기 ',V.saved.preview_id.slice(0,12),' · 스냅숏 ',V.saved.snapshot_id,' · 설정 ',V.saved.canonical_config_hash.slice(0,12)));
  const sel=(idk,label,opts,cur,on)=>h('div',{class:'sort-row'},h('label',{for:idk},label),h('select',{id:idk,dataset:{k:idk},onchange:on},...opts.map(([val,t])=>h('option',{value:val,selected:val===cur},t))));
  const ctxRow=h('div',{class:'sq-ctx'},
   sel('sq-sector','섹터(책 10섹터)',c.sectors.map(s=>[s.sector_id,S.text(S.SECTOR_TEXT,s.sector_id)]),V.sector,e=>{keepEdit();V.sector=e.target.value;V.view=null;V.edit=null;draw();void loadView();}),
   sel('sq-template','회계모형',c.templates.map(t=>[t,S.text(S.TEMPLATE_TEXT,t)]),V.template,e=>{keepEdit();V.template=e.target.value;V.view=null;V.edit=null;draw();void loadView();}),
   sel('sq-input','입력(합성)',c.inputs.map(x=>[x.input_id,x.label]),V.input,e=>{V.input=e.target.value;draw();}));
  if(!V.view||!V.edit){body.replaceChildren(...[status,gate,store,initial,...notes,ctxRow,V.err?h('p',{class:'hand err',role:'alert',dataset:{sqErr:''}},V.err):V.viewLoading?h('p',{class:'pending',role:'status',dataset:{sqState:'VIEW_LOADING'}},'요소 목록 불러오는 중'):null,
   V.viewLoading?null:h('button',{type:'button',class:'btn',dataset:{k:'sq-reload-view'},onclick:()=>{void loadView();}},'요소 목록 다시 불러오기')].filter(Boolean));refocus(k);return;}
  const p=V.edit,F=factorsBy(),sm=S.sums(p);
  const num=(idk,label,valueBp,on)=>h('input',{type:'number',min:'0',max:'100',step:'0.01',inputmode:'decimal',value:String(valueBp/100),dataset:{k:idk},'aria-label':label,
   onchange:e=>{const n=Math.round(Number(e.target.value)*100);if(!Number.isFinite(n)||n<0||n>10000){V.err='비중은 0~100%';draw();return;}V.err=null;on(n);draw();}});
  const axes=h('div',{class:'sq-axes',role:'group','aria-label':'축 비중'},...S.AXES.map(a=>h('label',{class:'sq-ax'},S.AXIS_TEXT[a],' ',num('sq-axis-'+a,S.AXIS_TEXT[a]+' 축 비중(%)',p.axis_weights[a],n=>{V.edit=S.setAxis(V.edit,a,n);}),'%')),
   h('span',{class:sm.axis===10000?'reason':'hand err',dataset:{sqAxisSum:String(sm.axis)}},'합계 ',pct(sm.axis)),
   ...S.AXES.filter(a=>p.axis_weights[a]===0).map(a=>h('span',{class:'chip',dataset:{sqExcluded:a}},a,' 제외(사용자)')));
  const tabs=h('div',{class:'scroll',role:'group','aria-label':'축'},...S.AXES.map(a=>h('button',{type:'button',class:'chip','aria-pressed':String(V.axis===a),dataset:{k:'sq-tab-'+a},onclick:()=>{V.axis=a;draw();}},S.AXIS_TEXT[a])));
  const inEdit=v=>Object.values(p.axes[V.axis]).some(x=>Object.prototype.hasOwnProperty.call(x.factors,v));
  // 선택됨 follows the edit (the user's settings); every other badge fact is the engine's list_factors entry.
  const badgeEls=f=>S.badges({...f,selected:f.axis===V.axis?inEdit(f.variant_id):f.selected},V.coverage).map(b=>h('span',{class:b.code==='PENDING'||b.code==='NOT_FIT'?'chip wait':'chip',dataset:{sqBadge:b.code}},b.code==='SELECTED'?'✓ ':'',b.text));
  const why=f=>h('details',{class:'why'},h('summary',null,'산식·출처·추천 이유 ▸'),
   h('p',{class:'reason'},'설계 ID ',f.factor_id,' · 변형 ',f.variant_id,' · 산식 ',f.formula,' v',f.formula_version,' · 단위 ',f.unit,' · 기간 ',f.period,' · ',f.direction==='LOWER'?'낮을수록 우수':'높을수록 우수'),
   h('p',{class:'reason'},'입력 ',(f.inputs||[]).map(x=>x.field+'('+x.period+', '+x.unit+')').join(' · ')||'정의 전'),
   f.aliases&&f.aliases.length?h('p',{class:'reason'},'다른 이름: ',f.aliases.join(', ')):null,
   f.recommendation&&f.recommendation.recommended?h('p',{class:'reason',dataset:{sqRec:f.recommendation.evidence_level}},'추천 · ',f.recommendation.reason,' · 근거 ',S.text(S.EVIDENCE_TEXT,f.recommendation.evidence_level),' · ',(f.recommendation.source_refs||[]).join('; '),' · 검토 ',f.recommendation.reviewed_at):null,
   h('p',{class:'reason'},f.domain_rules));
  const roleBlock=(role,r)=>{const label=S.text(S.ROLE_TEXT,role);
   const alternatives=v=>[...F.values()].filter(f=>f.axis===V.axis&&f.role===role&&f.variant_id!==v&&S.selectable(f)==='OK'&&!Object.values(p.axes[V.axis]).some(x=>Object.prototype.hasOwnProperty.call(x.factors,f.variant_id)));
   return h('div',{class:'sk sq-role',dataset:{sqRole:role}},
    h('div',{class:'sq-role-head'},h('b',null,label),V.adv?h('label',null,' 역할 비중 ',num('sq-role-'+role,label+' 역할 비중(%)',r.weight,n=>{V.edit=S.setRole(V.edit,V.axis,role,n);}),'%'):h('span',{class:'reason'},' 역할 ',pct(r.weight)),
     r.weight===0?h('span',{class:'hand err'},' 역할 비중 0 · 고급에서 예산을 정하세요'):null,
     h('span',{class:sm.factors[V.axis+'|'+role]===10000?'reason':'hand err',dataset:{sqFactorSum:String(sm.factors[V.axis+'|'+role])}},' 요소 합계 ',pct(sm.factors[V.axis+'|'+role]))),
    h('ul',{class:'sq-factors'},...Object.entries(r.factors).map(([v,w])=>{const f=F.get(v);
     return h('li',{dataset:{sqFactor:v}},h('span',{class:'sq-fname'},f?f.display_name:v),' ',h('span',{class:'reason',dataset:{sqShare:''}},'역할 안 ',pct(w)),' ',...(f?badgeEls(f):[]),
      V.adv?h('label',null,' 요소 비중 ',num('sq-fw-'+v,(f?f.display_name:v)+' 요소 비중(%)',w,n=>{V.edit=S.setFactor(V.edit,V.axis,role,v,n);}),'%'):null,
      h('span',{class:'sq-acts'},
       alternatives(v).length?h('select',{dataset:{k:'sq-replace-'+v},'aria-label':'같은 역할 요소로 교체',onchange:e=>{if(!e.target.value)return;try{V.edit=S.replaceFactor(V.edit,V.axis,role,v,F.get(e.target.value));V.err=null;}catch(err){V.err=S.errorText(err.message);}draw();}},
        h('option',{value:''},'요소 교체 ▾'),...alternatives(v).map(x=>h('option',{value:x.variant_id},x.display_name,x.is_default?' · 기본값':'',x.recommendation&&x.recommendation.recommended?' · 추천':''))):null,
       h('button',{type:'button',class:'btn',dataset:{k:'sq-remove-'+v},'aria-label':(f?f.display_name:v)+' 빼기',onclick:()=>{try{V.edit=S.removeFactor(V.edit,V.axis,role,v);V.err=null;}catch(err){V.err=S.errorText(err.message);}draw();}},'빼기')),
      f?why(f):null);})));};
  const roles=h('div',{class:'sq-roles',dataset:{sqAxis:V.axis}},...Object.entries(p.axes[V.axis]).map(([role,r])=>roleBlock(role,r)));
  const found=S.search([...F.values()].filter(f=>f.axis===V.axis),V.query);
  const search=h('div',{class:'sq-search'},h('label',{for:'sq-q'},'전체 후보 검색 (예: PER, PBR, 배당)'),
   h('input',{id:'sq-q',type:'search',value:V.query,autocomplete:'off',dataset:{k:'sq-q'},oninput:e=>{V.query=e.target.value;draw();}}),
   V.query.trim()&&!found.length?h('p',{class:'reason'},'이 축에서 찾은 요소 없음'):null,
   h('ul',{class:'sq-found',dataset:{sqFound:String(found.length)}},...found.map(f=>{const ok=S.selectable(f)==='OK',has=inEdit(f.variant_id);
    return h('li',{dataset:{sqCand:f.variant_id}},h('b',null,f.display_name),' · ',S.text(S.ROLE_TEXT,f.role),' ',...badgeEls(f),' ',
     h('button',{type:'button',class:'btn',disabled:!ok||has,dataset:{k:'sq-add-'+f.variant_id},'aria-label':f.display_name+' 추가',
      onclick:()=>{try{V.edit=S.addFactor(V.edit,f);V.err=null;}catch(err){V.err=S.errorText(err.message);}draw();}},has?'선택됨':!ok?(S.selectable(f)==='PENDING'?'준비 중':'부적합'):'추가'),why(f));})));
  const valid=V.view.validation&&V.view.validation.valid===false?h('p',{class:'hand err',dataset:{sqInvalid:V.view.validation.code}},'엔진 검증 · 저장된 설정 오류 ',S.errorText(V.view.validation.code),' · 기본값으로 표시'):null;
  const sumLine=sm.ok?null:h('p',{class:'hand err',role:'alert',dataset:{sqFault:'SUM'}},'비중 합계가 100%가 아님 · 축 합계, 각 축의 역할 합계, 각 역할의 요소 합계를 100%로 · 엔진이 미리보기를 거부함');
  const scopeEl=h('div',{class:'scroll',role:'radiogroup','aria-label':'적용 범위'},...[['CONTEXT','현재 섹터·회계모형만'],['ALL','전체 섹터에 적용']].map(([id,t])=>
   h('label',{class:'check'},h('input',{type:'radio',name:'sq-scope',value:id,checked:V.scope===id,dataset:{k:'sq-scope-'+id},onchange:()=>{V.scope=id;draw();}}),t)));
  const cur=current(),fresh=!!(V.shown&&cur&&V.shown.key===cur.key),savable=fresh&&!V.shown.res.saved.refused;
  const actions=h('div',{class:'sq-actions'},
   h('button',{type:'button',class:'btn solid',disabled:!sm.ok||!!V.pendingId,dataset:{k:'sq-preview'},onclick:()=>{void preview();}},V.pendingId?'계산 중…':'결과 미리보기'),
   h('button',{type:'button',class:'btn',disabled:!savable,dataset:{k:'sq-save'},onclick:e=>save(e)},'내 설정으로 저장'),
   h('button',{type:'button',class:'btn',dataset:{k:'sq-cancel'},onclick:()=>{V.work=V.savedState==='OK'?copy(V.saved.config):copy(c.default_config);V.view=null;V.edit=null;V.msg='마지막 저장 상태로 되돌림';V.err=null;draw();void loadView();}},'변경 취소'),
   h('button',{type:'button',class:'btn',dataset:{k:'sq-restore'},onclick:()=>{V.work=S.withoutScope(V.work,V.sector,V.template);V.view=null;V.edit=null;V.msg='이 섹터·회계모형을 엔진 기본값('+vs.model_version+')으로 · 저장 전까지 기기 설정은 그대로';V.err=null;draw();void loadView();}},'기본값 복원'),
   h('label',{class:'check'},h('input',{type:'checkbox',checked:V.adv,dataset:{k:'sq-adv'},onchange:e=>{V.adv=e.target.checked;draw();}}),'고급: 역할·요소 비중 편집'),
   h('span',{class:'reason',dataset:{sqSaveNeed:savable?'OK':fresh?'REFUSED':'PREVIEW'}},savable?'미리보기와 같은 설정 · 저장 가능':fresh?'엔진이 저장을 거부 · '+S.errorText(V.shown.res.saved.refused):'저장하려면 지금 설정으로 미리보기'));
  const msg=V.msg||V.err?h('p',{class:V.err?'hand err':'reason',role:'status',dataset:{sqMsg:''}},V.err||V.msg):null;
  const prev=fresh?previewView(V.shown):V.shown?h('p',{class:'reason',dataset:{sqStale:''}},'설정이나 입력이 바뀜 · 이전 미리보기는 지금과 맞지 않아 숨김 · 다시 미리보기'):null;
  body.replaceChildren(...[status,gate,store,initial,...notes,ctxRow,valid,axes,tabs,roles,search,sumLine,scopeEl,actions,msg,prev,comparisonsBlock(),h('span',{hidden:true,dataset:{sqDropped:String(V.dropped)}})].filter(Boolean));
  refocus(k);}

 function previewView(shown){const {before,after,comparison}=shown.res,c=V.ctx;
  const rate=t=>String(t.valid)+' / '+String(t.denominator);
  const inputLabel=(c.inputs.find(x=>x.input_id===shown.input)||{label:shown.input}).label;
  const failures=Object.entries(after.coverage.row_failures||{});
  const summary=h('div',{class:'sk sq-summary',dataset:{sqSummary:after.preview_id}},
   h('p',null,h('b',null,'미리보기 · 공통 엔진 재계산'),' · ',after.engine_version,' · 설정 ',after.config_hash.slice(0,12),' · 기준일 ',after.valuation_date,' · 스냅숏 ',after.snapshot_id,' · 입력 ',inputLabel),
   h('p',{dataset:{sqComputed:after.coverage.total.valid+'/'+after.coverage.total.denominator}},'총점 산출 · 전 ',rate(before.coverage.total),' → 후 ',rate(after.coverage.total),' · 원래 모집단 전체 기준'),
   h('p',{class:'reason'},'축별 산출(후) · ',S.AXES.map(a=>a+' '+rate(after.coverage.axes[a])).join(' · '),' · 세 축 모두 ',rate(after.coverage.all_axes),' · 전후 모두 산출 ',String(comparison.common_valid),' · 새로 산출 ',String(comparison.gained.length),' · 산출 안 됨으로 바뀜 ',String(comparison.lost.length)),
   failures.length?h('p',{class:'reason',dataset:{sqReasons:''}},'미산출 사유(후) · ',failures.map(([k,n])=>S.text(S.STATUS_TEXT,k)+' '+n).join(' · ')):null,
   shown.skipped.length?h('p',{class:'hand err',dataset:{sqSkipped:String(shown.skipped.length)}},'전체 적용에서 제외(요소 적용 부적합) ',String(shown.skipped.length),'곳 · ',shown.skipped.slice(0,8).map(k=>{const[s,t]=k.split('|');return S.text(S.SECTOR_TEXT,s)+'·'+S.text(S.TEMPLATE_TEXT,t);}).join(', '),shown.skipped.length>8?' 외':''):null,
   h('p',{class:'reason'},'섹터 기준 상대 점수 · 순위는 이 모델의 원래 모집단 순위(공식 순위 아님) · 성과 ',after.performance_state,' · ',after.validation_state));
  const cmp=new Map(comparison.rows.map(r=>[r.company_id,r])),b=new Map(before.result_rows.map(r=>[r.company_id,r]));
  const rows=after.result_rows.filter(r=>!V.only||(r.sector_id===V.sector&&r.accounting_template===V.template));
  const rk=r=>r.rank===null?Infinity:r.rank,ordered=[...rows].sort((x,y)=>rk(x)-rk(y)||(x.company_id<y.company_id?-1:1));
  const F=factorsBy(),name=v=>(F.get(v)||{display_name:v}).display_name;
  const axisCell=(r,a)=>{if(!r)return '—';const v=r.axes&&r.axes[a];if(v!==null&&v!==undefined)return fmt(v);
   const miss=r.missing_factors&&r.missing_factors[a]||[];return h('span',{class:'na',dataset:{na:r.status}},'미산출 · ',miss.length?miss.map(name).join(', ')+' '+miss.map(x=>S.text(S.FACTOR_TEXT,r.factors[x]&&r.factors[x].score_status)).join(', '):S.text(S.STATUS_TEXT,r.status));};
  const totalCell=r=>{if(!r)return '—';if(r.total!==null&&r.total!==undefined)return fmt(r.total);return h('span',{class:'na',dataset:{na:r.status}},'최종 점수 없음 · ',S.text(S.STATUS_TEXT,r.status));};
  const gateCell=r=>{if(!r||r.status==='MAPPING_UNRESOLVED')return '—';const t=S.text(S.GATE_TEXT,r.gate_status);
   return h('span',{dataset:{sqGate:r.gate_status}},t,r.gate_status==='VALUE_EXCLUDED'?' · 적용 '+S.AXES.filter(a=>r.post_gate_axis_weights[a]>0).map(a=>a+' '+fmt(r.post_gate_axis_weights[a]*100)+'%').join(' · '):'');};
  const rankTxt=v=>v===null||v===undefined?'없음':String(v);
  const phone=window.matchMedia&&window.matchMedia('(max-width:720px)').matches;
  const filter=h('label',{class:'check'},h('input',{type:'checkbox',checked:V.only,dataset:{k:'sq-only'},onchange:e=>{V.only=e.target.checked;draw();}}),'이 섹터·회계모형만 보기 (순위는 그대로)');
  const list=phone?h('ol',{class:'news-lines sq-rows',dataset:{sqRows:String(ordered.length)}},...ordered.map(r=>{const x=cmp.get(r.company_id),o=b.get(r.company_id);
    return h('li',{dataset:{sqRow:r.company_id,sqStatus:r.status}},h('b',null,r.company_id),' · ',S.text(S.STATUS_TEXT,r.status),h('br'),gateCell(r),h('br'),'총점 ',totalCell(o),' → ',totalCell(r),' · 순위 ',rankTxt(o&&o.rank),' → ',h('span',{dataset:{sqRank:''}},rankTxt(r.rank)),
     h('br'),h('span',{class:'reason'},...S.AXES.flatMap(a=>[a,' ',axisCell(o,a),' → ',axisCell(r,a),' · ']),'공통 순위 ',rankTxt(x&&x.before_common_rank),' → ',rankTxt(x&&x.after_common_rank)));}))
   :h('div',{class:'tbl-wrap'},h('table',{class:'tbl sq-rows',dataset:{sqRows:String(ordered.length)}},
    h('caption',null,'전→후 · 엔진 결과 그대로 · 이 표는 순위를 다시 매기지 않음'),
    h('thead',null,h('tr',null,...['기업(합성)','상태','관문','Q','G','V','총점','순위','공통 순위'].map(t=>h('th',{scope:'col'},t)))),
    h('tbody',null,...ordered.map(r=>{const x=cmp.get(r.company_id),o=b.get(r.company_id);
     return h('tr',{dataset:{sqRow:r.company_id,sqStatus:r.status}},h('td',null,r.company_id),h('td',null,S.text(S.STATUS_TEXT,r.status)),h('td',null,gateCell(r)),
      ...S.AXES.map(a=>h('td',{dataset:{sqCell:a}},axisCell(o,a),' → ',axisCell(r,a))),h('td',{dataset:{sqCell:'total'}},totalCell(o),' → ',totalCell(r)),
      h('td',{dataset:{sqRank:''}},rankTxt(o&&o.rank),' → ',rankTxt(r.rank)),h('td',null,rankTxt(x&&x.before_common_rank),' → ',rankTxt(x&&x.after_common_rank)));}))));
  const first=after.result_rows.find(r=>r.sector_id===V.sector&&r.accounting_template===V.template&&r.nominal_effective_weights);
  const weights=first?h('details',{class:'why',dataset:{sqWeights:''}},h('summary',null,'이 섹터·회계모형의 요소 실효비중(엔진) ▸'),
   h('ul',null,...Object.entries(first.nominal_effective_weights).filter(([,w])=>w>0).map(([v,w])=>h('li',null,name(v),' · ',fmt(w*100),'%')))):null;
  // Codex's Q/G partial comparison of these two previews, drawn once per shown preview (its filters keep their state).
  if(!shown.axisEl)shown.axisEl=I.sectorQgvAxisLive.render(shown.res.axis,{kind:'PREVIEW'});
  return h('section',{class:'sq-preview','aria-label':'결과 미리보기',dataset:{sqPreview:after.preview_id}},summary,weights,shown.axisEl,filter,
   ordered.length?list:h('p',{class:'reason',dataset:{sqRows:'0'}},after.result_rows.length?'이 섹터·회계모형의 행 없음 · 필터를 끄면 전체':'모집단 0 · 계산할 행 없음'));}

 paint();
}
I.sectorQgvLive=Object.freeze({fill});
})();
