/* Universe504 company page (IA-18 (b), screen only). Opens for a Universe code that is not a TARGET company and shows, from public
   files the Pages build already serves, the published QGV v2 row of `sec-qgv2.json` (state, calc_version, as_of, acquired_at,
   Q/G axis scores with their coverage and peer basis/count, each factor percentile with the Q1…Q5 / G1…G5 labels of
   CompanyScreen.V2_LABEL, reason codes and NA reasons), the SIC / industry group / financial profile of that row, the device type
   memberships (QgvScores.typeMemberships, the same rule as every other row) and the SEC cover facts of `sec-universe-shares.json`.
   V, the QGV total and the value-trap gate come only from the existing device path (QgvScores.collectQuotes -> QgvScores.compute):
   device prices stay in RAM and are never shown, stored or sent; without them V is NOT_AVAILABLE with the engine's reason code.
   The daily-candle chart (PrivateHistory) is mounted only for a code in its price scope (a TARGET issuer by CIK); any other code
   shows NOT_AVAILABLE (TA G2 undecided). Missing values are NOT_AVAILABLE with a reason, never 0, and no number is invented.
   No inline styles: bars are SVG rect widths, colours come from universe-company.css classes. Names (KR-NAMES, 2026-10-18) come
   from the reviewed company-names-ko.json: the title is "한국어명 · 티커" (English name, then the ticker, as fallbacks) and the
   page lists the English (SEC) name and the name source. Names are display only and never reach a score. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.UniverseCompany=api;})(typeof globalThis!=='undefined'?globalThis:this,function(g){
'use strict';
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v),object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const num=(v,locale,digits=1)=>new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v);
const na=(reason,locale)=>'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>'+(reason?' <span class="small">'+esc(reason)+'</span>':'');
const CODE=/^(NYSE|NASDAQ|BATS):([A-Z0-9][A-Z0-9.\-]{0,15})$/;
const AXES=['Q','G','V'],AXIS_NAME={Q:['Q 질','Q quality'],G:['G 성장','G growth'],V:['V 가치','V value']};
const GROUP_LABEL={resources_mining:['자원·광업','Resources / mining'],construction:['건설','Construction'],food_tobacco:['식품·담배','Food / tobacco'],manufacturing_industrial_tech:['제조·산업·기술','Manufacturing / industrial / tech'],transportation:['운송','Transportation'],telecommunications:['통신','Telecommunications'],utilities:['유틸리티','Utilities'],wholesale_retail:['도소매','Wholesale / retail'],finance_real_estate:['금융·부동산','Finance / real estate'],services_software_health:['서비스·소프트웨어·헬스','Services / software / health']};
const PROFILE_LABEL={GENERAL:['일반','General'],FINANCIAL:['금융','Financial']};
const PEER_LABEL={INDUSTRY_GROUP:['같은 SIC 업종군','Same SIC industry group'],UNIVERSE:['504 전체(일반 프로필)','Whole 504 (general profile)'],UNIVERSE_FALLBACK:['504 전체(업종군 8곳 미만이라 대체)','Whole 504 (industry group below 8 peers)'],FINANCIAL_PROFILE:['금융 프로필 전체','Financial profile']};
/* Source reasons of a row without data (sec-qgv2.json REASONS + the Universe withdrawal) and of a stale row. Each is shown apart. */
const SOURCE_REASON={NOT_COLLECTED:['미수집: 이 코드의 SEC 자료를 아직 모으지 않았습니다','Not collected: SEC data for this code has not been gathered yet'],
 CIK_UNRESOLVED:['CIK 미확인: 이 코드의 SEC 등록번호를 찾지 못했습니다','CIK unresolved: no SEC registrant number was found for this code'],
 NO_ANNUAL_SEC_FINANCIALS:['연간 SEC 재무 없음: 연간 보고서 재무 항목이 없습니다','No annual SEC financials'],
 NON_SEC_ISSUER:['SEC 발행인 아님','Not an SEC issuer'],INVALID_INPUT:['입력 검증 실패: 원자료가 검증을 통과하지 못했습니다','Invalid input: the source did not pass validation'],
 IDENTITY_CONFLICT_WITHDRAWN:['식별 충돌로 사용 중지: 이 코드의 이전 관측을 쓰지 않습니다','Withdrawn: identity conflict, the earlier observation is not used'],
 STALE_INPUT:['오래된 자료: 마지막 유효 값 기준','Stale: last valid value']};
const sourceText=(code,en)=>Object.hasOwn(SOURCE_REASON,code)?SOURCE_REASON[code][en?1:0]:code;
const label=(map,key,en)=>Object.hasOwn(map,key)?map[key][en?1:0]:key;
function codeParts(code){const m=typeof code==='string'?CODE.exec(code):null;return m?{exchange:m[1],ticker:m[2]}:null;}
function factorLabels(locale){const L=g.CompanyScreen&&g.CompanyScreen.V2_LABEL,W=g.QgvV2?g.QgvV2.WEIGHTS:null,en=locale==='en-US'?1:0,out={};
 if(!W)return out;for(const a of AXES)Object.keys(W[a]).forEach((f,i)=>{out[f]={axis:a,n:a+(i+1),weight:W[a][f],name:L&&L[f]?L[f][en]:f};});return out;}
function inputsOf(screens){const F=g.Qgv2Inputs;return F&&screens&&object(screens[F.FILE])?screens[F.FILE]:null;}
function fileReason(){try{return g.Qgv2Inputs&&g.Qgv2Inputs.lastReason()==='SCHEMA_NEWER'?'SEC_QGV2_SCHEMA_NEWER':'SEC_QGV2_NOT_AVAILABLE';}catch(_){return 'SEC_QGV2_NOT_AVAILABLE';}}
// TARGET issuer of this code by CIK (SecQgv2.TARGET_CIKS): the TARGET page and the daily chart scope belong to it.
function targetIdOf(rec){const T=g.SecQgv2&&g.SecQgv2.TARGET_CIKS;if(!T||!rec||typeof rec.cik!=='string')return null;for(const[id,cik]of Object.entries(T))if(cik===rec.cik)return id;return null;}
function ageDays(at,now){const t=Date.parse(at);return Number.isFinite(t)?Math.max(0,Math.floor((now-t)/864e5)):null;}
function clock(x){return typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';}
/* Page state of the published row, told apart: no file, code not in the file, withdrawn, not collected (with its reason), other
   calculation-rule version, or LIVE / STALE (device-time freshness from the row's own acquired_at). */
function rowState(inputs,code){
 if(!inputs)return{state:'NO_FILE',reason:fileReason(),rec:null};
 const rec=object(inputs.records)&&Object.hasOwn(inputs.records,code)?inputs.records[code]:null;
 if(!rec)return{state:'NOT_IN_FILE',reason:'NOT_IN_UNIVERSE',rec:null};
 if(rec.identity_withdrawn===true)return{state:'WITHDRAWN',reason:'IDENTITY_CONFLICT_WITHDRAWN',rec};
 if(rec.calc_version_mismatch===true)return{state:'CALC_VERSION_MISMATCH',reason:'CALC_VERSION_MISMATCH',rec};
 if(rec.state==='NOT_AVAILABLE')return{state:'SOURCE_NA',reason:(rec.na_reasons&&rec.na_reasons[0])||'NOT_COLLECTED',reasons:[...(rec.na_reasons||[])],rec};
 return{state:rec.state,reason:rec.state==='STALE'?'STALE_INPUT':null,rec};
}
/* Device computation through the one score accessor (same engine, same population as S04/S06). Rank is not used here. */
function scored(code,ctx){const QS=g.QgvScores,p=codeParts(code);if(!QS||!p)return null;
 try{const S=QS.compute({identities:[{company_id:code,ticker:p.ticker}],publicScreens:ctx.screens||{},quotes:object(ctx.quotes)?ctx.quotes:{}});const row=S&&S.rows?S.rows[code]:null;return row&&row.code===code?row.primary:null;}catch(_){return null;}}
function bar(axis,value){if(!finite(value))return '<span class="uc-bar-na" aria-hidden="true"></span>';const w=Math.max(0,Math.min(100,value));
 return '<svg class="uc-bar" viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="uc-track" x="0" y="0" width="100" height="8"></rect><rect class="uc-fill uc-fill-'+axis.toLowerCase()+'" x="0" y="0" width="'+w.toFixed(2)+'" height="8"></rect></svg>';}
function freshLine(parts){return '<p class="small uc-fresh" data-uc-fresh>'+parts.filter(Boolean).map(esc).join(' · ')+'</p>';}
function qgFresh(inputs,rs,locale,now){const T=tr(locale),rec=rs.rec,has=rec&&typeof rec.acquired_at==='string',age=has?ageDays(rec.acquired_at,now):null;
 return freshLine([T('출처 sec-qgv2.json','Source sec-qgv2.json'),'as_of '+(inputs?clock(inputs.as_of):'—'),T('수집 ','acquired ')+(has?clock(rec.acquired_at):'—'),age!==null?T('수집 후 ','age ')+age+T('일',' d'):null,T('상태 ','state ')+rs.state,'calc_version '+(rs.state==='LIVE'||rs.state==='STALE'?(inputs.calc_version||'—'):rs.state==='CALC_VERSION_MISMATCH'?T('파일과 다름','differs from file'):'—')]);}
/* One axis (Q or G) as published: score or the NA kind (policy NA of a collected row vs. no source / withdrawn / other version). */
function axisState(rs,pub){if(rs.state==='WITHDRAWN')return 'WITHDRAWN';if(rs.state==='CALC_VERSION_MISMATCH')return 'CALC_VERSION';if(rs.state!=='LIVE'&&rs.state!=='STALE')return 'SOURCE_NA';return pub&&finite(pub.score)?'SCORED':'POLICY_NA';}
function axisWhy(state,pub,rs,locale){const QS=g.QgvScores,en=locale==='en-US',T=tr(locale);
 if(state==='SCORED')return '';if(state==='POLICY_NA'){const c=pub&&pub.reason_codes&&pub.reason_codes[0];return T('정책상 NA · ','Policy NA · ')+(QS?QS.reasonText(c||'AXIS_COVERAGE_BELOW_50',en):c);}
 if(state==='WITHDRAWN')return sourceText('IDENTITY_CONFLICT_WITHDRAWN',en);if(state==='CALC_VERSION')return QS?QS.reasonText('CALC_VERSION_MISMATCH',en):'CALC_VERSION_MISMATCH';
 return (rs.reasons&&rs.reasons.length?rs.reasons:[rs.reason]).map(c=>sourceText(c,en)).join(' · ');}
function axisMeta(axis,pub,locale){const T=tr(locale),en=locale==='en-US';if(!pub)return '';
 const parts=[T('요인 ','factors ')+(pub.factors_available??'—'),T('가중치 충족 ','weight covered ')+(finite(pub.available_weight)?pub.available_weight+'%':'—'),T('비교군 ','peers ')+(pub.peer_basis?label(PEER_LABEL,pub.peer_basis,en)+' ('+pub.peer_basis+')':'—')+(Number.isInteger(pub.peer_count)?' · '+pub.peer_count+T('곳',' cos'):''),T('대체 순위 ','sub-metric fallbacks ')+(pub.submetric_fallbacks??'—'),'reason_codes '+(pub.reason_codes&&pub.reason_codes.length?pub.reason_codes.join(', '):'—')];
 return '<p class="small" data-uc-axis-meta="'+axis+'" data-uc-peer-basis="'+esc(pub.peer_basis||'')+'" data-uc-peer-count="'+esc(Number.isInteger(pub.peer_count)?pub.peer_count:'')+'">'+parts.map(esc).join(' · ')+'</p>';}
/* Factor rows: Q/G percentiles are the published values; V factors come from the device computation (null without prices). */
function factorRows(axis,rs,d,locale){const T=tr(locale),en=locale==='en-US',QS=g.QgvScores,labels=factorLabels(locale),rec=rs.rec;
 const cov=d&&d.coverage&&d.coverage.axes?d.coverage.axes[axis]:null;
 return Object.entries(labels).filter(([,x])=>x.axis===axis).map(([f,x])=>{
  let v=null;if(axis==='V'){const s=d&&d.factors&&d.factors[f];v=s&&finite(s.score)?s.score:null;}else if(rec&&(rs.state==='LIVE'||rs.state==='STALE')&&rec.factors)v=finite(rec.factors[f])?rec.factors[f]:null;
  const c=cov?cov.factors.find(y=>y.id===f):null;let why='';
  if(v===null){if(axis!=='V'&&rs.state!=='LIVE'&&rs.state!=='STALE')why=axisWhy(axisState(rs,null),null,rs,locale);else why=c&&QS?QS.reasonText(c.reason,en):T('계산 불가','Not calculated');}
  const kind=v!==null?'SCORED':c&&c.category?c.category:'NOT_AVAILABLE';
  return '<tr data-uc-factor="'+f+'" data-uc-value="'+(v===null?'NA':String(v))+'" data-uc-factor-state="'+esc(kind)+'"><th scope="row"><b>'+esc(x.n)+'</b> '+esc(x.name)+'</th><td class="num">'+esc(x.weight)+'</td><td class="uc-pct">'+bar(axis,v)+'<span class="num" data-uc-pct>'+(v===null?'—':esc(num(v,locale)))+'</span></td><td class="small">'+(v===null?'<span class="badge '+(kind==='NOT_APPLICABLE'?'NOT_AVAILABLE':'partial')+'">'+esc(QS&&kind!=='NOT_AVAILABLE'?QS.stateText(kind,en):kind)+'</span> '+esc(why):esc(axis==='V'?T('이 기기 계산','device'):T('공개 백분위','published')))+'</td></tr>';}).join('');}
function vInfo(d,rec,locale,priced){const T=tr(locale),en=locale==='en-US',QS=g.QgvScores,cov=d&&d.coverage&&d.coverage.axes?d.coverage.axes.V:null;
 const status=cov?cov.status:'NOT_AVAILABLE',reason=finite(d&&d.v)?null:cov&&cov.reason?cov.reason:priced?'V_INPUTS_NOT_AVAILABLE':'NO_DEVICE_PRICE';
 return{status,reason,text:reason?(QS?QS.reasonText(reason,en):reason):'',fresh:freshLine([T('출처 이 기기 시세(메모리 전용, 공개 안 함)','Source this device’s quotes (RAM only, never published)'),T('시세 ','quote ')+(priced?T('있음','present'):T('없음','none')),T('시세 시각은 이 화면에 보관하지 않음','quote time is not kept on this screen'),T('SEC 입력은 sec-qgv2.json 수집 시각 기준','SEC inputs as of the sec-qgv2.json acquisition')])};}
function gate(d,locale){const T=tr(locale),V2=g.QgvV2,lim=V2?V2.GATE_PERCENTILE:30;if(!d)return{state:'NOT_EVALUATED',text:T('관문 판정 불가: 점수 계산 없음','Gate not evaluated: no score')};
 const flags=d.flags||[],p=finite(d.q_industry_percentile)?d.q_industry_percentile:null,base=T('가치 함정 관문 켬(기본) · Q 업종 내 백분위 ','Value-trap gate on (default) · Q industry percentile ')+(p===null?'—':num(p,locale))+T(' · 기준 ≤ ',' · limit ≤ ')+lim;
 if(flags.includes('VALUE_TRAP_CAUTION'))return{state:'CAUTION',text:base+T(' → 가치 함정 주의: V를 총점에서 뺍니다',' → value-trap caution: V is left out of the total')};
 if(flags.includes('GATE_NOT_EVALUATED')||p===null)return{state:'NOT_EVALUATED',text:base+T(' → 관문 판정 불가(Q 업종 백분위 없음)',' → not evaluated (no Q industry percentile)')};
 return{state:'PASS',text:base+T(' → 통과',' → passed')};}
function qgvCard(code,rs,d,inputs,ctx,now){const T=tr(ctx.locale),en=ctx.locale==='en-US',rec=rs.rec,priced=!!(rec&&object(ctx.quotes)&&Object.hasOwn(ctx.quotes,code)),v=vInfo(d,rec,ctx.locale,priced);
 const pubAxis=a=>rec&&rec.qg_axes&&rec.qg_axes[a]?rec.qg_axes[a]:null;
 const line=a=>{let score=null,state,why;if(a==='V'){score=d&&finite(d.v)?d.v:null;state=score!==null?'SCORED':v.status==='NOT_APPLICABLE'?'NOT_APPLICABLE':'DEVICE_NA';why=v.text;}else{const pub=pubAxis(a);state=axisState(rs,pub);score=state==='SCORED'?pub.score:null;why=axisWhy(state,pub,rs,ctx.locale);}
  return '<div class="uc-axis-row" data-uc-axis="'+a+'" data-uc-axis-state="'+state+'" data-uc-score="'+(score===null?'NA':String(score))+'"><b class="uc-axis uc-axis-'+a.toLowerCase()+'">'+esc(label(AXIS_NAME,a,en))+'</b>'+bar(a,score)+'<span class="num">'+(score===null?'—':esc(num(score,ctx.locale)))+'</span>'+(why?'<span class="small uc-axis-why">'+esc(why)+'</span>':'')+'</div>';};
 const total=d&&finite(d.total)?'<span class="num" data-uc-total="'+String(d.total)+'">'+esc(num(d.total,ctx.locale))+'</span> <span class="small">'+esc(T('이 기기 계산 · 순위 아님 · 반영 축 ','computed on this device · not a rank · axes counted ')+(d.coverage&&d.coverage.axes?AXES.filter(a=>d.coverage.axes[a].use==='INCLUDED').join('·')||'—':'—'))+'</span>':'<span data-uc-total="NA">'+na(d&&d.total_reason?(g.QgvScores?g.QgvScores.reasonText(d.total_reason,en):d.total_reason):'',ctx.locale)+'</span>';
 return '<h2><span class="flow-number">1</span> QGV v2 <span class="badge partial">PROVISIONAL</span></h2><div class="uc-bars">'+AXES.map(line).join('')+'</div><p data-uc-total-line>'+esc(T('QGV v2 종합 ','QGV v2 total '))+total+'</p>'+qgFresh(inputs,rs,ctx.locale,now)+v.fresh;}
function factorsCard(rs,d,inputs,ctx,now){const T=tr(ctx.locale),en=ctx.locale==='en-US',rec=rs.rec,gt=gate(d,ctx.locale),v=vInfo(d,rec,ctx.locale,false);
 const head='<thead><tr><th scope="col">'+esc(T('요인','Factor'))+'</th><th scope="col">'+esc(T('비중','Weight'))+'</th><th scope="col">'+esc(T('백분위','Percentile'))+'</th><th scope="col">'+esc(T('상태·사유','State / reason'))+'</th></tr></thead>';
 const axisBlock=a=>{const pub=a!=='V'&&rec&&rec.qg_axes?rec.qg_axes[a]:null;return '<h3 class="uc-axis-head"><span class="uc-axis uc-axis-'+a.toLowerCase()+'">'+esc(label(AXIS_NAME,a,en))+'</span></h3>'+(a==='V'?'<p class="small" data-uc-axis-meta="V">'+esc(T('V는 이 기기 시세로만 계산합니다(공개 파일에는 가격·V 없음).','V is computed only from this device’s quotes (public files carry no price or V).'))+'</p>':axisMeta(a,pub,ctx.locale))+'<div class="table-wrap"><table class="uc-table" data-uc-factor-table="'+a+'">'+head+'<tbody>'+factorRows(a,rs,d,ctx.locale)+'</tbody></table></div>';};
 const reasons=rec?[...(rec.na_reasons||[]),...(rs.state==='STALE'?['STALE_INPUT']:[])]:[rs.reason];
 const rules='<p class="small" data-uc-rules>'+esc(T('규칙: 축 안 비례 재정규화 · 축 최소 50%(원래 가중치) · 결측은 0으로 채우지 않음 · 비교군 최소 8곳 · 비교군: Q는 업종군(금융은 금융 프로필), G는 504 전체','Rules: proportional renormalization within an axis · axis needs 50% of its original weight · missing is never 0 · at least 8 peers · peers: Q by industry group (financials by the financial profile), G across the 504'))+'</p>';
 return '<h2>'+esc(T('QGV 구성 · 요인별 백분위','QGV structure · factor percentiles'))+'</h2>'+AXES.map(axisBlock).join('')+rules
  +'<p class="small" data-uc-gate="'+gt.state+'">'+esc(gt.text)+'</p>'
  +'<p class="small" data-uc-reasons="'+esc(reasons.filter(Boolean).join(',')||'NONE')+'">'+esc(T('행 reason_codes: ','Row reason_codes: ')+(reasons.filter(Boolean).length?reasons.filter(Boolean).map(c=>c+' ('+sourceText(c,en)+')').join(' · '):'—'))+'</p>'
  +qgFresh(inputs,rs,ctx.locale,now)+v.fresh;}
function typeChips(code,rs,ctx){const T=tr(ctx.locale),QS=g.QgvScores,CS=g.CompanyScreen,p=codeParts(code);
 if(rs.state!=='LIVE'&&rs.state!=='STALE')return '<span data-uc-type="NA">'+na(T('유형 계산 불가: 공개 Q·G 행 없음','No type: no published Q·G row'),ctx.locale)+'</span>';
 let m=null;try{m=QS&&p?QS.typeMemberships({identity:{company_id:code,ticker:p.ticker},publicScreens:ctx.screens||{}}):null;}catch(_){m=null;}
 if(!m||m.code!==code||!object(m.memberships))return '<span data-uc-type="NA">'+na(T('유형 계산 불가','No type'),ctx.locale)+'</span>';
 const picked=CS&&CS.selectTypes?CS.selectTypes(m.memberships):null;
 return '<span data-uc-type="'+esc(picked&&picked.length?picked.join(','):'NONE')+'">'+(picked&&picked.length?picked.map(t=>'<span class="badge LIVE" data-type-chip="'+esc(t)+'">'+esc(CS.typeName(t,ctx.locale))+' '+esc(num(m.memberships[t],ctx.locale,2))+'</span>').join(' '):na(T('소속도 0.3 이상 유형 없음','No type with membership ≥ 0.3'),ctx.locale))+' <span class="small">'+esc(T('이 기기 계산 · 공개 지표 · 유형 규칙 PROVISIONAL · ','device · public metrics · type rules PROVISIONAL · ')+(m.type_scope||'—'))+'</span></span>';}
function sharesBlock(code,ctx){const T=tr(ctx.locale),en=ctx.locale==='en-US',dir=ctx.shares,r=dir&&dir.state==='READY'&&object(dir.records)?dir.records[code]:null;
 if(!dir||dir.state==='LOADING')return{state:'LOADING',html:'<p role="status" class="small" data-uc-shares="LOADING">'+esc(T('공개 SEC 표지 정보를 불러오는 중…','Loading the public SEC cover facts…'))+'</p>'};
 if(!r){const why=dir.reason==='SEC_UNIVERSE_SHARES_SCHEMA_NEWER'?T('자료 형식이 새 버전입니다. 새로고침하세요','The data format is newer. Reload the page'):dir.reason;return{state:'NOT_AVAILABLE',html:'<p class="empty">NOT_AVAILABLE · '+esc(why||'NOT_IN_UNIVERSE')+'</p>'};}
 const reasons=Array.isArray(r.reason_codes)?r.reason_codes:[];
 const rows=[[T('SEC 주식수 상태','SEC shares state'),r.state+(reasons.length?' · '+reasons.map(c=>c==='IDENTITY_CONFLICT_WITHDRAWN'?sourceText(c,en):c).join(' · '):'')],[T('발행주식수(SEC 표지)','Shares outstanding (SEC cover)'),r.shares===null?'NOT_AVAILABLE':Number(r.shares).toLocaleString(ctx.locale)],[T('기준일','Measured'),r.measurement_date||'—'],[T('서식·제출일','Form / filed'),(r.form||'—')+' · '+(r.filed||'—')],[T('주식 종류 기준','Share-class basis'),r.share_class_basis],['CIK',r.cik||'—']];
 return{state:r.state,html:'<dl class="kv">'+rows.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl>'+freshLine([T('출처 sec-universe-shares.json','Source sec-universe-shares.json'),'as_of '+clock(dir.as_of),T('수집 ','acquired ')+clock(r.acquired_at),T('상태 ','state ')+r.state])};}
function classificationCard(code,rs,inputs,ctx,now){const T=tr(ctx.locale),en=ctx.locale==='en-US',rec=rs.rec,has=rs.state==='LIVE'||rs.state==='STALE',SQ=g.SecQgv2;
 const range=grp=>{const x=SQ&&SQ.SIC_GROUPS?SQ.SIC_GROUPS.find(([id])=>id===grp):null;return x?' · SIC '+x[1].map(([lo,hi])=>lo+'–'+hi).join(', '):'';};
 const sic=has&&rec.sic?esc(rec.sic):na(axisWhy('SOURCE_NA',null,rs,ctx.locale),ctx.locale);
 const group=has&&rec.industry_group?esc(label(GROUP_LABEL,rec.industry_group,en)+range(rec.industry_group)+' ('+rec.industry_group+')'):na('',ctx.locale);
 const profile=has&&rec.published_profile?esc(label(PROFILE_LABEL,rec.published_profile,en)+' ('+rec.published_profile+')')+' <span class="small">'+esc(T('재무 프로필 · 기업 유형과 다른 개념 · 금융 = SIC 6000–6499','Financial profile · not the company type · financial = SIC 6000–6499'))+'</span>':na('',ctx.locale);
 const fy=has&&rec.fiscal_year_end?esc(rec.fiscal_year_end):na('',ctx.locale);
 return '<h2>'+esc(T('분류·공시','Classification / filings'))+'</h2><dl class="kv"><dt>SIC</dt><dd data-uc-sic="'+esc(has&&rec.sic?rec.sic:'NA')+'">'+sic+'</dd><dt>'+esc(T('업종군','Industry group'))+'</dt><dd data-uc-group="'+esc(has&&rec.industry_group?rec.industry_group:'NA')+'">'+group+'</dd><dt>'+esc(T('재무 프로필','Financial profile'))+'</dt><dd data-uc-profile="'+esc(has&&rec.published_profile?rec.published_profile:'NA')+'">'+profile+'</dd><dt>'+esc(T('기업 유형','Company type'))+'</dt><dd>'+typeChips(code,rs,ctx)+'</dd><dt>'+esc(T('최근 회계연도 말','Latest fiscal year end'))+'</dt><dd>'+fy+'</dd>'
  +'<dt>'+esc(T('실적 공시 예상 시기','Filing windows'))+'</dt><dd data-uc-filing-windows="NA">'+na(T('공개 sec-filing-windows.json은 TARGET 19개만 담습니다(504 공시 시기 미수집)','The public sec-filing-windows.json covers the 19 TARGET companies only (504 filing windows not collected)'),ctx.locale)+'</dd></dl>'+qgFresh(inputs,rs,ctx.locale,now);}
function chartCard(target,locale){const T=tr(locale),inScope=!!(target&&g.PrivateHistory&&g.PrivateHistory.symbolFor(target));
 return '<h2><span class="flow-number">2</span> '+esc(T('기술적 분석','Technical'))+'</h2>'+(inScope?'<div data-uc-chart-host></div>':'<p data-uc-chart="NA">'+na(T('일봉 차트의 가격 범위는 TARGET 19개입니다. 그 밖의 코드는 TA G2 결정 전이라 표시하지 않습니다.','The daily chart’s price scope is the 19 TARGET companies; other codes wait for the TA G2 decision.'),locale)+'</p>')
  +freshLine([T('가격은 이 기기에서만(공개 파일에 가격 없음)','Prices on this device only (public files carry none)')]);}
/* Company names of a page (also used by the TARGET page header in app.js). rec: a CompanyNames record, null (no record for this
   id) or undefined (names file not loaded). Shows the English (SEC) name, the Korean name with its status and source, aliases
   and the share class; a missing Korean name is said plainly (English name used), never invented. */
const KO_STATUS={OFFICIAL:['공식 한국어명','Official Korean name'],COMMON:['통용 한국어명(출처 기록)','Common Korean name (sourced)'],UNREGISTERED:['한국어명 미등록 · 영문명으로 표시','No Korean name registered · shown in English']};
function link(url,text){return /^https:\/\/[A-Za-z0-9.\-]+\//.test(url||'')?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(text)+'</a>':'';}
function namesHtml(rec,locale){const T=tr(locale),en=locale==='en-US';
 if(rec===undefined)return '<p class="small" data-company-names="NOT_LOADED">'+esc(T('기업명 자료를 불러오지 못했습니다 · 티커로 표시합니다','Company names not loaded · shown by ticker'))+'</p>';
 if(!rec)return '<p class="small" data-company-names="NO_RECORD">'+esc(T('기업명 기록 없음 · 티커로 표시합니다','No company-name record · shown by ticker'))+'</p>';
 const rows=[[T('영문명','English name'),'<span data-name-en="'+(rec.en_name?'PRESENT':'MISSING')+'">'+(rec.en_name?esc(rec.en_name)+' <span class="small">'+link(rec.en_source,rec.en_source&&rec.en_source.includes('sec.gov')?'SEC':T('출처','source'))+'</span>':esc(T('없음 · 이 코드의 SEC 이름이 없습니다','None · no SEC name for this code')))+'</span>'],
  [T('한국어명','Korean name'),'<span data-name-ko="'+esc(rec.ko_status)+'">'+(rec.ko_name?esc(rec.ko_name)+' · ':'')+esc(label(KO_STATUS,rec.ko_status,en))+(rec.ko_source?' · '+link(rec.ko_source,T('출처','source')):'')+'</span>']];
 if(rec.aliases.length)rows.push([T('별칭(검색)','Aliases (search)'),'<span data-name-aliases="'+rec.aliases.length+'">'+rec.aliases.map(a=>esc(a.text)).join(', ')+'</span>']);
 if(rec.share_class_note)rows.push([T('주식 종류','Share class'),'<span data-name-class="'+esc(rec.class_label)+'">'+esc(rec.share_class_note)+'</span>']);
 return '<dl class="kv uc-names" data-company-names="'+esc(rec.ko_status)+'">'+rows.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+v+'</dd>').join('')+'</dl><p class="small">'+esc(T('이름은 표시·검색에만 씁니다. QGV 계산·순위·기업 식별·기록은 바뀌지 않습니다.','Names are for display and search only; QGV calculation, ranking, identity and records do not change.'))+'</p>';}
function macroCard(locale){const T=tr(locale);return '<h2><span class="flow-number">3</span> '+esc(T('매크로','Macro'))+'</h2><p data-uc-macro="NA">'+na(T('기업별 매크로 노출이 아직 없습니다.','No per-company macro exposure yet.'),locale)+'</p>';}
/* Page HTML (synchronous: public files are already loaded by the app). ctx: {locale, screens, shares, quotes, now}. */
function html(code,ctx={}){
 const locale=ctx.locale==='en-US'?'en-US':'ko-KR',T=tr(locale),p=codeParts(code),now=finite(ctx.now)?ctx.now:Date.now(),c={...ctx,locale};
 if(!p)return '<p class="empty" data-universe-page="INVALID">NOT_AVAILABLE · INVALID_CODE</p>';
 const inputs=inputsOf(ctx.screens),rs=rowState(inputs,code),d=rs.rec?scored(code,c):null,target=targetIdOf(rs.rec),sh=sharesBlock(code,c);
 const logo=g.CompanyLogos&&g.CompanyLogos.html?g.CompanyLogos.html(code,40):'';
 const names=ctx.names&&typeof ctx.names.get==='function'?ctx.names.get(code):undefined,ES=g.EntitySearch,title=ES&&ES.companyTitle?ES.companyTitle(names||null,p.ticker,locale):p.ticker;
 const head='<a class="small" href="#companies">'+esc(T('← 기업 목록','← Companies'))+'</a><div class="eyebrow">UNIVERSE504</div><h1>'+logo+esc(title)+'</h1><p class="muted">'+esc(code)+'</p>'
  +'<p class="chips uc-chips"><span class="badge">Universe504</span><span class="badge" data-uc-name="'+esc(names?names.ko_status:names===null?'NO_RECORD':'NOT_LOADED')+'">'+esc(names?label(KO_STATUS,names.ko_status,locale==='en-US'):T('기업명 자료 없음','Names not loaded'))+'</span><span class="badge">'+esc(T('공개 파일에 가격 없음','No prices in public files'))+'</span>'+(rs.rec&&rs.rec.sic?'<span class="badge">SIC '+esc(rs.rec.sic)+'</span>':'')+'</p>'
  +namesHtml(names,locale)+(target?'<p class="small" data-uc-target="'+esc(target)+'"><a href="#company/'+encodeURIComponent(target)+'">'+esc(T('이 발행인은 TARGET 기업입니다 · TARGET 기업 페이지 →','This issuer is a TARGET company · open the TARGET page →'))+'</a></p>':'');
 const top=rs.state==='NO_FILE'||rs.state==='NOT_IN_FILE'?'<p class="small" data-uc-file="'+esc(rs.reason)+'">'+na(rs.reason==='SEC_QGV2_SCHEMA_NEWER'?T('자료 형식이 새 버전입니다. 새로고침하세요','The data format is newer. Reload the page'):rs.reason,locale)+'</p>':'';
 return '<div class="uc-page" data-universe-page="'+esc(code)+'" data-universe-state="'+esc(rs.state)+'" data-universe-reason="'+esc(rs.reason||'')+'" data-universe-v="PENDING">'+head+top
  +'<div class="uc-cards"><section class="card uc-card uc-card-q" data-universe-card="qgv">'+qgvCard(code,rs,d,inputs,c,now)+'</section><section class="card uc-card uc-card-g" data-universe-card="technical">'+chartCard(target,locale)+'</section><section class="card uc-card uc-card-v" data-universe-card="macro">'+macroCard(locale)+'</section></div>'
  +'<section class="card" data-universe-card="factors">'+factorsCard(rs,d,inputs,c,now)+'</section>'
  +(g.StatRadar?'<section class="card" data-universe-card="radar">'+g.StatRadar.html({code},{screens:ctx.screens,locale})+'</section>':'')
  +(g.StatRadar?'<section class="card" data-universe-card="financials"><h2>'+esc(T('재무 상세','Financial detail'))+'</h2><dl class="kv">'+g.StatRadar.marginDetail({code},{screens:ctx.screens,locale})+'</dl></section>':'')
  +'<section class="card" data-universe-card="classification">'+classificationCard(code,rs,inputs,c,now)+'</section>'
  +'<section class="card" data-universe-company="'+esc(sh.state)+'"><h2>'+esc(T('SEC 표지 정보','SEC cover facts'))+'</h2>'+sh.html+'<p class="small">'+esc(T('가격·시가총액·순위: 공개 화면에서는 NOT_AVAILABLE (GSQ-010). V와 종합 점수는 이 기기 시세로만 계산합니다.','Price, market cap and rank: NOT_AVAILABLE on public screens (GSQ-010). V and the total are computed only from this device’s quotes.'))+'</p></section></div>';
}
/* After html(): read this device's quotes for the code (existing V path, RAM only) and repaint the QGV and factor cards; mount the
   daily chart only for a code in its price scope. ctx adds {catalogPromise, config}. Stale mounts (re-render) stop silently. */
async function mount(host,ctx={}){
 const page=host&&host.querySelector?host.querySelector('[data-universe-page]'):null;if(!page)return;
 const code=page.dataset.universePage,locale=ctx.locale==='en-US'?'en-US':'ko-KR',inputs=inputsOf(ctx.screens),rs=rowState(inputs,code),target=targetIdOf(rs.rec),p=codeParts(code);
 const chartHost=page.querySelector('[data-uc-chart-host]');if(chartHost&&target&&g.PrivateHistory)try{void g.PrivateHistory.mount(chartHost,{companyId:target,locale,config:ctx.config||{}});}catch(_){}
 let quotes=object(ctx.quotes)?{...ctx.quotes}:{};
 if(inputs&&rs.rec&&p&&g.QgvScores&&g.QgvScores.collectQuotes){let catalog=null;try{catalog=await ctx.catalogPromise;}catch(_){catalog=null;}
  try{quotes={...quotes,...await g.QgvScores.collectQuotes(g,{identities:[{company_id:code,ticker:p.ticker}],v2Inputs:inputs,catalog})};}catch(_){}}
 if(!page.isConnected)return;
 const c={...ctx,locale,quotes},now=finite(ctx.now)?ctx.now:Date.now(),d=rs.rec?scored(code,c):null;
 const q=page.querySelector('[data-universe-card="qgv"]'),f=page.querySelector('[data-universe-card="factors"]');
 if(q)q.innerHTML=qgvCard(code,rs,d,inputs,c,now);if(f)f.innerHTML=factorsCard(rs,d,inputs,c,now);
 page.dataset.universeV=Object.hasOwn(quotes,code)?'DEVICE_PRICED':'NO_DEVICE_PRICE';
 if(g.StatRadar)await g.StatRadar.mount(page,{catalogPromise:ctx.catalogPromise});  // stat window: V from the shared page result (stat-radar.js)
}
return Object.freeze({html,mount,rowState,codeParts,namesHtml,SOURCE_REASON,GROUP_LABEL,PEER_LABEL});
});
