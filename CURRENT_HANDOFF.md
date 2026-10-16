# 현재 인수인계 — 2026-10-16 밤 (Claude Code)

먼저 읽기: [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md) → [PLAYBOOK_V1.md](implementation/docs/playbook/PLAYBOOK_V1.md)(17·18절 포함).
이전 기록: [HANDOFF_HISTORY_THROUGH_20261013.md](implementation/docs/handoff/HANDOFF_HISTORY_THROUGH_20261013.md), [HANDOFF_HISTORY_20261014_15.md](implementation/docs/handoff/HANDOFF_HISTORY_20261014_15.md).
보고 규칙: 시각은 UTC와 KST를 함께 적는다. `PUBLISHED_COVERAGE`는 같은 실행의 deploy 성공을 확인했을 때만 "실제 게시 커버리지"라고 부른다.

## 최신 실행 증거

- **10/14 정기 실행**(22:37 UTC / 10/15 07:37 KST, run 38648878883)
  - 성공했고 23:05 UTC(10/15 08:05 KST)에 배포됐다.
  - 10/10~10/13 실패 이후 처음 성공한 실행이다.
- **10/15 정기 실행**(22:37 UTC / 10/16 07:37 KST, run 38818351490, head 4badfff0)
  - #240 구조로 처음 돈 실행이다. collect·verify·deploy 모두 성공했고, 23:04 UTC(10/16 08:04 KST)에 배포됐다.
  - 단계 순서는 W-F1대로다. DART → Universe 샤드 4 → DART 투영 → **원장** → SIC·로고·13F → 8-K·뉴스 → 커버리지 보고 → 업로드.
  - 원장: `FORWARD_LEDGER_PREVIOUS source=PAGES raw=NONE`. 시작일 이전이라 비공개 사본이 없고, `NOT_STARTED`이며 업로드하지 않았다(정상).
  - **실제 게시 커버리지:** Q 146 / G 150 / 둘 다 143 (504 중). 샤드 2/7(3: 10/14, 4: 10/15). 수집 기록 없는 행 350, 7일 넘은 행 0, calc_version 없음(#264 미병합).
  - 매크로 공개 경고등 3/5(곡선·고용·물가). 모두 LIVE이고 켜진 것은 없다.
  - DART(한미반도체)는 정상이다.
- **두 번 성공했다고 장기 운영 안정성이 검증된 것은 아니다.** 10/16·10/17 실행을 리허설로 계속 확인한다.

## 원장 연속성 (W-F2)

- 테스트로 확인했다. "배포가 보류된 날 → 다음 날 비공개 사본에서 복구"(`test_a_withheld_day_is_recovered_from_the_private_copy_the_next_day`)와 대체 경로 테스트가 통과한다(#240).
- 운영에서 확인한 범위: RAW_FIRST 설정이 적용됐고, 시작일 이전에는 정상 동작한다.
- **실제 비공개 사본 복구는 아직 확인하지 못했다.** 실제로 배포가 실패한 날이 생기면 다음 실행에서 아래를 확인한다.
  - 비공개 사본을 골랐는지
  - 누락 행이 복구됐는지
  - 행이 중복되지 않았는지
  - 기존 행이 보존됐는지
- 확인하려고 운영 배포를 일부러 실패시키지 않는다.

## 병합 상태 (2026-10-16 13:30 UTC / 22:30 KST 기준, canonical 6d4bb5cd)

- 10/16에 병합했다(모두 기준과 동기화한 최신 HEAD에서 필수 6체크 성공 확인).
  - #270 인수인계·결정 기록
  - #271 원장 관측 기준(basis·PRIMARY/PREPARATORY·평가 구간)
  - #272 calc_version 표시 수정
  - #247 v2 보강 태그
  - #264 v2 규칙 + `calc_version=qgv2-calc/2026-10-15.1`
  - #259 DCF h 기간 규칙(#264와 충돌을 양쪽 반영으로 해결)
  - #273 차트 설계 문서(구현 착수 아님)
- 승인됐고 순서를 기다린다: #248 → #263(TARGET v1), #260 → #262(매크로).
- 보류: #267(합성 데이터 투자 스튜디오).

## 다음 실행 작업

1. **10/16 정기 실행**: 예약 22:17 UTC(10/17 07:17 KST). 새 규칙으로 도는 첫 실행이다.
   - 이전 샤드 행에는 calc_version이 없어 순위 모집단에서 빠진다. 그래서 게시 Q·G가 일시적으로 줄 것으로 예상한다.
   - 점검은 23:15 UTC(10/17 08:15 KST)에 한다(예약됨).
2. **504종목 일괄 수동 실행**(`all_shards=true`): 10/17 UTC 중 정기 실행과 겹치지 않게 돌리고 검증·배포까지 마친다.
   - 보고할 것: 실행 ID·커밋·calc_version, 샤드별 성공·실패, 이전 값 유지 행, 정상 NA, 버전 불일치, 수집 시각 범위, Q·G·동시 산출 수, collect·verify·deploy.
3. **10/17 정기 실행**에서 전체 데이터가 유지되는지 확인한다. 점검은 23:15 UTC(10/18 08:15 KST)에 한다(예약됨).
4. 10종목 숫자 재대조를 같은 calc_version으로 한다.
5. 10/18은 여유일이다. 최종 준비 목표는 10/18 22:00 UTC / 10/19 07:00 KST. 시각 때문에 필수 검증을 생략하지 않는다.
6. 차트 구현은 착수 조건 5개를 보고한 뒤 사용자가 결정한다(설계: `implementation/docs/technical_chart/TECHNICAL_PATTERN_CHART_V1_DESIGN.md`).

## 다음 보고의 핵심

1. 실제 게시 Q·G 각 454개 이상 여부와 calc_version
2. 수정 후 10종목 재대조 결과
3. 원장 연속성: 테스트 결과와 실제 운영에서 확인한 범위
