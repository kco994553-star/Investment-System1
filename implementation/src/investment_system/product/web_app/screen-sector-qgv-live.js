/* 1. QGV · 1.2 가중치 · QGV 구성 — sector QGV factor choice and recalculation (feature 2.2.1–2.2.7; owner 2026-11-06, design
   "섹터별 QGV 요소 선택·추천·재계산" §3, §6). screen-qgv.js gives this file the 1.2 section body; it fills it after IS2.ready.
   - Models kept apart: 공식 QGV (the published official page of 1.1, never changed here), 연구 프리셋 sector-qgv-default/<version>
     (기본값 · 초기 설정: the base presets, read only) and 내 QGV (base presets + the user's overrides). Totals of different models
     are never put in one ranking; the 1.1 table and its filters never re-rank from this screen.
   - Flow: 섹터 · 회계모형 → Q/G/V 비중 → 역할 · 요소 (교체, 추가, 빼기, 검색 by familiar names such as PER / PBR) → 결과 미리보기
     → 내 설정으로 저장 / 변경 취소 / 기본값 복원. Saving needs the latest successful preview of exactly the edited config
     (same key: snapshot, universe, engine, normalization, mapping, preset version, config hash).
   - Badges told apart: 기본값 · 초기 설정 · 추천 (reason, evidence, source) · 선택됨 · 계산 기능 준비 중 (not selectable) · 산식 적용
     부적합 (not selectable for this template) · 자료 일부 부족 (selectable; the preview shows who is unscored). Words, never colour
     alone.
   - Scope: 현재 섹터·회계모형만 (default) or 전체 섹터에 적용 (an explicit copy to every context that can use the factors; the
     others are listed). A bank change never spreads to insurance, asset managers or REITs by itself.
   - The preview runs IS2.sectorQgv.preview(value, saved, edited) — a Promise; only the answer of the latest request whose key
     equals the current edit is shown (an older answer arriving later is dropped). Unscored is never 0: the reason is shown.
   - Saved on this device only (IS2.store.sectorQgv, no account sync, not in a backup). A newer default version never rewrites
     a saved config: the screen says the base differs and starting over on the new default is the user's click.
   Nothing here computes a factor; nothing is sent. View state lives in RAM for this page load. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const X=()=>I.sectorQgv;
const AX={Q:'Q · 질',G:'G · 성장',V:'V · 가치'};
const V={model:'MINE',ctx:null,axis:'Q',scope:'CONTEXT',query:'',adv:false,edit:null,work:null,saved:null,savedState:'EMPTY',msg:null,req:0,shown:null,pending:false,dropped:0,saveErr:null};
let NF=null;const fmt=v=>(NF||(NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}))).format(v);
const pct=bp=>fmt(bp/100)+'%';
const reason=(code,words)=>h('span',{class:'reason',dataset:{na:code||''}},words);
const na=(code)=>h('span',{class:'na',dataset:{na:code}},'미산출 · ',X().reasonText(code));
const val=v=>v===null||v===undefined?null:fmt(v);

let shared=null;
function load(){const api=X();if(shared&&shared.api===api)return shared.p;
 const p=(async()=>{let src;try{src=await api.source();}catch(_){return{state:'ERROR',code:'SECTOR_QGV_SOURCE_FAILED'};}
  if(!src||src.state==='NONE')return{state:'NONE',code:(src&&src.code)||'SECTOR_QGV_NOT_CONNECTED'};
  if(src.state!=='OK')return{state:'ERROR',code:src.code||'SECTOR_QGV_SOURCE_FAILED'};
  const r=api.validate(src.payload);return r.ok?{state:'OK',value:r.value}:{state:'INVALID',code:r.code,path:r.path};})().catch(()=>({state:'ERROR',code:'SECTOR_QGV_SOURCE_FAILED'}));
 shared={api,p};p.then(x=>{if(x.state==='ERROR'&&shared&&shared.p===p)shared=null;});return p;}

function fill(route,{body}){
 const signal=route.signal;let res=null;
 const focusKey=()=>{const a=document.activeElement;return a&&body.contains(a)&&a.dataset&&a.dataset.k?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const el=body.querySelector('[data-k="'+CSS.escape(k)+'"]');if(el&&!el.disabled)el.focus({preventScroll:true});};
 const card=(state,words,why,alert)=>h('div',{class:'sk state-card',role:alert?'alert':null,dataset:{sqState:state}},I.parts.mascot(alert?'alarm':'plain'),h('b',null,words),why?h('span',{class:'reason'},why):null);
 // ---- the user's saved config (device) and the working copy
 function readSaved(v){const st=I.store.sectorQgv.read();V.savedState=st.state;
  if(st.state==='OK'){const c=X().validateConfig(st.value,v);if(c.ok){V.saved=JSON.parse(JSON.stringify(st.value));return;}V.savedState=c.code==='BASE_VERSION_DIFFERS'?'BASE_DIFFERS':'INVALID';V.savedRaw=st.value;}
  V.saved=X().emptyConfig(v);}
 function ctxOf(v){const cs=X().contexts(v);if(!V.ctx||!cs.some(c=>c.key===V.ctx))V.ctx=cs[0].key;const c=cs.find(x=>x.key===V.ctx);return c;}
 function resetEdit(v){const c=ctxOf(v);V.work=JSON.parse(JSON.stringify(V.saved));V.edit=X().treeFor(v,V.work,c.key);V.shown=null;V.pending=false;V.saveErr=null;}
 const editedConfig=(v,c)=>{if(V.model==='DEFAULT')return X().emptyConfig(v);return X().applyEdit(V.work,v,c,V.edit,V.scope);};
 const draw=()=>{if(!signal.aborted)paint();};

 function paint(){
  const k=focusKey(),S=X();
  if(!res){body.replaceChildren(h('p',{class:'pending',role:'status',dataset:{sqState:'LOADING'}},'불러오는 중'));return;}
  if(res.state==='NONE'){body.replaceChildren(card('NONE',S.TEXT.NONE,S.TEXT.NONE_WHY),
   h('p',{class:'hand'},'자료가 오면: 섹터·회계모형 → Q/G/V 비중 → 요소 교체·추가 → 결과 미리보기 → 내 설정으로 저장 · 변경 취소 · 기본값 복원'),
   h('p',{class:'reason'},'공식 QGV(1.1 리더보드)는 이 화면과 상관없이 그대로'));return;}
  if(res.state!=='OK'){body.replaceChildren(card(res.state,res.state==='INVALID'?S.TEXT.INVALID:S.TEXT.FAILED,res.state==='INVALID'?'규격 위반 '+res.code+' · '+res.path:'공식 QGV는 그대로',true));body.dataset.sqCode=res.code;return;}
  const v=res.value,c=ctxOf(v),X_=S.index(v),preset=X_.P.get(c.key);
  // status, models, storage note
  const status=h('p',{class:'sk status-line',dataset:{sqData:v.data_kind}},S.status(v),' · 기준일 ',v.snapshot.as_of,' · 엔진 ',v.snapshot.engine_version,' · 분류 ',v.snapshot.mapping_version,' · 계산 Codex');
  const model=(id,label)=>h('button',{type:'button',class:'chip','aria-pressed':String(V.model===id),dataset:{k:'sq-model-'+id,sqModel:id},onclick:()=>{V.model=id;V.shown=null;draw();}},label);
  const models=h('div',{class:'scroll',role:'group','aria-label':'QGV 모델'},model('OFFICIAL','공식 QGV'),model('MINE','내 QGV'),
   model('DEFAULT','연구 프리셋 '+S.PRESET_SET+'/'+X_.version+' · '+(preset&&preset.validation_state==='validated'?S.TEXT.VALIDATED:S.TEXT.INITIAL)));
  const store=h('p',{class:'reason',dataset:{sqStorage:'DEVICE'}},'내 설정은 이 기기(이 브라우저)에만 저장 · 다른 기기와 동기화 안 됨 · 백업 파일에 들어가지 않음');
  const initial=h('p',{class:'reason',dataset:{sqInitial:''}},'기본값 · 초기 설정 = 비교검증으로 조정할 시작값 · 최적값이나 성과 검증 완료가 아님 · 린치 유형 태그는 점수에 영향 없음');
  if(V.model==='OFFICIAL'){body.replaceChildren(status,models,h('div',{class:'sk state-card',dataset:{sqState:'OFFICIAL'}},h('b',null,'공식 QGV는 1.1 리더보드의 게시본 그대로'),
   h('span',{class:'reason'},'이 화면의 섹터 설정으로 공식 점수·순위·TARGET이 바뀌지 않음 · 섹터 모델은 따로 계산하고 섞지 않음'),h('a',{class:'lk',href:'#/qgv'},'→ 1.1 리더보드')),store);refocus(k);return;}
  const notes=[];
  if(V.savedState==='BASE_DIFFERS')notes.push(h('p',{class:'hand err',dataset:{sqSaved:'BASE_DIFFERS'}},'저장한 설정의 기준 버전이 지금 기본값('+X_.version+')과 다름 · 자동으로 바꾸지 않음',
   h('button',{type:'button',class:'btn',dataset:{k:'sq-restart'},onclick:()=>{V.savedState='EMPTY';V.saved=S.emptyConfig(v);resetEdit(v);V.msg='새 기본값으로 새로 시작 · 저장하기 전까지 이전 저장은 그대로';draw();}},'새 기본값으로 새로 시작')));
  if(V.savedState==='INVALID')notes.push(h('p',{class:'hand err',dataset:{sqSaved:'INVALID'}},'이 기기의 저장 설정을 읽을 수 없음 · 덮어쓰지 않음',
   h('button',{type:'button',class:'btn',dataset:{k:'sq-clear-bad'},onclick:e=>{try{I.store.sectorQgv.clear(e);V.savedState='EMPTY';V.saved=S.emptyConfig(v);resetEdit(v);}catch(_){V.msg='지우지 못함';}draw();}},'저장 설정 지우기')));
  // context
  const sectors=[...new Set(S.contexts(v).map(x=>x.sector_id))],tpls=S.contexts(v).filter(x=>x.sector_id===c.sector_id);
  const sel=(idk,label,opts,cur,on)=>h('div',{class:'sort-row'},h('label',{for:idk},label),h('select',{id:idk,dataset:{k:idk},onchange:on},...opts.map(([val,t])=>h('option',{value:val,selected:val===cur},t))));
  const ctxRow=h('div',{class:'sq-ctx'},sel('sq-sector','섹터(책 10섹터)',sectors.map(s=>[s,X_.sectors.get(s)]),c.sector_id,e=>{const n=S.contexts(v).find(x=>x.sector_id===e.target.value);V.ctx=n.key;resetEdit(v);draw();}),
   sel('sq-template','회계모형',tpls.map(x=>[x.key,X_.templates.get(x.template_id)]),c.key,e=>{V.ctx=e.target.value;resetEdit(v);draw();}));
  const ro=V.model==='DEFAULT',tree=ro?X().treeFor(v,null,c.key):V.edit,fault=ro?null:S.checkTree(tree,c,v);
  // axis weights
  const axisIn=a=>h('label',{class:'sq-ax'},AX[a],' ',h('input',{type:'number',min:'0',max:'100',step:'0.01',inputmode:'decimal',value:String(tree.axis_weights[a]/100),disabled:ro,dataset:{k:'sq-axis-'+a},'aria-label':AX[a]+' 축 비중(%)',
   onchange:e=>{const n=Math.round(Number(e.target.value)*100);if(!Number.isFinite(n))return;V.edit=S.setAxisWeights(V.edit,{...V.edit.axis_weights,[a]:Math.max(0,Math.min(10000,n))});V.shown=null;draw();}}),'%');
  const sum=S.AXES.reduce((t,a)=>t+tree.axis_weights[a],0);
  const axes=h('div',{class:'sq-axes',role:'group','aria-label':'축 비중'},...S.AXES.map(axisIn),h('span',{class:sum===10000?'reason':'hand err',dataset:{sqAxisSum:String(sum)}},'합계 ',pct(sum)),
   ...S.AXES.filter(a=>tree.axis_weights[a]===0).map(a=>h('span',{class:'chip',dataset:{sqExcluded:a}},a,' 제외(사용자)')));
  // axis tabs + roles
  const tabs=h('div',{class:'scroll',role:'group','aria-label':'축'},...S.AXES.map(a=>h('button',{type:'button',class:'chip','aria-pressed':String(V.axis===a),dataset:{k:'sq-tab-'+a},onclick:()=>{V.axis=a;draw();}},AX[a])));
  const cat=new Map(S.catalog(v,c,tree,V.axis).map(r=>[r.factor.factor_id,r]));
  const badges=r=>[r.base?h('span',{class:'chip',dataset:{sqBadge:'BASE'}},preset&&preset.validation_state==='validated'?S.TEXT.VALIDATED:S.TEXT.INITIAL):null,
   r.recommended.length?h('span',{class:'chip',dataset:{sqBadge:'RECOMMENDED'}},S.TEXT.RECOMMENDED):null,
   r.selected?h('span',{class:'chip',dataset:{sqBadge:'SELECTED'}},'✓ ',S.TEXT.SELECTED):null,
   r.state==='PENDING'?h('span',{class:'chip wait',dataset:{sqBadge:'PENDING'}},S.TEXT.PENDING):null,
   r.state==='NOT_FIT'?h('span',{class:'chip wait',dataset:{sqBadge:'NOT_FIT'}},S.TEXT.NOT_FIT):null,
   r.state==='PARTIAL'?h('span',{class:'chip',dataset:{sqBadge:'PARTIAL'}},S.TEXT.PARTIAL,' · ',String(r.scored),'/',String(r.members)):null];
  const why=r=>h('details',{class:'why'},h('summary',null,'산식·출처·추천 이유 ▸'),
   h('p',{class:'reason'},r.factor.explain,' · 단위 ',r.factor.unit,' · 기간 ',r.factor.period,' · ',r.factor.direction==='LOWER'?'낮을수록 우수':'높을수록 우수',' · 산식 ',r.factor.formula_version),
   r.factor.aliases.length?h('p',{class:'reason'},'다른 이름: ',r.factor.aliases.join(', ')):null,
   ...r.recommended.map(x=>h('p',{class:'reason',dataset:{sqRec:x.evidence_level}},'추천 · ',x.reason,' · 근거 ',S.EVIDENCE[x.evidence_level],' · ',x.source_refs.join('; '),' · 검토 ',x.reviewed_at)),
   r.state==='PARTIAL'?h('p',{class:'reason'},'이 섹터·회계모형 ',String(r.members),'개 중 점수 있는 기업 ',String(r.scored),'개 · 나머지는 미리보기에서 미산출로'):null);
  const eff=new Map(S.effective(tree).map(e=>[e.factor_id,e.share]));
  const roleBlock=role=>{const label=X_.roles.get(V.axis+'|'+role.role)||role.role;
   const alternatives=fid=>[...cat.values()].filter(r=>r.factor.role===role.role&&r.factor.factor_id!==fid&&r.selectable&&!r.selected);
   return h('div',{class:'sk sq-role',dataset:{sqRole:role.role}},
    h('div',{class:'sq-role-head'},h('b',null,label),V.adv&&!ro?h('label',null,' 역할 비중 ',h('input',{type:'number',min:'0',max:'100',step:'0.01',value:String(role.weight_bp/100),dataset:{k:'sq-role-'+role.role},'aria-label':label+' 역할 비중(%)',
     onchange:e=>{const n=Math.round(Number(e.target.value)*100);if(!Number.isFinite(n))return;V.edit=S.setRoleWeight(V.edit,V.axis,role.role,Math.max(0,Math.min(10000,n)));V.shown=null;draw();}}),'%'):h('span',{class:'reason'},' 역할 ',pct(role.weight_bp)),
     role.weight_bp===0?h('span',{class:'hand err'},' 역할 비중 0 · 고급에서 예산을 정하세요'):null),
    h('ul',{class:'sq-factors'},...role.factors.map(f=>{const r=cat.get(f.factor_id),share=eff.get(f.factor_id);
     return h('li',{dataset:{sqFactor:f.factor_id}},h('span',{class:'sq-fname'},r?r.factor.display_name:f.factor_id),' ',
      h('span',{class:'reason',dataset:{sqShare:''}},'역할 안 ',pct(f.weight_bp),' · 총점 실효 ',share===undefined?'0.0%':fmt(share*100)+'%'),' ',...(r?badges(r):[]),
      V.adv&&!ro?h('label',null,' 요소 비중 ',h('input',{type:'number',min:'0',max:'100',step:'0.01',value:String(f.weight_bp/100),dataset:{k:'sq-fw-'+f.factor_id},'aria-label':(r?r.factor.display_name:f.factor_id)+' 요소 비중(%)',
       onchange:e=>{const n=Math.round(Number(e.target.value)*100);if(!Number.isFinite(n))return;V.edit=S.setFactorWeight(V.edit,V.axis,f.factor_id,Math.max(0,Math.min(10000,n)));V.shown=null;draw();}}),'%'):null,
      ro?null:h('span',{class:'sq-acts'},
       alternatives(f.factor_id).length?h('select',{dataset:{k:'sq-replace-'+f.factor_id},'aria-label':'같은 역할 요소로 교체',onchange:e=>{if(!e.target.value)return;V.edit=S.replaceFactor(V.edit,v,V.axis,f.factor_id,e.target.value);V.shown=null;draw();}},
        h('option',{value:''},'요소 교체 ▾'),...alternatives(f.factor_id).map(x=>h('option',{value:x.factor.factor_id},x.factor.display_name,x.base?' · 기본값':'',x.recommended.length?' · 추천':''))):null,
       h('button',{type:'button',class:'btn',dataset:{k:'sq-remove-'+f.factor_id},'aria-label':(r?r.factor.display_name:f.factor_id)+' 빼기',onclick:()=>{V.edit=S.removeFactor(V.edit,V.axis,f.factor_id);V.shown=null;draw();}},'빼기')),
      r?why(r):null);})));};
  const roles=h('div',{class:'sq-roles',dataset:{sqAxis:V.axis}},...tree.roles[V.axis].map(roleBlock));
  // search / add
  const found=V.query.trim()?S.catalog(v,c,tree,V.axis,V.query):[];// the candidate list only for a search (the role's own alternatives are in 요소 교체)
  const search=ro?null:h('div',{class:'sq-search'},h('label',{for:'sq-q'},'전체 후보 검색 (예: PER, PBR, 배당)'),
   h('input',{id:'sq-q',type:'search',value:V.query,autocomplete:'off',dataset:{k:'sq-q'},oninput:e=>{V.query=e.target.value;draw();}}),
   V.query.trim()&&!found.length?h('p',{class:'reason'},'이 축에서 찾은 요소 없음'):null,
   h('ul',{class:'sq-found',dataset:{sqFound:String(found.length)}},...found.map(r=>h('li',{dataset:{sqCand:r.factor.factor_id}},h('b',null,r.factor.display_name),' · ',r.role_label,' ',...badges(r),' ',
    h('button',{type:'button',class:'btn',disabled:!r.selectable||r.selected,dataset:{k:'sq-add-'+r.factor.factor_id},'aria-label':r.factor.display_name+' 추가',
     onclick:()=>{try{V.edit=S.addFactor(V.edit,v,V.axis,r.factor.factor_id);V.shown=null;V.msg=null;}catch(err){V.msg=String(err.message);}draw();}},r.selected?'선택됨':!r.selectable?(r.state==='PENDING'?'준비 중':'부적합'):'추가'),why(r)))));
  // validation, scope, actions
  const faultLine=fault?h('p',{class:'hand err',role:'alert',dataset:{sqFault:fault.code}},'설정 오류 · ',fault.code,' · 미리보기 전에 고치세요 (축 합계 100%, 활성 축의 역할 합계 100%, 활성 역할의 요소 합계 100%)'):null;
  const scope=ro?null:h('div',{class:'scroll',role:'radiogroup','aria-label':'적용 범위'},...[['CONTEXT','현재 섹터·회계모형만'],['ALL','전체 섹터에 적용']].map(([id,t])=>
   h('label',{class:'check'},h('input',{type:'radio',name:'sq-scope',value:id,checked:V.scope===id,dataset:{k:'sq-scope-'+id},onchange:()=>{V.scope=id;V.shown=null;draw();}}),t)));
  const cfg=editedConfig(v,c),curKey=S.key(v,cfg.config||cfg,V.model);
  const fresh=V.shown&&V.shown.key===curKey;
  const actions=h('div',{class:'sq-actions'},
   h('button',{type:'button',class:'btn solid',disabled:!!fault,dataset:{k:'sq-preview'},onclick:()=>runPreview(v,c)},V.pending?'계산 중…':'결과 미리보기'),
   ro?null:h('button',{type:'button',class:'btn',disabled:!fresh||!!fault,dataset:{k:'sq-save'},onclick:e=>save(e,v,c)},'내 설정으로 저장'),
   ro?null:h('button',{type:'button',class:'btn',dataset:{k:'sq-cancel'},onclick:()=>{resetEdit(v);V.msg='마지막 저장 상태로 되돌림';draw();}},'변경 취소'),
   ro?null:h('button',{type:'button',class:'btn',dataset:{k:'sq-restore'},onclick:()=>{V.work=S.restoreDefault(V.work,c);V.edit=S.treeFor(v,null,c.key);V.shown=null;V.msg='이 섹터·회계모형을 기본값('+S.PRESET_SET+'/'+X_.version+')으로 · 저장 전까지 기기 설정은 그대로';draw();}},'기본값 복원'),
   ro?null:h('label',{class:'check'},h('input',{type:'checkbox',checked:V.adv,dataset:{k:'sq-adv'},onchange:e=>{V.adv=e.target.checked;draw();}}),'고급: 역할·요소 비중 편집'),
   ro?null:h('span',{class:'reason',dataset:{sqSaveNeed:fresh?'OK':'PREVIEW'}},fresh?'미리보기와 같은 설정 · 저장 가능':'저장하려면 지금 설정으로 미리보기'));
  const msg=V.msg||V.saveErr?h('p',{class:V.saveErr?'hand err':'reason',role:'status',dataset:{sqMsg:''}},V.saveErr||V.msg):null;
  const prev=V.shown&&V.shown.key===curKey?previewView(v,c,V.shown):V.shown?h('p',{class:'reason',dataset:{sqStale:''}},'설정이 바뀜 · 이전 미리보기는 지금 설정과 맞지 않아 숨김 · 다시 미리보기'):null;
  body.replaceChildren(...[status,models,store,initial,...notes,ctxRow,axes,tabs,roles,search,faultLine,scope,actions,msg,prev,h('span',{hidden:true,dataset:{sqDropped:String(V.dropped)}})].filter(Boolean));
  delete body.dataset.sqCode;refocus(k);}

 function runPreview(v,c){const S=X(),cfg=editedConfig(v,c),edited=cfg.config||cfg,keyNow=S.key(v,edited,V.model);
  const before=V.model==='DEFAULT'?S.emptyConfig(v):V.saved,id=++V.req;V.pending=true;V.msg=null;V.skipped=cfg.skipped||[];draw();
  Promise.resolve(S.preview(v,before,edited)).then(out=>{if(signal.aborted)return;
   const cur=editedConfig(v,ctxOf(v)),curKey=S.key(v,cur.config||cur,V.model);
   if(id!==V.req||keyNow!==curKey){V.dropped++;draw();return;}// an older answer or one for another edit: never shown
   V.pending=false;V.shown={key:keyNow,out,config:edited,skipped:V.skipped};draw();},
  ()=>{if(signal.aborted||id!==V.req)return;V.pending=false;V.msg='미리보기를 계산하지 못함';draw();});}
 function save(e,v,c){const S=X();if(!V.shown)return;try{I.store.sectorQgv.save(e,V.shown.config);V.saved=JSON.parse(JSON.stringify(V.shown.config));V.savedState='OK';V.work=JSON.parse(JSON.stringify(V.saved));
  V.saveErr=null;V.msg='이 기기에 저장함 · 기준 '+S.PRESET_SET+'/'+S.index(v).version+' · 설정 '+S.configHash(V.saved);}catch(err){V.saveErr='저장하지 못함 · '+String(err&&err.message);}draw();}

 function previewView(v,c,shown){const S=X(),{before,after,diff}=shown.out,X_=S.index(v);
  const rate=(n,d)=>String(n)+' / '+String(d)+' ('+fmt(d?100*n/d:0)+'%)';
  const label=V.model==='DEFAULT'?'연구 프리셋 '+S.PRESET_SET+'/'+X_.version:'내 QGV';
  const summary=h('div',{class:'sk sq-summary',dataset:{sqSummary:''}},
   h('p',null,h('b',null,'미리보기 · ',label),' · 설정 ',S.configHash(shown.config),' · 기준일 ',v.snapshot.as_of,' · 모집단 ',v.snapshot.universe_id,' ',v.snapshot.universe_version),
   h('p',{dataset:{sqComputed:after.computed+'/'+after.denominator}},'총점 산출 · 전 ',rate(before.computed,before.denominator),' → 후 ',rate(after.computed,after.denominator),' · 원래 모집단 전체 기준'),
   h('p',{class:'reason'},'축별 산출(후) · ',S.AXES.map(a=>a+' '+after.axes[a]).join(' · '),' · 둘 다 산출 ',String(diff.common),'개'),
   Object.keys(after.reasons).length?h('p',{class:'reason',dataset:{sqReasons:''}},'미산출 사유(후) · ',Object.entries(after.reasons).map(([k,n])=>S.reasonText(k)+' '+n).join(' · ')):null,
   shown.skipped&&shown.skipped.length?h('p',{class:'hand err',dataset:{sqSkipped:String(shown.skipped.length)}},'전체 적용에서 제외(요소 적용 부적합) · ',shown.skipped.map(k=>{const[s,t]=k.split('|');return X_.sectors.get(s)+'·'+X_.templates.get(t);}).join(', ')):null,
   h('p',{class:'reason'},'섹터 기준 상대 점수 · 다른 섹터의 같은 점수는 같은 기대수익이 아님 · 공식 순위와 별개'));
  const effTree=V.model==='DEFAULT'?S.treeFor(v,null,c.key):S.treeFor(v,shown.config,c.key);
  const weights=h('details',{class:'why',dataset:{sqWeights:''}},h('summary',null,'이 섹터·회계모형의 축·요소 실효비중 ▸'),
   h('ul',null,...S.effective(effTree).map(e=>h('li',null,e.axis,' · ',X_.roles.get(e.axis+'|'+e.role)||e.role,' · ',(X_.F.get(e.factor_id)||{display_name:e.factor_id}).display_name,' · ',fmt(e.share*100),'%'))));
  const inCtx=diff.rows.filter(r=>r.sector_id===c.sector_id&&r.template_id===c.template_id);
  const rk=r=>r.after.rank===null?Infinity:r.after.rank,ordered=[...inCtx].sort((a,b)=>rk(a)-rk(b)||(a.company_id<b.company_id?-1:1));
  const cell=(row,ax)=>row[ax]===null?(ax==='total'?na(row.reason||'AXIS_UNSCORED'):row.excluded.includes(ax)?h('span',{class:'reason'},'제외'):na(row.why[ax]||'MISSING_INPUT')):val(row[ax]);
  const phone=window.matchMedia&&window.matchMedia('(max-width:720px)').matches;
  const rankTxt=r=>r===null?'—':String(r);
  const list=phone?h('ol',{class:'news-lines sq-rows',dataset:{sqRows:String(ordered.length)}},...ordered.map(r=>h('li',{dataset:{sqRow:r.company_id}},h('b',null,r.company_id),' ',
    ...r.after.lynch_tags.map(t=>h('span',{class:'chip',dataset:{sqTag:''}},t)),h('br'),'총점 ',cell(r.before,'total'),' → ',cell(r.after,'total'),' · 순위 ',rankTxt(r.before.rank),' → ',rankTxt(r.after.rank),
    h('br'),h('span',{class:'reason'},'Q ',cell(r.before,'Q'),' → ',cell(r.after,'Q'),' · G ',cell(r.before,'G'),' → ',cell(r.after,'G'),' · V ',cell(r.before,'V'),' → ',cell(r.after,'V')))))
   :h('div',{class:'tbl-wrap'},h('table',{class:'tbl sq-rows',dataset:{sqRows:String(ordered.length)}},
    h('caption',null,X_.sectors.get(c.sector_id),' · ',X_.templates.get(c.template_id),' · 전→후 · 순위는 이 모델의 전체 모집단 순위(공식 순위 아님) · 이 표는 순위를 다시 매기지 않음'),
    h('thead',null,h('tr',null,...['기업(합성)','태그','Q','G','V','총점','순위','공통 순위'].map(t=>h('th',{scope:'col'},t)))),
    h('tbody',null,...ordered.map(r=>h('tr',{dataset:{sqRow:r.company_id}},h('td',null,r.company_id),h('td',null,...r.after.lynch_tags.map(t=>h('span',{class:'chip',dataset:{sqTag:''}},t))),
     ...['Q','G','V','total'].map(ax=>h('td',{dataset:{sqCell:ax}},cell(r.before,ax),' → ',cell(r.after,ax))),
     h('td',{dataset:{sqRank:''}},rankTxt(r.before.rank),' → ',rankTxt(r.after.rank)),h('td',null,rankTxt(r.common_before),' → ',rankTxt(r.common_after)))))));
  return h('section',{class:'sq-preview','aria-label':'결과 미리보기',dataset:{sqPreview:shown.key}},summary,weights,list);}

 load().then(x=>{if(signal.aborted)return;res=x;if(x.state==='OK'){readSaved(x.value);resetEdit(x.value);}draw();});
 paint();
}
I.sectorQgvLive=Object.freeze({fill,load});
})();
