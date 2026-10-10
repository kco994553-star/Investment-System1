/* GSQ-015. Display calculations only; no storage, provider, QGV or model calls. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ResearchIndicators=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const ROLE='RESEARCH_DISPLAY_ONLY';
  const finite=x=>typeof x==='number'&&Number.isFinite(x), positive=x=>finite(x)&&x>0;
  function mean(xs){const scale=Math.max(...xs.map(Math.abs));return scale===0?0:xs.reduce((a,x)=>a+x/scale,0)/xs.length*scale;}
  const checked=x=>finite(x)?x:null;
  function series(name,values,reasons,visible=null){return Object.freeze({indicator_id:name,role:ROLE,values:Object.freeze(values),unavailable_reasons:Object.freeze(reasons),default_visible:visible,latest_state:values.at(-1)!==null&&values.length?'AVAILABLE':'NOT_AVAILABLE'});}
  function sma(xs,n){
    const values=[],reasons=[];let window=[];
    for(const x of xs){if(x===null)window=[];else{window.push(x);if(window.length>n)window.shift();}const v=window.length===n?checked(mean(window)):null;values.push(v);reasons.push(v!==null?null:window.length<n?'WARMUP':'CALCULATION_ERROR');}
    return [values,reasons];
  }
  function ema(xs,n){
    const values=[],reasons=[];let seed=[],previous=null;const alpha=2/(n+1);
    for(const x of xs){let v=null,reason='WARMUP';if(x===null){seed=[];previous=null;}else if(previous===null){seed.push(x);if(seed.length===n){v=checked(mean(seed));seed=[];previous=v;reason=v===null?'CALCULATION_ERROR':null;}}else{v=checked(previous+alpha*(x-previous));previous=v;reason=v===null?'CALCULATION_ERROR':null;}values.push(v);reasons.push(reason);}
    return [values,reasons];
  }
  function rsi(xs){
    const values=[],reasons=[];let prev=null,gains=[],losses=[],gain=null,loss=null;
    for(const x of xs){let v=null,reason='WARMUP';if(x===null){prev=null;gain=null;loss=null;gains=[];losses=[];}else if(prev!==null){const d=x-prev,g=Math.max(d,0),l=Math.max(-d,0);if(gain===null){gains.push(g);losses.push(l);if(gains.length===14){gain=mean(gains);loss=mean(losses);}}else{gain+=(g-gain)/14;loss+=(l-loss)/14;}
        if(gain!==null){const scale=Math.max(gain,loss);v=scale?checked(100*(gain/scale)/(gain/scale+loss/scale)):null;reason=v!==null?null:scale===0?'ZERO_TOTAL_CHANGE':'CALCULATION_ERROR';}}
      if(x!==null)prev=x;values.push(v);reasons.push(reason);
    }return [values,reasons];
  }
  function atr(bars,closes,basis){
    if(basis!=='RAW_CLOSE')return [bars.map(()=>null),bars.map(()=>'OHLC_BASIS_UNCONFIRMED')];
    const values=[],reasons=[];let seed=[],prev=null;
    bars.forEach((b,i)=>{let v=null,reason='WARMUP';if(closes[i]===null||!positive(b.high)||!positive(b.low)||b.high<b.low){seed=[];prev=null;reason='OHLC_MISSING';}else if(i===0||closes[i-1]===null){seed=[];prev=null;}else{const tr=checked(Math.max(b.high-b.low,Math.abs(b.high-closes[i-1]),Math.abs(b.low-closes[i-1])));if(tr===null){seed=[];prev=null;reason='CALCULATION_ERROR';}else if(prev===null){seed.push(tr);if(seed.length===14){v=checked(mean(seed));seed=[];prev=v;reason=v!==null?null:'CALCULATION_ERROR';}}else{v=checked(prev+(tr-prev)/14);prev=v;reason=v!==null?null:'CALCULATION_ERROR';}}values.push(v);reasons.push(reason);});return [values,reasons];
  }
  function unavailable(reason){return Object.freeze({role:ROLE,state:'NOT_AVAILABLE',reason_code:reason,indicators:Object.freeze([])});}
  function calculate(bars,{priceBasis='RAW_CLOSE',includeSma240=false}={}){
    if(typeof includeSma240!=='boolean')return unavailable('INVALID_DISPLAY_CONFIG');
    if(!['RAW_CLOSE','PROVIDER_ADJUSTED_CLOSE'].includes(priceBasis))return unavailable('BASIS_UNCONFIRMED');
    if(!Array.isArray(bars)||bars.length>1500)return unavailable('INVALID_DAILY_INPUT');
    let previous=0;
    for(const b of bars){if(!b||!Number.isSafeInteger(b.timestamp)||b.timestamp<=previous||!['COMPLETE','IN_PROGRESS','UNKNOWN'].includes(b.session_status))return unavailable('INVALID_DAILY_INPUT');previous=b.timestamp;
      for(const key of ['close','adjusted_close','open','high','low'])if(b[key]!==null&&!positive(b[key]))return unavailable('INVALID_DAILY_INPUT');
      if(positive(b.high)&&positive(b.low)&&b.high<b.low)return unavailable('INVALID_OHLC');
      if([b.open,b.high,b.low,b.close].every(positive)&&(b.open<b.low||b.open>b.high||b.close<b.low||b.close>b.high))return unavailable('INVALID_OHLC');
    }
    const prices=bars.map(b=>b.session_status==='COMPLETE'?b[priceBasis==='RAW_CLOSE'?'close':'adjusted_close']:null),items=[];
    for(const n of [5,20,60,120,...(includeSma240?[240]:[])])items.push(series('SMA_'+n,...sma(prices,n),n!==240));
    items.push(series('EMA_20',...ema(prices,20)),series('RSI_14',...rsi(prices)));
    const fast=ema(prices,12)[0],slow=ema(prices,26)[0],macd=prices.map((_,i)=>fast[i]===null||slow[i]===null?null:checked(fast[i]-slow[i])),mr=macd.map(x=>x===null?'WARMUP':null),[signal,sr]=ema(macd,9);
    const histogram=macd.map((x,i)=>x===null||signal[i]===null?null:checked(x-signal[i])),hr=histogram.map((x,i)=>x!==null?null:macd[i]===null?mr[i]:signal[i]===null?sr[i]:'CALCULATION_ERROR');
    items.push(series('MACD_12_26',macd,mr),series('MACD_SIGNAL_9',signal,sr),series('MACD_HISTOGRAM_12_26_9',histogram,hr));
    const [middle,br]=sma(prices,20),upper=[],lower=[],reasons=[];
    middle.forEach((m,i)=>{let u=null,l=null,reason=br[i];if(m!==null){const window=prices.slice(i-19,i+1),scale=Math.max(...window),sigma=Math.sqrt(window.reduce((a,x)=>a+(x/scale-m/scale)**2,0)/20)*scale;u=checked(m+2*sigma);l=checked(m-2*sigma);if(u===null||l===null){u=l=null;reason='CALCULATION_ERROR';}else reason=null;}upper.push(u);lower.push(l);reasons.push(reason);});
    items.push(series('BOLL_MIDDLE_20',middle,br),series('BOLL_UPPER_20_2',upper,reasons),series('BOLL_LOWER_20_2',lower,reasons.slice()),series('ATR_14',...atr(bars,prices,priceBasis)));
    return Object.freeze({role:ROLE,state:'INPUT_RESEARCH',price_basis:priceBasis,pit_status:'NOT_VERIFIED',indicators:Object.freeze(items)});
  }
  return Object.freeze({ROLE,calculate});
});
