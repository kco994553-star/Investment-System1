# 보유 확장 카탈로그의 공통 분류·Q/G 연결

`held-expanded-issuer-adapter/1`은 #482/#500의 해시 고정 보유 입력을
공통 분류와 섹터 QGV 엔진에 연결한다. 공식 운영504·전체시장 선정 모집단을
교체하지 않는다. 현재 명부의 적격성 관문이나 과거 C2 설정도 변경하지 않는다.

분석 단위는 **관측 카탈로그의 고유 발행사**다. `ISSUER:<기존 CIK>`는
연구 행 ID이며 고정 증권 ID가 아니다. 원래 관측 티커 행은
`catalog-crosswalk.json`에 모두 남긴다. 같은 발행사의 종류주 중 첫 행을
대표 증권으로 선택하지 않는다. 재무 미확보 발행사도 분모에 남는다.
기존 원시 재무 산출 표본은 별도 하위 집합이며 이 집합의 확보율은 전체시장
커버리지가 아니다. 전체시장 분모·커버리지는 null이다.

입력 job `held-expanded-classification-job/1`:
- `held`, `archive`: 기존 정규화 캐시와 원본 ZIP의 path/SHA256. 원문 멤버와
  receipt의 URL·취득 시각·바이트·해시·성공 상태를 대조한다. 신규 요청은 없다.
- `upstream_snapshot`, `upstream_store`: 기존 운영 분류의 근거·상태·기간과
  재무 source_profile을 재사용한다. 같은 발행사/평가일, 일치하는 SIC·회계
  프로필, 평가시각까지 확보된 근거만 재사용한다. 충돌은 명시적으로 남긴다.
- `config`: 기존 sector-qgv-default/0.1.0 저장 설정. strict·최소20 유지.
- `as_of`, `recorded_at`: 재무/근거 사용 cutoff와 이번 검토 시각을 분리한다.
- `retained_transform` (선택): 앞선 이 어댑터의 manifest, snapshot,
  source_evidence path/SHA256. 같은 원문·캐시·평가일의 원지표를 재사용하여
  분류/비교집단만 바뀌었을 때 재무 계산을 반복하지 않는다.

기존 calc23.1 원시 지표는 다시 계산하지 않는다. 새 섹터 요소에 필요한
기간 조합은 `sector_qgv_held.held_observations`를 운영504와 공유하며 기존
SEC facts 엔진과 calculate_factor를 호출한다. 기존 연간 비율을 TTM으로
바꾸거나 EPS를 재구성하지 않는다. 해당 snapshot의 원지표가 새로 변환된
수와 이후 재사용 수를 구분한다.

SIC /0.1 → 명시적 추가 대응 /0.2 → 보관 근거 검토 /0.3 경로를 재사용한다.
운영504에서 이미 검토한 같은 발행사를 다시 조사하지 않는다. 상위 섹터,
회계모형, 산업은 독립 상태이며 source SIC/적용일/가용시각/원문/상위 기록
ID를 보존한다. 현재 분류를 과거로 소급하지 않는다. 하나라도 충돌하면
기존 판정을 무조건 복사하지 않는다.

실행:
```
PYTHONPATH=implementation/src python implementation/tools/expanded_held_classification.py \
  --job PRIVATE_JOB.json --output PRIVATE_NEW_DIRECTORY
```

출력은 기존 common-classification/1, view/1, sector-qgv-input/1,
preview/1을 사용한다. `summary.json`은 카탈로그 전체와 보유 재무 하위표본의
원래 분모, 분류/회계/산업, 원지표, 요소 점수, Q/G/V/동시/총점을 구분한다.
미분류·미확보도 `classification-summary.csv`에 남는다. 이 CSV와 JSON view는
압축 없이 읽을 수 있다. 모든 실자료 출력은 checkout 밖에 저장하며 정상
로그에는 회사별 값이 없다.

Main은 `analysis_row_id`와 `issuer_id`를 구분하고 원래 티커 관측 행과 연결한다.
이 ID를 기술 보드의 검증된 security_id나 대표 증권에 쓰지 않는다. 이 표본의
요소 백분위는 이 **발행사 표본 전체**로 다시 계산한다. 기존504 점수를 붙여
넣거나 두 모집단의 순위를 섞지 않는다. 관문용 공식 Q 입력은 연결되지 않았으며
가격/V/최종 총점도 별도 미산출 상태다. 태그·하위 산업 개수는 점수에 영향이 없다.

정상/복수코드/미확보/같은 날 근거 재사용/다른 날짜/SIC·회계 충돌/미래 근거/
원본 및 receipt 해시 불일치/분모 보존/원지표 재사용의 공개 합성 시험은
`tests/research/test_expanded_held_classification.py`에 있다. 기존 `pytest tests`
자동 수집을 사용하고 CI 목록·공용 의존성·워크플로 변경은 요청하지 않는다.
실제 브라우저·인증된 자료 전달·정기 실행·배포는 Main의 별도 단계다.

## 2026-11-08 추가 연결 (기존 결과와 구분)

- job의 선택 필드 `classification_rule_version=held-sec-book-correspondence/0.4.0`은
  27개 명확한 SEC 주 활동 대응을 추가한다. 생략하면 기존 /0.3 결과를 재현한다.
  **기업별 보류 판정은 새로운 일반 SIC 규칙으로 덮지 않는다.** `project_qgv`는
  현재 분류 기록 ID·구성요소별 결손 사유를 전달한다. 예전 입력의 미검토 사유가
  남아 완료된 기업별 예외를 다시 일반 대응하는 결함을 수정했다.
- `official_gate_source: {path,sha256}`는 같은 평가일의 보존 `sec-qgv2.json`을
  선택적으로 연결한다. 회사 원문 해시·원재무 지표·회계기간·SIC·회계모형·통화·
  calc 버전이 모두 같고, 기존 공식 Q 재생 근거가 맞는 발행사만 연결한다.
  유일한 원지표 비교 제외 필드는 이미 계산된 **G** 비교집단 백분위
  `revenue_volatility_5y_rank_pct`다. 복수 코드의 관문이 다르면 거부한다.
- 관문은 **기존 Universe504 공식 Q 재생값**이다. 확장 집단 Q나 공식 게시값으로
  바꾸어 표시하지 않는다. `official-gate-linkage.json`은 원래 모집단·버전·코드·
  원문 해시·연결 실패 사유를 보존한다. 새 섹터 Q를 관문에 넣지 않는다.
- `input-gaps.json`은 분류/회계/하위산업, Q/G 기간별 원지표 상태,
  평가일 증권·주식 기준·가격·선택 요소에 필요한 EV 구성, 공식 Q 관문을 분리한다.
  NOT_CONNECTED는 어댑터 미연결이며 원자료가 세상에 없다는 뜻이 아니다.
  최소 표본 부족은 입력 결손과 별도다.

같은 2026-11-04·원래 분모·원재무 입력에서 운영504 섹터 416→417,
회계 407→414, Q230→231·G317→318. 확장 보유1057발행사는
섹터815→852·회계792→828·하위산업185→188, Q470→493·G633→661.
확장 관문 연결은0→243이며 V·동시·총점과 검증된 증권 ID는 계속0이다.
원재무 지표 재계산은0건; 상대점수 변화는 비교집단 변경 효과이며 성과 개선이 아니다.
원래 미검토40코드는 섹터확정18·미확정22로 유지된다. 확장 미검토85는
36개 연결 뒤49개 남는다. REIT 상위 배치·미디어 경계·관리의료 정책은 바꾸지 않았다.

이번 시험: `test_classification_held_review.py`, `test_expanded_held_classification.py`,
`test_common_classification_qgv.py`, `test_common_classification_cli.py`의 변경 경로.
기존 CI의 `pytest tests` 자동 발견 범위여서 CI 목록 추가는 필요 없다.
Main의 #519 계약 인수·브라우저 실행·배포는 이번 자료 계산과 별개이며 재시험하지 않았다.

비공개 증분 보존 위치: `investment-system1-raw`,
`handoff/input-recovery-20261103`,
`handoffs/classification-expansion-followup-20261108`.
회사별 JSON/CSV·manifest·재개 명령은 그 위치를 사용한다.
