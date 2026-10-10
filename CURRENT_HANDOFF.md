# 현재 인수인계

확인일: 2026-10-10 UTC. 현재 상태는 이 파일에서 시작하고, 운영은 [WORKING_RULES.md](WORKING_RULES.md)를 따른다. 앞으로 승인된 PR 병합 직후 이 파일을 갱신한다. 아래 흩어진 문서는 세부 설계와 과거 상태의 참고 자료다.

## 기준 HEAD

- 기본 브랜치: `claude/investment-system-top500-validation-alrugm`
- 확인한 원격 HEAD: `7ffd856fd585dc2862591e2540d56d23eb076f47`.
- 이번 사용자 승인으로 #100 → #95 → #96 → #97을 순서대로 병합했다. #96·#97은 각각 실행된 필수 체크 6개 성공·실패 0건을 병합 직전에 확인했다. 다른 PR은 병합하지 않았다.
- [#76](https://github.com/kco994553-star/Investment-System1/pull/76)은 2026-10-09 09:47:52 UTC에 병합됐다. 기본 브랜치의 입력 변수 34개와 한국어·영어 안내 34개가 모두 일치한다.
- #96의 공개 출력·수집 28개 경로 차단과 #97의 DATA 140개 정리(138개 삭제·2개 테스트 입력 교체)가 반영됐다. 보류 5개·Frozen 메타데이터·원본 TARGET은 보존했다. Git 이력과 기존 Pages·Actions 사본은 재작성하지 않았다.

## 배포 상태

- Worker 주소: https://private-investment-history.kco994553.workers.dev
- [수동 배포 실행 38018407666](https://github.com/kco994553-star/Investment-System1/actions/runs/38018407666): whoami 사전 점검과 실제 Worker·SQLite Durable Objects 배포는 성공했다. 전체 워크플로는 마지막 무인증 검사에서 실패했고 마스킹된 코드는 `ANONYMOUS_CHECK_CACHE_FAILED`다.
- 별도 읽기 전용 검사에서 명시적인 검증용 User-Agent를 쓰면 3개 경우 모두 통과했다. Origin 없음·허용되지 않은 Origin은 `403 ORIGIN_FORBIDDEN`, 허용 Origin·무인증은 `503 CONFIG_UNAVAILABLE`; 모두 `Cache-Control: private, no-store, max-age=0`다. Google·Yahoo 데이터 요청을 수행하지 않았다. 이 검사가 실패한 워크플로 자체를 성공으로 바꾸지는 않는다.
- 기존 검증기의 기본 urllib User-Agent 응답 차이를 고치는 별도 코드 PR을 준비한다. 인증 설정이 준비되지 않았으므로 앱 private history는 OFF를 유지한다. 필요한 설정 이름은 `ALLOWED_EMAIL`, `GOOGLE_CLIENT_ID`다. 실제 값은 조회·출력하지 않았다.
- Wrangler 4.149.0에서 `compatibility_date = 2026-10-09`를 유지했고 CI Node 22의 실제 배포도 성공했다. Edit Cloudflare Workers 템플릿의 `Workers Scripts Write` 및 `Account Settings Read`로 사전 점검·SQLite DO 배포가 성공했으며, 추가 DO 전용 권한 부족은 나타나지 않았다.
- [GitHub Pages](https://kco994553-star.github.io/Investment-System1/)는 이전 HTTP 200 확인만 있다. #96·#97 병합 후 최신 화면 내용·배포 SHA는 별도 확인 대상이다.

## 열린 PR 요약

확인 시점 열린 PR은 18개다. 새 코드·현황 PR을 만들면 이 표를 같은 현황 PR에서 갱신한다. 아래 추가 구현은 사용자 승인 전 병합하지 않는다.

| PR | 내용 | 상태·검증 |
| --- | --- | --- |
| [#98](https://github.com/kco994553-star/Investment-System1/pull/98) | M2 Q·G 후보 앱 표시, V NOT_AVAILABLE, “보정 전·가격 미포함” | WIP. 기존 전체 오프라인 1,304개+하위 검사 347개·후보/기존 화면 한영·모바일/데스크톱 검사 통과. 독립 리뷰에서 모순된 보정 상태·가격 사용 플래그 거절을 보완할 1건 확인, 수정 후 최종 검증 예정. |
| [#101](https://github.com/kco994553-star/Investment-System1/pull/101) | Codex2의 최신 M3·비공개 Universe 상위 N 명세 | 문서 PR, 병합하지 않음. 최신 명세는 이 PR의 파일을 기준으로 구현한다. N=20·상대오차 10%는 미확정 제안이다. |

M2의 실제 후보·financial blob 입력은 현재 체크아웃에 없다. 기본 출력은 NOT_AVAILABLE이며 합성 입력은 검증용이다. 가격 기반 값·원시 근거·새 순위·가중치는 공개 후보 출력에 넣지 않는다.

### 보존한 이전 기능 PR

| 번호 | 제목 | 권장 | 이유 |
| --- | --- | --- | --- |
| [#71](https://github.com/kco994553-star/Investment-System1/pull/71) | Chart public reference B: verified TARGET freshness, bilingual notice and scoped gate correction | 유지 | 미반영 TARGET 최신성·한영 안내 기능은 보존하되, 구 A-G/FPIA 문서와 오래된 배포 변경을 현 정책에 맞춰 정리 필요. |
| [#43](https://github.com/kco994553-star/Investment-System1/pull/43) | docs(ops): common GitHub API write-path instruction | 유지 | Git 전송 실패 시 API 대체 안내는 유효하므로 보존하되, 구 Global 담당자·과도한 증빙 요구를 현 운영 문서로 축약 필요. |
| [#31](https://github.com/kco994553-star/Investment-System1/pull/31) | Track C: approved CDR-012 v2 squaring and all-degenerate fail-closed | 유지 | 실제 bootstrap 제곱 계산·전부 퇴화 시 차단 수정이 있어 보존하되, 대량 증빙·통합 변경을 분리하기 전 병합 보류. |
| [#29](https://github.com/kco994553-star/Investment-System1/pull/29) | Existing Web: withheld producer-contract fixture and locale/mobile/failure E2E | 유지 | 보류 데이터 누출·한영·모바일·오류 상태를 검증하는 실제 브라우저 테스트가 유용하므로 현 UI에 맞춰 보존. |
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
| [#7](https://github.com/kco994553-star/Investment-System1/pull/7) | Entity Metadata Coverage: CIK-bound Top-500 search metadata (stacked on #6) | 유지 | CIK·종목·Universe 일치로 묶는 검색 메타데이터 확장이 미반영이므로 오인 연결 방지와 함께 보존. |
| [#4](https://github.com/kco994553-star/Investment-System1/pull/4) | Track C: C7 software frozen; C8-C10 policy packages await approval | 유지 | EVL·시계열 분할·검증 계산 코드가 대량 미반영이므로 보존하되 구 승인 문서·미승인 C8~C10과 분리 전 병합 보류. |

### 실행한 PR 정리

사용자 승인에 따라 #61·#47·#46·#45·#42·#40·#39·#38·#37·#36·#35·#34·#33·#32·#30·#28·#27·#26·#25·#24·#23·#22·#21·#9·#6, 총 25개를 닫았다. 각각 해당 PR에 닫는 이유 한 줄을 남겼다. 브랜치 삭제 0개이며 위 기능 PR 16개는 유지했다.

## 결정 대기

1. 앞으로 만들 Worker 검증 수정·#98 완성·매크로·M3·현황 갱신 PR의 병합 여부. 현재 추가 병합 승인은 없다.
2. Worker의 `ALLOWED_EMAIL`·`GOOGLE_CLIENT_ID` 설정 준비. 값은 대화나 저장소에 기록하지 않는다.
3. M3의 N과 Google/SEC 시총 상대오차 허용값. #101의 N=20·10%는 제안이므로 확인 전 자동 적용하지 않고 `CONFIG_CONFIRMATION_REQUIRED`로 차단한다.

## 다음 할 일 5개

1. Worker 무인증 검증기에 명시적인 User-Agent를 넣어 테스트·PR로 준비하고, 이후 승인된 병합·재실행에서 전체 워크플로 결과를 확인한다.
2. #98의 보정·가격 사용 모순 거절을 보완하고 최종 리뷰·필수 CI를 확인해 WIP를 해제한다. 실제 입력이 없으면 NOT_AVAILABLE을 유지한다.
3. Codex2 [매크로 4축 명세](implementation/docs/macro_data_rights/PHASE1_FOUR_AXES_IMPLEMENTATION_SPEC.md)의 BLS·BEA·Treasury 순수 입력 계약·파서·48칸 근거 표와 계약 테스트를 구현한다. 새 계산식·가중치는 만들지 않는다.
4. #101의 M3 명세로 TARGET19 + 기기 ★ + 비공개 Universe의 검증된 상위 N을 RAM에서 처리한다. 시트 전체 후보를 SEC shares × 같은 행 가격으로 비교한 뒤 선정하고, 설정 미확정·근거 부족은 차단한다. 실제 시트·비밀값을 조회하지 않고 합성 core부터 구현한다.
5. 새 PR 번호·검증·남은 실제 연결 조건을 이 파일에 갱신하고 묶어서 보고한다. D 모의 일봉/returns 작업은 최신 대기열 뒤로 보류한다.

## 외부 서비스·저장 위치

설정 이름만 기록한다. 존재·권한을 확인하지 않은 비밀값이 설정됐다고 간주하지 않는다.

| 서비스 | 상태 | 필요한 계정·설정/비밀값 이름 | 저장 위치 |
| --- | --- | --- | --- |
| Cloudflare Workers·SQLite DO | 배포 성공, 전체 워크플로 최종 검사 실패; 인증 설정 미준비 | Cloudflare 계정 / CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, ALLOWED_EMAIL, GOOGLE_CLIENT_ID | 배포 키: GitHub Secrets; 인증 설정: Worker; DO: 요청 제한 상태만 |
| Google Identity·Sheets | 기존 Quotes 선택 기능과 M3 Universe 연결은 구분; M3 구현 준비 | Google 계정·OAuth Web client / googleSheetsClientId, GOOGLE_CLIENT_ID | client ID: 앱 설정; token: 메모리; Sheet: Drive; 기존 Quotes 복사본: IndexedDB; M3 입력·파생값·Universe ID는 RAM-only·백업 제외 |
| BLS 공개 API | 매크로 순수 파서·플래너 구현 준비, 실제 호출 없음 | 계정·비밀값 없음 | 제공 응답: 메모리; 연구 입력: 로컬 |
| BEA API | 매크로 순수 파서·플래너 구현 준비, 실제 호출 없음 | 선택 BEA API 계정 / BEA_USERID | 향후 전송 계층의 실행 환경변수; 입력·근거: 메모리·로컬 |
| Treasury 공개 XML | 매크로 순수 파서·플래너 구현 준비, 실제 호출 없음 | 계정·비밀값 없음 | 제공 응답: 메모리; 연구 입력: 로컬 |
| FRED·ALFRED API / 공개 CSV | 서면 허가 전 차단 유지, 실제 연결 없음 | 선택 FRED API 계정 / FRED_API_KEY | 실행 환경변수 또는 /tmp/is1_fred_key; 기존 연구 결과: 로컬 |
| Alpha Vantage | disabled, 시세 fetch 없음 | 향후 선택 계정 / api_key | 브라우저 IndexedDB api-settings |
| Tiingo | 공개 수집 차단 #96 반영 | 선택 Tiingo 계정 / TIINGO_API_KEY | GitHub Secrets·실행 환경; 기존 raw store·Actions 사본 |
| KRX Open API | 공개 수집 차단 #96 반영 | KRX API 계정·권한 / KRX_AUTH_KEY | 실행 환경변수; 로컬 raw store |
| SEC EDGAR | 금융 어댑터·공개 수집 경계 #96 반영 | 계정 없음 / SEC_USER_AGENT, INVESTMENT_SYSTEM_SEC_UA | 식별 header: GitHub Secrets·실행 환경; 기존 raw store·Actions 사본 |
| Yahoo Finance | 개인 Worker upstream, 무인증 거절·설정 미준비 | Yahoo 키 없음; 개인 gateway는 Google 로그인 | Worker 응답·메모리(no-store); 기존 도구 raw store |
| Stooq / iShares | 공개 수집 차단 #96 반영 | 계정·비밀값 없음 | 기존 로컬 raw store·연구 결과 |

개인 포트폴리오·기존 시세 입력·설정·가져오기 기록은 앱 origin의 IndexedDB에 저장된다. localStorage에는 기존 기기 ★·언어·앱 설정과 선택한 Worker origin이 있다. M3는 ★ 스냅샷을 읽되 Universe 목록·가격·품질 비교·순위·시트 ID를 RAM에서만 처리하고 설정/백업에 넣지 않는다. Google access token은 메모리에만 있으며 DO는 가격 일봉을 저장하지 않는다.

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
