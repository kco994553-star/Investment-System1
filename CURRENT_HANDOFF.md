# 현재 인수인계 — 2026-10-14 (Claude Code)

먼저 읽기: [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md) → [PLAYBOOK_V1.md](implementation/docs/playbook/PLAYBOOK_V1.md)(17절 포함).
10/13까지의 긴 기록은 [HANDOFF_HISTORY_THROUGH_20261013.md](implementation/docs/handoff/HANDOFF_HISTORY_THROUGH_20261013.md)에 있다.

## 현재 상태

- canonical `claude/investment-system-top500-validation-alrugm`.
- 10/14 승인 병합 5건: #234(QGV v2 V·원장2) → #233(플레이북 화면·기록) → #235(매크로·DART 참고) → #231(13F) → #237(로고·TradingView iframe). 각 최신 HEAD에서 필수 6체크 성공 후 병합했다.
  - #233은 동기화 뒤 가상 장부 세트 저장 안내가 다시 그리기 때 사라지는 경쟁 조건이 있어 원인을 고쳤다(테스트 조건은 바꾸지 않음).
- 배포(D-DEPLOY, 10/14 12:06 UTC): Pages(cockpit-pages 수동 실행)와 Worker(private-history-deploy) 모두 성공했다.
  - 같은 커밋을 로컬에서 빌드해 390/1280px를 확인했다(가로 넘침 0, 외부 요청 0, TradingView 꺼짐).
  - 컨테이너에서는 공개 주소(github.io)를 열 수 없다.
- **SEC 일일 실행은 10/10~10/13 4회 모두 실패했다.**
  - 실패 단계는 "Verify device features"다. 원인은 `dart_disclosures` 테스트가 실데이터 없음을 전제한 것(10/13)이다.
  - 그래서 그날 샤드(Universe504 7분할)가 공개 파일에 반영되지 않았다.
  - 수정 PR과 실행 분리 PR(A)은 진행 중이다. 아래 열린 PR 표를 본다.
- v2 커버리지(B, #238): 공개 Q 207/504, G 222/504의 주원인은 샤드 미수집이다. 전체 수집 시 오프라인 계산은 Q 471, G 493(#238 포함)이다.
- 10/14 추가 병합(필수 6체크 성공): #243 DART·개인 이력 테스트 실데이터 가정 수정(10/13 일일 실행 실패 원인), #241 v2 품질·#19 우량·후보 30 초안 보고서(`QGV_V2_QUALITY_20261014.md`), #242 휴장일 채점 = 직전 완료 거래일(B-1).
- 매크로: #239로 과거 재생 완료 전까지 참고 표시만 한다(승인 대기).
- 과거 PR 16개(#4, #7, #10~#19, #29, #31, #43, #71)는 제목에 `[historical]`을 붙여 닫았다. 연결 도구에 PR 라벨 기능이 없어 라벨 대신 제목을 썼다. 브랜치·이력은 보존했다.

## 열린 PR

| PR | 내용 | 상태 |
| --- | --- | --- |
| #238 | v2 매출 태그 1개 추가(DTE·XEL G 복구) | 계산 변경 → 승인 필요, 6체크 성공 |
| #239 | 매크로 게이트 비활성(참고 표시) | 판정 동작 변경 → 승인 필요 |
| #240 | 일일 워크플로 분리(collect / verify / deploy, 실패 토큰 `DAILY_VERIFY_FAILED`) | 워크플로 → 승인 필요 |

알려진 제품 문제: 실데이터 `sec-qgv2.json`이 있으면 기업 화면이 v2 시세 갱신 뒤 다시 그려져 불러온 개인 이력 표가 사라질 수 있다(app.js `refreshQgv2Quotes`). 별도 수정 필요.
원장 주의: 전진검증 원장의 이전 기록은 Pages 사본에서 읽는다. 배포가 보류된 날의 기록은 raw release에만 남는다(#240 이후 별도 변경 필요).

## 결정 대기

[USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md) 참고. 요약: #238·#239·워크플로 분리 승인, 매크로 규칙 재검토(재생 후), [QGV v2 채택과 TARGET v1 재구성]·[화면 정리] 지시 원문 재전달 필요(이 세션에 도착하지 않음).

## 다음 할 일 5개

1. 10/14 22:17 UTC 일일 실행(샤드 3)이 성공하고 배포되었는지 확인한다(#243 반영). 실패하면 원인을 고치고 같은 UTC 날짜 안에 workflow_dispatch로 재실행한다(샤드 손실 방지).
2. 워크플로 분리 PR 승인 후 병합한다. 10/19 전에 끝내야 한다.
3. 10/19 준비(대기열 2):
   - 2-1 시작 가능 여부: v2·v1 원장, 세트 A, V 기록.
   - 2-2 10/16·10/17 데이터로 리허설.
   - 2-3 10/20 첫 기록 확인.
4. 화면 정리 1·3(NVDA 유형 버그, 원자료 카드 이동)은 지시 원문을 받은 뒤 진행한다. B 커버리지는 #238 승인 후 다음 단계로 간다.
5. TARGET v1 후보는 초안만 만든다("커버리지 편향 가능" 표시). 확정·카드 화면 공개는 커버리지 보고 후에 한다.
