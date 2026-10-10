# 현행 TechnicalEngine 세 계산 — RAM 참조 구현

2026-10-10 사용자 결정으로 #111의 범위를 **전체 returns 모집단형 표준편차·마지막 return·마지막 5개 합**으로 확정했다. #105의 [daily_input.py](../../src/investment_system/technical/daily_input.py) 검증을 재사용하며 기존 engine·임계값·snapshot·QGV 계약을 바꾸지 않는다. Research 표시 runtime·GSQ-015는 별도 #115이며 이 세 계산의 입력이 아니다. 최신 대기열에 따라 #111은 기기 구현 대조용 독립 Python 참조 도구·합성 JSON 벡터를 함께 제공한다.

## 구현 계약

[engine_calculations.py](../../src/investment_system/technical/engine_calculations.py)의 `calculate_daily_engine_inputs(series, as_of)`는 `DailyEngineCalculationsResult`를 반환한다.

- 입력 실패는 #105의 prepared reason/quality를 그대로 보존하고 `NOT_AVAILABLE`, `data=None`이다. real input은 기존 `REAL_INPUT_NOT_AUTHORIZED`를 유지한다.
- 정상 합성 입력은 `DEMO`이며 `EngineReturnCalculations`의 `population_stddev`, `last_return`, `last5_sum`, `return_count`를 RAM에 둔다. role은 `EXISTING_ENGINE_INPUTS`다.
- 전체 returns는 **엔진에 전달되는 전체 입력**이다. #105가 마지막 20개를 선택하므로 여기서 원 history 전체·별도 변동성 window로 바꾸지 않는다.
- 분산의 분모는 N이고 식과 연산 순서는 기존 engine과 같다. 마지막 5개 합은 복리 5일 수익률이 아니며 5개 미만이면 기존 engine처럼 제공된 부분을 더한다. 단일 return의 모집단 표준편차는 실제 계산값 0이다.
- 산술 overflow/비유한 결과는 `CALCULATION_ERROR`, `data=None`, prepared returns 제거로 처리한다. 값·raw exception을 진단에 넣지 않는다.
- `synthetic=True`, `pit_status=NOT_VERIFIED`, `model_status=PLACEHOLDER_UNVALIDATED`를 유지한다. 계산 완료가 실제 모델·추천·OOS/calibration 완료를 뜻하지 않는다.

## 경계와 검증

반환 dataclass는 frozen이고 가격 기반 값은 repr에서 제외한다. 공개 serializer·producer registry·파일/DB/로그/네트워크·기기/Worker 연결은 추가하지 않았다. 함수가 TechnicalEngine을 호출하거나 regime/zone·placeholder·QGV 원점수를 수정하지 않는다.

[test_technical_engine_calculations.py](../../tests/test_technical_engine_calculations.py)의 합성 검사 22개는 정확한 기존 산술/마지막20, 손계산 참조값, 1~5개의 짧은 returns, 입력 실패·real/basis/calendar/event 차단, 미래 bar 제외·가용 시각 차단, overflow 제거, 기존 engine 출력 불변성과 serializer/repr 경계를 확인한다. 기존 일봉 검사 40개와 함께 62개가 통과했다. 실제 일봉·공급자·개인 데이터·Holdout을 조회하지 않았다.

```bash
# cwd: implementation
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -p no:cacheprovider -q tests/test_technical_engine_calculations.py tests/test_technical_daily_input.py
```

최신 사용자 선택에 따라 26E 미변경 PR은 최종 실행 필수 체크 전부 성공·실패0일 때 자체 병합 가능하다. 현재 canonical의 앱 CSP 기대값 회귀가 남아 있어 #111은 전체 suite 성공으로 표시하지 않는다. SMA/EMA/RSI/MACD/Bollinger/ATR의 Research 표시 구현·기본값은 별도 PR에 한정하고 Model/TSV/QGV에 연결하지 않는다.
