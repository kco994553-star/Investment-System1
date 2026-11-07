# 공통 분류 인계 — common-classification/1

상태: 연구 구현 / Main 계약 제안. 공개 게시·배포·모든 기업 분류 확정 승인이 아니다.
근거: 2026-11-07 오너 공통 분류 지시. #505의 기존 분류 및 QGV, #515 기술 결합,
#514 저장 설정을 재사용한다. UI·가드·워크플로·CI 목록은 변경하지 않는다.

## 사전과 독립 필드

`catalog.dictionary()`가 유일한 새 상위 연결 사전이다. 기존 `book-sector-map/1`의
10 sector ID와 기존 `sic_industry_groups/v0`의 명시적 하위 ID 7개를 재사용한다.
새 `common-industry-dictionary/1`은 그 하위 산업의 상위 섹터 대응만 명시한다.
원천 SIC 범위나 QGV 분류기를 복제하지 않는다. 광범위 SIC 그룹은 그대로 별도 원천
그룹이며 10섹터와 동의어가 아니다. 사전 변경은 새 버전과 과거 결과를 보존한다.

| 필드 | 의미 |
|---|---|
| company_id | 원래 모집단의 기존 기업 코드. Universe504에서는 증권 코드 행이다. |
| issuer_id | 기존 발행사 ID/CIK. 고정 증권 ID가 아니다. |
| source_sic | SEC_SIC 체계·원코드·기존 원문 근거. 다른 원천 코드를 동일시하지 않는다. |
| sector / industry / accounting | 각각 `id`, `status`, `reasons`, `evidence_refs`; 상태는 CONFIRMED/UNKNOWN/CONFLICT. |
| tags | 사업 노출·테마·린치·정책 등 설명용. 원래 모집단에 행을 추가하지 않는다. |
| benchmark | 기존 D22 SIC→ETF 비교계열. 공통 섹터·자체 섹터 수익률이 아니다. |

주 섹터는 발행사 하나당 하나다. 한 발행사의 코드들이 서로 다른 확정 주 섹터를
주장하면 모두 CONFLICT다. 회계모형 충돌은 독립 판정한다. 하위 산업이 없어도
섹터·회계모형이 확인되면 기존 QGV 경로를 사용할 수 있다. 사업 근거만으로도 명시적
사전 산업에 연결할 수 있으나 SIC 부재를 임의 코드로 채우지 않는다.

REIT 6798의 상위 배치·모형은 기존 미확인을 유지한다. XLRE 벤치마크 존재는 이를
확정하지 않는다. 책 통신 4812/4813과 현대 XLC/Communication Services의 미디어
범위는 별개다. 복합 사업의 주 사업 미확인은 태그 개수나 SIC 대분류로 결정하지 않는다.

## 기록·시점

`common-classification/1`: `members`, 원문 `sources`, 변경을 보존하는 `records`,
`universe_id/version`, `dictionary_version`, `mapping_version`, `data_kind`.
각 기록은 `record_id`, `company_id`, `issuer_id`, `rule_version`, `basis`, `source_refs`,
`recorded_at`, `supersedes`, `applicability`를 갖는다. 이전 기록은 수정·삭제하지 않는다.
source에는 URL, 위치, SHA-256, `published_at` 또는 `published_date`, `acquired_at`이 있다.
발표일만 있으면 시각은 null이다. 기존 보관 자료의 최초 공개시각 미보존은 별도 사유다.

`resolve(store, valuation_date=..., knowledge_as_of=...)`의 결과는
`common-classification-view/1`이다. 분류 적용일과 시스템 가용시각을 모두 검사한다.
INTERVAL은 `[valid_from, valid_to)`이며 시작일 미상은 해당 날짜 확정에 쓰지 않는다.
EVALUATION_ONLY는 지정 평가일만 확인한 연구 대응이고 실제 시작/종료일은 null이다.
같은 날짜에 시각이 없는 가용 근거는 당일 시각 조회에서 미확인이다(날짜 비교 기준 UTC).
미래 기록·근거는 과거 판단에 쓰지 않으며 늦은 정정은 이전 조회 결과를 덮어쓰지 않는다.

보관 QGV 매핑의 현재 인계는 **현재 검토한 과거 평가일 입력**이다. 원래 검토시각은
미확인, 새 `recorded_at`은 이번 연결 시각이다. 금융 입력 `as_of`를 바꾸지 않는다.
이 구조 연결이나 원문 입수시각을 역사 PIT 완성으로 표시하지 않는다.

`classification_hash`는 사전·선택된 원문·분류·기준일·모집단·조회 cutoff를 포함한다.
미래 근거 추가는 당시 선택되지 않은 정보이므로 과거 계산 hash를 바꾸지 않는다.
전체 이력은 별도 `history_hash`로 검증한다.
태그는 `display_hash`에만 반영한다. 증권/가격 입력과 조정 기준은 기술 계약의 별도
입력으로 유지한다. QGV 입력은 공통 해시와 엔진/설정/입력/모집단 버전을 함께 캐시한다.

## 세 기능 연결

1. `project_qgv(snapshot, view)` → 기존 `sector-qgv-input/1` → `preview_qgv`.
   공통 sector/accounting만 투영한다. 관측값·가격·주식 기준·기존 공식 관문·대표 발행사
   근거·기준일·저장 설정은 보존한다. 기존 엔진용 하루 적용 범위는 EVALUATION_ONLY
   변환임을 명시한다. 원지표는 분류 결손과 독립이며 새 모형 strict/최소20을 유지한다.
   구 공식 모델·공격/균형/수비 설정을 새 기본값으로 이관하거나 저장 결과를 덮어쓰지 않는다.
2. `technical_groups(view, measurements, security_links, price_basis=...)` →
   `common-classification-technical/1` 안의 기존 `technical-leaderboard/1`.
   회사 코드/발행사/증권/가격계열, 평가일, 종류주/ADR 비율, RAW/SPLIT_ADJUSTED가 맞아야 한다.
   링크는 #515의 고정 ID·검증·근거·inclusive `[valid_from,valid_to]`에
   `company_id, security_type, adr_ratio, recorded_at, acquired_at`을 더한 공통 경로용 계약이다.
   기존 링크에 없는 시각을 평가일로 채우지 않는다. 공개 합성 ID는 실자료에 사용할 수 없다.
   `measurements`는 **이미 적격성 판정을 거친 채택값**이다. 진단 VWAP×volume,
   미확인 기업행사·조정·초기화 결과를 이 어댑터로 승격하지 않는다.
   분류 미확인 행이 있으면 전체 섹터 모집단 확정이 불가하다. 신원 미확인은 해당 그룹을
   미확인으로 둔다. 검증된 멤버의 측정값만 없으면 멤버를 남기고 지표별 N만 줄인다.
   N<10의 분위/상하위10%는 null, 기존 순위·중앙값 규칙 유지. 필터 후 재순위하지 않는다.
3. `macro_projection(view, source_links=[])` → `common-classification-macro/1`.
   원천 SIC 그룹·공통 산업·기존 ETF 비교계열을 구분한다. 통계 대응은 원천
   `system/version/code`, `target_industry_id`, EXACT/SOURCE_BROADER/SOURCE_NARROWER/OVERLAP,
   근거·적용기간·기록/입수 시각이 있어야 한다. 코드 문자열만으로 매핑하지 않는다.
   자체 섹터 수익률·순환매 확률은 null이다. 구성원/비중/리밸런싱/기업행사 규칙은 미정이다.

기존 #515 `join_filtered_rows`는 명시적 `issuer_id`가 있으면 기존 `id`와 분리해서 검사한다.
필드가 없는 구 소비자만 예전 `id=issuer` 계약을 유지한다. 명시적 null은 대체하지 않는다.
Main은 같은 평가일의 validated board와 verified security link를 소비해야 한다.

## 사전등록 비교 — 실자료 실행 전 고정

- **CC-CLASSIFICATION-20261107-C1**: 원래 Universe504·재무 입력·설정·관문 고정,
  기존 분류→공통 분류 투영만 변경. 기존 저장 preview를 before로 재사용하고 after만 계산.
  회사별 Q/G·요소 유효 N·가중치·전환 사유를 기존 비교기로 기록한다. A/B/C 이름과 정의 불변.
- **CC-GATE-20261107-C1**: 기존 calc23.1의 검증된 `source_q_score`를 공통
  `(sector, accounting_template)` 내 발행사 대표 집합으로 백분위화한다. 최소20,
  fallback 없음, 기존 ≤30 기준. 새 Q축 점수는 쓰지 않는다. **진단 전용, 실제 관문 변경 없음**.
  기존 공식 관문은 기존 업종·최소8·fallback을 유지한다. 비교집단과 N 변화의 영향만 본다.
  전환에는 동일 기준일의 입력·분류·대표 증권/발행사 근거, 결손/영향 대조, 별도 오너 결정이 필요하다.
  현재 데이터에서 가격·V·전체 성과가 없으면 잠정 관문 변화가 개선이나 전략 성과라는 뜻이 아니다.

## Main용 공개 합성 입력과 기대 동작

`fixtures.json`은 SYNTHETIC만 담는다. record_cases 13개와 technical_cases 9개에 입력과
기대 상태/N/k/필터 순위를 함께 둔다. 정상·다중사업·섹터만 확인·미분류·전후 정정·미래 근거·
REIT·통신 예외·증권 누락/중복·다른 날짜/종류주/ADR·9개 유효 관측을 포함한다.
추가로 주 섹터 충돌·적용기간 외·계약 버전 불일치·빈 그룹을 검증한다.
화면은 unknown을 0점/불량기업으로 표시하지 않고 사유를 보여준다. 태그로 중복 행을 만들지 않는다.
증권 연결 오류는 필터 결합 불가, 가격 결손은 해당 지표 null, 필터 후 기존 순위 유지다.
이 fixture의 브라우저 수령·통합은 Main 확인 전까지 미완료다.

재현(저장소 루트):

```sh
PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_common_classification_fixtures.py
python implementation/tools/common_classification.py --job /private/classification-job.json --output /private/new-run
```

CLI는 네트워크가 없고 hash-pinned snapshot/retained_preview/saved_config 및
classification_store 또는 source_evidence를 입력한다. private 출력은 모든 git checkout 밖,
기존 출력 덮어쓰기 금지, 파일0600/폴더0700. manifest에 입력·출력 해시, 재개 job을 남긴다.
`reference-saved-config.json`은 이전 설정 참조를 그대로 보존하고 `saved-config.json`은
같은 설정과 새 입력/preview를 묶으므로 기존 #514 재실행 경로로 복원할 수 있다.
선택적 technical_input/macro_source_links도 파일 해시를 검증한다. 실자료는 공개 fixture와 분리한다.
`price_availability.valid=null`은 이 경로에서 가격 확보율을 측정하지 않았다는 뜻이다.
입력되지 않은 실가격을 0건 확보로 추정하지 않는다. 실제 순위0건·V0건은 단계별 실행 결과다.
테스트는 현행 pytest tests/ 자동 검색 대상이다. CI 목록/새 의존성 변경 요청은 없다.

## Main #437 질문에 대한 연결 기준

- 새 섹터 QGV의 `signal_day`는 생성기 snapshot/preview의 `valuation_date`다.
  `as_of`(가용 cutoff)나 `price_basis_date`(가격일)를 대신 쓰지 않는다. 기존 공개 공식
  생산자에 검증된 평가일 필드가 없다면 Main은 null을 유지하고 생산자별 계약을 연결한다.
- 이번 보관 Universe504의 `security_id`는 0건이다. 이를 보충하는 검증된 공개 links
  파일은 현재 인계하지 않는다. 향후 적격 자료의 company→issuer→security/series 관계가
  비공개 경로로 연결되어야 한다. 공개 배포는 별도 승인이고 ticker/CIK로 대체하지 않는다.
- #515 결합 함수에는 **보드 그룹의 전체 구성원**에 해당하는 QGV행을 제공한다.
  보드에 이미 있는 증권만으로 교집합을 만들어 결손을 숨기면 안 된다. 전체 Universe504가
  아닌 그룹이라면 확인된 공통 분류/멤버십으로 그룹을 먼저 고정한다. 그룹 밖 행은
  원래 화면 모집단·순위를 유지한다. 제공한 그룹의 필수 증권 연결이 빠지면 결합을 거부한다.
- listing-level `id`와 링크의 `issuer_id`는 다르다. 새 producer는 별도 `issuer_id`를
  전달하고 #515 확장 검사가 이를 사용한다. 구 계약에서 필드 부재일 때만 기존 동작 유지.
- 작은 표본의 미산출은 기능별로 다르다. 섹터 QGV는 N<20이면 요소점수 null,
  기술은 N<10이면 분위/상하위10% null이나 기존 ordinal rank·중앙값은 유지한다.
  신원/구성원 미확인은 rank·중앙값까지 null이다. Main이 이를 모두 같은 UI 상태로 합치지 않는다.
- `qgv-classification-links.json`은 engine preview의 input/config/cache hash와 분류 record ID를
  연결한다. 계산 preview와 saved-config 형식을 바꾸지 않는다. 기술/매크로 행도
  `classification_record_id`, 상위 `classification_hash`로 같은 기록 사용을 검증한다.
  기술 `input_hash/cache_key`는 분류·측정·증권 연결·조정 기준·기존 기술 설정 버전을 포함한다.
