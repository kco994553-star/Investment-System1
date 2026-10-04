// Display only. No financial calculation, provider request or publication grant.
const {doc,rows}=window.CHART_DEMO;
const host=document.querySelector('#chart');const output=document.querySelector('#values');const status=document.querySelector('#status');
const chart=LightweightCharts.createChart(host,{autoSize:true,localization:{locale:'ko-KR'},layout:{fontFamily:'Noto Sans KR, sans-serif',background:{color:'#0e1624'},textColor:'#b7c9e0',attributionLogo:true},grid:{vertLines:{color:'#1d2b42'},horzLines:{color:'#1d2b42'}},timeScale:{timeVisible:false},rightPriceScale:{borderColor:'#344960'},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}});
const candles=chart.addSeries(LightweightCharts.CandlestickSeries,{upColor:'#55c7ae',downColor:'#ee8383',borderVisible:false,wickUpColor:'#55c7ae',wickDownColor:'#ee8383'});
const volume=chart.addSeries(LightweightCharts.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:'volume'});
candles.priceScale().applyOptions({scaleMargins:{top:0.08,bottom:0.3}});volume.priceScale().applyOptions({scaleMargins:{top:0.77,bottom:0}});
const byTime=new Map(rows.map(r=>[r.time,r]));
let active=false;let selectedIndex=-1;
const previous=document.querySelector('#previous');const next=document.querySelector('#next');
function showValue(r){
 output.textContent=r?`${new Date(r.time*1000).toISOString().slice(0,10)} UTC · O ${r.open??'미제공'} · H ${r.high??'미제공'} · L ${r.low??'미제공'} · C ${r.close??'미제공'} · V ${r.volume??'미제공'}`:'캔들 위로 이동하면 원본 OHLCV가 표시됩니다.';
}
function navigate(delta){
 if(!active)return;
 selectedIndex=Math.max(0,Math.min(rows.length-1,selectedIndex<0?(delta>0?0:rows.length-1):selectedIndex+delta));
 const r=rows[selectedIndex];showValue(r);
 if(r.close!==undefined)chart.setCrosshairPosition(r.close,r.time,candles);
}
previous.onclick=()=>navigate(-1);next.onclick=()=>navigate(1);
host.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();navigate(event.key==='ArrowLeft'?-1:1);}});
document.querySelector('#download').onclick=()=>{
 const url=URL.createObjectURL(new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='chart-contract-demo.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function setData(mode='all'){
 active=false;selectedIndex=-1;previous.disabled=true;next.disabled=true;chart.clearCrosshairPosition();showValue(null);
 if(doc.data_state!=='DEMO'||doc.synthetic!==true||mode==='blocked'){candles.setData([]);volume.setData([]);status.textContent='BLOCKED · 운영 publication이 활성화되지 않았습니다.';return;}
 const selected=mode==='empty'?[]:rows;
 candles.setData(selected.map(({volume,...r})=>r));
 volume.setData(selected.map(r=>({time:r.time,...(r.volume===null?{}:{value:r.volume,color:'#627fa8'})})));
 active=selected.length>0;previous.disabled=!active;next.disabled=!active;
 status.textContent=selected.length?`${selected.length}개 합성 point · 거래량 0은 0, 미확인은 미제공 · 실제 데이터 연결 전`:'EMPTY · 제공된 데이터가 없습니다.';
 chart.timeScale().fitContent();
}
chart.subscribeCrosshairMove(param=>{
 if(!active)return;
 const r=byTime.get(param.time);if(!r){if(selectedIndex<0)showValue(null);return;}
 selectedIndex=rows.indexOf(r);showValue(r);
});
document.querySelector('#all').onclick=()=>setData();document.querySelector('#last').onclick=()=>{setData();if(active)chart.timeScale().setVisibleLogicalRange({from:Math.max(0,rows.length-5),to:Math.max(0,rows.length-1)});};
document.querySelector('#empty').onclick=()=>setData('empty');document.querySelector('#blocked').onclick=()=>setData('blocked');
document.querySelector('#evidence').textContent=JSON.stringify(doc,null,2);
for(const p of doc.points){const tr=document.createElement('tr');for(const v of [p.time.slice(0,10),p.open,p.high,p.low,p.close,p.volume]){const td=document.createElement('td');td.textContent=v===null?'미제공':String(v);tr.append(td);}document.querySelector('#raw').append(tr);}
setData();
// Narrow read-only inspection hooks for deterministic browser acceptance of DEMO.
window.__chartLab={chart,candles,volume,rows,doc};
