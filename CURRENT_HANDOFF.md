# 현재 인수인계

확인일: **2026-10-10 UTC**. 현재 상태는 이 파일에서 시작하고 운영은 [WORKING_RULES.md](WORKING_RULES.md), 실행 순서는 [실행 로드맵 v2](implementation/docs/ROADMAP_2026Q4.md)를 따른다. canonical의 26E는 [GSQ-014까지](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)이며, 최신 대화의 **GSQ-015 ‘표시 전용 기본값(한국식), 모델 채택 아님’** 기록은 [#115](https://github.com/kco994553-star/Investment-System1/pull/115)에 포함돼 병합 대기다. 이번 로드맵 정리는 새 GSQ·receipt·fingerprint를 만들지 않는다.

## 기준 HEAD

- 기본 브랜치: `claude/investment-system-top500-validation-alrugm`.
- 확인한 원격 canonical HEAD: **`eb3c86aebc4eb1bf0ba7708786fa9baa0fa46810`** (#118 병합 후). 이 현황 문서 PR 자체의 병합 HEAD는 해당 GitHub PR에서 확인한다.
- 코덱1 #98 병합 확인 후 사용자 승인 순서 #104→#105→#106을 병합했고 #108 GSQ-014, #110 근거 있는 SHARE_CLASS_BASIS, #112 원기관 Macro 후속4축 출처 조사가 병합됐다. 각 코덱2 병합의 최종 실행 체크·단계 성공·실패0을 확인했다.
- #95·#96·#97·#100·#101은 병합된 기준선이다. #102·#113·#114·#116·#117·#118도 GitHub metadata에서 병합을 확인했다. 코덱1 변경분을 수정하지 않고 현재 상태에 반영한다. Frozen·원본 TARGET·공개 가격 차단 유지, force push·ruleset·AUTONOMY_MODE 변경 없음.
- #111·#115는 **열림·미병합**이다. 최신 사용자 선택에 따라26E 미변경 PR은 최종 필수 체크 성공·실패0이면 자체 병합 가능하며, GSQ-015 기록을 포함한 #115는 별도 승인 대기다. 최신 코드가 canonical에 들어갔다고 간주하지 않는다.

## 배포·입력 상태

- #113은 검증된 Worker에 앱 private history를 연결하고 email 재동의를 추가한 코덱1 PR이다. #114는 public artifact·브라우저 검증 후 수동 Pages 게시 경로다. 이번 작업은 GitHub metadata·저장소 근거만 확인했으며 실제 Worker/Pages 조회·배포·키·계정·개인 시트 호출은 실행하지 않았다.
- #103의 Worker 실행38018407666 보고는 당시 배포 성공/마지막 무인증 검사 실패(`ANONYMOUS_CHECK_CACHE_FAILED`) 기록이다. 당시 private history OFF·설정 미준비를 현재 앱 상태로 재사용하지 않는다. 현재 서비스 성공은 코덱1의 후속 운영 검증과 구분해 확인해야 한다.
- SEC M1은 US17 수동 취득 CLI·보존/replay 구현이 있고 #98은 가격 없는 Q/G 후보 표시다. 실제 취득·일일 Actions 운영은 미확인/미구현이며 V는 NOT_AVAILABLE다.
- Macro #104는 원기관4축 raw 입력/48칸 근거 계약, #112는 후속4축 출처 조사다. 실제8축 국면 계산·producer·앱 연결은 완료되지 않았다. FRED/ALFRED는 차단한다.
- #116은 기기 관심·그룹·포트폴리오·안전 설정의 통합 백업/불러오기를 연결했고 #117은 표시 전용 JS 지표·합성 참조 대조를 병합했다. 기존 Python #115는 여전히 미병합이다. 추가 범위와 통합 복원 동작을 확인하되 M3 가격/파생 결과·시트 ID·토큰/키는 백업 제외다.

## 열린 PR 및 정리

이번 사용자 지시와 대기열에 관련된 항목만 다룬다. 다른 열린 PR을 닫거나 브랜치를 삭제하지 않는다.

| PR | 상태·내용 |
| --- | --- |
| [#111](https://github.com/kco994553-star/Investment-System1/pull/111) | 현행 engine 세 계산·#105 연결 완성. 현행 엔진 세 계산만 유지. 관련62개 통과. 이전 전체1502통과·1canonical CSP실패·subtests358(아래 CSP 장애). 미병합·회귀 해소/최종 체크 대기(조건부 자체 병합 가능). |
| [#115](https://github.com/kco994553-star/Investment-System1/pull/115) | 독립 Research 표시 지표·GSQ-015. 관련89개 통과·독립 리뷰 지적 없음·최종 CI6개/실행53단계 성공. 전체1529통과·1실패·subtests358(같은 CSP 장애). 미병합·승인 대기. |
| [#103](https://github.com/kco994553-star/Investment-System1/pull/103) | 사용자 지시로 닫음. canonical 단일 인수인계가 최신 현황을 반영하므로 이전 현황 초안을 이력으로 보존. |
| [#107](https://github.com/kco994553-star/Investment-System1/pull/107) | 사용자 지시로 닫음. 정식 M3 #106·#108·#110 이후 이전 계약 테스트 초안을 정리하며 미병합 브랜치/이력 보존. |
| [#109](https://github.com/kco994553-star/Investment-System1/pull/109) | 이미 CLOSED·미병합 확인. 코덱1에게 종료 유지 확인만 요청; 코덱2는 PR 상태·Worker·브랜치 변경 없음. |

## 현재 검증 장애

`tests/test_app_nav_ia.py::test_navigation_does_not_expand_approved_external_csp_permissions`가 #113 이후 canonical07ba93e3 단독 checkout과 #111·#115에서 동일하게 실패했다. CSP connect-src에 Worker 출처1개가 추가됐지만 기대값은 이전 목록이다. #114는 해당 앱/테스트를 바꾸지 않았다. 코덱1 앱/CSP 계약 검증 범위이며 두 Python PR의 diff 밖이다. 코덱2는 테스트를 완화하거나 앱·워크플로를 수정하지 않는다.

최신 canonical 이전에는 #111 전체1503·#115 전체1530과 각각 subtests358이 통과했다. 제한된 CI 성공을 전체 suite 성공으로 보고하지 않으며 26E 미변경 PR은 조건부 자체 병합할 수 있으나 현재 코드의 회귀 해소를 기다린다. 26E 변경 PR은 별도 사용자 승인을 기다린다. 문서 PR의 자체 병합은 .md만 변경·최종 실행 필수 체크 성공·실패0이라는 기존 사용자 승인 범위를 따른다.

## 결정 대기·유지 경계

- 필요한 결정은 [로드맵 v2의 별도 표](implementation/docs/ROADMAP_2026Q4.md#사용자-결정조치가-필요한-항목)에 모았다: 26E 변경 PR(#115) 병합, SEC 운영 범위/일정, V 재계산, Macro 후속 입력 의미, 추가 백업/Trades, DART 알림, EDINET 등록, 예비 가격 조건, 실적/13F/뉴스 범위, 모델6관점, forward 시작.
- M3는 TARGET19 + 기기 ★ + 비공개 Universe 검증 시총 상위N. **N=20·시총 불일치10%**는 확정이며 근거 있는 SHARE_CLASS_BASIS는 표시만·자동 보정 없음. identity/주식 종류·통화/단위·가용시각·권리 근거 부족은 차단한다. 개인 목록·가격·시총·순위·시트 ID는 공개하지 않는다.
- Research 기본값은 사용자 승인 표시 범위이며 Model/TSV/QGV 채택이 아니다. warm-up null·0 대체 금지·RAM 전용·공개 serializer 연결 금지를 유지한다.
- **DART는 사용자가 10/11 18시 이후 DART_API_KEY 등록을 알린 뒤에만 착수**한다. 아직 알림이 없으며 시간 경과를 등록/승인으로 추정하지 않는다. 그전에는 코드·키 존재 확인·인증/API 실행도 금지다.
- QGV v2 보류, 기존 Holdout **UNCONFIRMED·v2 근거 제외·미사용** 유지. forward 데이터 시작 시점은 향후 사용자 결정이며 에이전트는 기간을 선택·사용하지 않는다.

## 현재 사용자 대기열

아래 순서로 항목당 PR1개를 보존하고 중간 항목 보고 없이 완료/필수 결정 시 묶어 보고한다. **26E 결정 기록 변경이 없는 PR은 실행된 필수 체크 전부 성공·실패0이면 자체 병합 가능**하다. 이 선택은 force push·ruleset·AUTONOMY_MODE·워크플로/Worker/웹 수정 허가가 아니다.

1. 실행 로드맵 v2·#103/#107 종료(이번 문서 PR), #109는 이미닫힘·코덱1 확인 요청만.
2. #111 현행 세 계산 마무리·차트 지표 Python 참조/코덱1 JSON 합성 벡터. 사용자 답변대로 #111은 세 계산만, #115는 Research runtime·Python 참조·합성 JSON 벡터·GSQ-015를 함께 유지한다.
3. US17 SEC companyfacts/submissions 취득 모듈·Secret 이름 참조·retry/rate limit·실행 진입점(워크플로는 코덱1), 실제 호출/Secret 출력 없음.
4. SEC 10-Q/10-K 제출 패턴의 **예상 시기**(확정 실적 발표일 아님), 이어서 기존 정의만 사용하는 가격 인자/RAM-only Vv1 순수 함수·미확정 요소 NOT_AVAILABLE.
5. 공식v1 비중 복사본/사용자 비중·합100·결측수·PREVIEW 재계산, 4축→기존 Macro 엔진/정부 자료 화면JSON·후속4축 입력, 13F parser/분기변화 순으로 각각 별도 PR.
6. EDINET은 키 요구를 확인하고 필요하면 보고 후 대기. DART는 지정 시각 이후 사용자 등록 알림 전 비착수다.

코덱1은 앱/CSP 회귀·기기/Worker/Actions 연결을 맡는다. 모델6관점/forward 시작·보관·입력 의미 등의 별도 사용자 결정과 로드맵의 나머지 항목은 유지한다. 이번 구현 대기열을 실제 대량 수집·배포·Holdout·새 방법론/가중치 승인의 근거로 확대하지 않는다.

## 외부 서비스·저장 위치

설정 이름만 기록한다. 실제 값·서비스 응답·개인 계정을 이번 작업에서 조회하지 않았다.

| 서비스 | 현재 범위 | 저장 경계 |
| --- | --- | --- |
| BLS·BEA·Treasury | 원기관 요청 계획/제공 응답 파서. BEA 설정 이름 BEA_USERID. | Macro 근거와 개인 가격 보관 조건은 별개, 공개 앱 연결 미완료. |
| FRED·ALFRED | 서면 허가 전 차단. | 새 호출/키 조회 없음. |
| SEC EDGAR | M1 수동 CLI·Q/G 후보·SEC shares 검증. SEC_USER_AGENT·INVESTMENT_SYSTEM_SEC_UA. | 공개 가능 재무만 후속 Actions 후보, 가격/개인 선택 roster는 제외. |
| Google Identity·Sheets | 기존 readonly 로그인·Quotes, Universe/M3·Trades 후속 연결. | 토큰/RAM 파생값·Universe ID는 저장/공개 제외. 기존 Quotes와 M3 RAM 경계를 구분. |
| Cloudflare·Pages | #102·#113·#114 코드/metadata 확인. CLOUDFLARE_API_TOKEN·CLOUDFLARE_ACCOUNT_ID·ALLOWED_EMAIL·GOOGLE_CLIENT_ID. | 실제 배포·인증은 코덱1 확인 범위; DO는 가격 일봉 저장소가 아님. |
| DART·EDINET | 숫자 재무 adapter 준비/등록 대기. DART_API_KEY는 이름만. | 사용자 등록 알림/조건 전 실제 호출·키 조회 없음. |
| Tiingo·KRX 등 가격 출처 | 무료/권리/시장 coverage 조건 확인 대기. KRX_API_KEY는 GSQ-009 등록 보고. | 개인 RAM·공개 금지 유지, 실제 계정/키 검증 없음. |

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
