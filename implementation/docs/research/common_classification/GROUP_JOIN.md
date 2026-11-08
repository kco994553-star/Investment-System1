# 공통 분류 그룹 결합 추가 계약

2026-11-08 · Codex · 기존 #516 /1 판독 계약을 변경하지 않는 명시적 추가 경로.
화면/인증/공용 가드/워크플로는 Main 담당이다. 합성 검증이며 실자료 증권 ID 확보가 아니다.

## 호출과 신뢰 경계

```python
from investment_system.research.common_classification.group_join import build_group_manifest
from investment_system.research.technical_filter_join import join_group_rows

manifest = build_group_manifest(verified_view, verified_technical, requested_group_id)
result = join_group_rows(board, qgv_rows=complete_group_rows,
    security_links=verified_links, conditions=conditions, data_kind=data_kind,
    group_manifest=manifest, group_context=pinned_request_context,
    connect_issuers=False)
```

`verified_view`와 `verified_technical`은 같은 승인 보관 묶음의 manifest/해시·접근 권한을
확인한 입력이다. 임의 객체의 hash 문자열이 같다는 사실은 인증이 아니다. `pinned_request_context`는
호출자가 요청한 평가/모집단/분류 문맥이다. 요청 행, 기술 원값이 있는 행, 필터 통과 행에서
기대 명부를 만들지 않는다. view의 원래 members/rows 전체와 technical 투영 전체가 먼저 일치해야 한다.
분류 적용일, 그룹/발행사/record ID/섹터도 대조한다. 원지표 결측은 확인된 구성원을 삭제하지 않는다.

`technical-filter-membership/1`:
- `schema_version`, `data_kind`, `membership_status` (`CONFIRMED` 또는 `UNKNOWN`), `reasons`.
- `context`: `signal_day`, `group_id`, `classification_hash`, `population_hash`,
  `universe_id`, `universe_version`, `universe_members_hash`, `dictionary_version`,
  `mapping_version`, `knowledge_as_of`, `price_basis`.
- `members[]`: `company_id`, `issuer_id`, `classification_record_id`, `security_id`, `evidence_refs`.

문맥 필드는 전부 요청 문맥과 같아야 한다. board의 날짜·그룹·population hash 및
`membership_source = common-classification:<classification_hash>`도 같아야 한다.
`universe_members_hash`는 기존 `sector_qgv.digest(sorted(view.members))`다.
`population_hash`는 기존 board 산식 그대로이며 새 해시 의미를 추가하지 않는다:
`sha256(json.dumps({group_id, signal_day, members: sorted(security_ids)}, sort_keys=True).encode())`.
이 기존 산식의 공백 포함 JSON 직렬화와 sector digest의 compact 직렬화는 서로 다르다.
소비자는 임의 JSON.stringify 해시로 대체하지 않는다. fixture에 기존 board 해시가 포함돼 있다.

## 코드 행·발행사·증권

이번 Universe504에서 공통 분류 `company_id`는 **Main `row.code` = `universe_code`**다.
2026-11-04 보관 snapshot과 view의 504개 company_id 집합이 정확히 일치함을 직접 확인했다.
Main `qgv.js::rowRecord`의 `id = r.company_id`는 기존 화면 registry ID일 수 있어 서로 다르다.
`web_assets/qgv-scores.js`는 `universe_code = U[c.company_id]`로 코드 행을 별도 공급한다.
소문자화·ticker 대입으로 대응하지 않는다. `issuer_id`는 발행사이며 하나의 발행사에 여러 코드 행이
가능하다. 코드 행을 발행사 기준으로 합치지 않는다. `security_id`는 검증된 별도 증권 ID이며
CIK/기업 ID/ticker를 대신 넣지 않는다. 기존 유효기간·종류주·ADR·조정 기준 검증은 그대로다.

그룹 입력의 code 집합은 명부의 company_id와 정확히 같아야 한다. 중복/명부 누락/그룹 밖 행은
일괄 거부한다. 상위 화면의 전체 모집단에는 다른 그룹 행이 있을 수 있다. Main은 신뢰된 그룹
명부로 그 그룹의 **전체** 행을 선택한 다음 공통 결합을 호출한다. 그룹 밖 원래 행·점수·순위는
변경하지 않는다. strict 함수에 이미 그룹 행이라고 전달한 입력의 extra 행은 거부하는 별도 경계다.

## 발행사 보완과 호환

기본 `connect_issuers=False`: 명시적 `issuer_id:null`은 기존처럼 거부한다.
`True`일 때만 같은 코드·평가일·분류 기록·해시의 적격 명부 근거로 null/부재 issuer를 보완한다.
근거 없는 값, 비어 있지 않은 기존 issuer 충돌, 제공된 row classification hash/record ID의
불일치는 거부한다. 잘못된 기존 record ID를 새 값으로 덮어쓰지 않는다.
원행은 깊은 복사로 보존하고 `issuer_connections[]`에 이전 필드 존재/값·연결 issuer·record ID·
classification hash·signal day·knowledge cutoff·근거 참조·`VERIFIED_CLASSIFICATION_RECORD`를 남긴다.
이는 ticker나 row.id fallback이 아니라 기록된 입력 연결이다. 기존 identity 링크와 다시 일치해야 한다.

새 결과 `technical-filter-join/2`는 `context`, `original_group_count`, `selected_count`,
`issuer_connections`, `rows`, `membership_validation=VERIFIED|VERIFIED_EMPTY`를 반환한다.
확인된 빈 그룹은 `VERIFIED_EMPTY / 0`이다. 명부 미확인은 빈 정상 결과가 아니다.
`join_filtered_rows`의 기존 목록 반환은 유지한다. 선택 인자 `group_manifest`와 `group_context`를
주면 같은 완전성 검사를 한다. 두 인자 없는 /1 호출은 **identity 검증만 수행하며 그룹 완전성
NOT_CHECKED**다. /1 성공을 /2 VERIFIED로 포장하지 않는다. /1의 issuer 필드 부재에 한한 기존
id 호환은 유지하되, 명시적 null에 적용하지 않는다.

기존 CONTRACT.md, fixtures.json, dictionary.json, manifest.json 바이트/핀은 유지했다.
새 GROUP_JOIN.md와 group-join-fixtures.json 및 재현 probe는 별도 group-join-manifest.json에 핀한다.
Main이 /2를 인수하기 전 기존 화면 /1 성공은 새 계약 인수 완료가 아니다.

## 반례와 재현

`group-join-fixtures.json`: 공통 base의 deep copy에 cases의 sets/removes를 순서대로 적용한다.
expected는 수작업 불변 조건이며 계산 결과를 다시 정답으로 복제하지 않았다.
정상, 행 누락, 중복, 그룹 밖, 미확인/없는 명부, 확인된 빈 그룹, 동일 발행사 복수 코드,
날짜/해시/모집단 불일치, 발행사 보완 근거 없음/충돌/적용일 불일치, 코드 대소문자 변조,
원래 순서/순위 보존 및 중앙값 필터의 23사례다. 모든 값은 SYNTHETIC이다.

```sh
python implementation/tools/research_technical_group_fixture.py --check
PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_technical_filter_membership.py implementation/tests/research/test_technical_group_shared_fixture.py implementation/tests/research/test_technical_filter_join.py
node implementation/docs/research/common_classification/consumer-probe.cjs /path/to/Main-checkout
```

Node probe는 실제 `classification.validate → groupRowsWhy → techScreen.joinRows → evaluate`를 호출한다.
화면 keep/DOM 또는 실제 브라우저 검증이 아니다. Main은 같은 fixture를 Node·실제 호출부·브라우저에
연결해야 한다. 테스트 의존성 외 새 도구 설치/실행 서비스/수집기는 없다.

통합 #519 `23dd5dc515e241c035bc48c9ebc6e1365d3ce513` 직접 대조:
- 행 누락/중복 거부, 동일 발행사 복수 코드 유지, issuer 충돌/행 날짜 불일치 거부.
- 그룹 밖 원래 점수/순위/원행은 불변. 정상 null 보완은 원행을 변경하지 않는다.
- **row_hash_mismatch**: 잘못된 row.classification_hash를 확인하지 않아 통과.
- **row_record_mismatch**: 잘못된 row.classification_record_id를 덮어쓰고 통과.
- **classification_not_applicable_on_day**: 평가일과 다른 EVALUATION_ONLY 기록으로 null issuer를 채우고 통과.
  `classification.js::groupRowsWhy`(기준 SHA 254–268행), 적용일 검증과 위 불일치 거부는 Main 수정 대상이다.
- 요청 명부/독립 context/보완 audit는 새 계약이므로 기존 판독기는 아직 읽지 않는다.
  23사례 중 기존 경로의 허용/거부 및 선택 수가 같은 것은 12사례다. 나머지 11을 모두 기존 버그로
  세지 않는다: 3개 위 반례, 7개 새 요청 계약 차이, 1개 전체 모집단/strict 그룹 입력 범위 차이다.

## 비공개 자료와 2.2.7 인계

기존 자료는 **보존됨 / 인증된 화면 전달 경로 미연결**이다. 미보유가 아니며 재다운로드하지 않았다.
repo `kco994553-star/investment-system1-raw`, ref `handoff/input-recovery-20261103`,
commit `d6196b6d1c7d73d93649f126dcd452820fea5703`,
path `handoffs/common-classification-20261107/common-classification-private.tar.gz`.
기존 검증 크기 1,575,920 bytes, SHA256 `b2987c2489823feb14995bbdf4d286d05a819d436f4d669d783a9fe888ab08ec`.
압축 member `handoff-manifest.json`, 세션 로컬의 `preservation-proof.json`; 로컬 묶음 경로는
`/workspace/private-common-classification-20261107`. 이전 원격 readback 23 members 확인을 재사용한다.

`result/classification-view.json`과 `result/qgv-classification-links.json`을 같은
`result/qgv-preview.json`에 연결한다. `common-classification-qgv-links/1`의 valuation_date,
classification_hash, preview_identity의 preview_id/input_hash/config_hash/cache_key/engine_version이
동일한 preview여야 한다. rows의 company_id로 결과 행을 찾고 classification_record_id를 view.record_id와
대조한다. 원래 preview의 504행을 보존하며 기록 없는 행도 null/사유로 유지한다. 2.2.7 화면 대조는 Main 담당.
공개 파일에 이 실자료를 복사하거나 전달 권한을 우회하지 않는다.

실자료 신규 계산/연결/채택 **0**. 기존 Q213/G293, 하위 산업90행/89발행사는 재사용 수량이다.
기존 고정 증권 ID/기술 순위/매크로 통계 대응 0건은 이번 합성 결합 인수와 구분한다.
매크로 #513 `1c9b858b`의 record_mismatch/record_withheld는 미해결 유지하며 같은 실패를 재실행하지 않았다.
