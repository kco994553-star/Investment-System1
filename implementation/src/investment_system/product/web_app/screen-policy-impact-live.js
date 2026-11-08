/* 3.5 나비효과 · 정책·지정학 (features 4.5.1.1–4.5.4.1, owner 2026-11-07; contract docs/frontend_v2/POLICY_IMPACT_V1.md).
   Reads policy-impact.json (Codex policy-impact-view/2 public or /1 private, #509 c2ae92a0) and, optionally, its title / news
   navigation sidecar policy-impact-navigation.json (bound to that exact view by hash) through the layer (IS2.data.static, same
   origin) and IS2.policyImpact.validate / validateNavigation; nothing else. When the file is not published the screen says 자료 없음 (정책 파일
   미게시); a synthetic file is never put in its place (tests inject it explicitly).
   - The engine decides: the current revision of a policy is the one current_policy_revisions names, the list order is the
     bundle's, REVIEW_REQUIRED (이전 분석 · 재검토 필요) and review_due are read as delivered. This screen never picks a
     revision, compares evidence times or re-judges a hypothesis; a date never changes a status.
   - macro(route, {body, params}): inside the existing 4.5 block of #/macro. The list is read on 「정책·지정학 열기」 or when the
     route names a policy (#/macro/policy/<policy_id>[/<revision_id>], a link or back / forward), so opening #/macro alone sends
     no request for a file that is not published yet. List: 유형 · 관할 · 상태 · 기업 filters (values present in the file),
     cards with 상태 · 적용 범위 · 발표일 · 시행일 · 기업 연결. Detail: ① 무엇이 바뀌었나 (current or an older revision) ② 관련
     기업 (exposure evidence and policy applicability apart; none = 연결 근거 미확인, never 영향 없음) ③ 영향 가설 (단계 ·
     성립 조건 · 반대 조건 · 확인할 것; REVIEW_REQUIRED apart) ④ 원문 · 변경 이력 · 검토 기록 ⑤ 다음 확인. Filters and the list
     scroll position live in RAM and come back after a detail and 뒤로.
   - companyCard(route, {after, cid}): the folded 관련 정책 card of a company page (read when it is opened).
   - news(route, {body, links}): 5.2 → 4.5, on a click: the policies citing a news link of the current list.
   States told apart: 자료 없음 · 불러오기 실패 (다시 읽기) · 규격 불일치 (file refused whole) · 등록 정책 0건 · 검색 결과 0건 ·
   수동 검토 / 갱신 실패 (마지막 정상본) · 합성 · 시험용 / 실자료 · 역사 사례. No score, rank, probability or netting; QGV, macro
   gates and prices are not read or changed here. Text is set as text; only https links outside reserved test domains become
   links (rel noopener noreferrer). */
(function(){
'use strict';
const I=window.IS2,{h,href}=I;
const P=()=>I.policyImpact;
const V={filters:{type:null,jurisdiction:null,status:null,company:null},scroll:null,opened:false};
const utc=v=>v?String(v).replace('T',' ').replace(/(:\d{2})(\.\d+)?(Z|\+00:00)$/,'$1 UTC'):'—';
const dated=d=>!d||d.precision==='UNKNOWN'?'미확인':d.precision==='DATE'?d.value+' (날짜만)':utc(d.value)+(d.timezone?' · '+d.timezone:'');
const period=p=>(p.start||'시작 미확인')+' ~ '+(p.end||'끝 미확인');
const reasons=codes=>codes.map(c=>P().text(P().REASON_TEXT,c)).join(' · ');
const companyRow=id=>{try{return I.companies.get(id);}catch(_){return null;}};
const label=id=>{const r=companyRow(id);return r?(r.name_ko||r.name_en||r.ticker):id;};
const companyEl=id=>{const r=companyRow(id);
 return r?h('a',{href:href('company',r.id),class:'lk',dataset:{polCompany:id}},label(id)):h('span',{dataset:{polCompany:id,na:'COMPANY_UNRESOLVED'}},id,' · 기업 식별 미해결');};
const ext=(u,txt)=>P().linkable(u)?h('a',{href:u,target:'_blank',rel:'noopener noreferrer',class:'lk',dataset:{polExternal:''}},txt,' ↗'):h('span',{dataset:{linkWithheld:''}},txt);
const card=(state,words,why,alert,...more)=>h('div',{class:'sk state-card',role:alert?'alert':null,dataset:{polState:state}},I.parts.mascot(alert?'alarm':'plain'),h('b',null,words),why?h('span',{class:'reason'},why):null,...more);
const chip=(txt,data,cls='chip')=>h('span',{class:cls,dataset:data||{}},txt);

// The one read of the page (the layer keeps it; a failed read is tried again on the next call).
// The company list is awaited with it (no new file: the search list's own), so company links resolve on a direct visit.
// The navigation sidecar is optional: not published -> the file's own titles and no 5.2 links (NONE); refused -> the same, with
// its code (INVALID); it never changes a policy fact, a status or an evidence list.
async function readNav(record,delivery){const name=P().DELIVERY[delivery].nav;let n=null;try{n=await I.data.static(name);}catch(_){n=null;}
 if(n===null){let st=null;try{st=I.data.state(name);}catch(_){st=null;}return {state:st&&st.state==='NOT_PUBLISHED'?'NONE':'FAILED',index:P().navIndex(null)};}
 const r=await P().validateNavigation(n,record);return r.ok?{state:'OK',index:P().navIndex(r.value)}:{state:'INVALID',code:r.code,path:r.path,index:P().navIndex(null)};}
// The public file first; only when it is not published, the development-only private name (never allowed on Pages). Each file
// is read as its own delivery path; neither is ever read as the other. The file comes as its delivered bytes (IS2.data.static);
// decodeView checks and reads those same bytes, and the navigation sidecar is checked against that record (navigation/2: the
// byte hash; /1: the canonical digest as before).
async function readOne(delivery){const name=P().DELIVERY[delivery].file;let v=null;try{v=await I.data.static(name);}catch(_){v=null;}
 if(v===null){let st=null;try{st=I.data.state(name);}catch(_){st=null;}return st&&st.state==='NOT_PUBLISHED'?{state:'NONE'}:{state:'FAILED',text:st&&st.text||'읽기 실패'};}
 const d=v&&v.kind==='DELIVERED_BYTES'?await P().decodeView(v.copy()):{ok:false,code:'VIEW_BYTES_REQUIRED',path:'$'};
 if(!d.ok)return {state:'INVALID',code:d.code,path:d.path,delivery};
 const r=P().validate(d.value.json,{delivery});if(!r.ok)return {state:'INVALID',code:r.code,path:r.path,delivery};
 const nav=await readNav(d.value,delivery);const vw=P().view(r.value);vw.nav=nav.index;vw.navState=nav;return {state:'OK',view:vw};}
async function load(){const ready=I.companies&&I.companies.ready?I.companies.ready().catch(()=>null):null;
 let res=await readOne('PUBLIC');if(res.state==='NONE')res=await readOne('PRIVATE_DEV');await ready;return res;}
const titleOf=(vw,r)=>P().titleOf(r,vw.nav);
// Official title, Korean explanation and identifier apart (Codex navigation/1); without the sidecar, the file's title as it is.
function titleLines(vw,r){const t=P().titleState(r,vw.nav),out=[];
 if(t.state==='OFFICIAL')out.push(h('p',{class:'reason',dataset:{polTitleState:'OFFICIAL'}},t.text),h('p',{dataset:{polTitleKo:''}},t.ko,h('span',{class:'reason'},' · ',t.koText)));
 else if(t.text)out.push(h('p',{class:'reason',dataset:{polTitleState:t.state}},t.text));
 out.push(h('p',{class:'reason',dataset:{polIdentifier:r.policy_id}},'정책 식별자 ',r.policy_id,' · 개정 ',r.revision_id));
 if(vw.navState&&vw.navState.state==='INVALID')out.push(h('p',{class:'hand err',dataset:{polNavState:'INVALID'}},'제목·기사 연결 파일 규격 불일치 · 사용하지 않음 · ',vw.navState.code,' · ',vw.navState.path));
 return out;}
function stateCard(res,retry){
 if(res.state==='NONE')return card('NONE','자료 없음 · 정책 파일 미게시','policy-impact.json이 아직 게시되지 않았습니다 · 합성·지어낸 정책을 대신 보이지 않음');
 if(res.state==='INVALID')return card('INVALID','규격 불일치 · 파일 전체 거부',res.code+' · '+res.path,true);
 return card('FAILED','불러오기 실패',res.text,true,h('button',{type:'button',class:'btn',dataset:{k:'pol-retry'},onclick:retry},'다시 읽기'));}

function band(vw){const P_=P(),r=vw.refresh,f=vw.freshness,out=[];
 out.push(h('p',{class:'sk status-line',dataset:{polBand:vw.data_kind}},chip(P_.text(P_.KIND_DATA_TEXT,vw.data_kind),{polKind:vw.data_kind}),
  chip(vw.delivery==='PUBLIC'?'공개 파일':'비공개 개발 자료 · 이 개발 경로 전용 · 게시본 아님',{polDelivery:vw.delivery}),
  ' 현재 지원: ',vw.scope.policy_types.map(x=>P_.text(P_.TYPE_TEXT,x)).join(' · '),' · 관할 ',vw.scope.jurisdictions.join(' · '),' · 선별 소표본(검토한 범위만)',
  ' · 조회 기준 ',utc(vw.as_of),' (',vw.query_timezone,') · 정책 확인 ',vw.policy_as_of?utc(vw.policy_as_of):'이 조회 시점의 확인 기록 없음',
  ' · 마지막 원천 확인 ',utc(f.last_source_check_at),' · 마지막 검토 ',utc(f.last_reviewed_at)));
 if(vw.reason_codes.length)out.push(h('p',{class:vw.historical?'hand err':'reason',dataset:{polBundleReasons:vw.reason_codes.join(' ')}},reasons(vw.reason_codes)));
 if(r.mode==='MANUAL_REVIEW')out.push(h('p',{class:'reason',dataset:{polRefresh:'MANUAL_REVIEW'}},'수동 검토 자료 · 마지막 수동 검토 ',utc(r.last_manual_review_at),' · 자동 수집 결과가 아님'));
 else{const bad=r.result==='PARTIAL_FAILED'||r.result==='FAILED'||r.result==='INCOMPLETE';
  out.push(h('p',{class:bad?'hand err':'reason',dataset:{polRefresh:r.result}},P_.text(P_.REFRESH_TEXT,r.result),' · 마지막 시도 ',utc(r.last_attempt_at),' · 마지막 성공 ',utc(r.last_success_at),
   r.retained_bundle_id?' · 유지한 정상본 '+r.retained_bundle_id+' (정책 확인 '+utc(r.retained_policy_as_of)+')':'',r.incomplete_ranges.length?' · 미조회 '+r.incomplete_ranges.join(', '):''));
  r.sources.forEach((s,i)=>{if(s.result!=='UPDATED'&&s.result!=='NO_NEW_ITEMS')out.push(h('p',{class:'hand err',dataset:{polSourceRefresh:String(i)}},'원천 ',String(i+1),' · ',P_.text(P_.REFRESH_TEXT,s.result),
   s.incomplete_ranges.length?' · 미조회 '+s.incomplete_ranges.join(', '):''));});}
 if(f.review_due===true)out.push(h('p',{class:'hand err',dataset:{polReviewDue:'TRUE'}},'검토 예정일 지남 · 재검토 필요 (정책 효력이 끝났다는 뜻이 아님)'));
 else if(f.review_due===null)out.push(h('p',{class:'reason',dataset:{polReviewDue:'NULL'}},'다음 검토 예정일 미정'));
 if(f.reason_codes.length)out.push(h('p',{class:'reason',dataset:{polFreshness:f.reason_codes.join(' ')}},reasons(f.reason_codes)));
 return out;}

// The current judgment of a policy: exposures and hypotheses the engine did not mark REVIEW_REQUIRED.
const live=list=>list.filter(x=>x.review_status!=='REVIEW_REQUIRED'),stale=list=>list.filter(x=>x.review_status==='REVIEW_REQUIRED');
function linksLine(p){const cur=live(p.exposures),companies=new Set(cur.map(e=>e.company_id));
 const doc=cur.filter(e=>e.evidence_status==='DOCUMENTED'&&e.policy_applicability==='DOCUMENTED').length;
 return companies.size?h('p',{class:'reason',dataset:{polLinks:String(companies.size)}},'연결 기업 ',String(companies.size),'곳 · 노출·적용 근거 확인 ',String(doc),'건 · 확인 필요 ',String(cur.length-doc),'건')
  :h('p',{class:'reason',dataset:{polLinks:'0'}},'연결된 기업 노출 기록 없음 · 연결 근거 미확인 (영향 없음이라는 뜻이 아님)');}
function statusChips(vw,x){const P_=P(),st=P_.status(vw,x);
 return [chip(P_.text(P_.TYPE_TEXT,x.policy_type)),' ',chip(st.text,st.historical?{polStatus:x.lifecycle_status,polHistorical:''}:{polStatus:x.lifecycle_status},st.historical?'chip wait':'chip'),
  x.subsidy_stage?h('span',{class:'chip wait',dataset:{polStage:x.subsidy_stage}},P_.text(P_.STAGE_TEXT,x.subsidy_stage)):null];}

function listView(vw,body,rerender){const P_=P(),fc=P_.facets(vw),F=V.filters;
 const sel=(k,lab,opts,txt)=>h('div',{class:'sort-row'},h('label',{for:'pol-'+k},lab),h('select',{id:'pol-'+k,dataset:{k:'pol-'+k},onchange:e=>{F[k]=e.target.value||null;rerender();}},
  h('option',{value:''},'전체'),...opts.map(o=>h('option',{value:o,selected:F[k]===o},txt(o)))));
 const filters=h('div',{class:'pol-filters'},sel('type','유형',fc.type,x=>P_.text(P_.TYPE_TEXT,x)),sel('jurisdiction','관할',fc.jurisdiction,x=>x),
  sel('status','정책 상태',fc.status,x=>P_.text(P_.STATUS_TEXT,x)),sel('company','기업',fc.company,label));
 const rows=P_.list(vw,F);
 const count=h('p',{class:'reason',dataset:{polCount:String(rows.length)}},String(rows.length),'건 · 수집·검토한 범위의 수 · 0건은 영향 없음이나 세계 정책 없음이 아님');
 let content;
 if(!vw.order.length)content=h('p',{class:'reason',dataset:{polEmpty:'FILE'}},'등록된 정책 0건 · 검토 범위에 아직 없음 · 영향 없음이 아님');
 else if(!rows.length)content=h('div',{dataset:{polEmpty:'FILTER'}},h('p',{class:'reason'},'검색 결과 0건 · 조건은 그대로'),h('button',{type:'button',class:'btn',dataset:{k:'pol-clear'},onclick:()=>{for(const k of Object.keys(F))F[k]=null;rerender();}},'조건 모두 풀기'));
 else content=h('ul',{class:'pol-list'},...rows.map(p=>{const x=p.current;
  return h('li',{class:'sk pol-card',dataset:{polCard:p.policy_id}},
   h('p',{class:'pol-card-head'},h('a',{href:href('macro','policy',p.policy_id),class:'pol-title',dataset:{k:'pol-open-'+p.policy_id},onclick:()=>{V.scroll=window.scrollY;}},titleOf(vw,x)),' ',
    ...statusChips(vw,x),stale(p.hypotheses).length||stale(p.exposures).length?h('span',{class:'chip wait',dataset:{polStale:''}},'이전 분석 · 재검토 필요 있음'):null),
   h('p',{class:'reason'},'적용 범위 · ',x.scope_description),
   h('p',{class:'reason'},'발표 ',dated(x.published),' · 시행 ',dated(x.effective_from),' · 종료 ',dated(x.effective_to),p.parent?' · 상위 '+p.parent:'',p.older.length?' · 이전 개정 '+p.older.length+'개':''),
   linksLine(p));}));
 body.replaceChildren(...band(vw),filters,count,content);
 if(V.scroll!==null){const y=V.scroll;V.scroll=null;requestAnimationFrame(()=>window.scrollTo(0,y));}}

function refLine(vw,r){const s=P().source(vw,r),P_=P();
 return h('li',{dataset:{polRef:r.source_id}},s?ext(s.url,s.title):r.source_id,' · ',r.locator,' · ',r.claim,s?' · '+P_.text(P_.KIND_TEXT,s.kind)+' · '+P_.text(P_.VERIFY_TEXT,s.verification_status):'');}
const refs=(vw,list)=>list.length?h('ul',{class:'news-lines'},...list.map(r=>refLine(vw,r))):h('p',{class:'reason',dataset:{na:'NO_EVIDENCE'}},'근거 문서 없음');
function reviewLines(vw,group,idv,rev){const rs=P().reviewsOf(vw,group,idv,rev);
 return rs.length?h('ul',{class:'news-lines',dataset:{polReviews:String(rs.length)}},...rs.map(r=>h('li',{dataset:{polReviewMethod:r.method}},P().text(P().METHOD_TEXT,r.method),' · 검토 ',utc(r.reviewed_at),' · 기록 ',utc(r.recorded_at),' · 검토자와 작성자 분리')))
  :h('p',{class:'reason',dataset:{polReviews:'0'}},'검토 기록 없음');}
// 공통 분류 (DC-48): the company's common sector next to its name as context only — the exposure, its evidence and its
// applicability are the engine's and never follow from the sector (IS2.classification; nothing when no record set is loaded).
function ccContext(cid){const C=I.classification,st=C&&typeof C.state==='function'?C.state():null;if(!st||st.state!=='OK')return null;
 const row=companyRow(cid),r=C.recordFor(row&&typeof row.code==='string'?row.code:cid);// the record's company_id is the Universe504 code
 return h('span',{class:'reason',dataset:{ccContext:r.state,ccRecord:r.record_id||''}},' · 공통 섹터 ',r.sector&&r.sector.status==='CONFIRMED'?C.sectorName(r.sector.id):r.words,' (문맥 · 노출 근거와 별개)');}
function exposureLine(vw,e){const P_=P();
 return h('li',{class:'sk pol-exposure',dataset:{polExposure:e.exposure_id,polEvidence:e.evidence_status,polApplicability:e.policy_applicability}},
  h('p',null,companyEl(e.company_id),ccContext(e.company_id),' · ',P_.text(P_.EXPOSURE_TEXT,e.exposure_type),' · ',h('b',null,P_.text(P_.EVIDENCE_TEXT,e.evidence_status)),' · ',h('b',null,P_.text(P_.APPLY_TEXT,e.policy_applicability))),
  h('p',null,e.description),h('p',{class:'reason'},'기간 ',period(e.period),' · 정책 개정 ',e.policy_revision_id),
  e.ratio?h('p',{class:'reason',dataset:{polRatio:''}},'비율 ',String(Math.round(e.ratio.value*1000)/10),'% · 분모 ',e.ratio.denominator_description,' · ',e.ratio.scope)
   :h('p',{class:'reason',dataset:{polRatio:'NULL'}},'비율 없음 · ',reasons(e.reason_codes),' · 0%가 아님'),
  e.ratio&&e.reason_codes.length?h('p',{class:'reason'},reasons(e.reason_codes)):null,
  h('details',null,h('summary',{class:'lk'},'노출 근거 · 검토 기록'),refs(vw,e.evidence_refs),reviewLines(vw,'exposures',e.exposure_id,e.exposure_revision_id)),
  h('p',{class:'reason'},'검토 ',utc(e.reviewed_at),' · ',P_.text(P_.REVIEW_TEXT,e.review_status)));}
function watchLine(vw,w){const P_=P();let go=null;
 const av=P_.availability(w.availability);
 // UNKNOWN availability links nowhere (never read as public, never as 자료 없음).
 if(w.availability==='UNKNOWN')go=null;
 else if(w.kind==='MACRO_SERIES'&&w.availability==='PUBLIC_REFERENCE')go=h('a',{href:href('macro'),class:'lk',dataset:{polWatchLink:'MACRO'}},'→ 4.1 지표 보기');
 else if(w.kind==='COMPANY_DISCLOSURE'&&companyRow(w.reference_id))go=h('a',{href:href('company',companyRow(w.reference_id).id),class:'lk',dataset:{polWatchLink:'COMPANY'}},'→ 기업 화면');
 else if(w.kind==='POLICY_UPDATE'&&vw.policies.has(w.reference_id))go=h('a',{href:href('macro','policy',w.reference_id),class:'lk',dataset:{polWatchLink:'POLICY'}},'→ 정책');
 return h('li',{dataset:{polWatch:w.kind,polAvailability:w.availability}},P_.text(P_.WATCH_TEXT,w.kind),' · ',w.kind==='COMPANY_DISCLOSURE'?label(w.reference_id):w.reference_id,' · ',w.rationale,' · ',h('span',{dataset:{polAvailabilityKnown:av.known?'yes':'no'}},av.text),go?' ':null,go);}
function hypothesisBlock(vw,x){const P_=P(),old=x.review_status==='REVIEW_REQUIRED';
 return h('div',{class:'sk pol-hypothesis',dataset:{polHypothesis:x.hypothesis_id,polReview:x.review_status}},
  h('p',null,chip('조건부 영향 가설'),' ',old?chip('이전 분석 · 재검토 필요',null,'chip wait'):null,' ',h('b',null,x.claim)),
  h('p',{class:'reason'},'대상 ',...x.company_ids.flatMap((c,i)=>[i?', ':'',companyEl(c)]),' · 기준 정책 개정 ',x.policy_revision_id,old?' (근거를 새 개정으로 바꾸지 않음)':''),
  h('ol',{class:'pol-steps'},...x.steps.map(s=>h('li',{dataset:{polEpistemic:s.epistemic_status}},h('b',null,P_.text(P_.EPI_TEXT,s.epistemic_status)),' · ',s.text,s.evidence_refs.length?h('ul',{class:'news-lines'},...s.evidence_refs.map(r=>refLine(vw,r))):null))),
  h('div',{class:'pol-conds'},h('div',null,h('h5',null,'성립 조건'),h('ul',null,...x.conditions.map(c=>h('li',null,c)))),h('div',{dataset:{polCounter:''}},h('h5',null,'반대 조건'),h('ul',null,...x.counter_conditions.map(c=>h('li',null,c))))),
  h('h5',null,'확인할 것'),x.watch_items.length?h('ul',{class:'news-lines'},...x.watch_items.map(w=>watchLine(vw,w))):h('p',{class:'reason'},'없음'),
  h('details',null,h('summary',{class:'lk'},'검토 기록'),reviewLines(vw,'hypotheses',x.hypothesis_id,x.hypothesis_revision_id)));}

function detailView(vw,body,policyId,revisionId){const P_=P(),d=P_.get(vw,policyId,revisionId||null);
 const back=h('p',null,h('a',{href:href('macro'),class:'lk',dataset:{k:'pol-back'}},'← 정책 목록'));
 if(!d){body.replaceChildren(back,card('NOT_FOUND','정책 없음 · 잘못된 주소','이 파일에 '+policyId+(revisionId?' / '+revisionId:'')+'가 없습니다'));return;}
 const x=d.shown,older=x!==d.current;
 const sec=(n,title,...c)=>h('section',{class:'pol-sec',dataset:{polSection:n}},h('h4',null,n,' ',title),...c);
 const curExp=live(d.exposures),oldExp=stale(d.exposures),curHyp=live(d.hypotheses),oldHyp=stale(d.hypotheses);
 const linked=curExp.filter(e=>e.evidence_status==='DOCUMENTED'),toCheck=curExp.filter(e=>e.evidence_status!=='DOCUMENTED');
 const allRefs=[...d.revisions.flatMap(r=>[...r.evidence_refs,...r.identity_basis.relation_evidence_refs]),...d.exposures.flatMap(e=>e.evidence_refs),...d.hypotheses.flatMap(y=>y.steps.flatMap(s=>s.evidence_refs))];
 const srcs=[];const seen=new Set();for(const r of allRefs){const s=P_.source(vw,r),k=r.source_id+'|'+r.source_revision_id;if(s&&!seen.has(k)){seen.add(k);srcs.push(s);}}
 body.replaceChildren(...[back,...band(vw),
  h('h3',{class:'pol-detail-title',tabindex:'-1',dataset:{polDetail:policyId}},titleOf(vw,x)),
  ...titleLines(vw,x),
  older?h('p',{class:'hand err',dataset:{polOldRevision:x.revision_id}},'이전 개정을 보는 중 (현재 판단 아님) · 현재 개정 ',h('a',{href:href('macro','policy',policyId),class:'lk'},d.current.revision_id)):null,
  sec('①','무엇이 바뀌었나',h('p',null,...statusChips(vw,x)),
   h('p',null,'적용 범위 · ',x.scope_description),h('p',{class:'reason'},'대상 지역 · ',x.target_regions.join(', ')||'—',' · 발행 ',x.issuer,' · 관할 ',x.jurisdiction),
   h('p',{class:'reason'},'발표 ',dated(x.published),' · 시행 ',dated(x.effective_from),' · 종료 ',dated(x.effective_to),' (날짜가 상태를 바꾸지 않음)'),
   h('p',{class:'reason'},'개정 ',x.revision_id,x.supersedes_revision_id?' · 이전 개정 '+x.supersedes_revision_id+'을 대체':' · 최초 기록',' · 변경 기록 ',utc(x.change_recorded_at)),
   x.policy_type==='INDUSTRIAL_SUBSIDY'?h('p',{dataset:{polSubsidy:x.subsidy_stage}},'지원 단계 · ',h('b',null,P_.text(P_.STAGE_TEXT,x.subsidy_stage)),' (프로그램 상태와 따로 · 금액은 이 규격에 없음)'):null,
   d.parent?h('p',{class:'reason'},'상위 정책 · ',h('a',{href:href('macro','policy',d.parent),class:'lk'},vw.policies.has(d.parent)?titleOf(vw,vw.policies.get(d.parent).current):d.parent)):null,
   d.children.length?h('div',{dataset:{polChildren:String(d.children.length)}},h('p',null,'적용 단위별 별도 상태(부분 유예·면제 등)'),h('ul',{class:'news-lines'},...d.children.map(c=>{const ch=vw.policies.get(c).current;
    return h('li',null,h('a',{href:href('macro','policy',c),class:'lk'},titleOf(vw,ch)),' · ',P_.status(vw,ch).text,' · ',ch.scope_description);}))):null,
   h('details',null,h('summary',{class:'lk'},'이 개정의 근거'),refs(vw,x.evidence_refs))),
  sec('②','관련 기업',h('p',{class:'reason'},'노출 근거와 정책 적용 여부는 따로 · 지역 매출 근거가 곧 정책 적용 대상이라는 뜻이 아님'),
   !d.exposures.length?h('p',{class:'hand',dataset:{polNoExposure:''}},'연결된 기업 노출 기록 없음 · 연결 근거 미확인 (영향 없음이라는 뜻이 아님)'):null,
   d.exposures.length?h('h5',null,'근거 있는 연결 ',String(linked.length),'건'):null,linked.length?h('ul',{class:'pol-exposures',dataset:{polGroup:'LINKED'}},...linked.map(e=>exposureLine(vw,e))):null,
   toCheck.length?h('h5',null,'확인 필요 ',String(toCheck.length),'건'):null,toCheck.length?h('ul',{class:'pol-exposures',dataset:{polGroup:'CHECK'}},...toCheck.map(e=>exposureLine(vw,e))):null,
   oldExp.length?h('details',{open:true,dataset:{polGroup:'OLD'}},h('summary',{class:'lk'},'이전 개정 기준 연결 · 재검토 필요 ',String(oldExp.length),'건'),h('ul',{class:'pol-exposures'},...oldExp.map(e=>exposureLine(vw,e)))):null),
  sec('③','영향 가설',h('p',{class:'reason'},'모두 조건부 가설 · 상반된 가설은 함께 보임 · 합산·확률·예상 수익률 없음'),
   ...(curHyp.length?curHyp.map(y=>hypothesisBlock(vw,y)):[h('p',{class:'reason',dataset:{na:'NO_HYPOTHESIS'}},'현재 판단 가설 없음 · 미분석 (영향 없음이라는 뜻이 아님)')]),
   oldHyp.length?h('details',{open:true,dataset:{polGroup:'OLD_HYPOTHESES'}},h('summary',{class:'lk'},'이전 분석 · 재검토 필요 ',String(oldHyp.length),'건 (정책 개정 전 기준 · 근거를 새 개정으로 바꾸지 않음)'),...oldHyp.map(y=>hypothesisBlock(vw,y))):null),
  sec('④','원문 · 변경 이력 · 검토 기록',h('details',{open:d.older.length>0},h('summary',{class:'lk'},'변경 이력 ',String(d.revisions.length),'개 개정'),h('ol',{class:'news-lines',dataset:{polHistory:String(d.revisions.length)}},
    ...d.revisions.map(r=>h('li',{dataset:r===d.current?{polRevision:r.revision_id,polCurrent:''}:{polRevision:r.revision_id}},r===x?h('b',null,r.revision_id):h('a',{href:href('macro','policy',policyId,r.revision_id),class:'lk'},r.revision_id),
     r===d.current?' · 현재 개정':' · 이전 개정',' · 변경 기록 ',utc(r.change_recorded_at),' · ',P_.status(vw,r).text)))),
   h('details',{open:true},h('summary',{class:'lk'},'원문 문서 ',String(srcs.length),'건'),h('ul',{class:'news-lines',dataset:{polSources:String(srcs.length)}},...srcs.map(s=>h('li',{dataset:{polSource:s.source_id}},ext(s.url,s.title),' · ',P_.text(P_.KIND_TEXT,s.kind),' · ',s.publisher,
     s.document_id?' · 문서 '+s.document_id:'',' · 게시 ',dated(s.published),' · 입수 ',utc(s.revision_acquired_at),s.first_seen_at?' · 처음 발견 '+utc(s.first_seen_at)+' (게시 시각 아님)':'',' · ',P_.text(P_.VERIFY_TEXT,s.verification_status),' · 위치 ',s.evidence_locator)))),
   h('details',null,h('summary',{class:'lk'},'이 개정의 검토 기록'),reviewLines(vw,'policies',policyId,x.revision_id))),
  sec('⑤','다음 확인',h('p',null,'다음 검토 예정일 · ',x.next_review_on||'미정',' · 마지막 검토 ',utc(x.reviewed_at),' · ',P_.text(P_.REVIEW_TEXT,x.review_status)),
   h('p',{class:'reason'},'예약 실행·알림은 만들지 않음 · 하루 한 번 이하 확인 · 실시간 탐지가 아님'))].filter(Boolean));}

function macro(route,{body,params}){const signal=route.signal,want=params&&params[0]==='policy'?params[1]||null:null,rev=want&&params[2]?params[2]:null;
 const paint=res=>{if(signal.aborted)return;if(res.state!=='OK'){body.replaceChildren(stateCard(res,()=>open()));return;}
  if(want)detailView(res.view,body,want,rev);else listView(res.view,body,()=>paint(res));};
 const open=()=>{V.opened=true;body.replaceChildren(h('p',{class:'pending',role:'status',dataset:{polState:'LOADING'}},'정책·지정학 불러오는 중'));load().then(paint);};
 if(want||V.opened){open();if(want){const s=body.closest('section');if(s)requestAnimationFrame(()=>s.scrollIntoView({block:'start'}));}return;}
 body.replaceChildren(h('p',{class:'hand'},'정책·지정학 · 현재 지원: 관세 · 수출통제 · 산업 보조금 (미국 연방 정책 선별 사례)'),
  h('p',{class:'reason'},'정책 사실 · 기업 노출 근거 · 영향 가설을 나눠 보임 · 점수·순위·확률을 만들지 않음 · QGV·매크로 관문과 상관없음'),
  h('button',{type:'button',class:'btn solid',dataset:{k:'pol-open'},onclick:open},'정책·지정학 열기'));}

function companyCard(route,{after,cid}){if(!after||!after.parentNode)return;const signal=route.signal;
 const inner=h('div',{class:'card-body',dataset:{polCompanyBody:''}},h('p',{class:'reason'},'열면 불러옴'));
 const box=h('details',{class:'pol-company',dataset:{polCompanyCard:cid}},h('summary',{class:'lk'},'관련 정책 (4.5 정책·지정학)'),inner);
 let done=false;box.addEventListener('toggle',()=>{if(!box.open||done)return;done=true;inner.replaceChildren(h('p',{class:'pending'},'불러오는 중'));
  load().then(res=>{if(signal.aborted)return;if(res.state!=='OK'){done=res.state==='INVALID'||res.state==='NONE';inner.replaceChildren(stateCard(res,()=>{done=false;box.open=false;box.open=true;}));return;}
   const s=P().forCompany(res.view,cid);
   inner.replaceChildren(...(s?[h('p',{dataset:{polCompanySummary:String(s.policies.length)}},'관련 정책 ',String(s.policies.length),'건 · 노출·적용 근거 확인 ',String(s.documented),'건 · 확인 필요 ',String(s.confirm),'건',
      s.old?' · 이전 분석 · 재검토 필요 '+s.old+'건':'',' · 마지막 검토 ',utc(s.last_reviewed_at)),
     h('ul',{class:'news-lines'},...s.policies.map(p=>h('li',null,h('a',{href:href('macro','policy',p.policy_id),class:'lk'},titleOf(res.view,res.view.policies.get(p.policy_id).current)),' · ',P().text(P().TYPE_TEXT,p.type))))]
    :[h('p',{class:'reason',dataset:{polCompanySummary:'0'}},'연결된 정책 없음 · 미분석 또는 연결 근거 미확인 · 영향 없음이라는 뜻이 아님')]),
    h('p',{class:'reason'},'정책 점수·수혜 순위는 만들지 않음'),h('p',{class:'reason',dataset:{polKind:res.view.data_kind}},P().text(P().KIND_DATA_TEXT,res.view.data_kind),res.view.historical?' · 역사 사례 · 현재 상태 미확인':''));});});
 after.parentNode.insertBefore(box,after.nextSibling);}

function news(route,{body,links}){const signal=route.signal;
 const go=()=>{body.replaceChildren(h('p',{class:'pending'},'불러오는 중'));load().then(res=>{if(signal.aborted)return;if(res.state!=='OK'){body.replaceChildren(stateCard(res,go));return;}
  // 5.2 -> 4.5 comes only from reviewed navigation links (Codex navigation/1): the exact article link, a discovery reference,
  // never policy evidence, never a title match. A NEWS_REFERENCE source inside the policy file stays a reference in the detail only.
  const vw=res.view,ns=vw.navState,map=vw.nav.news,now=links(),hits=[...map].filter(([u])=>now.has(u));
  const none=ns.state==='INVALID'?h('p',{class:'hand err',dataset:{polNewsState:'NAV_INVALID'}},'연결 파일 규격 불일치 · 사용하지 않음 · ',ns.code,' · ',ns.path)
   :ns.state!=='OK'?h('p',{class:'reason',dataset:{polNewsState:'NO_LINK_FILE'}},'연결 자료 없음 · 정책–기사 연결 파일 미게시 (연결 기능 자체는 합성 시험으로 확인됨 · 영향 없음이라는 뜻이 아님)')
   :!vw.nav.count?h('p',{class:'reason',dataset:{polNewsState:'NO_LINK_DATA'}},'연결 자료 없음 · 검토된 정책–기사 연결 0건 (연결 기능 자체는 합성 시험으로 확인됨 · 영향 없음이라는 뜻이 아님)')
   :h('p',{class:'reason',dataset:{polNewsState:'NO_OVERLAP'}},'지금 목록의 뉴스와 겹치는 연결 없음 · 검토된 연결 ',String(vw.nav.count),'건은 다른 기사');
  body.replaceChildren(h('p',{class:'reason',dataset:{polNewsHits:String(hits.length)}},'지금 목록의 뉴스와 연결된 정책 ',String(hits.length),'건 · 검토된 정책–기사 연결 ',String(vw.nav.count),'건'),
   hits.length?h('ul',{class:'news-lines'},...hits.flatMap(([u,ls])=>ls.map(l=>{const p=vw.policies.get(l.policy_id);return h('li',{dataset:{polNewsLink:l.policy_id}},h('a',{href:href('macro','policy',l.policy_id),class:'lk'},titleOf(vw,p.current)),' · 관련 기사 ',ext(u,'원문'),' (탐색 참조 · 정책 검증 근거 아님 · 시행·기업 적용 미평가 · 연결 검토 ',utc(l.reviewed_at),')');})))
    :none,h('p',null,h('a',{href:href('macro'),class:'lk'},'→ 4.5 정책·지정학')));});};
 body.replaceChildren(h('p',{class:'hand'},'관련 정책 (4.5) · 누르면 정책 파일을 읽어 지금 목록의 뉴스와 이음'),h('button',{type:'button',class:'btn',dataset:{k:'pol-news'},onclick:go},'관련 정책 연결 보기'));}

I.policyImpactLive=Object.freeze({macro,companyCard,news,load});
})();
