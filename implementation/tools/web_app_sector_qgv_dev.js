'use strict';
// Development site with the sector QGV engine route (Main, owner 2026-11-06): builds the new app into a temporary folder, serves it
// on 127.0.0.1 and answers POST `sector-qgv-engine` with Codex's common engine (synthetic inputs only, web_app_sector_qgv_engine.js).
//   node implementation/tools/web_app_sector_qgv_dev.js      → prints the URL; open #/qgv, 1.2 「계산 엔진 연결」. Ctrl-C stops.
// Development only: the published site has no such route (the screen then says 계산 실행 경로 연결 전).
const site = require('./web_app_test_site');
const eng = require('./web_app_sector_qgv_engine');

(async () => {
  const engine = eng.start();
  const s = await site.start({ posts: { [eng.ROUTE]: engine.route } });
  console.log('sector QGV development site: ' + s.base + '#/qgv  (engine: Codex sector_qgv via ' + eng.ROUTE + ', SYNTHETIC inputs only)');
  const stop = async () => { await s.close(); await engine.close(); process.exit(0); };
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
})().catch((e) => { console.error('DEV_SITE_FAILED ' + (e && e.message)); process.exit(1); });
