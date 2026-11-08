# 보관 근거 추가 검토 — held-sec-book-correspondence/0.3.0

`extend_held_classification(snapshot, evidence_by_code, rule_version=...,
business_reviews=...)`를 확장한다. 인자를 생략한 기존 /0.2.0과 원래 /0.1.0은
보존한다. 공통 사전·공식 모델·관문·strict/20·기술 분위/10은 변경하지 않는다.

이번 규칙은 연구 대응이며 공식 원천 분류나 신원 검증이 아니다. SEC SIC와 설명,
발행사, 원문/보관 묶음 해시, 입수 시각을 먼저 검사한다. 명시적으로 검토한
정확 SIC 활동만 추가한다. 금융 활동은 확인돼도 수익·자본 구조가 모호하면
섹터만 확인하고 회계모형은 null이다. 기존 회계모형 충돌도 확인된 섹터를 지우지 않는다.

기업별 검토는 별도 `business_reviews` 입력이다. 회사 코드·발행사·평가일·submissions
해시, 해시 고정된 보관 XBRL 문서, 정확한 태그/문맥/텍스트 해시/대상 기간을
각 주장에 연결한다. sector/accounting/industry별 값·판정 이유·인용 인덱스를
명시하며 단어 검색이나 SIC 대분류로 자동 선정하지 않는다. 로컬 파일 경로는
검토 규칙 식별 해시에서 제외한다. 소스 프로필이 없으면 GENERAL로 채우지 않는다.
REIT의 물적 부동산 보유·임대형 회계모형 근거와 상위 섹터 배치 정책은 별개다.

`component_mappings`와 `review_sources`는 이 연구 어댑터의 내부 입력이다.
Main이 읽는 `common-classification/1`, `common-classification-view/1`,
`common-classification-qgv-links/1`은 그대로다. 예를 들어 sector=CONFIRMED FINANCIALS,
accounting=UNKNOWN/null, industry=UNKNOWN/null이면 확인된 섹터를 표시할 수 있지만
QGV 비교집단 완결로 읽어서는 안 된다. sector=UNKNOWN/null,
accounting=CONFIRMED EQUITY_REIT도 가능한 독립 상태다. 새 공개 기업 자료는 없다.

`append_review`는 변경된 코드 행만 현재 기록을 supersede하는 새 기록으로 추가한다.
이전 원문·기록·기존 조회 cutoff는 보존한다. 같은 본문에 보관 위치 근거가 추가돼도
기존 source를 덮지 않고 새 metadata ID로 남긴다. 적용은 해당 평가일 한정이며
현재 검토 시각을 과거 원문 발표시각으로 대체하지 않는다.

재실행은 기존 CLI `implementation/tools/common_classification.py --job JOB --output DIR`다.
JOB에는 보관 `snapshot`, `retained_preview`, `saved_config`, 새 `classification_store`의
경로·해시를 준다. 새 `comparison_id`는 분류만 변경한 비교를 식별한다. 원래 모집단,
재무 관측, 관문, 대표 발행사 근거, 저장 설정은 유지하며 가격을 만들지 않는다.
동일 분류/회계모형의 기존 기업도 peer 유효 N 변화 때문에 상대점수가 달라질 수 있다.
원지표 입력 확보 수와 새 회계모형 적용 후 `raw_valid` 수는 구별한다. NOT_APPLICABLE
증가는 원재무 자료 소실이나 새 수집 실패가 아니다.

시험: `PYTHONPATH=implementation/src:implementation python -m pytest -q
implementation/tests/research/test_classification_held_review.py`.
관련 기록·QGV 투영·CLI·기존 분류 회귀도 실행한다. 기존 CI `pytest tests`가
새 시험을 자동 발견하므로 CI 목록·의존성·워크플로 변경은 필요 없다.

실제 회사별 검토/분류/점수와 원문은 승인된 비공개 인계에만 보존한다. 행 요약
JSON/CSV에는 company_id(원래 코드 행), issuer_id, 전후 세 독립 상태, 적용일,
현재 검토시각, 원문 위치/해시/기간, 미확인 이유를 포함한다. 압축 묶음 밖에도 같은
요약을 보존한다. 계약 인수·오프라인 계산·인증된 화면 전달·배포는 각각 구분한다.
