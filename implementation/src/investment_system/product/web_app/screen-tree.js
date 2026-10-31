/* Feature 8 · 투자시스템 전체 내용구성 트리 (spec v1.0 8 / 8.1.1–8.1.4 · menu n · route #/tree; boards SystemTree · m/MTree ·
   add/TreeCommon). Loaded before screen-menus.js, so this real screen replaces the menu placeholder.
   - The whole product structure as one tree: the menus 0 ~ n+1 from IS2.MENU (their order, numbers, names and routes), under each
     the feature numbers of docs/SPEC/FUNCTION_HIERARCHY_v1.0.md (levels 2 ~ 4, names as written there; 4.5 is "나비효과",
     DC-17), and the detail screens IS2.DETAILS with where each is entered from (TreeCommon: proposals). The structure is static
     and written here: the old app's tree (web_assets/ia-screens.js) builds HTML strings and reads AppShell, which this app does
     not load. Menu numbers are the draft's (core.js), feature numbers the spec's (FUNCTION_STATUS §0 maps them).
   - Every node is a link to its route (a feature goes to its menu's screen; 2.4 QGV 상세 opens from 기업 검색, a detail to
     #/detail/<id>). Tree semantics (WAI-ARIA navigation tree): role tree / treeitem / group, aria-level · setsize · posinset ·
     expanded, one tab stop (roving tabindex); ↑ ↓ move, → opens or goes to the first child, ← closes or goes to the parent,
     Home / End, * opens the siblings, Enter follows the link. The 44 px caret opens and closes without leaving the page; 모두
     펼치기 / 모두 접기 buttons do the same for every node. Which nodes are open is kept in this module's RAM only.
   - Status per screen node, asked from the screen registry at render time and nothing else: 화면 있음 (a real screen is
     registered), 준비 중 (a placeholder or no screen yet), 상태 확인 불가 (the registry could not answer: partial failure, the rest
     stays). No percentage, phase or 구현 분류 is invented: the per-feature classes and the 개발 · 병합 · 게시 · 실제 확인 steps of
     8.1.3 are shown as 준비 중 with what is missing.
   - Reads nothing (no IS2.data call, no request) and does not wait for IS2.ready: the whole tree draws at the first paint and
     stays whole when the P1 layer fails. States: ready, partial (a status unknown, or a feature area missing from IS2.MENU), empty
     (IS2.MENU is an empty list), error (IS2.MENU unreadable or drawing failed; 다시 그리기 redraws). No number from the boards. */
(function(){
'use strict';
const I=window.IS2,{h,icon,register,parts:{head,section,mascot}}=I;
// Spec v1.0 areas (level 1) per menu id: [feature number, spec name].
const AREA={search:['1','홈 · 기업검색'],qgv:['2','QGV'],technical:['3','기술적 분석'],macro:['4','매크로'],news:['5','뉴스 · 공시 · 관계망'],
 portfolio:['6','포트폴리오'],prompts:['7','프롬프트 라이브러리'],tree:['8','투자시스템 전체 내용구성 트리'],lab:['9','Lab']};
// Levels 2 ~ 4 per menu id: [number, name, menu number (FUNCTION_STATUS §0) or null, children, own screen id, note]. The notes are
// the owner's fixed words for the unfinished models (공식 국면 미산출 · 준비 중), never a result.
const L=(n,t,k,note)=>[n,t,null,k||[],null,note||null];
const FEATURES={
 search:[['1.1','기업검색 및 기업 진입','0',[L('1.1.1','기업 검색'),L('1.1.2','기업 통합 진입'),L('1.1.3','검색 전 콘텐츠'),L('1.1.4','검색 전 개인화')]]],
 qgv:[['2.1','리더보드','1.1',[L('2.1.1','평가 대상과 목록'),L('2.1.2','순위와 정렬'),L('2.1.3','분류와 필터'),L('2.1.4','기간별 수익률'),L('2.1.5','산출 상태별 목록'),L('2.1.6','공식 결과와 개인 결과'),L('2.1.7','후보 선정 연결')]],
  ['2.2','가중치 변화 · 사용자 설정','1.2',[L('2.2.1','축 가중치'),L('2.2.2','내부 요인 가중치'),L('2.2.3','프리셋'),L('2.2.4','변경 영향'),L('2.2.5','결측과 적용 비중'),L('2.2.6','설정 관리')]],
  ['2.3','13F 기반 가중치 연구','1.3',[L('2.3.1','과거 보유 기록'),L('2.3.2','가중치 탐색'),L('2.3.3','백테스트 연결'),L('2.3.4','연구와 채택 구분')]],
  ['2.4','QGV 상세',null,[L('2.4.1','기업 설명과 분류'),L('2.4.2','점수와 원지표 상세'),L('2.4.3','자료 상태와 커버리지'),L('2.4.4','V의 입력 기준'),
   L('2.4.5','기업 비교 레이더',[L('2.4.5.1','축 구성'),L('2.4.5.2','비교군'),L('2.4.5.3','결측 처리'),L('2.4.5.4','상세 확인')])],'company'],
  ['2.5','QGV 내용구성 트리','1.4',[L('2.5.1','구조 탐색'),L('2.5.2','설명과 예시'),L('2.5.3','상세 연결')]]],
 technical:[['3.1','기술적 지표 · 시나리오','2.1',[L('3.1.1','차트 탐색'),L('3.1.2','지표와 정도 설정'),L('3.1.3','시나리오'),L('3.1.4','결과 구분')]],
  ['3.2','차트 패턴 · 시나리오','2.2',[L('3.2.1','패턴 탐색'),L('3.2.2','정도 설정'),L('3.2.3','확인·실패·무효화'),L('3.2.4','패턴 카드와 시나리오'),L('3.2.5','데이터 적합성')]],
  ['3.3','차트 노트','2.3',[L('3.3.1','직접 작성'),L('3.3.2','편집과 저장'),L('3.3.3','분석과 분리')]],
  ['3.4','기술적 분석 내용구성 트리','2.4',[L('3.4.1','구조 탐색'),L('3.4.2','설명과 예시')]]],
 macro:[['4.1','경기·주식시장 국면','3.1',[L('4.1.1','국면 그래프',null,'공식 국면 미산출'),L('4.1.2','국면 탐색'),L('4.1.3','근거 세로선',[L('4.1.3.1','근거 시점'),L('4.1.3.2','근거 설명'),L('4.1.3.3','근거 탐색')]),
   L('4.1.4','기존 매크로 연결'),L('4.1.5','판단 상태')]],
  ['4.2','순환매','3.2',[L('4.2.1','위치',null,'위치 모델 준비 중'),L('4.2.2','조정 조건'),L('4.2.3','확률')]],
  ['4.3','SIC 산업 사이클','3.3',[L('4.3.1','산업 선택'),L('4.3.2','현재 예상 위치',null,'사이클 위치 준비 중'),L('4.3.3','조정 조건과 확률')]],
  ['4.4','사용자 국면 판단','3.4',[L('4.4.1','위치 선택'),L('4.4.2','저장과 비교')]],
  ['4.5','나비효과','3.5',[L('4.5.1','사건과 파급 경로'),L('4.5.2','투자 가설'),L('4.5.3','근거와 반증'),L('4.5.4','관계망 연결')],null,'준비 중'],
  ['4.6','매크로 내용구성 트리','3.6',[L('4.6.1','구조 탐색'),L('4.6.2','설명과 예시')]]],
 news:[['5.1','관계망','4.1',[L('5.1.1','기업 중심 관계'),L('5.1.2','연결 근거'),L('5.1.3','검색 전 추천'),L('5.1.4','개인 설정')]],
  ['5.2','공시 · 뉴스','4.2',[L('5.2.1','목록과 개인화'),L('5.2.2','요약'),L('5.2.3','영향 분석'),L('5.2.4','주가 반영 여부'),L('5.2.5','신규·중복·변경'),L('5.2.6','컨센서스 변화'),L('5.2.7','수집 상태')]],
  ['5.3','뉴스 내용구성 트리','4.3',[L('5.3.1','구조 탐색'),L('5.3.2','설명과 예시')]]],
 portfolio:[['6.1','포트폴리오 구성','5.1',[L('6.1.1','종류 구분'),L('6.1.2','모델 후보와 선정'),L('6.1.3','비중과 조건'),L('6.1.4','입력과 버전'),L('6.1.5','개인·모의 구성 관리')]],
  ['6.2','실제 포트폴리오 일일·주간 보고','5.2',[L('6.2.1','보고 내용'),L('6.2.2','기간 선택'),L('6.2.3','보고 불가 시 프롬프트'),L('6.2.4','결과 검토')]],
  ['6.3','모의 포트폴리오 일일·주간 보고','5.3',[L('6.3.1','모의 성과'),L('6.3.2','판단 추적'),L('6.3.3','보고 불가 시 프롬프트')]],
  ['6.4','포트폴리오 내용구성 트리','5.4',[L('6.4.1','구조 탐색'),L('6.4.2','설명과 예시')]]],
 prompts:[['7.1','프롬프트 탐색 · 사용 · 개인화','6',[L('7.1.1','분야별 탐색'),L('7.1.2','맥락 반영'),L('7.1.3','복사와 실행 안내'),L('7.1.4','내 사본'),L('7.1.5','화면 연결')]]],
 tree:[['8.1','전체 구조와 영역 연결','n',[L('8.1.1','시스템 구조'),L('8.1.2','영역 상세'),L('8.1.3','구현 상태'),L('8.1.4','예시와 근거')]]],
 lab:[['9.1','백테스트','n+1.1',[L('9.1.1','연구 목적'),L('9.1.2','실험 구성'),L('9.1.3','가중치 연구'),L('9.1.4','평가 기준'),L('9.1.5','데이터 조건'),L('9.1.6','결과 보고')]],
  ['9.2','전진검증','n+1.2',[L('9.2.1','관측 기록'),L('9.2.2','이후 성과'),L('9.2.3','평가 가능 여부'),L('9.2.4','운영 증거')]]],
};
// Where each detail screen is entered from (board add/TreeCommon 8.1.2; every entrance is a proposal there).
const FROM={settings:'전체 메뉴 · 머리의 기기 칩',['data-status']:'화면마다 기준 시각 칩 → 자세히',financials:'2.4 QGV 상세 → 근거 · 자세히',['sec-cover']:'2.4 QGV 상세 → 근거',
 playbook:'6.2 일일 보고 → 자세히',['virtual-trading']:'6.1 · 6.3 모의 → 자세히',['target-v1']:'6.1 모델 후보 → 자세히'};
const STATUS={ready:['화면 있음','chip'],pending:['준비 중','chip wait'],unknown:['상태 확인 불가','chip err']};
const RIGHT='M19 15 L26 22 L19 29',DOWN='M15 19 L22 26 L29 19',DOT='M22 21.5 L22 22.5';
// Open nodes: RAM only (kept while the page lives, gone on reload). The menus start open, as on the boards.
const OPEN=new Set();let seeded=false;

// Registry answers, at render time (a lane that lands later shows up on the next render).
function screenStatus(id){try{const R=window.IS2;if(typeof R.screen!=='function'||typeof R.isPlaceholder!=='function')return'unknown';
 return !R.screen(id)||R.isPlaceholder(id)?'pending':'ready';}catch(_){return'unknown';}}
function detailStatus(id){try{const R=window.IS2;if(typeof R.detail!=='function')return'unknown';return R.detail(id)?'ready':'pending';}catch(_){return'unknown';}}

// Node model: {key, href, label: [nodes], status, current, kids}.
function features(list,href){return list.map(([no,name,menuNo,kids,own,note])=>({key:'f:'+no,href:own==='company'?I.href('search'):href,status:own?screenStatus(own):null,
 label:[h('b',null,no),' ',name,menuNo?h('span',{class:'meta'},' · 메뉴 ',menuNo):null,own==='company'?h('span',{class:'meta'},' · 기업 상세 · 검색에서 기업을 고르면 열림'):null,
  note?h('span',{class:'meta',dataset:{prep:no}},' · ',note):null],
 kids:features(kids,href)}));}
function model(){
 const R=window.IS2,menu=R.MENU,details=R.DETAILS;
 if(!Array.isArray(menu))throw Error('MENU_UNREADABLE');
 const seen=new Set(),nodes=menu.map(m=>{
  if(!m||typeof m.id!=='string')throw Error('MENU_UNREADABLE');
  const area=AREA[m.id],href=I.href(m.id);seen.add(m.id);
  return{key:'m:'+m.id,href,status:screenStatus(m.id),current:m.id==='tree',
   label:[h('span',{class:'opt-name'+(m.id==='tree'?' here':'')},m.no,'. ',m.ko),area?h('span',{class:'meta'},' 기능 ',area[0],' · ',area[1]):h('span',{class:'meta'},' 기능 번호 연결 없음')],
   kids:features(FEATURES[m.id]||[],href)};});
 const missing=Object.keys(AREA).filter(id=>!seen.has(id)).map(id=>AREA[id][0]);
 const dl=Array.isArray(details)?details.filter(d=>d&&typeof d.id==='string'):[];
 if(dl.length)nodes.push({key:'g:details',href:null,status:null,label:[h('span',{class:'opt-name'},'세부 화면'),h('span',{class:'meta'},' 메뉴 번호 없음')],
  kids:dl.map(d=>({key:'d:'+d.id,href:I.href('detail',d.id),status:detailStatus(d.id),
   label:[d.ko],sub:FROM[d.id]?['들어오는 곳 (제안): ',FROM[d.id]]:null,kids:[]}))});
 return{nodes,missing,empty:menu.length===0};
}
const chip=st=>{const[t,c]=STATUS[st];return h('span',{class:c,dataset:{statusChip:st}},t);};
const glyph=(d,toggle)=>{const s=icon([d],44);if(toggle)s.dataset.treeToggle='';return s;};
function item(n,level,pos,size){
 const parent=n.kids.length>0,on=parent&&OPEN.has(n.key),gid=parent?'tree-g-'+n.key.replace(/[^a-z0-9]+/gi,'-'):null;
 // A group heading without a route of its own (세부 화면) is a treeitem without href: it only opens and closes.
 const a=h(n.href?'a':'div',{role:'treeitem',href:n.href||null,class:'lk',tabindex:'-1','aria-level':level,'aria-setsize':size,'aria-posinset':pos,
  'aria-expanded':parent?String(on):null,'aria-owns':gid,'aria-current':n.current?'page':null,dataset:{treeNode:n.key,...(n.status?{nodeStatus:n.status}:{})}},
  glyph(parent?(on?DOWN:RIGHT):DOT,parent),h('span',null,...n.label,n.status?[' ',chip(n.status)]:null,n.sub?[h('br'),h('span',{class:'note'},...n.sub)]:null));
 // The group carries [hidden] and no class: .branch sets display, which would win over the hidden attribute (app.css has no [hidden] rule).
 return h('div',{role:'none',dataset:{treeWrap:n.key}},a,parent?h('div',{role:'group',id:gid,hidden:!on},h('div',{class:'branch'},n.kids.map((k,i)=>item(k,level+1,i+1,n.kids.length)))):null);
}
// Keyboard and pointer behaviour of one drawn tree (WAI-ARIA tree pattern; the listeners end with the tree's DOM).
function behave(tree){
 const all=()=>[...tree.querySelectorAll('[role=treeitem]')];
 const shown=()=>all().filter(a=>!a.closest('[role=group][hidden]'));
 const kids=a=>a.getAttribute('aria-expanded')!==null;
 const isOpen=a=>a.getAttribute('aria-expanded')==='true';
 const rove=a=>{for(const x of all())x.tabIndex=x===a?0:-1;};
 const move=a=>{if(!a)return;rove(a);a.focus();};
 const parentOf=a=>{const g=a.parentElement.closest('[role=group]');return g&&tree.contains(g)?g.previousElementSibling:null;};
 const set=(a,on)=>{const g=a.nextElementSibling;if(!g||!kids(a))return;a.setAttribute('aria-expanded',String(on));g.hidden=!on;
  const p=a.querySelector('[data-tree-toggle] path');if(p)p.setAttribute('d',on?DOWN:RIGHT);if(on)OPEN.add(a.dataset.treeNode);else OPEN.delete(a.dataset.treeNode);
  if(!on&&g.contains(document.activeElement))move(a);};
 tree.addEventListener('keydown',e=>{
  const a=e.target.closest('[role=treeitem]');if(!a||e.altKey||e.ctrlKey||e.metaKey||e.isComposing)return;
  const list=shown(),i=list.indexOf(a);
  switch(e.key){
   case'ArrowDown':move(list[i+1]);break;
   case'ArrowUp':move(list[i-1]);break;
   case'Home':move(list[0]);break;
   case'End':move(list[list.length-1]);break;
   case'ArrowRight':if(kids(a)){if(!isOpen(a))set(a,true);else move(a.nextElementSibling.querySelector('[role=treeitem]'));}break;
   case'ArrowLeft':if(kids(a)&&isOpen(a))set(a,false);else move(parentOf(a));break;
   case'*':for(const w of a.parentElement.parentElement.children){const x=w.firstElementChild;if(x&&x.getAttribute('role')==='treeitem')set(x,true);}break;
   case'Enter':case' ':if(a.hasAttribute('href')&&e.key==='Enter')return;if(kids(a))set(a,!isOpen(a));break;// Enter on a link follows it (native)
   default:return;
  }
  e.preventDefault();
 });
 tree.addEventListener('click',e=>{const t=e.target.closest('[data-tree-toggle]'),a=e.target.closest('[role=treeitem]');if(!a)return;
  if(t||!a.hasAttribute('href')){e.preventDefault();set(a,!isOpen(a));move(a);}});
 tree.addEventListener('focusin',e=>{const a=e.target.closest('[role=treeitem]');if(a)rove(a);});
 const first=shown()[0];if(first)first.tabIndex=0;
 return{every(on){for(const a of all())if(kids(a))set(a,on);const cur=all().find(x=>x.tabIndex===0);if(!cur||cur.closest('[role=group][hidden]'))rove(shown()[0]);}};
}
const block=(id,stamp,fn,hand,...body)=>h('div',{class:'lb',dataset:{treeBlock:id}},h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},stamp),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null),h('div',{class:'lb-body'},...body));
const go=(id,t,...p)=>h('a',{class:'lk',href:I.href(id,...p)},'→ ',t);
// 재료 (board SystemTree; phone: the one-line box of MTree).
function sources(){
 const S=[['SEC 공시','companyfacts · 10-K · 8-K · 13F'],['DART','한국 공시'],['시세','내 기기에서 누를 때만 · 공개 화면에 가격 없음'],['경제지표','금리 · 고용 · 물가 · 신용'],['뉴스','GDELT · IR'],['내 정보','보유 · 설정 · 노트 (비공개)']];
 return block('sources','재료 (어디서 오나)',null,'자료가 들어오는 곳',
  h('div',{class:'pop pc-only'},S.map(([b,t])=>h('div',{class:'sk dashed pop-box'},h('b',null,b),h('span',{class:'hand'},t)))),
  h('p',{class:'sk pop-box m-only'},'재료: SEC · DART · 시세(내 기기에서 누를 때만) · 경제지표 · 뉴스 · 내 정보(비공개)'),
  h('div',{class:'node'},h('b',null,'투자시스템'),h('span',{class:'hand'},' · 기업 검색 → 한 기업을 QGV + 기술적 분석 + 매크로 + 뉴스로 봄')));
}
// 8.1.1 한 줄 흐름 (board TreeCommon) + 서로 이어지는 선 (board SystemTree, without its example values).
function flow(){
 const steps=[['① 자료',['SEC · DART · 경제지표 · 뉴스 = 공개','시세 = 내 기기에서 누를 때만','내 정보 = 비공개'],[go('detail','세부 · 자료 상태','data-status')]],
  ['② 계산',['QGV Q · G · V','기술 지표'],[go('qgv','QGV'),go('technical','기술')]],
  ['③ 판단',['매크로 국면 · 준비 중 (공식 국면 미산출)','차트 패턴','뉴스 영향'],[go('macro','매크로'),go('technical','기술'),go('news','뉴스')]],
  ['④ 후보',['N10 · N15 · N20','TARGET v1 초안'],[go('qgv','QGV'),go('portfolio','포트폴리오')]],
  ['⑤ 포트폴리오',['모델 · 실제 · 모의','보고 불가 → 프롬프트'],[go('portfolio','포트폴리오'),go('prompts','프롬프트')]],
  ['⑥ 검증',['9.1 백테스트','9.2 전진검증'],[go('lab','Lab')]]];
 return block('8.1.1','한 줄 흐름','8.1.1','자료 → 계산 → 판단 → 후보 → 포트폴리오 → 검증 · 상자의 링크로 그 화면에',
  h('ol',{class:'pop outside-list','aria-label':'투자시스템 흐름'},steps.map(([t,lines,links])=>h('li',{class:'sk pop-box',dataset:{flowStep:t}},
   h('b',null,t),lines.map(x=>h('span',{class:'hand'},x)),h('span',{class:'links'},links)))),
  h('p',{class:'hand'},'서로 이어지는 선'),
  h('ul',{class:'news-lines'},['SEC 공시 → QGV Q · G → 모델 포트폴리오 후보 → 일일 보고 "확인할 것"','시세(내 기기 · 누를 때만) → 기술적 분석 → 같은 보고의 기술 항목',
   '경제지표 → 매크로 국면(공식 국면 미산출) → 순환매 · 산업 사이클(위치 준비 중)','8-K 공시 → 공시 · 뉴스 → 관계망 → 나비효과(준비 중)'].map(x=>h('li',null,x))),
  h('p',{class:'hand'},'같은 엔진을 따로 만들지 않음 · 각 메뉴의 화면과 그 안의 내용구성 트리로 이동'));
}
// 8.1.3 구현 상태 (what the chips mean, the true counts, and what is not shown yet).
function status(counts){
 const why='기능별 구현 분류(기존 구현 · 부분 구현 · 구현 예정 · 결정 대기)와 개발 · 병합 · 게시 · 실제 확인 단계';
 const prep=typeof I.parts.notReady==='function'?I.parts.notReady('준비 중 · '+why,['화면이 읽을 기능 상태 공개 자료']):h('p',{class:'pending'},'준비 중 · ',why,' · 없는 것: 화면이 읽을 기능 상태 공개 자료');
 prep.dataset.prep='8.1.3';
 return block('8.1.3','구현 상태 읽는 법','8.1.3','화면 단위 · 앱의 화면 목록에서 바로 확인',
  h('ul',{class:'outside-list'},
   h('li',null,chip('ready'),h('span',{class:'who'},'이 앱에 화면이 연결됨 · 화면이 있어도 그 안의 기능과 자료가 모두 된 것은 아님')),
   h('li',null,chip('pending'),h('span',{class:'who'},'아직 자리만 있음 · 들어가면 연결 전 표시'))),
  h('p',{class:'hand',dataset:{treeSummary:''}},'메뉴 · 기업 상세 · 세부 화면 기준: 화면 있음 ',String(counts.ready),' · 준비 중 ',String(counts.pending),counts.unknown?' · 상태 확인 불가 '+counts.unknown:''),
  prep);
}
// 8.1.4 예시와 근거 (the three shapes every screen uses; this tree itself shows no value).
function shapes(){
 return block('8.1.4','예시와 실제 구분','8.1.4','값마다 세 모양 중 하나',
  h('ul',{class:'outside-list'},
   h('li',null,h('b',null,'[예시]'),h('span',{class:'who'},'설명용 그림 값 · 계산 결과 아님')),
   h('li',null,h('b',null,'[실제]'),h('span',{class:'who'},'공개 자료 · 파일 이름 · 기준 시각과 함께')),
   h('li',null,h('b',null,'[NA]'),h('span',{class:'who'},'NA와 사유 글 · 0으로 채우지 않음'))),
  h('p',{class:'hand'},'이 트리는 구조만 보여 주고 값을 쓰지 않음 · 값과 근거는 노드를 눌러 들어간 화면에서'));
}
const stateCard=(kind,mood,text,reason,...more)=>h('div',{class:'sk state-card',role:kind==='error'?'alert':null,dataset:{treeCard:kind}},mascot(mood),h('p',{class:kind==='error'?'err':null},text),h('p',{class:'reason'},reason),...more);
function render(route){
 let root=null;
 const redraw=()=>{if(root&&root.isConnected&&!(route.signal&&route.signal.aborted))root.replaceWith(render(route));};
 const frame=(state,...body)=>(root=h('div',{class:'screen',dataset:{menuScreen:'tree',treeState:state}},
  head('n','투자시스템 한 장 지도','전체 내용구성 트리 · 메뉴 · 기능 번호 · 세부 화면이 어디로 이어지는지'),section('n-1','n. 구조 트리',null,...body)));
 let m;
 try{m=model();}catch(e){return frame('error',stateCard('error','alarm','구조 트리를 그리지 못했습니다','메뉴 목록을 읽지 못했습니다 · 다시 그리거나 새로고침해 주세요',
  h('button',{class:'btn',type:'button',dataset:{treeRedraw:''},onclick:redraw},'다시 그리기')));}
 if(!seeded){seeded=true;for(const n of m.nodes)OPEN.add(n.key);}
 if(m.empty)return frame('empty',stateCard('empty','plain','보여 줄 메뉴가 없습니다','메뉴 목록이 비어 있습니다 · 구조를 그릴 항목이 없음'));
 const counts={ready:0,pending:0,unknown:0};
 const walk=list=>{for(const n of list){if(n.status)counts[n.status]++;walk(n.kids);}};walk(m.nodes);
 const tree=h('div',{class:'grid-3',role:'tree','aria-label':'투자시스템 전체 구조',dataset:{tree:''}},m.nodes.map((n,i)=>item(n,1,i+1,m.nodes.length)));
 const api=behave(tree);
 const problems=[counts.unknown?h('p',{class:'err',dataset:{treePartial:'status'}},'일부 화면의 상태를 확인하지 못했습니다 · 구조와 이동 링크는 그대로입니다'):null,
  m.missing.length?h('p',{class:'err',dataset:{treePartial:'menu'}},'메뉴 목록에 없는 기능 영역은 빼고 그렸습니다 · 기능 ',m.missing.join(' · ')):null].filter(Boolean);
 const tools=h('div',{class:'links'},h('button',{class:'btn',type:'button',dataset:{treeAll:'open'},onclick:()=>api.every(true)},'모두 펼치기'),
  h('button',{class:'btn',type:'button',dataset:{treeAll:'close'},onclick:()=>api.every(false)},'모두 접기'),
  h('span',{class:'hand'},'키보드: ↑ ↓ 이동 · → 펼치기 · ← 접기 · Home / End 처음 · 끝 · Enter 열기'));
 return frame(problems.length?'partial':'ready',sources(),
  block('8.1.2','메뉴 · 기능 · 세부 화면','8.1.2','노드를 누르면 그 화면으로 · 왼쪽 › 표시를 누르면 펼치고 접기',tools,...problems,tree),
  flow(),status(counts),shapes());
}
register('tree',render);
})();
