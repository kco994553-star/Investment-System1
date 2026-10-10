/* Native SVG daily candles and Research overlays. All values remain in the mounted device view. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TechnicalChart=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';const NS='http://www.w3.org/2000/svg';
 const positive=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
 function geometry(bars,overlays=[],average=null){
  const values=bars.flatMap(b=>[b.low,b.high,b.open,b.close]).filter(positive).concat(overlays.flatMap(a=>a.filter(x=>typeof x==='number'&&Number.isFinite(x))),positive(average)?[average]:[]);
  if(!values.length)return null;
  const scale=Math.max(...values.map(Math.abs)),minimum=Math.min(...values.map(v=>v/scale)),maximum=Math.max(...values.map(v=>v/scale)),spread=maximum-minimum||1;
  return {x:i=>20+i*600/Math.max(1,bars.length-1),y:v=>220-(v/scale-minimum)/spread*200,width:Math.max(1,Math.min(10,480/Math.max(1,bars.length))),minimum,maximum,scale};
 }
 function paths(values,g){const result=[];let points=[];const finish=()=>{if(points.length){result.push(points.length===1?points[0]+' L'+points[0].slice(1):points.join(' '));points=[];}};values.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){finish();return;}points.push((points.length?'L':'M')+g.x(i).toFixed(2)+','+g.y(v).toFixed(2));});finish();return result;}
 function render(host,{bars,indicators,selected,average=null,locale='ko-KR',trades=[]}){
  const doc=host.ownerDocument,svg=doc.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 640 240');svg.setAttribute('width','100%');svg.setAttribute('role','img');svg.setAttribute('aria-label',locale==='en-US'?'Daily raw candles · Research moving averages · Device AVG':'일봉 원시 캔들 · 연구용 이동평균 · 기기 AVG');svg.setAttribute('data-history-chart','');svg.setAttribute('data-role','RESEARCH_DISPLAY_ONLY');
  const lines=indicators.indicators.filter(x=>selected.has(x.indicator_id)),g=geometry(bars,lines.map(x=>x.values),selected.has('AVG')?average:null);if(!g){host.append(svg);return;}
  const node=(tag,attrs)=>{const n=doc.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));return n;};
  for(const ratio of [0,1]){const label=node('text',{x:635,y:ratio?30:218,'text-anchor':'end',class:'chart-axis'});label.textContent=((ratio?g.maximum:g.minimum)*g.scale).toLocaleString(locale,{maximumSignificantDigits:6});svg.append(label);}
  for(const i of [...new Set([0,Math.floor((bars.length-1)/2),bars.length-1])]){const label=node('text',{x:g.x(i),y:238,'text-anchor':i===0?'start':i===bars.length-1?'end':'middle',class:'chart-axis'});label.textContent=new Date(bars[i].timestamp*1000).toISOString().slice(0,10);svg.append(label);}
  bars.forEach((b,i)=>{if(![b.open,b.high,b.low,b.close].every(positive)||b.low>Math.min(b.open,b.close)||b.high<Math.max(b.open,b.close))return;const x=g.x(i),yo=g.y(b.open),yc=g.y(b.close),group=node('g',{'data-candle-index':i,'data-session':b.session_status,class:'daily-candle '+(b.close>=b.open?'candle-up':'candle-down')});group.append(node('path',{d:'M'+x.toFixed(2)+','+g.y(b.high).toFixed(2)+' L'+x.toFixed(2)+','+g.y(b.low).toFixed(2),fill:'none'}),node('rect',{x:(x-g.width/2).toFixed(2),y:Math.min(yo,yc).toFixed(2),width:g.width.toFixed(2),height:Math.max(.8,Math.abs(yc-yo)).toFixed(2)}));const title=node('title',{});title.textContent=new Date(b.timestamp*1000).toISOString().slice(0,10)+' · '+b.session_status;group.append(title);svg.append(group);});
  for(const item of lines)for(const d of paths(item.values,g))svg.append(node('path',{d,fill:'none',class:'research-line '+item.indicator_id.toLowerCase(),'data-indicator':item.indicator_id,'data-role':'RESEARCH_DISPLAY_ONLY'}));
  const markerCounts=new Map();
  for(const trade of trades){const b=bars[trade.bar_index];if(!b||!positive(b.low)||!positive(b.high)||!['B','S'].includes(trade.side))continue;const key=trade.bar_index+trade.side,count=markerCounts.get(key)||0;markerCounts.set(key,count+1);const label=node('text',{x:g.x(trade.bar_index),y:g.y(trade.side==='B'?b.low:b.high)+(trade.side==='B'?12+count*12:-8-count*12),'text-anchor':'middle',class:'trade-marker trade-'+trade.side.toLowerCase(),'data-trade-side':trade.side,'data-trade-date':trade.date,'data-role':'USER_DEVICE_ONLY'});label.textContent=trade.side;const title=node('title',{});title.textContent=trade.date+' · '+trade.side+' · '+trade.quantity+' · '+(locale==='en-US'?'Execution price not provided':'체결 가격 미제공');label.append(title);svg.append(label);}
  if(selected.has('AVG')&&positive(average))svg.append(node('path',{d:'M20,'+g.y(average).toFixed(2)+' L620,'+g.y(average).toFixed(2),fill:'none',class:'device-average','data-average-line':'','data-role':'USER_DEVICE_ONLY'}));
  host.append(svg);
 }
 return Object.freeze({geometry,paths,render});
});
