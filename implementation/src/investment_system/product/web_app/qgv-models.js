/* QGV 모형 구분 (IS2.qgvModels; owner 2026-11-10 「통합 QGV·섹터 QGV」 queue §2, 2026-11-11 「두 모형 실제 연결」 §3): which QGV
   model the 2.1 leaderboard shows, and which ones can be chosen now. Pure words and states; no request, no storage, no score.
   - 공식 QGV: the published official result (sec-qgv2.json, IS2.qgv). Always selectable.
   - U1 / U2 (통합 연구) and S1 (섹터 연구): Codex #529's preregistered research candidates (qgv-dual-delivery/1, IS2.dualQgv). One is
     selectable exactly when the operating504 delivery, checked by IS2.dualQgv against the result already delivered, is in RAM and
     carries that board. Selectable does not mean complete: Q / G, factors and missing reasons are readable even while V and the
     total are null everywhere; a null total has no total rank. Recalculation, saving and replay are separate states.
   - U1 and U2 are two different unified candidates; S1 is the sector candidate (core reduction). Their cores are reduced ones
     (U1/U2 Q1 · G1 · V2, S1 Q2 · G1 · V2): not the owner's 3/3/3 composition (owner 2026-11-13).
   - U2-333 / U1-333 / S1-333 (owner 2026-11-13 「QGV 3/3/3」; Codex #534 qgv-333-contract/1, #437 6849630620 / 6850109806): the
     Q3 · G3 · V3 candidates under their own model ids (unified-333-eps/0.1.0, unified-333-persistence/0.1.0, sector-333/0.1.0),
     qgv-dual-config/2 and their registered configuration hashes (IS2.dualQgv.MODELS). The contract, synthetic and boundary examples
     and the private real results are delivered; one is selectable exactly when the checked operating504 3/3/3 delivery (its own
     slot, never the reduced one's) is in RAM and carries that board. Never shown as a recommended or better-performing model. Never: one model's score shown as
     another's, an average or sum, a combined rank stitched from sector ranks, a rank across accounting models the producer did not
     rank together. A filter never changes a model's original score, rank, denominator or reference N. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgvModels=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const STATE=Object.freeze({READY:'선택 가능',RESULT_NOT_READ:'비공개 연구 결과 읽기 전'});
const KIND=Object.freeze({OFFICIAL:'공식',RESEARCH:'연구 후보',MINE:'내 설정'});
const MODELS=Object.freeze([
 Object.freeze({id:'OFFICIAL',label:'공식 QGV',kind:'OFFICIAL',research:false,note:'공개 게시된 공식 결과'}),
 Object.freeze({id:'U1',label:'통합 연구 U1',kind:'RESEARCH',research:true,core:'Q1 · G1 · V2(축소 구성 · 3/3/3 아님)',note:'모든 평가 기업에 같은 핵심 요소(ROA · ROA 개선 · 이익·장부)와 같은 참조집단'}),
 Object.freeze({id:'U2',label:'통합 연구 U2',kind:'RESEARCH',research:true,core:'Q1 · G1 · V2(축소 구성 · 3/3/3 아님)',note:'U1과 같고 G만 매출 성장 · U1과 다른 후보'}),
 Object.freeze({id:'S1',label:'섹터 연구 S1',kind:'RESEARCH',research:true,core:'Q2 · G1 · V2(축소 구성 · 3/3/3 아님)',note:'섹터·회계모형별 축소 핵심 요소 · 순위는 섹터×회계모형 안에서만'}),
 // The 3/3/3 candidates (owner 2026-11-13; Codex #534): their own delivery (set 333), selectable once that delivery is checked in RAM.
 Object.freeze({id:'U2-333',label:'통합 연구 U2-333',kind:'RESEARCH',research:true,gen:'Q333',core:'Q3 · G3 · V3',note:'unified-333-eps/0.1.0 · G에 희석 EPS 3년 성장 · 축 1:1:1 · 요소 1/9씩 · 우선 검증 후보(추천·성과 우수 아님)'}),
 Object.freeze({id:'U1-333',label:'통합 연구 U1-333',kind:'RESEARCH',research:true,gen:'Q333',core:'Q3 · G3 · V3',note:'unified-333-persistence/0.1.0 · G에 매출 성장 지속성 · U2-333과 G 한 요소만 다름 · 대조 후보'}),
 Object.freeze({id:'S1-333',label:'섹터 연구 S1-333',kind:'RESEARCH',research:true,gen:'Q333',core:'Q3 · G3 · V3',note:'sector-333/0.1.0 · 섹터×회계모형별 구성 · 축 비중은 기존 섹터 설정 · 축 안 요소 1/3씩 · 순위는 섹터×회계모형 안에서만 · Equity REIT는 G 세 번째 정의 준비 중(G·총점 없음, Q·V는 따로)'})]);
const RULES=Object.freeze([
 '모형마다 점수는 같은 척도가 아님 · 평균·합산·비교 점수로 쓰지 않음',
 '섹터 점수를 이어 붙여 통합 순위를 만들지 않음 · 회계모형이 다른 순위를 합치지 않음',
 '총점이 없으면 총점 순위도 없음 · V·총점이 없어도 Q·G·개별 요소·결손 사유는 조회함',
 '필터는 원점수·원순위·분모·참조 N을 바꾸지 않음',
 '연구 후보는 공식 QGV·포트폴리오 목표에 반영되지 않음 · 화면 재계산 연결 안 됨(보관 결과만)']);
const REASON=Object.freeze({RESULT_NOT_READ:'0. 기업 검색 → 비공개 분류 묶음 → 운영504 두 모형 결과 불러오기 뒤 선택 가능',
 RESULT_NOT_READ_333:'계약·합성·실자료 전달됨 · 0. 기업 검색 → 비공개 분류 묶음 → 운영504 3/3/3 결과 불러오기(인증 · 검증) 뒤 선택 가능 · 기존 연구 결과·공식 QGV·저장 설정은 그대로'});
const byId=id=>MODELS.find(m=>m.id===id)||null;
// ready: the research boards the checked operating504 delivery carries (e.g. ['U1','U2','S1']), or none.
const has=(ready,id)=>Array.isArray(ready)&&ready.includes(id);
const stateOf=(id,ready)=>{const m=byId(id);return!m?null:!m.research||has(ready,id)?'READY':'RESULT_NOT_READ';};
const selectable=(id,ready)=>stateOf(id,ready)==='READY';
// The model to show: the asked one when it can be chosen, otherwise the official one (never a not-ready model's empty table).
const resolve=(id,ready)=>selectable(id,ready)?id:'OFFICIAL';
const line=(m,ready)=>{const s=stateOf(m.id,ready);return m.label+' · '+KIND[m.kind]+(m.core?' · 핵심 '+m.core:'')+' · '+STATE[s]+(s==='READY'?'':' · '+REASON[m.gen==='Q333'?s+'_333':s]);};
return Object.freeze({STATE,KIND,MODELS,RULES,REASON,byId,stateOf,selectable,resolve,line});
});
