# DCF v1·역DCF — RAM 순수 참조 / 기본 파라미터 확인 대기

사용자 승인 구조: 명시5년+영구성장 Gordon의2단계 DCF, 현재가에 맞는 명시기간 내재 성장률은 이분법. `qgv/dcf.py`는 가격을 인자로만 받으며 반환 repr에서 계산 수치도 숨긴다. 저장·공개 serializer·자동 V 요소 연결·QGV/Model 채택은 없다. `dcf_config_v1.json`은 버전 있는 확인 대기 설정이며 금융 파라미터는null/confirmed=false다. 사용자 확인 전 결과는 NOT_AVAILABLE다.

## 정확한 함수·basis

`two_stage_dcf(cashflow_per_share, growth_rate, parameters, cashflow_currency)`와 `reverse_dcf(cashflow_per_share, price, parameters, cashflow_currency, price_currency)`는 keyword-only다. 공통 cashflow는 기간0의 **주당 FCFE**, 할인율은 동일 통화 cost of equity라는 caller 확인이 필요하다. FCFF/WACC를 주당 주가와 직접 비교하지 않고 net debt/ADR/split/통화 변환도 하지 않는다. 표준 [Damodaran FCFE valuation 장](https://pages.stern.nyu.edu/~adamodar/pdfiles/valn2ed/ch14.pdf)의 equity cash flow/discount-rate 구분에 따른다. 원본 데이터로 FCFE를 산출하는 별도 정의는 아직 미확정이다.

기호 F0=주당 cashflow, h=명시기간 성장률, r=할인율, g=영구성장률, n=명시기간:

- t=1..n: Ft=F0×(1+h)^t, PVt=Ft/(1+r)^t.
- terminal PV=Fn×(1+g)/(r−g)/(1+r)^n.
- value_per_share=PVt 합+terminal PV. 계산 순서를 보존하며 금융 값을 임의 clip하지 않는다.
- 역DCF는 위 동일 함수가 price와 같아지는 h를 제공 bracket 안에서 이분법으로 찾는다. 양의FCFE/가격·r>g·동일 통화/주당 basis·bracket을 요구하며 자동 bracket 확장/금융 기본값 추정은 없다.

실제 cashflow0이면 순방향0은 가능하지만 역DCF는 NON_POSITIVE_CASHFLOW다. 결측 cashflow는0이 아니다. 순방향 음의 cashflow도 수학적으로 계산할 수 있지만 valuation 적합성 승인이나 V 점수로 취급하지 않는다. currency는USD/KRW/JPY 중 caller가 확인한 값이며 없는 price_currency를 현지통화로 추정하지 않는다.

고정 실패 코드: PARAMETER_APPROVAL_PENDING, PARAMETER_INVALID, GORDON_RATE_ORDER, CASHFLOW_BASIS_UNCONFIRMED, SHARE_BASIS_UNCONFIRMED, CURRENCY_BASIS_UNCONFIRMED, INPUT_INVALID, SOLVER_INVALID, ROOT_NOT_BRACKETED, ROOT_NOT_CONVERGED, NUMERIC_OVERFLOW.

## 기본값 제안 — 사용자 결정 전 비활성

| 파라미터 | 제안 | 근거·한계 |
| --- | --- | --- |
| 명시기간 |5년| 사용자 구조 승인값. 설정으로 변경 가능하되 투자 방법의 자동 채택 아님. |
| 할인율 |10%| USD 주당FCFE 연구 예시용 둥근 cost-of-equity 가정. 실제 기업/시장 자본비용을 관측한 값이 아니며 공통10%의 적합성은 사용자 확인이 필요. 위험프리미엄·기업 beta를 새로 창작하지 않음. |
| 영구성장률 |2%| [Fed의 장기 물가목표](https://www.federalreserve.gov/faqs/economy_14400.htm)를 보수적 USD 장기 nominal 가정의 참고로 제안. 물가목표는 기업 FCFE 성장의 증거가 아니며 KRW/JPY나 모든 회사에 자동 적용하지 않음. r보다 반드시 낮아야 함. |
| cashflow/할인율 basis | FCFE_PER_SHARE/COST_OF_EQUITY | 위 표준 equity DCF의 동일 basis. 원천 FCFE 산식·주식 종류·희석/ADR 처리는 미확정. |
| 역DCF bracket |−50%~+100%| 합성 테스트 범위의 초기 탐색 구간 제안일 뿐 경제적 허용 성장 범위/새 지표 임계값이 아님. 구간 밖이면NA이며 자동 확대하지 않음. |
| solver 상대 가격오차/반복 |1e−10/200| 금융 점수 임계값이 아닌 계산 정밀도·종료 조건. JS 대조는 동일 설정을 사용. |

파일의 proposal은 검토 대상 메타데이터이며 실제 parameters로 복사하거나 confirmed를 켜지 않는다. 사용자 설정은 별도 기기 복사본으로 공급한다. 공식 기본 금융 파라미터 채택은 이후 사용자 결정이다. engineering 상한(n100, iterations10000)은 계산 자원 경계이며 공식 금융 horizon은5년이다.

## 기존 V 연결의 미확정 항목

#125의 `price_value.calculate_v_price_factors`는 기존 v1 scoring map을 유지한다. DCF 계산이 추가됐다고 자동으로 FCFE/FCFF를 고르거나 score에 연결하지 않는다. FCF→FCFE·주당 분모·PER/EVEBIT의 업종/역사 비교·정규화5년 이익→V 점수·테마 할인·가격 취득basis는 미확정이다. 이 결과를 V 인자로 사용하는 것은 caller의 동일 basis 확인 이후이며 공개 산출물은 계속 금지다.

## 검증

합성 입력으로 constant perpetuity1/r, 독립 Decimal 참조값, 알려진 성장률 재구성·endpoint·bracket 실패·null/0·통화/주당 basis·overflow·비수렴·불변 입력을 확인한다. 실제 종목/가격/검증 기간·Holdout을 사용하지 않는다. JS 이식 벡터는 이 함수의 동일 인자와 Python 결과를 포함한다.
