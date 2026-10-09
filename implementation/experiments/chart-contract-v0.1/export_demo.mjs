// Portable review artifact; still synthetic chart data, no network at runtime.
import {readFileSync,writeFileSync} from 'node:fs';
const read=f=>readFileSync(`dist/${f}`,'utf8');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let html=read('index.html');
const css=read('font.css').replace(/url\(([^)]+)\)/g,(_,url)=>`url(data:font/woff2;base64,${readFileSync(`dist/${url.replaceAll(/['"]/g,'')}`).toString('base64')})`);
html=html.replace('<link rel="stylesheet" href="font.css">',`<style>${css}</style>`);
for(const f of ['lightweight-charts.js','data.js','app.js','portfolio-data.js','portfolio_app.js','inventory-data.js','inventory_app.js'])html=html.replace(`<script src="${f}"></script>`,`<script>${read(f).replaceAll('</script','<\\/script')}</script>`);
for(const f of ['NOTICE.lightweight-charts','LICENSE.lightweight-charts'])html=html.replace(`href="${f}"`,`download="${f}" href="data:text/plain;base64,${Buffer.from(read(f)).toString('base64')}"`);
const acceptance=readFileSync('ACCEPTANCE.json','utf8');
const source=readFileSync('evidence/2026-10-04-source/real-source-preflight.json','utf8');
const summary=`<section style="border-bottom:1px solid #4b6284;padding-bottom:20px;margin-bottom:24px"><h1>Investment-System1 · 전체 요구 목록 및 Portfolio 차트 v0.3</h1><p>2026-10-04 KST · API 우선 / MCP 후속 · <a href="https://github.com/kco994553-star/Investment-System1/pull/41">Draft PR #41</a></p><p><strong>전체 요구 목록 + Portfolio 참고자료/DEMO · 실데이터 운영 차트는 미완료</strong></p><p>실제 API 응답 5개 일봉의 OHLCV와 원본 해시를 확인했습니다. 기업·증권·날짜별 상장 식별자 연결과 PIT·세션 근거가 없어 실데이터 차트 공개는 차단 상태입니다.</p><p>기존 가격 차트에 산업군·유형 구성·유형 중복 표시를 추가했습니다. 아래 전체 목록은 핵심81개, 추가 Spec24개, Macro Candidate8개로 구분합니다. 실제 보유·유형 분류·분기 이력은 미연결입니다.</p><details><summary>이번 개선과 남은 작업</summary><ul><li>기존 RawDatasetStore를 읽는 adapter와 source preflight CLI 추가. 원본 수집기를 재사용했습니다.</li><li>시가·고가·저가·종가·거래량 배열 정렬, timestamp, 가격 기준·요청 충돌 검증을 강화했습니다.</li><li>원본 수집 완료 시각과 저장 시각을 별도로 보존합니다. 어느 것도 과거 available_at으로 대체하지 않습니다.</li><li>Canonical의 Yahoo 명명 manifest 1,404개 중 1,346개는 원본 파일 미보유, 58개는 실제 Tiingo source입니다. 과거 검증 기록을 현재 재현 결과로 취급하지 않습니다.</li><li>다음 의존성: exact-hash 원본 복원 → 근거 있는 issuer/security/listing 연결 → exchange session vintage → Web/P01 연결. 기존 owner·보호영역·canonical은 변경하지 않았습니다.</li><li>분류: 원본 표본 SOURCE DATA 확보, 저장소 연결부 검증, 운영 차트·historical PIT·MCP 서버·FPIA 통합 미완료. 실제 차트 완성률에 DEMO를 합산하지 않습니다.</li></ul></details><details><summary>검증 증거</summary><pre>${escape(acceptance)}</pre></details><details><summary>실데이터 사전검사 · 원본 획득 근거</summary><pre>${escape(source)}</pre></details></section>`;
html=html.replace('<body>','<body>'+summary).replace('</footer>',`<details><summary>Noto Sans KR font license</summary><pre>${escape(read('LICENSE.font'))}</pre></details></footer>`);
writeFileSync('dist/standalone.html',html);
console.log('Exported standalone synthetic DEMO with source-preflight evidence.');
