# 4.5 정책·지정학 공개 게시 준비 (2026-11-07, 미적용 · 오너 승인 전)

이 문서와 `policy_impact_publish_prep.patch`는 **준비물**이다. 이 가지는 가드·워크플로를 바꾸지 않았고, 공개 파일을 저장소·Pages에 넣지 않았다. 게시는 오너 승인 뒤 별도 PR로 한다.

## 1. 후보 파일 (비공개 위치에만 있음)

| 항목 | 값 |
| --- | --- |
| 만든 방법 | Codex `tools/policy_impact.py --job real-job.json` (`public=True`, `public_macro_ids=[]`). 인계받은 #509 묶음 그대로, 수집 없음 |
| 재현 | 다시 만든 파일이 인계받은 `real-view-final.json`과 바이트까지 같음 (SHA-256 `f5b6a6d4045b61d9e6ad3d2beadaa2df84f49c8131395b41bc48cbbd9883073c`, 17,905 B) |
| 내용 수 | 정책 3 (관세·수출통제·보조금, 모두 역사 사례 · 현재 상태 UNKNOWN) · 출처 3 (모두 VERIFIED, 공식 문서) · 기업 노출 1 · 조건부 가설 1 · 검토 기록 5 |
| 위치 | Git 밖 비공개 작업 폴더(소유자만 읽기). 저장소·로그·Pages에 없음 |
| 합성 자료 | 대신 쓰지 않는다. 승인 전 공개 위치에는 파일이 없고 화면은 "자료 없음 · 정책 파일 미게시" |

## 2. 공개되는 필드 (Codex 공개 투영 그대로, 값은 여기 적지 않음)

| 묶음 | 필드 |
| --- | --- |
| 봉투 | `schema_version` `as_of` `query_timezone` `historical_pit_eligible`(false) `current_policy_revisions` `bundle` |
| bundle | `bundle_id` `generated_at` `data_kind`(REAL_REVIEWED) `policy_as_of` `score_effect`·`gate_effect`(NONE) `scope` `freshness` `refresh` `reason_codes` `historical_pit_eligible` `review_records` + 아래 넷 |
| sources | `source_id` `source_revision_id` `kind` `publisher` `url`(https) `title` `document_id` `published` `first_seen_at` `acquired_at` `revision_acquired_at` `verification_status` `evidence_locator` `content_sha256` `data_kind` |
| policies | `policy_id` `revision_id` `supersedes_revision_id` `parent_policy_id` `policy_type` `title` `issuer` `jurisdiction` `target_regions` `scope_description` `lifecycle_status` `subsidy_stage` `published` `effective_from` `effective_to` `evidence_refs` `identity_basis` `recorded_at` `change_recorded_at` `reviewed_at` `review_status` `next_review_on` `data_kind` |
| exposures | `exposure_id` `exposure_revision_id` `company_id`(기존 공개 504 종목 키) `policy_id` `policy_revision_id` `exposure_type` `evidence_status` `policy_applicability` `description` `period` `ratio` `evidence_refs` `reason_codes` `recorded_at` `reviewed_at` `review_status` `data_kind` |
| hypotheses | `hypothesis_id` `hypothesis_revision_id` `policy_id` `policy_revision_id` `company_ids` `exposure_refs` `claim` `steps` `conditions` `counter_conditions` `watch_items` `created_at` `recorded_at` `reviewed_at` `review_status` `data_kind` |
| review_records | `group` `id` `revision_id` `reviewed_at` `recorded_at` `reviewer` `author` `method`(AI_INDEPENDENT_SOURCE_CHECK) `evidence_refs`. `reviewer`·`author`는 에이전트·역할 이름표이고 사람 이름·주소가 아님 |

가격·가격 파생값·보유·거래·점수·순위·이메일은 없다. 원문 바이트는 들어가지 않고 SHA-256과 원문 주소만 들어간다.

## 3. 검증 결과 (2026-11-07, 이 가지 + 패치를 적용한 임시 작업본)

| 검사 | 결과 |
| --- | --- |
| Codex `contract.validate` (공개 504 종목, 게시된 `macro-evidence.json` 계열만 허용) | 통과 |
| 공개 경계 `require_policy_impact_public` (패치) | 실자료 후보 통과. Codex 합성 view·Main 화면 변형 3건은 모두 거부 |
| 규칙별 거부 시험 (패치의 `tests/test_policy_impact_public.py`, 4) | 키 추가·PIT·SYNTHETIC·미검증 출처·UNREVIEWED·CANDIDATE 노출·목록 밖 기업·현재 개정 불일치·검토자 이름표(공백·주소)·1 MiB 초과 모두 거부 |
| 게시 단계 (패치의 `tools/policy_impact_publish.py`) | 승인 파일 없음 → 아무것도 쓰지 않음, 합성 → 거부(종료 1), 승인 파일 → 바이트 그대로 복사 |
| Pages 가드, 빌드한 사이트 + 실자료 후보 | 패치 적용: 138 파일 PASS, 위반 0. 지금 가드(패치 없음): 같은 사이트를 FAIL로 막음(등록 안 된 파일) |
| 가드·보존·빌드·워크플로 시험 (`test_pages_artifact_guard` `test_manual_deploy_preserve` `test_pages_cockpit_build` 워크플로 정적 시험) | 패치 적용 상태에서 109 통과 |
| 화면, 실자료 비공개 확인 (`web_app_policy_impact_private.js check`) | 18 통과, 1440·390·320 페이지 넘침 0 |

## 4. 패치 내용 (`policy_impact_publish_prep.patch`, 6 파일 +218 −1, 이 가지에 `git apply --check` 통과)

1. `product/policy_impact_public.py`(새 파일): 공개 경계. Codex 계약을 다시 돌리고 공개 전용 조건만 더한다(위 3장). 계산·필터는 하지 않는다(Codex 공개 투영을 다시 만들지 않음).
2. `tools/pages_artifact_guard.py`: `policy-impact.json` 한 이름만 허용 목록에 넣고 그 파일에 위 경계를 건다. 포괄 허용 없음. 다른 규칙은 그대로.
3. `tools/policy_impact_publish.py`(새 파일): 승인된 파일 하나를 바이트 그대로 복사. 수집 없음.
4. `.github/workflows/cockpit-pages.yml`: 화면만 배포할 때 보존 단계들 뒤에 복사 한 줄. 마지막 가드가 그대로 검사한다.
5. `.github/workflows/sec-daily-public-inputs.yml`: 뉴스 단계 뒤에 복사 단계 하나(복사 + 가드). `continue-on-error` 없음: 저장소의 승인 파일이 경계를 못 넘으면 배포를 멈춘다.
6. `tests/test_policy_impact_public.py`(새 파일): 위 시험. "승인 파일이 아직 커밋되지 않았다"도 확인한다(승인 PR에서 이 줄을 바꾼다).

## 5. 승인 뒤 할 일 (승인 PR 한 개)

1. 패치 적용.
2. 후보 파일을 `implementation/src/investment_system/product/policy_impact_public.json`에 커밋(바이트 그대로). 시험의 "아직 커밋되지 않음" 줄을 "커밋된 파일 = 후보 SHA"로 바꿈.
3. 전체 시험 → CI → 병합 → 다음 정기 배포(또는 화면 배포)에서 게시. Secret이 필요 없다.

승인 범위로 따로 정할 것: (a) 이 3건 공개 여부, (b) `review_records`의 이름표(`Codex`, 검토 역할 이름) 공개 여부, (c) 갱신 방식 = 새 Codex 인계 때마다 같은 승인 PR을 되풀이(자동 수집 없음).
