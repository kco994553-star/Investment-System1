/* Virtual trading set comparison (decision 2026-10-11): rule-based numeric table only, RAM only.
   Pure part mirrors qgv/virtual_trading_compare.py (vectors: tests/fixtures/virtual_trading_compare_v1.json).
   One row per metric, one column per set (Set A and the user sets B/C/D). The return series are those of S17 ⑫⑬
   (ReportBenchmarks: SPY session calendar, one currency basis — KRW by default, US index × same-session KRW=X —, the
   engine time-weighted ledger chain, every missing close / rate / value a gap, never interpolated or carried). Standard
   definitions only; a metric with fewer samples than its minimum is NA (never 0). No narrative fields (no strengths /
   weaknesses / watch items): the only interpretation is the one-line summary, written by the user's AI from the exported
   numbers (【AI】) or, without it, by the rule line. Amounts on screen go through DailyReport.money (hidden by default).
   Virtual · not a recommendation · no order function. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading,node?()=>require('./report-benchmarks.js'):()=>root.ReportBenchmarks);if(node)module.exports=api;else root.VirtualTradingCompare=api;})(typeof globalThis==='object'?globalThis:this,function(engine,benchmarks){
'use strict';
const SCHEMA='virtual-trading-compare/1',TYPES=Object.freeze(['growth','quality','cyclical','defensive']);
// Minimum samples per metric (documented in ENGINE_V1.md). Hit rate keeps the engine's own D-12 minimum (30).
const MIN=Object.freeze({capture_days:20,max_drawdown:20,volatility:20});
const CODES=Object.freeze(['INSUFFICIENT_SAMPLE','VALUATION_NOT_AVAILABLE','WEIGHTS_NOT_AVAILABLE','TYPES_NOT_AVAILABLE','LEDGER_NOT_AVAILABLE','COMPARE_NEEDS_TWO_SETS']);
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const na=reason=>({state:'NOT_AVAILABLE',value:null,reason});
const ok=(value,extra={})=>({state:'OK',value,reason:null,...extra});

/* Engine days → the price-free compare days: date, total value (null = NOT_AVAILABLE), deposit, the held companies'
   weights (% of total) and whether every held company had its own close and FX on that day. */
function compareDays(days){
 return (Array.isArray(days)?days:[]).map(d=>{const w={},j=object(d.judgements)?d.judgements:{};let priced=true;
  for(const cid of Object.keys(j).sort()){const x=j[cid];if(!x.held)continue;w[cid]=x.actual_weight;
   if((x.reason_codes||[]).includes('DATA_PRICE_MISSING')||(x.reason_codes||[]).includes('DATA_FX_MISSING'))priced=false;}
  return{date:d.date,total_value:num(d.total_value)?d.total_value:null,deposit:d.deposit,weights:w,priced};});
}
/* Daily returns from index levels (⑬ points, gaps null) on consecutive sessions of the period window: r = P_i / P_{i−1} − 1
   when both levels exist. The base → first-session link is left out (no capital before the ledger's first day). */
function pointReturns(points){const out=[];for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i];out.push(num(a)&&num(b)&&a>0?b/a-1:null);}return out;}
function mean(xs){let s=0;for(const x of xs)s+=x;return s/xs.length;}
/* Metrics for one set. days: engine days; indices/sources: runner result.indices / sources (SPY, ⑬ ETFs, KRW=X);
   basis: ⑫⑬ currency basis. Period return and excess are ReportBenchmarks ⑫ SINCE_START (the set's own start). */
function metrics({days=[],indices={},sources={},basis='KRW',types=null,hits=null,summary=null}={}){
 const d=compareDays(days),last=d.length?d[d.length-1]:null,out={};
 out.value=last&&num(last.total_value)?ok(last.total_value,{date:last.date}):na(last?'VALUATION_NOT_AVAILABLE':'LEDGER_NOT_AVAILABLE');
 const rb=benchmarks().build({indices,sources,ledgers:[{key:'SET',state:d.length?'OK':'NOT_AVAILABLE',reason_codes:d.length?[]:['LEDGER_NOT_AVAILABLE'],days:d.map(x=>({date:x.date,total_value:x.total_value,deposit:x.deposit}))}],period:'SINCE_START',basis});
 const row=rb.periods.find(p=>p.period==='SINCE_START');
 if(!d.length){out.period_return=na('LEDGER_NOT_AVAILABLE');out.excess_return=na('LEDGER_NOT_AVAILABLE');}
 else if(!row||row.state!=='OK'){const r=row?row.reason:rb.reason;out.period_return=na(r);out.excess_return=na(r);}
 else{
  out.period_return=row.target.state==='OK'?ok(row.target.return,{start:row.start,end:row.end}):na(row.target.reason);
  out.excess_return=row.excess===null?na(row.target.state!=='OK'?row.target.reason:row.sp500.reason):ok(row.excess,{portfolio:row.target.return,benchmark:row.sp500.return});
 }
 const dash=rb.dashboard,series=dash&&dash.state==='OK'?dash.series:[];
 const ledger=series.find(s=>s.kind==='LEDGER'),spy=series.find(s=>s.key==='SP500');
 const r=ledger?pointReturns(ledger.points):[],b=spy?pointReturns(spy.points):[];
 const rets=r.filter(num),aligned=[];for(let i=0;i<r.length;i++)if(num(r[i])&&num(b[i]))aligned.push({r:r[i],b:b[i]});
 // Capture ratios (arithmetic mean form) on the S&P 500's up days and down days, ×100.
 const capture=list=>list.length<MIN.capture_days?na('INSUFFICIENT_SAMPLE'):ok(mean(list.map(x=>x.r))/mean(list.map(x=>x.b))*100,{samples:list.length});
 out.upside_capture=capture(aligned.filter(x=>x.b>0));out.downside_capture=capture(aligned.filter(x=>x.b<0));
 // Max drawdown on the ⑬ ledger index levels (time-weighted, deposit-neutral), ≤ 0; gaps are skipped, never filled.
 if(rets.length<MIN.max_drawdown)out.max_drawdown=na('INSUFFICIENT_SAMPLE');
 else{let peak=null,mdd=0;for(const p of ledger.points){if(!num(p))continue;if(peak===null||p>peak)peak=p;const dd=p/peak-1;if(dd<mdd)mdd=dd;}out.max_drawdown=ok(mdd,{samples:rets.length});}
 // Volatility: sample standard deviation of daily returns × √252.
 if(rets.length<MIN.volatility)out.volatility=na('INSUFFICIENT_SAMPLE');
 else{const m=mean(rets);let v=0;for(const x of rets)v+=(x-m)*(x-m);out.volatility=ok(Math.sqrt(v/(rets.length-1))*Math.sqrt(252),{samples:rets.length});}
 // Concentration: top-3 holding weight (% of total value) on the last session; NA when that day is not fully priced.
 const weighted=last&&num(last.total_value)&&last.priced;
 if(!weighted)out.concentration=na(last?'WEIGHTS_NOT_AVAILABLE':'LEDGER_NOT_AVAILABLE');
 else{const ws=Object.values(last.weights).sort((a,b)=>b-a);let top=0;for(const x of ws.slice(0,3))top+=x;out.concentration=ok(top,{holdings:ws.length});}
 // Type exposure: Σ weight × public membership (0–1) per type; holdings without a public membership (ETFs included) are unclassified.
 if(!weighted)out.type_exposure=na(last?'WEIGHTS_NOT_AVAILABLE':'LEDGER_NOT_AVAILABLE');
 else if(!object(types))out.type_exposure=na('TYPES_NOT_AVAILABLE');
 else{const e={};for(const t of TYPES)e[t]=0;let unclassified=0;
  for(const cid of Object.keys(last.weights).sort()){const w=last.weights[cid],m=own(types,cid)&&object(types[cid])?types[cid]:null;
   const known=m?TYPES.filter(t=>num(m[t])):[];if(!known.length){unclassified+=w;continue;}for(const t of known)e[t]+=w*m[t];}
  out.type_exposure=ok(e,{unclassified});}
 // Virtual trading: counts from the engine summary; D+20 hit rate from the engine's own check (D-12 minimum 30).
 const h20=Array.isArray(hits)?hits.find(h=>h.window===20):null;
 out.virtual_trades=object(summary)?ok({buy:summary.buy_count,sell:summary.sell_count},{hit20:h20&&h20.hit_rate!==null?ok(h20.hit_rate,{samples:h20.samples}):na('INSUFFICIENT_SAMPLE')}):na('LEDGER_NOT_AVAILABLE');
 return out;
}
// Compare view from set entries [{id, kind, label, purpose, ledger, hits}] + the runner's indices/sources + public types.
function build(entries,{indices={},sources={},basis='KRW',types=null}={}){
 const sets=(Array.isArray(entries)?entries:[]).map(e=>{const ready=!!(e.ledger&&e.ledger.state==='OK');
  return{id:e.id,kind:e.kind,label:e.label,purpose:e.purpose||null,state:ready?'OK':'NOT_AVAILABLE',reason_codes:ready?[]:(e.ledger?e.ledger.reason_codes:['LEDGER_NOT_AVAILABLE']),
   metrics:metrics({days:ready?e.ledger.days:[],indices,sources,basis,types,hits:e.hits,summary:ready?e.ledger.summary:null})};});
 return{schema:SCHEMA,basis,state:sets.length>=2?'READY':'NOT_AVAILABLE',reason_codes:sets.length>=2?[]:['COMPARE_NEEDS_TWO_SETS'],sets};
}
// Public company-types-pricefree.json → {cid: memberships} (price-free); null when not published.
function typesFrom(payload){try{const rows=payload.data.companies,out={};for(const cid of Object.keys(rows).sort()){const r=rows[cid];if(object(r)&&object(r.memberships))out[cid]=r.memberships;}return out;}catch(_){return null;}}

/* ---------- screen / export ---------- */
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=(v,d=2)=>num(v)?(v>0?'+':v<0?'−':'')+Math.abs(v*100).toFixed(d)+'%':'N/A';
const pctPlain=(v,d=1)=>num(v)?v.toFixed(d)+'%':'N/A';
const ratio=v=>num(v)?v.toFixed(1):'N/A';
const TYPE_KO={growth:'성장',quality:'품질',cyclical:'경기민감',defensive:'방어'};
const ROWS=Object.freeze([
 ['value','평가액'],['period_return','기간 수익률'],['excess_return','S&P 500 대비 초과'],['concentration','집중도(상위 3종목 비중)'],['type_exposure','유형 노출'],
 ['upside_capture','상승포착(S&P 500 상승일)'],['downside_capture','하락포착(S&P 500 하락일, 낮을수록 방어)'],['max_drawdown','최대낙폭'],['volatility','변동성(연율)'],['virtual_trades','가상매매 성과']]);
function cell(key,m,money){
 const x=m[key];if(!x||x.state!=='OK')return'N/A'+(x&&x.reason?' ('+(engine().codeLabel(x.reason)||benchmarks().codeLabel(x.reason)||x.reason)+')':'');
 if(key==='value')return money(x.value);
 if(key==='period_return')return pct(x.value)+' · '+x.start+'~'+x.end;
 if(key==='max_drawdown')return pct(x.value)+' · '+x.samples+'일';
 if(key==='excess_return')return pct(x.value,2)+' (S&P 500 '+pct(x.benchmark)+')';
 if(key==='volatility')return pct(x.value,1).replace('+','')+' · '+x.samples+'일';
 if(key==='upside_capture'||key==='downside_capture')return ratio(x.value)+' · '+x.samples+'일';
 if(key==='concentration')return pctPlain(x.value)+' · '+x.holdings+'종목';
 if(key==='type_exposure')return TYPES.map(t=>TYPE_KO[t]+' '+pctPlain(x.value[t])).join(' · ')+' · 미분류 '+pctPlain(x.unclassified);
 if(key==='virtual_trades'){const h=x.hit20;return'가상 매수 '+x.value.buy+'건 · 가상 매도 '+x.value.sell+'건 · D+20 적중률 '+(h.state==='OK'?pct(h.value,1).replace('+','')+'('+h.samples+'건)':'N/A (표본 30건 미만)');}
 return'N/A';
}
// Rule line (no AI): the best period return and the lowest volatility among sets with a value; NA otherwise.
function ruleLine(view){
 const best=(key,dir)=>{const c=view.sets.filter(s=>s.metrics[key].state==='OK');if(!c.length)return null;return c.reduce((a,b)=>dir*(b.metrics[key].value-a.metrics[key].value)>0?b:a);};
 const r=best('period_return',1),v=best('volatility',-1);
 const parts=[];if(r)parts.push('기간 수익률 최고 '+r.label+'('+pct(r.metrics.period_return.value)+')');if(v)parts.push('변동성 최저 '+v.label+'('+pct(v.metrics.volatility.value,1).replace('+','')+')');
 return parts.length?parts.join(' · '):'표본 부족으로 비교 판정 없음(N/A)';
}
// Numeric table (screen). picked: set ids shown (phone: 2–3 chosen; PC: all).
function tableHtml(view,{money=v=>'N/A',picked=null}={}){
 const sets=view.sets.filter(s=>!picked||picked.includes(s.id));
 let h='<div class="table-scroll"><table data-compare-table><thead><tr><th>지표</th>'+sets.map(s=>'<th data-compare-set="'+esc(s.id)+'">'+esc(s.label)+'</th>').join('')+'</tr></thead><tbody>';
 h+='<tr data-compare-row="purpose"><td>목적</td>'+sets.map(s=>'<td class="small">'+esc(s.purpose||(s.kind==='SET_A'?'v1.1 예시':'N/A'))+'</td>').join('')+'</tr>';
 for(const[key,name]of ROWS)h+='<tr data-compare-row="'+key+'"><td>'+esc(name)+'</td>'+sets.map(s=>'<td data-compare-cell="'+esc(s.id+':'+key)+'" data-state="'+(s.metrics[key]&&s.metrics[key].state)+'">'+esc(cell(key,s.metrics,money))+'</td>').join('')+'</tr>';
 return h+'</tbody></table></div>';
}
function html(view,{money=v=>'N/A',picked=null,wide=true,locale='ko-KR'}={}){
 const VT=engine();
 let h='<section class="card" data-compare data-compare-state="'+esc(view.state)+'" data-compare-layout="'+(wide?'PC':'PHONE')+'"><h2>세트 비교 '+VT.disclaimerHtml(locale)+'</h2>';
 if(view.state!=='READY')return h+'<p data-compare-na>'+esc('NOT_AVAILABLE · 비교는 세트가 2개 이상일 때 보입니다(세트 A + 사용자 세트 1개 이상).')+'</p></section>';
 if(!wide)h+='<fieldset data-compare-picker><legend class="small">비교할 세트 2~3개 선택</legend>'+view.sets.map(s=>'<label class="toggle"><input type="checkbox" data-compare-pick="'+esc(s.id)+'"'+(picked&&picked.includes(s.id)?' checked':'')+'> '+esc(s.label)+'</label>').join('')+'</fieldset>';
 h+=tableHtml(view,{money,picked:wide?null:picked});
 h+='<p data-compare-summary>'+esc('한 줄 요약: 【규칙】 '+ruleLine(view))+'</p>';
 h+='<p class="small">'+esc('규칙 기반 숫자 비교입니다. 수익률은 ⑫⑬과 같은 계산(S&P 500 세션 기준, '+(view.basis==='USD'?'달러':'원화')+' 기준, 입금 제외 시간가중, 결측은 비우고 채우지 않음)이며 기간은 세트마다 장부 시작 이후입니다. 일간 수익률은 값이 있는 연속 거래일만 씁니다. 상승·하락포착 각 20일 이상, 최대낙폭·변동성 20일 이상, D+20 적중률 30건 이상이 아니면 N/A입니다. 집중도는 마지막 거래일 상위 3종목 비중, 유형 노출은 공개 유형 소속도(0~1)로 가중한 비중입니다. 해석은 한 줄 요약에만 둡니다.')+'</p></section>';
 return h;
}
// Export text: the numbers with amounts through the same money function, and one 【AI】 line only.
function template(view,{money=v=>'[숨김]',reportDate=null}={}){
 const VT=engine(),L=['[세트 비교 템플릿] '+VT.DISCLAIMER.ko,'보고일 '+(reportDate||'N/A'),''];
 if(view.state!=='READY')return L.concat(['NOT_AVAILABLE · 세트 2개 이상 필요'],'').join('\n')+'\n';
 L.push('| 지표 | '+view.sets.map(s=>s.label).join(' | ')+' |','|---|'+view.sets.map(()=>'---|').join(''));
 L.push('| 목적 | '+view.sets.map(s=>s.purpose||(s.kind==='SET_A'?'v1.1 예시':'N/A')).join(' | ')+' |');
 for(const[key,name]of ROWS)L.push('| '+name+' | '+view.sets.map(s=>cell(key,s.metrics,money)).join(' | ')+' |');
 L.push('','한 줄 요약: 【AI】 (없으면 【규칙】 '+ruleLine(view)+')');
 return L.join('\n')+'\n';
}
return Object.freeze({SCHEMA,TYPES,MIN,CODES,ROWS,compareDays,pointReturns,metrics,build,typesFrom,ruleLine,tableHtml,html,template});
});
