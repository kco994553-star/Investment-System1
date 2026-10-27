/* Menu 1 QGV first-paint skeleton (feature 2.1, P2-2a); screen-qgv-live.js fills it after IS2.ready (P1_DATA_LAYER.md §1.1). */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,pending}}=I;
const later=(route,k,x,fail)=>{const a=()=>route.signal.aborted;(I.ready||Promise.reject()).then(()=>{const L=I.qgvLive;if(L&&!a())L[k](route,x);},()=>{if(fail&&!a())fail();});};
// Board add/QGVLeaderboard: stamp (menu numbers), feature number, hand line, what the block shows once connected.
const LB=[['1.1.1 평가 대상과 목록','2.1.1','무엇을 줄 세웠는지 먼저 말함','보기 범위 · 평가 대상 · 리더보드 표'],
 ['1.1.2 순위와 정렬','2.1.2','정렬은 줄 순서 · 순위는 번호','정렬 · 방향 · 모집단 구분'],
 ['1.1.3 분류와 필터','2.1.3','산업 분류와 투자 유형은 서로 다른 분류','업종군 · SIC · 기업 유형 · 자료 상태'],
 ['1.1.4 기간별 수익률','2.1.4','수익률은 가격에서 나온 값이라 기기에서만 계산','기간 · 이 기기 가격으로만 계산'],
 ['1.1.5 산출 상태별 목록','2.1.5','순위에 섞지 않고 목록을 나눠 보여 줌','종합 순위 · 참고 목록 · 일부 축 · 확인 필요'],
 ['1.1.6 공식 결과와 개인 결과','2.1.6','누가 계산했고 어떤 V로 계산했는지 배지로','공식 가중치 결과 · 내 설정 미리보기'],
 ['1.1.7 후보 선정 연결','2.1.7','짧게만 · 자세한 그림은 5.1 모델 후보','모델 후보 · 선정 · 제외 근거']];
const off=(...c)=>h('button',{type:'button',class:'btn',disabled:true},...c);
function render(route){
 const bodies={},blocks=LB.map(([stamp,fn,hand,what])=>{const body=bodies[fn]=h('div',{class:'lb-body'},pending(what));
  return h('div',{class:'lb',dataset:{lb:fn}},h('div',{class:'lb-head'},h('h3',{class:'stamp sub blue',tabindex:'-1'},stamp),h('span',{class:'meta'},'기능 ',fn),h('span',{class:'hand'},hand)),body);});
 const buttons=['구글 로그인 준비','로그인','가격 불러오기 · 이 기기에서만'].map((t,i)=>off(h('span',{class:'m-only'},['①','②','③'][i]+' '),t));
 const chips=h('div',{class:'scroll lb-chips',dataset:{qgvChips:''}},h('span',{class:'chip wait'},'점수 갱신 · 연결 전'));
 const conn=h('span',{class:'chip wait',dataset:{qgvConn:''}},'연결 전');
 const status=h('div',{class:'band-lines',role:'status',dataset:{qgvStatus:''}});
 const nav=h('nav',{class:'scroll lb-nav','aria-label':'QGV 하위 화면'},h('span',{class:'chip on','aria-current':'page'},'1.1 리더보드'),
  ...[['1.2 가중치','1-2'],['1.3 13F (연구 단계)','1-3']].map(([t,id])=>h('button',{type:'button',class:'chip',disabled:true,dataset:{to:id}},t)),
  h('span',{class:'chip wait'},'1.5 QGV 상세 · 연결 전'),h('button',{type:'button',class:'chip',disabled:true,dataset:{to:'1-4'}},'1.4 구조 트리'));
 const band=h('div',{class:'sk band',dataset:{qgvBand:''}},chips,
  h('div',{class:'conn'},conn,buttons[0],h('span',{'aria-hidden':'true'},'→'),buttons[1],h('span',{'aria-hidden':'true'},'→'),buttons[2],
   h('span',{class:'hand'},'준비되기 전에는 세 버튼 모두 꺼짐 · 누를 때만 가격을 부름')),status,nav);
 later(route,'leaderboard',{band,chips,conn,buttons,status,nav,bodies},()=>{for(const b of Object.values(bodies))b.replaceChildren(h('p',{class:'na',dataset:{na:'LOADER_FAILED'}},'층을 불러오지 못해 리더보드를 그리지 못했습니다'));});
 return h('div',{class:'screen lb-screen'},head('1','QGV','기업의 질(Q) · 성장(G) · 가치(V)를 한 장으로'),band,
  section('1-1','1.1 리더보드','blue',...blocks),
  section('1-2','1.2 가중치','blue',pending('다음 단계에서 연결')),
  section('1-3','1.3 13F (연구 단계)','blue',pending('다음 단계에서 연결')),
  section('1-4','1.4 구조 트리','blue',pending('다음 단계에서 연결')));
}
register('qgv',render);
})();
