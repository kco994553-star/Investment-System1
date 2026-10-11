/* S17 daily reports (모의투자 일일보고서 / 투자 일일보고서): report model, template v1 export, amount hiding and AI answers.
   Everything stays on this device. Nothing here sends a report anywhere: export is a user copy, the optional mailbox writes
   only to the user's own Google Sheet tabs (ReportInbox/ReportOutbox) through the existing drive.file session.
   Amount hiding is ONE function (money/quantity) used by both the screen and the export. Default: hidden. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?require('./virtual-trading.js'):root.VirtualTrading,node?require('./report-benchmarks.js'):root.ReportBenchmarks);if(node)module.exports=api;else root.DailyReport=api;})(typeof globalThis==='object'?globalThis:this,function(VT,RB){
'use strict';
const TEMPLATE_VERSION='템플릿 v1',GUIDE_VERSION='지침 v1',HIDE_KEY='investment.web.v1.report-amounts-hidden',AI_KEY='investment.web.v1.report-ai-answers',MAX_ANSWERS=30;
const KINDS=Object.freeze({MOCK:{ko:'모의투자 일일보고서',en:'Paper trading daily report'},REAL:{ko:'투자 일일보고서',en:'Investment daily report'}});
const TABS=Object.freeze({SET_A:'세트 A',SET_B:'세트 B',COMPARE:'A/B 비교',REAL:'내 실제 포트폴리오'});
// Level order, symbols, names, chips and reason-code labels: VirtualTrading (D-19 vocabulary, one source).
const LEVELS=VT.LEVELS;
const CHECK_LINES=['✔ 템플릿에 없는 숫자를 만들지 않음','✔ 외부 정보마다 날짜·출처 표시(또는 확인 불가)','✔ 실제 계좌 매수·매도 권유 없음','✔ 절 순서와 표 구조 유지'];
const GUIDE_A=['[Investment-System1 · AI 해석 지침 v1 · 템플릿 v1]','','역할','너는 Investment-System1의 해석 보조자다. 투자 자문가나 매매 결정자가 아니다.','사용자가 붙여넣는 [일일보고서 템플릿]의 숫자와 규칙 판단을 읽고, 【AI】로 표시된 칸만 채워 보고서를 완성한다.','','템플릿 규칙','1. 제목, 절 순서(요약, ①~⑬, 최종 투자판단, 각주), 표 구조, 숫자는 바꾸지 않는다. 템플릿 전체를 그대로 돌려주되 【AI】 칸만 채운다.','2. 【규칙】 문장은 지우지 않는다. 다르게 보면 그 아래에 "[의견]"으로 시작하는 줄을 덧붙인다.','3. [숨김] 금액은 추정하지 않는다. 규모는 비중·%·한도 대비 %로만 말한다.','','숫자 규칙','4. 템플릿에 없는 숫자(가격, 목표가, 확률, 점수, 수익률)를 만들지 않는다.','5. 계산이 필요하면 식을 보이고 결과에 ≈를 붙인다.','6. NOT_AVAILABLE·N/A는 "확인 불가"로 쓰고 채우지 않는다.','7. 점수는 STANDARD v1 · UNCALIBRATED(보정 전)다. 검증된 모델처럼 말하지 않는다.','','판단 어휘','8. 실제 포트폴리오에 대해 매수·매도 권유를 쓰지 않는다. 판단은 다음 7개만 쓴다:','   '+VT.priorityText('ko-KR',' / '),'9. 가상 장부(세트 A·B, 그림자 장부)의 매수·매도는 이미 규칙이 정한 가상 기록이다. 바꾸지 말고 이유만 해설한다.','','외부 정보','10. ⑧ 뉴스는 웹 검색이 가능할 때만 쓴다. 각 항목에 발표일과 출처 링크를 붙이고, 신규/반복, 구조적/일시적, 관련 종목, 영향받는 QGV 요소(예: Q-경쟁우위, G-매출성장, V-역DCF)를 표시한다. 검색할 수 없으면 "외부 정보 확인 불가"라고 쓴다.','11. 뉴스(신호)와 확정 실적·공시(증거)를 구분한다. 뉴스로 점수를 고치지 않는다.','','시나리오','12. ⑨ 시나리오는 부정·중립·긍정 각각 전제 조건, 확인 신호, 무효화 조건만 쓴다. 확률과 목표가는 쓰지 않는다.','','어조','13. 한국어, 중립적, 짧게. "반드시", "확실히", "지금 사야", "놓치면" 같은 단정·권유 표현 금지.','14. 영어 용어는 처음 한 번만 English(한국어)로 병기한다.','','마지막에 아래 점검을 한 줄씩 붙인다.',...CHECK_LINES].join('\n');
const HEADER_B='아래 일일보고서 템플릿의 【AI】 칸을 지침대로 채워 전체를 돌려줘. 웹 검색으로 ⑧ 뉴스를 확인해.';
const KIND_LINE={MOCK:'대상은 모의 포트폴리오(세트 A·B)다. 실제 자금이 아니다.',REAL:'대상은 사용자의 실제 포트폴리오다. 실제 계좌에 대한 지시는 쓰지 말고, 그림자 장부는 "규칙대로 했다면"의 가상 기록으로만 해설한다.'};
const NA='N/A';
const num=v=>typeof v==='number'&&Number.isFinite(v);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function group3(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,',');}
// KRW amount, readable: 1억 830만원 / 65만원 / 9,500원. Negative values keep the sign.
function formatKrw(v){
 if(!num(v))return NA;const sign=v<0?'−':'',a=Math.round(Math.abs(v));
 if(a>=100000000){const eok=Math.floor(a/100000000),man=Math.round((a%100000000)/10000);return sign+group3(eok)+'억'+(man?' '+group3(man)+'만':'')+'원';}
 if(a>=10000)return sign+group3(Math.round(a/10000))+'만원';
 return sign+group3(a)+'원';
}
/* The single amount-hiding function (D-18). mode 'screen' → ●●●만원, mode 'export' → [숨김] or "한도 대비 n%" when a limit is
   given (virtual trade amounts), so the AI still sees the scale. Hidden output never contains the amount or its digits. */
function money(v,{hidden=true,mode='screen',limit=null}={}){
 if(!num(v))return NA;
 if(!hidden)return formatKrw(v);
 if(mode==='export')return num(limit)&&limit>0?'한도 대비 '+Math.round(v/limit*100)+'%':'[숨김]';
 return '●●●만원';
}
// Quantities and average prices are hidden with the amounts (they reveal amounts).
function quantity(v,{hidden=true,mode='screen'}={}){if(!num(v))return NA;if(hidden)return mode==='export'?'[숨김]':'●●●';return group3(Math.round(v*10000)/10000);}
function pct(v,d=2){return num(v)?(v>0?'+':v<0?'−':'')+Math.abs(v*100).toFixed(d)+'%':NA;}
function pp(v,d=1){return num(v)?(v>0?'+':v<0?'−':'')+Math.abs(v).toFixed(d)+'%p':NA;}
function weight(v){return num(v)?v.toFixed(1)+'%':NA;}
function score(v){return num(v)?v.toFixed(1):NA;}
function hiddenSetting(storage,value){
 try{if(value!==undefined){storage.setItem(HIDE_KEY,value?'1':'0');return value;}return storage.getItem(HIDE_KEY)!=='0';}catch(_){return true;}
}
/* Report model from device inputs (all RAM): engine ledger result, ACTUAL weights (no amounts), public Q·G rows. */
function buildModel({kind='MOCK',tab='SET_A',reportDate,baseDates={},ledger=null,ram=null,qg={},targets={},names={},config=null,investStart=null,runner=null,hits=null,mode=null,signals=null,rehearsal=null,bench=null,track=null}={}){
 const cfg=config||{};
 const started=!!(ledger&&ledger.state==='OK'),last=started?ledger.days[ledger.days.length-1]:null;
 const holdings=[];
 if(started){
  for(const[cid,j]of Object.entries(last.judgements))holdings.push({company:cid,name:names[cid]||cid,actual_weight:j.actual_weight,target_weight:j.target_weight,main:j.main,aux:j.aux_levels,judgement:{main:j.main,aux_levels:j.aux_levels,aux:j.aux,reason_codes:j.reason_codes},reasons:VT.reasonCodes(j),q:qg[cid]?.q??null,g:qg[cid]?.g??null,basis:signals&&signals.basis&&signals.basis[cid]||null});
 }else if(kind==='REAL'&&ram&&Array.isArray(ram.rows)){
  for(const r of ram.rows){const cid=r.company_id||r.ticker;holdings.push({company:cid,name:names[cid]||r.ticker,actual_weight:num(r.weight)?r.weight*100:null,target_weight:num(targets[cid])?targets[cid]:null,main:null,aux:[],judgement:null,reasons:[],q:qg[cid]?.q??null,g:qg[cid]?.g??null});}
 }
 holdings.sort(VT.compareRows);
 const executed=started?last.executed:[],orders=started?last.orders:[],cancelled=started?last.cancelled:[];
 const sum=(list,side)=>list.filter(t=>t.side===side).reduce((a,t)=>a+t.amount,0);
 return {kind,tab,report_date:reportDate||null,base_dates:baseDates,started,ledger_state:ledger?ledger.state:'NOT_AVAILABLE',ledger_reasons:ledger?ledger.reason_codes:['LEDGER_NOT_AVAILABLE'],
  start_date:cfg.start_date??null,invest_start:investStart,buy_limit:cfg.buy_limit??null,sell_limit:cfg.sell_limit??null,
  summary:started?ledger.summary:null,last,days:started?ledger.days.slice(-5):[],holdings,executed,orders,cancelled,runner,hits:Array.isArray(hits)?hits:[],
  buy_total:started?sum(executed,'BUY'):null,sell_total:started?sum(executed,'SELL'):null,ram_state:ram?ram.state:'NOT_AVAILABLE',
  mode:mode==='REHEARSAL'?'REHEARSAL':'RECORDING',signals:signals||null,rehearsal:mode==='REHEARSAL'&&rehearsal?rehearsal:null,
  bench:bench||null,track:track||null};
}
/* ⑪⑫⑬ text helpers (ReportBenchmarks model; index levels and returns are percentages, never amounts). */
function benchCode(c,locale='ko-KR'){if(c===null||c===undefined)return NA;const l=(RB&&RB.codeLabel(c,locale))||VT.codeLabel(c,locale);return l?l+' ('+c+')':String(c);}
const periodName=(p,locale='ko-KR')=>RB?RB.label(RB.PERIOD_LABELS,p,locale):p;
const seriesName=(k,locale='ko-KR')=>RB?RB.label(RB.SERIES_LABELS,k,locale):k;
const basisName=(b,locale='ko-KR')=>RB?RB.label(RB.BASIS_LABELS,b,locale):b;
const verdictName=(v,locale='ko-KR')=>v&&RB?RB.label(RB.VERDICT_LABELS,v,locale):NA;
function retText(x){return x&&num(x.return)?pct(x.return):NA+(x&&x.reason?'('+x.reason+')':'');}
function excessText(x){return num(x)?pp(x*100,2):NA;}
function minSamples(t){return t&&num(t.min_samples)?t.min_samples:30;}
function hitText(w,t,locale='ko-KR'){
 if(w.state==='OK')return (w.hit_rate*100).toFixed(1)+'% ('+w.hits+'/'+w.samples+')';
 if(w.state==='INSUFFICIENT_SAMPLE')return '표본 부족(n<'+minSamples(t)+')';
 return NA+' · '+benchCode(w.reason,locale)+(w.expected_first?' · 첫 평가 예상 '+(w.expected_estimated?'≈ ':'')+w.expected_first:'');
}
function seriesState(x,locale='ko-KR'){return x.state==='OK'?(x.gaps?'결측 '+x.gaps+'세션(보간 없음)':'정상'):benchCode(x.reason,locale);}
/* Recording vs rehearsal (리허설 · 기록 없음): a rehearsal runs the rules on today's data in RAM and is never recorded. */
const MODE_LABEL={REHEARSAL:{ko:'리허설 · 기록 없음',en:'Rehearsal · not recorded'},RECORDING:{ko:'기록 모드',en:'Recording mode'}};
const BASIS_KO={ABNORMAL:'이상 하락',NORMAL:'정상'},vSlopeText=v=>v==='READY'?'V 기울기 사용':VT.codeLabel(v)||v;
// D-5 basis label for one company: benchmark actually used (S&P 500 fallback named), state or NA reason, V slope use.
function basisText(b){
 if(!b)return NA;const bench=b.benchmark==='SP500'?'S&P 500':b.benchmark;
 return bench+(b.fallback?' ('+b.requested+' 없음 → 대체)':'')+' · '+(b.state==='NOT_AVAILABLE'?'기준 N/A('+b.reason+(b.reason==='HISTORY_INSUFFICIENT'?' '+b.aligned+'/'+b.needed:'')+(VT.codeLabel(b.reason)?' · '+VT.codeLabel(b.reason):'')+')':BASIS_KO[b.state]||b.state)+' · '+vSlopeText(b.v_slope);
}
function vProgressText(p){
 if(!p)return null;if(p.state==='READY')return 'V 기록 '+p.needed+'일 이상 · V 기울기 계산 가능';
 return 'V 기록 '+Math.min(p.elapsed,p.needed)+'/'+p.needed+'일'+(p.state==='NOT_RECORDED'?' · 아직 기록 없음':' · 첫 기록 '+p.first);
}
function rehearsalLine(m){const r=m.rehearsal||{},n=Array.isArray(r.qg_filled)?r.qg_filled.length:0;
 return '리허설 · 기록 없음: 오늘 데이터로 규칙만 돌려 본 결과이며 어떤 장부·시트에도 기록하지 않음 · '+(r.start_date||NA)+'부터 최근 '+(r.window||NA)+'거래일 · 현금 0에서 매일 가상 입금'+(n?' · 기록된 Q·G가 없는 '+n+'거래일은 오늘 공개 화면 Q·G 사용':'');}
// A row's judgement: the engine object, or {main, aux} for rows built by hand (main null → no judgement).
const judgementOf=h=>h.judgement||(h.main?{main:h.main,aux_levels:Array.isArray(h.aux)?h.aux:[],aux:[],reason_codes:[]}:null);
function counts(holdings){const c={};for(const h of holdings)if(h.main)c[h.main]=(c[h.main]||0)+1;return c;}
function countsLine(holdings){const c=counts(holdings),parts=LEVELS.filter(l=>c[l]).map(l=>VT.label(l)+' '+c[l]);return parts.length?parts.join(' · ')+' (주 판단만 집계)':NA;}
function notStarted(m){
 if(m.mode==='REHEARSAL')return '리허설 · 기록 없음 · 계산 전('+VT.codesText(m.ledger_reasons)+')';
 if(!m.start_date)return '가상매매 시작일 미정 · 가상 장부 기록 없음('+VT.codesText(m.ledger_reasons)+')';
 if(m.report_date&&m.report_date<m.start_date)return '가상매매 시작일 '+m.start_date+' 전 · 기록 없음';
 return '가상매매 시작일 '+m.start_date+' · 가상 장부 계산 전('+VT.codesText(m.ledger_reasons)+')';
}
function ruleSummary(m){
 if(!m.started)return notStarted(m)+'.';
 const b=m.executed.filter(t=>t.side==='BUY').map(t=>t.company),s=m.executed.filter(t=>t.side==='SELL').map(t=>t.company);
 return '가상 매수 '+(b.join('·')||'없음')+', 가상 매도 '+(s.join('·')||'없음')+'. '+countsLine(m.holdings);
}
// ⑫ rule sentence: the latest period with both returns, else NA.
function benchRule(B){
 if(!B)return NA;const r=[...B.periods].reverse().find(x=>x.state==='OK'&&num(x.excess));
 return r?periodName(r.period)+' 대상 '+retText(r.target)+', S&P 500 '+retText(r.sp500)+' → '+excessText(r.excess)+' '+verdictName(r.verdict):NA+'('+(B.reason||'NO_COMPARABLE_PERIOD')+')';
}
/* Template v1 (REPORT_TEMPLATE_V1 §3) as markdown. Same input + same settings → same text. */
function renderTemplate(m,{hidden=true,guide=true}={}){
 const H={hidden,mode:'export'},L=[],kindName=KINDS[m.kind].ko,target=TABS[m.tab]||m.tab;
 const base=Object.entries(m.base_dates||{}).map(([k,v])=>k+' '+v).join(' / ')||NA;
 if(guide)L.push(GUIDE_A,'');else L.push(HEADER_B,'');
 L.push(KIND_LINE[m.kind],'','[일일보고서 템플릿]');
 L.push('# '+target+' '+kindName,TEMPLATE_VERSION+' · '+GUIDE_VERSION+' · 보고일 '+(m.report_date||NA)+' · 기준 완료 거래일 '+base,
  '포트폴리오 v1.1 · QGV 점수 기준 v1(UNCALIBRATED) · 유형 v1 잠정 · 가상매매 규칙 v1(PROVISIONAL)','금액 표시: '+(hidden?'숨김':'표시'),'');
 if(m.mode==='REHEARSAL')L.push(rehearsalLine(m),'');
 const s=m.summary;
 L.push('## 요약','| 평가액 | 마지막 거래일 | 가상 매수 | 가상 매도 |','|---|---|---|---|',
  '| '+(s?money(s.total_value,H)+' ('+pct(s.simple_return)+')':NA)+' | '+NA+' | '+(m.buy_total===null?NA:money(m.buy_total,{...H,limit:m.buy_limit}))+' | '+(m.sell_total===null?NA:money(m.sell_total,{...H,limit:m.sell_limit}))+' |',
  '한 줄 요약: 【AI】 (없으면 【규칙】 '+ruleSummary(m)+')','');
 L.push('## ① 전체 투자장부','| 거래일 | 평가액 | 1D | 누적 |','|---|---|---|---|');
 if(m.days.length){let prev=null;for(const d of m.days){const one=prev&&num(prev.total_value)&&num(d.total_value)&&prev.total_value>0?(d.total_value-d.deposit)/prev.total_value-1:null;L.push('| '+d.date+' | '+money(d.total_value,H)+' | '+pct(one)+' | '+NA+' |');prev=d;}}
 else L.push('| '+NA+' | '+NA+' | '+NA+' | '+NA+' |');
 L.push('원금 '+(s?money(s.initial_value,H):NA)+' · 추가입금 '+(s?money(s.deposits,H):NA)+' · 출금 '+NA+' · 신뢰도 '+(m.started?'중간':NA),'');
 L.push('## ② 포트폴리오 구성','| 업종군(SIC) | 목표 | 실제 | 차이 |','|---|---|---|---|','| '+NA+' (SIC v0 연결 전) | '+NA+' | '+NA+' | '+NA+' |','집중도: 【규칙】 '+NA,'');
 L.push('## ③ 전 종목 장부','판단: '+VT.DISCLAIMER.ko+' · 우선순위 '+VT.priorityText('ko-KR')+' · 주 판단 1개 + 보조 칩','| 기업(티커) | 실제/목표 | 1D | 누적 | QGV(Q·G) | 판단 | 사유 코드 |','|---|---|---|---|---|---|---|');
 if(m.holdings.length)for(const h of m.holdings)L.push('| '+h.name+' | '+weight(h.actual_weight)+' / '+weight(h.target_weight)+' | '+NA+' | '+NA+' | '+(num(h.q)&&num(h.g)?score((h.q+h.g)/2):NA)+' | '+(judgementOf(h)?VT.judgementText(judgementOf(h),'ko-KR'):NA)+' | '+(h.reasons.join(', ')||NA)+' |');
 else L.push('| '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' |');
 const based=m.holdings.filter(h=>h.basis);if(based.length)L.push('업종 기준(D-5): '+based.map(h=>h.name+' '+basisText(h.basis)).join(' / '));
 L.push('판단 집계: '+countsLine(m.holdings),'당일 변동요인: 【AI】 (없으면 비움)','');
 L.push('## ④ 성과기여','| 종목 | 기여 %p |','|---|---|','| '+NA+' | '+NA+' |','성과의 주요 원인: 【AI】','');
 L.push('## ⑤ QGV','| 기업 | Q | G | V | 총점(유형 가중) | 유형 |','|---|---|---|---|---|---|');
 const withQg=m.holdings.filter(h=>num(h.q)||num(h.g));
 if(withQg.length)for(const h of withQg)L.push('| '+h.name+' | '+score(h.q)+' | '+score(h.g)+' | '+NA+' | '+NA+' (V 없음 → Q·G 점수 '+(num(h.q)&&num(h.g)?score((h.q+h.g)/2):NA)+') | '+NA+' |');
 else L.push('| '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' |');
 L.push('가격 변화와 Q·G 변화 구분: 【AI】','');
 L.push('## ⑥ 기술적 분석 (표시 전용, GSQ-015)','| 지표 | 값 | 판정 |','|---|---|---|','| '+NA+' | '+NA+' | '+NA+' |','기술적 결론: 【AI】 (없으면 【규칙】 '+NA+')','');
 L.push('## ⑦ 거시환경','| 축 | 최신값 | 방향 | 상태 |','|---|---|---|---|','| '+NA+' | '+NA+' | '+NA+' | '+NA+' |','국면 판정 NOT_AVAILABLE · 매핑 채택 전','Macro 판정: 【AI】','');
 L.push('## ⑧ 뉴스·경쟁기업·산업 영향','| 사건 | 발표일 | 출처 | 관련 기업 | 방향 | 구조적/일시적 | 신규/반복 | 영향 QGV 요소 |','|---|---|---|---|---|---|---|---|','【AI】 (검색 불가 시 "외부 정보 확인 불가")','');
 L.push('## ⑨ Portfolio Driver','| 순위 | Driver | 노출 | 오늘 기여 |','|---|---|---|---|','| '+NA+' | '+NA+' | '+NA+' | '+NA+' |','상승·하락 시나리오: 【AI】 (부정/중립/긍정, 전제·확인 신호·무효화, 확률·목표가 없음)','');
 const ledgerName=(m.mode==='REHEARSAL'?'리허설 · 기록 없음 · ':'')+(m.kind==='REAL'?'그림자 장부':TABS[m.tab]+' 가상 장부');
 L.push('## ⑩ 행동요령 · 가상 매매장부 ('+VT.DISCLAIMER.ko+')',ledgerName+(m.started?'':' · 시작 전'),'| 구분 | 기업 | 금액 | 규칙 사유 |','|---|---|---|---|');
 if(m.executed.length)for(const t of m.executed)L.push('| 가상 '+(t.side==='BUY'?'매수':'매도')+' | '+t.company+' | '+money(t.amount,{...H,limit:t.side==='BUY'?m.buy_limit:m.sell_limit})+' | '+t.reason_codes.join(', ')+' |');
 else L.push('| '+NA+' | '+NA+' | '+NA+' | '+(m.started?'거래 없음':m.ledger_reasons.join(', '))+' |');
 for(const o of m.cancelled)L.push('| 가상 주문 취소 | '+o.company+' | '+money(o.amount,{...H,limit:o.side==='BUY'?m.buy_limit:m.sell_limit})+' | '+o.cancel_reason+' |');
 if(s)L.push('가상 현금 '+money(s.cash,H)+' · 총 가상자산 '+money(s.total_value,H)+' · 누적 입금 '+money(s.deposits,H)+' · 실현손익 '+money(s.realized_pnl,H)+' · 미실현손익 '+money(s.unrealized_pnl,H));
 L.push('가상매매 해설: 【AI】 · [의견]은 별도 줄','');
 L.push('## ⑪ 누적 검증·성과','| 평가 창 | 표본 | 적중률 | 벤치마크 |','|---|---|---|---|');
 const T=m.track;
 if(T&&T.windows.length)for(const w of T.windows)L.push('| D+'+w.window+' | '+(w.samples===null?NA:w.samples)+' | '+hitText(w,T)+' | S&P 500 |');
 else{const hits=m.hits||[];if(hits.length)for(const h of hits)L.push('| D+'+h.window+' | '+h.samples+' | '+(h.hit_rate===null?'표본 부족(n<30)':(h.hit_rate*100).toFixed(1)+'%')+' | S&P 500 |');else L.push('| '+NA+' | '+NA+' | '+NA+' | S&P 500 |');}
 L.push('적중: 체결일 종가 대비 D+N 세션 종가 수익률을 S&P 500(SPY, 현지 통화)과 비교 · 가상 매수는 상회, 가상 매도는 하회면 적중 · 표본 '+minSamples(T)+'건 미만은 적중률 비표시 (D-11·D-12)');
 if(T&&T.recent.length){L.push('| 최근 판정 | 수익률 | 벤치마크 | 평가 |','|---|---|---|---|');for(const r of T.recent)L.push('| '+r.date+' '+r.company+' 가상 '+(r.side==='BUY'?'매수':'매도')+' D+'+r.window+' | '+pct(r.stock_return)+' | '+pct(r.benchmark_return)+' | '+(r.hit?'적중':'미적중')+' |');}
 L.push('누적 가상 실현손익 '+(s?money(s.realized_pnl,H):NA)+' · 누적 가상 TWR '+(s?pct(s.twr):NA),'');
 const B=m.bench;
 L.push('## ⑫ 기간별 성과','| 기간 | 대상 | S&P 500 | 초과 | 판정 |','|---|---|---|---|---|');
 if(B&&B.periods.length)for(const r of B.periods)L.push('| '+periodName(r.period)+(r.base?' (기준 '+r.base+' 종가)':'')+' | '+(r.state==='OK'?retText(r.target):NA+'('+r.reason+')')+' | '+(r.state==='OK'?retText(r.sp500):NA)+' | '+excessText(r.excess)+' | '+verdictName(r.verdict)+' |');
 else L.push('| '+NA+' | '+NA+' | '+NA+' | '+NA+' | '+NA+' |');
 if(B)L.push(basisName(B.basis)+' · 기준 완료 거래일 '+(B.as_of||NA)+' · 기간 시작 직전 종가 = 100 · 결측 보간 없음');
 L.push('해석: 【AI】 (없으면 【규칙】 '+benchRule(B)+')','');
 const D=B&&B.dashboard;
 L.push('## ⑬ 성과·위험','| 시리즈 | '+(D?periodName(D.period):NA)+' 수익률 |','|---|---|');
 if(D&&D.state==='OK')for(const x of D.series)L.push('| '+seriesName(x.key)+' | '+retText(x)+(x.state==='OK'&&x.gaps?' · 결측 '+x.gaps+'세션':'')+' |');
 else L.push('| '+NA+' | '+(D?NA+'('+D.reason+')':NA)+' |');
 if(D&&D.state==='OK')L.push('기준 '+D.base+' 종가 = 100 · '+(D.sessions[0]||NA)+'~'+(D.sessions[D.sessions.length-1]||NA)+' · '+(B?basisName(B.basis):NA));
 L.push('| 위험지표 | 값 | 상태 |','|---|---|---|','| '+NA+' | '+NA+' | '+NA+' |','');
 L.push('## 최종 투자판단','| 영역 | 판단 | 출처 |','|---|---|---|','| 가상매매 | '+ruleSummary(m)+' | 규칙 v1 |','최종 행동(7단계 어휘): 【AI】 (없으면 【규칙】 '+countsLine(m.holdings)+')','');
 L.push('## 각주',target+' · 포트폴리오 v1.1 · QGV 점수 기준 v1(보정 전) · 유형 v1 잠정 · 평가액 '+(s?money(s.total_value,H):NA)+' · 기준 종가일 '+base+' · 가상매매 실제 평가액 미반영 · 추산값 ≈ · 결측 N/A',
  '보고일: '+(m.report_date||NA),'투자 시작일: '+(m.invest_start||NA),'가상매매 시작일: '+(m.start_date||'미정'),'');
 const used=[...new Set(m.holdings.flatMap(h=>h.reasons).concat(m.executed.flatMap(t=>t.reason_codes),m.cancelled.map(o=>o.cancel_reason),m.started?[]:m.ledger_reasons))].sort();
 L.push('## 사유 코드 사전 (그날 쓰인 코드만)',...(used.length?used.map(c=>'- '+c+': '+(VT.codeLabel(c,'ko-KR')||'라벨 없음 · 코드 그대로')):['- 없음']));
 return L.join('\n')+'\n';
}
// Numbers in the AI answer that the template does not contain (warning only; the answer is stored as-is).
function numbersIn(text){return (String(text).match(/\d[\d,]*(?:\.\d+)?/g)||[]).map(x=>x.replace(/,/g,'').replace(/\.0+$/,''));}
function checkAnswer(answer,template){
 const known=new Set(numbersIn(template)),foreign=[...new Set(numbersIn(answer).filter(n=>!known.has(n)))];
 const missing=CHECK_LINES.filter(l=>!String(answer).includes(l.slice(2)));
 const dateLine=/보고일 (\d{4}-\d{2}-\d{2})/.exec(template),versionOk=String(answer).includes(TEMPLATE_VERSION)&&String(answer).includes(GUIDE_VERSION);
 return {foreign_numbers:foreign,format_ok:missing.length===0&&versionOk,missing_checks:missing,version_ok:versionOk,date_ok:!dateLine||String(answer).includes(dateLine[1])};
}
async function hash(text,cryptoImpl){
 const c=cryptoImpl||(typeof crypto!=='undefined'?crypto:null);if(!c||!c.subtle)throw new Error('HASH_UNAVAILABLE');
 const digest=await c.subtle.digest('SHA-256',new TextEncoder().encode(text));return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
// AI answers live only in this browser's storage, keyed by the template hash (newest MAX_ANSWERS kept).
function answers(storage){try{const v=JSON.parse(storage.getItem(AI_KEY)||'{}');return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}catch(_){return {};}}
function saveAnswer(storage,key,entry){
 const all=answers(storage);all[key]={answer:String(entry.answer).slice(0,200000),saved_at:entry.saved_at,source:entry.source,model:entry.model||null,report_date:entry.report_date||null};
 const keep=Object.entries(all).sort((a,b)=>String(b[1].saved_at).localeCompare(String(a[1].saved_at))).slice(0,MAX_ANSWERS);
 try{storage.setItem(AI_KEY,JSON.stringify(Object.fromEntries(keep)));return true;}catch(_){return false;}
}
/* Mailbox (template §8, GSQ-019 pending): the user's own sheet, tabs ReportInbox / ReportOutbox. Default OFF.
   Inbox row: created_at | report_date | kind | template_version | sha256 | data_sha256 | status(NEW) | template.
     sha256      = SHA-256 of the exact template text written in this row (what the AI reads and must echo back).
     data_sha256 = SHA-256 of the canonical data template (amounts hidden, no guide); the device's answer-storage key.
   Outbox row: sha256 | model | created_at | answer. A result is accepted only when its sha256 equals the Inbox sha256
   of the template this device would write for the same data. */
const INBOX='ReportInbox',OUTBOX='ReportOutbox',INBOX_HEAD=['created_at','report_date','kind','template_version','sha256','data_sha256','status','template'],OUTBOX_HEAD=['sha256','model','created_at','answer'];
async function ensureTabs(session,id){
 const titles=await session.sheetTitles(id),missing=[INBOX,OUTBOX].filter(t=>!titles.includes(t));
 if(missing.length){await session.addTabs(id,missing);for(const t of missing)await session.appendRows(id,"'"+t+"'!A1",[t===INBOX?INBOX_HEAD:OUTBOX_HEAD]);}
 return missing;
}
async function postInbox(session,id,{report_date,kind,template,data_sha256,now},cryptoImpl){
 const sha256=await hash(template,cryptoImpl);
 await ensureTabs(session,id);
 await session.appendRows(id,"'"+INBOX+"'!A1",[[now,report_date||'',kind,TEMPLATE_VERSION,sha256,data_sha256||'','NEW',template]]);
 return sha256;
}
async function readOutbox(session,id,sha256){
 const payload=await session.fetchValues(id,"'"+OUTBOX+"'!A1:D500",{maxBytes:1048576});const rows=Array.isArray(payload.values)?payload.values:[];
 let found=null;for(const r of rows.slice(1))if(Array.isArray(r)&&r[0]===sha256&&typeof r[3]==='string'&&r[3])found={model:typeof r[1]==='string'?r[1]:null,created_at:typeof r[2]==='string'?r[2]:null,answer:r[3]};
 return found;
}
/* ---------- S17 screen ---------- */
// Runner input status: symbols, states and reason codes only (prices, FX and ledgers never reach this card).
const RUNNER_KO={LOADING:'가상 장부 입력 불러오는 중',READY:'가상 장부 입력 준비됨',NOT_STARTED:'시작일 전 · 가격 요청 없음',NOT_AVAILABLE:'가상 장부 입력 NOT_AVAILABLE'};
function inputsCard(r){
 if(!r)return '';
 const rows=Array.isArray(r.sources)?r.sources:[],bad=rows.filter(x=>x.state!=='OK');
 let h='<section class="card" data-report-inputs data-runner-state="'+esc(r.state)+'"><h2>가상 장부 입력 <span class="badge">기기 RAM 전용</span></h2>';
 h+='<p data-runner-summary>'+esc((RUNNER_KO[r.state]||r.state)+(r.reason_codes&&r.reason_codes.length?' · '+VT.codesText(r.reason_codes):''))+'</p>';
 if(r.state==='LOADING')h+='<p class="small" data-runner-progress>'+esc(r.progress||'')+'</p>';
 if(rows.length)h+='<p class="small">'+esc('시세 '+(rows.length-bad.length)+'/'+rows.length+' 사용 가능')+'</p>';
 if(bad.length)h+='<ul class="small" data-runner-sources>'+bad.map(x=>'<li data-source-symbol="'+esc(x.symbol)+'" data-source-code="'+esc(x.code||'')+'">'+esc(x.symbol+' · '+x.state+(x.code&&x.code!==x.state?' · '+VT.codeText(x.code):''))+'</li>').join('')+'</ul>';
 h+='<p class="small">가격·환율은 구글 로그인 상태에서 비공개 가격 Worker로 이 기기 메모리에만 불러옵니다. 저장·전송하지 않습니다. 없는 값은 채우지 않고 N/A·사유 코드로 둡니다.</p></section>';
 return h;
}
/* ⑪ Track Record card: per window samples, hit rate only from the minimum, NA reason and expected first date. */
function trackCard(m,{hidden=true,locale='ko-KR'}={}){
 const T=m.track,s=m.summary,H={hidden,mode:'screen'};
 let h='<section class="card" data-report-section="11"><h2>⑪ 누적 검증·성과 <span class="badge">D+5 · D+20 · D+63</span></h2>';
 if(T){h+='<div class="table-scroll"><table data-track-windows><thead><tr><th>평가 창</th><th>표본</th><th>적중률</th><th>벤치마크</th></tr></thead><tbody>'
  +T.windows.map(w=>'<tr data-track-window="'+w.window+'" data-track-state="'+esc(w.state)+'"><td>D+'+w.window+'</td><td>'+esc(w.samples===null?NA:String(w.samples))+'</td><td>'+esc(hitText(w,T,locale))+'</td><td>S&amp;P 500</td></tr>').join('')+'</tbody></table></div>';
  if(T.recent.length)h+='<h3>최근 판정 (D+'+T.recent_window+')</h3><div class="table-scroll"><table data-track-recent><thead><tr><th>체결일</th><th>기업</th><th>구분</th><th>수익률</th><th>S&amp;P 500</th><th>평가</th></tr></thead><tbody>'
   +T.recent.map(r=>'<tr><td>'+esc(r.date)+'</td><td>'+esc(r.company)+'</td><td>'+(r.side==='BUY'?'가상 매수':'가상 매도')+'</td><td>'+esc(pct(r.stock_return))+'</td><td>'+esc(pct(r.benchmark_return))+'</td><td>'+(r.hit?'적중':'미적중')+'</td></tr>').join('')+'</tbody></table></div>';}
 else h+='<p>'+esc(NA)+'</p>';
 h+='<p class="small">'+esc('누적 가상 실현손익 '+(s?money(s.realized_pnl,H):NA)+' · 누적 가상 TWR '+(s?pct(s.twr):NA))+'</p>';
 h+='<p class="small">'+esc('적중: 가상 체결일 종가 대비 D+N 세션 종가 수익률을 S&P 500(SPY, 현지 통화)과 비교(D-11). 가상 매수는 상회, 가상 매도는 하회면 적중. 표본 '+minSamples(T)+'건 미만이면 적중률을 숫자로 보이지 않습니다(D-12). 예상일 ≈는 주말·NYSE 휴장일만 뺀 추산입니다.')+'</p></section>';
 return h;
}
/* ⑫ period table (current basis). */
function periodsCard(m,{locale='ko-KR'}={}){
 const B=m.bench;let h='<section class="card" data-report-section="12"><h2>⑫ 기간별 성과</h2>';
 if(!B)return h+'<p>'+esc(NA)+'</p></section>';
 h+='<p class="small" data-bench-basis-line data-basis="'+esc(B.basis)+'">'+esc(basisName(B.basis,locale)+' · 기준 완료 거래일 '+(B.as_of||NA))+'</p>';
 if(B.state!=='OK')h+='<p class="badge NOT_AVAILABLE" data-bench-state>'+esc('NOT_AVAILABLE · '+benchCode(B.reason,locale))+'</p>';
 const why=c=>'<br><span class="small" data-bench-reason="'+esc(c)+'">'+esc((RB&&RB.codeLabel(c,locale))||VT.codeLabel(c,locale)||c)+'</span>';
 const cell=x=>'<td>'+esc(x.return===null?NA:pct(x.return))+(x.return===null?why(x.reason):'')+'</td>';
 h+='<div class="table-scroll"><table data-bench-periods><thead><tr><th>기간</th><th>대상</th><th>S&amp;P 500</th><th>초과 · 판정</th></tr></thead><tbody>'
  +B.periods.map(r=>'<tr data-bench-period-row="'+esc(r.period)+'" data-bench-row-state="'+esc(r.state)+'"><td>'+esc(periodName(r.period,locale))+(r.base?'<br><span class="small">'+esc('기준 '+r.base)+'</span>':'')+'</td>'
   +(r.state==='OK'?cell(r.target)+cell(r.sp500):'<td>'+esc(NA)+why(r.reason)+'</td><td>'+esc(NA)+'</td>')
   +'<td>'+esc(excessText(r.excess))+(r.verdict?'<br><span class="small">'+esc(verdictName(r.verdict,locale))+'</span>':'')+'</td></tr>').join('')+'</tbody></table></div>';
 return h+'<p class="small">'+esc('기간 시작 직전 세션 종가 = 기준. 결측 종가·환율·장부 평가는 채우지 않고 N/A와 사유 코드로 둡니다. 대상 수익률은 가상 입금을 뺀 시간가중 수익률입니다.')+'</p></section>';
}
/* ⑬ relative-index dashboard: period and basis selectors, SVG lines (gaps break), legend table with returns. */
function dashboardCard(m,{locale='ko-KR'}={}){
 const B=m.bench,D=B&&B.dashboard;let h='<section class="card" data-report-section="13" data-report-section-wide><h2>⑬ 상대지수 · 성과 <span class="badge">기준 = 100</span></h2>';
 if(!B)return h+'<p>'+esc(NA)+'</p></section>';
 const ids=RB?RB.PERIOD_IDS:[];
 h+='<div class="chips mode-toggle" data-bench-periods-select role="group" aria-label="기간">'+ids.map(p=>'<button type="button" data-bench-period="'+esc(p)+'" aria-pressed="'+(p===B.period?'true':'false')+'">'+esc(periodName(p,locale))+'</button>').join('')+'</div>';
 h+='<label class="toggle">통화 기준 <select data-bench-basis>'+(RB?RB.BASES:[]).map(b=>'<option value="'+b+'"'+(b===B.basis?' selected':'')+'>'+(b==='KRW'?'원화(KRW)':'달러(USD)')+'</option>').join('')+'</select></label>';
 h+='<p class="small" data-bench-basis-note>'+esc(basisName(B.basis,locale))+'</p>';
 if(!D||D.state!=='OK')return h+'<p class="badge NOT_AVAILABLE" data-bench-dashboard-state>'+esc('NOT_AVAILABLE · '+benchCode(D?D.reason:B.reason,locale))+'</p></section>';
 const target=D.series.length?D.series[0].key:null;
 h+='<p class="small">'+esc('기준 '+D.base+' 종가 = 100 · '+D.sessions[0]+'~'+D.sessions[D.sessions.length-1]+' · '+D.sessions.length+'세션')+'</p>';
 h+='<div class="bench-chart">'+(RB?RB.chartSvg(D,{locale,target}):'')+'</div>';
 h+='<div class="table-scroll"><table data-bench-series><thead><tr><th>시리즈</th><th>'+esc(periodName(D.period,locale))+' 수익률</th><th>상태</th></tr></thead><tbody>'
  +D.series.map(x=>'<tr data-bench-series-row="'+esc(x.key)+'" data-bench-series-state="'+esc(x.state)+'"><td>'+(RB?RB.swatchSvg(x.key,x.key===target):'')+esc(seriesName(x.key,locale)+(x.key===target?' · 대상':''))+'</td><td>'+esc(x.return===null?NA:pct(x.return))+'</td><td class="small">'+esc(seriesState(x,locale))+'</td></tr>').join('')+'</tbody></table></div>';
 return h+'<p class="small">'+esc('S&P 500은 SPY 일봉. 결측 종가·환율은 보간하지 않고 선을 끊습니다. 지수와 수익률은 %라 금액 숨김 대상이 아닙니다. 위험지표(MDD·변동성 등)는 아직 연결 전(N/A)입니다.')+'</p></section>';
}
function screenHtml(m,{hidden=true,answer=null,check=null,locale='ko-KR'}={}){
 const H={hidden,mode:'screen'},s=m.summary,en=locale==='en-US',kindName=KINDS[m.kind][en?'en':'ko'];
 const base=Object.entries(m.base_dates||{}).map(([k,v])=>k+' '+v).join(' · ')||NA;
 const tabs=m.kind==='MOCK'?['SET_A','SET_B','COMPARE']:['REAL'];
 const rehearsal=m.mode==='REHEARSAL',modeName=MODE_LABEL[m.mode][en?'en':'ko'];
 let h='<div class="chips data-badges" data-report-badges><span class="badge mode '+m.mode+'" data-report-mode="'+m.mode+'">'+esc(modeName)+'</span><span class="badge">'+esc(kindName)+'</span><span class="badge">'+esc('기준 완료 거래일 '+base)+'</span><span class="badge">포트폴리오 v1.1 · QGV 점수 기준 v1 · 가상매매 규칙 v1</span><span class="badge">STANDARD v1 · UNCALIBRATED</span><span class="badge">유형 v1 잠정</span><span class="badge">비용 미반영 · 소수점 가정</span><span class="badge PROVISIONAL">PROVISIONAL 기본값 · 나중에 수정 가능</span>'+VT.disclaimerHtml(locale)+'</div>';
 h+='<label class="toggle" data-report-hide><input type="checkbox" data-hide-amounts'+(hidden?' checked':'')+'> 금액 숨김 <span class="small">· 기본 켜짐</span></label>';
 if(tabs.length>1)h+='<nav class="chips screen-tabs" data-report-tabs>'+tabs.map(t=>'<a href="#report/mock-'+t.toLowerCase()+'"'+(t===m.tab?' aria-current="page"':'')+'>'+esc(TABS[t])+'</a>').join('')+'</nav>';
 else h+='<p class="small">'+esc('그림자 장부는 실제 보유에서 출발한 "규칙대로 했다면"의 가상 기록입니다. 실제 계좌 지시가 아닙니다.')+'</p>';
 h+='<section class="card" data-report-summary><h2>'+esc(m.kind==='REAL'?'평가액':'총 모의평가액')+'</h2><p class="big">'+esc(s?money(s.total_value,H):NA)+'</p><p>'+esc('누적 '+(s?pct(s.simple_return):NA))+'</p>'
  +'<div class="grid two"><div><b>가상 매수</b><p>'+esc(m.buy_total===null?NA:money(m.buy_total,H))+'</p><p class="small">'+esc('가상 매수 한도 '+money(m.buy_limit,H)+(m.buy_total!==null&&num(m.buy_limit)?' 중 '+Math.round(m.buy_total/m.buy_limit*100)+'%':''))+'</p></div>'
  +'<div><b>가상 매도</b><p>'+esc(m.sell_total===null?NA:money(m.sell_total,H))+'</p><p class="small">'+esc('가상 매도 한도 '+money(m.sell_limit,H)+(m.sell_total!==null&&num(m.sell_limit)?' 중 '+Math.round(m.sell_total/m.sell_limit*100)+'%':''))+'</p></div></div>'
  +(m.started?'':'<p class="badge NOT_AVAILABLE" data-report-not-started>'+esc(notStarted(m))+'</p>')+'</section>';
 const before=!!(m.report_date&&m.start_date&&m.report_date<m.start_date),sig=m.signals||{},cap=sig.capture||null,vp=vProgressText(sig.v_progress);
 h+='<section class="card mode-card '+m.mode+'" data-report-mode-card data-mode="'+m.mode+'"><h2>'+esc(modeName)+'</h2>'
  +(rehearsal?'<p data-rehearsal-note>'+esc(rehearsalLine(m))+'</p><div class="sheet-actions"><button type="button" data-recording-mode>'+esc(en?'Back to recording mode':'기록 모드로 돌아가기')+'</button></div>'
   :'<p class="small">'+esc(before?'가상매매 시작일 전입니다. 리허설은 오늘 데이터로 규칙만 돌려 보고, 어떤 장부·시트에도 기록하지 않습니다.':'시작일 이후 규칙 결과입니다. 리허설로 최근 거래일을 기록 없이 다시 볼 수 있습니다.')+'</p><div class="sheet-actions"><button type="button" data-rehearsal-run>'+esc(en?'Run rehearsal':'리허설 실행')+'</button></div>')
  +(vp?'<p class="small" data-v-progress data-v-state="'+esc(sig.v_progress.state)+'">'+esc(vp+' · V 기울기(D-21)는 첫 기록 뒤 20거래일부터 · 이 기기에만 V 점수 저장(가격 없음)')+'</p>':'')
  +(cap?'<p class="small" data-v-capture="'+esc(cap.state)+'">'+esc(cap.state==='RECORDED'?'오늘 V 기록: '+cap.date+' · '+cap.added.length+'개 기업':'오늘 V 기록 없음 · '+(cap.reason?VT.codeText(cap.reason):NA))+'</p>':'')+'</section>';
 h+=inputsCard(m.runner);
 h+='<section class="card" data-report-ai-summary><h2>오늘의 요약 <span class="badge">AI 해석</span></h2>'+(answer?'<pre class="ai-answer" data-ai-answer>'+esc(answer.answer)+'</pre><p class="small">'+esc((answer.model?answer.model+' · ':'')+'보관 '+(answer.saved_at||'')+' · '+(answer.source==='MAILBOX'?'우체통':'붙여넣기'))+'</p>':'<p data-rule-summary>'+esc('【규칙】 '+ruleSummary(m))+'</p>')
  +(check?'<p class="badge '+(check.format_ok?'LIVE':'NOT_AVAILABLE')+'" data-answer-format>'+esc(check.format_ok?'형식 확인됨':'형식 확인 필요')+'</p>'+(check.foreign_numbers.length?'<p class="badge STALE" data-foreign-numbers>'+esc('템플릿에 없는 숫자 '+check.foreign_numbers.length+'개')+'</p>':''):'')
  +'<p class="small">숫자는 앱 계산, 문장은 붙여넣은 AI 해석입니다. AI 해석이 없으면 규칙 문장으로 대신 채웁니다.</p></section>';
 h+='<section class="card" data-report-section="3"><h2>③ 전 종목 장부 '+VT.disclaimerHtml(locale)+(rehearsal?' <span class="badge mode REHEARSAL">'+esc(modeName)+'</span>':'')+'</h2>';
 const basisCell=x=>x.basis?'<td class="small" data-basis="'+esc(x.company)+'" data-basis-benchmark="'+esc(x.basis.benchmark)+'" data-basis-state="'+esc(x.basis.state)+'" data-basis-fallback="'+(x.basis.fallback?'1':'0')+'" data-v-slope="'+esc(x.basis.v_slope)+'">'+esc(basisText(x.basis))+'</td>':'<td class="small">'+NA+'</td>';
 if(m.holdings.length){h+='<div class="table-scroll"><table><thead><tr><th>기업</th><th>실제/목표</th><th>Q·G</th><th>판단</th><th>사유</th>'+(m.started?'<th>업종 기준 · D-5</th>':'')+'</tr></thead><tbody>'+m.holdings.map(x=>'<tr><td>'+esc(x.name)+'</td><td>'+esc(weight(x.actual_weight)+' / '+weight(x.target_weight))+'</td><td>'+esc(num(x.q)&&num(x.g)?score((x.q+x.g)/2):NA)+'</td><td data-judgement-cell="'+esc(x.company)+'">'+(judgementOf(x)?VT.judgementHtml(judgementOf(x),{locale}):NA)+'</td><td class="small" data-reasons-cell="'+esc(x.company)+'">'+(x.reasons.length?VT.reasonsHtml(x.reasons,{locale}):NA)+'</td>'+(m.started?basisCell(x):'')+'</tr>').join('')+'</tbody></table></div><p class="small">'+esc(countsLine(m.holdings))+'</p>'
  +(m.started?'<p class="small">'+esc('업종 기준: D-5 이상 하락 판정에 실제로 쓴 기준(D-22 업종 ETF, 없으면 S&P 500 대체). 정렬된 일봉 273개 미만이거나 기준이 없으면 기준 N/A이고 V 기울기도 쓰지 않습니다.')+'</p>':'');}
 else h+='<p>'+esc(NA+' · '+(m.kind==='REAL'?'기기 보유(ACTUAL) 없음 또는 시세 부족':'가상 장부 시작 전'))+'</p>';
 h+='<p class="small" data-level-priority>'+esc('우선순위: '+VT.priorityText(locale)+'. 회사마다 주 판단 1개, 나머지는 보조 칩. 가상 매수·가상 매도 표현은 ⑩ 가상 장부 안에서만 씁니다.')+'</p></section>';
 h+='<section class="card" data-report-section="10"><h2>⑩ 행동요령 · 가상 매매장부 '+VT.disclaimerHtml(locale)+(rehearsal?' <span class="badge mode REHEARSAL">'+esc(modeName)+'</span>':'')+'</h2>';
 if(m.executed.length)h+='<div class="table-scroll"><table><thead><tr><th>구분</th><th>기업</th><th>금액</th><th>수량</th><th>규칙 사유</th></tr></thead><tbody>'+m.executed.map(t=>'<tr><td>'+(t.side==='BUY'?'가상 매수':'가상 매도')+'</td><td>'+esc(t.company)+'</td><td>'+esc(money(t.amount,H))+'</td><td>'+esc(quantity(t.quantity,H))+'</td><td class="small">'+VT.reasonsHtml(t.reason_codes,{locale})+'</td></tr>').join('')+'</tbody></table></div>';
 else h+='<p>'+esc(m.started?'오늘 가상 거래 없음':'시작 전 · 거래 기록 없음')+'</p>';
 if(m.cancelled.length){const codes=[...new Set(m.cancelled.map(o=>o.cancel_reason))].sort();
  h+='<h3>가상 주문 취소</h3><div class="table-scroll"><table data-report-cancelled><thead><tr><th>기업</th><th>구분</th><th>금액</th><th>사유 코드</th></tr></thead><tbody>'+m.cancelled.map(o=>'<tr data-cancel-reason="'+esc(o.cancel_reason)+'"><td>'+esc(o.company)+'</td><td>'+(o.side==='BUY'?'가상 매수':'가상 매도')+'</td><td>'+esc(money(o.amount,H))+'</td><td class="small">'+VT.reasonsHtml([o.cancel_reason],{locale})+'</td></tr>').join('')+'</tbody></table></div>'
   +'<p class="small" data-cancel-legend>'+esc(codes.map(c=>c+': '+(VT.codeLabel(c,locale)||c)).join(' · ')+' · 없는 값은 채우지 않습니다.')+'</p>';}
 if(s)h+='<p class="small">'+esc('가상 현금 '+money(s.cash,H)+' · 실현손익 '+money(s.realized_pnl,H)+' · 미실현손익 '+money(s.unrealized_pnl,H))+'</p>';
 h+='<p class="small">체결은 다음 완료 정규장 종가 가정입니다. 가상 매도대금은 가상 현금으로 가며 다음 날 한도를 늘리지 않습니다. 이 장부는 실제 평가액과 합산하지 않습니다. 주문 기능은 없습니다.</p></section>';
 h+='<section class="card" data-report-section="rest"><h2>①②④⑤⑥⑦⑧⑨</h2><p>'+esc('이 절들은 보고서 템플릿 내보내기에 같은 순서로 들어갑니다. 연결되지 않은 값은 N/A로 표시합니다.')+'</p></section>';
 h+=trackCard(m,{hidden,locale})+periodsCard(m,{locale})+dashboardCard(m,{locale});
 h+='<section class="card" data-report-export><h2>AI 해석 받기 <span class="badge">템플릿 v1</span></h2><p>숫자가 모두 채워진 보고서 템플릿과 \'AI 해석 지침 v1\'을 함께 복사합니다. AI는 【AI】 칸만 채워 같은 형식으로 돌려줍니다.</p>'
  +'<label class="toggle"><input type="checkbox" data-hide-amounts-export'+(hidden?' checked':'')+'> 금액 숨김 <span class="small">· 기본 켜짐, 금액은 [숨김]·한도 대비 %로</span></label>'
  +'<label class="toggle"><input type="checkbox" data-include-guide checked> 지침 포함 <span class="small">· 프로젝트 지침에 넣어 두었다면 끄기</span></label>'
  +'<div class="sheet-actions"><button type="button" data-export-template>보고서 템플릿 내보내기</button></div>'
  +'<label for="ai-answer-input">AI 답변 붙여넣기 → \'AI 해석\'에 보관</label><textarea id="ai-answer-input" data-ai-input rows="6"></textarea><div class="sheet-actions"><button type="button" data-save-answer>AI 답변 보관</button></div>'
  +'<p class="small">개인 금액이 포함될 수 있습니다. 앱은 자동으로 전송하지 않고, 사용자가 직접 복사할 때만 기기 밖으로 나갑니다. 시트 ID·토큰·이메일은 어떤 설정에서도 내보내지 않습니다.</p><p role="status" data-report-status></p></section>';
 h+='<section class="card" data-report-mailbox><h2>AI 우체통 <span class="badge">선택 · 기본 OFF</span></h2><p class="small">켜면 연결된 내 구글 시트의 ReportInbox 탭에 오늘 템플릿(금액 숨김 상태)을 쓰고, ReportOutbox 탭에서 해시가 같은 답만 가져옵니다. 종목·비중·점수는 사용자가 연결한 AI 공급자에게 전달됩니다. Worker를 쓰지 않습니다.</p>'
  +'<div class="sheet-actions"><button type="button" data-mailbox-post>우체통에 오늘 템플릿 넣기</button><button type="button" data-mailbox-read>우체통 답 확인</button></div></section>';
 h+='<section class="card" data-report-footnote><h2>고정 각주</h2><p class="small">'+esc((TABS[m.tab]||'')+' · 포트폴리오 v1.1 · QGV 점수 기준 v1(보정 전) · 유형 v1 잠정 · 평가액 '+(s?money(s.total_value,H):NA)+' · 가상매매 실제 평가액 미반영 · 결측 N/A')+'</p><p class="small">'+esc('보고일: '+(m.report_date||NA)+' · 가상매매 시작일: '+(m.start_date||'미정 (D-13)'))+'</p></section>';
 return h;
}
return Object.freeze({TEMPLATE_VERSION,GUIDE_VERSION,KINDS,TABS,CHECK_LINES,GUIDE_A,HEADER_B,KIND_LINE,HIDE_KEY,AI_KEY,INBOX,OUTBOX,MODE_LABEL,basisText,vProgressText,
 formatKrw,money,quantity,hiddenSetting,buildModel,renderTemplate,checkAnswer,hash,answers,saveAnswer,ensureTabs,postInbox,readOutbox,screenHtml});
});
