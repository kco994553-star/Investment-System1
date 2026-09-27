# Track A REAL-DATA Baseline — 2026-09-27 19:56 KST

**상태: BLOCKED / NOT FROZEN. 새 D3-P 후보 CA-UNIT-v1.0 승인 대기. 원격 미반영.**

기준: 최신 GitHub `ebf8263`; Actions #70 (`36305927245`, evidence `ed343ba`). 다른 Track의 코드·명세는 변경하지 않았다.

## 이번에 실제 완료한 일

- 원본 Actions 압축파일 SHA-256 검증 및 raw 6,808개/6,136,954,924 bytes의 개별 해시·크기 검증: PASS.
- C-40: 미래 BlackRock CIK가 과거 날짜의 재무 입력을 덮어쓰던 워크포워드 오류 수정. 실제 BLK 데이터에서 재현 및 단일 날짜와 일치 확인.
- 500종목 메모리 적재에서 exit 137을 확인하고 종목별 지연 읽기로 변경. 세 날짜 진단 재생 성공, 최대 메모리 363.1 MiB.
- 수정 전 roster를 RESEARCH로만 사용한 3-date 진단 워크포워드: 두 구간 모두 단일 날짜 결과와 종목 목록·수익률·연결 수·오류가 일치. 날짜별 선정 471/469/468, name errors 0. 이 진단은 무효화된 Universe를 복원하거나 Official 결과를 승격하지 않는다.
- 세 날짜 전체 후보(992/990/987)에 대해 Gate 재실행: base Promotion Gate v2 및 내부 Gate/Snapshot consistency는 PASS지만 새로운 주식 수/가격 단위 감사는 FAIL. 최종 Official 선언은 세 날짜 모두 false.
- 현재 Official pipeline 재실행: BLOCKED_NO_OFFICIAL_DATE / BLOCKED_NOT_ALL_DATES_OFFICIAL. 과거 Official snapshot JSON은 역사적 증거로 보존하고 freeze_readiness JSON에 SUSPENDED_C41로 명시했다.

## 현재 blocker

C-41: 주식 수 공시 뒤 기준일 이전의 분할·주식배당·분사·합병을 가격과 동일한 단위로 재구성하는 일반 기준이 빠져 있다. 후보 이벤트는 20건(4/8/8). NVDA만의 예외가 아니며 CMG처럼 기존 Top-500 밖 후보에도 영향을 줄 수 있다. SIRI의 합병 교환, ILMN의 분사 가격 조정은 단순 분할 배율 적용과 구분해야 한다.

정책 후보: `implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md`.
순수 분할은 증권·배율·효력일·측정단위를 1차 근거로 확인, 분사는 모회사 수량 변경과 구별, 합병은 소각·교환·추가발행을 별도 확인한다. 기존 사후 재구성 허용을 확장하지 않는다. 승인 전 어떤 배율도 적용하지 않았다.

## Freeze 경로의 현재 판정

| 확인 항목 | 판정 |
|---|---|
| 실제 raw 복구/무결성 | PASS |
| 기존 C-34~C-38 처리 | Run #70에서 적용·통과; 새로운 C-41과 별개 |
| corrected Gate 최종 승격 | BLOCKED — 3/3 날짜의 단위 감사 FAIL |
| 현재 유효한 Official snapshot | SUSPENDED — 역사적 파일만 보존 |
| Official single_as_of / 3-date Walk-Forward | BLOCKED; 수정 경로의 RESEARCH 진단만 PASS |
| 실제 500종목 재생 성능 | 측정 완료; 네트워크 수집 포함 측정은 미완료 |
| PIT/provenance/regression audit | raw/회귀/식별자 PASS; C-41 미해결 |
| Track A Baseline FROZEN | NO |

이 표는 기존 Track A 실행 경로의 상태다. 전체 Investment System의 OOS/Calibration/Forward Validation 또는 Track C 승격 기준을 대체하지 않는다.

## 다음 작업과 전달

1. 새 D3-P CA-UNIT-v1.0 승인 여부 결정.
2. 승인 후 모든 후보의 1차 증거 대조와 D3-C 적용 → 세 날짜 Gate/Official 재생성 → Official 워크포워드 및 네트워크 포함 benchmark → 최종 audit.
3. 모든 수용기준이 실제 충족될 때만 Track A FROZEN으로 기록하고 멈춘다.

GitHub git push는 인증 정보 부재, 연결 앱 branch 생성은 HTTP 403으로 실패했다. 변경은 로컬 commit/patch/bundle로 보존하며 원격 반영됐다고 주장하지 않는다. 새 API 키는 이번 수정·감사에 필요하지 않았다.
