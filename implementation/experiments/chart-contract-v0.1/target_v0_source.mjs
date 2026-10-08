// Bounded YAML 1.2 subset for this immutable user file, not a general YAML loader.
// Block maps/sequences and scalar-only flow maps are accepted; all other syntax fails closed.
import {createHash} from 'node:crypto';
import {renderPortfolioInput} from './portfolio_contract.mjs';

export const TARGET_V0_SHA256='a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b';
export const TARGET_V0_SOURCE_PATH='implementation/docs/portfolio_target_owner/TARGET_v0.yaml';
const fail=message=>{throw new Error('TARGET v0: '+message);};
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');

function unquotedParts(value,delimiter){
 const parts=[];let start=0,quote=null;
 for(let i=0;i<value.length;i++){
  const c=value[i];
  if(quote==='"'&&c==='\\'){i++;continue;}
  if(quote==="'"&&c==="'"&&value[i+1]==="'"){i++;continue;}
  if(quote){if(c===quote)quote=null;continue;}
  if(c==='"'||c==="'"){quote=c;continue;}
  if(c===delimiter){parts.push(value.slice(start,i));start=i+1;}
 }
 if(quote)fail('unclosed quote');
 parts.push(value.slice(start));return parts;
}
function stripComment(line){
 let quote=null;
 for(let i=0;i<line.length;i++){
  const c=line[i];
  if(quote==='"'&&c==='\\'){i++;continue;}
  if(quote==="'"&&c==="'"&&line[i+1]==="'"){i++;continue;}
  if(quote){if(c===quote)quote=null;continue;}
  if(c==='"'||c==="'"){quote=c;continue;}
  if(c==='#'&&(i===0||/\s/.test(line[i-1])))return line.slice(0,i);
 }
 if(quote)fail('unclosed quote');return line;
}
function scalar(raw){
 const s=raw.trim();if(!s)fail('empty scalar');
 if(s.startsWith('"')){try{const v=JSON.parse(s);if(typeof v!=='string')fail('quoted scalar must be a string');return v;}catch{fail('invalid quoted scalar');}}
 if(s.startsWith("'")){if(!/^'(?:[^']|'')*'$/.test(s))fail('invalid single quote');return s.slice(1,-1).replaceAll("''","'");}
 if(/^[&*!>|\[\]{}]/.test(s)||/^(?:null|true|false|~)$/i.test(s)||/:\s|\s#/.test(s))fail('unsupported YAML scalar');
 if(/^-?(?:0|[1-9]\d*)$/.test(s))return Number(s);
 return s;
}
function keyValue(s){
 const m=/^([a-z_]+):(?:\s+(.*))?$/.exec(s);if(!m)fail('unexpected mapping field or indentation');
 return [m[1],m[2]??''];
}
function set(map,key,value){if(Object.hasOwn(map,key))fail('duplicate field '+key);map[key]=value;}
function flowMap(raw){
 if(!raw.startsWith('{')||!raw.endsWith('}'))fail('unsupported flow map');
 const out=Object.create(null);
 for(const part of unquotedParts(raw.slice(1,-1),',')){
  if(!part.trim())fail('empty flow map field');
  const [key,value]=keyValue(part.trim());set(out,key,scalar(value));
 }
 return out;
}

export function parseTargetV0Yaml(text){
 if(typeof text!=='string'||text.includes('\t')||text.includes('\r'))fail('tabs/unsupported indentation or line endings');
 const lines=text.split('\n').map((line,i)=>({s:stripComment(line).trimEnd(),line:i+1})).filter(l=>l.s.trim());
 for(const l of lines){l.indent=l.s.length-l.s.trimStart().length;l.s=l.s.trimStart();if(l.indent%2)fail('unexpected indentation');}
 let cursor=0;
 function field(map,line,indent){
  const [key,value]=keyValue(line.s);cursor++;
  if(value){set(map,key,scalar(value));return;}
  if(!lines[cursor]||lines[cursor].indent<=indent)fail('missing mapping value '+key);
  set(map,key,block(lines[cursor].indent));
 }
 function block(indent){
  if(!lines[cursor]||lines[cursor].indent!==indent)fail('unexpected indentation');
  if(lines[cursor].s.startsWith('- ')){
   const list=[];
   while(lines[cursor]?.indent===indent&&lines[cursor].s.startsWith('- ')){
    const item=lines[cursor].s.slice(2);
    if(item.startsWith('{')){list.push(flowMap(item));cursor++;}
    else{
     const map=Object.create(null);field(map,{s:item},indent+2);
     while(lines[cursor]?.indent===indent+2&&!lines[cursor].s.startsWith('- '))field(map,lines[cursor],indent+2);
     list.push(map);
    }
    if(lines[cursor]?.indent>indent)fail('unexpected sequence indentation');
   }
   return list;
  }
  const map=Object.create(null);
  while(lines[cursor]?.indent===indent&&!lines[cursor].s.startsWith('- '))field(map,lines[cursor],indent);
  if(lines[cursor]?.indent>indent)fail('unexpected mapping indentation');
  return map;
 }
 if(!lines.length||lines[0].indent!==0)fail('missing root mapping');
 const source=block(0);if(cursor!==lines.length)fail('unexpected trailing YAML');
 validate(source);return source;
}
function fields(obj,expected,where){
 if(!obj||Array.isArray(obj)||typeof obj!=='object')fail('mapping required '+where);
 for(const k of expected)if(!Object.hasOwn(obj,k))fail('missing '+where+'.'+k);
 for(const k of Object.keys(obj))if(!expected.includes(k))fail('unknown field '+where+'.'+k);
}
function string(s,where){if(typeof s!=='string'||!s.length||s!==s.trim())fail('string required '+where);}
function integer(n,where){if(!Number.isSafeInteger(n)||n<0)fail('nonnegative safe integer required '+where);}
function utc(value,where){
 string(value,where);
 const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(Z|[+-]\d{2}:\d{2})$/.exec(value);
 if(!m)fail('timezone-aware timestamp required '+where);
 const local=Date.parse(m[1]+'T'+m[2]+'Z'),stamp=Date.parse(value);
 if(!Number.isFinite(local)||!Number.isFinite(stamp)||new Date(local).toISOString().slice(0,19)!==m[1]+'T'+m[2])fail('invalid timestamp '+where);
 return new Date(stamp).toISOString().replace('.000Z','Z');
}
function validate(d){
 fields(d,['schema','version','status','owner','provenance','effective_at','available_at','unit','total_units','cash_units','themes'],'root');
 if(d.schema!=='PORTFOLIO_TARGET/0.1'||d.version!=='v0'||d.status!=='ADOPTED'||d.unit!=='weight_units')fail('unsupported schema/version/status/unit');
 fields(d.owner,['role','note'],'owner');if(d.owner.role!=='USER')fail('USER owner required');string(d.owner.note,'owner.note');
 fields(d.provenance,['derived_from','adopted_by','adopted_at','adoption_note'],'provenance');
 if(d.provenance.adopted_by!=='USER')fail('USER adoption required');
 string(d.provenance.derived_from,'provenance.derived_from');string(d.provenance.adoption_note,'provenance.adoption_note');
 const adopted=utc(d.provenance.adopted_at,'adopted clock'),effective=utc(d.effective_at,'effective clock'),available=utc(d.available_at,'available clock');
 if(effective!==adopted||available!==adopted)fail('clock differs from adoption; no backdating');
 integer(d.total_units,'total_units');integer(d.cash_units,'cash_units');
 if(d.total_units!==10000||d.cash_units!==0)fail('v0 explicit total10000/cash0 required');
 if(!Array.isArray(d.themes)||d.themes.length!==4)fail('four themes required');
 const ids=new Set(),members=new Set();let count=0,total=d.cash_units;
 for(const t of d.themes){
  fields(t,['theme_id','label','target_units','holdings'],'theme');string(t.theme_id,'theme_id');string(t.label,'theme.label');
  if(ids.has(t.theme_id))fail('duplicate theme concept');ids.add(t.theme_id);integer(t.target_units,'target_units');
  if(!Array.isArray(t.holdings)||!t.holdings.length)fail('theme holdings required');let subtotal=0;
  for(const h of t.holdings){
   fields(h,['label','ticker_hint','listing','weight_units'],'holding');
   for(const k of ['label','ticker_hint','listing'])string(h[k],'holding.'+k);
   integer(h.weight_units,'weight_units');
   if(h.listing!=='UNRESOLVED_BY_AGENT'&&!h.listing.startsWith('USER_DECIDED: '))fail('unsupported listing source role');
   const key=JSON.stringify([h.label,h.ticker_hint]);if(members.has(key))fail('duplicate source member');members.add(key);
   subtotal+=h.weight_units;if(!Number.isSafeInteger(subtotal))fail('integer subtotal overflow');count++;
  }
  if(subtotal!==t.target_units)fail('theme subtotal differs from supplied target_units');total+=t.target_units;
 }
 if(count!==19)fail('exact19 source rows required');if(total!==d.total_units)fail('source total and cash differ');
}

export function projectTargetV0(bytes,mapping,{observed_at,source_path=TARGET_V0_SOURCE_PATH}={}){
 const buffer=Buffer.isBuffer(bytes)?bytes:Buffer.from(bytes),sourceHash=hash(buffer);
 if(sourceHash!==TARGET_V0_SHA256)fail('source bytes sha256 differs from immutable adopted file');
 const d=parseTargetV0Yaml(buffer.toString('utf8')),observed=utc(observed_at,'observation clock');
 const available=utc(d.available_at,'available clock');if(Date.parse(observed)<Date.parse(available))fail('observation precedes source availability');
 const sourceRows=d.themes.flatMap((t,ti)=>t.holdings.map((h,hi)=>({source_pointer:`/themes/${ti}/holdings/${hi}`,theme_id:t.theme_id,theme_label:t.label,...h,security_id:null})));
 const mapSource=mapping?.user_target_source??mapping?.source;
 if(mapSource?.sha256!==sourceHash)fail('mapping source hash differs');
 if(!Array.isArray(mapping.rows)||mapping.rows.length!==19)fail('mapping must cover exact19 source rows');
 const byPointer=new Map();
 for(const row of mapping.rows){
  const pointer=row.user_source_pointer??row.source_pointer;
  if(typeof pointer!=='string'||byPointer.has(pointer)||row.security_id!==null||row.status!=='UNRESOLVED')fail('mapping identity incomplete or fabricated');
  byPointer.set(pointer,row);
 }
 for(const row of sourceRows){
  const mapped=byPointer.get(row.source_pointer),input=mapped?.owner_listing_input??mapped?.source_row;
  if(!mapped||!input||['label','ticker_hint','listing','weight_units'].some(k=>input[k]!==row[k]))fail('mapping source row differs');
 }
 const input={snapshot_id:`source:${d.schema}:${d.version}:sha256:${sourceHash}`,portfolio_version:'TARGET v0',qgv_version:'NOT_AVAILABLE',as_of:observed,source:`USER · ${source_path} · sha256:${sourceHash}`,weight_basis:'TARGET',data_kind:'USER_SPEC_REFERENCE',total_units:d.total_units,cash_units:d.cash_units,type_catalog:[],classification:{version:`${d.schema}/${d.version}/USER_DEFINED_STRATEGY_THEME_PORTFOLIO_BUCKET`,source:source_path,available_at:available},holdings:sourceRows.map(r=>({holding_id:r.source_pointer,security_id:null,label:r.label,weight_units:r.weight_units,industry:r.theme_label,types:null}))};
 const projection=renderPortfolioInput(input);
 return {...projection,source_metadata:{schema:d.schema,version:d.version,owner:d.owner.role,status:d.status,source_path,source_sha256:sourceHash,source_bytes:buffer.length,root_identity_role:'IMMUTABLE_SOURCE_PATH_VERSION_HASH_NOT_SECURITY_ID',holding_key_role:'SOURCE_DOCUMENT_POINTER_NOT_SECURITY_ID',declared_clocks:{effective_at:d.effective_at,available_at:d.available_at,adopted_at:d.provenance.adopted_at},effective_at_utc:utc(d.effective_at,'effective clock'),available_at_utc:available,adopted_at_utc:utc(d.provenance.adopted_at,'adopted clock'),observed_at:observed,provenance:{...d.provenance},themes:d.themes.map(t=>({theme_id:t.theme_id,label:t.label,target_units:t.target_units})),mapping:{admitted:0,unresolved:19,total:19},source_rows:sourceRows}};
}
