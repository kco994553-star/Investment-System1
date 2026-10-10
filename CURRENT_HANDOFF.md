# 현재 인수인계

확인일: 2026-10-10 UTC. 현재 상태는 이 파일에서 시작하고, 운영은 [WORKING_RULES.md](WORKING_RULES.md)를 따른다. 과거 현황 문서는 아래 참고 링크로 모았다.

## 기준 HEAD

- 기본 브랜치: `claude/investment-system-top500-validation-alrugm`
- 확인한 원격 코드/운영 HEAD: `7ffd856fd585dc2862591e2540d56d23eb076f47` (#100 규칙·#95 배포 진단·#96 공개 경계·#97 자료 정리 병합 포함). 최신 M3 문서 반영은 [#101](https://github.com/kco994553-star/Investment-System1/pull/101)이며 실제 병합 HEAD는 해당 PR/GitHub 기본 브랜치를 기준으로 확인한다.
- 기본 브랜치와 아래 미병합 작업은 구분한다. #95·#96·#97·#100은 병합됐고 #98은 아직 후속 PR이다. #101은 기본 브랜치에 대한 M3 문서 PR이다.
- [#76](https://github.com/kco994553-star/Investment-System1/pull/76)은 2026-10-09 09:47:52 UTC에 병합됐다. 현재 기본 브랜치 카탈로그의 입력 변수 34개와 한국어·영어 안내 34개가 모두 일치한다.

## 배포 상태

- [GitHub Pages](https://kco994553-star.github.io/Investment-System1/): 현재 주소 HTTP 200 확인. 이 응답은 #95~#98의 배포나 화면 내용의 최신성을 보증하지 않는다.
- Cloudflare Worker: #95는 병합됐다. 이후 [수동 배포 재실행](https://github.com/kco994553-star/Investment-System1/actions/runs/38018407666)은 completed/failure다. 이번 M3 문서 작업은 원인/로그/Secret을 조사하거나 재배포하지 않았다. 성공 배포는 확인되지 않았으며 앱 private history는 OFF다. 이전 사용자 확인은 이메일 인증·workers.dev 등록·Account ID 일치다.
- Wrangler 4.149.0의 credential-free dry-run·로컬 런타임에서 `compatibility_date = 2026-10-09` 사용을 확인해 날짜를 유지했다. Node 22의 실제 재실행은 위 실패 상태이며 성공 배포로 표시하지 않는다.
- SQLite Durable Objects 배포 권한 `Workers Scripts Write`(대시보드 Workers Scripts Edit), whoami 사전 점검 권한 `Account Settings Read`는 Edit Cloudflare Workers 템플릿에 포함된다. 별도 Durable Objects 권한 부족은 확인되지 않았으며, 실제 토큰 권한·계정 범위는 승인 후 사전 점검에서 확인한다.
- #96/#97의 공개 가격 경로 차단과 HEAD 자료 정리는 기본 브랜치에 반영됐다. 실제 Pages 최신 배포 반영은 이 문서 작업에서 확인하지 않았고, Git 이력과 기존 Pages·Actions 사본은 재작성하지 않았다.

## 열린 PR 요약

| PR | 내용 | 상태·검증 |
| --- | --- | --- |
| [#98](https://github.com/kco994553-star/Investment-System1/pull/98) | `[WIP]` M2 Q·G 후보 별도 화면, V NOT_AVAILABLE, “보정 전·가격 미포함” | 전체 오프라인 1,304개+하위 검사 347개, 후보·기존 기기 브라우저 각 4개 조합과 CI 6개 통과. 최종 커밋 독립 리뷰·실제 입력 연결은 남음. |
| [#101](https://github.com/kco994553-star/Investment-System1/pull/101) | GSQ-012·013 및 M3 기기 ★/비공개 Universe 상위 N 구현 명세 | 이번 문서 PR. .md 전용·최종 필수 체크 성공 시 사용자 승인으로 자체 병합. 상태는 연결된 PR을 참조. |

그 밖의 열린 PR은 기능 보존 16개·닫기 권고 25개로 분류했다. 권고는 실행 승인이 아니며 실제 병합·닫기를 하지 않았다. 아래 정리안에 전체 번호·제목·권고·한 줄 이유를 모았다.

M2의 실제 후보·financial blob 입력은 현재 체크아웃에 없다. #98 기본 출력은 NOT_AVAILABLE이며, 합성 입력은 검증용이다. 가격·원시 근거·새 순위·가중치는 공개 후보 출력에 넣지 않는다.

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

## 결정 대기

1. M3의 **기본 N=20 제안**, Google/SEC 시총의 **상대오차10% 제안** 확인. 제안은 확정/자동 적용이 아니다. 상세 근거·불일치/결측·검증 범위는 [M3 구현 명세](implementation/docs/daily_data_pipeline/M3_SUBSET_IMPLEMENTATION_SPEC.md#2a-비공개-universe-1회-읽기품질-비교상위-n)에 있다.
2. #98 실제 M2 입력 연결 범위와 미완료 리뷰를 코덱1 작업에서 확인한다. #96 → #97은 이미 병합됐다. 이 M3 문서 PR은 다른 code/mixed PR을 병합하지 않는다.
3. 이전 정리안의 닫기 권고25개 PR 정리 여부. #98과 미반영 기능 PR은 보존한다.

M3 최신 범위는 **TARGET19 + 기기 ★ + 사용자 비공개 Universe 시트의 검증된 상위 N**이다. 앱은 기존 readonly 로그인으로 시트를1회 읽으며 시트 ID/실제 목록·가격·시총·순위는 저장소에 기록하지 않는다. 후보504개/503개 값/PSKY 빈칸·BLK/BNY 시총 오류는 사용자 보고이며 이번 작업에서 실제 시트를 읽지 않았다. SEC shares×같은 Sheet price로 전 후보를 검사하고 검증 불일치/미완료 범위를 표시한다.

기존 Holdout은 **UNCONFIRMED 유지·v2 근거 제외**다. 향후 v2는 forward 데이터로 검증하며 시작 시점은 v2 착수 시 사용자가 결정한다. 에이전트는 기간을 선택·사용하지 않고 현재 v2는 보류한다. [26E 최신 결정](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)의 GSQ-012·013을 따른다.

## 다음 할 일 5개

1. 코덱1은 [M3 명세](implementation/docs/daily_data_pipeline/M3_SUBSET_IMPLEMENTATION_SPEC.md)의 pure 계약/합성 tests부터 구현한다. N/품질 임계는 사용자 확인 전 확정값으로 적용하지 않는다.
2. 코덱1은 #95 이후 Worker 실패 원인을 마스킹된 진단 범위에서 확인한다. 다음 실제 배포 실행은 해당 사용자 승인 범위에서만 진행한다.
3. 이미 반영된 #96 → #97의 공개 가격 경계/HEAD 자료 정리와 실제 Pages 반영 상태를 코덱1에서 확인한다. 현재 M3 문서 작업에서 다른 PR 병합·닫기·데이터 정리는 실행하지 않는다.
4. #98 최종 코드 리뷰·실제 M2 후보 입력 연결을 확인한다. 실제 입력이 없으면 NOT_AVAILABLE을 유지한다.
5. [D 상세 명세](implementation/docs/technical_live_data/FIRST_IMPLEMENTATION_SPEC.md)의 모의 일봉/returns 어댑터/계약 검사를 코덱1 구현 범위에서 진행한다. 코덱2는 이번 M3 문서 병합 후 대기한다.

## 외부 서비스·저장 위치

설정 이름만 기록한다. 존재·권한을 확인하지 않은 비밀값이 설정됐다고 간주하지 않는다. GitHub Pages는 위 배포 상태를 참조한다.

| 서비스 | 상태 | 필요한 계정·설정/비밀값 이름 | 저장 위치 |
| --- | --- | --- | --- |
| Cloudflare Workers·SQLite DO | 재실행 failure, 성공 배포 미확인 | Cloudflare 계정 / CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, ALLOWED_EMAIL, GOOGLE_CLIENT_ID | 배포 키: GitHub Secrets; 인증 설정: Worker; DO: 요청 제한 상태만 |
| Google Identity·Sheets | 선택 기능 OFF, 기존 Quotes와 Universe M3 연결은 구분; 실제 M3 미구현 | Google 계정·OAuth Web client / googleSheetsClientId, GOOGLE_CLIENT_ID | 공개 client ID: 앱 설정; token: 메모리; Sheet: Drive. 기존 Quotes 기기 저장과 M3 Universe RAM-only는 구분; Universe ID 기기 설정/백업 제외 |
| FRED·ALFRED API | 서면 허가 전 차단; 키/실연결 미확인 | 선택 FRED API 계정 / FRED_API_KEY | 실행 환경변수 또는 /tmp/is1_fred_key; 연구 결과: 로컬 |
| Alpha Vantage | disabled, 시세 fetch 없음 | 향후 선택 계정 / api_key | 입력한 키: 브라우저 IndexedDB api-settings |
| Tiingo | 기존 fallback, 수집 차단 #96 반영 | 선택 Tiingo 계정 / TIINGO_API_KEY | GitHub Secrets·실행 환경; 기존 raw store·Actions 사본 |
| KRX Open API | 기존 도구, 수집 차단 #96 반영 | KRX API 계정·권한 / KRX_AUTH_KEY | 실행 환경변수; 로컬 raw store |
| FRED 공개 CSV | FRED 차단 유지; 키 없는 경로도 활성화하지 않음 | 계정·비밀값 없음 | 메모리·로컬 연구 결과 |
| SEC EDGAR | 금융 어댑터, 공개 수집 경계 #96 반영 | 계정 없음 / SEC_USER_AGENT, INVESTMENT_SYSTEM_SEC_UA | 식별 header: GitHub Secrets·실행 환경; 로컬 raw store·기존 Actions 사본 |
| Yahoo Finance | 개인 Worker upstream, Worker 미배포 | Yahoo 키 없음; 개인 gateway는 Google 로그인 | Worker 응답·메모리(no-store); 기존 도구 raw store |
| Stooq | 기존 fallback, 수집 차단 #96 반영 | 계정·비밀값 없음 | 로컬 raw store·연구 결과 |
| iShares 공개 참고 자료 | 기존 수집 도구, 차단 PR #96 | 계정·비밀값 없음 | 로컬 raw store·연구 결과 |

개인 포트폴리오·시세 입력·설정·가져오기 기록은 해당 앱 origin의 브라우저 IndexedDB에 저장된다. localStorage에는 기존 기기 ★ 관심 기업/Groups·언어·앱 설정과 선택한 Worker origin이 있다. M3는 ★를 읽고 파생 manifest/가격/품질 비교/순위는 RAM-only로 처리한다. Google access token은 메모리에만 있고, SQLite Durable Object는 제한 상태만 저장하며 가격 일봉을 저장하지 않는다.

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
