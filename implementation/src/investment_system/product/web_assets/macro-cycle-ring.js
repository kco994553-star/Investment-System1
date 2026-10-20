/* Macro cycle rings (FRONTEND_INTERACTION_CONTRACT_20261019 §4; MACRO_PHASE_MODEL_DRAFT_20261019 §4–§8): three separate concept
   rings — 경기 (economy), 주식시장 (market), SIC 산업 (industry:<industry_group>) — in phase order, clockwise, turning without end
   (after the last phase comes the first). The ring itself is a concept diagram (화면 틀), never data. A position is shown only as
   an interval arc taken unchanged from a published model output; no model output is published today, so every ring reads
   "미산출" and no arc, point or probability is drawn. Phase panels quote the approved drafts only; where a draft leaves a value
   open the panel says "미정(소유자 결정)".
   The user's own estimates (사용자 추정 · 공식 판정 아님) are an append-only history per ring (the latest is a separate dashed purple
   arc), each with its reason and a snapshot of what the system layer showed then, kept in this browser's localStorage only,
   never sent and never mixed with the official layer. Focus (rotation) lives in module RAM per ring key, so the full re-render of
   the macro screen keeps it. No request of its own, no price, no score. Macro lights, their reference mode and the macro gate are
   untouched. Evidence for a phase can be attached by another module through attachEvidence() (the observation graph is separate). */
(function(root){
 'use strict';
 const T=(l,ko,en)=>l==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 const OPEN='미정(소유자 결정)';
 const USER_KEY='investment.web.v1.macro-cycle-user-estimate',USER_SCHEMA='macro-cycle-user-estimate/2',USER_SCHEMA_V1='macro-cycle-user-estimate/1',USER_CAP=50;
 const PARTS=['초입','후반'];
 const SLOP_PX=8,SNAP_SHARE=1/3,ANIM_MS=260;// UI constants (contract §4-5), not methodology values
 // ---------- draft text (MACRO_PHASE_MODEL_DRAFT_20261019). Interpretation candidates, not approved (MEV-1). ----------
 const SHARED_ABSTAIN=[['충돌·과대·v0만·규칙 미승인','경기 모델(§5-6)과 같은 형태','CONFLICTING_FAMILIES · INTERVAL_TOO_WIDE · NO_APPROVED_STATE_RULE']];
 const MODELS={
  economy:{label:['경기','Economy'],draft:'§5',phases:['회복','확장','둔화','수축'],
   cells:{'회복':[['PO 음→양 전환 [문헌]. LU 개선 시작. HO 증가 전환',['E25','E22','E14','E26']],['PO 양 유지. MO 증가 전환. BK 긴축 종료',['E21','E36']]],
    '확장':[['PO 양 유지. LD 개선. LU 안정',['E16','E17']],['IN 가속. BK 긴축 시작. C 평탄화(역전 전)',['E39','E36']]],
    '둔화':[['C 역전 [문헌, 확장→둔화 경고]. HO 감소 전환',['E09','E26']],['LD 악화. MO 감소 전환. LU 악화 시작',['E16','E17','E21','E14']]],
    '수축':[['LU Sahm 발동 [문헌, 확장→수축 전환]. PO 양→음',['E13','E25','E22']],['PO 음 유지. LE 감소 지속',['E25','E18']]]},
   transitions:[['회복','확장','PO 양 유지 + LD 또는 MO 개선','LU 악화 지속'],['확장','둔화','C 역전 또는 IN 가속 + LD·MO·HO 중 하나 악화','PO·LU 모두 개선 중'],
    ['둔화','수축','LU Sahm 발동 또는 PO 양→음, 그리고 다른 계열 악화','PO 양 유지 + LU 개선'],['수축','회복','PO 음→양 [문헌] + LU 또는 HO 개선','LU 악화 지속']],
   transitionNotes:['공통 형태: 다음 칸 방향 계열 ≥ N_t, 반대 방향 계열 ≤ M_t, 조건이 연속 K_t회 실행에서 유지. N_t·M_t·K_t '+OPEN,
    '역방향(예: 둔화 → 확장): 둔화 근거 계열이 해제되고 확장 근거 ≥ N_t('+OPEN+')',
    '국면을 건너뛰는 이동은 구간이 넓어지는 것으로 표현한다. 폭이 W_max('+OPEN+')를 넘으면 유보한다',
    '단일 계열로 국면을 옮기지 않는다. Sahm 발동도 혼자서는 "둔화 후반~수축 초입" 구간까지만 넓힌다(후보)'],
   against:[['후보 구간 반대 방향의 현재 유효 계열','반대 계열 수 > M_max('+OPEN+') → 구간을 반대쪽으로 넓힘. 넓힌 뒤 W_max 초과 → 유보'],
    ['같은 계열 안 엇갈림(예: E16 개선·E17 악화)','그 계열을 세지 않음. "엇갈림"으로 표시'],
    ['속보 기반 근거(E25 속보, E21 속보)','근거로 세되 "속보 · 수정 가능" 표식. 다음 발표에서 조건이 풀리면 해제 사건'],
    ['금리 인하 사건만 있음','국면을 옮기지 않음. 예방적 인하 가능성 [미확인]'],['역전 해소(E10)','회복 근거로 세지 않음'],
    ['헤드라인 물가만 있음','IN 계열을 "자료 없음"으로 둠. 헤드라인으로 대신하지 않음'],['발표 공백','해당 계열 "자료 지연". 신선도 조건에 따라 유보']],
   abstain:[['근거 부족','셀 수 있는 계열 < K_min('+OPEN+')','MISSING_SOURCE · SOURCE_NOT_COLLECTED'],['자료 낡음','계열 최신 발표가 정해진 주기 밖(기준 '+OPEN+')','STALE'],
    ['근거 충돌','받치는 계열 수 ≤ 반대 계열 수','CONFLICTING_FAMILIES(새 코드 후보)'],['구간 과대','구간 폭 > W_max('+OPEN+')','INTERVAL_TOO_WIDE(새 코드 후보)'],
    ['수정 직후','수정 발표로 근거 조건이 해제·성립 → 다음 정기 발표까지 유보(후보)','CONFLICTING_VINTAGE · HISTORICAL_VINTAGE_NOT_PROVEN'],
    ['규칙 미승인','공식 층: 쓰려는 해석이 승인되지 않음','NO_APPROVED_STATE_RULE'],['v0만 있음','공식 층: 받치는 계열이 모두 v0','NO_APPROVED_STATE_RULE + 탐색 층에만 표시'],
    ['시각 의문','근거 시각이 판정 시각보다 뒤','AVAILABLE_AFTER_AS_OF · SOURCE_AFTER_AS_OF']],
   note:'지금 공개 입력만으로 셀 수 있는 계열은 PO·LU·C·BK다. 경기 모델 출력은 게이트·경고등·U3·확대 차단의 입력이 아니다.'},
  market:{label:['주식시장','Equity market'],draft:'§6',phases:['바닥','상승 초기','상승 후기','하락'],
   cells:{'바닥':[['MV 위험 정점 뒤 하락 전환. CR 악화 멈춤',['MV','CR']],['CR 개선 전환. MT 아직 장기선 아래',['CR','E45']]],
    '상승 초기':[['MT 장기선 상향 교차. CR 개선 유지',['E45','CR']],['MT 유지. ME 이익 증가 비율 상승(후행)',['E45','E51']]],
    '상승 후기':[['MT 유지. ME 증가 비율 하락 전환. C 역전(시장용으로 따로 셈)',['E45','E51','E09']],['CR 악화 시작. BK 긴축',['CR','E36']]],
    '하락':[['MT 장기선 하향 교차. CR 급악화. MV 급등',['E45','CR','MV']],['MT 아래 유지. 경고등 시장·신용 동시 점등',['E45','MV','CR']]]},
   transitions:[['바닥','상승 초기','MT 상향 교차 + CR 개선','MV 재급등'],['상승 초기','상승 후기','ME 증가 비율 하락 또는 C 역전 + MT 유지','CR 개선 지속 + ME 상승'],
    ['상승 후기','하락','MT 하향 교차 + CR 악화','MT 즉시 복귀(기준 '+OPEN+')'],['하락','바닥','MV 하락 전환 + CR 악화 멈춤','MT 하향 지속 + CR 악화 지속']],
   transitionNotes:['필요 계열 수 N_t와 유지 횟수 K_t '+OPEN,'시장은 경기를 앞설 수 있다. "경기 수축 + 시장 상승 초기"는 모순으로 보지 않는다. 경기 구간을 시장 반대 근거로 세지 않는다'],
   against:[['MT 교차가 짧게 반복(휩쏘)','교차 계열을 "엇갈림"으로 둔다. 반복 횟수 기준 '+OPEN],
    ['HYG÷IEF는 듀레이션·자금 흐름 영향을 받는다','CR 단독으로 국면을 옮기지 않는다'],['ME(E51)는 공시 후행','전환의 막는 근거로만 쓰고 단독 전환 근거로 쓰지 않는다(후보)']],
   abstain:[['기기 자료 없음','기기에 가격이 로드되지 않음','DEVICE_NOT_LOADED'],['허용 목록 밖','필요한 기호가 Worker 허용 목록 밖','WORKER_ALLOWLIST_REQUIRED'],
    ['이력 부족','변동성 이력·장기선 창 미달','경고등 기존 결측 사유'],['공개 층','가격 근거를 공개에 쓸 수 없음','PUBLIC_PRICE_BOUNDARY(새 코드 후보)'],...SHARED_ABSTAIN],
   note:'시장 근거는 대부분 가격에서 나온다. 공개 층은 기본 "판정 유보 · 공개 근거 부족"이고, 기기 층 구간은 PM-6 결정 뒤에만 만든다. 가격은 이 화면에 없다.'},
  industry:{label:['SIC 산업','SIC industry'],draft:'§7',phases:['회복','확장','둔화','수축'],vocabOpen:true,
   cells:{'회복':[['매출 증가율 중앙값 음→양. 재고/매출 하락 뒤 안정. 이익 증가 비율 상승',['E51']]],'확장':[['매출·이익 증가 폭 넓음. 설비투자 증가',['E51']]],
    '둔화':[['증가율 양이지만 하락. 재고/매출 상승. 이익 증가 비율 하락',['E51']]],'수축':[['중앙값 음. 증가 폭 낮음. 재고 조정',['E51']]]},
   transitions:[],
   transitionNotes:['공시 집계 계열 + 그룹 공식 지표 계열 중 N_t 계열이 다음 칸 방향이고, 마감 후 상태로 K_t분기 유지. N_t·K_t '+OPEN,
    '증가 폭 교차(E51) 기준은 CAT의 [제안]이다. 결정이 아니다('+OPEN+')','초입·후반 구분 기준 '+OPEN],
   against:[['합계 비율과 중앙값 방향이 다름','"엇갈림"(대형사 한 곳 영향)'],['한 발행인이 쌍 집합 매출을 크게 차지','"집중", 합계 비율 근거 제외(기준 '+OPEN+')'],
    ['이상치 쌍, M&A·분할 기간','집계에서 제외(기준 '+OPEN+')']],
   abstain:[['표본 부족','쌍 수·커버리지가 기준 미달(기준 '+OPEN+')','SAMPLE_TOO_SMALL(새 코드 후보)'],['잠정 기간','공시 마감 전','FILING_WINDOW_OPEN(새 코드 후보)'],
    ['그룹 너무 넓음','하위 그룹 없는 manufacturing_industrial_tech','GROUP_TOO_BROAD(새 코드 후보)'],['구성원 없음','SIC 없음·0000','MISSING_0000_OR_UNMATCHED_IS_NOT_AVAILABLE'],
    ['과거 재생','당시 모집단 없음','NEEDS_HISTORICAL_UNIVERSE'],...SHARED_ABSTAIN],
   note:'산업 어휘는 '+OPEN+'(PM-7). 이 링은 초안 권장안 (a) 경기 어휘를 후보로 쓴다. 이름은 늘 "분석 대상 내 표본 집계"이며 산업 전체가 아니다. 3.2 순환매 위치로 바꾸지 않는다.'}};
 const CYCLES=['economy','market','industry'];
 // ---------- state (module RAM; contract §4-7 "보관 위치") ----------
 const RING={};// key -> {turns, shown, userRotated, last:{state,text,asOf}, changed:null|string}
 let publication=new Map(),failed=false,activeCycle='economy',industryGroup=null,groupMissing=false,evidenceHook=null;
 const mounts=new Set();
 const ringState=key=>RING[key]||(RING[key]={turns:0,shown:0,userRotated:false,init:false,last:null,changed:null});
 const mod=(a,n)=>((a%n)+n)%n;
 const reduced=()=>{try{return !!(root.matchMedia&&root.matchMedia('(prefers-reduced-motion: reduce)').matches);}catch(_){return false;}};
 // ---------- publication (format: draft §4-2 objects; file and schema PM-2 — tests use synthetic objects only) ----------
 function cellIndex(model,ref){if(!ref||typeof ref!=='object')return null;const p=model.phases.indexOf(ref.phase);if(p<0)return null;if(ref.part==null)return{p,part:null};const q=PARTS.indexOf(ref.part);return q<0?null:{p,part:ref.part};}
 function readOutput(cycle,o){
  const model=MODELS[cycle.split(':')[0]],bad=why=>({state:'NOT_COMPUTED',reason:why});
  if(!o)return bad('NO_MODEL_OUTPUT');
  if(o.point!==null&&o.point!==undefined)return bad('INVALID_OUTPUT_POINT');// a point coordinate is never shown (§4-3 4)
  const base={modelId:typeof o.model_id==='string'?o.model_id:'NA',layer:o.layer==='OFFICIAL'?'OFFICIAL':'EXPLORATORY_V0',asOf:typeof o.as_of==='string'?o.as_of:null,
   supporting:Array.isArray(o.supporting)?o.supporting:[],opposing:Array.isArray(o.opposing)?o.opposing:[],mixed:Array.isArray(o.mixed)?o.mixed:[],missing:Array.isArray(o.missing)?o.missing:[],
   transition:o.transition_frequency&&typeof o.transition_frequency==='object'?o.transition_frequency:null,oldest:typeof o.oldest_input_release_at==='string'?o.oldest_input_release_at:null};
  if(o.status==='ABSTAIN'){const r=Array.isArray(o.abstain_reasons)?o.abstain_reasons.filter(x=>typeof x==='string'&&x):[];return r.length&&!o.interval?{...base,state:'ABSTAINED',reasons:r}:bad('INVALID_OUTPUT');}
  if(o.status==='ESTIMATED_INTERVAL'){const iv=o.interval||{},a=cellIndex(model,iv.from),b=cellIndex(model,iv.to);
   if(!a||!b||!base.asOf)return bad('INVALID_OUTPUT');return{...base,state:'ESTIMATED',from:a,to:b};}
  return bad('INVALID_OUTPUT');
 }
 const outputFor=key=>readOutput(key,publication.get(key));
 function setPublication(p){
  const list=Array.isArray(p)?p:p&&Array.isArray(p.outputs)?p.outputs:[];const next=new Map();
  for(const o of list)if(o&&typeof o.cycle==='string')next.set(o.cycle,o);
  publication=next;failed=false;
  for(const key of Object.keys(RING))follow(key);
  for(const m of mounts)m.refresh();
 }
 function refreshFailed(){failed=true;for(const m of mounts)m.refresh();}
 function attachEvidence(fn){evidenceHook=typeof fn==='function'?fn:null;for(const m of mounts)m.refresh();}
 // ---------- geometry (degrees clockwise from 12 o'clock; cell i spans [i·s − s/2, i·s + s/2]) ----------
 const C=160,R={pin:[0,10],iv:[140,151],cell:[96,134],user:[81,90]};
 function edge(model,ref,end){const s=360/model.phases.length,start=ref.p*s-s/2;if(ref.part===null)return end?start+s:start;const q=PARTS.indexOf(ref.part);return start+(end?(q+1):q)*s/2;}
 function span(model,a,b){const from=edge(model,a,false);let to=edge(model,b,true);while(to<=from)to+=360;return[from,Math.min(to,from+360)];}
 const pt=(r,deg)=>{const t=(deg-90)*Math.PI/180;return[(C+r*Math.cos(t)).toFixed(2),(C+r*Math.sin(t)).toFixed(2)];};
 function band(r0,r1,a0,a1){if(a1-a0>=359.99)return band(r0,r1,a0,a0+180)+' '+band(r0,r1,a0+180,a0+360);
  const L=a1-a0>180?1:0,[x0,y0]=pt(r1,a0),[x1,y1]=pt(r1,a1),[x2,y2]=pt(r0,a1),[x3,y3]=pt(r0,a0);
  return 'M'+x0+' '+y0+' A'+r1+' '+r1+' 0 '+L+' 1 '+x1+' '+y1+' L'+x2+' '+y2+' A'+r0+' '+r0+' 0 '+L+' 0 '+x3+' '+y3+' Z';}
 const label=(model,ref)=>ref.part?model.phases[ref.p]+' '+ref.part:model.phases[ref.p];
 const intervalText=(model,o)=>label(model,o.from)+'~'+label(model,o.to);
 function covers(model,o,i){if(!o||o.state!=='ESTIMATED')return false;const s=360/model.phases.length,[a,b]=span(model,o.from,o.to);
  for(const k of [-1,0,1]){const lo=i*s-s/2+k*360,hi=lo+s;if(Math.min(b,hi)-Math.max(a,lo)>1e-6)return true;}return false;}
 // ---------- focus follows the interval until the user turns the ring (§4-7) ----------
 function nearest(turns,n,target){let d=mod(target-mod(turns,n),n);if(d>n/2)d-=n;return d;}
 function follow(key){const st=ringState(key),cycle=key.split(':')[0],model=MODELS[cycle],o=outputFor(key),n=model.phases.length;
  const text=o.state==='ESTIMATED'?intervalText(model,o):o.state==='ABSTAINED'?'판정 유보':'미산출',asOf=o.asOf||null;
  if(st.last&&(st.last.text!==text||st.last.asOf!==asOf))st.changed='추정 구간 바뀜: '+st.last.text+' → '+text+' · 기준 '+(st.last.asOf||'NA')+' → '+(asOf||'NA');
  st.last={text,asOf,state:o.state};
  if(!st.userRotated&&o.state==='ESTIMATED'){st.turns+=nearest(st.turns,n,o.from.p);}
  st.init=true;}
 // ---------- device-only user estimate (사용자 추정 · 공식 판정 아님) ----------
 // Schema /2 (2026-10-20, functional hierarchy 4.4.2): an append-only history per ring key, oldest first, at most USER_CAP entries
 // (the oldest is dropped beyond that). Each entry keeps when, which interval, the user's own reason, and what the system layer
 // showed at that moment (status code/text, model id and as_of when a publication existed) — never a made-up system position.
 // A /1 value (one estimate per ring) is read as a one-entry history without loss; it is written as /2 on the next change.
 const refOk=r=>r&&typeof r==='object'&&typeof r.phase==='string'&&typeof r.part==='string';
 function cleanEntry(e,seq){if(!e||typeof e!=='object'||!refOk(e.from)||!refOk(e.to))return null;const sys=e.system&&typeof e.system==='object'?e.system:null;
  return{seq:Number.isInteger(e.seq)&&e.seq>0?e.seq:seq,saved_at:typeof e.saved_at==='string'?e.saved_at:'',from:{phase:e.from.phase,part:e.from.part},to:{phase:e.to.phase,part:e.to.part},note:typeof e.note==='string'?e.note.slice(0,200):'',
   system:sys&&typeof sys.state==='string'?{state:sys.state,text:typeof sys.text==='string'?sys.text:'',reason:typeof sys.reason==='string'?sys.reason:null,layer:typeof sys.layer==='string'?sys.layer:null,model_id:typeof sys.model_id==='string'?sys.model_id:null,as_of:typeof sys.as_of==='string'?sys.as_of:null}:{state:'NOT_RECORDED',text:'',reason:null,layer:null,model_id:null,as_of:null}};}
 function readUser(){const empty={schema:USER_SCHEMA,rings:{}};let v;try{v=JSON.parse(root.localStorage.getItem(USER_KEY)||'null');}catch(_){return empty;}
  if(!v||typeof v!=='object'||!v.rings||typeof v.rings!=='object')return empty;const out={schema:USER_SCHEMA,rings:{}};
  for(const [k,r] of Object.entries(v.rings)){const list=v.schema===USER_SCHEMA_V1?[r]:v.schema===USER_SCHEMA&&Array.isArray(r)?r:[];
   const clean=list.map((e,i)=>cleanEntry(e,i+1)).filter(Boolean);if(clean.length)out.rings[k]=clean.slice(-USER_CAP);}
  return out;}
 function writeUser(v){try{for(const k of Object.keys(v.rings))if(!v.rings[k].length)delete v.rings[k];if(Object.keys(v.rings).length)root.localStorage.setItem(USER_KEY,JSON.stringify(v));else root.localStorage.removeItem(USER_KEY);return true;}catch(_){return false;}}
 function historyFor(key,model){return (key&&readUser().rings[key]||[]).map(e=>{const a=cellIndex(model,e.from),b=cellIndex(model,e.to);return a&&b&&a.part&&b.part?{...e,a,b}:null;}).filter(Boolean);}
 function userFor(key,model){const h=historyFor(key,model),u=h[h.length-1];return u?{from:u.a,to:u.b,note:u.note,saved:u.saved_at}:null;}
 function systemSnapshot(key){const o=outputFor(key),base={state:o.state,reason:o.state==='NOT_COMPUTED'?o.reason||null:o.state==='ABSTAINED'?o.reasons.join(' · '):null,layer:o.state==='NOT_COMPUTED'?null:o.layer,model_id:o.state==='NOT_COMPUTED'?null:o.modelId,as_of:o.asOf||null};
  const model=MODELS[key.split(':')[0]];return{...base,text:o.state==='ESTIMATED'?intervalText(model,o):STATE_TEXT[o.state][0]};}
 // ---------- groups for the industry ring: industry_group values of the published sec-qgv2.json rows (§4-9) ----------
 function groupsOf(bundle){const p=bundle&&bundle['sec-qgv2.json'],out=new Set();
  if(p&&p.records&&typeof p.records==='object')for(const r of Object.values(p.records))if(r&&typeof r.industry_group==='string'&&r.industry_group)out.add(r.industry_group);
  return [...out].sort();}
 const groupName=(g,l)=>{const L=root.UniverseCompany&&root.UniverseCompany.GROUP_LABEL&&root.UniverseCompany.GROUP_LABEL[g];return L?(l==='en-US'?L[1]:L[0])+' ('+g+')':g;};
 const keyOf=cycle=>cycle==='industry'?(industryGroup?'industry:'+industryGroup:null):cycle;
 // ---------- rendering ----------
 const STATE_TEXT={ESTIMATED:['추정','Estimated'],ABSTAINED:['판정 유보','Abstained'],NOT_COMPUTED:['미산출','Not computed']};
 const REASON_TEXT={NO_MODEL_OUTPUT:['위치 판정 모델 없음 · 게시된 모델 출력 없음','No position model · no published model output'],
  INVALID_OUTPUT:['게시된 출력 형식을 확인할 수 없음','The published output could not be verified'],INVALID_OUTPUT_POINT:['게시된 출력에 점 좌표가 있어 쓰지 않음','The published output has a point coordinate and is not used'],
  NO_GROUP:['업종 그룹을 고르지 않음','No industry group chosen']};
 function evidenceLine(e,l){const f=x=>x==null||x===''?'NA':esc(x),basis=e.release_basis==='CAPTURE'||!e.release_at?T(l,'수집 시각 기준(상한)','capture time (upper bound)'):f(e.release_at);
  return '<li data-cycle-evidence-line><b>'+f(e.label||e.indicator||e.family)+'</b> <span class="badge">'+f(e.family)+'</span>'+(e.v0?' <span class="badge partial">v0 · 미검증</span>':'')+
   '<br><span class="small">'+T(l,'관측 기간 ','period ')+f(e.period)+' · '+T(l,'발표 ','released ')+basis+' · '+T(l,'수집 ','acquired ')+f(e.acquired_at)+' · '+T(l,'출처 ','source ')+f(e.source)+(e.rule_version?' · '+T(l,'규칙 ','rule ')+f(e.rule_version):'')+'</span></li>';}
 function transitionHtml(o,model,i,l){const t=o&&o.transition,ok=t&&t.validated===true&&Number.isInteger(t.k)&&Number.isInteger(t.n)&&t.n>0&&t.k>=0&&t.k<=t.n&&typeof t.period_from==='string'&&typeof t.period_to==='string'&&typeof t.rule_id==='string'&&typeof t.to==='string';
  if(!ok)return '<p data-cycle-transition="NOT_COMPUTED">'+esc(T(l,'전환 비율 미산출 · 근거 규칙 = 과거 국면 전환 빈도(결정됨) · Lab 검증 전에는 숫자를 쓰지 않음','Transition share not computed · basis = past phase-transition frequency (decided) · no number before Lab validation'))+'</p>';
  return '<p data-cycle-transition="VALIDATED">'+esc(T(l,'이 국면에서 '+t.to+'로 넘어간 과거 비율 '+t.k+'/'+t.n+' · 기간 '+t.period_from+'~'+t.period_to+' · 표본 '+t.n+'회 · 규칙 '+t.rule_id,'Past share moving from this phase to '+t.to+': '+t.k+'/'+t.n+' · period '+t.period_from+'–'+t.period_to+' · '+t.n+' samples · rule '+t.rule_id))+'</p>';}
 function detailHtml(cycle,key,model,i,o,l){
  const n=model.phases.length,ph=model.phases[i],cells=model.cells[ph]||[];
  const inside=o.state==='ESTIMATED'?(covers(model,o,i)?T(l,'추정 구간에 포함','inside the estimated interval'):T(l,'추정 구간 밖','outside the estimated interval')):T(l,'추정 구간 없음('+STATE_TEXT[o.state][0]+')','no estimated interval ('+STATE_TEXT[o.state][1]+')');
  const slot=c=>'<div data-cycle-evidence-slot="'+esc(key||cycle)+':'+esc(ph)+(c?':'+esc(c):'')+'"></div>';
  const cellHtml=cells.map(([text,codes],q)=>'<li data-cycle-cell-text="'+esc(cells.length>1?PARTS[q]:'')+'"><b>'+esc(ph+(cells.length>1?' '+PARTS[q]:''))+'</b> '+esc(text)+
   '<br><span class="small">'+T(l,'근거 자리(카탈로그 코드): ','Evidence slots (catalog codes): ')+codes.map(c=>'<span class="badge" data-cycle-code="'+esc(c)+'">'+esc(c)+'</span>').join(' ')+' · '+esc(T(l,'관측값 없음','no observation'))+'</span>'+slot(cells.length>1?PARTS[q]:'')+'</li>').join('');
  const tin=model.transitions.filter(t=>t[1]===ph),tout=model.transitions.filter(t=>t[0]===ph);
  const trow=t=>'<li><b>'+esc(t[0]+' → '+t[1])+'</b> '+esc(T(l,'필요: ','needs: ')+t[2])+' · '+esc(T(l,'막는 근거: ','blocked by: ')+t[3])+' · <span class="small">'+esc(T(l,'필요 계열 수 ','count ')+OPEN)+'</span></li>';
  return '<h3 data-cycle-detail-title>'+esc(ph)+' <span class="small">'+(i+1)+'/'+n+' · '+esc(inside)+'</span></h3>'+
   '<p class="small">'+esc(T(l,'국면 설명은 초안 '+model.draft+'의 해석 후보입니다(미승인). 관측값이 아닙니다.','Phase text quotes draft '+model.draft+' (interpretation candidates, not approved). Not observations.'))+'</p>'+
   '<h4>'+esc(T(l,'근거 패턴','Evidence pattern'))+'</h4><ul class="cycle-list" data-cycle-panel-evidence>'+cellHtml+'</ul>'+
   '<h4>'+esc(T(l,'전환 조건','Transition conditions'))+'</h4><ul class="cycle-list" data-cycle-panel-transitions>'+(tin.length||tout.length?tin.concat(tout).map(trow).join(''):'')+model.transitionNotes.map(x=>'<li class="small">'+esc(x)+'</li>').join('')+'</ul>'+
   '<div class="cycle-conds" data-cycle-conditions>'+[['상향 조건','Up'],['유지 조건','Hold'],['하향 조건','Down']].map(([k,e])=>'<div><b>'+esc(T(l,k,e))+'</b><span>'+esc(T(l,'기준 미정','Criteria undecided'))+'</span></div>').join('')+'</div>'+
   transitionHtml(o,model,i,l)+
   '<details data-cycle-panel-against><summary>'+esc(T(l,'반대 증거 (모델 공통)','Counter-evidence (model-wide)'))+'</summary><ul class="cycle-list">'+model.against.map(([a,b])=>'<li><b>'+esc(a)+'</b> — '+esc(b)+'</li>').join('')+'</ul></details>'+
   '<details data-cycle-panel-abstain><summary>'+esc(T(l,'판정 유보 조건 (모델 공통)','Abstain conditions (model-wide)'))+'</summary><ul class="cycle-list">'+model.abstain.map(([a,b,c])=>'<li><b>'+esc(a)+'</b> — '+esc(b)+' <span class="small">'+esc(c)+'</span></li>').join('')+'</ul></details>'+
   '<p class="small">'+esc(model.note)+'</p>';
 }
 function officialHtml(cycle,key,model,o,l){
  const st=o.state,mark=o.layer==='OFFICIAL'?T(l,'공식','official'):T(l,'탐색 층 · v0 · 미검증','exploratory · v0 · unvalidated');
  let head;
  if(st==='ESTIMATED')head='<p data-cycle-interval-text><b>'+esc(T(l,'추정 구간: ','Estimated interval: ')+intervalText(model,o))+'</b> · '+esc(o.modelId)+' · '+esc(T(l,'기준 ','as of ')+o.asOf)+' <span class="badge partial">'+esc(mark)+'</span></p>';
  else if(st==='ABSTAINED')head='<p data-cycle-interval-text><b>'+esc(T(l,'판정 유보','Abstained'))+'</b> · '+esc(o.modelId)+(o.asOf?' · '+esc(T(l,'기준 ','as of ')+o.asOf):'')+'</p>';
  else head='<p data-cycle-interval-text><span class="badge NOT_AVAILABLE">'+esc(T(l,'미산출','Not computed'))+'</span></p>';
  const reason=st==='ABSTAINED'?o.reasons.join(' · '):st==='ESTIMATED'?(o.layer==='OFFICIAL'?T(l,'게시된 공식 모델 출력','Published official model output'):T(l,'탐색 층 출력 · 공식 승인 전','Exploratory output · not approved as official')):T(l,...(REASON_TEXT[o.reason]||REASON_TEXT.INVALID_OUTPUT));
  const official=o.layer==='OFFICIAL'&&st!=='NOT_COMPUTED'?STATE_TEXT[st]:['미산출','Not computed'];
  const rows=(arr,kind)=>'<ul class="cycle-list" data-cycle-evidence="'+kind+'">'+(st==='NOT_COMPUTED'?'<li class="small">'+esc(T(l,'모델 출력 없음 · 근거 목록 없음','No model output · no evidence list'))+'</li>':arr.length?arr.map(e=>evidenceLine(e||{},l)).join(''):'<li class="small">'+esc(T(l,'없음','none'))+'</li>')+'</ul>';
  return head+'<p data-cycle-official>'+esc(T(l,'공식 판정: ','Official judgement: ')+T(l,...official))+'</p>'+
   '<p data-cycle-reason><span class="small">'+esc(T(l,'사유: ','Reason: '))+esc(reason)+'</span></p>'+
   '<p class="small" data-cycle-probability>'+esc(T(l,'확률 미산출 · 링 위 점 좌표 없음','Probability not computed · no point on the ring'))+'</p>'+
   (failed?'<p class="badge NOT_AVAILABLE" data-cycle-refresh-failed>'+esc(T(l,'갱신 실패 · 이전 게시본 그대로 표시','Refresh failed · showing the previous publication'))+'</p>':'')+
   (st!=='NOT_COMPUTED'?'<p class="small" data-cycle-counts>'+esc(T(l,'받치는 근거 '+o.supporting.length+'계열 · 반대 근거 '+o.opposing.length+'계열 · 엇갈림 '+o.mixed.length+' · 자료 없음 '+o.missing.length,'Supporting '+o.supporting.length+' families · opposing '+o.opposing.length+' · mixed '+o.mixed.length+' · missing '+o.missing.length))+(o.oldest?' · '+esc(T(l,'가장 오래된 근거 발표 ','oldest input released ')+o.oldest):'')+'</p>':'')+
   '\u0000<div class="cycle-evidence"><div><h4>'+esc(T(l,'찬성 근거','Supporting evidence'))+'</h4>'+rows(o.supporting,'for')+'</div><div><h4>'+esc(T(l,'반대 근거','Opposing evidence'))+'</h4>'+rows(o.opposing,'against')+'</div></div>';
 }
 const stamp=t=>t?(/T/.test(t)?t.slice(0,16).replace('T',' '):t)+' UTC':'NA';
 function systemText(sys,l){if(sys.state==='NOT_RECORDED')return T(l,'시스템: 기록 없음(이전 형식)','System: not recorded (older format)');
  const lay=sys.layer==='OFFICIAL'?'':sys.layer?T(l,' · 탐색 층 v0',' · exploratory v0'):'';return T(l,'시스템: ','System: ')+(sys.text||sys.state)+lay+(sys.model_id?' · '+sys.model_id:'')+(sys.as_of?T(l,' · 기준 ',' · as of ')+sys.as_of:'');}
 function historyHtml(model,key,l){
  const h=historyFor(key,model).reverse();if(!h.length)return '';
  const now=key?systemSnapshot(key):null,iv=e=>label(model,e.a)+'~'+label(model,e.b);
  const wide=(()=>{try{return !!(root.matchMedia&&root.matchMedia('(min-width: 900px)').matches);}catch(_){return false;}})(),show=wide?10:5;
  const row=(e,i)=>{const prev=h[i+1],same=prev&&iv(prev)===iv(e);
   return '<li data-cycle-user-entry="'+e.seq+'"><b>'+esc(iv(e))+'</b> <span class="small">'+esc(stamp(e.saved_at))+(i===0?T(l,' · 현재',' · current'):'')+'</span>'+
    '<br><span class="small" data-cycle-user-entry-system>'+esc(systemText(e.system,l))+'</span>'+
    (e.note?'<br><span class="small" data-cycle-user-entry-note>'+esc(T(l,'근거: ','Reason: ')+e.note)+'</span>':'')+
    '<br><span class="small" data-cycle-user-entry-compare>'+esc(prev?(same?T(l,'이전 사용자 추정과 같음','Same as the previous user estimate'):T(l,'이전 사용자 추정 '+iv(prev)+' → '+iv(e),'Previous user estimate '+iv(prev)+' → '+iv(e))):T(l,'첫 기록','First record'))+'</span>'+
    ' <button type="button" class="cycle-user-del" data-cycle-user-delete="'+e.seq+'" aria-label="'+esc(T(l,'이 기록 지우기 · ','Delete this record · ')+iv(e)+' · '+stamp(e.saved_at))+'">'+esc(T(l,'지우기','Delete'))+'</button></li>';};
  const first=h.slice(0,show).map(row).join(''),rest=h.slice(show).map((e,i)=>row(e,i+show)).join('');
  return '<h4>'+esc(T(l,'내 추정 기록 · 비교','My estimate history · comparison'))+'</h4>'+
   '<p class="small" data-cycle-user-now>'+esc(T(l,'지금 ','Now · ')+systemText(now,l))+'</p>'+
   '<ol class="cycle-list cycle-user-history" data-cycle-user-history>'+first+'</ol>'+
   (rest?'<details data-cycle-user-more><summary>'+esc(T(l,'더 보기 (','More (')+(h.length-show)+')')+'</summary><ol class="cycle-list cycle-user-history" start="'+(show+1)+'">'+rest+'</ol></details>':'')+
   '<p class="small" data-cycle-user-cap>'+esc(T(l,'기록 '+h.length+'개 · 링마다 최근 '+USER_CAP+'개까지 보관하고, 넘으면 가장 오래된 기록부터 지웁니다.',h.length+' records · up to '+USER_CAP+' per ring are kept; beyond that the oldest is dropped.'))+'</p>';
 }
 function userHtml(model,key,l){
  const opts=sel=>model.phases.flatMap(ph=>PARTS.map(pa=>{const v=ph+'|'+pa;return '<option value="'+esc(v)+'"'+(sel===v?' selected':'')+'>'+esc(ph+' '+pa)+'</option>';})).join('');
  const u=key?userFor(key,model):null,v=r=>r?model.phases[r.p]+'|'+r.part:'';
  return '<fieldset class="cycle-user" data-cycle-user'+(key?'':' disabled')+'><legend>'+esc(T(l,'사용자 추정 · 공식 판정 아님 · 이 기기에만 저장','User estimate · not an official judgement · this device only'))+'</legend>'+
   '<p class="small">'+esc(T(l,'이 기기(브라우저)에만 저장합니다. 어디에도 보내지 않고 공식 판정·점수에 쓰지 않습니다. 저장할 때마다 기록을 덧붙이고, 그때 시스템 표시(지금은 미산출)를 함께 남깁니다. 보라색 점선 호는 가장 최근 추정입니다. 초입·후반 세분은 초안 후보(PM-1)입니다.','Stored in this browser only. Never sent, never used for the official judgement or scores. Each save adds a record together with what the system showed then. The dashed purple arc is the latest estimate. The early/late split is a draft candidate (PM-1).'))+'</p>'+
   '<div class="cycle-user-row"><label>'+esc(T(l,'시작','From'))+' <select data-cycle-user-from>'+opts(v(u&&u.from))+'</select></label><label>'+esc(T(l,'끝','To'))+' <select data-cycle-user-to>'+opts(v(u&&u.to))+'</select></label></div>'+
   '<label class="cycle-user-note">'+esc(T(l,'근거(선택)','Reason (optional)'))+' <input type="text" maxlength="200" data-cycle-user-note value=""></label>'+
   '<div class="cycle-user-row"><button type="button" data-cycle-user-save>'+esc(T(l,'이 기기에 기록','Record on this device'))+'</button><button type="button" data-cycle-user-clear>'+esc(T(l,'모두 지우기','Clear all'))+'</button></div>'+
   '<p data-cycle-user-current>'+(u?esc(T(l,'최근 사용자 추정: ','Latest user estimate: ')+label(model,u.from)+'~'+label(model,u.to)+' · '+T(l,'이 기기에만 저장','this device only')+(u.saved?' · '+T(l,'기록 ','saved ')+stamp(u.saved):'')):esc(T(l,'저장된 사용자 추정 없음','No saved user estimate')))+'</p>'+
   (key?historyHtml(model,key,l):'')+'</fieldset>';
 }
 function ringPanel(cycle,l,groups){
  const model=MODELS[cycle],id='cycle-'+cycle;
  const group=cycle==='industry'?'<label class="cycle-group">'+esc(T(l,'업종 그룹','Industry group'))+' <select data-cycle-group><option value="">'+esc(T(l,'선택 안 함','None'))+'</option>'+groups.map(g=>'<option value="'+esc(g)+'"'+(g===industryGroup?' selected':'')+'>'+esc(groupName(g,l))+'</option>').join('')+'</select></label>'+
   (groups.length?'':'<p class="small" data-cycle-group-empty>'+esc(T(l,'공개 sec-qgv2.json에 업종 그룹 값이 없습니다.','No industry_group values in the public sec-qgv2.json.'))+'</p>')+
   (groupMissing?'<p class="small" data-cycle-group-missing>'+esc(T(l,'고른 업종 그룹이 새 게시본에 없음','The chosen industry group is not in the new publication'))+'</p>':'')+
   '<p class="small">'+esc(T(l,'산업 어휘 '+OPEN+'(PM-7) · 초안 후보 어휘 표시','Industry vocabulary undecided (PM-7) · draft candidate vocabulary shown'))+'</p>':'';
  return '<div class="cycle-ring" id="'+id+'" role="tabpanel" aria-labelledby="'+id+'-tab" data-cycle-ring="'+cycle+'"'+(cycle===activeCycle?'':' hidden')+'>'+group+
   '<div class="cycle-layout"><div class="cycle-state" data-cycle-state-box></div>'+
   '<figure class="cycle-figure"><figcaption class="small">'+esc(T(l,'개념도 · 국면 순서 · 칸 길이는 기간이 아님','Concept diagram · phase order · cell length is not time'))+'</figcaption>'+
   '<div class="cycle-drag" data-cycle-drag><svg class="cycle-svg" viewBox="0 0 320 320" role="img" data-cycle-kind="concept" focusable="false"><g data-cycle-cells></g><g data-cycle-arcs></g><g data-cycle-labels></g>'+
   '<path class="cycle-pin" d="M152 0 L168 0 L160 10 Z" data-cycle-pointer></path><text class="cycle-center" x="160" y="156" text-anchor="middle" data-cycle-center></text><text class="cycle-center-sub" x="160" y="176" text-anchor="middle">'+esc(T(l,'보는 국면 ▲','Viewed phase ▲'))+'</text></svg></div>'+
   '<div class="cycle-nav"><button type="button" data-cycle-prev aria-label="'+esc(T(l,'이전 국면','Previous phase'))+'">◀</button>'+
   '<div class="cycle-tabs" role="tablist" aria-label="'+esc(T(l,model.label[0]+' 국면','Phases of '+model.label[1]))+'" data-cycle-tabs>'+model.phases.map((ph,i)=>'<button type="button" role="tab" id="'+id+'-ph'+i+'" aria-controls="'+id+'-detail" data-cycle-phase="'+esc(ph)+'" data-cycle-index="'+i+'">'+esc(ph)+'</button>').join('')+'</div>'+
   '<button type="button" data-cycle-next aria-label="'+esc(T(l,'다음 국면','Next phase'))+'">▶</button></div>'+
   '<p class="small cycle-legend">'+esc(T(l,'바깥 굵은 띠 = 게시된 추정 구간(있을 때만) · 안쪽 보라색 점선 = 사용자 추정','Outer band = published estimated interval (only when one exists) · inner dashed purple = user estimate'))+'</p>'+
   '<p class="small cycle-loop-note">'+esc(T(l,'순환은 둘러보기 순서일 뿐입니다. 실제 경기·시장이 이 순서로만 움직인다는 뜻이 아닙니다. 국면은 건너뛰거나 되돌아갈 수 있습니다.','The loop is only a browsing order. Real cycles need not follow it; phases can be skipped or reversed.'))+'</p>'+
   '<p class="small" data-cycle-change-box></p></figure>'+
   '<div class="cycle-evidence-box" data-cycle-evidence-box></div><div class="cycle-detail" role="tabpanel" id="'+id+'-detail" data-cycle-focus tabindex="0"></div>'+
   '<div class="cycle-user-box" data-cycle-user-box></div></div></div>';
 }
 function mount(host,{bundle,locale}={}){
  if(!host)return null;const l=locale||'ko-KR';
  for(const m of [...mounts])if(!m.host.isConnected||m.host===host)mounts.delete(m);
  const groups=groupsOf(bundle);if(industryGroup&&!groups.includes(industryGroup)){industryGroup=null;groupMissing=true;}
  host.innerHTML='<section class="card cycle-root" id="macro-cycle-ring" data-cycle-root aria-labelledby="macro-cycle-ring-title">'+
   '<h2 id="macro-cycle-ring-title">'+esc(T(l,'순환 국면 링','Cycle phase rings'))+' <span class="badge" data-cycle-frame>'+esc(T(l,'화면 틀 · 예시 · 사용자 입력','Screen frame · example · user input'))+'</span></h2>'+
   '<p class="small">'+esc(T(l,'경기·주식시장·SIC 산업은 서로 다른 모델이고 따로 돕니다. 위치는 승인된 모델이 게시한 구간으로만 보입니다. 지금은 게시된 모델 출력이 없어 공식 판정은 미산출입니다. 위의 매크로 경고등(참고 표시)과 섞지 않습니다.','Economy, market and SIC industry are separate models and turn separately. A position appears only as an interval published by an approved model. No model output is published, so the official judgement is not computed. Kept apart from the macro lights above (reference only).'))+'</p>'+
   '<div class="cycle-switch" role="tablist" aria-label="'+esc(T(l,'사이클 선택','Choose cycle'))+'" data-cycle-switch>'+CYCLES.map(c=>'<button type="button" role="tab" id="cycle-'+c+'-tab" aria-controls="cycle-'+c+'" data-cycle-tab="'+c+'" aria-selected="'+(c===activeCycle)+'" tabindex="'+(c===activeCycle?0:-1)+'">'+esc(T(l,...MODELS[c].label))+'</button>').join('')+'</div>'+
   CYCLES.map(c=>ringPanel(c,l,groups)).join('')+
   '<p class="small cycle-live" aria-live="polite" role="status" data-cycle-live></p></section>';
  const card=host.querySelector('[data-cycle-root]'),live=card.querySelector('[data-cycle-live]');
  const say=t=>{live.textContent='';live.textContent=t;};
  const rings={};
  for(const cycle of CYCLES){
   const el=card.querySelector('[data-cycle-ring="'+cycle+'"]'),model=MODELS[cycle],n=model.phases.length,step=360/n;
   const svg=el.querySelector('svg'),cellsG=svg.querySelector('[data-cycle-cells]'),arcsG=svg.querySelector('[data-cycle-arcs]'),labelsG=svg.querySelector('[data-cycle-labels]');
   let anim=0;
   const st=()=>{const k=keyOf(cycle);return k?ringState(k):ringState('industry:');};
   function draw(){const s=st(),key=keyOf(cycle),o=key?outputFor(key):{state:'NOT_COMPUTED',reason:'NO_GROUP'},rot=-s.shown*step;
    let cells='',labels='';
    for(let i=0;i<n;i++){const a=i*step-step/2+rot;cells+='<path class="cycle-cell'+(mod(s.turns,n)===i?' is-focus':'')+'" d="'+band(R.cell[0],R.cell[1],a+0.8,a+step-0.8)+'" data-cycle-cell="'+i+'"></path>';
     {const [x,y]=pt((R.cell[0]+R.cell[1])/2,a+step/2);labels+='<text class="cycle-label" x="'+x+'" y="'+y+'" text-anchor="middle" dominant-baseline="middle">'+esc(model.phases[i])+'</text>';}
     const [x1,y1]=pt(R.cell[0]-1,a),[x2,y2]=pt(R.cell[1]+1,a);cells+='<line class="cycle-tick" data-cycle-boundary="'+i+'" x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'"></line>';}
    let arcs='';
    if(o.state==='ESTIMATED'){const [a0,a1]=span(model,o.from,o.to);arcs+='<path class="cycle-interval" d="'+band(R.iv[0],R.iv[1],a0+rot,a1+rot)+'" data-cycle-interval data-cycle-from="'+esc(label(model,o.from))+'" data-cycle-to="'+esc(label(model,o.to))+'" data-cycle-span-deg="'+(a1-a0).toFixed(1)+'"><title>'+esc(T(l,'추정 구간 ','Estimated interval ')+intervalText(model,o))+'</title></path>';}
    const u=key?userFor(key,model):null;
    if(u){const [a0,a1]=span(model,u.from,u.to);arcs+='<path class="cycle-user-arc" d="'+band(R.user[0],R.user[1],a0+rot,a1+rot)+'" data-cycle-user-arc data-cycle-user-from="'+esc(label(model,u.from))+'" data-cycle-user-to="'+esc(label(model,u.to))+'"><title>'+esc(T(l,'사용자 추정 · 공식 판정 아님','User estimate · not official'))+'</title></path>';}
    cellsG.innerHTML=cells;arcsG.innerHTML=arcs;labelsG.innerHTML=labels;
    svg.setAttribute('data-cycle-display-deg',(s.shown*step).toFixed(3));svg.setAttribute('data-cycle-turn-deg',String(s.turns*step));
    const f=mod(s.turns,n);svg.querySelector('[data-cycle-center]').textContent=model.phases[f];
    svg.setAttribute('aria-label',T(l,model.label[0]+' 국면 개념도 · '+n+'개 국면 · 보는 국면 '+model.phases[f]+'('+(f+1)+'/'+n+') · '+(o.state==='ESTIMATED'?'추정 구간 '+intervalText(model,o):STATE_TEXT[o.state][0]),
     model.label[1]+' phase concept diagram · '+n+' phases · viewing '+model.phases[f]+' ('+(f+1)+'/'+n+') · '+(o.state==='ESTIMATED'?'estimated interval '+intervalText(model,o):STATE_TEXT[o.state][1])));
    el.setAttribute('data-cycle-state',o.state);el.setAttribute('data-cycle-key',key||'');}
   function animate(){const s=st();cancelAnimationFrame(anim);
    if(reduced()||Math.abs(s.shown-s.turns)<1e-6||typeof requestAnimationFrame!=='function'){s.shown=s.turns;draw();return;}
    const from=s.shown,to=s.turns,t0=performance.now();
    const tick=now=>{const k=Math.min(1,(now-t0)/ANIM_MS),e=1-Math.pow(1-k,3);s.shown=from+(to-from)*e;draw();if(k<1)anim=requestAnimationFrame(tick);};anim=requestAnimationFrame(tick);}
   function texts(){const s=st(),key=keyOf(cycle),o=key?outputFor(key):{state:'NOT_COMPUTED',reason:'NO_GROUP'},f=mod(s.turns,n);
    const [head,ev]=officialHtml(cycle,key,model,o,l).split('\u0000');el.querySelector('[data-cycle-state-box]').innerHTML=head;el.querySelector('[data-cycle-evidence-box]').innerHTML=ev;
    svg.setAttribute('data-cycle-turn-deg',String(s.turns*step));
    const tabs=el.querySelectorAll('[data-cycle-phase]');tabs.forEach((b,i)=>{const on=i===f;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;
     b.setAttribute('aria-label',model.phases[i]+' · '+(i+1)+'/'+n+(covers(model,o,i)?T(l,' · 추정 구간에 포함',' · inside the estimated interval'):''));});
    const det=el.querySelector('[data-cycle-focus]');det.setAttribute('aria-labelledby','cycle-'+cycle+'-ph'+f);det.setAttribute('data-cycle-focus',model.phases[f]);det.innerHTML=detailHtml(cycle,key,model,f,o,l);
    if(evidenceHook)det.querySelectorAll('[data-cycle-evidence-slot]').forEach(slot=>{try{const r=evidenceHook({cycle,key,phase:model.phases[f],part:slot.dataset.cycleEvidenceSlot.split(':').slice(-1)[0],codes:[...slot.parentElement.querySelectorAll('[data-cycle-code]')].map(x=>x.dataset.cycleCode),locale:l,slot});if(typeof r==='string')slot.textContent=r;else if(r&&r.nodeType)slot.append(r);}catch(_){}});
    const ch=el.querySelector('[data-cycle-change-box]');ch.innerHTML=s.changed?'<span class="badge partial" data-cycle-changed>'+esc(s.changed)+'</span> '+(o.state==='ESTIMATED'?'<button type="button" data-cycle-goto-interval>'+esc(T(l,'추정 구간으로','Go to the interval'))+'</button>':''):'';
}
   function update(){texts();el.querySelector('[data-cycle-user-box]').innerHTML=userHtml(model,keyOf(cycle),l);draw();animate();}
   function turn(d,how){const s=st(),before=mod(s.turns,n);s.turns+=d;s.userRotated=true;const f=mod(s.turns,n);
    let msg=T(l,'보는 국면 '+model.phases[f]+'('+(f+1)+'/'+n+')','Viewing '+model.phases[f]+' ('+(f+1)+'/'+n+')');
    if(d===1&&before===n-1)msg=T(l,model.phases[before]+' 다음은 '+model.phases[f]+' · 처음으로','After '+model.phases[before]+' comes '+model.phases[f]+' · back to the start');
    else if(d===-1&&before===0)msg=T(l,model.phases[before]+' 이전은 '+model.phases[f]+' · 마지막으로','Before '+model.phases[before]+' is '+model.phases[f]+' · to the end');
    texts();animate();say(msg);
    el.dispatchEvent(new CustomEvent('macro-cycle-focus',{bubbles:true,detail:{cycle,key:keyOf(cycle),phase:model.phases[f],index:f}}));
    if(how==='key')el.querySelector('[data-cycle-index="'+f+'"]').focus();}
   const goTo=(i,how)=>{const d=nearest(st().turns,n,i);if(d)turn(d,how);else if(how==='key')el.querySelector('[data-cycle-index="'+i+'"]').focus();};
   el.addEventListener('click',e=>{const t=e.target.closest('button,[data-cycle-cell]');if(!t||!el.contains(t))return;
    if(t.hasAttribute('data-cycle-prev'))turn(-1);else if(t.hasAttribute('data-cycle-next'))turn(1);
    else if(t.hasAttribute('data-cycle-phase'))goTo(Number(t.dataset.cycleIndex));
    else if(t.hasAttribute('data-cycle-goto-interval')){const k=keyOf(cycle),o=k?outputFor(k):null;st().changed=null;if(o&&o.state==='ESTIMATED'){const d=nearest(st().turns,n,o.from.p);if(d)turn(d);else update();}else update();}
    else if(t.hasAttribute('data-cycle-user-save')){const k=keyOf(cycle);if(!k)return;const pick=s=>{const [phase,part]=String(el.querySelector(s).value).split('|');return{phase,part};};
     const from=pick('select[data-cycle-user-from]'),to=pick('select[data-cycle-user-to]');if(!cellIndex(model,from)||!cellIndex(model,to)||!from.part||!to.part)return;// the arc carries data-cycle-user-from too: read the selects only
     const v=readUser(),list=v.rings[k]||[],seq=list.reduce((m,e)=>Math.max(m,e.seq),0)+1;
     list.push({seq,saved_at:new Date().toISOString().slice(0,19)+'Z',from,to,note:String(el.querySelector('[data-cycle-user-note]').value||'').slice(0,200),system:systemSnapshot(k)});
     v.rings[k]=list.slice(-USER_CAP);
     say(writeUser(v)?T(l,'사용자 추정을 이 기기에 저장했습니다','User estimate saved on this device'):T(l,'이 브라우저에 저장할 수 없습니다','This browser cannot store it'));update();el.querySelector('[data-cycle-user-save]').focus();}
    else if(t.hasAttribute('data-cycle-user-clear')){const k=keyOf(cycle);if(!k)return;const v=readUser();delete v.rings[k];writeUser(v);say(T(l,'이 링의 사용자 추정 기록을 모두 지웠습니다','All user estimates of this ring cleared'));update();el.querySelector('[data-cycle-user-clear]').focus();}
    else if(t.hasAttribute('data-cycle-user-delete')){const k=keyOf(cycle);if(!k)return;const seq=Number(t.dataset.cycleUserDelete),v=readUser();v.rings[k]=(v.rings[k]||[]).filter(e=>e.seq!==seq);writeUser(v);
     say(T(l,'사용자 추정 기록 하나를 지웠습니다','One user estimate record deleted'));update();el.querySelector('[data-cycle-user-save]').focus();}});
   el.querySelector('[data-cycle-tabs]').addEventListener('keydown',e=>{const k=e.key;
    if(k==='ArrowRight'||k==='ArrowDown'){e.preventDefault();turn(1,'key');}else if(k==='ArrowLeft'||k==='ArrowUp'){e.preventDefault();turn(-1,'key');}
    else if(k==='Home'){e.preventDefault();goTo(0,'key');}else if(k==='End'){e.preventDefault();goTo(n-1,'key');}});
   // pointer drag / swipe (mouse, touch, pen); vertical movement stays page scroll (touch-action: pan-y in CSS); no wheel handler
   const drag=el.querySelector('[data-cycle-drag]');let g=null;
   drag.addEventListener('pointerdown',e=>{if(e.button!==undefined&&e.button!==0)return;g={id:e.pointerId,x:e.clientX,y:e.clientY,on:false,px:Math.max(60,drag.getBoundingClientRect().width/3),cell:e.target.closest('[data-cycle-cell]')};});
   drag.addEventListener('pointermove',e=>{if(!g||e.pointerId!==g.id)return;const dx=e.clientX-g.x,dy=e.clientY-g.y;
    if(!g.on){if(Math.abs(dx)<SLOP_PX||Math.abs(dx)<Math.abs(dy))return;g.on=true;try{drag.setPointerCapture(e.pointerId);}catch(_){}cancelAnimationFrame(anim);}
    const s=st();s.shown=s.turns+(-dx)/g.px;draw();e.preventDefault();});
   const end=e=>{if(!g||e.pointerId!==g.id)return;const was=g;g=null;const s=st();
    if(!was.on){if(e.type==='pointerup'&&was.cell)goTo(Number(was.cell.dataset.cycleCell));return;}
    const delta=(was.x-e.clientX)/was.px,steps=Math.sign(delta)*Math.floor(Math.abs(delta)+(1-SNAP_SHARE));
    if(e.type==='pointercancel'||!steps){animate();return;}
    const before=mod(s.turns,n);s.turns+=steps;s.userRotated=true;const f=mod(s.turns,n);texts();animate();
    const wrapF=steps>0&&before+steps>=n,wrapB=steps<0&&before+steps<0;
    say(wrapF?T(l,model.phases[mod(f-1,n)]+' 다음은 '+model.phases[f]+' · 처음으로','after '+model.phases[mod(f-1,n)]+' comes '+model.phases[f]+' · back to the start'):wrapB?T(l,model.phases[mod(f+1,n)]+' 이전은 '+model.phases[f]+' · 마지막으로','before '+model.phases[mod(f+1,n)]+' is '+model.phases[f]+' · to the end'):T(l,'보는 국면 '+model.phases[f]+'('+(f+1)+'/'+n+')','Viewing '+model.phases[f]+' ('+(f+1)+'/'+n+')'));
    el.dispatchEvent(new CustomEvent('macro-cycle-focus',{bubbles:true,detail:{cycle,key:keyOf(cycle),phase:model.phases[f],index:f}}));};
   drag.addEventListener('pointerup',end);drag.addEventListener('pointercancel',end);
   if(cycle==='industry')el.addEventListener('change',e=>{if(!e.target.matches('[data-cycle-group]'))return;industryGroup=e.target.value||null;groupMissing=false;const k=keyOf(cycle);if(k&&!ringState(k).init)follow(k);st().shown=st().turns;update();});
   const k0=keyOf(cycle);if(k0&&!ringState(k0).init)follow(k0);st().shown=st().turns;
   rings[cycle]={update};
  }
  const sw=card.querySelector('[data-cycle-switch]');
  const pick=(c,focus)=>{activeCycle=c;sw.querySelectorAll('[data-cycle-tab]').forEach(b=>{const on=b.dataset.cycleTab===c;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;if(on&&focus)b.focus();});
   card.querySelectorAll('[data-cycle-ring]').forEach(p=>{p.hidden=p.dataset.cycleRing!==c;});};
  sw.addEventListener('click',e=>{const b=e.target.closest('[data-cycle-tab]');if(b)pick(b.dataset.cycleTab,false);});
  sw.addEventListener('keydown',e=>{const i=CYCLES.indexOf(activeCycle);let j=null;if(e.key==='ArrowRight')j=mod(i+1,3);else if(e.key==='ArrowLeft')j=mod(i-1,3);else if(e.key==='Home')j=0;else if(e.key==='End')j=2;if(j!==null){e.preventDefault();pick(CYCLES[j],true);}});
  const m={host,refresh(){if(!host.isConnected){mounts.delete(m);return;}for(const c of CYCLES)rings[c].update();}};
  mounts.add(m);m.refresh();return m;
 }
 // Test/diagnostic view of the RAM state (no storage, no request).
 function snapshot(){return JSON.parse(JSON.stringify({activeCycle,industryGroup,rings:Object.fromEntries(Object.entries(RING).map(([k,v])=>[k,{turns:v.turns,userRotated:v.userRotated}]))}));}
 root.MacroCycleRing=Object.freeze({mount,setPublication,refreshFailed,attachEvidence,snapshot,USER_KEY,MODELS:Object.freeze(Object.fromEntries(Object.entries(MODELS).map(([k,v])=>[k,Object.freeze({phases:Object.freeze([...v.phases])})])))});
})(typeof window!=='undefined'?window:globalThis);
