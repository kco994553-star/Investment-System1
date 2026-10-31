/* Device drafts contain configuration only. Calculated scores remain in RAM. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./profile-defaults.js'):root.ProfileDefaults);if(typeof module==='object'&&module.exports)module.exports=api;else root.DeviceProfiles=api;})(globalThis,function(defaults){
'use strict';const KEY='investment.web.v1.profile-drafts',SCHEMA='device-profile-drafts/1';
const node=typeof module==='object'&&module.exports,typeDefaults=()=>node?require('./type-config-defaults.js'):globalThis.TypeConfigDefaults,engineApi=()=>node?require('./engine-preview.js'):globalThis.EnginePreview;
function need(v){if(!v)throw Error('PROFILE_INVALID');}
function keys(v,ks){need(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k)));}
function empty(){return {schema:SCHEMA,strategies:[],types:[]};}
function copyOfficial(){return structuredClone(defaults.weights);}
function weights(w){keys(w,['Q','G','V']);for(const axis of ['Q','G','V']){keys(w[axis],Object.keys(defaults.weights[axis]));for(const v of Object.values(w[axis]))need(typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=100);need(Math.abs(Object.values(w[axis]).reduce((a,b)=>a+b,0)-100)<=defaults.sum_tolerance);}return structuredClone(w);}
function copyOfficialTypes(){const c=structuredClone(typeDefaults());c.status='CUSTOM_PREVIEW';return c;}
function typeConfig(c){const engine=engineApi();need(engine&&c&&typeof c==='object'&&!Array.isArray(c)&&c.status==='CUSTOM_PREVIEW');const text=JSON.stringify(c);need(text.length<=65536&&!/NaN|Infinity/.test(JSON.stringify(c,(k,v)=>typeof v==='number'&&!Number.isFinite(v)?'NaN':v)));need(engine.validateTypeConfig(c).length===0);return JSON.parse(text);}
function validate(v){keys(v,['schema','strategies','types']);need(v.schema===SCHEMA&&Array.isArray(v.strategies)&&v.strategies.length<=20&&Array.isArray(v.types)&&v.types.length<=10);const ids=new Set();const strategies=v.strategies.map(p=>{keys(p,['id','name','weights']);need(typeof p.id==='string'&&/^[a-z0-9-]{1,80}$/.test(p.id)&&!ids.has(p.id)&&typeof p.name==='string'&&p.name.trim().length>0&&p.name.length<=60&&!/[\x00-\x1f]/.test(p.name));ids.add(p.id);return{id:p.id,name:p.name,weights:weights(p.weights)};});const typeIds=new Set(),types=v.types.map(p=>{keys(p,['id','name','config']);need(typeof p.id==='string'&&/^[a-z0-9-]{1,80}$/.test(p.id)&&!typeIds.has(p.id)&&typeof p.name==='string'&&p.name.trim().length>0&&p.name.length<=60&&!/[\x00-\x1f]/.test(p.name));typeIds.add(p.id);return{id:p.id,name:p.name,config:typeConfig(p.config)};});return{schema:SCHEMA,strategies,types};}
function read(storage){const raw=storage.getItem(KEY);return raw?validate(JSON.parse(raw)):empty();}
function write(storage,v){const next=validate(v);storage.setItem(KEY,JSON.stringify(next));return next;}
// RAM-only type PREVIEW: published price-free metrics (revenue_cagr_3y, roic) under official vs custom type_config.
// Q/G come from published factors with official leaf weights; V needs prices, so adjusted scores stay NOT_AVAILABLE.
function typePreview(typesPayload,qgPayload,custom,engine=engineApi()){
 const rows=typesPayload?.data?.companies;if(!engine||!rows||typeof rows!=='object')return{state:'NOT_AVAILABLE',reason:'PUBLIC_TYPE_METRICS_NOT_AVAILABLE',rows:[]};
 const official=engine.compileCustomTypeConfig(copyOfficialTypes()),mine=engine.compileCustomTypeConfig(custom);if(mine.state!=='COMPILED'||official.state!=='COMPILED')return{state:'INVALID_INPUT',reason:'TYPE_CONFIG_INVALID',rows:[]};
 const out=[];for(const[id,r]of Object.entries(rows)){const metrics={};for(const[k,v]of Object.entries(r?.metrics||{}))if(typeof v==='number'&&Number.isFinite(v))metrics[k]=v;if(!Object.keys(metrics).length)continue;
  const observations={};for(const[f,v]of Object.entries(qgPayload?.data?.companies?.[id]?.factors||{}))if(v&&v.score!==null&&v.state!=='NOT_AVAILABLE')observations[f]={score:v.score,quality:v.state==='LIVE'?'OK':'STALE_DATA'};
  const axes=engine.strategy({observations}).axes||{},qgv={Q:typeof axes.Q?.score==='number'?axes.Q.score:null,G:typeof axes.G?.score==='number'?axes.G.score:null,V:null};
  const run=h=>{const x=engine.companyTypes({metrics,original_qgv:qgv,config:h});return x.state==='INVALID_INPUT'?null:{selected_types:x.selected_types,weights:x.weights,adjusted_score:x.adjusted_score,reason_codes:x.reason_codes};};
  out.push({company_id:id,official:run(official),mine:run(mine)});}
 out.sort((a,b)=>a.company_id<b.company_id?-1:1);return{state:out.length?'PREVIEW':'NOT_AVAILABLE',reason:out.length?null:'PUBLIC_TYPE_METRICS_NOT_AVAILABLE',rows:out};
}
// S13 official view: six separate perspectives and the version record. Display only. QGV v2 is the only score on screens
// (owner decision 2026-10-14): the v1 official leaf-weight bars and the 'v1 비교용' record are no longer shown; the v2 default
// weights are in activeV2View.
const PERSPECTIVES=[['기업분석','Company analysis'],['기술','Technical'],['매크로','Macro'],['포트폴리오 적합','Portfolio fit'],['위험','Risk'],['계좌 상황','Account context']];
function officialView(el,en,view){const box=el('div',undefined,{'data-profile-official':''});
 const p=el('div',undefined,{'data-six-perspectives':''});p.append(el('h4',en?'Six perspectives (shown separately)':'6관점 (따로 표시)'));const list=el('dl');for(const[ko,enl]of PERSPECTIVES)list.append(el('dt',en?enl:ko),el('dd','NOT_AVAILABLE'));p.append(list,el('p',en?'Definitions await your decision; results would be one of watch / review / holding context / weight review / risk review / blocked.':'정의는 사용자 확정 대기입니다. 결과는 관찰/추가검토/보유맥락/비중재검토/위험재검토/차단 중 하나로 표시됩니다.',{class:'small'}));box.append(p);
 let drafts=0;try{drafts=read((view||globalThis).localStorage).strategies.length;}catch(_){}
 const v=el('div',undefined,{'data-version-record':''});v.append(el('h4',en?'Version record':'버전 기록'));const vl=el('ul');for(const text of [en?'v2 default · PROVISIONAL':'v2 기본 · PROVISIONAL',(en?'My drafts: ':'내 프로필 초안: ')+drafts])vl.append(el('li',text));v.append(vl);box.append(v);return box;}
// The active v2 profile is a device RAM preview. v1 drafts remain compatible comparison configurations.
function activeV2View(el,en,view){
 const api=view.QgvV2,scores=view.QgvScores,box=el('div',undefined,{'data-profile-v2':''});
 if(!api||!scores||scores.scoringDefault()!=='v2')return box;
 box.append(el('h3',en?'Default · QGV v2 · PROVISIONAL · UNCALIBRATED':'기본 · QGV v2 · PROVISIONAL · UNCALIBRATED'),
  el('p',en?'Missing factors stay unavailable. An axis needs at least 50% of its weight. Prices and V stay in RAM.':'결측 요인은 확인 불가입니다. 축 비중 50% 이상일 때만 점수를 냅니다. 가격과 V는 기기 메모리에만 둡니다.',{class:'small'}));
 const labels=FACTOR_LABELS;
 for(const axis of ['Q','G','V']){const field=el('div',undefined,{'data-v2-official-axis':axis});field.append(el('h4',axis));for(const[f,w]of Object.entries(api.WEIGHTS[axis]))field.append(el('p',labels[f][en?1:0]+' '+w+'%',{class:'small'}));box.append(field);}
 const presets=el('ul');for(const[id,p]of Object.entries(api.PRESETS))presets.append(el('li',(en?p.name_en:p.name)+' · '+['Q','G','V'].map(a=>a+' '+p.weights[a]).join(' / '),{'data-v2-preset':id}));box.append(presets,
  el('p',en?'Value-trap gate ON: industry Q percentile ≤ 30 excludes V from the total.':'가치 함정 관문 기본 켬: 업종 내 Q 백분위 30 이하이면 V를 총점에서 제외합니다.',{class:'small'}),
  el('p',en?'Historical return / MDD: NOT_AVAILABLE · PIT history is not prepared. Holdout unused.':'과거 수익률 / 최대낙폭: 확인 불가 · PIT 이력이 준비되지 않았습니다. Holdout 사용 없음.',{class:'small','data-v2-performance':'NOT_AVAILABLE'}));
 return box;
}
// S13 TARGET view of the type PREVIEW: every TARGET company, official vs custom, plus the changed config leaves.
// Python reference: investment_system/qgv/type_preview.py (tests/fixtures/s16_s13_reference_v1.json).
const TARGET_IDS=Object.freeze(['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok']);
function sameValue(a,b){if(typeof a==='number'&&typeof b==='number')return a===b;if(Array.isArray(a)&&Array.isArray(b))return a.length===b.length&&a.every((x,i)=>sameValue(x,b[i]));
 const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);if(obj(a)&&obj(b)){const ka=Object.keys(a),kb=Object.keys(b);return ka.length===kb.length&&ka.every(k=>Object.hasOwn(b,k)&&sameValue(a[k],b[k]));}return a===b;}
function configDiff(official,custom){const out=[],obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x),get=(x,k)=>Object.hasOwn(x,k)?x[k]:null;
 const walk=(a,b,path)=>{if(path==='status')return;
  if(Array.isArray(a)&&Array.isArray(b)&&[...a,...b].every(x=>obj(x)&&typeof x.id==='string')){const ids=[...new Set([...a.map(x=>x.id),...b.map(x=>x.id)])];for(const id of ids)walk(a.find(x=>x.id===id)??null,b.find(x=>x.id===id)??null,path+'.'+id);return;}
  if(obj(a)&&obj(b)){for(const k of [...new Set([...Object.keys(a),...Object.keys(b)])].sort())walk(get(a,k),get(b,k),path?path+'.'+k:k);return;}
  if(!sameValue(a,b))out.push({path,official:a===undefined?null:structuredClone(a),mine:b===undefined?null:structuredClone(b)});};
 walk(official,custom,'');return out;}
function targetTypePreview(typesPayload,qgPayload,custom,engine=engineApi(),ids=TARGET_IDS){const base=typePreview(typesPayload,qgPayload,custom,engine);
 if(base.state==='INVALID_INPUT')return{state:'INVALID_INPUT',reason:base.reason,rows:[],diff:[]};const byId=new Map(base.rows.map(r=>[r.company_id,r])),companies=typesPayload?.data?.companies;
 const rows=ids.map(id=>{const r=byId.get(id),na=reason=>({company_id:id,state:'NOT_AVAILABLE',reason,official:null,mine:null,types_changed:null,weight_delta:null});
  if(!r)return na(companies&&typeof companies==='object'&&!Object.hasOwn(companies,id)?'COMPANY_NOT_IN_PUBLIC_FILE':'PUBLIC_TYPE_METRICS_NOT_AVAILABLE');if(!r.official||!r.mine)return na('TYPE_ENGINE_INVALID_INPUT');
  const delta={};for(const p of ['Q','G','V'])delta[p]=r.mine.weights[p]-r.official.weights[p];
  return{company_id:id,state:'PREVIEW',reason:null,official:r.official,mine:r.mine,types_changed:!sameValue(r.official.selected_types,r.mine.selected_types),weight_delta:delta};});
 const ok=rows.some(r=>r.state==='PREVIEW');return{state:ok?'PREVIEW':'NOT_AVAILABLE',reason:ok?null:'PUBLIC_TYPE_METRICS_NOT_AVAILABLE',rows,diff:configDiff(copyOfficialTypes(),custom)};}
// S13 custom company types: device copy of type_config v1 (PREVIEW). Official config is never modified; the custom
// copy is used only inside '내 설정 미리보기' (never by public data, the forward ledger, virtual trading or other screens).
const CUSTOM_BADGE=['사용자 설정 · 공식 아님','User setting · not official'];
function officialTypesView(el,en){const box=el('div',undefined,{'data-type-official':''}),official=typeDefaults();
 box.append(el('p',(en?'Official · ':'공식 · ')+official.config_version+' · '+official.status+' · '+(en?'uncalibrated':'보정 전'),{class:'badge','data-type-official-badge':''}));
 const rule=t=>t.rule.kind==='ramp'||t.rule.kind==='gated_ramp'?t.rule.metric+' '+t.rule.lower+'–'+t.rule.upper+(t.rule.gate_metric?' · '+t.rule.gate_metric:''):t.rule.kind==='rank'?t.rule.metric+' ≤ '+t.rule.max_rank:'NOT_AVAILABLE · '+(t.rule.reasons||[]).join(' · ');
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-type-official-table':''}),thead=el('thead'),head=el('tr'),body=el('tbody');
 for(const h of [en?'Type':'유형',en?'Rule (price-free metric)':'기준(가격 불필요 지표)','Q','G','V'])head.append(el('th',h,{scope:'col'}));thead.append(head);
 for(const t of [...official.types,{...official.fallback,rule:{kind:'fallback'},affects_qgv:true}]){const tr=el('tr',undefined,{'data-type-official-row':t.id});
  for(const v of [t.name+' ('+t.id+')',t.rule.kind==='fallback'?(en?'No type recognized':'인식된 유형 없음'):rule(t),...['Q','G','V'].map(p=>t.affects_qgv&&t.weights?String(t.weights[p]):'—')])tr.append(el('td',v));body.append(tr);}
 table.append(thead,body);wrap.append(table);box.append(wrap);
 const m=official.mixing;box.append(el('p',(en?'Mixing: ':'혼합 규칙: ')+'minimum_membership '+m.minimum_membership+' · maximum_types '+m.maximum_types+' · pillar '+m.pillar_min+'–'+m.pillar_max+' · '+m.exclusive_pairs.map(x=>x.join('/')).join(', '),{class:'small'}));
 box.append(el('p',en?'Published company types (price-free) are on each company screen. Official values are never changed by device settings.':'기업별 공식 유형(가격 불필요)은 각 기업 화면에 있습니다. 기기 설정은 공식값을 바꾸지 않습니다.',{class:'small'}));return box;}
function mountTypes(section,status,el,view,en){
 const engine=engineApi();let state=empty(),writable=true,draft=null,selectedId=null,checked=false,tab='official';try{state=read(view.localStorage);}catch(_){writable=false;}
 status.textContent=writable?'OFFICIAL_PROVISIONAL · type_config/1 · '+(en?'Copy to edit':'복사해서 편집'):'PROFILE_STORAGE_UNREADABLE';
 const tabs=el('div',undefined,{class:'chips analysis-tabs',role:'tablist','data-type-tabs':''}),officialPanel=el('div',undefined,{role:'tabpanel','data-type-panel':'official'}),minePanel=el('div',undefined,{role:'tabpanel','data-type-panel':'mine'});
 const tabButtons={official:el('button',en?'Official types':'공식 유형',{type:'button',role:'tab','data-type-view':'official'}),mine:el('button',en?'My settings preview':'내 설정 미리보기',{type:'button',role:'tab','data-type-view':'mine'})};
 const show=next=>{tab=next;for(const[id,b]of Object.entries(tabButtons)){b.setAttribute('aria-selected',String(id===tab));}officialPanel.hidden=tab!=='official';minePanel.hidden=tab!=='mine';};
 for(const[id,b]of Object.entries(tabButtons)){b.onclick=()=>show(id);tabs.append(b);}
 const name=el('input',undefined,{id:'type-profile-name',maxlength:'60',placeholder:en?'Name':'이름'}),label=el('label',en?'Name':'이름',{for:'type-profile-name'}),editor=el('div',undefined,{'data-type-fields':''}),errors=el('p','',{'data-type-errors':'',class:'small'}),results=el('div',undefined,{'data-type-preview':'','aria-live':'polite'}),saved=el('ul',undefined,{class:'list','data-saved-types':''});
 const copy=el('button',en?'Copy official to edit':'공식값 복사해 편집',{type:'button',id:'type-copy'}),reset=el('button',en?'Start from official':'공식값으로 시작',{type:'button',id:'type-reset'}),check=el('button',en?'Preview':'미리보기',{type:'button',id:'type-preview',disabled:''}),save=el('button',en?'Save on device':'기기 저장',{type:'button',id:'type-save',disabled:''});
 const changed=()=>{checked=false;save.disabled=true;errors.textContent='';results.replaceChildren();status.textContent='PREVIEW · '+(en?'Draft changed':'초안 수정됨');};
 function numberInput(id,value,set,attrs={}){const input=el('input',undefined,{id,type:'number',step:'any',...attrs});input.value=String(value);input.oninput=()=>{set(input.value.trim()===''?NaN:Number(input.value));changed();};return input;}
 function weightsField(legend,w,prefix){const field=el('fieldset');field.append(el('legend',legend));for(const p of ['Q','G','V']){const id=prefix+'-'+p;field.append(el('label',p,{for:id}),numberInput(id,w[p],v=>{w[p]=v;},{min:'0',max:'100','data-type-weight':prefix+'-'+p}));}return field;}
 function render(){editor.replaceChildren();reset.textContent=draft?(en?'Reset to official':'공식값으로 되돌리기'):(en?'Start from official':'공식값으로 시작');if(!draft){editor.append(el('p',en?'Start from the official values or open a saved setting.':'공식값으로 시작하거나 저장한 설정을 여세요.',{class:'empty'}));check.disabled=true;save.disabled=true;return;}
  for(const t of draft.types){if(!t.affects_qgv){editor.append(el('p',t.name+' · '+(en?'exposure only, no Q/G/V weight':'노출 전용, Q/G/V 비중 없음'),{class:'small'}));continue;}const field=weightsField(t.name+' · Q/G/V',t.weights,'type-'+t.id);
   if(t.rule.kind==='ramp'||t.rule.kind==='gated_ramp')for(const k of ['lower','upper']){const id='type-'+t.id+'-'+k;field.append(el('label',t.rule.metric+' '+k,{for:id}),numberInput(id,t.rule[k],v=>{t.rule[k]=v;}));}
   else if(t.rule.kind==='unresolved')field.append(el('p','NOT_AVAILABLE · '+t.rule.reasons.join(' · '),{class:'small'}));editor.append(field);}
  editor.append(weightsField(draft.fallback.name+' · Q/G/V',draft.fallback.weights,'type-fallback'));
  const mix=el('fieldset');mix.append(el('legend',en?'Mixing':'혼합 규칙'));for(const k of ['minimum_membership','maximum_types','pillar_min','pillar_max']){const id='type-mix-'+k;mix.append(el('label',k,{for:id}),numberInput(id,draft.mixing[k],v=>{draft.mixing[k]=v;}));}editor.append(mix);check.disabled=false;save.disabled=true;}
 function renderSaved(){saved.replaceChildren();for(const p of state.types){const row=el('li',undefined,{class:'card'}),open=el('button',p.name,{type:'button','data-open-type':p.id}),remove=el('button',en?'Delete':'삭제',{type:'button','data-remove-type':p.id});
   open.onclick=()=>{selectedId=p.id;name.value=p.name;draft=structuredClone(p.config);checked=false;render();show('mine');status.textContent='PREVIEW · '+(en?'Saved configuration copied into draft':'저장 설정을 초안으로 복사했습니다.');};
   remove.onclick=()=>{if(!writable)return;try{state=write(view.localStorage,{...state,types:state.types.filter(x=>x.id!==p.id)});if(selectedId===p.id){selectedId=null;checked=false;save.disabled=true;}renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};remove.disabled=!writable;row.append(open,remove);saved.append(row);}
  if(!state.types.length)saved.append(el('li',en?'No saved type configurations.':'저장한 유형 설정이 없습니다.',{class:'empty'}));}
 const startOfficial=keepName=>{draft=copyOfficialTypes();checked=false;if(!keepName||!name.value.trim())name.value=en?'My types':'내 유형';render();results.replaceChildren();errors.textContent='';};
 copy.onclick=()=>{selectedId=null;startOfficial(false);show('mine');status.textContent='PREVIEW · '+(en?'Official type_config/1 copied':'공식 type_config/1을 복사했습니다.');};
 reset.onclick=()=>{const had=!!draft;startOfficial(true);status.textContent='PREVIEW · '+(had?(en?'Reset to official values (save to keep)':'공식값으로 되돌렸습니다(저장해야 유지)'):(en?'Official type_config/1 copied':'공식 type_config/1을 복사했습니다.'));};
 name.oninput=changed;
 check.onclick=()=>{const codes=engine?engine.validateTypeConfig(draft):['ENGINE_NOT_AVAILABLE'];let ok=!codes.length&&name.value.trim().length>0;try{if(ok)typeConfig(draft);}catch(_){ok=false;}
  checked=ok;save.disabled=!ok||!writable;errors.textContent=codes.length?codes.join(' · '):name.value.trim()?'':(en?'Enter a name.':'이름이 필요합니다.');
  status.textContent=ok?'PREVIEW · '+(en?'Configuration valid':'설정 유효'):'TYPE_CONFIG_INVALID';results.replaceChildren();if(!ok)return;const token=draft;
  Promise.resolve(view.PublicScreens?view.PublicScreens.load(view):{}).then(bundle=>{if(token!==draft||!checked)return;const r=targetTypePreview(bundle['company-types-pricefree.json'],bundle['sec-qg-factors.json'],draft,engine);renderTypePreview(r);
   if(r.state!=='PREVIEW')status.textContent='PREVIEW · '+(en?'Configuration valid · company results NOT_AVAILABLE · price-free type metrics are not published':'설정 유효 · 기업별 결과 NOT_AVAILABLE · 가격 불필요 유형 지표 미게시');}).catch(()=>{});};
 function renderTypePreview(r){results.replaceChildren();if(r.state==='INVALID_INPUT')return;const pct=w=>w?['Q','G','V'].map(p=>p+' '+(Math.round(w[p]*10)/10).toFixed(1)).join(' · '):'—',types=x=>x?(x.selected_types.join(', ')||(en?'unclassified':'미분류')):'—';
  const delta=row=>{if(row.state!=='PREVIEW')return 'NOT_AVAILABLE · '+row.reason;const parts=['Q','G','V'].filter(p=>Math.abs(row.weight_delta[p])>=0.05).map(p=>p+' '+(row.weight_delta[p]>0?'+':'−')+(Math.round(Math.abs(row.weight_delta[p])*10)/10).toFixed(1));return (row.types_changed?(en?'Types changed':'유형 변경')+(parts.length?' · ':''):'')+(parts.join(' · ')||(row.types_changed?'':(en?'Same':'같음')));};
  results.append(el('p',CUSTOM_BADGE[en?1:0]+' · PREVIEW',{class:'badge partial','data-type-custom-badge':'preview'}));
  const diff=el('div',undefined,{'data-type-diff':''});diff.append(el('h4',en?'Changed from official':'공식값에서 바꾼 항목'));if(!r.diff.length)diff.append(el('p',en?'No change from the official values.':'공식값과 같습니다.',{class:'small','data-type-diff-none':''}));
  else{const list=el('ul',undefined,{class:'list'});for(const d of r.diff)list.append(el('li',d.path+' · '+JSON.stringify(d.official)+' → '+JSON.stringify(d.mine),{'data-type-diff-path':d.path}));diff.append(list);}results.append(diff);
  const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-type-preview-table':''}),head=el('tr'),body=el('tbody'),thead=el('thead');for(const h of [en?'Company':'기업',en?'Official types':'공식 유형',en?'My types':'내 유형',en?'Official Q/G/V weights':'공식 Q/G/V 비중',en?'My Q/G/V weights':'내 Q/G/V 비중',en?'Change':'변화'])head.append(el('th',h,{scope:'col'}));thead.append(head);
  for(const row of r.rows){const tr=el('tr',undefined,{'data-type-preview-row':row.company_id,'data-type-preview-state':row.state});for(const v of [row.company_id.toUpperCase(),types(row.official),types(row.mine),pct(row.official?.weights),pct(row.mine?.weights),delta(row)])tr.append(el('td',v));body.append(tr);}
  table.append(thead,body);wrap.append(table);results.append(el('p',(en?'TARGET companies · ':'TARGET 기업 · ')+'PREVIEW · '+(en?'RAM only · adjusted QGV needs V (prices): NOT_AVAILABLE':'메모리 전용 · 유형조정 QGV는 V(가격) 필요: NOT_AVAILABLE'),{class:'small'}),wrap);}
 save.onclick=()=>{if(!checked||!writable)return;try{const id=selectedId||'type-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8);state=write(view.localStorage,{...state,types:[...state.types.filter(x=>x.id!==id),{id,name:name.value.trim(),config:draft}]});selectedId=id;status.textContent='PREVIEW · '+(en?'Saved on this device':'이 기기에 저장했습니다.');renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};
 officialPanel.append(officialTypesView(el,en),copy);
 minePanel.append(el('p',CUSTOM_BADGE[en?1:0],{class:'badge partial','data-type-custom-badge':''}),
  el('p',en?'Stored only on this device (included in the device backup with your profiles). Never changes public data, the forward ledger, virtual trading or official screens.':'이 기기에만 저장됩니다(프로필과 함께 기기 백업에 포함). 공개 데이터·전진검증 원장·가상매매·공식 화면을 바꾸지 않습니다.',{class:'small','data-type-device-note':''}),
  label,name,reset,editor,check,errors,results,save,el('h3',en?'Saved type configurations':'저장한 유형 설정'),saved);
 section.append(el('p',en?'Industry, strategy theme and investment type are separate axes. Raw QGV and type-adjusted QGV are both kept.':'산업·전략 테마·투자 유형은 서로 다른 축입니다. 원 QGV와 유형조정 QGV를 함께 보존합니다.',{class:'small'}),tabs,officialPanel,minePanel);render();renderSaved();show('official');
}
// RAM-only PREVIEW: published price-free Q/G factors under official vs draft leaf weights. Never stored.
function previewRanks(payload,draft,engine){
 const companies=payload?.data?.companies;if(!engine||!companies||typeof companies!=='object')return{state:'NOT_AVAILABLE',reason:'PUBLIC_QG_NOT_AVAILABLE',rows:[]};
 const rows=[];for(const[id,r]of Object.entries(companies)){if(!r||r.state==='NOT_AVAILABLE')continue;const observations={};for(const[f,v]of Object.entries(r.factors||{}))if(v&&v.score!==null&&v.state!=='NOT_AVAILABLE')observations[f]={score:v.score,quality:v.state==='LIVE'?'OK':'STALE_DATA'};
  const official=engine.strategy({observations}),mine=engine.strategy({observations,user_weights:draft}),value=x=>typeof x?.qg_preview_total==='number'?x.qg_preview_total:null,axis=(x,a)=>typeof x?.axes?.[a]?.score==='number'?x.axes[a].score:null;rows.push({company_id:id,official:value(official),mine:value(mine),official_q:axis(official,'Q'),official_g:axis(official,'G'),mine_q:axis(mine,'Q'),mine_g:axis(mine,'G')});}
 const rank=key=>{const ranked=rows.filter(r=>r[key]!==null).sort((a,b)=>b[key]-a[key]||(a.company_id<b.company_id?-1:1));ranked.forEach((r,i)=>{r[key+'_rank']=i+1;});for(const r of rows)if(r[key]===null)r[key+'_rank']=null;};
 rank('official');rank('mine');for(const r of rows)r.rank_change=r.official_rank!==null&&r.mine_rank!==null?r.official_rank-r.mine_rank:null;
 rows.sort((a,b)=>(a.mine_rank??1e9)-(b.mine_rank??1e9)||(a.company_id<b.company_id?-1:1));
 const any=rows.some(r=>r.mine_q!==null||r.mine_g!==null);return{state:any?'PREVIEW':'NOT_AVAILABLE',reason:any?null:'PUBLIC_QG_NOT_AVAILABLE',rows};
}
/* QGV v2 two-level weights · PERSONAL_PREVIEW (owner directive 2026-10-18 §4.2/§4.3). Axis Q/G/V weights and the 15 inner factor
   weights are edited, compared with the official result and saved as versioned personal profiles in THIS browser only
   (V2_KEY, schema device-profile-drafts/2; not in the device backup). Scores are recomputed in RAM by QgvScores.compute
   ({weights}) under its separate personal key; the official score, rank, published files and ledgers never change. v1 drafts
   (KEY, schema /1) stay readable and are labelled 'v1 미리보기'. */
const V2_KEY='investment.web.v1.profile-drafts-v2',V2_SCHEMA='device-profile-drafts/2',qgvApi=()=>node?require('./qgv-v2.js'):globalThis.QgvV2;
const FACTOR_LABELS={q_profitability:['수익성','Profitability'],q_moat_proxy:['해자 대리','Moat proxy'],q_earnings_quality:['이익의 질','Earnings quality'],q_financial_safety:['재무 안전','Financial safety'],q_capital_allocation:['자본 배분','Capital allocation'],g_revenue_growth:['매출 성장','Revenue growth'],g_per_share_growth:['주당 성장','Per-share growth'],g_growth_efficiency:['성장 효율','Growth efficiency'],g_consistency:['성장 일관성','Growth consistency'],g_recent_acceleration:['최근 가속','Recent acceleration'],v_earnings_yield:['이익 수익률','Earnings yield'],v_fcf_yield:['FCF 수익률','FCF yield'],v_vs_industry:['업종 대비','Industry comparison'],v_vs_own_history:['자기 과거 대비','Own history'],v_expectation_check:['기대 점검','Expectation check']};
const AXIS_NAMES={Q:['Q 우량','Q quality'],G:['G 성장','G growth'],V:['V 가치','V value']};
/* Product presets (directive §0-1, §4.3; owner decision 2026-10-18 '프리셋 v0.1 후보 정의'): 공격형/균형형/수비형 are the v0.1
   candidates QgvV2.USER_PRESETS (ids user-preset/<key>@0.1, CANDIDATE_UNVALIDATED, official inner weights, type weights and gate on).
   Selecting one loads its tree into the editor (PERSONAL_PREVIEW only); it is never mapped to the code presets
   balanced/quality/growth/value, which stay available under their own label, and never replaces the official default. */
const PRODUCT_PRESETS=Object.freeze([['aggressive',['공격형','Aggressive']],['balanced',['균형형','Balanced']],['defensive',['수비형','Defensive']],['custom',['사용자 설정','Custom']]]);
const CANDIDATE_LABEL=Object.freeze(['v0.1 후보 · 검증 전 · 공식 기본값 아님','v0.1 candidate · not validated · not the official default']);
// The v0.1 candidate definition of a product preset key (null for 'custom' or an unknown key).
function candidateFor(key,api=qgvApi()){const id=Object.keys(api.USER_PRESETS||{}).find(k=>api.USER_PRESETS[k].key===key);return id?api.userPreset(id):null;}
/* Weight stages (owner decision 2026-10-18): reason words for the engine's change codes (QgvV2 weight_stages). Display only. */
const STAGE_REASON={TYPE_WEIGHTS:['기업 유형 반영','Company-type adjustment'],RENORMALIZED:['다른 축·요인이 빠져 남은 비중으로 다시 나눔','Renormalized: another axis or factor left out'],
 MISSING:['결측 · 남은 요인 비중으로 다시 나눔(0점 아님)','Missing · remaining weights renormalized (never 0)'],AXIS_NOT_AVAILABLE:['축 산출 불가 · 총점에서 제외','Axis not calculated · left out of the total'],
 AXIS_NOT_USED:['축이 총점에서 빠짐','Axis left out of the total'],VALUE_TRAP_GATE:['가치 함정 관문: 업종 내 Q 백분위 30 이하 · V 제외','Value-trap gate: industry Q percentile ≤ 30 · V dropped'],
 ZERO_WEIGHT:['0 = 제외(결측 아님)','0 = left out (not missing)'],TOTAL_NOT_AVAILABLE:['총점 산출 불가 · 적용 비중 없음','No total · no applied weights'],
 INNER_NOT_DERIVABLE:['공개 축 점수 · 세부 비중 산출 불가','Published axis score · inner shares not derivable'],
 AXIS_WEIGHT_INSUFFICIENT:['비중 50% 미만','below 50% of the weight'],AXIS_NOT_PUBLISHED:['공개 축 점수 없음','no published axis score'],PRICE_IDENTITY_CONFLICT:['가격 식별 충돌로 총점 사용 중지','Price identity conflict: total not used']};
/* Profile summary of the three stages over the personal rows of a QgvScores.compute result: (a) base axis shares, (b) mean
   type-adjusted axis weights (rows with stages), (c) mean applied axis weights (rows with a total) and how many rows each
   change reason touched. All values are the engine's; nothing is recomputed here. */
function stageSummary(mine){const P=['Q','G','V'],rows=Object.values(mine&&mine.rows?mine.rows:{}).map(r=>r.personal&&r.personal.weight_stages).filter(Boolean);
 const out={rows:rows.length,base:rows.length?{...rows[0].base.axis}:null,type:{n:rows.length,changed:0,mean:null},applied:{n:0,mean:null},counts:{VALUE_TRAP_GATE:0,MISSING:0,TOTAL_NOT_AVAILABLE:0,STOPPED:0,AXIS_NOT_AVAILABLE:{Q:0,G:0,V:0}}};
 if(!rows.length)return out;const tsum={Q:0,G:0,V:0},asum={Q:0,G:0,V:0};
 for(const w of rows){for(const p of P)tsum[p]+=w.type_adjusted.axis[p];if(w.type_adjusted.changes.length)out.type.changed++;
  if(w.display_stop){out.counts.STOPPED++;continue;}if(w.applied.state!=='READY'){out.counts.TOTAL_NOT_AVAILABLE++;}else{out.applied.n++;for(const p of P)asum[p]+=w.applied.axis[p];}
  const c=w.applied.changes;if(c.some(x=>x.reason==='VALUE_TRAP_GATE'))out.counts.VALUE_TRAP_GATE++;if(c.some(x=>x.reason==='MISSING'))out.counts.MISSING++;for(const p of P)if(c.some(x=>x.level==='axis'&&x.key===p&&x.reason==='AXIS_NOT_AVAILABLE'))out.counts.AXIS_NOT_AVAILABLE[p]++;}
 out.type.mean=Object.fromEntries(P.map(p=>[p,tsum[p]/rows.length]));if(out.applied.n)out.applied.mean=Object.fromEntries(P.map(p=>[p,asum[p]/out.applied.n]));return out;}
const DECISION_URL='https://github.com/kco994553-star/Investment-System1/blob/claude/investment-system-top500-validation-alrugm/implementation/docs/USER_DECISIONS_PENDING.md';
function validName(n){return typeof n==='string'&&n.trim().length>0&&n.length<=60&&!/[\x00-\x1f]/.test(n);}
function emptyV2(){return{schema:V2_SCHEMA,profiles:[]};}
function validateV2(v){keys(v,['schema','profiles']);need(v.schema===V2_SCHEMA&&Array.isArray(v.profiles)&&v.profiles.length<=20);const ids=new Set();
 return{schema:V2_SCHEMA,profiles:v.profiles.map(p=>{keys(p,['id','name','version','saved_at','weights','type_weights','gate']);
  need(typeof p.id==='string'&&/^qgv2-[a-z0-9-]{1,72}$/.test(p.id)&&!ids.has(p.id)&&validName(p.name)&&Number.isInteger(p.version)&&p.version>=1&&p.version<=100000&&typeof p.saved_at==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(p.saved_at)&&typeof p.type_weights==='boolean'&&typeof p.gate==='boolean');ids.add(p.id);
  let w=null;try{w=qgvApi().validateWeights(p.weights);}catch(_){w=null;}need(w);return{id:p.id,name:p.name,version:p.version,saved_at:p.saved_at,weights:w,type_weights:p.type_weights,gate:p.gate};})};}
function readV2(storage){const raw=storage.getItem(V2_KEY);return raw?validateV2(JSON.parse(raw)):emptyV2();}
function writeV2(storage,v){const next=validateV2(v);storage.setItem(V2_KEY,JSON.stringify(next));return next;}
// A save of an open profile is its next version (same id); otherwise a new profile at version 1.
function saveV2(doc,{id=null,name,weights,type_weights=true,gate=true},now=new Date()){const prev=id?doc.profiles.find(p=>p.id===id):null,nid=prev?prev.id:'qgv2-'+now.getTime().toString(36)+'-'+Math.random().toString(36).slice(2,8);
 const p={id:nid,name:String(name||'').trim(),version:prev?prev.version+1:1,saved_at:now.toISOString(),weights:structuredClone(weights),type_weights:Boolean(type_weights),gate:Boolean(gate)};need(validName(p.name));
 return validateV2({schema:V2_SCHEMA,profiles:[...doc.profiles.filter(x=>x.id!==nid),p]});}
const finiteNum=v=>typeof v==='number'&&Number.isFinite(v);
/* Within-axis share and total contribution share (%) of a tree, before type weights: axis p share = w_p / Σw; factor share
   inside p = w_f / Σ inner p; contribution = axis share × factor share. Sum 0 or an invalid value -> null (never a guess). */
function weightShares(tree){const api=qgvApi(),out={axis_sum:null,axis:{},inner_sum:{},inner:{},total:{}};let s=0,ok=true;for(const p of api.PILLARS){const v=tree.axis[p];if(!finiteNum(v)||v<0)ok=false;else s+=v;}out.axis_sum=ok?s:null;
 for(const p of api.PILLARS){out.axis[p]=ok&&s>0?100*tree.axis[p]/s:null;let t=0,good=true;for(const f of Object.keys(api.WEIGHTS[p])){const v=tree.inner[p][f];if(!finiteNum(v)||v<0)good=false;else t+=v;}out.inner_sum[p]=good?t:null;out.inner[p]={};out.total[p]={};
  for(const f of Object.keys(api.WEIGHTS[p])){out.inner[p][f]=good&&t>0?100*tree.inner[p][f]/t:null;out.total[p][f]=out.inner[p][f]!==null&&out.axis[p]!==null?out.axis[p]*out.inner[p][f]/100:null;}}
 return out;}
// Scale the unlocked values so the group totals 100; locked values stay. null when the locked values alone exceed 100 or a value is invalid.
function fitTo100(values,locks={}){const ids=Object.keys(values);if(ids.some(k=>!finiteNum(values[k])||values[k]<0))return null;let locked=0,free=0;for(const k of ids){if(locks[k])locked+=values[k];else free+=values[k];}
 const open=ids.filter(k=>!locks[k]);if(locked>100+1e-9||!open.length)return locked<=100+1e-9&&Math.abs(locked-100)<1e-9?{...values}:null;const out={...values},room=100-locked;
 for(const k of open)out[k]=free>0?values[k]*room/free:room/open.length;return out;}
// Which rule a tree breaks, in words (null when valid).
function treeProblem(tree,en){const api=qgvApi();for(const p of api.PILLARS){const vals=[tree.axis[p],...Object.values(tree.inner[p])];if(vals.some(v=>!finiteNum(v)||v<0||v>100))return en?'Enter numbers from 0 to 100.':'0~100 사이 숫자만 입력할 수 있습니다.';}
 const sh=weightShares(tree);if(!(sh.axis_sum>0))return en?'The axis weights sum to 0: nothing to score.':'축 비중 합계가 0이면 계산할 수 없습니다.';for(const p of api.PILLARS)if(!(sh.inner_sum[p]>0))return(en?p+' inner weights sum to 0.':p+' 축 내부 비중 합계가 0이면 계산할 수 없습니다.');
 try{api.validateWeights(tree);}catch(_){return 'WEIGHTS_INVALID';}return null;}
/* Pure compare rows: official result (QgvScores.compute without weights) vs the personal rows of a compute with weights. Rows are
   ordered by the personal rank, then the personal QG 참고 목록 (V 미포함, D11) in its own order, then NA by ticker; ranks are each
   result's own (the official rank is never renumbered). qg = {order, reason} of a total from Q·G only (no rank), else null. */
function compareRows(official,mine){const side=(row,p,rank,qg)=>{if(!p)return null;const cov=p.coverage&&p.coverage.axes?p.coverage.axes:null;
  return{q:p.q,g:p.g,v:p.v,total:p.total,rank:Number.isInteger(rank)?rank:null,eligible:Number.isInteger(rank),qg:!Number.isInteger(rank)&&qg&&typeof qg==='object'?{order:Number.isInteger(qg.order)?qg.order:null,reason:qg.reason||null}:null,gate:p.value_trap_gate===true?'TRAP':(p.flags||[]).includes('GATE_NOT_EVALUATED')?'NOT_EVALUATED':'CLEAR',factors_available:p.factors_available,factors_total:p.factors_total,
   coverage:cov?Object.fromEntries(['Q','G','V'].map(a=>[a,{custom:finiteNum(cov[a].weight_available)?cov[a].weight_available:null,official:finiteNum(cov[a].weight_available_official)?cov[a].weight_available_official:finiteNum(cov[a].weight_available)?cov[a].weight_available:null,status:cov[a].status}])):null};};
 const rows=[];for(const[cid,r]of Object.entries(official&&official.rows?official.rows:{})){const m=mine&&mine.rows?mine.rows[cid]:null,o=side(r,r.primary,r.rank,r.qg_reference),x=m&&m.personal?side(m,m.personal,m.personal_rank,m.personal_qg_reference):null;
  rows.push({company_id:cid,ticker:r.ticker,official:o,mine:x,rank_change:o&&x&&o.rank!==null&&x.rank!==null?o.rank-x.rank:null});}
 const key=s=>!s?[2,0]:s.rank!==null?[0,s.rank]:s.qg&&s.qg.order!==null?[1,s.qg.order]:[2,0];
 rows.sort((a,b)=>{const x=key(a.mine),y=key(b.mine);return x[0]-y[0]||x[1]-y[1]||String(a.ticker).localeCompare(String(b.ticker));});return rows;}
let v2CtxPromise=null;
// Public inputs and identities for the S13 compare (the same public files as S06), loaded once per page. No price (DC-31).
function defaultV2Context(view){
 if(!v2CtxPromise)v2CtxPromise=(async()=>{const inputs=view.Qgv2Inputs?await view.Qgv2Inputs.load(view):null;let catalog=null;try{const r=await view.fetch('actual-catalog.json',{cache:'no-store'});if(r.ok)catalog=await r.json();}catch(_){catalog=null;}
  let identities=[];try{identities=catalog&&view.DeviceWatchlist?view.DeviceWatchlist.identities(catalog):[];}catch(_){identities=[];}return{inputs,identities,catalog};})().catch(e=>{v2CtxPromise=null;throw e;});
 return v2CtxPromise;}
function mountV2(box,el,view,en,{v2Context=defaultV2Context}={}){
 const api=view.QgvV2,QS=view.QgvScores;if(!api||!QS||typeof api.validateWeights!=='function'){box.append(el('p',en?'QGV v2 engine not loaded.':'QGV v2 엔진을 불러오지 못했습니다.',{class:'small'}));return;}
 const T=(ko,e)=>en?e:ko,pct=v=>finiteNum(v)?(Math.round(v*10)/10).toFixed(1)+'%':'—',num=v=>finiteNum(v)?(Math.round(v*10)/10).toFixed(1):'—';
 let doc2=emptyV2(),writable=true;try{doc2=readV2(view.localStorage);}catch(_){writable=false;}
 const official=()=>({tree:api.officialWeights(),locks:{axis:{Q:false,G:false,V:false},inner:Object.fromEntries(api.PILLARS.map(p=>[p,Object.fromEntries(Object.keys(api.WEIGHTS[p]).map(f=>[f,false]))]))}});
 let st={...official(),typeWeights:true,gate:true,product:'custom',selectedId:null,name:'',company:null,result:null,token:0};
 const status=el('p',T('개인 설정 미리보기 · 공식 점수 아님','Personal setting preview · not an official score'),{role:'status','data-qgv2w-status':''}),body=el('div');
 box.append(el('h3',T('QGV v2 두 단계 가중치 · 개인 설정 미리보기','QGV v2 two-level weights · personal preview')),
  el('p',QS.PERSONAL_LABEL?QS.PERSONAL_LABEL[en?1:0]:T('개인 설정 미리보기 · 공식 점수 아님','Personal setting preview · not an official score'),{class:'badge partial','data-qgv2w-badge':''}),
  el('p',T('축 비중(Q/G/V)과 축마다 5개 세부 요인 비중을 바꿔 이 기기 메모리에서 다시 계산합니다. 공식 점수·순위·게시 파일·원장은 바뀌지 않습니다. 이 브라우저에만 저장됩니다(기기 백업 미포함).','Change the Q/G/V axis weights and the 5 factor weights of each axis and recalculate in this device’s memory. Official scores, ranks, published files and ledgers do not change. Saved in this browser only (not in the device backup).'),{class:'small'}),status,body);
 const changed=()=>{st.result=null;st.token++;};
 function render(){body.replaceChildren();const sh=weightShares(st.tree),problem=treeProblem(st.tree,en);
  // Product presets: 공격/균형/수비 = the v0.1 candidates (CANDIDATE_UNVALIDATED); selecting one fills the editor below.
  const prod=el('div',undefined,{class:'chips',role:'group','aria-label':T('제품 프리셋','Product presets'),'data-qgv2w-product-presets':''});
  for(const[id,[ko,e]]of PRODUCT_PRESETS){const b=el('button',en?e:ko,{type:'button','data-product-preset':id,'aria-pressed':String(st.product===id)});b.onclick=()=>{
    if(id==='custom'){st.product='custom';render();return;}const d=candidateFor(id,api);if(!d)return;
    st.tree=structuredClone(d.weights);st.locks=official().locks;st.typeWeights=d.type_weights;st.gate=d.gate;st.product=id;st.selectedId=null;st.name=(en?d.name_en:d.name)+' v'+d.version;changed();
    status.textContent=T(d.name+' v'+d.version+' 후보(검증 전)를 불러왔습니다 · 축·세부 비중을 바꿔 개인 프로필로 저장할 수 있습니다.','Loaded the '+d.name_en+' v'+d.version+' candidate (not validated) · edit both levels and save as a personal profile.');render();};prod.append(b);}
  body.append(el('h4',T('프리셋','Presets')),prod);
  const cand=st.product!=='custom'?candidateFor(st.product,api):null;
  if(cand){const card=el('div',undefined,{class:'card','data-product-preset-status':st.product,'data-user-preset-id':cand.id});card.append(el('p',CANDIDATE_LABEL[en?1:0],{class:'badge partial','data-user-preset-label':''}));
   const dl=el('ul',undefined,{class:'list','data-user-preset-fields':''}),add=(ko,e,v,attr)=>{const li=el('li',undefined,{class:'small'});li.append(el('strong',(en?e:ko)+': '),el('span',v,attr?{[attr]:''}:{}));dl.append(li);};
   add('ID','ID',cand.id,'data-user-preset-ident');add('축 비중','Axis weights','Q '+cand.weights.axis.Q+' / G '+cand.weights.axis.G+' / V '+cand.weights.axis.V,'data-user-preset-axis');
   add('세부 요인 비중','Inner factor weights',T('현재 공식 15요인 비중 공통 · ','Current official 15-factor weights · ')+api.PILLARS.map(p=>p+' '+Object.values(cand.weights.inner[p]).join('/')).join(' · '),'data-user-preset-inner');
   add('기업 유형 조정 · 가치 함정 관문','Type adjustment · value-trap gate',T('기본 켬','On by default'),'data-user-preset-toggles');
   add('검증 상태','Validation status',T('검증 전 후보 ('+cand.status+') · 과거 수익률·최대낙폭 확인 불가','Candidate before validation ('+cand.status+') · historical return / MDD not available'),'data-user-preset-validation');
   add('유지되는 안전 조건','Safety conditions kept',T('축·총점 50% 충족 규칙 · 가치 함정 관문 · 계산 규칙 버전 혼합 금지 · 식별 충돌 철회 제외 · 순위·후보 자격 조건 그대로','50% coverage rule · value-trap gate · no mixed calculation versions · withdrawn identities excluded · rank and candidate rules unchanged'));card.append(dl);
   card.append(el('p',T('공식 기본값(균형 34/33/33 · 관문 켬)을 바꾸지 않는 별도 ID·버전의 후보입니다. 기존 balanced/quality/growth/value와 다른 프리셋입니다. 수비형이라는 이름이 손실 방지나 낮은 변동성을 보장하지 않습니다. 아래에서 축·세부 비중을 모두 바꿔 개인 프로필로 저장할 수 있습니다. ','A candidate with its own id and version; it does not change the official default (balanced 34/33/33, gate on) and is not one of the code presets balanced/quality/growth/value. "Defensive" does not promise loss protection or low volatility. Edit both levels below and save as a personal profile. '),{class:'small'}),
    el('p','',{class:'small','data-product-preset-modified':''}),el('a',T('결정 기록 보기','Open the decision record'),{href:DECISION_URL,target:'_blank',rel:'noopener noreferrer','data-product-preset-decision':''}));body.append(card);}
  // The four code presets stay under their own label: they only fill the editor's starting axis weights.
  const code=el('div',undefined,{class:'chips',role:'group','aria-label':T('기존 축 비중 프리셋','Existing axis-weight presets'),'data-qgv2w-code-presets':''});
  for(const[id,p]of Object.entries(api.PRESETS)){const b=el('button',id+' · '+(en?p.name_en:p.name)+' · Q'+p.weights.Q+'/G'+p.weights.G+'/V'+p.weights.V,{type:'button','data-code-preset':id});b.onclick=()=>{const o=official();st.tree=api.officialWeights(id);st.locks=o.locks;st.product='custom';changed();status.textContent=T('기존 축 비중 프리셋 '+id+'을 시작값으로 불러왔습니다(세부 요인은 공식값).','Loaded code preset '+id+' as the start (official inner weights).');render();};code.append(b);}
  body.append(el('h4',T('기존 축 비중 프리셋(balanced/quality/growth/value)','Existing axis-weight presets (balanced/quality/growth/value)')),code);
  // Editor rows: slider + number + lock, with within-axis share and total contribution share.
  const row=(path,label,value,locked,share)=>{const id='qgv2w-'+path.replaceAll('.','-'),r=el('div',undefined,{class:'chips qgv2w-row','data-qgv2w-row':path});
   const range=el('input',undefined,{type:'range',min:'0',max:'100',step:'1','aria-label':label+T(' 슬라이더',' slider'),'data-qgv2w-range':path}),input=el('input',undefined,{id,type:'number',min:'0',max:'100',step:'any',inputmode:'decimal','data-qgv2w':path}),lock=el('input',undefined,{type:'checkbox','data-qgv2w-lock':path,'aria-label':label+T(' 잠금',' lock')});
   range.value=String(finiteNum(value)?Math.round(value):0);input.value=finiteNum(value)?String(value):'';lock.checked=locked;range.disabled=input.disabled=locked;
   const set=v=>{const[kind,p,f]=path.split('.');if(kind==='axis')st.tree.axis[p]=v;else st.tree.inner[p][f]=v;changed();refresh();};
   range.oninput=()=>{input.value=range.value;set(Number(range.value));};input.oninput=()=>{const v=input.value.trim()===''?NaN:Number(input.value);if(finiteNum(v))range.value=String(Math.round(v));set(v);};
   lock.onchange=()=>{const[kind,p,f]=path.split('.');if(kind==='axis')st.locks.axis[p]=lock.checked;else st.locks.inner[p][f]=lock.checked;range.disabled=input.disabled=lock.checked;};
   const lockLabel=el('label',T('잠금','Lock'),{class:'small'});lockLabel.prepend(lock);r.append(el('label',label,{for:id}),range,input,lockLabel,el('span',share,{class:'small','data-qgv2w-share':path}));return r;};
  const axisBox=el('fieldset',undefined,{'data-qgv2w-axes':''});axisBox.append(el('legend',T('1단계 · 축 비중 (Q/G/V)','Level 1 · axis weights (Q/G/V)')));
  for(const p of api.PILLARS)axisBox.append(row('axis.'+p,AXIS_NAMES[p][en?1:0],st.tree.axis[p],st.locks.axis[p],axisShareText(sh,p)));
  axisBox.append(el('p','',{class:'small','data-qgv2w-sum':'axis'}),fitButton('axis'));body.append(axisBox);
  for(const p of api.PILLARS){const f=el('fieldset',undefined,{'data-qgv2w-inner':p});f.append(el('legend',T('2단계 · ','Level 2 · ')+AXIS_NAMES[p][en?1:0]+T(' 세부 요인 비중',' factor weights')));
   for(const k of Object.keys(api.WEIGHTS[p]))f.append(row('inner.'+p+'.'+k,FACTOR_LABELS[k][en?1:0]+' ('+p+(Object.keys(api.WEIGHTS[p]).indexOf(k)+1)+')',st.tree.inner[p][k],st.locks.inner[p][k],innerShareText(sh,p,k)));
   f.append(el('p','',{class:'small','data-qgv2w-sum':p}),fitButton(p));body.append(f);}
  const types=el('label',T(' 기업 유형 비중을 축 비중 위에 적용(프리셋과 같은 방식 · 기본 켬)',' Apply company-type weights on top of the axis weights (as on presets · default on)'),{class:'small'}),tbox=el('input',undefined,{type:'checkbox','data-qgv2w-types':''});tbox.checked=st.typeWeights;tbox.onchange=()=>{st.typeWeights=tbox.checked;changed();refresh();};types.prepend(tbox);
  const gate=el('label',T(' 가치 함정 관문(업종 내 Q 백분위 30 이하이면 V 제외 · 기본 켬)',' Value-trap gate (industry Q percentile ≤ 30 drops V · default on)'),{class:'small'}),gbox=el('input',undefined,{type:'checkbox','data-qgv2w-gate':''});gbox.checked=st.gate;gbox.onchange=()=>{st.gate=gbox.checked;changed();refresh();};gate.prepend(gbox);
  body.append(el('div',undefined,{class:'stack'}),types,el('br'),gate,el('p',T('0 = 그 요인(또는 축)을 계산에서 뺍니다(결측이 아님). 결측 요인은 0점으로 채우지 않고, 남은 요인 비중으로 다시 나눕니다. 축은 내 설정 비중의 50% 이상 요인이 있어야 점수를 냅니다. 원래 가중치 기준 충족률도 함께 보여 줍니다. 잠근 값은 직접 바꾸거나 100으로 맞출 때 바뀌지 않습니다.','0 = the factor (or axis) is left out (not missing). Missing factors are never filled with 0; the remaining weights are renormalized. An axis needs factors worth ≥ 50% of your weights; the fill rate against the original weights is shown too. Locked values do not change, also not when fitting to 100.'),{class:'small','data-qgv2w-rules':''}));
  const err=el('p','',{class:'small','data-qgv2w-error':'','aria-live':'polite'});body.append(err);
  const actions=el('div',undefined,{class:'chips'}),reset=el('button',T('공식값으로 초기화','Reset to official'),{type:'button','data-qgv2w-reset':''}),cmp=el('button',T('변경 전후 비교','Compare before / after'),{type:'button','data-qgv2w-compare':''});
  reset.onclick=()=>{const o=official();st.tree=o.tree;st.locks=o.locks;st.typeWeights=true;st.gate=true;st.product='custom';changed();status.textContent=T('공식값(균형 34/33/33 · 공식 세부 비중 · 관문 켬)으로 되돌렸습니다.','Reset to official (balanced 34/33/33, official inner weights, gate on).');render();};
  cmp.onclick=()=>compare();actions.append(reset,cmp);body.append(actions);
  const results=el('div',undefined,{'data-qgv2w-results':'','aria-live':'polite'});body.append(results);
  const name=el('input',undefined,{id:'qgv2w-name',maxlength:'60',placeholder:T('프로필 이름','Profile name')}),save=el('button',T('이 브라우저에 저장','Save in this browser'),{type:'button','data-qgv2w-save':''});name.value=st.name;name.oninput=()=>{st.name=name.value;refresh();};
  save.onclick=()=>{if(!writable||treeProblem(st.tree,en)||!validName(st.name))return;try{doc2=writeV2(view.localStorage,saveV2(doc2,{id:st.selectedId,name:st.name,weights:st.tree,type_weights:st.typeWeights,gate:st.gate}));const p=doc2.profiles[doc2.profiles.length-1];st.selectedId=p.id;status.textContent=T('이 브라우저에 저장했습니다 · v','Saved in this browser · v')+p.version;renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};
  body.append(el('label',T('이름','Name'),{for:'qgv2w-name'}),name,save,el('p',writable?T('설정(가중치·토글)만 저장합니다. 점수·순위·가격은 저장하지 않습니다.','Only the settings (weights, toggles) are saved; no score, order or price.'):'PROFILE_STORAGE_UNREADABLE',{class:'small','data-qgv2w-storage':writable?'OK':'UNREADABLE'}));
  const saved=el('ul',undefined,{class:'list','data-qgv2w-saved':''});body.append(el('h4',T('저장한 두 단계 프로필','Saved two-level profiles')),saved);
  function renderSaved(){saved.replaceChildren();for(const p of doc2.profiles){const li=el('li',undefined,{class:'card'}),open=el('button',p.name+' · v'+p.version+' · '+p.saved_at.slice(0,10),{type:'button','data-qgv2w-open':p.id}),del=el('button',T('삭제','Delete'),{type:'button','data-qgv2w-remove':p.id});
    open.onclick=()=>{st.tree=structuredClone(p.weights);st.locks=official().locks;st.typeWeights=p.type_weights;st.gate=p.gate;st.selectedId=p.id;st.name=p.name;st.product='custom';changed();status.textContent=T('저장한 프로필을 열었습니다 · 다시 저장하면 v','Opened the saved profile · saving again makes v')+(p.version+1);render();};
    del.disabled=!writable;del.onclick=()=>{try{doc2=writeV2(view.localStorage,{...doc2,profiles:doc2.profiles.filter(x=>x.id!==p.id)});if(st.selectedId===p.id)st.selectedId=null;renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};li.append(open,del);saved.append(li);}
   let v1=[];try{v1=read(view.localStorage).strategies;}catch(_){v1=[];}
   for(const p of v1)saved.append(el('li',p.name+' · '+T('v1 미리보기 · 공식 v2 점수 아님 · 아래 v1 편집기에서 열기','v1 preview · not the official v2 score · open in the v1 editor below'),{class:'small','data-qgv2w-v1':p.id}));
   if(!doc2.profiles.length&&!v1.length)saved.append(el('li',T('저장한 프로필이 없습니다.','No saved profiles.'),{class:'empty'}));}
  renderSaved();
  function fitButton(group){const b=el('button',T('합계 100으로 맞추기','Fit to 100'),{type:'button','data-qgv2w-fit':group});b.onclick=()=>{const vals=group==='axis'?st.tree.axis:st.tree.inner[group],locks=group==='axis'?st.locks.axis:st.locks.inner[group],next=fitTo100(vals,locks);
   if(!next){err.textContent=T('잠근 값의 합이 100을 넘거나 잘못된 값이 있어 맞출 수 없습니다.','Cannot fit: locked values exceed 100 or a value is invalid.');return;}if(group==='axis')st.tree.axis=next;else st.tree.inner[group]=next;changed();render();};return b;}
  function refresh(){const s=weightShares(st.tree),bad=treeProblem(st.tree,en);for(const p of api.PILLARS){const n=body.querySelector('[data-qgv2w-share="axis.'+p+'"]');if(n)n.textContent=axisShareText(s,p);for(const k of Object.keys(api.WEIGHTS[p])){const m=body.querySelector('[data-qgv2w-share="inner.'+p+'.'+k+'"]');if(m)m.textContent=innerShareText(s,p,k);}
    const sum=body.querySelector('[data-qgv2w-sum="'+p+'"]');if(sum)sum.textContent=sumText(s.inner_sum[p]);}
   const a=body.querySelector('[data-qgv2w-sum="axis"]');if(a)a.textContent=sumText(s.axis_sum);err.textContent=bad||'';
   const mod=body.querySelector('[data-product-preset-modified]');if(mod){const m=modified();mod.dataset.productPresetModified=String(m);mod.textContent=m?T('수정됨 · 후보 값과 다릅니다 · 저장하면 내 개인 프로필(사용자 설정)이 됩니다','Modified · differs from the candidate · saving makes a personal profile (custom)'):T('후보 값 그대로 · 유형 조정·관문 켬','Candidate values as defined · type adjustment and gate on');}cmp.disabled=!!bad;save.disabled=!!bad||!writable||!validName(st.name);
   if(!st.result)results.replaceChildren();}
  function sumText(v){return v===null?T('합계 — (잘못된 값)','Sum — (invalid value)'):T('합계 ','Sum ')+num(v)+(Math.abs(v-100)<1e-9?'':T(' · 계산 때 100으로 정규화',' · normalized to 100 when calculating'));}
  function compare(){if(treeProblem(st.tree,en))return;const token=++st.token;results.replaceChildren(el('p',T('계산 중…','Calculating…'),{class:'small'}));
   Promise.resolve(v2Context(view)).then(async ctx=>{if(token!==st.token)return;
    /* D12 + 'V 일치' (owner 2026-10-19) + DC-31: '공식' here is the ONE official evaluation every other screen shows: the shared
       QgvScores.officialPage (the central publication's Q·G·V, totals and ranks over the same identities and Universe rank
       population as S06, the company pages, the radar, the V panel and the candidates); '내 설정' is the personal result recomputed
       from the published factor scores over that same population (QgvScores.compute({publication, weights}); without a
       publication the price-free Q·G compute with every V NA, never a device V). The TARGET rows are listed, as before. */
    let R=null;try{R=ctx.inputs&&typeof QS.officialPage==='function'?QS.officialPage(view,{v2Inputs:ctx.inputs,identities:ctx.identities}):null;}catch(_){R=null;}if(token!==st.token)return;
    let off,mine,shown=null,basis=null;
    if(R&&R.computed&&R.official){const pub=R.source==='PUBLICATION'&&typeof QS.pagePublication==='function'?QS.pagePublication().publication:null,base={identities:R.identities,v2Inputs:ctx.inputs,quotes:{},official:R.official,referenceRows:typeof QS.pageReferences==='function'?QS.pageReferences():{},...(pub?{publication:pub}:{vMissing:R.v_reason})};
     off=R.computed;mine=QS.compute({...base,gate:st.gate,weights:st.tree,typeWeights:st.typeWeights});shown=new Set(ctx.identities.map(c=>c.company_id));basis=typeof QS.publicationBasis==='function'?QS.publicationBasis():null;}
    else{const base={identities:ctx.identities,v2Inputs:ctx.inputs,quotes:{},vMissing:(typeof QS.pagePublication==='function'&&QS.pagePublication().reason)||'OFFICIAL_NOT_PUBLISHED'};
     off=QS.compute(base);mine=QS.compute({...base,gate:st.gate,weights:st.tree,typeWeights:st.typeWeights});}
    const only=x=>shown?{...x,rows:Object.fromEntries(Object.entries(x.rows||{}).filter(([k])=>shown.has(k)))}:x;
    st.result={off:only(off),mine:only(mine),rows:compareRows(only(off),only(mine)),basis,inputs:ctx.inputs||null};renderResult();})
    .catch(()=>{if(token===st.token)results.replaceChildren(el('p',T('비교 자료를 불러오지 못했습니다 · NOT_AVAILABLE','Compare inputs could not be loaded · NOT_AVAILABLE'),{class:'small','data-qgv2w-result-state':'NOT_AVAILABLE'}));});}
  function renderResult(){results.replaceChildren();const r=st.result;if(!r)return;if(typeof QS.readMarks==='function')for(const[k,v]of Object.entries(QS.readMarks(r.basis||null,view)))results.setAttribute(k,v);const P=r.mine.personal,rows=r.rows;
   // V axis weight 0: a personal Q·G-only result, labelled '개인 설정 결과 (V 비중 0)' (QgvScores personal.label); never the official ranking.
   const plabel=P&&Array.isArray(P.label)?P.label:(QS.PERSONAL_LABEL||['개인 설정 미리보기 · 공식 점수 아님','Personal setting preview · not an official score']);
   results.append(el('p',plabel[en?1:0]+' · '+(P&&P.profile?P.profile.id:'—'),{class:'badge partial','data-qgv2w-result-label':P&&P.v_weight_zero?'V_WEIGHT_ZERO':''}));
   if(!P||P.state!=='READY'||!rows.length){results.append(el('p',T('내 설정 결과 없음 · ','No personal result · ')+(P?P.state+(P.reason?' · '+P.reason:''):'NOT_AVAILABLE'),{class:'small','data-qgv2w-result-state':P?P.state:'NOT_AVAILABLE'}));return;}
   results.append(el('p',T('공식 = 중앙 게시(균형 34/33/33 · 관문 켬) · 내 설정 = 그 게시본의 요인 점수를 위 비중으로 다시 계산','Official = central publication (balanced 34/33/33 · gate on) · Mine = recomputed from its factor scores with the weights above'),{class:'small','data-qgv2w-result-state':'READY'}));
   // DC-31: the central V basis (basis day, publication time, STALE, calc version) and the IEX attribution with its terms link.
   if(typeof QS.centralHtml==='function'&&typeof QS.pagePublication==='function'){const PP=QS.pagePublication(),cb=el('div',undefined,{'data-qgv2w-central':''});cb.innerHTML=QS.centralHtml(QS.centralBasis(PP.publication,{reason:PP.reason,v2Inputs:r.inputs||null}),en);results.append(cb);}
   const cand=st.product!=='custom'?candidateFor(st.product,api):null;if(cand)results.append(el('p',cand.name+' v'+cand.version+' · '+CANDIDATE_LABEL[en?1:0]+(modified()?T(' · 수정됨',' · modified'):''),{class:'small','data-qgv2w-result-preset':cand.id}));
   results.append(stagesSummaryBox(r.mine));
   if(!st.company||!rows.some(x=>x.company_id===st.company))st.company=rows[0].company_id;
   const pick=el('select',undefined,{'data-qgv2w-company':'','aria-label':T('비교할 기업','Company to compare')});for(const x of [...rows].sort((a,b)=>String(a.ticker).localeCompare(String(b.ticker)))){const o=el('option',x.ticker,{value:x.company_id});if(x.company_id===st.company)o.selected=true;pick.append(o);}
   pick.onchange=()=>{st.company=pick.value;renderResult();};results.append(el('label',T('선택 기업 ','Company '),{class:'small'}),pick);
   const x=rows.find(y=>y.company_id===st.company),gateText=g=>g==='TRAP'?T('가치 함정 주의(V 제외)','Value-trap caution (V dropped)'):g==='NOT_EVALUATED'?T('판정 불가','Not evaluated'):T('주의 없음','No caution');
   const cov=(s,a)=>s&&s.coverage?pct(100*s.coverage[a].custom)+T(' (원래 가중치 기준 ',' (original weights ')+pct(100*s.coverage[a].official)+')':'—';
   const lines=[['Q',s=>num(s.q)],['G',s=>num(s.g)],['V',s=>num(s.v)],['QGV',s=>num(s.total)],[T('순위','Rank'),s=>s.rank!==null?String(s.rank):s.qg?qgText(s.qg):'—'],[T('산출 요인','Factors'),s=>s.factors_available+'/'+s.factors_total],
    ...['Q','G','V'].map(a=>[a+T(' 축 충족률',' coverage'),s=>cov(s,a)]),[T('순위·후보 자격','Rank / candidate'),s=>s.eligible?T('사용','used'):s.qg?T('QG 참고 목록 (V 미포함) · 공식 순위 아님','Q·G reference list (V not included) · not an official rank'):T('제외','excluded')],[T('가치 함정 관문','Value-trap gate'),s=>gateText(s.gate)]];
   const t1=el('table',undefined,{'data-qgv2w-company-table':st.company}),h1=el('tr'),b1=el('tbody');for(const h of [T('항목','Item'),T('공식','Official'),T('내 설정','Mine')])h1.append(el('th',h,{scope:'col'}));
   for(const[label,f]of lines){const tr=el('tr');tr.append(el('th',label,{scope:'row'}),el('td',x.official?f(x.official):'—'),el('td',x.mine?f(x.mine):'—'));b1.append(tr);}
   const th1=el('thead');th1.append(h1);t1.append(th1,b1);const w1=el('div',undefined,{class:'table-scroll'});w1.append(t1);results.append(w1);
   results.append(companyStagesBox(r.mine.rows[st.company]));
   const t2=el('table',undefined,{'data-qgv2w-compare-table':''}),h2=el('tr'),b2=el('tbody');for(const h of [T('기업','Company'),T('공식 QGV (순위)','Official QGV (rank)'),T('내 설정 QGV (순위)','Mine QGV (rank)'),T('순위 변화','Rank change'),T('관문 공식→내 설정','Gate official→mine')])h2.append(el('th',h,{scope:'col'}));
   for(const y of rows){const tr=el('tr',undefined,{'data-qgv2w-compare-row':y.company_id});if(typeof QS.marks==='function'){const pr=r.mine.rows[y.company_id],pp=pr&&pr.personal?pr.personal:null;for(const[k,v]of Object.entries({...QS.marks(r.off.rows[y.company_id]||null,r.basis||null,view),'data-cx-personal-total':pp&&finiteNum(pp.total)?String(pp.total):'NA','data-cx-personal-v':pp&&finiteNum(pp.v)?String(pp.v):'NA','data-cx-personal-rank':pr&&Number.isInteger(pr.personal_rank)?String(pr.personal_rank):''}))tr.setAttribute(k,v);}const qr=s=>s?num(s.total)+(s.rank!==null?' ('+s.rank+')':s.qg?' ('+qgText(s.qg)+')':' (—)'):'—',chg=y.rank_change===null?'—':y.rank_change>0?'▲'+y.rank_change:y.rank_change<0?'▼'+(-y.rank_change):'0';
    tr.append(el('td',y.ticker),el('td',qr(y.official)),el('td',qr(y.mine)),el('td',chg),el('td',(y.official?gateText(y.official.gate):'—')+' → '+(y.mine?gateText(y.mine.gate):'—')));b2.append(tr);}
   const th2=el('thead');th2.append(h2);t2.append(th2,b2);const w2=el('div',undefined,{class:'table-scroll'});w2.append(t2);
   results.append(el('h4',P.v_weight_zero?T('상위 목록 · 개인 설정 결과 (V 비중 0) 순 · 공식 순위 아님','Top list · personal setting result (V weight 0) · not the official ranking'):T('상위 목록 · 내 설정 순','Top list · by my setting'),{'data-qgv2w-top-title':P.v_weight_zero?'V_WEIGHT_ZERO':'PERSONAL'}),w2,el('p',T('순위 —: QGV 종합 점수가 없어 순위·후보에 넣지 않습니다(0점 아님). QG 참고: Q·G만으로 낸 종합점수라 공식 QGV 순위와 섞지 않습니다(V 해당 없음·미산출). 공식 순위 번호는 바뀌지 않습니다.','Rank —: no QGV total, so no rank or candidate place (never 0). QG ref: a total from Q·G only, kept apart from the official QGV ranking (V not applicable or not computed). The official rank numbers do not change.'),{class:'small'}));}
  function qgText(q){return T('QG 참고','QG ref')+(q.order!==null?' '+q.order:'');}
  /* Three weight stages, all from the engine (QgvScores personal rows .weight_stages): (a) 기본 비중, (b) 유형 반영 비중,
     (c) 결측·관문 반영 후 실제 적용 비중, per axis and per factor, with the reason of every change. */
  function stageCell(v){return el('td',pct(v),{'data-value':finiteNum(v)?String(v):''});}
  function reasonWords(c,ws){const t=STAGE_REASON[c.reason]?STAGE_REASON[c.reason][en?1:0]:c.reason;let d='';
   if(c.reason==='TYPE_WEIGHTS'){const names=typeNames(ws.type_adjusted.selected_types);d=names.length?names.join('·'):'';}
   else if(c.reason==='MISSING'&&c.detail)d=QS.reasonText?QS.reasonText(c.detail,en):c.detail;else if(c.detail&&STAGE_REASON[c.detail]&&c.detail!==c.reason)d=STAGE_REASON[c.detail][en?1:0];
   return t+(d?' ('+d+')':'');}
  function typeNames(ids){let cfg=null;try{cfg=view.TypeConfigDefaults||null;}catch(_){cfg=null;}return(ids||[]).map(id=>{const t=cfg&&Array.isArray(cfg.types)?cfg.types.find(x=>x.id===id):null;return t&&!en?t.name:id;});}
  function stagesSummaryBox(mine){const box=el('div',undefined,{'data-qgv2w-stages-summary':''}),sm=stageSummary(mine);
   box.append(el('h4',T('비중 3단계 · 프로필 요약','Three weight stages · profile summary')));
   if(!sm.rows){box.append(el('p',T('비중 단계 없음 · v2 입력 없음','No weight stages · no v2 input'),{class:'small'}));return box;}
   const t=el('table',undefined,{'data-qgv2w-stages-summary-table':''}),h=el('tr'),b=el('tbody');for(const x of [T('축','Axis'),T('(a) 기본','(a) Base'),T('(b) 유형 반영 · 평균','(b) Type-adjusted · mean'),T('(c) 실제 적용 · 평균','(c) Applied · mean')])h.append(el('th',x,{scope:'col'}));
   for(const p of api.PILLARS){const tr=el('tr',undefined,{'data-qgv2w-stages-summary-row':p});tr.append(el('th',p,{scope:'row',title:AXIS_NAMES[p][en?1:0]}),stageCell(sm.base[p]),stageCell(sm.type.mean[p]),stageCell(sm.applied.mean?sm.applied.mean[p]:null));b.append(tr);}
   const th=el('thead');th.append(h);t.append(th,b);const w=el('div',undefined,{class:'table-scroll'});w.append(t);box.append(w);
   const c=sm.counts,ax=api.PILLARS.filter(p=>c.AXIS_NOT_AVAILABLE[p]).map(p=>p+' '+c.AXIS_NOT_AVAILABLE[p]).join(' · ');
   box.append(el('p',T('기업 '+sm.rows+'개 · (b) 유형 반영으로 축 비중이 바뀐 기업 '+sm.type.changed+'개 · (c) 평균은 총점이 있는 '+sm.applied.n+'개 기준','Companies '+sm.rows+' · (b) type adjustment changed the axis weights of '+sm.type.changed+' · (c) mean over '+sm.applied.n+' with a total'),{class:'small','data-qgv2w-stages-counts':'type'}),
    el('p',T('가치 함정 관문으로 V 제외 '+c.VALUE_TRAP_GATE+'개 · 결측 요인 재정규화 '+c.MISSING+'개 · 축 산출 불가 '+(ax||'0')+' · 총점 산출 불가 '+c.TOTAL_NOT_AVAILABLE+'개'+(c.STOPPED?' · 사용 중지 '+c.STOPPED+'개':''),'V dropped by the value-trap gate '+c.VALUE_TRAP_GATE+' · missing factors renormalized '+c.MISSING+' · axis not calculated '+(ax||'0')+' · no total '+c.TOTAL_NOT_AVAILABLE+(c.STOPPED?' · stopped '+c.STOPPED:'')),{class:'small','data-qgv2w-stages-counts':'applied'}));
   return box;}
  function companyStagesBox(row){const box=el('div',undefined,{'data-qgv2w-stages-company':row?row.company_id:''}),d=row&&row.personal?row.personal:null,ws=d&&d.weight_stages?d.weight_stages:null;
   box.append(el('h4',T('비중 3단계 · 선택 기업 ','Three weight stages · company ')+(row?row.ticker:'—')));
   if(!ws){box.append(el('p',T('비중 단계 없음 · 이 기업의 v2 입력 없음','No weight stages · no v2 input for this company'),{class:'small','data-qgv2w-stages-state':'NOT_AVAILABLE'}));return box;}
   const a=ws.applied,stop=ws.display_stop||null,state=stop?'STOPPED':a.state;
   const types=ws.type_adjusted.applied?(ws.type_adjusted.selected_types.length?T('유형 반영: ','Types: ')+typeNames(ws.type_adjusted.selected_types).join('·'):T('유형 반영 켬 · 인식된 유형 없음(기본과 같음)','Type adjustment on · no type recognized (same as base)')):T('유형 반영 끔','Type adjustment off');
   box.append(el('p',types+' · '+(state==='READY'?T('(c) = 총점을 만든 실제 비중','(c) = the weights that produced the total'):stop?(STAGE_REASON[stop]?STAGE_REASON[stop][en?1:0]:stop):STAGE_REASON.TOTAL_NOT_AVAILABLE[en?1:0]),{class:'small','data-qgv2w-stages-state':state}));
   const t=el('table',undefined,{'data-qgv2w-stages-table':row.company_id}),h=el('tr'),b=el('tbody');for(const x of [T('항목','Item'),T('(a) 기본','(a) Base'),T('(b) 유형 반영','(b) Type-adjusted'),T('(c) 실제 적용','(c) Applied')])h.append(el('th',x,{scope:'col'}));
   const reasonOf=(level,key)=>{const out=[];if(level==='axis')for(const c of ws.type_adjusted.changes)if(c.key===key)out.push(reasonWords(c,ws));for(const c of a.changes)if(c.level===level&&c.key===key)out.push(reasonWords(c,ws));
    if(level==='factor'&&a.factor_status[key]&&a.factor_status[key].status==='ZERO_WEIGHT')out.push(STAGE_REASON.ZERO_WEIGHT[en?1:0]);if(level==='axis'&&a.axis_status[key]&&a.axis_status[key].status==='ZERO_WEIGHT')out.push(STAGE_REASON.ZERO_WEIGHT[en?1:0]);return out.join(' · ');};
   const why=(path,text)=>{if(!text)return;const tr=el('tr',undefined,{'data-qgv2w-stage-reason-for':path,class:'qgv2w-stage-why'});tr.append(el('td',text,{colspan:'4',class:'small','data-stage-reason':''}));b.append(tr);};
   const applied=v=>stop?null:v;
   for(const p of api.PILLARS){const tr=el('tr',undefined,{'data-qgv2w-stage-row':'axis.'+p,class:'qgv2w-stage-axis'});tr.append(el('th',AXIS_NAMES[p][en?1:0],{scope:'row'}),stageCell(ws.base.axis[p]),stageCell(ws.type_adjusted.axis[p]),stageCell(applied(a.axis[p])));b.append(tr);why('axis.'+p,stop?(STAGE_REASON[stop]?STAGE_REASON[stop][en?1:0]:stop):reasonOf('axis',p));
    for(const f of Object.keys(api.WEIGHTS[p])){const fr=el('tr',undefined,{'data-qgv2w-stage-row':'factor.'+f});fr.append(el('th',FACTOR_LABELS[f][en?1:0],{scope:'row',class:'small'}),stageCell(ws.base.factor[f]),stageCell(ws.type_adjusted.factor[f]),stageCell(applied(a.factor[f])));b.append(fr);if(!stop)why('factor.'+f,reasonOf('factor',f));}}
   for(const tr of b.querySelectorAll('tr[data-qgv2w-stage-row]')){const cells=tr.querySelectorAll('td[data-value]');cells[0].dataset.stage='base';cells[1].dataset.stage='type';cells[2].dataset.stage='applied';}
   const th=el('thead');th.append(h);t.append(th,b);const w=el('div',undefined,{class:'table-scroll'});w.append(t);
   const basis=api.PILLARS.filter(p=>a.inner_basis[p]==='PUBLISHED');
   box.append(w,el('p',T('축 행 = 총점 대비 축 비중, 요인 행 = 총점 대비 요인 비중(축 비중 × 축 내 비중). 바뀐 항목 아래 줄에 이유를 적습니다(이유가 없으면 변경 없음). 결측 요인은 0점으로 채우지 않고 남은 요인 비중으로 다시 나눕니다.','Axis rows = share of the total; factor rows = share of the total (axis × within-axis). The reason of a change is on the line below it (no line = no change). Missing factors are never filled with 0; the remaining weights are renormalized.')+(basis.length?T(' '+basis.join('·')+' 축은 공개 점수를 쓰며, 세부 비중은 공식 비중을 있는 요인으로 다시 나눈 값입니다.',' The '+basis.join('/')+' axis uses the published score; its inner shares are the official weights renormalized over the available factors.'):''),{class:'small'}));
   return box;}
  function modified(){const c=candidateFor(st.product,api);return !c||JSON.stringify(c.weights)!==JSON.stringify(st.tree)||st.typeWeights!==c.type_weights||st.gate!==c.gate;}
  refresh();if(st.result)renderResult();}
 const axisShareText=(sh,p)=>sh.axis[p]===null?'—':(st.tree.axis[p]===0?T('0 = 제외 · ','0 = left out · '):'')+T('전체 ','total ')+pct(sh.axis[p]);
 const innerShareText=(sh,p,k)=>st.tree.inner[p][k]===0?T('0 = 제외(결측 아님)','0 = left out (not missing)'):T('축 내 ','in axis ')+pct(sh.inner[p][k])+T(' · 전체 ',' · total ')+pct(sh.total[p][k]);
 render();}
function mount(host,{locale,mode='strategy',qgFactors=()=>null,engine=globalThis.EnginePreview,v2Context}={}){
 if(!host)return;const doc=host.ownerDocument,view=doc.defaultView,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};const section=el('section',undefined,{class:'card','data-profile-editor':mode});section.append(el('h2',mode==='types'?(en?'Custom company types':'기업 유형 커스텀'):(en?'Strategy profiles':'전략 프로필')),el('p','PREVIEW · '+(en?'Device configuration · Official values are preserved':'기기 설정 · 공식값 유지'),{class:'badge'}));
 const status=el('p','NOT_AVAILABLE · '+(mode==='types'?'TYPE_CONFIG_PENDING_MERGE':'PREVIEW_NOT_RUN'),{role:'status','data-profile-status':''});section.append(status);
 if(mode==='types'){mountTypes(section,status,el,view,en);host.replaceChildren(section);return;}
 let state=empty(),writable=true,draft=null,selectedId=null,previewed=false;try{state=read(view.localStorage);}catch(_){writable=false;status.textContent='PROFILE_STORAGE_UNREADABLE';}
 const name=el('input',undefined,{id:'profile-name',maxlength:'60',placeholder:en?'Profile name':'프로필 이름'}),label=el('label',en?'Name':'이름',{for:'profile-name'}),editor=el('div',undefined,{'data-profile-fields':''}),saved=el('ul',undefined,{class:'list','data-saved-profiles':''});const results=el('div',undefined,{'data-profile-preview':'','aria-live':'polite'});
 const copy=el('button',en?'Copy official':'공식값 복사',{type:'button',id:'profile-copy'}),preview=el('button',en?'Preview':'미리보기',{type:'button',id:'profile-preview',disabled:''}),save=el('button',en?'Save on device':'기기 저장',{type:'button',id:'profile-save',disabled:''});
 function renderDraft(){editor.replaceChildren();for(const axis of ['Q','G','V']){const field=el('fieldset'),legend=el('legend',axis+(axis==='V'?' · PROVISIONAL_INITIAL_PRIOR':''));field.append(legend);for(const factor of Object.keys(draft[axis])){const id='weight-'+axis+'-'+factor,label=el('label',factor,{for:id}),input=el('input',undefined,{id,type:'number',min:'0',max:'100',step:'any','data-axis':axis,'data-factor':factor});input.value=String(draft[axis][factor]);input.oninput=()=>{draft[axis][factor]=input.value.trim()===''?NaN:Number(input.value);previewed=false;results.replaceChildren();save.disabled=true;status.textContent='PREVIEW · '+(en?'Draft changed':'초안 수정됨');};field.append(label,input);}const sum=el('p',axis+' · '+(en?'Sum 100 required':'합 100 필요'),{class:'small'});field.append(sum);editor.append(field);}preview.disabled=false;save.disabled=true;}
 function renderSaved(){saved.replaceChildren();for(const p of state.strategies){const row=el('li',undefined,{class:'card'}),open=el('button',p.name,{type:'button','data-open-profile':p.id}),remove=el('button',en?'Delete':'삭제',{type:'button','data-remove-profile':p.id});open.onclick=()=>{selectedId=p.id;name.value=p.name;draft=structuredClone(p.weights);previewed=false;renderDraft();status.textContent='PREVIEW · '+(en?'Saved configuration copied into draft':'저장 설정을 초안으로 복사했습니다.');};remove.onclick=()=>{if(!writable)return;try{const next=validate({...state,strategies:state.strategies.filter(x=>x.id!==p.id)});state=write(view.localStorage,next);if(selectedId===p.id){selectedId=null;previewed=false;save.disabled=true;}renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};remove.disabled=!writable;row.append(open,remove);saved.append(row);}if(!state.strategies.length)saved.append(el('li',en?'No saved profiles.':'저장한 프로필이 없습니다.',{class:'empty'}));}
 function renderPreview(result){results.replaceChildren();if(result.state!=='PREVIEW')return;const note=el('p',en?'PREVIEW · RAM only · Not mixed with official or actual results · Q/G only, V needs prices (NOT_AVAILABLE)':'PREVIEW · 메모리 전용 · 공식·실제와 섞지 않음 · Q/G만, V는 가격 필요(NOT_AVAILABLE)',{class:'small'}),wrap=el('div',undefined,{class:'table-wrap'}),table=el('table'),head=el('tr');for(const h of [en?'Company':'기업',en?'Official Q · G':'공식 Q · G',en?'My Q · G':'내 Q · G',en?'Q/G total':'Q/G 합계',en?'Rank change':'순위 변화'])head.append(el('th',h));const thead=el('thead'),body=el('tbody');thead.append(head);
  const show=v=>v===null?'—':(Math.round(v*10)/10).toFixed(1);for(const r of result.rows){const tr=el('tr',undefined,{'data-preview-row':r.company_id});const change=r.rank_change===null?'—':r.rank_change>0?'▲'+r.rank_change:r.rank_change<0?'▼'+(-r.rank_change):'0';for(const v of [r.company_id.toUpperCase(),show(r.official_q)+' · '+show(r.official_g),show(r.mine_q)+' · '+show(r.mine_g),show(r.official)+' → '+show(r.mine),change])tr.append(el('td',v));body.append(tr);}table.append(thead,body);wrap.append(table);results.append(note,wrap);}
 copy.onclick=()=>{draft=copyOfficial();selectedId=null;previewed=false;name.value=en?'My profile':'내 프로필';renderDraft();status.textContent='PREVIEW · '+(en?'Official leaf weights copied':'공식 개별 가중치를 복사했습니다.');};
 name.oninput=()=>{previewed=false;save.disabled=true;};
 preview.onclick=()=>{try{weights(draft);need(name.value.trim().length>0);previewed=true;save.disabled=!writable;const result=previewRanks(qgFactors(),draft,engine);status.textContent='PREVIEW · Q/G/V '+(en?'each sum 100':'각 합 100')+' · '+(result.state==='PREVIEW'?(en?'Q/G preview recalculated':'Q/G 미리보기 재계산'):(en?'Calculated results':'계산 결과')+' NOT_AVAILABLE · '+result.reason);renderPreview(result);}catch(_){previewed=false;save.disabled=true;status.textContent='PROFILE_INVALID · '+(en?'Each axis must total 100; enter a name.':'각 축 비중 합이 100이어야 하며 이름이 필요합니다.');}};
 save.onclick=()=>{if(!previewed||!writable)return;try{const id=selectedId||'device-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10),p={id,name:name.value.trim(),weights:weights(draft)},next={...state,strategies:[...state.strategies.filter(x=>x.id!==id),p]};state=write(view.localStorage,next);selectedId=id;status.textContent='PREVIEW · '+(en?'Saved on this device':'이 기기에 저장했습니다.');renderSaved();}catch(_){status.textContent='PROFILE_SAVE_FAILED';}};
 const v2box=el('div',undefined,{class:'card','data-qgv2-weights-editor':''});try{mountV2(v2box,el,view,en,{...(v2Context?{v2Context}:{})});}catch(_){v2box.append(el('p','NOT_AVAILABLE',{class:'small'}));}
 section.append(activeV2View(el,en,view),v2box,officialView(el,en,view),el('h3',en?'v1 preview · legacy leaf-weight drafts (not the official v2 score)':'v1 미리보기 · 기존 개별 가중치 초안 (공식 v2 점수 아님)',{'data-profile-v1-heading':''}),label,name,copy,editor,preview,results,save,el('h3',en?'Saved profiles · v1 preview':'저장한 프로필 · v1 미리보기'),saved);renderSaved();host.replaceChildren(section);
}
return Object.freeze({KEY,SCHEMA,V2_KEY,V2_SCHEMA,PRODUCT_PRESETS,CANDIDATE_LABEL,STAGE_REASON,candidateFor,stageSummary,FACTOR_LABELS,DECISION_URL,emptyV2,validateV2,readV2,writeV2,saveV2,weightShares,fitTo100,treeProblem,compareRows,TARGET_IDS,empty,copyOfficial,copyOfficialTypes,typeConfig,weights,validate,read,write,previewRanks,typePreview,targetTypePreview,configDiff,mount});
});
