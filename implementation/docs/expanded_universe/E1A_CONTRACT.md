# E0 / E1-A 실행 계약 — 2026-10-29

사용자가 제공한 Codex 명세·공통 계약과 이번 직접 실행 승인에 따른 독립 작업이다.
기준 HEAD: `282382a76c963e885bfd090d3eec79543bcd90e0`.
코드·시험은 합성 입력 전용으로 검증한다. 실자료 커버리지·수집·가격·QGV·운영은 NOT_RUN.

## 결정

기존 `UniverseMember`는 발행사 단위이고 `DataEvent`는 계산 dirty set용이다.
이를 상장 증권 사건 원장으로 바꾸면 기존 계약을 침범한다. 기존 `resolve.company_id_for`
CIK 식별 관례를 재사용하되, 별도 immutable 모델과 사건 원장을 사용한다.
현재 수집기에 어댑터를 붙이는 대안은 E1-B 승인·권리 검증 뒤 Main 담당이다.

- `expanded_catalog.py`: Policy, Issuer, SecurityRecord, ListingEvent, CatalogSnapshot,
  Rejection, ValidationResult; normalize_security_record, validate_catalog.
- `expanded_catalog_events.py`: apply_listing_events, diff_snapshots.
- `expanded_catalog_snapshot.py`: 결정적 private 직렬화/hash, 전체 batch 성공 시에만
  새 객체를 반환하는 dry_run_refresh, 집계 전용 render_private_receipt.
- 기존 파일·`__init__.py`·workflow·웹·공용 문서는 수정하지 않는다.

## 식별·시간

CIK는 ASCII 양의 1~10자리만 받아 10자리로 정규화한다. issuer_id는 기존
`cik:<10자리>` 관례다. 영구 security_id는 검증한 입력으로만 받고 티커에서 만들지 않는다.
CIK 미확인은 IDENTITY_AMBIGUOUS다. CIK 없는 발행사의 권위 있는 ID 매핑은 후속 계약이다.
같은 CIK의 여러 종류주는 하나의 발행사, 여러 증권으로 보존한다.

UTC timezone-aware 시각 필수. effective_at과 available_at은 별개이며 사전 발표와
지연 공개를 모두 허용한다. available_at > collected_at은 거절한다. 모든 시각 결측은
거절하며 현재 시각으로 보완하지 않는다. cutoff는 이전 as_of보다 작을 수 없다.
공개·효력 시각이 cutoff를 넘은 사건은 원장에는 보존하고 현재 상태에는 적용하지 않는다.
과거 자료를 오늘 수집해도 collected_at을 과거로 꾸미지 않는다.

보존된 사건 + 새 사건을 효력순으로 재생한다. 늦게 도착한 사건도 이력에 반영된다.
같은 증권·같은 효력 시각의 서로 다른 사건은 순서를 추측하지 않고 거절한다.
event_id 중복은 collected_at을 제외한 내용이 같을 때만 무시하고 충돌은 전체 거절한다.
첫 batch의 중복은 가장 이른 수집 사본을 선택하며 이후 재수집은 원래 수집 시각을 보존한다.
합병 상대 증권도 같은 시각에 변경되는 경우 순서를 추측하지 않고 전체 보류한다.
유효기간은 [valid_from, valid_to); 티커·거래소·종류·이름 변경은 이전 구간을 닫는다.
상폐/합병은 종전 구간을 보존한다. 재상장 시 새 security_id가 필요하다.

## 정책·출력

기본 거래소는 NASDAQ/NYSE/NYSE_AMERICAN/BATS, 정책에 명시해 변경 가능하다.
COMMON/COMMON_CLASS 적격, ETF/CLOSED_END_FUND/PREFERRED/WARRANT/RIGHT/UNIT 제외,
ADR/REIT는 기본 SOURCE_POLICY_PENDING이다. 포함/제외는 명시적 정책이고 투자 적격 판정이 아니다.
security_count/issuer_count는 현재 카탈로그 전체이며 included는 현재 보통주 정책 통과분이다.
종료 기록과 모든 사건은 별도 보존한다. 가격·시총 계산은 없다.

모든 외부 dict는 정확한 키 집합·값 형을 검사한다. 오류/거절 repr은 고정 사유 코드만
보이고 입력값을 되비추지 않는다. snapshot/event/record repr은 회사별 값·원장을 숨긴다.
private 직렬화는 공개 승인이 아니다. 공개 직렬화 경로는 없다.
receipt는 집계·정해진 상태/사유·카탈로그 hash만 받으며 임의 로그 메시지를 받지 않는다.

## 실행 계획

1. C01/C06/C07/C08/C05 정규화·스키마 실패 시험 → 순수 모델 구현 → 관련 기존 시험.
2. C02/C03/C04/C10 이력·역순·PIT·중복·충돌 실패 시험 → 사건 재생/diff 구현 → 회귀.
3. C09/C11/C12 실패 보존·비밀 차단·기존 504 불변 시험 → dry-run/hash/receipt 구현 → 회귀.
4. 공급원별 권리/비용 증거, E1-B/E2 계획, 직접 실행 결과·Main 인계 작성.
5. 전체 Python 시험과 기존 필수 guard 실행, 독립 검토, commit/push/Draft PR.

추가 검토 초점: 같은 시각 충돌, 이벤트 ID 내용 충돌, 늦게 도착한 과거 사건,
직접 생성한 무효 dataclass, 정책 변경을 숨긴 재실행. 각각 독립 반례로 시험한다.
모든 검증 이후에만 TESTED로 보고하며 INTEGRATED/DEPLOYED/LIVE_VERIFIED로 올리지 않는다.
