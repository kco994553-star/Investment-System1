/* 2.2.7 연구 후보 계산 · 저장 · 취소 · 복원 (owner 2026-11-11 「#530 후속 연결」 §3; IS2.dualEngine): under 1. QGV · 1.2, beside
   the sector QGV settings (which are not changed by anything here). It calls the development engine route with an explicitly named
   research candidate (U1 unified-roa-core / U2 unified-sales-core = 통합 연구, S1 sector-reduced-core = 섹터 연구; the 3/3/3
   U2-333 unified-333-eps / U1-333 unified-333-persistence / S1-333 sector-333, qgv-dual-config/2, owner 2026-11-13) and shows the
   engine's own board; nothing is scored, ranked, filled or averaged here.
   - No candidate is preselected: the owner names one. Changing the candidate (or the input) starts a new generation: the shown
     result is cleared at once and any answer that comes back for an earlier request is dropped (늦은 응답), so a previous model's
     result never stays on screen under another name.
   - An answer is used only when IS2.dualQgv.checkAnswer accepts it for that very request (op, request id, model, model_id, the
     board's model_id); a mismatch is an error in this block, never a result.
   - Q / G are shown when V and the total are null; a null total has no total rank (총점 없음 · 순위 없음).
   - 저장 keeps the engine's save_board record for that candidate on this device (IS2.store.dualQgv, its own key; the sector
     QGV record is never read or rewritten). 취소 drops an unsaved result. 복원 asks the engine to replay the saved record exactly
     (same configuration, code and original inputs); when the engine no longer holds the original inputs the answer is
     RETAINED_INPUT_NOT_FOUND and nothing is recalculated under that name — 최신 입력 재계산 is the separate 계산 button.
   - After the engine route restarts (nothing held in its memory), 복원 still replays exactly: the route reads the original inputs
     again from their fixed manifest and accepts only the pair the saved bindings name (원래 입력을 고정 목록에서 다시 읽음). When no
     pinned input matches, the answer is RETAINED_INPUT_NOT_FOUND and the device record stays as it was.
   - The published site has no engine route: ENGINE_NOT_CONNECTED (계산 실행 경로 연결 전). */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const D=()=>I.dualQgv;
const INPUTS=Object.freeze([['DUAL_BOTH_VALID','합성 · 세 축 모두 있음'],['DUAL_QG_ONLY','합성 · Q/G만 있음(V 핵심 관측 없음)']]);
const ERR=Object.freeze({ENGINE_NOT_CONNECTED:'계산 실행 경로 연결 전(개발 경로에서만 계산)',RETAINED_INPUT_NOT_FOUND:'원래 입력이 이 실행 경로에 없음 · 정확 재현 불가 · 최신 입력으로 다시 계산하지 않음',
 MODEL_RESPONSE_MISMATCH:'요청한 모형과 다른 응답 · 쓰지 않음',ENGINE_ANSWER_OTHER_REQUEST:'다른 요청의 응답 · 쓰지 않음',SAVED_SCHEMA_MISMATCH:'연구 저장본이 아닌 기록 · 바꾸지 않음',
 MODEL_ID_REQUIRED:'후보를 먼저 고르세요',ENGINE_UNREACHABLE:'계산 경로 응답 없음'});
const say=c=>ERR[c]||'오류 · '+c;
// Where an exact replay's original inputs came from (owner 2026-11-13 「재시작 후 저장·복원」): kept by this run of the engine
// route, or read again from their fixed manifest after a restart (only the pair the saved bindings name; never the latest input).
const SOURCE=Object.freeze({RETAINED_IN_PROCESS:'원래 입력(이 실행 경로가 보관)',PINNED_INPUT_REREAD:'원래 입력을 고정 목록에서 다시 읽음(재시작 뒤)'});

function block({signal}){
 const st={model_id:null,input:INPUTS[0][0],gen:0,busy:false,shown:null,code:null,msg:null};
 const root=h('div',{class:'sk card cc-wrap',dataset:{deBlock:''}});
 const saved=()=>{let r=null;try{r=I.store.dualQgv.read();}catch(_){r=null;}return r;};
 const draw=()=>{if(!signal.aborted)paint();};
 // A new generation: whatever was shown or in flight belongs to the previous choice.
 const reset=()=>{st.gen++;st.shown=null;st.code=null;st.msg=null;st.busy=false;};
 async function ask(op,fields){const my=++st.gen,req=D().engineRequest(op,st.model_id,fields);st.busy=true;st.code=null;st.msg=null;draw();
  let res=null,chk;try{res=await I.data.engine(req,{signal});chk=D().checkAnswer(req,res);}catch(e){chk={ok:false,code:e&&e.name==='AbortError'?'ABORTED':String(e&&e.message||'ENGINE_UNREACHABLE')};}
  if(signal.aborted||my!==st.gen)return null;   // 늦은 응답: a later choice or request owns the block now
  st.busy=false;if(!chk.ok){st.code=chk.code;draw();return null;}return chk.value;}
 // 계산 = the engine's preview, then the engine's save_board record of exactly that result (kept in RAM, nothing stored), so 저장
 // writes it inside its own click (the device store takes the click itself; a record of another result is never written).
 async function compute(){const v=await ask('preview',{input_id:st.input});if(!v)return;
  const s=await ask('save',{result_hash:v.board.result_hash});if(!s)return;
  st.shown={kind:v.kind,board:v.board,input:v.input_id,record:s.saved,saved:false};draw();}
 function save(e){const sh=st.shown;if(!sh||sh.kind!=='SYNTHETIC_RECALCULATION'||!sh.record||sh.record.result_hash!==sh.board.result_hash)return;
  try{I.store.dualQgv.save(e,sh.record);st.shown={...sh,saved:true};st.msg='이 기기에 저장함 · '+D().MODEL_OF[st.model_id].key+' · 결과 '+sh.record.result_hash.slice(0,12)+'…';}
  catch(err){st.code=String(err&&err.message||'DUAL_QGV_SAVE_FAILED');}draw();}
 async function restore(){const r=saved(),rec=r&&r.state==='OK'?r.value.records[st.model_id]:null;if(!rec)return;
  const v=await ask('replay',{saved:JSON.parse(JSON.stringify(rec))});if(!v)return;st.shown={kind:v.kind,board:v.board,input:v.input_id,saved:true,source:v.input_source||null};draw();}
 function cancel(){reset();draw();}

 function paint(){const M=D(),r=saved(),rec=r&&r.state==='OK'&&st.model_id?r.value.records[st.model_id]:null;
  const chips=h('div',{class:'scroll',role:'group','aria-label':'연구 후보'},...Object.entries(M.MODELS).map(([k,m])=>h('button',{type:'button',class:'chip','aria-pressed':String(st.model_id===m.model_id),
   dataset:{deModel:k,k:'de-model-'+k},onclick:()=>{if(st.model_id===m.model_id)return;st.model_id=m.model_id;reset();draw();}},m.label)));
  const inSel=h('select',{id:'de-input',dataset:{k:'de-input'},onchange:e=>{st.input=e.target.value;reset();draw();}},...INPUTS.map(([v,t])=>h('option',{value:v,selected:v===st.input},t)));
  const can=!!st.model_id&&!st.busy,sh=st.shown;
  const btn=(k,label,on,dis)=>h('button',{type:'button',class:'btn',disabled:dis,dataset:{k,deAct:k}},label);
  const bCompute=btn('de-compute','계산(합성 · 최신 입력)',null,!can),bSave=btn('de-save','저장',null,!can||!sh||sh.kind!=='SYNTHETIC_RECALCULATION'||sh.saved),
   bCancel=btn('de-cancel','취소',null,!sh&&!st.busy&&!st.code),bRestore=btn('de-restore','저장본 복원(정확 재현)',null,!can||!rec);
  bCompute.onclick=()=>{void compute();};bSave.onclick=e=>{save(e);};bCancel.onclick=cancel;bRestore.onclick=()=>{void restore();};
  const state=st.busy?h('p',{class:'pending',role:'status',dataset:{deState:'LOADING'}},'계산 경로에 요청 중'):
   st.code?h('p',{class:'hand err',role:'alert',dataset:{deState:'ERROR',deCode:st.code}},say(st.code),' · ',st.code):
   sh?h('p',{class:'reason',role:'status',dataset:{deState:'READY',deKind:sh.kind,deSource:sh.source||''}},M.KIND_WORD[sh.kind],' · 입력 ',sh.input,sh.source?' · '+SOURCE[sh.source]:'',' · ',M.MODELS[M.MODEL_OF[sh.board.model_id].key].label):
   h('p',{class:'reason',dataset:{deState:st.model_id?'IDLE':'CHOOSE'}},st.model_id?'계산을 누르면 개발 계산 경로에 이 후보로 한 번 요청합니다':'후보를 먼저 고르세요 · 기본·최적·채택 후보는 없음');
  const savedLine=r&&r.state==='INVALID'?h('p',{class:'hand err',dataset:{deSaved:'INVALID'}},'이 기기의 연구 저장본을 읽을 수 없음 · 덮어쓰지 않음'):
   rec?h('p',{class:'reason',dataset:{deSaved:'OK'}},'이 기기 저장본 · 결과 ',rec.result_hash.slice(0,12),'… · 설정 ',rec.bindings.model_hash.slice(0,12),'…'):
   st.model_id?h('p',{class:'reason',dataset:{deSaved:'EMPTY'}},'이 후보의 저장본 없음'):null;
  root.replaceChildren(...[h('h4',null,'연구 후보 계산 (2.2.7 · 통합 U1·U2 / 섹터 S1 · 3/3/3 U2-333·U1-333 / S1-333 · 연구 · 운영 채택 안 됨)'),
   h('p',{class:'reason'},'섹터 QGV 설정(위)과 따로 · 이 칸은 위 저장 설정을 읽거나 바꾸지 않음 · 공식 QGV·포트폴리오 목표는 바뀌지 않음'),
   chips,h('div',{class:'sort-row'},h('label',{for:'de-input'},'입력(합성)'),inSel),
   h('div',{class:'load-row'},bCompute,bSave,bCancel,bRestore),state,savedLine,
   st.msg?h('p',{class:'reason',dataset:{deMsg:''}},st.msg):null,
   sh?boardTable(sh.board):null,
   h('p',{class:'meta'},'이 기기에만 저장 · 다른 기기와 동기화 안 됨 · 백업 파일에 들어가지 않음')].filter(Boolean));}
 function boardTable(b){const M=D(),rows=M.boardRowsView(b,{sectorName:id=>I.taxonomy?I.taxonomy.sectorName(id):id});
  const th=t=>h('th',{scope:'col'},t);
  return h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{deBoard:b.model_id,deResult:b.result_hash}},
   h('caption',null,M.MODELS[M.MODEL_OF[b.model_id].key].label,' · 평가 ',String(b.evaluation_population.code_rows),'행 · 참조 ',String(b.reference_population.issuers),'발행사 · 엔진 행 순서'),
   h('thead',null,h('tr',null,th('기업'),th('Q'),th('G'),th('V'),th('총점'),th('총점 순위'),th('상태'))),
   h('tbody',null,...rows.map(x=>h('tr',{dataset:{deRow:x.company_id}},h('td',null,x.company_id),h('td',null,x.Q),h('td',null,x.G),h('td',null,x.V),h('td',null,x.total),
    h('td',{dataset:{deRank:''}},x.rank),h('td',null,x.status))))));}
 paint();return root;}
I.dualEngine=Object.freeze({block});
})();
