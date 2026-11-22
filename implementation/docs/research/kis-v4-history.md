# KIS 자기과거 가치 입력 — 명시적 연구 opt-in

`private_kis_reference.official_reference(..., kis_v4_history=True)`는 보관 KIS RAW 일봉을
기존 calc23.1의 자기과거 가치 역할에 연결한다. 기본값은 `False`이며 기존 호출의 결과·바이트는
유지된다. 수집·게시·워크플로·공식 V 경로는 바꾸지 않는다.

경로는 기존 `kis_stock_journal.generation` 또는 `kis_rebuild.rebuild`가 부르는
`official_reference → qgv_official.prepare/price_status/engine_quotes/score/projection`이다.
이 PR은 그 런타임 호출부에 자동 활성화를 추가하지 않는다. 활성화 승인 뒤 담당자가
보관 재무·종목 연결·가격 contract pin을 유지한 호출에만 opt-in을 연결하고 새 배치를 검증한다.
동일 과거 배치 재현은 이전 입력·코드·기본값을 유지한다.

## 입력과 계산 경계

- 보관 가격 contract와 독립 `expected_contract_hash`, 기존 공급처 연결의 `symb/excd`를 검사한다.
- 원천은 KIS `MODP=0/GUBN=0`, `OWNER_PRIVATE_ONLY`이며 `raw_bars`만 읽는다.
  분할조정 `bars`를 다시 조정하거나 공급처를 IEX ROUND 체결로 표시하지 않는다.
- 기존 재무 payload의 `ebit_per_share_history`와 양수 `share_basis_factor`만 읽는다.
  새 재무 anchor나 factor=1을 만들지 않는다. 가격은 기존 V-PRICE-BASIS와 같이 RAW/F_k로 놓는다.
- 현재/미래월은 제외하고 완료된 과거월의 정확한 마지막 NYSE 거래일 봉을 요구한다.
  거래일은 기존 연구 달력으로 판정한다. 달력 범위 밖·정확한 봉 미보유·held 구간은 미산출이다.
- 같은 calendar month의 두 재무 anchor가 서로 다른 F_k이거나 한쪽이 미확인이면 그 달을
  `CONFLICTING_FISCAL_MONTH_BASIS`로 보류한다. 한 anchor의 가격 기준을 다른 anchor에 빌려주지 않는다.
- 원천 취득이 계산 마감을 넘으면 거부한다. 원문 취득·계산·가격 관측일은 별도다.
  현재 얻은 과거 봉을 역사 당시 시스템 보유 자료로 표시하지 않는다.

이 변경은 V4 월말 입력에 한정된다. 현재 가격 수용, Q/G, 다른 네 V 역할, 표본·관문·비중·
순환형 정상화 정책은 그대로다. 순환형의 `NORMALIZED_HISTORY_NOT_AVAILABLE`는 새 가격만으로
해소되지 않는다. V4 하나의 산출은 V축·세 축·15역할·총점 완료와 각각 구분한다.

## 출력과 보존

반환 packet의 선택적 `v4_history`는 policy/provider/평가일/집계와 diagnostics hash만 가진다.
회사별 상세·가격은 넣지 않는다. `v4_audit_sink`에 명시적 비공개 저장 함수를 넘기면 전체 감사
자료를 별도 보존할 수 있다. sink가 실패하면 호출이 실패하므로 이전 정상 배치를 유지해야 한다.
파일당 기존 1,800,000바이트·인증·공개 경계를 유지한다. 부분 총점 마스킹도 그대로다.

등급은 `UNVERIFIED_REFERENCE`, 공식 게시 대체는 false다. 고정 증권 신원·기업행사 검증 승격,
브라우저·인증 전달·운영 배포를 이 함수의 계산 성공으로 대신하지 않는다.

합성 검증:
`PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_kis_v4_history.py implementation/tests/research/test_kis_reference.py`

실제 보관 입력·수치·회사별 순위 이동은 승인 비공개 연구 위치에만 남긴다. 공개 저장소에는
가공한 실제 가격이나 실회사 결과를 합성 fixture로 넣지 않는다.

### 모든 행의 V 완결도 표시

모집단 행과 TARGET 행 모두 기존 `rows[key].axes.V.state`를 읽고 활성 배치의
`v4_history.axis_state_labels`로 표시한다. `READY`는 전체 산출(유효 비중 100%),
`PARTIAL`은 부분 산출(점수가 있고 유효 비중 50% 이상 100% 미만),
`NOT_AVAILABLE`은 미산출이다. 점수 0도 산출된 값이다. 비중은
`weight_available`(0~1), 사용한 요소 수는 `factors_available`(0~5)다.
둘 다 정규화 전에 사용 가능했던 요소를 센다. 차트의 표시 등급과 V 완결도는 별도다.
옛 배치에도 같은 행 상태가 들어 있다. 표시는 기존 점수·총점·분모를 그대로 사용한다.
