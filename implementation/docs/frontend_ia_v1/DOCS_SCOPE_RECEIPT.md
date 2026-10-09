# Cockpit IA v1 문서 전용 작업 범위 영수증

다음 「PR #70 이후 문서 전용 범위」가 현재 작업 기준이다. 아래 최초 작업 기록은 당시 이력으로 보존하며, 과거 write-set·검증 결과를 현재 범위·결과로 재사용하지 않는다.

- 사용자 권한: 2026-10-09 「Cockpit IA v1 공식화 + 차트 목록 보강 + 26E 결정」 문서 전용 PR 지시.
- 기준 canonical: `d71243bcc79139149541f3627e8f227a32c463c5` (PR69 병합 이후).
- 작업 브랜치: `docs/cockpit-ia-v1`.
- lease_run_id: `cockpit-ia-docs-20261009T0325`
- lease_status: `RELEASED`
- lease_holder: `Main-directed observed documentation session`
- lease_acquired_at: `2026-10-09T03:24:35Z`
- lease_expires_at: `2026-10-09T05:24:35.000Z` (2시간).
- lease_released_at: `2026-10-09T03:37:54Z`
- 반환 이유: 문서 PR #72 생성 후 사용자 검토 대기. 이 기록은 다른 Work의 ownership·lease·STATE를 변경하지 않는다.
- AUTONOMY_MODE: `READ_ONLY` 유지. 이번 직접 지시는 이름 붙은 문서 작업만 허용하며 RUN/unattended 승인이 아니다.

## 승인된 write-set

- `implementation/docs/frontend_ia_v1/*.md`: IA, 디자인 출처, 본 범위 영수증.
- 기존 IA/화면 구조 `.md`: 사용자가 지정한 SUPERSEDED 한 줄만 맨 위에 추가; 나머지 바이트 보존.
- `implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md` 및 `chart_inventory.json`: 문서 요구사항·연결만 동기화. 후자는 실행 데이터가 아닌 기존 문서 inventory다.
- `implementation/docs/pages_cockpit_owner/*.md`: 26E 결정·SSoT8/26D 범위 영향·문서 조사. 기존 evidence 및 원본 기록은 보존.

## 금지·반환 계약

화면/데이터/계산식/워크플로/자동화/권한/규칙/AUTONOMY_MODE 및 DOCX를 변경하지 않는다. TARGET·금액·수량·평가액·계좌·키를 게시하지 않는다. 공급자 관측값 호출, 키 발급·가입·구현, Holdout 사용, 새 방법론·가중치·점수식 및 주문 기능을 하지 않는다. canonical 병합은 사용자 승인 대기다. 새 요구는 REQUIREMENT_IDENTIFIED_NOT_REAUDITED/NOT_AVAILABLE일 뿐 재감사·구현 완료가 아니다. 이 lease는 이 브랜치와 명시 write-set에만 유효하며 다른 Work의 소유권을 바꾸지 않는다.

## 문서 검증·인계

- [PR #72](https://github.com/kco994553-star/Investment-System1/pull/72): canonical 대상의 문서 전용 PR 1개, 미병합. 사용자 승인 전 병합하지 않는다.
- 검토 후보: `8155476afc16b6fb63acf3b82525570a9e29e826`, tree `1b966ecba165e04baa433ea6068f722be966142e`. 로컬 검증 tree와 정확히 일치했다.
- 13개 문서 경로만 변경. 기존 IA 3개 본문·DOCX·113개 inventory 항목·핵심81·baseline 보존, 12화면·신규8/총121·이관36묶음·상대 링크25개 확인. 독립 문서 검토의 차단 결함 없음.
- 로컬 가드 단위검증 37 tests OK. 기존 전체 Python 회귀 745 passed, 217 subtests passed. 관측값 수집·Holdout 선택/사용·방법론 변경 없이 기존 테스트만 실행했다.
- 검토 후보의 개인정보 가드·repository guard PASS, AUTONOMY_MODE READ_ONLY. GitHub repository-guard도 검토 후보에서 success; 이 반환 기록 이후 최종 HEAD의 CI는 별도 확인해야 한다. CI PASS는 gate 승격이나 API 채택 승인이 아니다.
- 남은 항목: 사용자 PR 병합 검토, 상세 시안 OPEN 4개, 이관 확인36묶음, 기기 직접 API의 미확인 gate와 별도 사용자 선택. 후속 구현·배포는 실행하지 않는다.

## PR #70 이후 문서 전용 범위 (2026-10-09)

- 사용자 지시: 「Cockpit IA v1 공식화 + 차트 목록 보강 (문서 전용 PR)」. 기준 canonical은 `011b75648f48f2890736d37c4a354f57004cf1f0`이며, 작업 브랜치는 `docs/cockpit-ia-v1`이다.
- 결과는 기존 [PR #72](https://github.com/kco994553-star/Investment-System1/pull/72) 한 개를 갱신한다. 기존 브랜치 이력을 보존하며 force push·canonical 병합을 하지 않는다. 병합은 사용자 승인 대기다.
- 현재 write-set은 이 폴더의 IA·디자인 출처·범위 영수증, 과거 IA Markdown 3개의 안내 한 줄, `implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md`와 문서용 `implementation/experiments/chart-contract-v0.1/chart_inventory.json` 동기화뿐이다. 실행 데이터·코드·계산식·워크플로·DOCX는 변경하지 않는다.
- 최초 작업의 `pages_cockpit_owner` 시세 조사 문서 변경은 현재 기준 canonical 내용으로 되돌린다. 당시 커밋 이력은 보존하지만 이번 PR의 최종 변경 범위에는 포함하지 않는다. 시세·환율 결정은 S11의 PR #70 구현 기록과 Alpha Vantage REVIEW ONLY·API OFF 기록 링크로만 연결한다.
- 신규 차트 요구는 L01–L07·L09의 8개이며 L08은 기존 K01 연결이다. 총 121개이고 기존 핵심 분모 81·113개 항목·감사 결과는 유지한다. 모든 새 요구·연결은 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`, 공급처는 `UNDECIDED`다.
- 검증은 현재 최종 문서 내용·원문 바이트·DOCX·상대 링크·기존 inventory 보존·개인정보 가드·repository-guard와 별도 독립 문서 검토를 대상으로 새로 수행한다. 위 최초 작업의 테스트·CI 결과는 현재 HEAD의 증거가 아니다.
- READ_ONLY 유지. 상세 시안 OPEN 및 이관 배치 확인은 후속 문서 검토 사항이며 구현·배포·새 계산법·API 채택 권한을 부여하지 않는다.

## PR #73 승인 병합 이후 문서 작업 재개 (2026-10-09)

이 절이 최신 작업 기준이며 앞의 PR #69·#70 기준과 검증 기록은 당시 이력으로 보존한다. 기존 본문 바이트를 수정·삭제하지 않고 이 절만 끝에 추가한다.

- 최신 사용자 지시: 「#73 병합을 승인합니다」와 「이전에 전달한 "Cockpit IA v1 공식화 + 차트 목록 보강 (문서 전용 PR)" 지시를 이어서 진행. 아직 시작하지 않았다면 지금 시작. 병합은 사용자 승인 대기」. PR #73만 승인 병합 대상이며 PR #72·다른 PR 병합은 승인되지 않았다.
- 문서 기준 canonical: `13e025b0e545fb3da14c15ce065a6a8e4a368eb0` (PR #73 승인 병합). 기존 `docs/cockpit-ia-v1` 이력과 PR #72를 이어서 사용하며 force push·ruleset·AUTONOMY_MODE 변경을 하지 않는다.
- 이번 추가 수정은 이 폴더의 `COCKPIT_IA_v1.md`, `DESIGN_SOURCE.md`, 본 영수증 3개뿐이다. 기존 전체 PR write-set 8개 문서 경계를 유지한다. 실행 코드·데이터·워크플로·DOCX·기존 차트 항목·감사 판정을 변경하지 않는다.
- S11은 PR #70의 수동 입력·KRW와 PR #73의 선택형 기본 OFF Google 시트 직접 읽기·단일 readonly scope·메모리 토큰·기기 ID/범위·백업 제외·로그인 없는 붙여넣기를 기존 owner 기록 링크로 연결한다. 일반 앱 계정 로그인·계좌 연결·동기화와 시세 소스 인증을 구분한다. Alpha Vantage OFF, 한국투자증권·중계 서버 DEFERRED, 수동 유지·주문 없음은 그대로다.
- IA 12화면·이관 확인39묶음, 차트 총121·핵심81·기존113, 신규 L01–L07·L09의 8개 및 L08→K01 연결을 유지한다. 신규 요구·연결은 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`, 공급처는 `UNDECIDED`다.
- 실제 Google 로그인은 하지 않는다. 실제 스크립트·공개 사이트 CSP·390/1280px 기기 확인은 별도 실행 작업이며 이 문서 PR의 PASS로 재사용하지 않는다. 문서 병합·구현·배포는 사용자 승인을 기다린다.
- 이번 문서 후보의 새 확인: 추가 수정 3개·전체 PR 문서 8개, 앞선 영수증 본문 prefix 보존, 과거 Markdown 3개 안내 한 줄 이후 원문 및 DOCX 바이트 보존, 12화면·이관39·차트121·기존113 항목 deep equality·핵심81·기존 baseline metrics·신규8/L08→K01 모두 PASS. 상대 링크7개·S11 절 anchor1개·PR #73 canonical owner 문서 링크3개가 실제 파일·절로 연결됨을 확인했다. `git diff --check` 통과.
- 현재 docs 브랜치 이력·작업 파일 가드와 PR #73 canonical에 문서8개만 적용한 별도 staged 후보의 최신 개인정보·repository guard가 각각 PASS, violations `[]`, mode `READ_ONLY`다. 최신 가드 단위 테스트 132개 PASS. 실제 관측값 호출·실제 Google 로그인·화면 코드 수정 없이 실행했다.
- 별도 읽기 전용 독립 문서 검토에서도 위 원문·inventory·요구사항 상태·인증 구분·Markdown 링크15개를 확인했고 material finding은 없었다. 새 게시 커밋의 native CI는 게시 후 따로 확인해야 하며 앞선 PR #72·#73의 테스트/CI 결과를 새 후보의 결과로 재사용하지 않는다.
