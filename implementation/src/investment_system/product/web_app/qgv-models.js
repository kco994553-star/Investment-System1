/* QGV 모형 구분 (IS2.qgvModels; owner 2026-11-10 「통합 QGV·섹터 QGV」 queue §2, 2026-11-11 「두 모형 실제 연결」 §3): which QGV
   model the 2.1 leaderboard shows, and which ones can be chosen now. Pure words and states; no request, no storage, no score.
   - 공식 QGV: the published official result (sec-qgv2.json, IS2.qgv). Always selectable.
   - U1 / U2 (통합 연구) and S1 (섹터 연구): Codex #529's preregistered research candidates (qgv-dual-delivery/1, IS2.dualQgv). One is
     selectable exactly when the operating504 delivery, checked by IS2.dualQgv against the result already delivered, is in RAM and
     carries that board. Selectable does not mean complete: Q / G, factors and missing reasons are readable even while V and the
     total are null everywhere; a null total has no total rank. Recalculation, saving and replay are separate states.
   - U1 and U2 are two different unified candidates; S1 is the sector candidate (core reduction). Never: one model's score shown as
     another's, an average or sum, a combined rank stitched from sector ranks, a rank across accounting models the producer did not
     rank together. A filter never changes a model's original score, rank, denominator or reference N. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgvModels=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const STATE=Object.freeze({READY:'선택 가능',RESULT_NOT_READ:'비공개 연구 결과 읽기 전'});
const KIND=Object.freeze({OFFICIAL:'공식',RESEARCH:'연구 후보',MINE:'내 설정'});
const MODELS=Object.freeze([
 Object.freeze({id:'OFFICIAL',label:'공식 QGV',kind:'OFFICIAL',research:false,note:'공개 게시된 공식 결과'}),
 Object.freeze({id:'U1',label:'통합 연구 U1',kind:'RESEARCH',research:true,note:'모든 평가 기업에 같은 핵심 요소(ROA · ROA 개선 · 이익·장부)와 같은 참조집단'}),
 Object.freeze({id:'U2',label:'통합 연구 U2',kind:'RESEARCH',research:true,note:'U1과 같고 G만 매출 성장 · U1과 다른 후보'}),
 Object.freeze({id:'S1',label:'섹터 연구 S1',kind:'RESEARCH',research:true,note:'섹터·회계모형별 축소 핵심 요소 · 순위는 섹터×회계모형 안에서만'})]);
const RULES=Object.freeze([
 '모형마다 점수는 같은 척도가 아님 · 평균·합산·비교 점수로 쓰지 않음',
 '섹터 점수를 이어 붙여 통합 순위를 만들지 않음 · 회계모형이 다른 순위를 합치지 않음',
 '총점이 없으면 총점 순위도 없음 · V·총점이 없어도 Q·G·개별 요소·결손 사유는 조회함',
 '필터는 원점수·원순위·분모·참조 N을 바꾸지 않음',
 '연구 후보는 공식 QGV·포트폴리오 목표에 반영되지 않음 · 화면 재계산 연결 안 됨(보관 결과만)']);
const REASON=Object.freeze({RESULT_NOT_READ:'0. 기업 검색 → 비공개 분류 묶음 → 운영504 두 모형 결과 불러오기 뒤 선택 가능'});
const byId=id=>MODELS.find(m=>m.id===id)||null;
// ready: the research boards the checked operating504 delivery carries (e.g. ['U1','U2','S1']), or none.
const has=(ready,id)=>Array.isArray(ready)&&ready.includes(id);
const stateOf=(id,ready)=>{const m=byId(id);return!m?null:!m.research||has(ready,id)?'READY':'RESULT_NOT_READ';};
const selectable=(id,ready)=>stateOf(id,ready)==='READY';
// The model to show: the asked one when it can be chosen, otherwise the official one (never a not-ready model's empty table).
const resolve=(id,ready)=>selectable(id,ready)?id:'OFFICIAL';
const line=(m,ready)=>{const s=stateOf(m.id,ready);return m.label+' · '+KIND[m.kind]+' · '+STATE[s]+(s==='READY'?'':' · '+REASON[s]);};
return Object.freeze({STATE,KIND,MODELS,RULES,REASON,byId,stateOf,selectable,resolve,line});
});
