import {renderPortfolioInput} from './portfolio_contract.mjs';
import {fictionalPortfolioFixture} from './portfolio_fixture.mjs';
import {projectTargetV0} from './target_v0_source.mjs';
import {mkdirSync,copyFileSync,writeFileSync,readFileSync,cpSync} from 'node:fs';
import {fixture} from './fixture.mjs';
import {normalizeStoredResponse,renderInput,hash} from './contract.mjs';
const f=fixture(); const doc=normalizeStoredResponse(f.bytes,f.ctx);const rows=renderInput(doc);
mkdirSync('dist',{recursive:true});
copyFileSync('node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js','dist/lightweight-charts.js');
copyFileSync('node_modules/lightweight-charts/LICENSE','dist/LICENSE.lightweight-charts');
copyFileSync('NOTICE.lightweight-charts','dist/NOTICE.lightweight-charts');
copyFileSync('page.html','dist/index.html');copyFileSync('app.js','dist/app.js');
copyFileSync('node_modules/@fontsource/noto-sans-kr/400.css','dist/font.css');
copyFileSync('node_modules/@fontsource/noto-sans-kr/LICENSE','dist/LICENSE.font');
cpSync('node_modules/@fontsource/noto-sans-kr/files','dist/files',{recursive:true});
writeFileSync('dist/data.json',JSON.stringify(doc,null,2));
writeFileSync('dist/data.js',`window.CHART_DEMO=${JSON.stringify({doc,rows})};`);
writeFileSync('dist/build-evidence.json',JSON.stringify({contract:doc.contract,fixture:true,raw_sha256:hash(f.bytes),data_sha256:hash(Buffer.from(JSON.stringify(doc,null,2))),renderer:'lightweight-charts@5.2.1',renderer_sha256:hash(readFileSync('dist/lightweight-charts.js')),state:'DEMO_ONLY'},null,2));
console.log('Built 12 synthetic daily records; volume missing=1, zero=1; PIT NOT_VERIFIED; no network data.');

const reference=JSON.parse(readFileSync('portfolio_reference.json','utf8'));
// Recorded extraction of this immutable source; repeated builds do not claim a fresh observation.
// An explicitly authorized new extraction may supply TARGET_OBSERVED_AT.
const observed_at=process.env.TARGET_OBSERVED_AT||'2026-10-08T12:15:25Z';
const target=projectTargetV0(readFileSync('../../docs/portfolio_target_owner/TARGET_v0.yaml'),JSON.parse(readFileSync('../../docs/security_map19_owner/TARGET_v0_SECURITY_MAP.json','utf8')),{observed_at});
writeFileSync('target_v0_projection.json',JSON.stringify(target,null,2)+'\n');
const portfolios={reference:target,historical:renderPortfolioInput(reference),demo:renderPortfolioInput(fictionalPortfolioFixture())};
// Bind the complete local reference display to the projection of authenticated source bytes.
// The expected serialized snapshot is separate from mutable UI payloads; it is not a production grant.
const canonicalTarget=JSON.stringify(JSON.stringify(target)).replaceAll('<','\\u003c');
writeFileSync('dist/portfolio-data.js',`Object.defineProperty(window,'TARGET_V0_REFERENCE_CANONICAL',{value:${canonicalTarget},writable:false,configurable:false});\nwindow.PORTFOLIO_CHARTS=${JSON.stringify(portfolios).replaceAll('<','\\u003c')};`);
copyFileSync('portfolio_app.js','dist/portfolio_app.js');
copyFileSync('inventory_app.js','dist/inventory_app.js');
writeFileSync('dist/inventory-data.js',`window.CHART_INVENTORY=${readFileSync('chart_inventory.json','utf8').replaceAll('<','\\u003c')};`);
