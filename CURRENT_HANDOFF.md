# 현재 인수인계

확인일: 2026-10-10 UTC. 현재 상태는 이 파일에서 시작하고 운영은 [WORKING_RULES.md](WORKING_RULES.md)를 따른다. 현재 사용자 결정은 [26E GSQ-014](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-014--26e-m3-설정-확정병합-순서주식-종류-기준-표시-2026-10-10-utc)다.

## 기준 HEAD

- 기본 브랜치: `claude/investment-system-top500-validation-alrugm`.
- 확인한 원격 코드 HEAD: `024b73b8a1032a24b7307ba4519f76f86148421c`. 이 인수인계 문서 PR 자체의 병합 HEAD는 GitHub에서 확인한다.
- 코덱1의 [#98](https://github.com/kco994553-star/Investment-System1/pull/98) 병합을 먼저 확인했다. 이후 사용자 승인 순서로 [#104](https://github.com/kco994553-star/Investment-System1/pull/104) → [#105](https://github.com/kco994553-star/Investment-System1/pull/105) → [#106](https://github.com/kco994553-star/Investment-System1/pull/106)를 병합했다. 각각 최종 HEAD의 실행 체크 6개와 실행 단계 전부 성공·실패 0을 확인했다.
- #104는 최신 canonical을 정상 병합으로 반영하고 base를 canonical로 전환했다. #98 변경분은 수정하지 않았고 각 구현 PR diff는 허용된 Python·tests·.md 범위다. force push·ruleset·AUTONOMY_MODE 변경은 없다.
- #95·#96·#97·#100·#101은 이전에 병합됐다. 공개 가격 수집·출력 차단, Frozen 메타데이터·원본 TARGET 보존은 유지한다.

## 배포 상태

- 이번 작업은 Python·문서 병합이며 배포·실제 데이터 수집·브라우저 연결을 실행하지 않았다.
- 코덱1의 열린 [#103](https://github.com/kco994553-star/Investment-System1/pull/103) 현황 보고에 따르면 [Worker 실행 38018407666](https://github.com/kco994553-star/Investment-System1/actions/runs/38018407666)의 실제 Worker·SQLite DO 배포는 성공했고 전체 워크플로는 마지막 무인증 검사에서 실패했다(`ANONYMOUS_CHECK_CACHE_FAILED`). 이 작업에서 로그·Secret·실서비스 응답을 재조회하지 않았다.
- 같은 보고에서 인증 설정 미준비로 앱 private history는 OFF다. 필요한 설정 이름은 `ALLOWED_EMAIL`, `GOOGLE_CLIENT_ID`이며 실제 값은 기록하지 않는다. 후속 검증 수정은 #102다.
- [GitHub Pages](https://kco994553-star.github.io/Investment-System1/)의 이전 HTTP 200 확인과 최신 화면·배포 SHA는 구분한다. 이번 병합이 실제 기기·Worker·Pages 연결 완료를 뜻하지 않는다.

## 열린 PR 요약

이번 대기열과 관련된 PR만 표시한다. 아래 과거 정리안은 현재 열린 PR 목록이 아니며 다른 PR을 닫거나 병합하지 않는다.

| PR | 내용 | 상태·검증 |
| --- | --- | --- |
| [#102](https://github.com/kco994553-star/Investment-System1/pull/102) | Worker 무인증 검증 User-Agent 수정 | 코덱1 범위; 이 작업에서 병합·재배포하지 않음. |
| [#103](https://github.com/kco994553-star/Investment-System1/pull/103) | 이전 인수인계 현황 갱신 | 열려 있는 별도 현황 PR; 이 문서는 최신 결정·병합 결과를 반영. 닫기·병합하지 않음. |
| [#107](https://github.com/kco994553-star/Investment-System1/pull/107) | M3 계산 계약 초안 | 코덱1의 보존된 초안; 기기·Worker 연결은 코덱1 범위. |
| [#108](https://github.com/kco994553-star/Investment-System1/pull/108) | GSQ-014·현재 인수인계 | 문서 전용; 최종 실행 체크 모두 성공·실패 0이면 자체 병합. |
| [#110](https://github.com/kco994553-star/Investment-System1/pull/110) | SHARE_CLASS_BASIS 표시 | 순수 Python·합성 검사·명세. 생성 후 별도 코드 병합 승인 대기; 자동 보정 없음. |

## 결정 대기

1. SHARE_CLASS_BASIS 후속 코드 PR의 병합 승인. 생성만 승인됐으며 이 작업에서는 병합하지 않는다.
2. 코덱1의 기기·Worker 연결 및 인증 설정 준비. 실제 비밀값·시트 ID는 대화나 저장소에 기록하지 않는다.
3. QGV v2 착수와 forward 검증 시작 시점은 향후 사용자 결정이다. 기존 Holdout은 **UNCONFIRMED 유지·v2 검증 근거 제외**이며 에이전트는 기간을 선택·사용하지 않는다.

M3 범위는 **TARGET19 + 기기 ★ + 비공개 Universe 시트의 검증된 시총 상위 N**이다. **기본 N=20, 시총 불일치 임계=10%**는 GSQ-014로 확정됐다. 기존 `abs(G-R)/R >= 0.10` 품질 검사와 R=검증된 SEC 주식 수×같은 행 price를 유지한다. 순수 함수에는 `SelectionConfig(20, True)`·`QualityConfig(0.10, True)`를 명시적으로 전달하며 기기 기본값 연결은 코덱1 범위다.

SEC 주식 수와 해당 상장 주식 종류의 기준 차이가 근거로 확인된 경우에만 **SHARE_CLASS_BASIS**를 표시한다. 종목 문자열이나 큰 오차만으로 원인을 추정하지 않는다. 현재 근거 부족 차단을 유지하고 합산·비율 추정·자동 보정·새 방법론·가중치를 추가하지 않는다. 실제 시트 목록·가격·시총·순위·시트 ID는 비공개 기기 RAM 경계에 둔다.

## 다음 할 일 5개

1. 코덱2는 승인된 #104 → #105 → #106 병합과 GSQ-014 문서·후속 표시 PR을 마친 뒤 대기한다.
2. 코덱1은 [M3 구현 명세](implementation/docs/daily_data_pipeline/M3_SUBSET_IMPLEMENTATION_SPEC.md)와 #106의 Python 계약을 기기·Worker 경로에 연결한다. Python 함수의 병합이 브라우저 실행 연결을 뜻하지 않는다.
3. 코덱1은 확정 N=20·10% 설정과 근거 기반 SHARE_CLASS_BASIS 표시를 기기에서 반영한다. 실제 source identity·발행주식 수의 클래스/통화/단위·이용 시각·권리를 확인하고 부족하면 차단한다.
4. 코덱1은 #98 M2 후보의 실제 입력 조건과 배포 상태를 맡는다. 실제 입력이 없으면 NOT_AVAILABLE을 유지한다. Worker #102 병합·재실행은 해당 승인 범위에서만 수행한다.
5. 매크로는 원기관 BLS·BEA·Treasury의 순수 어댑터·PIT 입력 근거까지 구현됐다. 실제 수집·역사적 최초 발표본 확보·미승인 6상태 규칙과 기술적 분석의 실제 입력 연결은 후속 승인 범위에서만 진행한다. FRED/ALFRED는 서면 허가 전 차단한다.

## 외부 서비스·저장 위치

설정 이름만 기록한다. 이번 작업에서 실제 서비스·계정·키·개인 시트를 조회하지 않았다.

| 서비스 | 현재 범위 | 저장 경계 |
| --- | --- | --- |
| BLS·BEA·Treasury | 원기관 순수 요청 계획·제공 응답 파서; 실제 호출 없음. BEA 설정 이름은 BEA_USERID. | 제공 입력·근거는 메모리·로컬; 공개 출력 연결 없음. |
| FRED·ALFRED / FRED 공개 CSV | 서면 허가 전 차단 유지. | 새 호출·키 조회 없음. |
| SEC EDGAR | 제공 응답의 식별·주식 수·이용 시각 검증; 실제 수집 없음. | 원시 응답을 공개 출력에 넣지 않음. 식별 설정 이름은 SEC_USER_AGENT·INVESTMENT_SYSTEM_SEC_UA. |
| Google Identity·Sheets | 기존 readonly 로그인으로 Universe 1회 읽기는 코덱1 연결 범위. | access token·Universe ID·목록·가격·시총·순위는 RAM; ID는 저장소·기기 설정·백업 제외. |
| Cloudflare Workers·SQLite DO | 배포 상태는 위 코덱1 보고 참조; 앱 private history OFF. | 설정 이름 CLOUDFLARE_API_TOKEN·CLOUDFLARE_ACCOUNT_ID·ALLOWED_EMAIL·GOOGLE_CLIENT_ID; 값 출력 금지. DO는 가격 일봉 저장소가 아님. |
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
