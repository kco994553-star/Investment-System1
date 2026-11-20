// Pure contract reference for Main: injected byte reader, no fetch/DOM/indicator math.
import {decodeRecord} from './kis_compact_reader.mjs';
const CAP=1800000, SCOPE='OWNER_PRIVATE_ONLY';
const fields=['date','open','high','low','close','volume','amount'];
const indicators=['SMA_20','SMA_60','SMA_120','BOLL_MIDDLE_20','BOLL_UPPER_20_2',
  'BOLL_LOWER_20_2','RSI_14','MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9'];
const need=(ok,reason)=>{if(!ok)throw new Error(reason);};
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),
  v=>v.toString(16).padStart(2,'0')).join('');
async function slot(symbol){return String(parseInt((await hash(new TextEncoder().encode(symbol))).slice(0,2),16)%32).padStart(2,'0');}
function parse(bytes){
  need(bytes instanceof Uint8Array && bytes.byteLength<=CAP,'STOCK_FILE_LIMIT');
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
async function pinned(read,ref){
  need(ref && typeof ref.path==='string' && /^(stock|qgv)\/[A-Za-z0-9_./-]+\.json$/.test(ref.path) &&
    !ref.path.split('/').includes('..'),'STOCK_PATH');
  const bytes=await read(ref.path);
  need(bytes.byteLength===ref.bytes && await hash(bytes)===ref.sha256,'STOCK_FILE_PIN');
  return parse(bytes);
}
async function manifest(read){
  const m=parse(await read('manifest.json'));
  need(m.schema==='kis-private-delivery/3' && m.layout==='B2_STOCK_SERIES' &&
    m.publication_scope===SCOPE && m.buckets===32,'STOCK_MANIFEST_REQUIRED');
  return m;
}
export async function readStock(read,symbol){
  const m=await manifest(read), bucket=await slot(symbol);
  const packet=await pinned(read,m.stock_buckets.find(x=>x.bucket===bucket));
  need(packet.context.evaluation_day===m.evaluation_day,'STOCK_DATE_MISMATCH');
  const record=decodeRecord(packet,symbol), raw=[],values=[];
  for(const ref of record.pieces){
    const p=await pinned(read,ref);
    need(p.schema==='kis-stock-piece/1' && p.publication_scope===SCOPE && p.symbol===symbol &&
      JSON.stringify(p.fields)===JSON.stringify([...fields,...indicators]) &&
      p.basis===record.chart.basis && p.currency===record.chart.currency,'STOCK_PIECE_CONTEXT');
    need(p.rows.every(v=>v.length===17),'STOCK_ROW_WIDTH');
    values.push(...p.rows);
    if(record.chart.basis==='SPLIT_ADJUSTED'){
      need(p.raw_rows?.length===p.rows.length && p.raw_rows.every(v=>v.length===7),'STOCK_RAW_ROW_WIDTH');
      raw.push(...p.raw_rows);
    }
  }
  raw.sort((a,b)=>a[0].localeCompare(b[0]));
  values.sort((a,b)=>a[0].localeCompare(b[0]));
  const days=values.map(v=>v[0]);
  need(new Set(days).size===days.length && days.every(d=>d<=m.evaluation_day),'STOCK_SESSION_SET');
  const out={schema:'kis-stock-view/1',publication_scope:SCOPE,symbol,evaluation_day:m.evaluation_day,
    chart:{...record.chart,schema:'kis-chart-metadata/1'},fields:[...fields,...indicators],rows:values,
    indicators:record.indicators,latest:record.latest,
    coverage:{scope:'ALL_RETAINED_SESSIONS',retained_sessions:days.length,
      retained_start:days[0]??null,retained_end:days.at(-1)??null},
    additional_requests_for_toggle:0,additional_requests_for_retained_period:0};
  if(record.chart.basis==='SPLIT_ADJUSTED'){
    need(raw.every((v,i)=>v[0]===days[i]),'STOCK_RAW_SESSION_SET');
    out.raw_fields=fields;out.raw_rows=raw;
  }
  need(new TextEncoder().encode(JSON.stringify(out)).length<=CAP,'STOCK_RESPONSE_LIMIT');
  return out;
}
export async function readQgvRow(read,code){
  const m=await manifest(read), bucket=await slot(code);
  const packet=await pinned(read,m.qgv_buckets.find(x=>x.bucket===bucket));
  const context=await pinned(read,m.qgv_context);
  return {context,row:decodeRecord(packet,code)};
}
