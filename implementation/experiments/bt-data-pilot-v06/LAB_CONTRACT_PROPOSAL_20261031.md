# Lab 계약 — 결과 경로 제안 및 lab-results/1 차이

기능 9.1 · **Main 합의 전 후보**, 공개 파일 생성 없음. 사용자 2026-10-31 「백테스트 연구·Lab 결과 생산 단일 최종본」과 「Lab 계약 제안 전달 방식」에 따른다. Codex는 연구·비공개 결과 원본만, Main은 앱·중앙 V·공통 가드·워크플로·게시 경로를 맡는다.

## 확인한 정본과 의존성

- 최신 기본 브랜치 `claude/investment-system-top500-validation-alrugm`, 조회 SHA `32cc3ffd54ba86f08a6ed87b67be9226c9834be0`.
- `START_HERE`, `WORKING_RULES`, `CURRENT_HANDOFF`, `DIRECTION_CHANGES`, `USER_DECISIONS_PENDING` 확인. 정본 결정 문서에는 새 `lab-backtest-v1` 확정 기록이 없고 `LAB-PUBLISH`의 옛 계약이 남아 있다. **사용자 초안을 Main이 이미 합의한 것으로 취급하지 않는다.** 재개 때 기본 브랜치를 다시 조회하고 결정 기록을 확인한다.
- #416 `ce6acdfa…` 기준, #417 `ec9788a6…` 연구 엔진, #418 `ef745b96…` 연간·분위 설계, #430 `56a0e8ce…` 재고정 제안은 각각 OPEN. 자동 병합하지 않는다.
- #432 `26396d1f9f71706ae6deaa1ee51797bebb4d9ffc`의 실자료·수집기·재현 결과를 그대로 보존한다. 이번 PR은 #432 연구 가지 위의 작은 후속이며 기존 워크플로를 수정하거나 호출하지 않는다.
- 기존 연구 장부·달력·통계는 보존 작업 트리 `ca310378ba4fe40a1a971da30b475d9812c68a15`의 `implementation/src/investment_system/research/qgv_backtest/`를 직접 import한다. 중복 엔진이나 코드 이동 없음. `source_commit`은 실행한 이번 연구 코드 전체 SHA이며, 외부 연구 의존성 SHA와 파일 해시는 비공개 evidence에 추가 기록한다.

## 경로 제안 — 새 영구 디렉터리 생성 없음

| 용도 | 제안/현재 위치 | 경계 |
|---|---|---|
| 연구 등록·어댑터·시험·계약 문서 | 기존 `implementation/experiments/bt-data-pilot-v06/` | 코드와 합성 시험만 저장소에 기록 |
| 임시 실제 결과 후보 | 기존 비공개 `$BT_PILOT_PRIVATE_ROOT/v-ledger-audit/results/lab-backtest-v1.candidate.json` | Main 경로 확인 전 임시 파일; 실제 수익곡선 포함, 공개 금지 |
| 비공개 재현 근거 | 같은 기존 위치의 `lab-backtest-v1.evidence-private.json` | 입력 해시·원본 경로·일별 장부 포함, 공개 금지 |
| 정식 연구 결과 | 기존 #417 승인된 비공개 출력 루트의 결과 원본과 나란히 둘 것을 제안 | 정확한 배치·소유권은 Main 확인 후 고정 |
| 공개 게시 파일 | **미생성·경로 미확정** | 이용권 확인 → Main의 허용목록 변환·검증 경로에서만 생성. 후보를 그대로 복사하지 않음 |

현재 임시 루트는 `/workspace/private-bt-data-pilot-v06`이다. 실제 결과 파일은 공개 checkout 밖이며 0600으로 기록한다. 경로를 확정했다는 의미가 아니다. 계약 또는 경로 결정이 없더라도 내부 파일럿은 계속한다. #436의 비공개 웹 연결은 이 실행의 선행 조건이 아니다.

## 두 계약의 차이·충돌

기존 근거: canonical `implementation/docs/expanded_universe/MAIN_E1B_E2_DESIGN_20261029.md` §5.4~5.6 및 `USER_DECISIONS_PENDING.md` LAB-PUBLISH.

| 항목 | lab-results/1 | 사용자 lab-backtest-v1 후보 / Main 조치 |
|---|---|---|
| 목적 | 공개 게시용 엄격 허용목록 | 비공개 결과 원본. 공개용 파일과 분리 |
| 최상위 | `schema`, `experiments` | `schema_version`, `generated_at`, `source_commit`, `runs` |
| 실행 구분 | 등록 전략 상태 | `PILOT/FORMAL`, `REAL/SYNTHETIC/MIXED`, 검증 상태를 독립 표시 |
| 모집단 | 미리 정한 정식 universe ID | 표본 선정 정의·PIT boolean·생존편향 설명 허용. PIT boolean은 모집단에만 적용 |
| 지표 | `{value, na_reason}`, `annualized_volatility` 등 | 숫자/null, `null_reasons`, `volatility`; 소수 수익률·음수 MDD |
| 비용 | ONE_WAY_BPS 열거형 | fee/slippage 숫자 각각 한쪽 체결 기준. 합계·중복 차감 주의 |
| 비교 | comparisons + CAGR 차이 | benchmark + benchmark_cagr + excess_cagr. 롱숏 성과 아님 |
| 시계열 | NAV·daily/monthly·benchmark·숫자 배열 금지 | 시작 100의 월별 equity_curve 허용(비공개). 기존 공개 가드와 충돌하므로 예외를 임의 추가하지 않음 |
| 서술 | 문자열 열거형/정규식, 자유문구 금지 | name/description/limitations 자유문구. 공개 시 개인정보·역산 위험 별도 검토 필요 |
| 권리·OOS | rights_state/oos_state 명시 | 새 필드를 덧붙이지 않고 limitations 및 별도 비공개 evidence에 기록 |
| 결과 없음 | BLOCKED_ON_DATA 상태 표시 | `runs: []`. 가짜 0%·합성 성과로 대체하지 않음 |
| 출처 | manifest hash | 전체 source_commit; 의존성·manifest·hash는 별도 근거 |

사용자 초안 필드와 `schema_version`은 바꾸지 않았다. `lab_results.py`는 **연구 측 후보 검증기**이며 Main의 공통/공개 검증기를 대신하지 않는다. 스키마 통과는 사실 검증·PIT 인증·게시 허가가 아니다. Main과 계약을 고정한 뒤 변경은 버전을 올리고 양쪽에 먼저 알린다.

월별 `YYYY-MM`만으로 최초 투자일과 같은 달 말일을 모두 나타낼 수 없다. 이번 후보는 **첫 달=실제 초기 NAV 100**, 이후 달=마지막 확보 거래일, 마지막 달=실제 청산일의 부분 월로 기록하고 limitations에 명시한다. 일별 통계는 전체 일별 장부에서 계산한다. 이 날짜 표시 규칙을 Main에게 확인 요청하며 같은 달 안에 끝나는 비영(非零) 성과는 현재 형식으로 내보내지 않는다.

## 먼저 실행할 파일럿

`LAB_PILOT_REGISTER_20261031.json`에 **LAB-PILOT-ABT-LEDGER-2016-v1** 등록. 이미 실행된 장부 진단의 사후 등록임을 숨기지 않는다. 기존 조건을 변경하지 않고 최초 Lab 투영 전에 조건을 고정한다. OOS 사전등록을 주장하지 않는다.

- ABT 1회사, 2016-02-12~2017-02-21. 기존 고정 10회사 중 증권·분할·배당 근거가 명확해 선정한 표본이다. 성과 비교로 고른 표본이 아니다.
- N15 중 1칸만 보유, 14칸 현금, 기존 연간 달력의 S 종가 수량 고정→T 시가 체결. QGV 점수로 종목을 고르지 않는 **장부 파일럿**이다. BT-01/02/03 정의·모집단·전략을 축소 대체하지 않는다.
- 실제 Alpaca SIP raw OHLCV와 발행사 배당 근거. 배당락일 DERIVED, 예외 미검증, 실제 입금 미관측. `REAL + NOT_VALIDATED`, universe.point_in_time=false. 가정이 있다는 이유로 사실 검증을 승격하지 않는다.
- 수수료 10bp/방향, 모델 슬리피지 0bp, 현금 이자 0이라는 명시적 진단 조건. 이것을 실측 실행 비용·실제 무위험수익률로 해석하지 않는다.
- 비교는 무이자 명목 USD 현금. 시장 대비 우위 없음. Sharpe는 무위험금리 미확보로 null. 다른 지표도 계산 불가하면 null+사유.
- 기존 engine의 실제 일수 CAGR, 일별 표본 표준편차×√252, 일별 MDD를 재사용. 실제 입력을 사용하는 결정론적 비용·현금 가정은 합성 시장 데이터가 아니며, 합성 fixture는 시험 파일에만 있다.
- 변형 조건을 시험해 좋은 것만 남기지 않는다. 동일 체결의 gross/net 비용 대사는 추가 전략 최적화 실험으로 세지 않는다.

## 실행과 검증

새 API 요청·키·KIS 호출 없음. 기존 SIP 원본 SHA와 정규화 5필드를 대조하고, 기존 장부를 다시 실행해 기존 결과와 바이트 일치를 확인한 뒤 통계 함수로 집계한다. 원가·가격·개별 장부는 결과 후보 JSON에 넣지 않는다. 비공개 evidence에는 재현을 위해 보존한다.

```bash
python -m pytest -q implementation/experiments/bt-data-pilot-v06/test_lab_results.py
python implementation/experiments/bt-data-pilot-v06/export_lab_pilot.py \
  --private-root /workspace/private-bt-data-pilot-v06 \
  --reviewed-src /workspace/Investment-System1/implementation/src \
  --generated-at '<실제 최초 실행 시각: timezone 포함 ISO8601>'
```

재생 시 최초 generated_at을 그대로 사용한다. source_commit이 바뀌면 기존 파일을 덮어쓰지 않고 변경 충돌로 멈춘다. 실행 시점·명령·입력 manifest와 hash는 비공개 근거에 기록한다. 공개 로그에는 수익률·곡선·원본 hash를 출력하지 않는다. 합성 테스트는 스키마/수치/누락/정렬/민감 필드/일별 MDD 회귀를 검사하며 실자료 실행 성공을 대신하지 않는다.

완료 수치와 CI 상태는 이 PR 설명의 관측값으로 갱신한다. 미실행 항목: 정식 시장 모집단·상폐 정산, QGV 전략 성과, OOS, 실제 계좌 체결, 공개권 검증·공개 파일·웹 연결. #432의 KIS/SIP 시가·거래량 차이는 미해결로 유지한다.

## Main 요청 사항

1. 위 비공개 원본/임시 경로와 정식 #417 출력 위치를 확인하고 결정 문서에 고정해 주세요. 사용자 전달을 경유하지 않고 이 Draft PR에서 논의합니다.
2. `lab-backtest-v1`을 연구 원본 계약으로, `lab-results/1`을 별도 공개 투영으로 둘지 또는 공개 계약을 대체할지 합의해 주세요. 여기서는 두 계약을 자동 변환하거나 버전을 바꾸지 않았습니다.
3. 월별 시작 100·부분 월 표시, source_commit와 외부 엔진 의존성 근거 방식, NOT_VALIDATED 표시를 확인해 주세요.
4. 공개권을 확보한 뒤에만 Main 소유 공통 가드·워크플로·프론트엔드·게시 파일을 구현해 주세요. 실제 후보 파일을 공개 PR에 첨부하지 않습니다.
5. 사용자 최신 역할 변경·파일럿 우선 지시를 공통 결정/인계 문서에 반영해 주세요. Codex가 해당 파일을 수정하지 않았습니다.

병합·배포·운영 설정·자동매매·유료 계약 변경 없음. `BLOCKED_ON_DATA`, `OOS_NOT_ESTABLISHED`, `BOOK_EXACT_UNCONFIRMED`는 정식 연구에 계속 적용한다.
