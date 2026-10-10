# 현재 인수인계

확인일: **2026-10-10 UTC**. 현재 상태는 이 파일에서 시작하고 [WORKING_RULES.md](WORKING_RULES.md)·[실행 로드맵 v2](implementation/docs/ROADMAP_2026Q4.md)를 따른다. canonical26E는 [GSQ-015까지](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)이며, GSQ-015는 승인 후 #115 병합됐다. 최신 GSQ-017 기업 유형 PROVISIONAL 설정은 구현/기록 PR 준비 중이다. 작은 구현 변경에 새 GSQ·receipt·fingerprint를 만들지 않았다.

## 기준 HEAD·운영 경계

- canonical: `claude/investment-system-top500-validation-alrugm`. 확인한 원격 HEAD **`8ff194cc2661ac555d207775bd20626cdab90b9f`** (#134 병합 후). 이 상태 문서 PR 자체의 병합 HEAD는 GitHub에서 확인한다.
- 코덱1 #98 확인 후 승인 순서 #104→#105→#106, 이어 #108·#110·#112를 병합했다. 이번 로드맵 **#118도 병합**했고 #103·#107은 지시대로 닫았다. #109는 이미 CLOSED이며 코덱1에게 종료 유지 확인만 요청했다.
- 코덱1 #113·#114·#116·#117·#119·#120 병합을 metadata에서 확인했다. #119는 candle/MA/기기 AVG, #120은 비공개 Trades1회 읽기·RAM B/S 표시다. 코드와 실제 본인 기기 운영 성공은 구분한다.
- 코덱2 수정은 허용된 Python src(웹 제외)·관련 tests/tools·문서다. Worker/web_assets/workflows·Frozen/TARGET·가중치·AUTONOMY_MODE·ruleset·force push 변경 없음. 실제 키/계정·가격/환율·provider 관측치 수집·배포·Holdout 사용 없음. 이번 사용자 승인에 따라 비공개 Universe A열의 code 504개만 1회 읽어 코드 전용 자산으로 제공했다; 시트 ID/URL·B/C열은 기록하거나 읽지 않았다.
- **26E 미변경 PR은 실행된 필수 체크 모두 성공·실패0이면 자체 병합 가능**하다는 최신 사용자 선택을 적용한다. 사용자가 기존 CSP 차이는 코덱1 범위임을 명시하고 #115를 승인했다. #115→#121→#111→#123→#125→#127→#128→#129를 각각 최종 필수6개/실행53단계 성공·실패0 확인 후 병합했다. #131의 로그인/CSP 기대값 수정은 코덱1 변경분으로 보존한다.

## 현재 PR·검증

사용자가 기존 분리를 확정했다. **#111은 현행 엔진 세 계산만**, Python 표시 참조·합성 JSON 벡터는 **#115에만** 포함한다. 아래 기존 구현 PR은 승인된 순서로 canonical에 병합됐다. 실제 provider/앱 운영 연결은 별도 상태다.

| PR | 내용·상태 | 관련 검증 |
| --- | --- | --- |
| [#118](https://github.com/kco994553-star/Investment-System1/pull/118) | 실행 로드맵 v2·이전 PR 정리, **병합** | 최종 필수6개/실행53단계 성공·실패0, .md만 변경 |
| [#111](https://github.com/kco994553-star/Investment-System1/pull/111) | 현행 returns 모집단표준편차·마지막return·마지막5합, 병합 | 합성/기존 입력62개 통과 |
| [#115](https://github.com/kco994553-star/Investment-System1/pull/115) | Research 표시 Python·GSQ-015 + Python 참조/JSON 벡터, 병합 |130개 통과; canonical JS 대조8120값/진단0실패 |
| [#121](https://github.com/kco994553-star/Investment-System1/pull/121) | US17 SEC companyfacts/submissions 수집 모듈·진입점, 병합 |171개 통과; 모의 transport·retry/rate·값 없는 오류 |
| [#123](https://github.com/kco994553-star/Investment-System1/pull/123) | SEC10-Q/10-K 제출 패턴 **예상 시기**·확정일 아님, 병합 |31개 통과 |
| [#125](https://github.com/kco994553-star/Investment-System1/pull/125) | 기존 v1 가격 인자 V 순수 함수·RAM, 병합 |52개 통과 |
| [#127](https://github.com/kco994553-star/Investment-System1/pull/127) | 공식 v1 축내부 비중 복사본·사용자 합100·결측수·PREVIEW, 병합 |57개 통과(신규29+v1 15+PIL13) |
| [#128](https://github.com/kco994553-star/Investment-System1/pull/128) | 정부 raw8축 화면 경계·합성 기존 Macro engine 연결·후속4축 공급 payload 파서, 병합 |93개 통과 |
| [#129](https://github.com/kco994553-star/Investment-System1/pull/129) | 사용자 선택 manager13F 정보표·분기 **보고 수량 변화**, 병합 |54개 통과 |

#111·#115·#121·#123·#125·#127·#128·#129는 확인한 head의 최종 필수6개/실행53단계 성공·실패0이다. canonical 동기화 후 head 및 이번 문서 PR의 최종 체크는 묶음 보고 전에 다시 확인한다. deploy의 실행 없는 SKIPPED는 배포 성공으로 세지 않는다.

코덱1 열린 작업은 **#122 M3 기기 Universe JS**, **#124 Tiingo/KRX 예비 가격**, **#126 SEC daily 공개 비가격 입력/Actions**다. 이 PR을 코덱2가 수정·닫기·병합하지 않았다. #121 Python 모듈과 별도 소관이며 실제 daily 운영은 아직 미완료다.

## 통합 검증과 이전 CSP 회귀

#131에서 코덱1이 CSP 기대값을 수정했다. 현재 SEC 입력 어댑터까지 합성 검증한 전체 suite는 1890 passed·358 subtests passed·실패0(36.61초)이다. 아래 실패 기록은 수정 전 이력이다.

canonical3e99e061에 이 대기열의 Python 코드·합성 fixture·테스트만 결합한 검증용 worktree에서 **1858 passed, 358 subtests passed, 1 failed(40.77초)**를 확인했다. 실패는 아래 기존 canonical CSP 검사1개다. 새 전략 함수를 독립 PIL 패키지에서 QGV bridge로 이동한 뒤 기존 PIL13개를 포함한 관련57개도 통과했다. 개별 관련 테스트 수는 중복을 포함하므로 합산하지 않는다.

`tests/test_app_nav_ia.py::test_navigation_does_not_expand_approved_external_csp_permissions`가 #113 이후 canonical07ba93e3 및 최신3e99e061에서도 재현된다. connect-src Worker 출처 추가와 이전 기대값 차이이며 코덱1 앱/CSP 검증 범위다. 코덱2는 해당 앱/테스트/워크플로를 수정하거나 검사를 완화하지 않는다. 필수CI 성공을 전체 suite 성공으로 보고하지 않는다.

## 구현의 실제 연결 상태·미확정 정의

- **SEC:** #121은 실제 호출 없이 모의 응답으로 검증한 수집기/명시적 live 진입점이다. SEC_USER_AGENT는 이름만 참조한다. 실제 US17 취득·daily Actions·공개 재무 producer는 코덱1 연결/운영 후 확인하며 ASML20-F 원문 취득 가능성과 기존10-K M1 READY는 별개다.
- **V:** 가격은 명시적 인자·RAM-only, 기존 raw_map 산식만 재사용한다. DCF/역DCF solver, 가격→자체multiple, 역사/sector/theme 가격 매핑은 미정이며 해당 미제공 요소를0으로 만들지 않는다. 통화·주당/ADR/split·시점 basis 근거도 자동 생성하지 않는다.
- **전략:** Q/G/V **축 내부** 공식 비중·사용자 비중을 재계산한다. GSQ-017의 유형별 Q/G/V 부모 비중은 사용자 승인 PROVISIONAL 값으로 새 설정 PR에서 구현한다. Technical/Macro 합성·새 모델/6관점은 별도다. Q/G 기존 평균과 V를 분리한 PREVIEW이며 모델 채택/저장 snapshot을 바꾸지 않는다.
- **Macro:** #128 정부 screen 함수는8×6 raw evidence·Decimal문자열·취득 cutoff를 제공하지만 공개 producer/앱 연결은 없다. GDP 수준·CPI 지수→기존 growth/inflation fraction 정의 미정으로 실제 국면은 NOT_AVAILABLE다. 후속4축 exact series/basis·모든 새6상태 규칙은 미채택이며 파서는 명시적 binding만 받는다. Fed는 확인된 DataSet fragment만 지원하고 full-feed/ZIP 추출 계보는 미검증이다. FRED/ALFRED 차단 유지.
- **실적/13F:** SEC 제출 패턴은 확정 실적 발표일이 아니다.13F NEW/ADD/REDUCE/EXIT는 공개 보고 수량 변화이며 실제 매매·현재 보유 추론이 아니다. 비공개·추가 정정·부분 표·비연속분기·미확인 귀속은 비교 차단한다. 투자자 기본 목록은 없고 사용자가 공급한다.
- **기기:** #116 통합 백업·#117 Research JS·#119 candle/MA·#120 private Trades 코드와 실기기 검증을 구분한다. M3 개인 선정·가격·시총·순위·Universe ID·키/토큰은 공개/새 백업에 넣지 않는다. M3 기본N20·불일치10%와 근거 있는 SHARE_CLASS_BASIS 표시만/자동 보정 없음은 확정이다.

## 긴급 SEC daily 진단

사용자 즉시 자체 병합 승인에 따라 고정 코드·HTTP 상태·fetch/parse/normalize·회사 순번만 노출하고 부분 실패를 분리했다. [연결 계약](implementation/docs/daily_data_pipeline/SEC_COLLECTION_DIAGNOSTICS.md). 전체1918개+358subtests 통과·실패0(45.14초), 관련86개·reader review 중요 미해결0. v1 전체 성공 유지, 일부 성공은 strict v2 LIVE/NOT_AVAILABLE17행, 전부 실패면 exit1·이전 파일 보존. 실행 환경 SEC_USER_AGENT 미설정으로 실제 Actions와 동일 조건의 재현은 미실행; UA/HTTP 원인은 아직 미확정. 워크플로·웹·Worker 수정 없음.

유형/GSQ-017은 #135 승인 대기, 테마 #136 확인 대기 제안·자동NA. 화면용 공개 JSON CLI·JS 이식 벡터가 새 최우선이고, DCF 작업은 그 뒤 계속한다. EDINET 후순위·DART 등록 알림 전 비착수.

## 다음 할 일5개 — GSQ-017 대기열

1. 이 PR의 SEC M3 어댑터·504 code-only JSON을 코덱1 #122/#126 loadInputs 연결에 사용한다. cover 근거 없는 종목은 NA; 주식 종류 차이는 표시만이다.
2. GSQ-017 versioned type_config·순수 유형 계산·기기 custom PREVIEW를 구현한다. 승인된 비중/램프 이외 미정값은 만들지 않는다.
3. 14개 테마 ETF 바스켓/키워드·소속도 정규화 후보와 DCF 파라미터 기본값을 사용자 확인 대상으로 제안한다.
4. Macro GDP/CPI·후속 series→8축 대응표 초안을 문서화하고 채택 전에 계산/상태 규칙을 바꾸지 않는다.
5. EDINET은 사용자 결정으로 후순위 보류한다. DART는 사용자 키 등록 알림 전 코드·키 조회·인증/API 비착수다.

기존 Holdout은 **UNCONFIRMED·v2 근거 제외·미사용**, QGV v2는 보류다. 검증은 향후 누적 forward 데이터이며 시작 시점은 사용자가 결정한다. 에이전트는 기간을 선택·사용하지 않는다. 기존 구현8개 PR은 병합됐으며 새 대기열은 [구현 계획](implementation/docs/ENGINE_QUEUE_GSQ017_PLAN.md)을 따른다.

## 외부 서비스·저장 위치

설정 이름만 기록하며 실제 값·계정·키/시트 존재 여부를 이번 작업에서 확인하지 않았다.

| 서비스 | 현재 범위 | 저장/연결 경계 |
| --- | --- | --- |
| BLS·BEA·Treasury·Fed | 공급 응답 파서·원기관 근거, BEA_USERID는 이름만 | 모델 의미/실제 수집·앱 연결 미완료; FX·가격 성격 입력 RAM-only |
| FRED·ALFRED | 서면 허가 전 차단 | 호출·키 조회·fallback 없음 |
| SEC EDGAR | #121 수집 모듈, #123 예상 패턴, #129 정보표 | SEC_USER_AGENT 이름만; daily 공개는 비가격 자료만·개인 선정 제외 |
| Google Identity·Sheets | 기존 readonly Quotes·private history/Trades, M3 #122 대기 | 개인 가격/파생·선정·Universe ID·토큰은 공개/새 저장 제외 |
| Cloudflare·Pages | 코덱1 Worker/Pages 코드·metadata 범위 확인 | 실제 배포/본인 인증/운영 검증은 이번 Python·문서 작업과 별개 |
| EDINET·DART | 사용자 결정으로 후순위 보류 | EDINET Subscription-Key·DART_API_KEY 값 출력/조회 없음; adapter 비착수 |
| Tiingo·KRX | #124 예비 경로 조건 대기 | 기존 등록 보고와 실제 인증/권리·3시장 coverage를 구분 |

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
