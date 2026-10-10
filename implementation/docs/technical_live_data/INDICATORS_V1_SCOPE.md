# 기술 지표 v1 — 기존 정의 확인과 착수 차단 항목

2026-10-10 UTC, canonical `83a2d0e3e5bf7ecf539a74a67f1a32c08480d0bb`. 사용자 요청은 #105의 일봉 입력 위에 [DESIGN.md](DESIGN.md) (#90)에 이미 정의된 지표만 구현하고 새 지표·임계값을 추가하지 않는 것이다. 합성 테스트만 사용하고 출력은 RAM 전용이며 공개 serializer를 연결하지 않는다.

**상태: WIP / 계산 범위 확인 대기.** 구현·테스트·기본 period·산식 선택은 아직 하지 않았다. 목록에 이름이 있는 지표와 계산 방법이 확정된 지표를 구분한다. 이번 PR은 사용자의 답을 받은 뒤 동일 PR에서 구현을 계속하기 위한 범위 확인 문서다. 문서만 있다는 이유로 자체 병합하지 않는다.

## 저장소에서 확인한 정의

| 대상 | 기존 근거 | 확인 상태 |
| --- | --- | --- |
| SMA·EMA·RSI·MACD·Bollinger Bands | DESIGN §5의 B01~B05 목록 | 지표 이름은 존재한다. §3.2·§10은 공식 산식·period·warm-up을 UNKNOWN/DEFERRED로 명시한다. EMA seed·RSI smoothing·MACD 초기화·Bollinger 분산/폭 등의 구현 방식을 관례로 확정하지 않는다. |
| ATR | DESIGN §5 B06, §3.2의 VMR ATR(14)% 표시 요구 | 공식 Technical 산식·period는 미확정이다. 다른 표시 요구의 14를 전체 Technical 기본값으로 적용하지 않는다. |
| Support/resistance·TSV·confidence·scenario | DESIGN §5 B08~B15, §10 | swing·기간·점수·가중치·confidence·확률 산식은 미확정 또는 구조 placeholder다. 이번 지표 구현에 추가하지 않는다. |
| 마지막 수익률 | [현행 engine](../../src/investment_system/technical/engine.py) `last = returns[-1]` | 코드에 연산이 정의돼 있다. #105는 같은 basis의 완료 합성 일봉에서 `p_cur / p_prev - 1`을 만들고 마지막 20개를 선택한다. |
| 마지막 5개 수익률의 합 | 현행 engine `sum(returns[-5:])` | 코드에 연산이 정의돼 있다. 복리 5일 수익률·연율 수익률로 바꾸지 않으며 짧은 입력을 충분한 공식 모델 window라고 주장하지 않는다. |
| 모집단형 표준편차 | 현행 engine `sqrt(sum((r - mean(returns))**2) / len(returns))` | 코드에 연산이 정의돼 있다. sample 표준편차·연율화·60일/1년·ATR·검증된 모델로 재해석하지 않는다. 기존 engine 분기 임계값은 변경하지 않는다. |

DESIGN §3.2: **‘공식 지표별 period·warm-up·Model Indicator Set·검증 표본량은 UNKNOWN/DEFERRED’**. §9: **‘누락 코드를 관례적 새 지표로 대체하지 않는다.’** [기존 결정 이력](../../../Technical%20Analysis%20%C2%B7%20Decision%20History%20v0.1.md)의 Indicator 구조도 최종 목록·수식 미확정이다.

## 필요한 범위 확인

대화에서 다음 두 범위 중 어느 기존 근거를 사용할지 확인을 요청했다. 답을 기간·산식 승인으로 추정하지 않는다.

1. **현재 engine에 이미 정의된 위 세 계산만 먼저 RAM용 결과로 제공**하고 SMA 등 미확정 지표는 후속으로 유지한다.
2. **SMA 등 지표의 기존 확정 산식·period·초기화/결측 처리 근거를 제공받아** 그 정의와 일치하는 계산만 구현한다.

1의 선택은 실제 구현 범위를 좁히는 사용자 결정이고, 2는 기존 정의의 복원 근거가 필요하다. 에이전트가 관례적 period·seed·평활화·배수·신호 임계·새 모델을 선택하지 않는다. 이 문서는 두 선택 중 하나를 확정하지 않는다.

## 답변 이후의 구현·검증 경계

- #105의 [daily_input.py](../../src/investment_system/technical/daily_input.py) 입력 검증을 통과한 합성 일봉만 계산한다. 관측 cutoff·최초 가용 시각·거래 session·완료 여부·basis/기업행사·식별·통화·결측 실패를 정상 지표로 바꾸지 않는다.
- 별도 순수 RAM 결과와 고정 미제공 사유를 사용하고 파일/DB/네트워크/로그·공개 serializer·producer registry·Pages/Worker 연결을 추가하지 않는다. 값이 있는 입력과 미제공을 구분하며 실제 공급자를 활성화하지 않는다.
- 산식이 확인된 항목의 손계산 가능한 합성 벡터, 정적/상승/하락·경계·정의된 warm-up/결측, 미래/미가용 bar 거부, raw/adjusted 분리, 입력 불변성을 검증한다. 현행 engine의 regime/zone·placeholder·QGV 원점수·버전이 바뀌지 않는 것을 확인한다.
- 기술적 지표 계산 통과는 모델 채택·실데이터·기기 실행·PIT/OOS/calibration 완료가 아니다. Holdout 사용·새 방법론·가중치·web_assets·Worker·workflow 변경을 하지 않는다.

코드 PR은 사용자의 별도 병합 승인 후에만 병합한다. 계산 범위 확인 전에는 WIP를 유지한다.
