# 현재 인수인계

확인일: **2026-10-10 UTC**. 현재 상태는 이 문서에서 시작하고 [WORKING_RULES.md](WORKING_RULES.md)·[실행 로드맵 v2](implementation/docs/ROADMAP_2026Q4.md)를 따른다. canonical26E는 GSQ-017까지 병합; 기업 유형 구현 **#135도 사용자 승인 후 병합**됐다. 작은 변경에 GSQ·receipt·fingerprint를 새로 만들지 않았다.

## 기준 HEAD·운영 경계

- canonical `claude/investment-system-top500-validation-alrugm`, 확인 HEAD `c96f05e9a10b7ba494a43b5f7fabf825ba89f21e` (#135 사용자 승인 병합 후). 이 문서 자체와 이후 병합 HEAD는 GitHub에서 확인한다.
- 사용자 선택: **26E 미변경 PR은 실행된 필수 체크 전부 성공·실패0이면 자체 병합**. #135는 사용자 병합 승인을 받았고 이후26E 변경 포함 PR은 별도 승인 대상. deploy 실행 없는 SKIPPED는 배포 성공이 아니다.
- 코덱2는 Python src(웹 제외)·관련tests/tools·문서. 코덱1의 웹/Worker/Actions 변경은 canonical 병합으로 보존한다. force push·ruleset·AUTONOMY_MODE·Secret 출력·새 미승인 산식/가중치·Holdout 사용 없음.
- Gate A·FPIA·HG는 **1인용 범위 해당 없음(종료)**. 계산/결측/입력/공개 개인정보 가드·Frozen/원본 TARGET 불변은 유지한다.

## 현재 코드·운영 상태

| PR | 상태/범위 | 검증·제한 |
| --- | --- | --- |
| #115→#121→#111→#123→#125→#127→#128→#129 | 승인 순서대로 병합 | 각각 필수6개/실행53단계 성공·실패0. Research 표시와Model입력은분리. |
| #134 | SEC M3 식별·cover 주식 종류 입력/Universe504code-only, 병합 | 코드만 공개,SheetID/가격/시총/기기★없음. 종류수치자동보정없음. |
| #135 | 기업유형8개·버전설정/불변공식·custom PREVIEW·GSQ-017, **사용자 승인 후 병합** | 현재설정의유형별램프·Q/G/V비중/혼합규칙구현;우량/가치/민감방어미정부분NA. |
| #136 | 테마14개/25ETF·키워드제안·pure exposure집계, 병합 | 바스켓확인·정규화/결합미정,자동membershipNA. QGV영향없음. |
| #137/#138 | SEC 고정진단·partial success·badrow제외·IFRS/10-KT/10-QT, 병합 | schema3, core shares존재할때회사유지. 실제재실행17/17성공확인,아래참조. |
| #141 | 공개 표시용5파일JSON CLI·strict guard, 병합 | macro/13F/filing/QG/가격없는type. as_of/source/state/version. 취득TTL은LIVE기준이며금융기간/PIT최신성아님. 타입#135 병합 후 가용한 가격없는소속도만표시. |
| #143 | RAM-only DCF/역DCF 순수함수, 병합 | 35개 합성/Decimal참조·전체1957+265subtests/0실패. 금융기본값null/confirmed=false. |
| #145 | Universe504확장registry·CIK중복제거·daily shard collector, **병합** | 명시적schedule·rate/retry·회사별partial/고정진단. 실제504대량실행없음,rawlocal전용. |
| #146 | JS 이식 계약·36합성JSON vectors·Python replay, **병합** | canonical36사례 Python대조(타입5사례 포함),JS대조는후속. JS실제parity는코덱1후속. |
| 코덱1 #122/#124/#126/#142/#144/#148 | #122 M3기기후속, #124예비가격/#126SECdaily/#142PWA/#144공개화면/#148기기프로필·백업코드병합 | 코드상태와본인기기·3시장·실제정부자료취득/배포운영성공은구분. 코덱2가웹/Worker/워크플로를수정하지않음. |

최신canonical의코덱1 device-profiles/profile-defaults·백업결속 변경도보존한다. 유형#135의공식설정과strategy의축내부PREVIEW는별개이며JS구현/실기기동작과Python참조의최종대조상태는분리한다.

## 통합 검증의 현재 제한

#135의관련104개(type/JSONvector/publicscreen)는통과했다. 최신결합full2069passed+267subtests,1실패는코덱1#148의웹문구 `기업 유형 커스텀`가locale.js에없는회귀다(test_web_state_presentation.py::test_every_ui_string_has_ko_and_en_entries). 사용자병합조건인실행필수6개/53단계는성공·실패0으로확인했다. 전체suite가0실패라고주장하지않으며웹source/해당기대값은코덱2가수정하지않았다.코덱1번역추가후전체재확인대상이다.

## 실제 SEC daily 확인

Actions `workflow_dispatch` **38039786166**, head303ae501854b1926bd21e406279cfe228d87dd26,completed/success에서고정진단만확인: **BUILD_OK / failed_companies=0**. company_index8(HUBB)의VALUE_INVALID행제외가있다. raw로그값/URL/UA출력없음. 이전AVGO/HUBB/MSFT3normalize실패가badfact1행때문이었는지실제원문줄은이환경에없어단정하지않는다. normalize17/17성공과QG전체재무원문17/17확보/계산성공은다르다.

## 정의·자료 미확정과 실제 결과

[19종목 결과·500회사 커버리지](implementation/docs/company_types/QUEUE_RESULTS_AND_COVERAGE.md)에전체표와근거를기록했다. 이환경의raw blobs는0개,STORE_INDEX의fact1117/sub1172/NPORT계열6건은metadata다. 실제원문·eligiblefund/issuerjoin가없어19종목가격없는유형·Q/G·테마는모두NOT_AVAILABLE이며0점/‘테마없음’으로표시하지않는다. 코드자산504listing은500회사coverage가아니다. 실제누적forward/Holdout을결과표로대체하지않았다.

- 유형: 성장3YCAGR·배당gate/ramp·업종시총rank와승인혼합규칙구현. 우량의마진/부채threshold·결합,가치할인basis/ramp,민감/방어SICmapping·매출변동성ramp/결합,5년정규화이익→Vscore미정. 설정으로후속확장가능,공식수정/custom PREVIEW혼합금지.
- 테마:14바스켓·Item1literalkeywords확인용제안. exactNPORTregistrant/series/class와보유수/비중0~1정규화·keyword보완·쏠림경고미정. 실제500커버미실측.
- V/DCF: 기존v1price_value·DCF순수함수만RAM. FCFE출처산식/주당·통화·ADR/split 및가격→multiple/역사/sector/theme mapping미정.10%할인율·2%영구성장은문서제안만,기본금융값비활성.
- Macro:4축/나머지4축공급파서와raw8×6화면/합성기존엔진연결준비. [8축매핑초안](implementation/docs/macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md)의GDP전기비연율/CPI NSA YoY·후속exactseries/basis 확인전실제국면NA. Direction/Momentum/Surprise/Stress/Confidence미정. FRED/ALFRED금지,FX공개출력제외.
- DART:사용자키등록알림미수신으로adapter비착수. EDINET:후순위보류. 기존Holdout UNCONFIRMED·v2근거제외;v2착수/forward시작일사용자결정전기간선택/사용없음.

## 결정 대기·다음 할 일5개

| 결정 | 확인 전 경계 |
| --- | --- |
| SIC→업종군 매핑 초안 확인 | #135 병합승인 완료; 별도 표 확인 전 경기민감·방어NA |
| 유형미정기준·SIC표/변동성·5년이익V | 새threshold/score추정 없이NA |
|14테마바스켓/keywords 및소속도정규화/보완·경고 | 자동membershipNA·override기기전용·QGV영향없음 |
| DCF10%/2%제안·FCFE/통화/주당basis | confirmed=false/기본NA |
| 매크로GDP/CPI대응·후속selector/8×6규칙 | raw만표시,실제국면NA |
| 향후DART등록알림·v2/forward착수시점 | 알림/결정전각각비착수,EDINET보류유지 |

1. 코덱1: #141/#144 공개5sidecar·출처/상태의실제원기관입력연결과본인기기확인. 원문재무공급후기존QGleafscore를재현;단순shares로QG대체금지.
2. 사용자/코덱2: #135 병합으로타입의존성해소,미정기준은별도결정때만구현. 승인값을재질문하거나새방법론자동채택안함.
3. 코덱1: #146의Python/JS vectors 실제대조·#122 SEC식별/주식basis/M3기기연결. 가격/시총/선정/★는기기RAM전용.
4. 코덱1: #145 collector의공식ticker metadata·일단위shard scheduling·rawprivate위치/rate coordination연결.504실측coverage별도검증.
5. 사용자/코덱2: ETF/매크로/DCF미정항목확인후필요구현;DART알림대기·EDINET보류·Holdout미사용유지.

## 이력·상세 참고

이전CSP실패는#131에서해소됐고최근PWA빌드진입점변화로인한public-screen테스트는현재공개builder로맞췄다. 사용자지시로#103/#107닫음,코덱1#109이미CLOSED유지요청만. 기존열린PR정리권고는아래이력으로남기며추가닫기/코드병합을자동실행하지않는다.

### 이전 열린 PR 정리안 (#100 작성 시점 참고)

아래는 #100 작성 시점의 열린 PR46개에 대한 과거 정리안이다. #95·#96·#97·#100은 이후 병합되어 현재 열린 PR이 아니다. #99는 그 작성 시점에도 이미 병합됐다. 표는 권고만 기록하며 이 정리 작업에서 닫기·병합을 실행하지 않았다.

| 번호 | 제목 | 권장 | 이유 |
| --- | --- | --- | --- |
| [#100](https://github.com/kco994553-star/Investment-System1/pull/100) | docs: 1인용 혼합 작업 규칙과 현재 인수인계 정리 | 병합 | 사용자 결정의 혼합 규칙과 최신 현황을 두 문서에 통합; 승인 후 반영. |
| [#98](https://github.com/kco994553-star/Investment-System1/pull/98) | [WIP] M2 Q·G 후보 앱 표시 — V NOT_AVAILABLE·가격 미포함 | 유지 | 최종 코드 리뷰·실제 입력 연결이 남아 WIP 보존; 전체·브라우저·CI 통과. |
| [#97](https://github.com/kco994553-star/Investment-System1/pull/97) | 공개 가격 DATA 140개 정리 및 보류·Frozen 메타데이터 보존 | 병합 | 공개 가격 DATA 140개 정리와 Frozen·보류 보존이 승인 범위이며 CI 6개 통과; #96 다음 순서로 병합. |
| [#96](https://github.com/kco994553-star/Investment-System1/pull/96) | Public boundary A: 공개 출력·수집 경로 28개 차단 | 병합 | 공개 출력·수집 28개 경로 차단과 SEC 식별 보존이 현 정책에 부합하고 CI 6개 통과; #97보다 먼저 병합. |
| [#95](https://github.com/kco994553-star/Investment-System1/pull/95) | Worker: 배포 오류 마스킹 진단과 토큰·계정 사전 점검 | 병합 | 승인된 Worker 오류 마스킹·배포 사전 점검이며 CI 통과; 병합 뒤 실제 배포 재실행으로 장애 원인 확인. |
| [#71](https://github.com/kco994553-star/Investment-System1/pull/71) | Chart public reference B: verified TARGET freshness, bilingual notice and scoped gate correction | 유지 | 미반영 TARGET 최신성·한영 안내 기능은 보존하되, 구 A-G/FPIA 문서와 오래된 배포 변경을 현 정책에 맞춰 정리 필요. |
| [#61](https://github.com/kco994553-star/Investment-System1/pull/61) | Web: close PPA-F08 ACTUAL/TARGET fallback | 닫기 | ACTUAL→TARGET 대체 방지는 #63 계열로 이미 반영됐고 현재 코드는 유한값 검사·별도 TARGET 표기로 더 강화됨. |
| [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | FPIA coverage, workflow-source observation and branch-independent applicability | 닫기 | FPIA 실행 coverage·workflow 출처·영수증 검증만 확장하므로 중단한 운영 증빙 범위에 해당. |
| [#46](https://github.com/kco994553-star/Investment-System1/pull/46) | [FPIA successor] Fix literal-source false PASS and inventory container images | 닫기 | FPIA literal-source·증거 식별 검증기 보수이므로 폐지한 FPIA 운영 절차와 함께 정리. |
| [#45](https://github.com/kco994553-star/Investment-System1/pull/45) | Independent Product Platform audit: synthetic fail-closed harness and owner evidence | 닫기 | tenant·서버 세션·동기화 저장소 중심 다중 사용자 플랫폼으로 현 1인용 범위 밖; 독립 보안 예제 코드는 브랜치 보존. |
| [#43](https://github.com/kco994553-star/Investment-System1/pull/43) | docs(ops): common GitHub API write-path instruction | 유지 | Git 전송 실패 시 API 대체 안내는 유효하므로 보존하되, 구 Global 담당자·과도한 증빙 요구를 현 운영 문서로 축약 필요. |
| [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | [proposal] Hardened Track C FPIA (CDR-014): integration acceptance on merge-result SHAs; frozen tools unchanged | 닫기 | 약 1.8만 줄의 FPIA 승인 검증기·전용 CI·vendoring으로 현 단일 사용자 운영에서 제외된 절차. |
| [#40](https://github.com/kco994553-star/Investment-System1/pull/40) | CDR-012 successor trial: #39 + PR #31 (F1 d*d, F3 NOT_RUN) + PR #35 (fresh heads) | 닫기 | #39에 #31·#35를 겹친 구 통합 시험이므로 종료하되, #31 계산 코드와 개별 기능 PR은 보존. |
| [#39](https://github.com/kco994553-star/Investment-System1/pull/39) | CDR-011 integration trial: #38 + PR #31 (CDR-010 M-B v2) + PR #35 (fresh heads) | 닫기 | #38에 이전 #31·#35를 겹친 통합 시험이며 #40으로도 대체되어 별도 유지 실익이 없음. |
| [#38](https://github.com/kco994553-star/Investment-System1/pull/38) | Integration trial: #30 + C-28 evidence (#32/#33) + Web render guard (#34) + production-state UI (#36) | 닫기 | UI guard·상태 표시는 이미 기본 브랜치에 들어갔고 남은 adoption 증빙 중심의 옛 통합 시험. |
| [#37](https://github.com/kco994553-star/Investment-System1/pull/37) | Dynamic Workflow M0: deterministic risk router and trace | 닫기 | 제품 계산 없이 작업 위험도와 trace만 분류하는 운영 라우터라 현재 단순화한 1인용 범위에서 제외. |
| [#36](https://github.com/kco994553-star/Investment-System1/pull/36) | [proposal] Web production-shaped state presentation (freshness, withheld metadata, ko/en, error fallback) | 닫기 | 현재 HEAD 전체가 기본 브랜치에 이미 포함되어 UI 상태·한영·오류 처리 기능을 보존한 채 중복 PR 정리 가능. |
| [#35](https://github.com/kco994553-star/Investment-System1/pull/35) | Integration: CI-verified CDR-012 PR31 dependency with preserved shared-source protection | 닫기 | 구 통합 source-compat·fingerprint 증빙 묶음이므로 종료하고 필요한 소스 호환 검사는 일반 테스트로 보존. |
| [#34](https://github.com/kco994553-star/Investment-System1/pull/34) | [proposal] Web render guard: research/provisional sections never render as LIVE/FROZEN (G3) | 닫기 | 연구 결과의 LIVE/FROZEN 오표시를 막는 guard가 기본 브랜치에 이미 포함되어 중복 PR 정리 가능. |
| [#33](https://github.com/kco994553-star/Investment-System1/pull/33) | [proposal] #7 C-28 adoption evidence record (CDR-004) | 닫기 | 검색 코드 변경 없이 C-28 adoption fingerprint 기록 2개만 추가하므로 중단한 증빙 업무에 해당. |
| [#32](https://github.com/kco994553-star/Investment-System1/pull/32) | [proposal] #9 C-28 adoption evidence record (CDR-004) | 닫기 | producer 코드 변경 없이 C-28 adoption 기록 2개만 추가하므로 중단한 증빙 업무에 해당. |
| [#31](https://github.com/kco994553-star/Investment-System1/pull/31) | Track C: approved CDR-012 v2 squaring and all-degenerate fail-closed | 유지 | 실제 bootstrap 제곱 계산·전부 퇴화 시 차단 수정이 있어 보존하되, 대량 증빙·통합 변경을 분리하기 전 병합 보류. |
| [#30](https://github.com/kco994553-star/Investment-System1/pull/30) | Integration trial: preserved C-28 adoption, producer compatibility and existing-Web E2E | 닫기 | 여러 미반영 엔진·producer를 묶은 352개 파일의 옛 통합 시험이므로 개별 #4/#7/#10~19를 남기고 종료. |
| [#29](https://github.com/kco994553-star/Investment-System1/pull/29) | Existing Web: withheld producer-contract fixture and locale/mobile/failure E2E | 유지 | 보류 데이터 누출·한영·모바일·오류 상태를 검증하는 실제 브라우저 테스트가 유용하므로 현 UI에 맞춰 보존. |
| [#28](https://github.com/kco994553-star/Investment-System1/pull/28) | Fresh takeover audit: exact remote state, capability inventory and verified integration receipts | 닫기 | 제품 코드 없이 412개 인수인계·상태·통합 영수증 파일을 추가하므로 중단한 대량 증빙 작업에 해당. |
| [#27](https://github.com/kco994553-star/Investment-System1/pull/27) | [proposal] #17 C-28 adoption re-pin (CDR-004) | 닫기 | P01 기능 추가 없이 C-28 fingerprint 재고정·상태·불변성 증빙만 변경하므로 정리. |
| [#26](https://github.com/kco994553-star/Investment-System1/pull/26) | [proposal] #14 C-28 adoption re-pin (CDR-004) | 닫기 | Leaderboard 기능 추가 없이 C-28 fingerprint 재고정과 증빙만 변경하므로 정리. |
| [#25](https://github.com/kco994553-star/Investment-System1/pull/25) | [proposal] #12 C-28 adoption re-pin (CDR-004) | 닫기 | Macro 계산 추가 없이 C-28 재고정·lineage adoption 증빙과 기존 테스트만 변경하므로 정리. |
| [#24](https://github.com/kco994553-star/Investment-System1/pull/24) | [proposal] #18 C-28 adoption re-pin (CDR-004) | 닫기 | 거래 세션 기능 추가 없이 C-28 fingerprint 재고정·상태·증빙만 변경하므로 정리. |
| [#23](https://github.com/kco994553-star/Investment-System1/pull/23) | [proposal] #15 C-28 adoption re-pin (CDR-004) | 닫기 | Technical 모델 추가 없이 C-28 fingerprint 재고정·상태·증빙만 변경하므로 정리. |
| [#22](https://github.com/kco994553-star/Investment-System1/pull/22) | [proposal] #11 C-28 adoption re-pin (CDR-004) | 닫기 | Technical 입력 기능 추가 없이 C-28 fingerprint 재고정·adoption 기록만 변경하므로 정리. |
| [#21](https://github.com/kco994553-star/Investment-System1/pull/21) | Claude Code Worker Contract v1.0 + CLAUDE.md routing (docs only) | 닫기 | 옛 다중 worker·Global 단일 작성자·증빙 운영 계약이 현재 단순화 정책과 맞지 않아 새 운영 문서로 대체. |
| [#19](https://github.com/kco994553-star/Investment-System1/pull/19) | Add QGV invalidation binding without activating display | 유지 | QGV 입력 변경·무효화 사건을 판별하는 실제 안전 코드가 미반영이므로 표시 허용과 분리해 보존. |
| [#18](https://github.com/kco994553-star/Investment-System1/pull/18) | US equity trading session v1: calendar vintage binder and close-availability guard | 유지 | 거래일·상장 식별·종가 이용시점 검증 코드가 미반영이므로 사설 가격 경로와의 연결 검토용으로 보존. |
| [#17](https://github.com/kco994553-star/Investment-System1/pull/17) | P01 research publication v1: envelope and predicate, display stays off | 유지 | 연구 결과의 상태·표시 허용을 구분하는 실제 envelope·predicate가 미반영이므로 필요한 안전 경계 보존. |
| [#16](https://github.com/kco994553-star/Investment-System1/pull/16) | SEC 8-K primary disclosure v1 (general news stays unavailable) | 유지 | SEC 8-K 원문 공시 adapter는 1인용 공개정보 수집에도 유용하고 미반영이라 일반 뉴스와 구분해 보존. |
| [#15](https://github.com/kco994553-star/Investment-System1/pull/15) | Technical REAL Model v1: M1 features and M2 regime (M3 held) | 유지 | 실제 M1 지표·M2 regime 계산이 미반영이므로 보존하고 사설 일봉 입력 설계에 맞춘 검증 뒤 통합. |
| [#14](https://github.com/kco994553-star/Investment-System1/pull/14) | Leaderboard REAL Producer v1: existing engine replay, research snapshot, publication blocked | 유지 | 기존 엔진 순위 재현·동점·누락 처리 코드가 미반영이므로 보존하되 현재 공개 가격 차단 정책에 맞춰 범위 조정. |
| [#13](https://github.com/kco994553-star/Investment-System1/pull/13) | RIG news ingestion v1: implementation baseline / integration wait | 유지 | 뉴스 정규화·중복 제거·기업 식별 안전 코드가 미반영이므로 보존하되 실제 공급자 연결은 별도 검토. |
| [#12](https://github.com/kco994553-star/Investment-System1/pull/12) | Macro REAL Producer v1: implementation baseline / integration wait | 유지 | Macro의 PIT vintage 선택·필수값 누락 차단 코드가 미반영이므로 보존하고 현 입력 경로와 통합 검토. |
| [#11](https://github.com/kco994553-star/Investment-System1/pull/11) | Technical real-input producer v1 (PIT gate, model NOT_AVAILABLE) | 유지 | Technical 입력의 PIT·식별·출처 검증 코드가 미반영이므로 보존하되 사설 Worker 경로와 정합성 검토 필요. |
| [#10](https://github.com/kco994553-star/Investment-System1/pull/10) | QGV Real Producer v1: per-company PIT persistence, batch manifest, exporter | 유지 | 기업별 QGV·PIT 저장과 batch exporter가 미반영이므로 보존하되 기존 가격 의존·대량 보고서는 새 QG 경로와 재정리. |
| [#9](https://github.com/kco994553-star/Investment-System1/pull/9) | Producer Infrastructure v1: producer contract, fail-closed bundle exporter, raw persistence design (stacked on PR #6) | 닫기 | producer 계약·기본 exporter·raw 보존 기반의 HEAD 전체가 기본 브랜치에 이미 포함되어 중복 PR 정리 가능. |
| [#7](https://github.com/kco994553-star/Investment-System1/pull/7) | Entity Metadata Coverage: CIK-bound Top-500 search metadata (stacked on #6) | 유지 | CIK·종목·Universe 일치로 묶는 검색 메타데이터 확장이 미반영이므로 오인 연결 방지와 함께 보존. |
| [#6](https://github.com/kco994553-star/Investment-System1/pull/6) | Global Language & Search implementation baseline | 닫기 | 한영·검색 구현 HEAD 전체가 기본 브랜치에 이미 포함되어 기능을 보존한 채 중복 PR 정리 가능. |
| [#4](https://github.com/kco994553-star/Investment-System1/pull/4) | Track C: C7 software frozen; C8-C10 policy packages await approval | 유지 | EVL·시계열 분할·검증 계산 코드가 대량 미반영이므로 보존하되 구 승인 문서·미승인 C8~C10과 분리 전 병합 보류. |

## 흩어진 현황 문서

아래 문서는 세부 설계·과거 상태의 참고 자료다. 운영상 충돌은 WORKING_RULES.md와 위 현재 상태가 우선한다.

- [이전 전체 상태 색인](Investment-System1%20%C2%B7%20Master%20Status%20Index%202026-09-22.md)
- [이전 프로젝트 인수인계](Investment-System1%20%C2%B7%20CURRENT_HANDOFF.md)
- [인수인계 이력](Investment-System1%20%C2%B7%20HANDOFF_HISTORY.md)
- [개인 투자 레이어 인수인계](Investment-System1%20%C2%B7%20PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md)
- [Track A 실제 데이터 상태](Investment-System1%20%C2%B7%20TRACK_A_REAL_DATA_STATUS.md)
- [프롬프트 라이브러리 상태](Investment-System1%20%C2%B7%20TRACK_E_PROMPT_LIBRARY_V1_STATUS.md)
- [분기 로드맵](implementation/docs/ROADMAP_2026Q4.md)
- [웹 MVP 상태](implementation/docs/web_mvp/STATUS.md)
- [언어·검색 상태](implementation/docs/global_language_search/STATUS.md)
- [Producer 기반 상태](implementation/docs/producer_infrastructure/STATUS.md)
- [QGV 계약 작업 상태](implementation/docs/qgv_common_contract_vnext/STATUS.md)
- [QGV 구조 조정 인수인계](implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/CURRENT_HANDOFF.md)
- [34개 변수 설명](implementation/docs/prompt_field_guide_owner/VARIABLE_MEANINGS.md)
- [D 상세 명세](implementation/docs/technical_live_data/FIRST_IMPLEMENTATION_SPEC.md)

최신 화면 정본: [사용자 제공 S01~S16 디자인 캔버스](implementation/docs/cockpit_ia/DESIGN_CANVAS_SCREENS_v1.md), 문서 PR #149. Cockpit IA에서 S13~S16을 연결하며 실제 화면/실데이터 완료와 구분한다.
