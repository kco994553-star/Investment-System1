# Investment-System1 — GPT Work Main 인수 실행 지시 v1.0

작성일: 2026-10-05 KST
용도: 새 GPT Work 채팅에 이 파일을 첨부하여 Claude Code Main의 후임 통합 Work를 시작한다.
이 파일 작성 자체로 역할·예약·GitHub가 변경된 것은 아니다. 사용자가 후임 Work에 이 파일을 적용하라고 전달하면 아래 인수 지시를 실행한다.

## 0. 사용자 실행 지시

이 Work를 Investment-System1의 후임 Primary Integration Coordinator / Primary Integration Writer로 지정한다.
기존 Claude Code Main의 통합·FPIA·cross-owner routing 책임을 인수한다.
새 프로젝트를 시작하거나 기존 owner의 업무를 중복 구현하지 않는다.

Repository: https://github.com/kco994553-star/Investment-System1
이전 Main: Claude Code session session_019znshzTYgyBnuuBmSxdPFN
Global branch: integration/global-handoff-v1
Canonical branch: claude/investment-system-top500-validation-alrugm

이전 Claude는 session limit에 도달했다. 그러나 이것만으로 background agent·예약·원격 CI가 종료됐다고 가정하지 않는다.
읽기·자료 복구·독립 검증은 즉시 시작한다. 공유 branch 쓰기는 아래 단일 작성자 인수 절차를 거친다.
역할 이전은 기존 승인 범위를 확대하지 않는다.

## 1. 우선순위와 목표

제품 구현을 진전시키는 것이 목적이다. 문서 수·검사 수·agent 수 자체를 성과로 삼지 않는다.
우선순위:
1. 이전 Main의 게시된 상태를 정확히 인수하고 동시 쓰기를 방지한다.
2. FPIA fix round 3의 실제 HEAD·CI·독립 검증 결과를 회수한다.
3. CDR-015 decision round의 미완료 결정을 최신 CDR-016/017 범위 안에서 처리한다.
4. Chart / QGV / Product Platform의 owner dependencies를 전달·회수하여 실제 blocker를 줄인다.
5. 독립적으로 가능한 구현·검증·통합 준비는 FPIA 대기 중에도 계속한다.

Dynamic Workflow: PLAN → DECOMPOSE → FAN-OUT → VERIFY → SINGLE ANSWER.
필요한 최소 규모로 적용한다. 독립 검증과 독립 routing은 병렬 agent로 수행할 수 있다. 같은 파일·branch에 복수 writer를 두지 않는다.

## 2. 이번 파일 작성 시 GitHub 직접 확인한 스냅샷

아래는 인수 탐색을 위한 참고점이며 시작 시 반드시 다시 확인한다.
PR 본문·Handoff 설명이 실제 head보다 오래됐을 수 있다.

| 대상 | 직접 확인한 상태 |
|---|---|
| Canonical | b8e39a2196a6d7794a04a0cd5393c68329e126ca |
| Global branch | b3532a2ebbe95310bbf222937466eb04a0211263 |
| CDR-017 | USER_DECIDED, 2026-10-05 13:05 KST, Global 위 commit에 기록 |
| Global Handoff | GCH-015; 일부 세부 상태는 이전 FPIA HEAD를 가리킴 |
| PR #42 / FPIA | 11d2f25ef8bef3459ca969f50eec190099f15ecb, Draft/Open |
| PR #42 base | integration/cdr012-successor-trial-2026-10-04 @ acaf1b5a82859ac2750a130ebe88f8b4d272ac66 |
| PR #42 CI | 6개 workflow success, track-c-fpia run 37260997788 in_progress |
| PR #42 본문 | 여전히 523e702를 Head로 설명. 실제 HEAD와 불일치 |
| PR #41 / Chart | ebeb8b1f2693703d33cff2610c277c7ce3dcbb18, codex/chart-contract-mcp-api-v0-1 |
| PR #44 | cb1906b207623168fd70f3dcdb5b30f2d82d807d, INACTIVE / SPEC-ONLY |
| QGV Missing-Data owner | codex/qgv-missing-data-decision-gate-2026-10-05 @ 4fb08a05728d83519b72a2bd995669f0cb06003a |
| QGV reconciliation | codex/qgv-architecture-reconciliation-review-2026-10-05 @ df5c70447dfa83805395b7cbbcacbc2024e77f3d |
| Product Platform | codex/product-platform-audit-v1 @ c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9 가 현재 존재 |
| PIW_DECISION_RECORDS.md | 작성 규칙만 존재; 실제 decision entry는 아직 없음 |

중요한 새 차이:
Claude의 마지막 보고에는 Product Platform branch가 없다고 되어 있으나, 이번 조회에서는 위 branch가 존재한다.
따라서 Platform을 미게시 상태로 계속 취급하지 않는다. branch의 scoped handoff·owner·lease·코드·evidence를 찾아 실제 성숙도를 판정한다.
이 branch의 최근 commit은 read-only gate의 interface drift fail-closed 수정이며, 이것만으로 Platform 전체가 완성됐다고 판단하지 않는다.

## 3. Fresh-read 순서

전체 저장소를 무차별 재감사하지 말고 아래 순서로 인수한다.

1. canonical/default branch, remote heads, PR 상태 및 실제 head/base
2. implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md
3. implementation/docs/coordination/GLOBAL_STATUS_INDEX.md
4. implementation/docs/coordination/GLOBAL_HANDOFF_HISTORY.md
5. implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md — 특히 CDR-014~017
6. implementation/docs/coordination/PIW_DECISION_RECORDS.md
7. Worker Contract: CDR-001의 operational pin을 확인하고 최신 사용자 지시와 대조
8. GIE-009/011/012 및 FPIA 후속 evidence; GIE-014 존재·완료 여부를 직접 확인
9. PR #42 소스·tests·workflow·reviews/comments·artifacts
10. Chart #41, QGV 두 successor branch, Product Platform branch의 scoped handoff/Decision/Evidence/Conflict/automation STATE
11. Portfolio, Identity, Product/P01, Web, Session 관련 owner handoff
12. 실제 active lease, write-set, 자동화 상태

존재하지 않는 파일 경로·decision 번호를 만들었다고 가정하지 않는다. 경로는 index와 repository 검색으로 해석한다.
Global은 routing SSoT이고 계산·정책 승인 자체의 authority는 아니다. 원문 decision, scoped evidence, exact SHA를 우선한다.

## 4. 권한 해석 — 반드시 최신 좁은 조건까지 반영

CDR-015:
D1 자율, D2 정책·configuration·계약·migration·canonical merge·publication·배포 위임, 비용만 D3라는 광범위 위임이다.

하지만 이후 CDR-016 §13은 Main의 canonical merge, Frozen semantics 변경, Holdout 소비, PIT 완화, Official/LIVE 승격, 유료 결제, 다른 owner protected contract 임의 변경에 명시적 승인을 요구한다.
기록된 해석도 해당 Work에 더 좁은 조건을 적용한다.

CDR-017:
- Main은 QGV production semantics를 임의 결정하지 않는다.
- 실제 credential·금융계정·production auth·유료 connector는 사용자 승인 없는 자동 진행 대상이 아니다.
- scoped owner의 lease·write-set·전문 소유권을 유지한다.

따라서 CDR-015만 읽어 “비용 외 전부 허용”으로 처리하지 않는다.
후속 승인이 있다면 exact decision을 확인하여 적용한다. 이 인수 파일 자체는 위 제한을 해제하지 않는다.
이 충돌 때문에 전체 업무를 멈추지 않는다. FPIA repair·검증·routing·evidence 등 명확히 허용된 일을 진행하고, 실제로 제한 행동이 필요한 시점에만 한정된 결정을 요청한다.
D3-a~e라는 옛 label만으로 재승인을 요청하지 말고, 항목별 authority·owner·허용 행동을 재분류한다.

## 5. 단일 작성자 이전과 충돌 방지

1. 이전 Claude Main의 remote update·lease·열린 Actions와 확인 가능한 background 상태를 점검한다.
2. 확인 가능한 이전 Main 전용 예약만 식별한다. QGV/Chart/Platform의 독립 owner 자동화를 중지하지 않는다.
3. Claude 내부 scheduler에 접근할 수 없으면 중지했다고 주장하지 않는다. 확인 불가능한 동시 writer가 실제 공유 쓰기를 막는 경우에만 사용자가 Claude Main을 중지하도록 요청한다.
4. 불확실한 동안에는 private clone / 별도 takeover proposal branch에서 읽기·검증·인수 준비를 계속한다. 보호 branch·lease를 강제로 덮어쓰지 않는다.
5. 인수 가능하면 기존 단일 작성자 절차에 따라 새 writer identity, 실제 KST 시각, 인수한 Global exact HEAD, write-set, 이전 writer 종료/제한 상태를 append한다.
6. Global 갱신 직전 fresh-read/CAS 또는 원격 parent 확인을 수행한다. 원격 이동 시 재조정한다. force push·history rewrite 금지.
7. Claude가 사용량 회복 후 자동으로 통합 쓰기를 재개하지 않도록 owner-transfer 상태와 이전 실행 식별자를 기록한다. 문서만으로 외부 실행이 실제 중단됐다고 주장하지 않는다.

실제 역할 이전 확인 전에는 TAKEOVER_PREPARING, 단일 작성자 확보 후에는 TAKEOVER_ACTIVE로 구분한다.
이 단계는 새로운 투자 정책 승인 요청이 아니라 동시 쓰기 제어다.

## 6. 인수할 네 개 작업 흐름

### A. FPIA fix round 3

Claude 보고: workflow wf_bdfed701-366. fix3 구현 후 real/battery, regression/CI, fresh adversarial pass, completeness 수행 예정.
PR #42 현재 실제 HEAD와 구현 diff를 읽어 진행 상태를 복구한다.

이전 523e702에서 확인된 문제:
- S24V2: 보이지 않는 Unicode와 rooted cd 조합으로 위조 tree가 FPIA_PASS
- shell 변형 다수의 탐지 누락
- symlinked venv/TMPDIR 등에 따른 환경 의존 판정
- 사용자명·검증기·vendored loader provenance 등 H3~H7
- T 바깥 외부 workflow/action/container 코드의 검사 경계 D3-e

새 감지는 보수적 identity key·Track C mention 과대근사 방향이다.
개별 반례 차단뿐 아니라 정상 workflow 대조, 과도한 차단, 실행 source와 감사 source 일치, 외부 코드 검사 범위를 검증한다.
FPIA_PASS와 CODE_IDENTITY_DIVERGED, Frozen historical identity, integration projection, runtime provenance를 분리한다.
CI PASS만으로 governance/GIE/completeness closure를 선언하지 않는다.

run 37260997788을 우선 조회한다. 이미 끝난 동일 head/attempt의 CI를 중복 재실행하지 않는다.
CI 결과가 old head이거나 변경 영향이 있으면 필요한 검사부터 재실행한다.
최종 head에서 실제 subject tree·verifier identity·test collection·결정성·negative probes·full/affected regression과 독립 검증을 연결한다.

### B. CDR-015 decision round

Claude가 자체 판단 중이던 FPIA D3-a~e와 G7을 회수한다.
- a: 신뢰할 verifier version/identity 인증
- b: workflow job-id collision 판정
- c: 동적으로 구성한 invocation 탐지·검증 한계
- d: #28 importer attribution
- e: 외부 repository reusable workflow, third-party action, container image 등 T 외부 실행 코드
- G7: Track C reference를 포함한 integration subject와 pre-Track-C tree에 대한 적용 범위/CI trigger

자체 decision 결과가 remote register에 없으면 완료로 가정하지 않는다.
현재 PIW_DECISION_RECORDS에는 entry가 없었다. 이후 생성 여부를 확인하고 없는 판단만 수행한다.
Main이 허용된 결정을 내릴 때 이유·대안·영향·검증·복구를 append한다.
검증하지 못한 외부 코드를 무조건 안전하다고 취급하지 않는다.

### C. Chart routing

최신 #41에서 Lane A 6 gate를 다시 판정한다.
1. authoritative current TARGET root — Portfolio
2. 19 security binding — Identity
3. Theme catalog/assignment revision — Portfolio/Classification
4. Product authority applicability — Product/P01
5. exact owner write-set/base acceptance — Chart/Web/Product/Integration
6. FPIA governance/admissibility 및 향후 exact merge-result audit — Integration

owner는 위 추정만 믿지 말고 실제 handoff로 확정한다.
A-G1/A-G2 routing request와 이후 답변을 찾는다.
TARGET/ACTUAL, GICS/Strategy Theme/Investment Type/Overlap을 분리한다.
Main이 Chart 기능을 중복 구현하지 않는다. authoritative owner가 없는 항목은 OWNER_UNASSIGNED로 드러내고 담당자·write-set을 확정할 절차를 마련한다.
Lane B의 8 evidence gap은 별도 유지하며 Target Theme에 불필요한 Market/GICS/ACTUAL dependency를 추가하지 않는다.

### D. QGV / Product Platform routing

QGV:
PR #44는 이전 spec-only 배포물이다. 최신 missing-data / reconciliation branch까지 읽는다.
Missing-data, requiredness, applicability, method/version identity, G horizon/lineage, EPS→FCF, V normalization, Composite, WeightOverride 중 실제 다른 owner 의존성만 Main이 연결한다.
연구·production semantic 선택은 QGV owner 및 최신 승인 절차에 맡긴다.

Platform:
이제 codex/product-platform-audit-v1 branch가 발견됐으므로 즉시 인수 입력으로 사용한다.
Auth, tenant isolation, financial sync/import, reconciliation, auditable records, read-only gate, API, Web/PWA, engine integration을 실제 코드·테스트·evidence로 분류한다.
branch 이름만으로 구현 owner와 감사 owner를 같다고 가정하지 않는다.
실제 계정 연결·production auth는 CDR-017 제한을 적용한다. trade/order/fund transfer는 구현·활성화하지 않는다.
Main은 플랫폼 전체를 새로 만들지 않고 shared contract·owner action·integration dependency를 해결한다.

## 7. 미게시 결과와 증거 복구

Claude의 “4 workflows running”은 마지막 보고이지 GPT에서도 계속 실행 중이라는 증거가 아니다.
각 흐름을 REMOTE_VERIFIED / LOCAL_REPORTED / RUNNING_CONFIRMED / UNKNOWN / NOT_RUN으로 구분한다.

- 원격 commit·Actions artifact·게시된 검증 로그가 있으면 exact SHA와 함께 재사용한다.
- 접근할 수 없는 Claude scratchpad·agent journal·partial outputs는 UNAVAILABLE로 기록한다.
- 요약 문장만으로 raw evidence가 존재한다고 가정하지 않는다.
- unavailable 검사만 필요한 범위에서 재현한다. 전체 프로젝트를 처음부터 재검증하지 않는다.
- 과거 wf16/v2-regress-ci/r2 사본 삭제와 최초 원본 잔존 보고는 사실관계를 보존한다. 동일성은 남아 있는 실제 hash/log가 있을 때만 확인했다고 기록한다.
- 인수 과정에서 미검토 scratch/evidence를 삭제하지 않는다.

## 8. Owner routing ledger와 수신 확인

기존 ledger가 있으면 재사용한다. 없으면 Global write-set 안에 작은 ledger를 추가한다.
각 항목:
id / finding / authoritative owner / required artifact / exact path·branch·PR /
acceptance criteria / dependencies / source HEAD·decision / delivery channel /
delivered_at / receipt / last_consumed_revision / state / next action

단계:
FOUND → ROUTED → RECEIVED → IN_PROGRESS → EVIDENCE_READY → CONSUMED → CLOSED

본 인수 작업 범위에서 관련 저장소의 owner PR에 필요한 routing comment/packet을 게시할 수 있다.
단, 실제 owner가 소비하는 채널인지 확인하고 동일 packet은 중복 게시하지 않는다.
댓글 게시만으로 owner 수신·작업 시작·blocker 해소를 주장하지 않는다.
자동화가 bot/API 작성 댓글을 trigger로 인정하는지도 확인한다. GitHub 이벤트 종류가 맞지 않으면 전달 성공과 자동 wake-up 성공을 구분한다.
Global-only material delta도 owner가 읽는 경로로 전달하고, 의미 없는 Global commit을 전체 broadcast하지 않는다.

## 9. 자동 재개 인수

1. 접근 가능한 기존 자동화를 조회하고 이름·ID·conversation·trigger·최근 실행·활성 상태를 확인한다.
2. 새 Main 전용 자동화만 생성/갱신한다. 기존 audit Work의 자동화·owner lease는 보존한다.
3. PR 이벤트는 지원되는 event만 사용한다. CI completion, Global branch-only push, bot comment가 자동 trigger인지 추정하지 않는다.
4. 이벤트가 포착하지 못하는 dependency와 장시간 CI에는 지원되는 최소 후속 확인을 둔다. 허용 cadence를 준수한다.
5. last_processed_HEAD / material delta / 실행 상태로 중복 및 자기-trigger loop를 방지한다.
6. 실제 event 수신 → 새 Main 실행 → handoff 재소비 → 허용 작업 수행을 관찰해야 END_TO_END_VERIFIED로 기록한다. 활성 readback만 확인되면 CONFIGURED_ONLY다.
7. 자동화가 실제 실행되지 않으면 수동 시작된 현재 작업에서 가능한 backlog를 끝내고 정확한 제한을 보고한다.
8. 완성된 작업에는 중복 구현을 하지 않고 실제 남은 작업이 있는지 판단한다.

## 10. GitHub 쓰기 경로

이전 환경의 push 실패를 이 환경 전체의 write 불가로 일반화하지 않는다.
현재 연결의 실제 read/write capability를 확인한다. Git transport가 막히면 승인된 GitHub API 경로를 검토한다.
이미 존재하는 local commit의 exact SHA 보존 여부는 remote에서 검증한다.
metadata 지원 부재로 replacement commit을 만든 경우 TREE_IDENTICAL과 COMMIT_IDENTICAL을 구분하고 기존 provenance를 보존한다.
#44는 TREE_IDENTICAL republishing 사례이며 원본 4b39197 게시 성공 사례가 아니다.
인증정보를 출력하거나 provenance를 날조하지 않는다.

## 11. 실행·완료 기준

초기 read-only inventory 후 동시 writer 문제가 없으면 사용자에게 “계속할까요?”를 묻지 말고 인수 기록과 다음 작업을 진행한다.
실제 쓰기 충돌·제한 승인·외부 입력/비용 문제만 해당 작업을 대기로 둔다. 독립 작업은 계속한다.
장시간 Actions 대기 때문에 shared write lease를 붙잡지 않는다.
마지막 테스트가 통과했으면 새 변경·실패 근거 없이 검증을 무한 확대하지 않는다.

첫 보고:
- TAKEOVER_PREPARING / ACTIVE와 단일 작성자 근거
- canonical / Global / FPIA exact HEAD
- 기존 네 흐름의 회수 결과와 재실행 필요 범위
- Chart / QGV / Platform routing 및 실제 receipt
- CDR-015/016/017 authority 충돌 적용표
- 자동화 CONFIGURED_ONLY / END_TO_END_VERIFIED / BLOCKED
- 지금 해결한 dependency와 다음 critical path

최종적으로 “다른 owner가 해야 한다”만 반복하지 않는다.
실제 delivery·receipt·artifact 검증·scoped re-consumption까지 추적하여 blocker 감소를 증명한다.

## 12. 인수용 원문 출처

아래 source들은 파일 작성 시 읽었으며 최신 인수 시 재조회한다.

- Global / CDR: https://github.com/kco994553-star/Investment-System1/tree/b3532a2ebbe95310bbf222937466eb04a0211263/implementation/docs/coordination
- FPIA: https://github.com/kco994553-star/Investment-System1/pull/42
- FPIA CI: https://github.com/kco994553-star/Investment-System1/actions/runs/37260997788
- Chart: https://github.com/kco994553-star/Investment-System1/pull/41
- QGV spec-only: https://github.com/kco994553-star/Investment-System1/pull/44
- Platform: https://github.com/kco994553-star/Investment-System1/tree/c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9
- QGV owner: https://github.com/kco994553-star/Investment-System1/tree/4fb08a05728d83519b72a2bd995669f0cb06003a
- QGV reconciliation: https://github.com/kco994553-star/Investment-System1/tree/df5c70447dfa83805395b7cbbcacbc2024e77f3d

## 부록: 조회한 CDR-015~017 원문 스냅샷

다음은 GitHub Decision Register에서 회수한 원문이다. 새 지시를 추가한 것으로 해석하지 않는다.
최신 원격 내용 또는 이후 사용자 결정이 있으면 그것을 우선한다.

## CDR-015 · Decision Authority delegation (D1/D2 self-decision; D3 = cost only); supersedes re-approval requirements

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-05 12:15 KST (2026-10-05T03:15Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-014b / `b5b4ca6`) |
| Supersedes | the user re-approval requirements in CDR-001 … CDR-014, within the scope below. Every earlier entry and approval record is preserved unchanged |
| Applies to | every Investment-System1 Work (owners, Codex, Claude Code workers, the Primary Integration Writer), including automatic resumption |

User wording (verbatim):

> Investment-System1의 Decision Authority를 다음과 같이 변경·승인한다.
>
> 이 지시는 기존의 사용자 재승인 요구를 아래 범위에서 대체한다. 실제 KST 시각과 사용자 원문을 Decision Register에 append하고 Global/scoped Handoff에 반영하라. 과거 승인 기록은 보존한다.
>
> D1:
> 일반 구현·문서·테스트·CI·자동화는 자율 실행한다.
>
> D2:
> 프로젝트 목표에 필요한 정책 선택, 수치 configuration, 계약 변경, versioned successor, migration, canonical merge, publication, 배포는 근거와 검증을 갖춰 자체 결정·실행한다. D3로 분류됐다는 이유만으로 사용자 승인을 다시 요청하지 않는다.
>
> D3:
> 유료 결제·유료 구독·추가 과금·무료 quota 초과만 사용자 승인을 요청한다. 비용 발생 여부를 확인할 수 없으면 해당 자원 사용만 보류한다.
>
> 실제 증권 주문·자금 이동과 프로젝트 밖의 행동은 위임 범위에 포함되지 않는다.
>
> 권한 확대는 검증 면제가 아니다. PIT, provenance, evidence 무결성과 결과의 정직한 표시는 유지한다. 실패를 숨기거나 테스트를 skip하여 PASS를 만들지 않는다. 기존 Frozen/history는 rewrite하지 않고 후속 버전으로 변경한다.
>
> 현재 미결정 사항은 새 권한 기준으로 재분류한다. FPIA D3-a~e도 요구사항·대안·영향을 검토하여 자체 해결한다. 탐지·검증하지 못한 범위를 숨기고 전체 PASS로 확대하지 않는다.
>
> 각 자체 결정에는 이유·영향·검증·복구 방법을 기록한다. 전체 프로젝트 완성을 기다리지 말고 검증된 작은 기능 묶음부터 단계적으로 통합한다.
>
> 각 Work의 자동 재개에도 이 권한 기준을 적용한다. 실행 가능한 backlog가 있으면 계속 진행하고, 실제 외부 입력 부재나 해결 불가능한 blocker가 있을 때만 대기한다. 다른 owner의 변경은 기존 routing과 단일 작성자 규칙을 따른다.
>
> 현재 작업을 중단하거나 처음부터 다시 시작하지 말고, 이 결정을 기록한 뒤 이어서 진행하라.

Recorded effect (routing writer's reading; the user wording above governs):

- **D1** (autonomous): implementation, documentation, tests, CI and automation.
- **D2** (decide and execute with evidence and verification, without asking the user again): policy choices needed for the project goal, numeric configuration, contract changes, versioned successors, migrations, canonical merges, publication and deployment. An item previously listed as "not approved" or as a D3 in CDR-003 … CDR-014 (for example canonical merge, numeric configuration, C8 Freeze, CAL_VERIFY, Holdout access, publication grants, Official/LIVE promotion, the #17 digest repin, FPIA D3-a … D3-e, the G7 interpretation) is now D2: it needs a recorded decision with reason, impact, verification and recovery, and the evidence that supports it, not a new user approval.
- **D3** (ask the user): only paid payment, paid subscription, extra charges, or exceeding a free quota. If whether a cost arises cannot be established, only the use of that resource is held.
- **Outside the delegation:** real securities orders, movements of funds, and actions outside the project.
- **Unchanged obligations:** PIT/no-lookahead, provenance, evidence integrity and honest reporting of results; no hidden failure and no skipped test to reach PASS; Frozen records and history are changed only by successor versions, never rewritten; undetected or unverified scope is disclosed and never folded into an overall PASS.
- **Self-decision records:** decisions taken under this delegation are recorded with reason, impact, verification and recovery. The Primary Integration Writer records its own in `PIW_DECISION_RECORDS.md` (this directory); capability owners record theirs in their scoped Decision Registers.
- **Integration cadence:** verified small bundles are integrated step by step, without waiting for the whole project.
- **Ownership:** changes to another owner's branch or scoped records still follow the existing routing and single-writer rules. Scoped owners adopt this entry at their next fresh read; the Primary Integration Writer does not write their scoped registers or handoffs.

## CDR-016 · Chart PR #41 production blockers: owner routing directive; protected boundaries for this Work

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (operating directive for the Integration / Claude Main Work) |
| Decided at | 2026-10-05 12:43 KST (2026-10-05T03:43Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-015 / `d92363f`) |
| Relates to | CDR-015 (decision authority), CDR-014 (FPIA), PR #41 (Chart) |

User wording (verbatim):

> Investment-System1 Integration / Claude Main Work를 최신 GitHub 실제 상태에서 계속 진행한다.
>
> 이번 작업의 추가 목표는 Chart PR #41이 확인한 production blocker 6개를
> 각 authoritative owner에게 정확히 routing하고,
> 이미 해결 가능한 것은 Integration에서 검증하여 Chart Work가 다시 진행될 수 있게 만드는 것이다.
>
> 새 Chart 기능을 Integration Work에서 직접 구현하는 것이 목적이 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 0. FRESH GITHUB / HANDOFF FIRST
> ━━━━━━━━━━━━━━━━━━━━
>
> 시작 시 반드시 GitHub를 fresh fetch/read한다.
>
> 다음 순서로 실제 상태를 복원한다.
>
> 1. canonical/default + exact HEAD
> 2. integration/global-handoff-v1
> 3. GLOBAL_CURRENT_HANDOFF
> 4. GLOBAL_STATUS_INDEX
> 5. COORDINATION_DECISION_REGISTER
> 6. Integration/FPIA scoped handoff
> 7. Chart PR #41 + Chart scoped handoff
> 8. Portfolio owner handoff
> 9. Identity owner handoff
> 10. Product/P01 handoff
> 11. Web owner handoff
> 12. QGV owner handoff
> 13. Decision / Approval / Evidence / Conflict registers
> 14. 관련 PR / branch / Actions / reviews
> 15. ownership / write-set / dependency
>
> 과거 SHA보다 실제 GitHub가 우선한다.
>
> 다른 owner의 구현을 중복하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 1. CHART CURRENT CHECKPOINT
> ━━━━━━━━━━━━━━━━━━━━
>
> 마지막 Chart 보고 기준:
>
> PR #41
> last observed HEAD:
> 74df6784071137bdca911964af94c8e1b6928c92
>
> 단 반드시 fresh-read한다.
>
> Chart Lane A:
> IMPLEMENTATION_NOT_READY
>
> production blockers:
> 정확히 6개
>
> 1. authoritative TARGET root
> 2. Security mapping
> 3. Theme revision/version
> 4. Product authority
> 5. owner write-set acceptance
> 6. FPIA governance/admissibility
>
> 마지막 분류:
>
> 1~5 = OWNER_ACTION_REQUIRED
> 6 = USER_D3_REQUIRED / existing Integration D3/G7 dependency
>
> Chart Work 자체에서 가능한 독립 검증은 현재 소진된 것으로 보고됐다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 2. OBJECTIVE
> ━━━━━━━━━━━━━━━━━━━━
>
> 6개 blocker를 단순히 Global Handoff에 다시 나열하지 않는다.
>
> 각 blocker에 대해:
>
> - authoritative owner를 확정
> - owner가 제공해야 할 exact artifact/evidence 결정
> - 이미 repository에 존재하는지 fresh 확인
> - 존재하면 Chart-compatible 여부 검증
> - 없으면 owner action으로 routing
> - 완료 조건 정의
> - dependency ordering 정의
>
> 를 수행한다.
>
> 목표는 Chart Work가 다음 실행에서
> 6개 blocker를 실제로 줄일 수 있도록 만드는 것이다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 3. BLOCKER 1 — AUTHORITATIVE TARGET ROOT
> ━━━━━━━━━━━━━━━━━━━━
>
> Portfolio owner를 확인한다.
>
> Chart가 요구하는 최소 receipt:
>
> - portfolio_id
> - portfolio_version
> - effective_at
> - current TARGET constituent set
> - security reference
> - target_weight
> - denominator
> - completeness
> - provenance/source
> - authoritative-root declaration
>
> 현재 repository에 이미 equivalent authoritative object가 있으면
> 새 object를 만들지 말고 재사용 가능성을 검증한다.
>
> 없다면 Portfolio owner action으로 routing한다.
>
> 현재 Strategy Theme target:
>
> 반도체 장비 30
> AI·반도체 25
> Big Tech 20
> 기타산업 25
>
> 는 Chart에서 Decimal 합계 100.000%까지 검증됐지만,
> 이 사실만으로 authoritative root가 되는 것은 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 4. BLOCKER 2 — SECURITY MAPPING
> ━━━━━━━━━━━━━━━━━━━━
>
> Identity owner를 확인한다.
>
> 기존 공통:
>
> Issuer → Security → dated Listing
>
> contract를 재사용한다.
>
> Chart Target constituents 전체에 대해 최소:
>
> portfolio constituent
> → internal security_id
> → correct share/security form
> → dated listing
>
> binding을 제공해야 한다.
>
> ticker-only identity는 허용하지 않는다.
>
> 19개 전체에 대한 mapping receipt 또는
> Chart가 deterministic하게 조회할 authoritative path를 제공한다.
>
> 새 Chart 전용 identity layer를 만들지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 5. BLOCKER 3 — STRATEGY THEME REVISION
> ━━━━━━━━━━━━━━━━━━━━
>
> Portfolio/Classification owner를 확정한다.
>
> Strategy Theme는 GICS가 아니다.
>
> User-defined Strategy Theme / Portfolio Bucket이다.
>
> 필요한 최소 contract:
>
> - theme taxonomy/catalog id
> - version
> - effective_at
> - assignment
> - completeness
> - provenance
> - TARGET root binding
>
> 현재 네 bucket의 경제적 의미를 새로 바꾸지 않는다.
>
> 단순 version/provenance 구조라면 기존 승인 범위에서
> D1/D2로 해결 가능한지 먼저 판단한다.
>
> 새 정책 결정이 아니라 기존 Target classification의 identity/version 문제라면
> 불필요하게 D3로 올리지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 6. BLOCKER 4 — PRODUCT AUTHORITY
> ━━━━━━━━━━━━━━━━━━━━
>
> P01/Product owner에게 다음 질문을 명시적으로 routing한다.
>
> "현재 P01 research-display/publication authority contract가
> user-authored TARGET Portfolio visualization에 적용 가능한가?"
>
> 가능한 답은 최소:
>
> A. 기존 P01 authority 재사용 가능
> B. 별도 Target/Product authority 필요
> C. 현재 contract로는 판단 불가
>
> 중 하나여야 한다.
>
> A라면 exact authority/read route와 predicate를 evidence로 남긴다.
>
> B/C라면 필요한 최소 contract를 owner가 제시한다.
>
> Chart Work가 임의로 publication policy를 만들게 하지 않는다.
>
> Source/data rights와 Product authority를 분리한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 7. BLOCKER 5 — OWNER WRITE-SET ACCEPTANCE
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart Target Strategy Theme vertical slice의 최소 write-set을
> Chart scoped handoff에서 읽는다.
>
> 각 파일/경로에 대해 owner matrix를 만든다.
>
> 최소:
>
> - Chart owner
> - Portfolio owner
> - Product owner
> - Web/P01 owner
> - Integration owner
> - Track C/FPIA impact
>
> 를 판정한다.
>
> 목표는:
>
> "누가 어떤 파일을 수정해도 되는지"
>
> 를 명시적으로 확정하는 것이다.
>
> 가능하면 Chart owner가 자신의 branch에서 구현하고,
> 다른 owner는 contract/acceptance만 제공하는 구조를 우선한다.
>
> 다른 owner가 Chart 기능 자체를 중복 구현하게 하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 8. BLOCKER 6 — FPIA GOVERNANCE / ADMISSIBILITY
> ━━━━━━━━━━━━━━━━━━━━
>
> 이 항목은 현재 Integration critical path다.
>
> PR #42 및 successor/FPIA work를 fresh-read한다.
>
> 특히 최신 Global에 기록된:
>
> - adversarial findings
> - environment-dependent judgement
> - round-3 fix
> - existing D3
> - G7
> - GIE closure
>
> 상태를 정확히 복원한다.
>
> 다음을 구분한다.
>
> FPIA implementation
> CI PASS
> independent review
> adversarial review
> D3 closure
> G7 closure
> GIE closure
> canonical applicability
> Chart exact-result FPIA
>
> 현재 owner 수정/검증으로 해결 가능한 것은 자동 진행한다.
>
> 실제 새로운 semantic/governance D3만 사용자에게 요청한다.
>
> 과거 D3라는 이유만으로 재질문하지 말고
> 이미 사용자가 승인한 것이 있는지 Decision Register와 현재 대화를 대조한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 9. ROUTING OUTPUT
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 blocker를 다음 형태로 기록한다.
>
> BLOCKER
> OWNER
> CURRENT STATE
> REQUIRED ARTIFACT
> EXACT PATH/PR
> ACCEPTANCE CRITERIA
> DEPENDENCY
> CAN PROCEED NOW?
> NEXT OWNER ACTION
>
> 가능하면 owner가 바로 소비할 수 있는 작은 packet/receipt 형태로 만든다.
>
> 단순 prose 요청보다 machine/checkable evidence를 우선한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 10. PARALLELISM
> ━━━━━━━━━━━━━━━━━━━━
>
> 독립적인 owner action은 병렬 routing한다.
>
> 예:
>
> Portfolio:
> TARGET root + Theme revision
>
> Identity:
> Security mapping
>
> Product/P01:
> authority applicability
>
> Web/Product:
> write-set acceptance
>
> Integration:
> FPIA closure
>
> 서로 dependency가 없는 것은 순차적으로 기다리지 않는다.
>
> 하지만 같은 파일을 여러 owner가 수정하게 만들지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 11. CHART AUTOMATION GAP
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart Work가 확인한 automation gap도 Integration coordination 관점에서 처리한다.
>
> 확인된 문제:
>
> PR dependency 변화는 wake-up 대상이지만
> Global branch에만 기록된 material dependency 변화는
> Chart Work를 즉시 깨우지 못할 수 있다.
>
> 새 automation framework를 만들지 않는다.
>
> 대신 가능한 최소 해결책을 판단한다.
>
> 우선순위:
>
> 1. 기존 Chart event automation이 Global material dependency change를 소비할 수 있는지
> 2. 불가능하면 Global writer가 Chart-relevant owner receipt/decision을
>    Chart가 감시하는 기존 경로에 전달할 수 있는지
> 3. 그래도 불가능하면 최소 polling/watch 보완
>
> 모든 Global commit마다 Chart를 재실행하는 방식은 피한다.
>
> Chart blocker와 관련된 material semantic delta만 trigger 대상이어야 한다.
>
> automation 자체가 프로젝트 병목이 되지 않게 한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 12. AUTO-CONTINUE
> ━━━━━━━━━━━━━━━━━━━━
>
> D1/D2에서는 owner routing만 하고 멈추지 않는다.
>
> 현재 Work가 직접 해결 가능한:
>
> - FPIA repair
> - regression
> - review response
> - evidence
> - routing packet
> - coordination record
> - owner handoff
>
> 는 계속 수행한다.
>
> 장시간 Actions는 run_id/head_sha/attempt를 기록하고
> 다음 check로 넘긴다.
>
> 실제 D3에서만 사용자에게 돌아온다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 13. PROTECTED BOUNDARIES
> ━━━━━━━━━━━━━━━━━━━━
>
> 명시적 승인 없이:
>
> - canonical merge
> - Frozen semantics 변경
> - Holdout 소비
> - PIT/no-lookahead 완화
> - Official/LIVE 승격
> - 유료 결제
> - 다른 owner의 protected contract 임의 변경
>
> 을 하지 않는다.
>
> Global Handoff는 Primary Integration Writer 권한을 따른다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 14. COMPLETION CONDITION
> ━━━━━━━━━━━━━━━━━━━━
>
> 이번 작업은 다음 중 하나까지 계속한다.
>
> A.
> 6개 Chart blocker 중 owner evidence로 실제 blocker가 감소
>
> B.
> 각 blocker가 정확한 owner에게 routing되고
> machine/checkable acceptance artifact가 준비됨
>
> C.
> Integration/FPIA의 실제 D3가 남아 사용자 결정 필요
>
> 단순히:
>
> "Chart는 6개 blocker를 기다리고 있다"
>
> 라고 다시 보고하고 종료하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 15. FINAL REPORT
> ━━━━━━━━━━━━━━━━━━━━
>
> 다음 순서로 보고한다.
>
> 1. Fresh canonical / Global / Integration HEAD
> 2. FPIA 현재 상태
> 3. Chart #41 현재 HEAD
> 4. 6 blocker owner-routing matrix
> 5. 이번에 즉시 해결한 blocker
> 6. owner에게 전달한 action
> 7. 병렬 진행 중인 owner action
> 8. 남은 blocker count
> 9. FPIA D3/G7/GIE 상태
> 10. Chart automation gap 처리 결과
> 11. Chart Work 자동 재개 조건
> 12. 새로운 USER_D3_REQUIRED
> 13. next exact integration step
>
> 마지막에 반드시 답한다.
>
> - Chart blocker가 6개에서 몇 개로 줄었는가?
> - 줄지 않았다면 각 blocker를 실제로 누가 해결 중인가?
> - Chart Work가 다시 자동/수동 재개되어야 하는 정확한 trigger는 무엇인가?
> - 사용자 결정 없이 지금 더 진행할 수 있는 Integration 작업이 남아 있는가?
>
> 사용자 결정 없이 진행 가능한 일이 남아 있다면 자동으로 계속 진행한다.

Recorded effect (routing writer's reading; the user wording above governs):

- The Integration Work routes each of Chart PR #41's six production blockers to its authoritative owner with an exact, machine-checkable request and acceptance criteria, verifies any artifact that already exists in the repository for Chart compatibility, and does not implement Chart features or duplicate another owner's implementation.
- Fixed meanings for the routing: the Strategy Theme is a user-defined Strategy Theme / Portfolio Bucket, not GICS, and the economic meaning of the four buckets (반도체 장비 30, AI·반도체 25, Big Tech 20, 기타산업 25) is not changed; a Chart-side Decimal sum of 100.000% does not make an authoritative root; security identity reuses Issuer → Security → dated Listing and ticker-only identity is not accepted; no Chart-only identity layer; Product authority is separate from source/data rights, and the Product/P01 owner answers the applicability question with A, B or C.
- Blocker 6 (FPIA governance/admissibility) is the Integration critical path. Items previously labelled D3 are not re-asked when CDR-015 already delegates them.
- **Protected boundaries (§13) for this Work.** CDR-015 delegated canonical merges, numeric configuration, publication and deployment as D2; §13 of this later directive lists canonical merge, a Frozen semantics change, Holdout consumption, PIT/no-lookahead relaxation, Official/LIVE promotion, paid payment and arbitrary change of another owner's protected contract as actions not taken without explicit approval. Until the user reconciles the two, the Primary Integration Writer applies the narrower rule: none of those actions is taken in this Work without an explicit user approval naming it. CDR-015 otherwise stays in force (D1/D2 self-decision for everything else, D3 = cost).

## CDR-017 · Claude Main = Primary Integration Coordinator for all audit/implementation Works (standing)

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (standing operating directive) |
| Decided at | 2026-10-05 13:05 KST (2026-10-05T04:05Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after CDR-016 / `5e33b30`) |
| Relates to | CDR-001 (Worker Contract routing), CDR-015 (authority), CDR-016 (Chart routing, protected boundaries) |

User wording (verbatim):

> Investment-System1 Claude Main / Integration Work를 앞으로 전체 감사·구현 Work의
> Primary Integration Coordinator로 계속 운영한다.
>
> 이 지시는 QGV / Chart / Product Platform 작업을 Main이 중복 구현하라는 뜻이 아니다.
>
> 각 scoped Work는 자기 영역을 독립적으로 계속 진행하며,
> Claude Main의 책임은 scoped Work 사이의 cross-owner dependency를 실제로 해소하고,
> Global Handoff와 Integration/FPIA를 통해 전체 시스템이 앞으로 진행되게 만드는 것이다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 1. FRESH GITHUB FIRST
> ━━━━━━━━━━━━━━━━━━━━
>
> 매 실행/재개 시 실제 GitHub를 fresh-read한다.
>
> 최소 확인:
>
> - canonical/default + exact HEAD
> - integration/global-handoff-v1
> - GLOBAL_CURRENT_HANDOFF
> - GLOBAL_STATUS_INDEX
> - COORDINATION_DECISION_REGISTER
> - Decision / Approval / Evidence / Conflict registers
> - Integration/FPIA scoped handoff
> - QGV scoped handoff
> - Chart scoped handoff
> - Product Platform scoped handoff
> - Portfolio/Identity handoff
> - Product/P01 handoff
> - Web handoff
> - open PR / Actions / reviews
> - owner branch/HEAD
> - active lease/write-set
>
> 실제 GitHub와 명시적 사용자 approval/decision evidence를
> 과거 대화나 오래된 Handoff보다 우선한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 2. PRIMARY ROLE
> ━━━━━━━━━━━━━━━━━━━━
>
> Main은 다음을 담당한다.
>
> 1. cross-owner dependency routing
> 2. Global Handoff coordination
> 3. Integration/FPIA
> 4. owner write-set 충돌 방지
> 5. scoped Work 결과의 integration readiness 판정
> 6. D1/D2 자동 진행 조율
> 7. 실제 D3만 사용자에게 escalation
> 8. canonical integration 준비
>
> Main은 각 scoped Work의 전문 업무를 불필요하게 다시 수행하지 않는다.
>
> 예:
>
> QGV scoring 연구
> → QGV Work 소유
>
> Chart contract/rendering
> → Chart Work 소유
>
> Auth/Tenant/Connector/Reconciliation
> → Product Platform Work 소유
>
> Portfolio Target
> → Portfolio owner
>
> Security/Listing identity
> → Identity owner
>
> Product publication authority
> → Product/P01 owner
>
> Main은 이들을 연결한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 3. THREE CONTINUOUS AUDIT WORKS
> ━━━━━━━━━━━━━━━━━━━━
>
> 현재 다음 세 Work가 독립 자동진행 중인 것으로 취급한다.
>
> A. QGV 구조 재감사
> B. Chart 구현 감사
> C. Product Platform 구현 감사
>
> 각 Work의 최신 scoped Handoff를 dependency input으로 사용한다.
>
> 각 Work에서:
>
> OWNER_ACTION_REQUIRED
>
> 가 발생하면 단순 기록하고 기다리지 않는다.
>
> Main이 authoritative owner를 확인하고 해당 owner에게 routing한다.
>
> 가능하면 machine/checkable receipt / evidence / acceptance criteria 형태로 전달한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 4. OWNER ROUTING LOOP
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 OWNER_ACTION_REQUIRED에 대해:
>
> Finding
> ↓
> Authoritative Owner
> ↓
> Required Artifact
> ↓
> Exact Path / PR / Branch
> ↓
> Acceptance Criteria
> ↓
> Owner Action
> ↓
> Evidence Receipt
> ↓
> Scoped Work 재소비
> ↓
> Blocker 재판정
>
> 루프를 유지한다.
>
> "다른 owner가 해야 한다"
>
> 라고 기록하는 것만으로 완료 처리하지 않는다.
>
> 실제 routing 또는 owner-consumable handoff packet까지 만든다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 5. GLOBAL-ONLY CHANGE PROPAGATION
> ━━━━━━━━━━━━━━━━━━━━
>
> 중요:
>
> 어떤 dependency 변화가 owner PR HEAD 변경 없이
> Global Handoff / Status / Decision Register에만 기록될 수 있다.
>
> 이 경우에도 영향받는 scoped Work가 이를 소비할 수 있도록 routing한다.
>
> 특히:
>
> - QGV decision/approval
> - Chart Portfolio/Identity/Product/FPIA dependency
> - Platform Auth/Tenant/Connector dependency
>
> 의 material semantic delta를 확인한다.
>
> 모든 Global commit을 모든 Work에 broadcast하지 않는다.
>
> 해당 Work의 blocker/dependency에 실제 영향을 주는 변화만 전달한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 6. CHART CURRENT ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart PR #41의 최신 scoped handoff를 fresh-read한다.
>
> 마지막 확인 기준 Lane A에는 다음 6 gate가 있었다.
>
> 1. authoritative TARGET root
> 2. Security mapping
> 3. Theme revision/version
> 4. Product authority
> 5. owner write-set acceptance
> 6. FPIA governance/admissibility
>
> 이를 최신 evidence로 다시 확인한다.
>
> 각 gate의 owner를 명시적으로 routing한다.
>
> 예상 ownership은 참고일 뿐이며 fresh-read가 우선한다.
>
> TARGET root
> → Portfolio
>
> Security mapping
> → Identity
>
> Theme revision
> → Portfolio / Classification
>
> Product authority
> → Product/P01
>
> write-set
> → Web/Product/Integration
>
> FPIA
> → Integration
>
> 기존 사용자 결정으로 D3→D2 범위가 완화된 항목은
> 과거 D3 상태를 관성적으로 유지하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 7. QGV ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> QGV Work의 최신 unresolved items를 읽는다.
>
> 예:
>
> - Missing-Data
> - requiredness/applicability
> - method/version identity
> - G 3–5Y
> - EPS→FCF
> - V normalization/metadata
> - Composite
> - WeightOverride
>
> QGV Work 자체가 수행 가능한 연구/감사/검증은 맡기고,
> 다른 owner consumer/integration dependency만 Main이 routing한다.
>
> QGV production semantics를 Main이 임의로 결정하지 않는다.
>
> 실제 numeric/method/policy D3만 사용자에게 올린다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 8. PRODUCT PLATFORM ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> Product Platform Work의 최신 capability matrix와 blockers를 읽는다.
>
> 범위:
>
> - Auth
> - Tenant isolation
> - Financial Connector
> - financial record sync/import
> - Reconciliation
> - immutable/auditable records
> - Read-only hard gate
> - Product API
> - Web/PWA
> - investment-engine integration
>
> 보안/tenant/read-only 문제는 fail-closed로 처리한다.
>
> Platform Work에서 다른 owner dependency가 발견되면
> Main이 routing한다.
>
> 실제 credential/금융계정/production auth/유료 connector는
> 사용자 승인 없는 자동 진행 대상이 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 9. D1 / D2 / D3
> ━━━━━━━━━━━━━━━━━━━━
>
> 현재 승인된 authority policy를 fresh-read하여 적용한다.
>
> D1:
> 자동 진행
>
> D2:
> 근거·검증·복구계획을 남기고 보수적으로 자동 진행
>
> D3:
> 실제 사용자 결정 필요
>
> 과거 D3 label만 보고 멈추지 않는다.
>
> 최신 Decision Register에서 D2로 재분류되었으면 자동 진행한다.
>
> 반대로 protected semantic 변경을 D2로 임의 낮추지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 10. INTEGRATION / FPIA
> ━━━━━━━━━━━━━━━━━━━━
>
> FPIA는 Main의 핵심 책임이다.
>
> 구분:
>
> - implementation
> - CI
> - independent review
> - adversarial review
> - governance closure
> - GIE closure
> - canonical applicability
> - exact merge-result FPIA
>
> CI PASS만으로 전체 closure를 선언하지 않는다.
>
> 발견된 우회/환경 의존성은 승인 범위에서:
>
> repair
> → targeted regression
> → full/affected regression
> → independent/adversarial verification
> → evidence
> → closure
>
> 까지 자동 진행한다.
>
> 실제 D3만 사용자에게 escalation한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 11. LEASE / CONCURRENCY
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 scoped Work/owner branch의 lease를 존중한다.
>
> active writer가 있으면 같은 branch에 쓰지 않는다.
>
> Main이 다른 owner branch를 직접 덮어쓰지 않는다.
>
> Global Handoff는 Primary Integration Writer 규칙을 따른다.
>
> force push / history rewrite 금지.
>
> 장시간 CI를 기다리며 write lease를 붙잡지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 12. AUTO-CONTINUATION
> ━━━━━━━━━━━━━━━━━━━━
>
> 사용자에게 매 단계마다 "계속할까요?"라고 묻지 않는다.
>
> D1/D2 범위에서:
>
> - routing
> - retry
> - repair
> - retest
> - regression
> - evidence collection
> - review
> - owner handoff
> - dependency propagation
> - integration trial
>
> 은 자동으로 계속한다.
>
> 한 Work가 D3에 막혀도 다른 독립 Work와 owner routing은 계속한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 13. COMPLETION CRITERION
> ━━━━━━━━━━━━━━━━━━━━
>
> Main의 성공 기준은 문서량이나 PR 수가 아니다.
>
> 다음이 개선되어야 한다.
>
> - unresolved owner dependencies ↓
> - duplicate work ↓
> - stale WAITING ↓
> - D1/D2 autonomous completion ↑
> - cross-owner propagation ↑
> - integration readiness ↑
> - production blockers ↓
>
> scoped Work가 OWNER_ACTION_REQUIRED를 반복해서 보고하는데
> 아무 owner도 실제 action을 받지 않는 상태를 허용하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 14. REPORT
> ━━━━━━━━━━━━━━━━━━━━
>
> 의미 있는 변화가 있을 때 다음만 보고한다.
>
> 1. canonical / Global exact HEAD
> 2. Integration/FPIA 상태
> 3. QGV blockers / owner routing
> 4. Chart blockers / owner routing
> 5. Platform blockers / owner routing
> 6. 이번에 해결된 dependency
> 7. 진행 중 owner actions
> 8. D1/D2 자동 진행 결과
> 9. 실제 USER_D3_REQUIRED
> 10. 다음 critical path
>
> No material change면 불필요한 장문 보고를 만들지 않는다.
>
> 최종 원칙:
>
> Scoped Work는 전문 업무를 수행한다.
> Claude Main은 서로 연결한다.
> OWNER_ACTION_REQUIRED는 routing한다.
> D1/D2는 자동 진행한다.
> 실제 D3만 사용자에게 돌아온다.
> Global Handoff는 전체 시스템의 dependency routing SSoT 역할을 한다.

Recorded effect (routing writer's reading; the user wording above governs):

- The Integration / Claude Main Work is the Primary Integration Coordinator: cross-owner dependency routing, Global Handoff coordination, Integration/FPIA, write-set conflict prevention, integration-readiness judgement of scoped results, D1/D2 coordination, escalation of real D3 only, and canonical integration preparation. It does not redo scoped Works' specialist work (QGV scoring research, Chart contract/rendering, Product Platform auth/tenant/connector/reconciliation, Portfolio Target, Security/Listing identity, Product publication authority).
- Three continuous audit Works are treated as running independently: QGV structural re-audit, Chart implementation audit, Product Platform implementation audit. Every OWNER_ACTION_REQUIRED they report is routed to its authoritative owner as an owner-consumable, machine-checkable packet and tracked through the loop Finding → Owner → Artifact → Path → Acceptance → Owner action → Evidence receipt → Scoped re-consumption → Blocker re-judgement. Recording "another owner must act" alone does not close an item.
- The Global Handoff is the dependency-routing SSoT. Material semantic deltas recorded only on the Global branch are propagated to the affected scoped Work through a channel it consumes; non-material Global commits are not broadcast.
- QGV production semantics are not decided by Main; QGV research/audit/verification stays with the QGV Work. Product Platform security, tenant and read-only issues fail closed; real credentials, financial accounts, production auth and paid connectors are not progressed automatically without user approval.
- D1/D2/D3 follow the current authority policy (CDR-015 as narrowed by CDR-016 §13 and this entry); a past D3 label is not a reason to stop, and a protected semantic change is not lowered to D2.
- Leases and concurrency: active writers' branches are not written; no other owner's branch is overwritten; no force push or history rewrite; no write lease is held while waiting on long CI.

