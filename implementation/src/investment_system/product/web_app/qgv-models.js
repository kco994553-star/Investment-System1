/* QGV 모형 구분 (IS2.qgvModels; owner 2026-11-10 「통합 QGV·섹터 QGV」 queue §2): which QGV model the 2.1 leaderboard shows, and
   which ones are ready to be chosen. Pure words and states; no request, no storage, no score.
   - 공식 QGV: the published official result (sec-qgv2.json, IS2.qgv). The only model the table reads today.
   - 통합 QGV (연구): one common core model for every evaluated company (same variants, formulas, weights and scoring rule). Its
     preset and result contract are Codex's (#437 6766774987); until a checked result exists it is 계산 연결 전, never a table of
     official numbers relabelled.
   - 섹터 QGV (연구): the sector · accounting-model core model of Codex's engine #505. The engine runs from 1.2 on synthetic input
     (development route); a leaderboard result for the evaluated population is not delivered yet, so it is 리더보드 결과 전달 전.
   - Never: one model's score shown as the other's, an average or sum of the two, a combined rank stitched from sector ranks, a
     financial-wide rank across accounting models that the producer did not rank together. A filter never changes a model's
     original score, rank, denominator or reference N.
   A model whose state is not READY cannot be chosen; its reason is shown instead. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgvModels=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const STATE=Object.freeze({READY:'선택 가능',NOT_CONNECTED:'계산 연결 전',RESULT_NOT_DELIVERED:'리더보드 결과 전달 전',DATA_SHORT:'자료 부족',NOT_APPLICABLE:'산식 적용 부적합'});
const KIND=Object.freeze({OFFICIAL:'공식',RESEARCH_DEFAULT:'연구 기본값',MINE:'내 설정'});
const MODELS=Object.freeze([
 Object.freeze({id:'OFFICIAL',label:'공식 QGV',kind:'OFFICIAL',state:'READY',reason:null,
  note:'공개 게시된 공식 결과 · 지금 표가 읽는 모형'}),
 Object.freeze({id:'INTEGRATED',label:'통합 QGV',kind:'RESEARCH_DEFAULT',state:'NOT_CONNECTED',reason:'COMMON_PRESET_CONTRACT_PENDING',
  note:'모든 평가 기업에 같은 공통 핵심 요소·산식·비중 · 공통 preset과 결과 계약 수령 전(Codex)'}),
 Object.freeze({id:'SECTOR',label:'섹터 QGV',kind:'RESEARCH_DEFAULT',state:'RESULT_NOT_DELIVERED',reason:'SECTOR_BOARD_RESULT_NOT_DELIVERED',
  note:'섹터·회계모형별 고정 핵심 요소 · 엔진 계산은 1.2 가중치·QGV 구성에서 합성 입력으로만 · 평가 집단 리더보드 결과 전달 전'})]);
const RULES=Object.freeze([
 '두 모형의 점수는 같은 척도가 아님 · 평균·합산·비교 점수로 쓰지 않음',
 '섹터 점수를 이어 붙여 통합 순위를 만들지 않음 · 회계모형이 다른 순위를 합치지 않음',
 '필터는 원점수·원순위·분모·참조 N을 바꾸지 않음',
 '연구 모형은 공식 QGV·포트폴리오 목표에 반영되지 않음']);
const REASON=Object.freeze({COMMON_PRESET_CONTRACT_PENDING:'공통 핵심 요소 preset·결과 계약 수령 전',SECTOR_BOARD_RESULT_NOT_DELIVERED:'섹터 모형의 평가 집단 결과 전달 전'});
const byId=id=>MODELS.find(m=>m.id===id)||null;
const selectable=id=>{const m=byId(id);return!!m&&m.state==='READY';};
// The model to show: the asked one when it can be chosen, otherwise the official one (never a not-ready model's empty table).
const resolve=id=>selectable(id)?id:'OFFICIAL';
const line=m=>m.label+' · '+KIND[m.kind]+' · '+STATE[m.state]+(m.reason?' · '+(REASON[m.reason]||m.reason):'');
return Object.freeze({STATE,KIND,MODELS,RULES,REASON,byId,selectable,resolve,line});
});
