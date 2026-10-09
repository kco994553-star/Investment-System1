# Cockpit IA v1 문서 전용 작업 범위 영수증

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
