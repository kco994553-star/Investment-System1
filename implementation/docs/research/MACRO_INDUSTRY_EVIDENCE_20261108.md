# 공통 산업에서 매크로 근거 조회

오너 2026-11-08 긴 대기열 3절과 공통 분류 명칭 보완을 구현한다.
기존 `common_classification.technical_macro.macro_projection`과 근거 시각 판독기를 재사용한다.
새 수집기·국면·순환매 확률·QGV 가중치·산업 관측 합계를 만들지 않는다.

## 한 사전, 기존 분류 기록 유지

`common_classification.catalog.current_taxonomy()`가 현행 **투자시스템 공통 10섹터** 정의를 반환한다.
`common-classification-definition/1`, 정의 버전 `investment-system-common-10-sector/1`.
기존 sector_id를 그대로 사용하며 `TELECOMMUNICATIONS`의 표시 이름은 통신서비스다.
ID·한국어명·정의·포함/제외·버전·근거는 catalog 한 곳에 있다. Main은 이 출력으로 표시한다.
GICS11·SIC·ETF와 동일한 체계가 아니며, 회계모형·태그·ETF는 별도 차원이다.
REIT/관리의료/통신·미디어의 승인된 시스템 정책은 개별 기업 자동 판정이 아니다.

`common-industry-dictionary/1`, `/2`는 과거 결과 복원용 직렬화와 해시를 보존한다.
현재 정의 출력은 기존 dictionary/map /1+/1, /2+/2를 새 기록 버전으로 자동 변환하지 않는다.
분류·비교집단·산식·설정 해시·점수는 그대로다. 명칭 변경을 재분류 증가로 집계하지 않는다.

## 입력과 시간

`macro-industry-evidence/1`: classification_context는 평가일·분류 해시·dictionary/mapping 버전을 묶는다.
`evidence[]`: evidence_id, ref, SHA-256, 문서 내 locator, published_at, available_at, acquired_at, 검증상태;
해당 근거가 확인하는 source_definition(system/code/name/version)과 series_ids도 명시한다.
`mappings[]`: mapping_id/revision_id/supersedes, source, relation(EXACT/PARTIAL/MULTIPLE/UNKNOWN),
targets(sector_id/industry_id/scope_relation), includes/excludes, [valid_from, valid_to),
reviewed_at/available_at/acquired_at, evidence_refs, series_ids, unknown_reasons, allocation_weights:null.
EXACT는 한 대상의 정확 대응, PARTIAL은 한 대상과 부분 관계, MULTIPLE은 명시된 복수 관계다.
UNKNOWN은 근거 부족 사유와 빈 targets를 보존한다. 비중 없는 복수 대응은 분배·합산하지 않는다.
확인된 원천 정의의 버전과 계열 목록이 맞지 않거나 근거 참조가 없으면 거부한다.
같은 코드 문자열이어도 서로 다른 분류체계는 연결하지 않는다. 중복 활성 대응은 기존 함수가 거부한다.

조회는 `view.valuation_date`의 분류/대응 적용 기간과 `view.knowledge_as_of`의 가용 근거를 함께 검사한다.
날짜만 있는 같은 날 가용시각은 미확인이다. 기록·원문·취득·계열 가용시각을 대체하지 않는다.
종료일은 exclusive다. 미래 근거/미래 cache/기간 밖 대응은 UNKNOWN이며 미래 관측값은 null이다.
`macro-current-query/1`의 원래 query_at/cache_asof, 관측 기간·단위·수정버전·최초 확보·마지막 성공·stale를 보존한다.
오늘 조회한 것처럼 최신성 시각을 바꾸지 않는다. 공식 발표/역사 PIT가 미확인이면 그대로다.

## 출력·Main 연결

`company-industry-macro-query/1`: companies[]는 기존 company_id·issuer_id·classification_record_id로 연결한다.
related_series_ids는 산업 대응, query_usable_series_ids는 원래 cache 조회 가능성을 별도로 나타낸다.
`observations`는 series_id당 한 번만 담고, 여러 회사/산업에서는 참조한다. aggregate_value/weights/probabilities/returns는 null.
분류만 확인되고 산업이 미확인인 회사도 원래 members에 유지한다.
Main은 기업 상세→공통 산업→근거 및 계열 조회를 연결한다. 미확인 대응이 기존 전체 매크로 조회를 차단하지 않는다.
개별 정책 적용·투자 신호·공식 점수에 사용할 수 있는 대응이라는 뜻은 아니다.

공개 합성 fixture: `implementation/tests/fixtures/macro_industry_evidence/`.
view/mappings/cache→expected와 7가지 표시·거부 사례, 파일별 SHA/bytes manifest를 제공한다.
복수 산업2회사/동일 계열1개/값0, 부분 대응1회사, 미래/날짜 정밀도/버전 오류/미확인 사례를 포함한다.

## 실행과 검증

```
PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_macro_industry_evidence.py
PYTHONPATH=implementation/src python implementation/tools/macro_industry_evidence.py --job <private-job.json> --output <new-private-dir>
```

변경 시험 18통과. 원래 분류와 cache를 변경하지 않음, 출처 버전/계열·기간·부모 관계·중복·미래 정보·null,
구사전 해시 재현·새 표시 ID 유지·CLI 핀 검증/덮어쓰기 거부를 검증했다.
기존 전체 기술·QGV 성공 시험은 반복하지 않았다.

보관 자료 실행: 2026-11-04 Universe504 분류와 기존 2026-11-05 매크로 query를 새 조회 계약으로 연결했다.
기존 inventory의 3계열(CES3000000007, CES6056132001, IP.B50001.S)은 원천 산업 정의·버전·포괄범위·적용 기간 부족.
새 원문 검토/수집 없이 이 결손을 UNKNOWN으로 보존했다. 실제 활성 대응0, 기업 연결0, 새로운 수치 계산0.
원래 현재조회 유효11계열을 이 산업 연결0과 혼동하지 않는다. 이번에 11계열을 다시 계산하지 않았다.
해소에 필요한 최소 입력은 해당 3계열의 공식 series→industry 정의/버전/범위/유효기간 문서다.
제조업 전체·임시고용·총산업생산을 기존 7개 하위 산업에 이름만으로 배정하지 않는다.
새 공식 문서 취득/API 호환/브라우저/정기 실행/배포/성과 검증은 범위 밖이다.

소유: catalog 현재 정의, research macro_evidence, offline CLI, 연구시험/fixture/본 계약은 Codex.
Main의 화면·인증·워크플로·공용 가드/CI 목록/결정 기록은 변경하지 않는다.
Main 필요 변경: 사전 표시 이름을 current_taxonomy로 읽고 이 조회 계약을 기존 매크로 현재조회 보조 계약 옆에 연결.
필요 시 공식 명세의 과거 “책 10섹터” 표기는 Main이 현행 명칭/시스템 적용 정책과 구분한다.
