# V v1 가격 인자 순수 계산

최신 사용자 대기열5번. [Scoring Standard v1](QGV_SCORING_STANDARD_v1.md)의 **STANDARD v1 · UNCALIBRATED**와 `qgv/raw_map.py`의 채택된 산식만 사용한다. 기존 raw_map·가중치·Q/G total·Frozen 계약은 바꾸지 않는다.

`qgv/price_value.py::calculate_v_price_factors(inputs, *, price)`는 가격을 호출 인자로 받고 RAM에서 계산한다. 가격을 반환 결과에 보관하지 않으며 파일/DB/로그·네트워크·공개 serializer/producer·Model/TSV/QGV에 연결하지 않는다. 결과 factor 값은 repr에서 제외하고 immutable mapping으로 제공한다.

## 기존 계산 경로

| 요소 | 기존 v1 경로 |
| --- | --- |
| Fundamental Value | 제공 DCF/가격의 상대 차이 → 기존 clip. DCF가 없거나0이면 양의 EPS·가격 P/E proxy 우선순위를 그대로 적용. 실제 DCF solver 추가 없음. |
| Margin of Safety | DCF의75% 또는 EPS의12배 conservative value/가격 → 기존 clip. Fundamental Value와 별도 값. |
| Reverse DCF | 제공 implied growth(0 포함)를 우선. 없으면 기존 P/E proxy, 제공 revenue/revenue_prev의 realized growth와 비교. 실제 reverse DCF solver 추가 없음. |
| Peer Relative | 제공 own_multiple와 peer_median_multiple의 기존 비교만 계산. price로 own_multiple 종류를 고르거나 peer 모집단/중앙값을 새로 만들지 않음. |
| Historical / Sector / Theme | 이미 제공된 각0~100 점수만 PASSTHROUGH. 새 가격에서 percentile/sector/theme 점수를 만드는 정의는 미확정이므로 제공값 부재 시 NOT_AVAILABLE. |

`basis_confirmed`는 호출자가 가격과 재무 입력의 **통화·주당/ADR·split 기준 일치**를 확인했다는 명시적 전제다. 기본false이며 근거가 없으면 가격 의존 요소는 `NOT_AVAILABLE`다. 이 플래그는 환산·분할 조정이나 실제 provider 검증을 수행하지 않는다.

결측·양의 유한 가격 부재·잘못된 수치·기준 미확인은 사유를 구분한다. 중간 산술 overflow를∞ clip으로 정상 점수로 바꾸지 않는다. 실제 계산값0은 결측 대체0과 구분한다. 승인된 proxy·clip을 새로 튜닝하지 않는다.

## 아직 정의/입력이 필요한 부분

- DCF의 현금흐름·할인율·terminal·통화/주당 입력 생성과 실제 solver.
- 실제 Reverse DCF solver(기존 명시적 implied growth/P/E proxy를 대체하지 않음).
- price에서 만들 own_multiple의 종류·분모·peer 비교 기준.
- Historical percentile의 모집단/기간·방향·가격 대응, Sector/Theme rubric와 새 가격 대응.
- 실제 미국/한국/일본 입력의 통화·주식 종류·ADR·split 결속 근거.

미확정 입력은 자동 보완하지 않는다. 이 목록은 새 산식 채택 제안이 아니며 제공된 기존 요소의 계산 성공을 v2/PIT/OOS/Calibration 완료로 해석하지 않는다. 합성 테스트로 기존 함수 참조값·우선순위·결측·0·비유한/overflow·불변/RAM 경계를 검증한다. Holdout·실제 가격은 사용하지 않는다.
