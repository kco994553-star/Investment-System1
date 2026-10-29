/* Menus 1 ~ n+1 (draft boards QGV · Technical · Macro · News · Portfolio · Prompt · SystemTree · Lab and their phone boards).
   P0 skeleton: each menu's numbered sections in the draft's order, every one 연결 전 until its P2 lane wires real data.
   Registered as placeholders: a lane's own screen file (screen-<menu>.js, loaded earlier) keeps its real screen. */
(function(){
'use strict';
const{h,register,parts:{head,section,pending}}=window.IS2;
const MENUS={
 qgv:['1','QGV','기업의 질(Q) · 성장(G) · 가치(V)를 한 장으로',null,[
  ['1-1','1.1 리더보드','순위 · SIC 분류 · 기업 유형 · 수익률 기간 선택 (수익률은 이 기기 시세로만)'],
  ['1-2','1.2 가중치 변화 + 사용자 설정','공격형 · 균형형 · 수비형 · 사용자 설정, 바꾸기 전 ↔ 후'],
  ['1-3','1.3 13F 가중치','기관 보유 변화'],
  ['1-4','1.4 QGV 시스템 내용구성','Q · G · V 요인 트리']]],
 technical:['2','기술적 분석','추세 · 패턴 · 시나리오와 내 노트',null,[
  ['2-1','2.1 기술적 분석 + 정도 설정 + 시나리오','추세 신호와 시나리오'],
  ['2-2','2.2 차트 패턴 + 정도 설정 + 시나리오','패턴 후보'],
  ['2-3','2.3 차트 위 내 노트','펜 · 수평선 · 지우개 · 되돌리기'],
  ['2-4','2.4 기술적 분석 시스템 내용구성','지표 트리']]],
 macro:['3','매크로','경기 · 순환매 · 산업 사이클의 현재 위치',null,[
  ['3-1','3.1 경기 · 주식시장 현재 예상 위치','근거 · 조건 · 확률(공식 국면은 아직 미산출)'],
  ['3-2','3.2 순환매 위치 (저점 / 고점)','업종 순환'],
  ['3-3','3.3 산업 사이클 (SIC 분류 기준)','산업별 위치'],
  ['3-4','3.4 내가 고르는 현재 위치','이 기기 선택'],
  ['3-5','3.5 나비효과','지표 연결'],
  ['3-6','3.6 매크로 시스템 내용구성','근거 목록 트리']]],
 news:['4','뉴스','공시 · 뉴스 · 관계망','',[
  ['4-1','4.1 관계망','기업 관계'],
  ['4-2','4.2 공시 · 뉴스','공시와 뉴스 요약'],
  ['4-3','4.3 뉴스 시스템 내용구성','출처 트리']]],
 portfolio:['5','포트폴리오','세 가지 포트폴리오와 일일 보고 (보유·거래는 이 기기와 내 시트에서만)','',[
  ['5-1','5.1 세 가지 포트폴리오','실제 · 모델 · 모의'],
  ['5-2','5.2 포트폴리오 보고','보고'],
  ['5-3','5.3 모의 포트폴리오 일일 보고','일일 보고'],
  ['5-4','5.4 포트폴리오 시스템 내용구성','트리']]],
 prompts:['6','프롬프트 라이브러리','개인화 — 어떤 값을 보여 줄까?','',[
  ['6-1','6.1 프롬프트 라이브러리','프롬프트 목록'],
  ['6-2','6.2 개인화','표시할 값 고르기']]],
 tree:['n','투자시스템 한 장 지도','메뉴와 세부 화면 전체 구조','',[
  ['n-1','n. 구조 트리','모든 메뉴와 세부 화면']]],
 lab:['n+1','Lab','실험 · 검증','',[
  ['lab-1','n+1.1 백테스트','백테스트 결과'],
  ['lab-2','n+1.2 전진 검증','전진검증 원장 요약']]],
};
for(const[id,[no,title,lead,color,sections]]of Object.entries(MENUS))
 register(id,()=>h('div',{class:'screen',dataset:{menuScreen:id}},head(no,title,lead),...sections.map(([sid,stamp,what])=>section(sid,stamp,color,pending(what)))),{placeholder:true});
})();
