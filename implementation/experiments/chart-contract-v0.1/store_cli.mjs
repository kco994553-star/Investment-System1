// Read-only source audit. Outputs JSON to stdout; never changes a raw store.
import {readdir, readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectStoredArtifact, readYahooRawCandidate} from './raw_store_bridge.mjs';

export async function auditYahooStore(root) {
  const names=(await readdir(path.join(root,'manifests'))).filter(n=>n.startsWith('yahoo_chart__')&&n.endsWith('.json')).sort();
  const results=[];
  for(const name of names){
    const parts=name.slice(0,-5).split('__');
    if(parts.length!==3){results.push({manifest:name,status:'INVALID',reason:'Unsupported artifact filename'});continue;}
    const [,symbol,range]=parts;
    try{
      const report=await inspectStoredArtifact({root,artifact_id:`yahoo_chart:${symbol}:${range}`,symbol,range});
      results.push({manifest:name,status:'BYTES_AND_SHAPE_CHECKED',report});
    }catch(error){results.push({manifest:name,status:error.code==='ENOENT'?'MISSING_LOCAL_FILE':error.message.startsWith('unsupported source_kind:')?'UNSUPPORTED_SOURCE_KIND':'INVALID',reason:error.message});}
  }
  const counts=Object.fromEntries(['BYTES_AND_SHAPE_CHECKED','MISSING_LOCAL_FILE','UNSUPPORTED_SOURCE_KIND','INVALID'].map(k=>[k,results.filter(r=>r.status===k).length]));
  return {scope:'YAHOO_NAMED_LATEST_SLOTS_ONLY',manifest_count:names.length,counts,
    financial_validity:'NOT_EVALUATED',identity_binding:'NOT_EVALUATED',historical_PIT:'NOT_VERIFIED',
    note:'Manifest presence is not raw-data availability. History slots and other source kinds are outside this scan.',results};
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const [mode,file]=process.argv.slice(2);
    if(!file||!['inspect','candidate','audit'].includes(mode)||process.argv.length!==4) throw Error('Usage: node store_cli.mjs inspect|candidate OPTIONS.json; node store_cli.mjs audit STORE_ROOT');
    const options=mode==='audit'?null:JSON.parse(await readFile(file,'utf8'));
    const report=mode==='audit'?await auditYahooStore(file):mode==='inspect'?await inspectStoredArtifact(options):await readYahooRawCandidate(options);
    process.stdout.write(JSON.stringify(report,null,2)+'\n');
  }catch(error){process.stderr.write(JSON.stringify({status:'BLOCKED',reason:error.message})+'\n');process.exitCode=1;}
}
