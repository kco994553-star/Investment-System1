# 4.5 나비효과 · 정책·지정학 — 화면 입력 `policy-impact-view/1`과 화면 (Main 정본)

작성 2026-11-07 Main. 같은 날 #509 인수로 개정: 화면 입력은 Codex가 만든 `policy-impact-view/1` 하나다.

**근거**
- 오너 지시 「메인 — 4.5 나비효과 '정책·지정학' 구현 지시」
- 첨부 설계 「Policy_Impact_Design_and_Prompts_20261107.md」(Codex 제안 v0.1, 이하 설계서)
- 오너 지시 「메인 — #509 정책 자료 인수 및 화면 연결」
- Codex #509 `e0bb68ddd612ecbef03dee8cf536afaa98ac8ae7`: `research/policy_impact/{contract,build}.py`, `docs/research/POLICY_IMPACT_V1.md`, `docs/research/policy_impact/*.json`

**범위**
- 병합·배포·수집·외부 모델 호출 승인이 아니다.
- QGV 점수·가중치·순위, 매크로 국면·관문, 자동매매는 바뀌지 않는다.

## 1. 위치 (새 메뉴 없음)

| 기능 | 화면 |
| --- | --- |
| 4.5.1.1 정책 사건 목록 | `#/macro` → 3.5 나비효과 → "정책 · 지정학" |
| 4.5.1.2 정책 상세·변경 이력 | `#/macro/policy/<policy_id>`, 이전 개정은 `#/macro/policy/<policy_id>/<revision_id>` |
| 4.5.2.1 기업 노출과 영향 가설 | 상세 ②·③ |
| 4.5.3.1 근거·반증·후속 확인 | 상세 ③ 반대 조건, ④ 원문·공시·변경 이력, ⑤ 다음 확인 |
| 4.5.4.1 공통 화면 연결 | 기업 화면(0. 기업 검색 → 기업)의 "관련 정책" 접힘 카드, 5.2 "관련 정책"(뉴스 → 정책), 상세의 "→ 4.1 지표 보기"(공개 지표만) |

- 4.7 메뉴는 만들지 않는다.
- `FUNCTION_HIERARCHY_v1.0.md` 본문은 바꾸지 않는다. 추가 번호는 #506이 만든 `docs/SPEC/FUNCTION_HIERARCHY_ADDITIONS.md`에 통합 때 넣는다. 이 가지는 #506과 독립이라, 지금은 이 문서와 `FUNCTION_STATUS`에 적는다.

## 2. 파일과 경로 (고정)

| 항목 | 값 |
| --- | --- |
| 공개 파일 이름 | `policy-impact.json`, 사이트 루트(다른 공개 JSON과 같은 자리) |
| 내용 | Codex `build()`의 출력 그대로: `policy-impact-view/1` 봉투와 그 안의 `policy-impact/1` bundle. 공개본은 `public=True`로 만든다 |
| 화면 읽기 | `IS2.data.static('policy-impact.json')`. 같은 출처, 자격 증명 없음, 리다이렉트 거부, 2 MiB 상한(`data.js` STATIC). 그 뒤 `IS2.policyImpact.validate` |
| 생성 | Codex 오프라인 CLI `implementation/tools/policy_impact.py --job … --output …`. 네트워크 없음. 실자료 출력은 Git 체크아웃 밖, mode 600 |
| 게시 | **아직 안 함.** 게시 승인 때 할 일: `cockpit-pages` 공개 파일 목록·Pages 가드 허용 경로에 이 한 파일을 등록하고, 실패 시 마지막 정상본을 유지한다. 지금 가드·워크플로는 바꾸지 않았다 |
| 파일이 없을 때 | 404 → "자료 없음 · 정책 파일 미게시". 합성 파일로 채우지 않는다. 합성 자료는 시험에서 명시적으로만 넣는다 |
| 언제 읽나 | `정책·지정학 열기`를 누를 때, 정책 주소로 들어올 때, 기업 화면 "관련 정책"을 펼칠 때, 5.2 `관련 정책 연결 보기`를 누를 때. `#/macro`를 열기만 해서는 읽지 않는다 |
| 비공개 실자료(개발 전용) | `tools/web_app_policy_impact_private.js serve|check` + `POLICY_IMPACT_PRIVATE_VIEW=<절대 경로>`. 127.0.0.1에서만, `REAL_REVIEWED`·Git 밖·mode 600·8 MiB 이하만 받는다. 복사·게시·저장·스크린숏 없음, 출력은 PASS와 개수뿐. CI 밖 |

## 3. 화면 입력 = Codex `policy-impact-view/1` (Main 인수)

Main이 앞서 낸 초안 `policy-impact/1`(Main 필드 이름)은 **철회**한다. 필드·코드·의미는 Codex `contract.json`(SHA-256 `27f19446…db77`)과 `contract.py`가 정본이다. 화면은 그 출력을 읽기만 한다.

### 3.1 봉투와 bundle

- 봉투 키: `query_timezone`, `schema_version`(`policy-impact-view/1`), `bundle`, `current_policy_revisions`, `as_of`, `historical_pit_eligible`(false).
- bundle 키: Codex `contract.json`의 `required_top_fields` 17개(`review_records` 포함). records 4종은 `(id, revision)` 쌍이 키다.
- `as_of` = 조회 시각, `bundle.policy_as_of` = 실제 확인 시각(그 조회 시점에 확인 기록이 없으면 null + 사유), `generated_at` = 파일 생성 시각. 셋을 따로 보인다.

### 3.2 화면이 계산하지 않는 것 (엔진 출력 그대로)

| 항목 | 화면이 읽는 것 |
| --- | --- |
| 현재 개정 | `current_policy_revisions[policy_id]`가 가리키는 개정. 날짜·`supersedes`로 고르지 않는다. 나머지 개정은 "이전 개정"으로 함께 보인다 |
| 목록 순서 | bundle의 정책 순서(엔진이 정렬). 화면은 다시 정렬하지 않는다 |
| 근거 가용 시각 | 엔진이 조회 시점 밖의 근거·노출·가설을 이미 뺐다. 화면은 시각을 비교하지 않는다 |
| 재검토 | `review_status = REVIEW_REQUIRED`를 "이전 분석 · 재검토 필요"로, 현재 판단과 나눠 보인다. 화면이 바꾸지 않는다 |
| 검토 기한 | `freshness.review_due`(true / false / null=미정) 그대로 |
| 상태 | `lifecycle_status` 그대로. 날짜가 상태를 바꾸지 않는다. bundle 사유 `HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED`가 있고 상태가 `UNKNOWN`이면 "역사 사례 · 현재 상태 미확인" |

### 3.3 판독기 규칙 (파일 전체 거부, 첫 위반에서)

- Codex `contract.py`와 같은 검사·같은 코드: `FIELDS`·`VERSION`·`FORBIDDEN_EFFECT`·`PIT_UNPROVEN`·`DATA_KIND`·`COVERAGE`·`MIXED_KIND`·`DUPLICATE_REVISION`·`ENUM`·`TIME`·`UTC_REQUIRED`·`DATE`·`DATE_TIMEZONE`·`PRECISION`·`UNSAFE_URL`·`SOURCE_HASH`·`SOURCE_TIME_ORDER`·`SOURCE_REF`·`EVIDENCE_LOCATION`·`UNSTABLE_POLICY_ID`·`REVISION_REF`·`PARENT_REF`·`SUBSIDY_STAGE`·`POLICY_REF`·`NULL_REASON`·`RATIO`·`RATIO_SCOPE`·`EXPOSURE_REF`·`EPISTEMIC`·`REVIEW_REF`·`INDEPENDENT_REVIEW`·`MANUAL_NOT_AUTO`·`INCOMPLETE_RANGE`·`POLICY_IDENTITY_MUTATION`. 키 누락·모르는 키는 `KEY_MISSING`·`KEY_UNKNOWN`, 글자 배열에 객체는 `TEXT`.
- Main이 더한 것(공개 화면 경계):
  - `VIEW_VERSION` · `TIMEZONE`: 봉투
  - `CURRENT_REF`: `current_policy_revisions`가 모든 정책을 정확히 한 번, 있는 개정으로 가리켜야 함
  - `UNREVIEWED_PUBLIC` · `CANDIDATE_PUBLIC`: 공개 파일에 미검토 기록·후보 노출 없음
  - `STALE_NOT_FLAGGED`: 현재가 아닌 개정 위의 노출·가설은 `REVIEW_REQUIRED`여야 함
  - `SYNTHETIC_REAL_LINK`: 합성 파일은 예약 도메인 링크만
- 링크: https이고 자격 증명이 없고 예약 도메인(RFC 2606/6761)이 아닌 것만 새 창 링크(`noopener noreferrer`). 나머지는 글자.

### 3.4 Main 초안과의 차이 (Codex 계약으로 정리)

| Main 초안 | Codex 계약 | 화면 |
| --- | --- | --- |
| `policies[].change_reason` | 없음 | 개정 id · 대체한 개정 · 변경 기록 시각만 보인다 |
| `policies[].amounts` | v1에 금액 없음 | 지원 단계만. "금액은 이 규격에 없음" |
| `exposures[].ratio_null_reason` | `reason_codes` 배열 | 사유 글자를 이어 보인다. "0%가 아님" |
| `ratio.unit = RATIO` | `fraction` | % 로 보인다 |
| `scope.source_kinds` | `scope.source_scope`(자유 글자) | 띠에 쓰지 않음 |
| `watch_items[].availability` 열거 | 자유 글자(`PUBLIC_REFERENCE`·`UNAVAILABLE` 확인) | 아는 값만 한글, 나머지는 코드 그대로. 4.1 링크는 `MACRO_SERIES`+`PUBLIC_REFERENCE`만 |
| 개정을 화면이 고름 | `current_policy_revisions` | 엔진 값 |
| 정책 제목 | 실자료 `title` = 정책 id | 그대로 보인다(사람이 읽을 제목은 Codex에 요청) |

## 3.5 실자료 (비공개, #509 인계)

- 보관: 비공개 저장소 `investment-system1-raw`, ref `handoff/input-recovery-20261103`, commit `838579716e6cfb2ca922637bf5bb41078489bcbb`, `handoffs/policy-impact-20261107`. manifest·묶음 SHA-256은 #437 Codex 댓글과 같음을 확인했다.
- 내용: 역사 정책 3(관세·수출통제·보조금), 프로젝트 노출 1, 조건부 가설 1. 현재 상태는 모두 UNKNOWN. 검토는 AI 독립 원문 대조(사람 검토 아님).
- 화면: 셋 다 "역사 사례 · 현재 상태 미확인". 관세·수출통제는 노출 없이 읽히고 "연결 근거 미확인 (영향 없음이라는 뜻이 아님)". 보조금은 "확정 지원 발표 · 실제 지급 아님(지급 미확인)".
- 공개 게시 승인 없음(`public_publication_approved=false`). 저장소·Pages·로그에 넣지 않는다.

## 4. 화면 상태

| 상태 | 화면 |
| --- | --- |
| 파일 미게시(404) | 자료 없음 · 정책 파일 미게시 |
| 규격 위반 | 규격 불일치 · 파일 전체 거부 + 코드·경로 |
| 읽기 실패 | 불러오기 실패 + 다시 읽기 |
| 정책 0건 | 등록된 정책 0건 · 검토 범위에 아직 없음 · 영향 없음이 아님 |
| 필터 0건 | 검색 결과 0건 · 조건은 그대로 + 조건 모두 풀기 |
| 수동 검토 | 수동 검토 자료 · 마지막 수동 검토 · 자동 수집 결과가 아님 |
| 자동 갱신 일부 실패·실패·불완전 | 해당 문구 + 마지막 성공 + 유지한 정상본 + 미조회 구간 |
| 검토 기한 지남 | 검토 예정일 지남 · 재검토 필요 (효력이 끝났다는 뜻이 아님) |
| 합성 / 실자료 | 합성 · 시험용 / 실자료 · 검토 기록 있음 |
| 역사 사례 | 역사 사례 · 현재 상태 미확인 (bundle 사유와 UNKNOWN 상태) |
| 노출 없음 | 연결된 기업 노출 기록 없음 · 연결 근거 미확인 (영향 없음이라는 뜻이 아님) |
| 검토 예정 없음 | 다음 검토 예정일 미정 (`review_due = null`) |
| 잘못된 정책 주소 | 정책 없음 · 잘못된 주소 |

- **글자:** 모두 텍스트 노드로 넣는다(HTML 해석 없음). https이고 예약 도메인이 아닌 링크만 새 창 링크(`noopener noreferrer`)로 만든다.
- **읽지 않는 것:** QGV·가격·저장소·엔진. 시험이 소스에서 이를 확인한다.

## 5. 겹치는 열린 PR (2026-11-07 확인)

| PR | 겹침 | 처리 |
| --- | --- | --- |
| #488 / #493 (`screen-macro-live.js`) | 3.5 블록 끝에 정책 칸 한 덩어리와 호출 한 줄 | 줄 추가뿐. 병합 때 줄 단위로 합침 |
| #490 / #493 (`screen-news-live.js`) | 5.2 칸에 "관련 정책" 블록 하나와 호출 | 줄 추가뿐 |
| #506 (`screen-search-live.js`) | 기업 화면 `company()`의 카드 호출 줄 바로 뒤 한 줄 | 줄 추가뿐. #506의 마크 줄과 다른 자리 |
| #506 (`FUNCTION_HIERARCHY_ADDITIONS.md`) | 4.5 추가 번호 | 통합 때 그 파일에 더함 |
| #477 / #483 / #503 | 계약 재사용(공개 지표 키, 뉴스 링크, 기업 키) | 이 화면은 공개 4.1 지표로 이동만 하고 값을 옮기지 않는다. 뉴스 링크는 읽기만 한다 |

## 6. Codex 인계 (확인 결과와 요청)

- 화면 입력 계약을 Codex `policy-impact-view/1`로 인수했다(위 3장). Main 초안 fixture `tests/fixtures/policy_impact_v1_synthetic.json`과 생성기는 지웠다.
- 호환: `synthetic-view.json`과 `synthetic-states.json` 기대 4건이 모두 Codex `build()` 출력과 같고(pytest), Main 판독기가 모두 받는다(node). 실자료 `real-view-final.json`도 받는다(비공개 확인).
- 화면 시험용 변형 3건(REVISED·HISTORICAL·NEWS)은 Codex `build()`로 만든다(`tools/policy_impact_main_variants.py`). Main이 손으로 쓴 view는 없다.

**Codex에 부탁할 일**
1. 사람이 읽을 정책 제목: 실자료 `title`이 정책 id와 같다. 뜻을 바꾸지 않는 한 `policy-impact/1` 안에서 고쳐 주면 된다.
2. `watch_items[].availability` 값 목록을 `contract.json` enum으로 고정해 달라(지금 `PUBLIC_REFERENCE`·`UNAVAILABLE`).
3. 공개 투영은 미검증 출처를 빼므로 뉴스 참조(#483 `from_news_reference`, 늘 `SOURCE_UNVERIFIED`)가 공개 파일에 남지 않는다. 그래서 5.2 → 4.5 연결은 공개 자료에서 0건이 정상이다. 공개에 남길지 결정이 필요하면 알려 달라.
4. 필드 의미를 바꾸면 `policy-impact/2`·`policy-impact-view/2`로 알려 달라.

**시험 담당**

| 담당 | 시험 |
| --- | --- |
| Codex(생성 쪽) | P01~P19·P22 데이터 사례(`tests/research/test_policy_impact.py`, 45개) |
| Main(이 화면) | P20 동선, P21 접근성, 브라우저 P19(글자·링크 안전), 엔진 출력 호환 |

## 7. 시험

| 시험 | 범위 |
| --- | --- |
| `tests/research/test_policy_impact.py` (Codex, 45) | 데이터 사례. build 단계 `pytest tests`에 수집된다(이 가지에서 45개 수집 확인) |
| `tests/test_policy_impact_main_variants.py` (4) | Codex synthetic-view·state 기대값 = Codex `build()` 출력; Main 변형 파일 = 생성기 출력; 철회한 초안 fixture 없음 |
| `tools/web_app_policy_impact_node_test.js` (11) | #437 SHA-256 4개 고정; 계약 enum 일치; 합성 view·state 4건 통과; 현재 개정은 엔진 값만(파일을 바꾸면 따라감); REVIEW_REQUIRED 그대로; 역사 사례·노출 없는 관세/수출통제·FINAL_AWARD ≠ 지급; 목록·필터·기업 요약; 뉴스 참조; 링크; 거부 코드 50여 건; 판독기·화면 소스에 요청·저장·시계·시각 정렬·점수·순위 없음 |
| `tools/web_app_policy_impact_browser_test.js` (16) | 미게시·규격 위반·봉투 없는 bundle·읽기 실패 → 다시 읽기; 1440·390 목록(엔진 순서)·상세 ①~⑤·기업 카드(키보드)·뒤로 ×3(필터·스크롤 복원)·이전 개정·잘못된 주소·역사 사례·5.2 연결·경계; 320 / 390 / 720(=1440 200%) / 1440 |
| `tools/web_app_policy_impact_private.js check` (CI 밖) | 실자료로 1440·390·320: 엔진 순서, 실자료 띠, 역사 사례 3건, 노출 없는 2건의 "연결 근거 미확인", 보조금 지급 아님, 원문 링크 `noopener noreferrer`, 노출 → 기존 기업 화면 → 관련 정책 1건 → 뒤로, 출처 밖 요청 0 |
| 회귀 | 저장소 전체 시험(매크로·뉴스·기업·QGV 화면 시험 포함) |

**320 px:** 정책 칸 안은 넘치지 않는다(긴 원문 링크는 줄바꿈). 다만 기존 3.1 국면 고리 때문에 페이지 전체가 40 px 넘친다. 이 기능 밖(#488·#493 영역)이라 바꾸지 않고 보고한다.
