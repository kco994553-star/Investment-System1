# 현재 인수인계

확인일: 2026-10-10 UTC. 현재 상태는 이 파일에서 시작하고 운영은 [WORKING_RULES.md](WORKING_RULES.md)를 따른다. 최신 사용자 결정은 [26E GSQ-015](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-015--26e-research-표시-전용-기본값한국식-모델-채택-아님-2026-10-10-utc), **표시 전용 기본값(한국식), 모델 채택 아님**이다. M3의 N=20·10%는 GSQ-014를 유지한다.

## 기준 HEAD

- 기본 브랜치: `claude/investment-system-top500-validation-alrugm`.
- 확인한 원격 canonical HEAD: `07ba93e335f5af57aa00e657a6ea0ddb9aefa7a0` (코덱1 #113 병합). 이전 코덱2 코드 HEAD는 `83a2d0e3e5bf7ecf539a74a67f1a32c08480d0bb` (#110), 조사 문서 HEAD는 `31932c25d06ec27648c70f87153c94c92f3290d0` (#112)다. #111·#115는 최신 canonical을 정상 병합으로 반영했으며 아직 기준 코드에 포함되지 않은 병합 승인 대기 PR이다.
- 코덱1의 [#98](https://github.com/kco994553-star/Investment-System1/pull/98) 병합을 먼저 확인했다. 이후 사용자 승인 순서로 [#104](https://github.com/kco994553-star/Investment-System1/pull/104) → [#105](https://github.com/kco994553-star/Investment-System1/pull/105) → [#106](https://github.com/kco994553-star/Investment-System1/pull/106)를 병합했다. 각각 최종 HEAD의 실행 체크 6개와 실행 단계 전부 성공·실패 0을 확인했다.
- #104는 최신 canonical을 정상 병합으로 반영하고 base를 canonical로 전환했다. #98 변경분은 수정하지 않았고 각 구현 PR diff는 허용된 Python·tests·.md 범위다. force push·ruleset·AUTONOMY_MODE 변경은 없다.
- #95·#96·#97·#100·#101은 이전에 병합됐다. 공개 가격 수집·출력 차단, Frozen 메타데이터·원본 TARGET 보존은 유지한다.
- #108은 GSQ-014·인수인계 문서로 병합됐다. 이후 사용자가 승인한 [#110](https://github.com/kco994553-star/Investment-System1/pull/110)에 최신 canonical을 정상 병합으로 반영하고 최종 실행 체크 6개·실행 단계 53개 전부 성공·실패 0 확인 후 병합했다. SHARE_CLASS_BASIS는 근거 기반 표시이며 자동 보정·기기/Worker 연결은 추가하지 않았다.

- [#112](https://github.com/kco994553-star/Investment-System1/pull/112)는 Macro 나머지4축 원기관 조사·인수인계의 .md 전용 PR로 병합됐다. 최종 실행 체크6개·실행 단계53개 전부 성공·실패0을 확인했으며 구현·실제 수집·새6상태 규칙은 없다.

## 배포 상태

- 이번 작업은 Python·문서 병합이며 배포·실제 데이터 수집·브라우저 연결을 실행하지 않았다.
- 코덱1의 열린 [#103](https://github.com/kco994553-star/Investment-System1/pull/103) 현황 보고에 따르면 [Worker 실행 38018407666](https://github.com/kco994553-star/Investment-System1/actions/runs/38018407666)의 실제 Worker·SQLite DO 배포는 성공했고 전체 워크플로는 마지막 무인증 검사에서 실패했다(`ANONYMOUS_CHECK_CACHE_FAILED`). 이 작업에서 로그·Secret·실서비스 응답을 재조회하지 않았다.
- #103의 당시 보고에서 private history는 OFF였다. 이후 코덱1 [#113](https://github.com/kco994553-star/Investment-System1/pull/113)이 병합되어 앱을 검증된 Worker로 연결하고 email 재동의를 추가했다. #102도 병합된 상태를 GitHub metadata로 확인했다. 이번 작업은 변경을 정상 병합으로 보존했으며 서비스·로그·개인 계정·Secret의 값을 재조회하지 않았다. 필요한 설정 이름은 `ALLOWED_EMAIL`, `GOOGLE_CLIENT_ID`다.
- [GitHub Pages](https://kco994553-star.github.io/Investment-System1/)의 이전 HTTP 200 확인과 최신 화면·배포 SHA는 구분한다. 이번 병합이 실제 기기·Worker·Pages 연결 완료를 뜻하지 않는다.

## 열린 PR 요약

이번 대기열과 관련된 PR만 표시한다. 아래 과거 정리안은 현재 열린 PR 목록이 아니며 다른 PR을 닫거나 병합하지 않는다.

| PR | 내용 | 상태·검증 |
| --- | --- | --- |
| [#103](https://github.com/kco994553-star/Investment-System1/pull/103) | 이전 인수인계 현황 갱신 | 열려 있는 별도 현황 PR; 이 문서는 최신 결정·병합 결과를 반영. 닫기·병합하지 않음. |
| [#107](https://github.com/kco994553-star/Investment-System1/pull/107) | M3 계산 계약 초안 | 코덱1의 보존된 초안; 기기·Worker 연결은 코덱1 범위. |
| [#109](https://github.com/kco994553-star/Investment-System1/pull/109) | Worker 대시보드 단일 파일·메모리 제한 대안 | 코덱1의 별도 Worker PR; 이 작업에서 병합·배포하지 않음. |
| [#111](https://github.com/kco994553-star/Investment-System1/pull/111) | 현행 engine 세 계산·#105 어댑터 연결 | 완성·병합 승인 대기. 새22개+기존 일봉40개=62 통과. 최신 canonical 반영 후 전체1502 통과·1 실패·subtests358 통과(아래 기준브랜치 CSP 장애). 독립 리뷰 중대 지적 없음; CI6개 성공과 전체 테스트 실패는 구분한다. |
| [#115](https://github.com/kco994553-star/Investment-System1/pull/115) | 표시 전용 지표 v1·GSQ-015 | #111과 독립된 canonical 기반 코드 PR. 새49개+기존 일봉40개=89 통과. 최신 canonical 반영 후 전체1529 통과·1 실패·subtests358 통과(아래 동일 CSP 장애). 독립 리뷰 지적 없음. role=RESEARCH_DISPLAY_ONLY·RAM·null; 공개 serializer·Model/TSV/QGV 연결 없음. 병합 승인 대기, 최종 CI는 PR에서 확인. |

## 기준브랜치 검증 장애

`tests/test_app_nav_ia.py::test_navigation_does_not_expand_approved_external_csp_permissions`가 최신 canonical `07ba93e3`와 #111·#115에서 동일하게 실패한다. #113은 앱 CSP의 `connect-src`에 Worker 접속 출처1개를 추가했지만 해당 테스트는 이전3개 출처만 기대한다. 원격 canonical의 별도 detached checkout에서 테스트1개 실패를 재현했다. 실제 Worker/개인 계정/Secret/API를 조회하지 않았고 endpoint 값은 기록하지 않는다.

이 장애는 두 Python 구현 diff 밖의 **코덱1 앱·CSP 계약 검증 범위**다. 코덱2는 앱·워크플로·해당 테스트를 변경하거나 체크를 우회하지 않는다. 최신 canonical 이전에는 #111 전체1503·#115 전체1530과 각각 subtests358이 통과했다. 위 표는 최신 상태로 바꿨으며, CI의 제한된 체크 성공을 전체 suite 성공으로 보고하지 않는다. 코드 병합은 사용자 승인뿐 아니라 이 기준브랜치 장애의 해소도 대기한다.

## 결정 대기

1. **#111·#115 코드 PR 병합 승인**. 사용자 결정으로 현행 세 계산과 표시 전용 기본값의 구현 범위는 확정됐다. 두 구현은 완성·독립 리뷰 후 보존한다. 기준브랜치 CSP 장애가 남아 있으며 사용자 승인 없이 병합하지 않는다. Research 지표는 표시용이며 모델 채택 또는 Model/TSV/QGV 입력 승인이 아니다.
2. 코덱1의 기기·Worker 연결 및 인증 설정 준비. 실제 비밀값·시트 ID는 대화나 저장소에 기록하지 않는다.
3. QGV v2 착수와 forward 검증 시작 시점은 향후 사용자 결정이다. 기존 Holdout은 **UNCONFIRMED 유지·v2 검증 근거 제외**이며 에이전트는 기간을 선택·사용하지 않는다.
4. **DART 착수 조건:** 사용자가 **10/11 18시 이후 DART_API_KEY 등록을 알리면** 시작한다. 그전에는 코드 작성·키 존재 확인·인증/API 실행을 포함해 착수하지 않는다. 현재 등록 알림은 없으며 시간 경과만으로 승인/등록을 추정하지 않는다.

M3 범위는 **TARGET19 + 기기 ★ + 비공개 Universe 시트의 검증된 시총 상위 N**이다. **기본 N=20, 시총 불일치 임계=10%**는 GSQ-014로 확정됐다. 기존 `abs(G-R)/R >= 0.10` 품질 검사와 R=검증된 SEC 주식 수×같은 행 price를 유지한다. 순수 함수에는 `SelectionConfig(20, True)`·`QualityConfig(0.10, True)`를 명시적으로 전달하며 기기 기본값 연결은 코덱1 범위다.

SEC 주식 수와 해당 상장 주식 종류의 기준 차이가 근거로 확인된 경우에만 **SHARE_CLASS_BASIS**를 표시한다. 종목 문자열이나 큰 오차만으로 원인을 추정하지 않는다. 현재 근거 부족 차단을 유지하고 합산·비율 추정·자동 보정·새 방법론·가중치를 추가하지 않는다. 실제 시트 목록·가격·시총·순위·시트 ID는 비공개 기기 RAM 경계에 둔다.

## 다음 할 일 5개

1. 코덱2는 #111·#115의 기준브랜치 CSP 장애 해소와 사용자 병합 승인을 기다린다. 현행 engine 세 계산과 Research 표시 지표는 분리하며 출력은 RAM 전용이다.
2. 코덱1은 향후 [Research 표시 계약](implementation/docs/technical_live_data/RESEARCH_DISPLAY_INDICATORS_V1.md)을 기기 차트에 연결할 때 role·null·가격 basis 경계를 유지한다. 이번 Python PR은 화면·Worker를 수정하지 않으며 Model/TSV/QGV·공개 serializer 연결은 금지다.
3. 코덱1은 #106·#110의 [M3 계약](implementation/docs/daily_data_pipeline/M3_SUBSET_IMPLEMENTATION_SPEC.md)을 기기·Worker에 연결한다. N=20·10%와 근거 기반 표시를 사용하며 identity·주식 종류·통화/단위·가용 시각·권리 미확인은 차단한다. #98 M2 실제 입력·배포도 코덱1 범위다.
4. 코덱2는 DART 등록 알림을 기다린다. 지정 시각 이후에도 사용자 알림이 없으면 착수하지 않으며 키 값을 조회·출력하지 않는다.
5. QGV v2는 보류하고 Holdout은 사용하지 않는다. 새 코드 PR은 완성·검증 뒤 사용자 병합 승인 대기로 보존한다.

## 외부 서비스·저장 위치

설정 이름만 기록한다. 이번 작업에서 실제 서비스·계정·키·개인 시트를 조회하지 않았다.

| 서비스 | 현재 범위 | 저장 경계 |
| --- | --- | --- |
| BLS·BEA·Treasury | 원기관 순수 요청 계획·제공 응답 파서; 실제 호출 없음. BEA 설정 이름은 BEA_USERID. | 제공 입력·근거는 메모리·로컬; 공개 출력 연결 없음. |
| FRED·ALFRED / FRED 공개 CSV | 서면 허가 전 차단 유지. | 새 호출·키 조회 없음. |
| SEC EDGAR | 제공 응답의 식별·주식 수·이용 시각 검증; 실제 수집 없음. | 원시 응답을 공개 출력에 넣지 않음. 식별 설정 이름은 SEC_USER_AGENT·INVESTMENT_SYSTEM_SEC_UA. |
| Google Identity·Sheets | 기존 readonly 로그인으로 Universe 1회 읽기는 코덱1 연결 범위. | access token·Universe ID·목록·가격·시총·순위는 RAM; ID는 저장소·기기 설정·백업 제외. |
| Cloudflare Workers·SQLite DO | 배포 상태는 위 코덱1 보고 참조; 앱 연결은 #113, 실제 상태는 위 코덱1 보고와 병합 시점 참조. | 설정 이름 CLOUDFLARE_API_TOKEN·CLOUDFLARE_ACCOUNT_ID·ALLOWED_EMAIL·GOOGLE_CLIENT_ID; 값 출력 금지. DO는 가격 일봉 저장소가 아님. |
| Yahoo / Tiingo / KRX / Stooq / iShares / Alpha Vantage | 이번 구현에서 호출하지 않음. 기존 공개 수집 차단·disabled 상태 유지. | 기존 사본의 정리·이력 재작성은 수행하지 않음. |

기존 기기 ★는 읽되 M3 파생 manifest·품질 비교·순위는 RAM-only다. 기존 Quotes IndexedDB 저장과 M3 Universe 경계를 혼동하지 않는다. 실제 대량 수집·공개 산출물 연결·Holdout 사용은 없다.

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
