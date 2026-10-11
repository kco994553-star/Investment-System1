/* Virtual trading set comparison (decision 2026-10-11): rule-based numeric table only, RAM only.
   Pure part mirrors qgv/virtual_trading_compare.py (vectors: tests/fixtures/virtual_trading_compare_v1.json).
   One row per metric, one column per set (Set A and the user sets B/C/D). Standard definitions only; a metric with fewer
   samples than its minimum is NA (never 0). No narrative fields (no strengths / weaknesses / watch items): the only
   interpretation is the one-line summary, written by the user's AI from the exported numbers (【AI】) or, without it,
   by the rule line. Prices, ledgers and amounts stay in memory; amounts on screen go through DailyReport.money (hidden by
   default). Virtual · not a recommendation · no order function. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading);if(node)module.exports=api;else root.VirtualTradingCompare=api;})(typeof globalThis==='object'?globalThis:this,function(engine){
'use strict';
const SCHEMA='virtual-trading-compare/1',SP500='SP500',TYPES=Object.freeze(['growth','quality','cyclical','defensive']);
// Minimum samples per metric (documented in ENGINE_V1.md). Hit rate keeps the engine's own D-12 minimum (30).
const MIN=Object.freeze({period_return:1,excess_return:1,capture_days:10,max_drawdown:20,volatility:20});
const CODES=Object.freeze(['INSUFFICIENT_SAMPLE','VALUATION_NOT_AVAILABLE','BENCHMARK_NOT_AVAILABLE','WEIGHTS_NOT_AVAILABLE','TYPES_NOT_AVAILABLE','LEDGER_NOT_AVAILABLE','COMPARE_NEEDS_TWO_SETS']);
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
/* Daily return on consecutive valued sessions: r_t = (V_t − deposit_t) / V_{t−1} − 1 (deposit-neutral, same form as the
   engine TWR). A day whose value or the previous day's value is NOT_AVAILABLE has no return (never 0). */
function dailyReturns(days){
 const out=[];
 for(let i=1;i<days.length;i++){const a=days[i-1],b=days[i];if(num(a.total_value)&&a.total_value>0&&num(b.total_value))out.push({date:b.date,prev:a.date,r:(b.total_value-b.deposit)/a.total_value-1});}
 return out;
}
function product(xs){let g=1;for(const x of xs)g=g*(1+x);return g-1;}
function mean(xs){let s=0;for(const x of xs)s+=x;return s/xs.length;}
function metrics({days=[],sp500=null,types=null,hits=null,summary=null}={}){
 const d=compareDays(days),rets=dailyReturns(d),last=d.length?d[d.length-1]:null,out={};
 out.value=last&&num(last.total_value)?ok(last.total_value,{date:last.date}):na(last?'VALUATION_NOT_AVAILABLE':'LEDGER_NOT_AVAILABLE');
 out.period_return=rets.length>=MIN.period_return?ok(product(rets.map(x=>x.r)),{samples:rets.length}):na('INSUFFICIENT_SAMPLE');
 // S&P 500 daily return on the same session pair (both closes present).
 const bench=object(sp500)?sp500:null,aligned=[];
 if(bench)for(const x of rets)if(num(bench[x.prev])&&num(bench[x.date])&&bench[x.prev]>0)aligned.push({r:x.r,b:bench[x.date]/bench[x.prev]-1});
 if(!bench)out.excess_return=na('BENCHMARK_NOT_AVAILABLE');
 else if(aligned.length<MIN.excess_return)out.excess_return=na('INSUFFICIENT_SAMPLE');
 else{const p=product(aligned.map(x=>x.r)),b=product(aligned.map(x=>x.b));out.excess_return=ok(p-b,{portfolio:p,benchmark:b,samples:aligned.length});}
 // Capture ratios (arithmetic mean form) on the S&P 500's up days and down days, ×100.
 const up=aligned.filter(x=>x.b>0),down=aligned.filter(x=>x.b<0);
 const capture=list=>!bench?na('BENCHMARK_NOT_AVAILABLE'):list.length<MIN.capture_days?na('INSUFFICIENT_SAMPLE'):ok(mean(list.map(x=>x.r))/mean(list.map(x=>x.b))*100,{samples:list.length});
 out.upside_capture=capture(up);out.downside_capture=capture(down);
 // Max drawdown on the deposit-neutral daily value index (W_0 = 1, W_t = W_{t−1}(1 + r_t)), ≤ 0.
 if(rets.length<MIN.max_drawdown)out.max_drawdown=na('INSUFFICIENT_SAMPLE');
 else{let w=1,peak=1,mdd=0;for(const x of rets){w=w*(1+x.r);if(w>peak)peak=w;const dd=w/peak-1;if(dd<mdd)mdd=dd;}out.max_drawdown=ok(mdd,{samples:rets.length});}
 // Volatility: sample standard deviation of daily returns × √252.
 if(rets.length<MIN.volatility)out.volatility=na('INSUFFICIENT_SAMPLE');
 else{const m=mean(rets.map(x=>x.r));let v=0;for(const x of rets)v+=(x.r-m)*(x.r-m);out.volatility=ok(Math.sqrt(v/(rets.length-1))*Math.sqrt(252),{samples:rets.length});}
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
 out.virtual_trades=object(summary)?ok({buy:summary.buy_count,sell:summary.sell_count},{hit20:h20?(h20.hit_rate===null?na('INSUFFICIENT_SAMPLE'):ok(h20.hit_rate,{samples:h20.samples})):na('INSUFFICIENT_SAMPLE')}):na('LEDGER_NOT_AVAILABLE');
 return out;
}
// Compare view from set entries [{id, kind, label, purpose, ledger, hits, input}] + public types → per-set metrics.
function build(entries,{types=null}={}){
 const sets=(Array.isArray(entries)?entries:[]).map(e=>{const L=e.input,ready=e.ledger&&e.ledger.state==='OK';
  return{id:e.id,kind:e.kind,label:e.label,purpose:e.purpose||null,state:ready?'OK':'NOT_AVAILABLE',reason_codes:ready?[]:(e.ledger?e.ledger.reason_codes:['LEDGER_NOT_AVAILABLE']),
   metrics:metrics({days:ready?e.ledger.days:[],sp500:L&&object(L.benchmarks)&&object(L.benchmarks[SP500])?L.benchmarks[SP500]:null,types,hits:e.hits,summary:ready?e.ledger.summary:null})};});
 return{schema:SCHEMA,state:sets.length>=2?'READY':'NOT_AVAILABLE',reason_codes:sets.length>=2?[]:['COMPARE_NEEDS_TWO_SETS'],sets};
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
 const x=m[key];if(!x||x.state!=='OK')return'N/A'+(x&&x.reason?' ('+(engine().codeLabel(x.reason)||x.reason)+')':'');
 if(key==='value')return money(x.value);
 if(key==='period_return'||key==='max_drawdown')return pct(x.value)+' · '+x.samples+'일';
 if(key==='excess_return')return pct(x.value,2)+' · '+x.samples+'일';
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
 h+='<p class="small">'+esc('규칙 기반 숫자 비교입니다. 일간 수익률 = (평가액 − 당일 입금) ÷ 전날 평가액 − 1, 평가액이 있는 연속 거래일만 사용. 기간 수익률 1일 이상, 상승·하락포착 각 10일 이상, 최대낙폭·변동성 20일 이상, D+20 적중률 30건 이상이 아니면 N/A입니다. 집중도는 마지막 거래일 상위 3종목 비중, 유형 노출은 공개 유형 소속도(0~1)로 가중한 비중입니다. 해석은 한 줄 요약에만 둡니다.')+'</p></section>';
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
return Object.freeze({SCHEMA,TYPES,MIN,CODES,ROWS,compareDays,dailyReturns,metrics,build,typesFrom,ruleLine,tableHtml,html,template});
});
